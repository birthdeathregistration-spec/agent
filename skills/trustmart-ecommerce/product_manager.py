#!/usr/bin/env python3
"""
TrustMart 2.0 — Admin Product & Combo Manager Skill
Allows authenticated admins to create combos and edit products dynamically.
"""

import os
import sys
import json
import time
import re
import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, '..', '..', '..'))
CATALOG_PATH = os.path.join(ROOT_DIR, 'catalog_seo.json')

# Load environment
def load_env(env_path):
    if not os.path.exists(env_path):
        return
    with open(env_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                k, v = line.split('=', 1)
                if k.strip() not in os.environ:
                    os.environ[k.strip()] = v.strip().strip('"').strip("'")

load_env(os.path.join(ROOT_DIR, 'hermes-agent', '.env'))
load_env(os.path.join(ROOT_DIR, '.env'))

ADMIN_USER_ID = str(os.environ.get('TELEGRAM_ALLOWED_USERS', '7886593741'))

def is_admin(user_id):
    if not user_id:
        return False
    return str(user_id).strip() == ADMIN_USER_ID.strip()

def load_catalog():
    if not os.path.exists(CATALOG_PATH):
        return {"products": []}
    with open(CATALOG_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_catalog(data):
    with open(CATALOG_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def slugify(text):
    text = re.sub(r'[^\w\s-]', '', text.lower()).strip()
    slug = re.sub(r'[\s_-]+', '-', text)
    if not slug:
        slug = f"bundle-{int(time.time())}"
    return slug

def find_product(query, products):
    q = query.strip().lower()
    # 1. Exact slug or id or sku
    for p in products:
        if p.get('slug') == q or p.get('id') == q or p.get('sku') == q:
            return p
    # 2. Substring in slug
    for p in products:
        if q in (p.get('slug') or '').lower():
            return p
    # 3. Substring in name
    for p in products:
        if q in (p.get('name') or '').lower():
            return p
    return None

def create_combo(title, price, product_queries, admin_id=None):
    """
    Create a new bundle/combo product from a list of queries.
    Only admin can execute.
    """
    if admin_id and not is_admin(admin_id):
        return {
            "success": False,
            "message": "⛔ অনুমতি নেই: কম্বো শুধুমাত্র ট্রাস্টমার্ট অ্যাডমিন তৈরি করতে পারবেন।"
        }

    catalog = load_catalog()
    products = catalog.get('products', [])

    found_items = []
    for pq in product_queries:
        prod = find_product(pq, products)
        if prod:
            found_items.append(prod)

    if len(found_items) < 2:
        return {
            "success": False,
            "message": f"কম্বো তৈরির জন্য কমপক্ষে ২টি প্রোডাক্ট প্রয়োজন। খুঁজে পাওয়া গেছে: {len(found_items)}টি।"
        }

    regular_total = sum(int(it.get('price') or 0) for it in found_items)
    combo_price = int(price)
    slug = f"combo-{slugify(title)}"

    # Primary image from first item
    primary_img = found_items[0].get('image') or ''

    items_summary = []
    for it in found_items:
        items_summary.append({
            "id": it.get('id'),
            "name": it.get('name'),
            "price": it.get('price'),
            "image": it.get('image'),
            "slug": it.get('slug')
        })

    new_combo = {
        "id": f"combo-{int(time.time())}",
        "sku": f"COMBO-{int(time.time())}",
        "slug": slug,
        "name": title,
        "price": combo_price,
        "regularPrice": regular_total,
        "stock": 50,
        "category": "Book Bundles",
        "subCategory": "Special Combo",
        "childCategory": "",
        "brand": "TrustMart Bundles",
        "author": "Various",
        "publisher": "TrustMart",
        "image": primary_img,
        "description": f"স্পেশাল কম্বো অফার: {title}। একসাথে পাচ্ছেন: " + ", ".join([it.get('name') for it in found_items]) + f"। সারা দেশে হোম ডেলিভারি সম্পূর্ণ ফ্রি!",
        "is_bundle": True,
        "items": items_summary,
        "createdAt": datetime.date.today().isoformat()
    }

    # Add to catalog
    products.insert(0, new_combo)
    catalog['products'] = products
    save_catalog(catalog)

    # Generate combo poster
    poster_path = os.path.join(ROOT_DIR, f"{slug}-poster.jpg")
    try:
        from poster_generator import generate_combo_poster
        generate_combo_poster(new_combo, poster_path)
    except Exception as e:
        print(f"Combo poster generation notice: {e}")
        poster_path = None

    return {
        "success": True,
        "combo": new_combo,
        "poster_path": poster_path,
        "message": f"✅ কম্বো '{title}' সফলভাবে তৈরি হয়েছে!\n💰 কম্বো মূল্য: ৳{combo_price} (রেগুলার: ৳{regular_total})\n🔥 সাশ্রয়: ৳{regular_total - combo_price}\n🔗 লিঙ্ক: https://trustmart.bd/product/{slug}"
    }

def edit_product(identifier, updates, admin_id=None):
    """
    Edit product details (price, stock, name, regularPrice).
    Only admin can execute.
    """
    if admin_id and not is_admin(admin_id):
        return {
            "success": False,
            "message": "⛔ অনুমতি নেই: প্রোডাক্ট শুধুমাত্র ট্রাস্টমার্ট অ্যাডমিন এডিট করতে পারবেন।"
        }

    catalog = load_catalog()
    products = catalog.get('products', [])

    prod = find_product(identifier, products)
    if not prod:
        return {
            "success": False,
            "message": f"প্রোডাক্ট পাওয়া যায়নি: '{identifier}'"
        }

    applied = {}
    for k, v in updates.items():
        if k in ['price', 'stock', 'regularPrice']:
            try:
                prod[k] = int(v)
                applied[k] = int(v)
            except ValueError:
                pass
        elif k in ['name', 'description', 'category', 'brand']:
            prod[k] = str(v).strip()
            applied[k] = str(v).strip()

    save_catalog(catalog)

    return {
        "success": True,
        "product": prod,
        "applied": applied,
        "message": f"✅ প্রোডাক্ট '{prod.get('name')}' আপডেট সম্পন্ন হয়েছে!\n" + "\n".join([f"• {k}: {v}" for k, v in applied.items()])
    }

if __name__ == '__main__':
    # Test CLI execution
    print("TrustMart Product Manager initialized. Admin:", ADMIN_USER_ID)
