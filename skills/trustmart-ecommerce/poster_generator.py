#!/usr/bin/env python3
"""
TrustMart.bd — Autonomous Marketing Poster Generator & Facebook/Telegram Publisher
Generates 1080x1080 high-converting e-commerce posters and publishes them with AI sales copy.
"""

import os
import sys
import json
import io
import math
import urllib.request
import urllib.parse
from PIL import Image, ImageDraw, ImageFont, ImageFilter

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Configuration
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, '..'))
CATALOG_PATH = os.path.join(ROOT_DIR, 'catalog_seo.json')

# Ensure Windows loads fribidi.dll for Pillow libraqm HarfBuzz text shaping
if sys.platform == 'win32':
    for p in [ROOT_DIR, SCRIPT_DIR, os.path.join(ROOT_DIR, 'Library', 'bin')]:
        if hasattr(os, 'add_dll_directory') and os.path.exists(p):
            try:
                os.add_dll_directory(p)
            except Exception:
                pass

# Load environment
def load_env(env_path):
    if not os.path.exists(env_path):
        return
    with open(env_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                k, v = line.split('=', 1)
                k = k.strip()
                v = v.strip().strip('"').strip("'")
                if k not in os.environ:
                    os.environ[k] = v

load_env(os.path.join(ROOT_DIR, 'hermes-agent', '.env'))
load_env(os.path.join(ROOT_DIR, '.env'))

GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', 'AQ.Ab8RN6LeUWlqqG21b2RGTuml_htnq1IC9k990-Hv0-SWMr0xzw')
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '8664874586:AAG7-JWqJzR5JBZUQ5L6Pag4bh4oA7jhy0Y')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID', '7886593741')
META_PAGE_ACCESS_TOKEN = os.environ.get('META_PAGE_ACCESS_TOKEN', 'EAAPRtR8kva4BShocCkvYmuZBLNBWYiZACG3P2QQ12ouuriQUQ9yf0HBC8v5xEWFh847WlmvoJSRRm0FjG30Gsk9Gco5mvUzvTSCKZCBwek8l7WoZBF7XvG2lnJkSuShKZAzfM61ZCylxK4dv6n0P7PK6DY3WLfbToHS9tp8WZB72JgId1lf9G3DJcerPh6DaZBdDl4wCxvWd5GO0yzj8GqlCZBgZDZD')
META_PAGE_ID = os.environ.get('META_PAGE_ID', '1299020649957056')

def get_bengali_font(size=24, bold=False):
    """
    Load a high-quality Bengali Unicode font with HarfBuzz/Raqm complex text shaping.
    Prioritizes Hind Siliguri (the gold standard for modern Bangla typography),
    followed by Noto Sans Bengali.
    """
    font_name = "HindSiliguri-Bold.ttf" if bold else "HindSiliguri-SemiBold.ttf"
    fallback_name = "HindSiliguri-Regular.ttf"

    candidates = [
        os.path.join(SCRIPT_DIR, "fonts", font_name),
        os.path.join(ROOT_DIR, "fonts", font_name),
        os.path.join(SCRIPT_DIR, "fonts", fallback_name),
        os.path.join(ROOT_DIR, "fonts", fallback_name),
        os.path.join(SCRIPT_DIR, "fonts", "NotoSansBengali.ttf"),
        os.path.join(ROOT_DIR, "fonts", "NotoSansBengali.ttf"),
        os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Fonts", "Nirmala.ttc"),
        os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Fonts", "NirmalaB.ttf"),
        os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Fonts", "vrinda.ttf"),
    ]
    for p in candidates:
        if os.path.exists(p):
            try:
                if p.endswith('.ttc'):
                    idx = 1 if bold else 0
                    return ImageFont.truetype(p, size, index=idx)
                return ImageFont.truetype(p, size)
            except Exception:
                continue
    try:
        return ImageFont.truetype("arial.ttf", size)
    except Exception:
        return ImageFont.load_default()

def get_font(name="segoeui.ttf", size=24):
    windir = os.environ.get('WINDIR', 'C:\\Windows')
    font_path = os.path.join(windir, 'Fonts', name)
    if os.path.exists(font_path):
        try:
            return ImageFont.truetype(font_path, size)
        except Exception:
            pass
    try:
        return ImageFont.truetype("arial.ttf", size)
    except Exception:
        return ImageFont.load_default()

def create_gradient(width, height, top_color, bottom_color):
    base = Image.new('RGB', (width, height), top_color)
    top_r, top_g, top_b = top_color
    bot_r, bot_g, bot_b = bottom_color
    draw = ImageDraw.Draw(base)
    for y in range(height):
        ratio = y / float(height)
        r = int(top_r + (bot_r - top_r) * ratio)
        g = int(top_g + (bot_g - top_g) * ratio)
        b = int(top_b + (bot_b - top_b) * ratio)
        draw.line([(0, y), (width, y)], fill=(r, g, b))
    return base

def download_image(url):
    try:
        # Properly quote non-ASCII characters in URL path
        parts = urllib.parse.urlsplit(url)
        quoted_path = urllib.parse.quote(parts.path)
        quoted_url = urllib.parse.urlunsplit((parts.scheme, parts.netloc, quoted_path, parts.query, parts.fragment))
        
        req = urllib.request.Request(quoted_url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
        with urllib.request.urlopen(req, timeout=15) as response:
            return Image.open(io.BytesIO(response.read())).convert('RGBA')
    except Exception as e:
        print(f"Failed to download image {url}: {e}")
        return None

def draw_wrapped_bengali_text(draw, text, x, y, max_w, font, fill=(255, 255, 255), max_lines=2):
    words = text.split()
    lines = []
    curr = []
    for w in words:
        test = " ".join(curr + [w])
        bbox = draw.textbbox((0, 0), test, font=font)
        if (bbox[2] - bbox[0]) <= max_w:
            curr.append(w)
        else:
            if curr:
                lines.append(" ".join(curr))
                curr = [w]
            else:
                lines.append(w)
                curr = []
    if curr:
        lines.append(" ".join(curr))
    
    cur_y = y
    for line in lines[:max_lines]:
        draw.text((x, cur_y), line, fill=fill, font=font)
        bbox = draw.textbbox((0, 0), line, font=font)
        cur_y += (bbox[3] - bbox[1]) + 8
    return cur_y

def generate_poster(product, output_path="trustmart_ad_poster.jpg"):
    W, H = 1080, 1080
    # Gradient Dark Luxury Navy background
    img = create_gradient(W, H, (10, 17, 40), (28, 37, 65))
    draw = ImageDraw.Draw(img)

    # Decorative subtle circles
    draw.ellipse((-150, -150, 350, 350), fill=(30, 58, 138, 40))
    draw.ellipse((W - 250, H - 350, W + 200, H + 100), fill=(16, 185, 129, 30))

    # Fonts with full Bengali support
    font_brand = get_font("segoeui.ttf", 36)
    font_badge = get_bengali_font(19, bold=False)
    font_title = get_bengali_font(32, bold=True)
    font_price = get_font("segoeui.ttf", 46)
    font_cta = get_bengali_font(21, bold=True)

    # 1. Header Bar
    # Logo Badge
    draw.rounded_rectangle([(50, 40), (280, 95)], radius=12, fill=(37, 99, 235))
    draw.text((70, 48), "TrustMart.bd", fill=(255, 255, 255), font=font_brand)
    draw.text((305, 58), "Official E-Commerce Marketplace", fill=(203, 213, 225), font=get_font("segoeui.ttf", 20))

    # Top Right Verified Badge (Bangla)
    draw.rounded_rectangle([(W - 280, 45), (W - 50, 92)], radius=20, fill=(16, 185, 129))
    draw.text((W - 255, 54), "✓ ১০০% আসল প্রোডাক্ট", fill=(255, 255, 255), font=font_badge)

    # 2. Centered Product Image Card
    card_x1, card_y1 = 190, 125
    card_x2, card_y2 = W - 190, 715
    # Drop shadow
    draw.rounded_rectangle([(card_x1 + 6, card_y1 + 8), (card_x2 + 6, card_y2 + 8)], radius=24, fill=(5, 10, 25))
    # Card background
    draw.rounded_rectangle([(card_x1, card_y1), (card_x2, card_y2)], radius=24, fill=(255, 255, 255))

    prod_img_url = product.get('image') or product.get('Image_URL')
    if prod_img_url:
        prod_img = download_image(prod_img_url)
        if prod_img:
            # Resize image to fit nicely within card
            avail_w = card_x2 - card_x1 - 40
            avail_h = card_y2 - card_y1 - 40
            prod_img.thumbnail((avail_w, avail_h), Image.Resampling.LANCZOS)
            px = card_x1 + (card_x2 - card_x1 - prod_img.width) // 2
            py = card_y1 + (card_y2 - card_y1 - prod_img.height) // 2
            img.paste(prod_img, (px, py), prod_img if prod_img.mode == 'RGBA' else None)

    # 3. Floating Offer / Price Tag
    price_val = product.get('price') or product.get('Price') or '390'
    price_pill = [(W - 320, 625), (W - 80, 735)]
    draw.rounded_rectangle([(price_pill[0][0] + 4, price_pill[0][1] + 4), (price_pill[1][0] + 4, price_pill[1][1] + 4)], radius=18, fill=(0, 0, 0))
    draw.rounded_rectangle(price_pill, radius=18, fill=(225, 29, 72))  # Vibrant Rose/Red
    draw.text((price_pill[0][0] + 25, price_pill[0][1] + 10), f"৳ {price_val}", fill=(255, 255, 255), font=font_price)
    draw.text((price_pill[0][0] + 35, price_pill[0][1] + 68), "স্পেশাল অফার", fill=(254, 205, 211), font=font_badge)

    # 4. Feature Badges Row (Bengali)
    badge_y = 740
    badges = [
        ("🚚 সারা দেশে ডেলিভারি", 50, (30, 41, 59)),
        ("💵 ক্যাশ অন ডেলিভারি (COD)", 390, (30, 41, 59)),
        ("⚡ ৭ দিনের রিটার্ন গ্যারান্টি", 745, (30, 41, 59))
    ]
    for text, bx, bg in badges:
        draw.rounded_rectangle([(bx, badge_y), (bx + 285, badge_y + 48)], radius=10, fill=bg, outline=(51, 65, 85))
        draw.text((bx + 18, badge_y + 11), text, fill=(241, 245, 249), font=font_badge)

    # 5. Product Title (Wrapped Bengali Text)
    name = (product.get('name') or product.get('Name') or 'প্রিমিয়াম প্রোডাক্ট').strip()
    draw_wrapped_bengali_text(draw, name, 50, 815, W - 100, font_title, fill=(255, 255, 255), max_lines=2)

    # 6. Bottom Call to Action Footer (Bengali)
    draw.rounded_rectangle([(50, 935), (W - 50, 1025)], radius=16, fill=(16, 185, 129))
    draw.text((80, 960), "👉 সরাসরি অর্ডার করুন: https://trustmart.bd/", fill=(255, 255, 255), font=font_cta)
    draw.text((W - 430, 960), "📞 WhatsApp অর্ডার: +8801756675724", fill=(255, 255, 255), font=font_cta)

    # Save
    img.convert('RGB').save(output_path, 'JPEG', quality=95)
    print(f"✓ Marketing poster with native Bengali typography saved: {output_path}")
    return output_path

def generate_combo_poster(combo_product, output_path="trustmart_combo_poster.jpg"):
    """
    Generate High-Converting Combo / Bundle Ad Poster
    """
    W, H = 1080, 1080
    img = create_gradient(W, H, (15, 23, 42), (30, 41, 59))
    draw = ImageDraw.Draw(img)

    font_brand = get_font("segoeui.ttf", 34)
    font_badge = get_bengali_font(20, bold=True)
    font_title = get_bengali_font(34, bold=True)
    font_price = get_font("segoeui.ttf", 48)
    font_strike = get_font("segoeui.ttf", 32)
    font_cta = get_bengali_font(22, bold=True)

    # Header
    draw.rounded_rectangle([(50, 40), (280, 95)], radius=12, fill=(37, 99, 235))
    draw.text((70, 48), "TrustMart.bd", fill=(255, 255, 255), font=font_brand)

    # Mega Combo Badge
    draw.rounded_rectangle([(W - 360, 42), (W - 50, 95)], radius=16, fill=(234, 88, 12)) # Vibrant Orange
    draw.text((W - 340, 52), "🔥 স্পেশাল কম্বো অফার 🔥", fill=(255, 255, 255), font=font_badge)

    # Image Card Container
    card_x1, card_y1 = 80, 125
    card_x2, card_y2 = W - 80, 680
    draw.rounded_rectangle([(card_x1 + 6, card_y1 + 8), (card_x2 + 6, card_y2 + 8)], radius=24, fill=(5, 10, 20))
    draw.rounded_rectangle([(card_x1, card_y1), (card_x2, card_y2)], radius=24, fill=(255, 255, 255))

    # Download items images
    items = combo_product.get('items', [])
    images_to_show = []
    for it in items[:3]:
        url = it.get('image') or it.get('Image_URL')
        if url:
            im = download_image(url)
            if im:
                images_to_show.append(im)
    
    if not images_to_show and (combo_product.get('image')):
        im = download_image(combo_product.get('image'))
        if im:
            images_to_show.append(im)

    if images_to_show:
        count = len(images_to_show)
        slot_w = (card_x2 - card_x1 - 60) // count
        avail_h = card_y2 - card_y1 - 60
        for i, im in enumerate(images_to_show):
            im.thumbnail((slot_w, avail_h), Image.Resampling.LANCZOS)
            sx = card_x1 + 30 + i * slot_w + (slot_w - im.width) // 2
            sy = card_y1 + 30 + (avail_h - im.height) // 2
            img.paste(im, (sx, sy), im if im.mode == 'RGBA' else None)
            if i < count - 1:
                # Draw a plus (+) circle between items
                px = card_x1 + 30 + (i + 1) * slot_w - 20
                draw.ellipse((px - 22, card_y1 + (card_y2 - card_y1)//2 - 22, px + 22, card_y1 + (card_y2 - card_y1)//2 + 22), fill=(234, 88, 12))
                draw.text((px - 9, card_y1 + (card_y2 - card_y1)//2 - 18), "+", fill=(255, 255, 255), font=font_title)

    # Pricing Box (Floating on right)
    price = combo_product.get('price', 0)
    regular = combo_product.get('regularPrice', price + 250)
    save = regular - price if regular > price else 0

    price_pill = [(W - 420, 580), (W - 60, 710)]
    draw.rounded_rectangle([(price_pill[0][0] + 4, price_pill[0][1] + 4), (price_pill[1][0] + 4, price_pill[1][1] + 4)], radius=18, fill=(0, 0, 0))
    draw.rounded_rectangle(price_pill, radius=18, fill=(225, 29, 72))
    draw.text((price_pill[0][0] + 25, price_pill[0][1] + 10), f"৳ {price}", fill=(255, 255, 255), font=font_price)
    if regular > price:
        draw.text((price_pill[0][0] + 210, price_pill[0][1] + 24), f"৳{regular}", fill=(226, 232, 240), font=font_strike)
        # Strike line
        draw.line([(price_pill[0][0] + 205, price_pill[0][1] + 42), (price_pill[0][0] + 320, price_pill[0][1] + 42)], fill=(255, 255, 255), width=3)
    draw.text((price_pill[0][0] + 25, price_pill[0][1] + 72), f"🔥 সাশ্রয়: ৳ {save} টাকা!", fill=(254, 240, 138), font=font_badge)

    # Badges Row
    badge_y = 730
    badges = [
        ("🚚 কম্বো অর্ডারে ডেলিভারি ফ্রি!", 50, (16, 185, 129)),
        ("💵 ক্যাশ অন ডেলিভারি (COD)", 440, (30, 41, 59)),
        ("⚡ ৭ দিনের রিটার্ন গ্যারান্টি", 745, (30, 41, 59))
    ]
    for text, bx, bg in badges:
        draw.rounded_rectangle([(bx, badge_y), (bx + 285, badge_y + 48)], radius=10, fill=bg, outline=(51, 65, 85))
        draw.text((bx + 18, badge_y + 11), text, fill=(255, 255, 255), font=font_badge)

    # Combo Name
    name = combo_product.get('name', 'এক্সক্লুসিভ বুক কম্বো প্যাকেজ')
    draw_wrapped_bengali_text(draw, name, 50, 810, W - 100, font_title, fill=(255, 255, 255), max_lines=2)

    # Footer
    draw.rounded_rectangle([(50, 935), (W - 50, 1025)], radius=16, fill=(16, 185, 129))
    draw.text((80, 960), "👉 এখনই কম্বো অর্ডার করুন: https://trustmart.bd/", fill=(255, 255, 255), font=font_cta)
    draw.text((W - 430, 960), "📞 WhatsApp অর্ডার: +8801756675724", fill=(255, 255, 255), font=font_cta)

    img.convert('RGB').save(output_path, 'JPEG', quality=95)
    print(f"✓ Combo poster saved: {output_path}")
    return output_path

def generate_ai_ad_copy(product):
    name = product.get('name') or product.get('Name')
    price = product.get('price') or product.get('Price')
    slug = product.get('slug') or product.get('Slug') or ''
    url = f"https://trustmart.bd/product/{slug}" if slug else "https://trustmart.bd/"

    prompt = f"""তুমি TrustMart (trustmart.bd) এর চিফ ডিজিটাল মার্কেটিং কপিরাইটার।
এই প্রোডাক্টের জন্য ফেসবুকে পোস্ট করার মতো একটি আকর্ষণীয়, সেলস-কনভার্টিং বাংলা ফেসবুক পোস্ট লেখো।

প্রোডাক্ট:
- নাম: {name}
- অফার মূল্য: ৳{price}
- লিঙ্ক: {url}
- ডেলিভারি: সারা দেশে ক্যাশ অন ডেলিভারি (পণ্য হাতে পেয়ে টাকা)
- বিশেষ সুবিধা: ৪টি বা ততোধিক বই অর্ডারে সারা দেশে ডেলিভারি সম্পূর্ণ ফ্রি!
- রিটার্ন: ৭ দিনের সহজ রিপ্লেসমেন্ট গ্যারান্টি।
- WhatsApp অর্ডার: +8801756675724

পোস্ট লেখার নিয়ম:
১. প্রথম লাইনে আকর্ষণীয় ইমোজিসহ হুক/হেডলাইন।
২. প্রোডাক্টের বৈশিষ্ট্য ও গুরুত্ব ৩-৪টি বুলেট পয়েন্টে।
৩. স্পষ্ট কল-টু-অ্যাকশন (CTA) সহ অর্ডার লিংক ও WhatsApp নম্বর।
৪. উপযুক্ত ফেসবুক হ্যাশট্যাগ (#TrustMart #CashOnDelivery #OnlineShopBD)।"""

    req_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash-lite:generateContent?key={GEMINI_API_KEY}"
    try:
        req = urllib.request.Request(
            req_url,
            data=json.dumps({"contents": [{"parts": [{"text": prompt}]}]}).encode('utf-8'),
            headers={'Content-Type': 'application/json'}
        )
        with urllib.request.urlopen(req, timeout=40) as response:
            res_data = json.loads(response.read().decode('utf-8'))
            return res_data['candidates'][0]['content']['parts'][0]['text']
    except Exception as e:
        print(f"Gemini copy gen error: {e}")
        return f"✨ আজকের স্পেশাল রিকমেন্ডেশন: {name} ✨\n\nদাম: মাত্র ৳{price}\nসারা বাংলাদেশে ক্যাশ অন ডেলিভারিতে হোম ডেলিভারি সুবিধা!\n👉 এখনই অর্ডার করুন: {url}\n📞 WhatsApp: +8801756675724\n\n#TrustMart #OnlineShopping"

def send_to_telegram(photo_path, caption):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram bot credentials not set.")
        return False
    try:
        # Build multipart form data for photo upload
        boundary = '----WebKitFormBoundary7MA4YWxkTrZu0gW'
        data = io.BytesIO()

        # chat_id
        data.write(f'--{boundary}\r\n'.encode('utf-8'))
        data.write(f'Content-Disposition: form-data; name="chat_id"\r\n\r\n{TELEGRAM_CHAT_ID}\r\n'.encode('utf-8'))

        # caption
        caption_trunc = caption[:1000] # Telegram caption max 1024
        data.write(f'--{boundary}\r\n'.encode('utf-8'))
        data.write(f'Content-Disposition: form-data; name="caption"\r\n\r\n{caption_trunc}\r\n'.encode('utf-8'))

        # photo file
        data.write(f'--{boundary}\r\n'.encode('utf-8'))
        data.write(f'Content-Disposition: form-data; name="photo"; filename="poster.jpg"\r\n'.encode('utf-8'))
        data.write(b'Content-Type: image/jpeg\r\n\r\n')
        with open(photo_path, 'rb') as f:
            data.write(f.read())
        data.write(b'\r\n')

        data.write(f'--{boundary}--\r\n'.encode('utf-8'))

        req_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
        req = urllib.request.Request(
            req_url,
            data=data.getvalue(),
            headers={'Content-Type': f'multipart/form-data; boundary={boundary}'}
        )
        with urllib.request.urlopen(req, timeout=20) as response:
            res = json.loads(response.read().decode('utf-8'))
            print("✓ Telegram send photo result:", res.get('ok'))
            return res.get('ok')
    except Exception as e:
        print(f"Telegram photo send error: {e}")
        return False

def post_to_facebook(photo_path, caption):
    token = os.environ.get('META_PAGE_ACCESS_TOKEN', META_PAGE_ACCESS_TOKEN)
    if not token:
        print("Facebook Meta Page Access Token not configured.")
        return {"success": False, "error": "টোকেন কনফিগার করা নেই। /fbtoken কমান্ড দিয়ে টোকেন সেট করুন।"}
    try:
        boundary = '----WebKitFormBoundaryFBPoster2026'
        data = io.BytesIO()

        # caption / message
        data.write(f'--{boundary}\r\n'.encode('utf-8'))
        data.write(b'Content-Disposition: form-data; name="caption"\r\n\r\n')
        data.write(caption.encode('utf-8'))
        data.write(b'\r\n')

        # access_token
        data.write(f'--{boundary}\r\n'.encode('utf-8'))
        data.write(b'Content-Disposition: form-data; name="access_token"\r\n\r\n')
        data.write(token.encode('utf-8'))
        data.write(b'\r\n')

        # photo binary
        data.write(f'--{boundary}\r\n'.encode('utf-8'))
        data.write(b'Content-Disposition: form-data; name="source"; filename="poster.jpg"\r\n')
        data.write(b'Content-Type: image/jpeg\r\n\r\n')
        with open(photo_path, 'rb') as f:
            data.write(f.read())
        data.write(b'\r\n')

        data.write(f'--{boundary}--\r\n'.encode('utf-8'))

        page_id = os.environ.get('META_PAGE_ID', META_PAGE_ID) or 'me'
        req_url = f"https://graph.facebook.com/v19.0/{page_id}/photos"
        req = urllib.request.Request(
            req_url,
            data=data.getvalue(),
            headers={'Content-Type': f'multipart/form-data; boundary={boundary}'}
        )
        with urllib.request.urlopen(req, timeout=30) as response:
            res = json.loads(response.read().decode('utf-8'))
            post_id = res.get('id') or res.get('post_id')
            print("✓ Facebook Page Photo Post SUCCESS! Post ID:", post_id)
            return {"success": True, "post_id": post_id, "url": f"https://facebook.com/{post_id}"}
    except Exception as e:
        err_msg = str(e)
        if hasattr(e, 'read'):
            try:
                err_json = json.loads(e.read().decode('utf-8'))
                err_msg = err_json.get('error', {}).get('message', str(e))
            except Exception:
                pass
        print(f"Facebook auto-post notice: {e} | Detail: {err_msg}")
        return {"success": False, "error": err_msg}

def run_daily_poster_campaign():
    if not os.path.exists(CATALOG_PATH):
        print(f"Catalog not found at {CATALOG_PATH}")
        return
    with open(CATALOG_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)
    products = data.get('products', [])
    valid_prods = [p for p in products if p.get('image') and p.get('image').startswith('http')]
    if not valid_prods:
        print("No products with valid images found.")
        return

    # Select product
    import random
    product = random.choice(valid_prods)
    print(f"Selected product: {product.get('name')} (Price: ৳{product.get('price')})")

    poster_path = os.path.join(ROOT_DIR, "trustmart_daily_poster.jpg")
    generate_poster(product, poster_path)

    print("Generating AI Sales Copy...")
    ad_copy = generate_ai_ad_copy(product)

    print("Sending poster & copy to Telegram (@trustmartbd_bot)...")
    tg_ok = send_to_telegram(poster_path, ad_copy)

    print("Attempting to post directly to Facebook Page (1299020649957056)...")
    fb_ok = post_to_facebook(poster_path, ad_copy)

    print("\n==========================================")
    print("CAMPAIGN COMPLETE!")
    print(f"Poster: {poster_path}")
    print(f"Telegram status: {'DELIVERED' if tg_ok else 'FAILED'}")
    print(f"Facebook status: {'PUBLISHED' if fb_ok else 'PENDING PERMISSION (pages_manage_posts)'}")
    print(f"Copy Preview:\n{ad_copy[:300]}...")
    print("==========================================")

if __name__ == '__main__':
    run_daily_poster_campaign()
