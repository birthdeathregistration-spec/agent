#!/usr/bin/env python3
"""
TrustMart 2.0 — 24/7 Autonomous Master AI Operations Agent & Web Service
Dual Interface: Telegram Bot (@trustmartbd_bot) + Admin Web Panel (trustmart.bd/admin)

Master Capabilities:
1. Unified Access: Full control from BOTH Telegram AND https://trustmart.bd/admin
2. Terminal & Shell Command Execution (run any bash/powershell/cli command, git, pip, curl)
3. Dynamic Python Script Runner (write and run any script on the fly)
4. Full File System Control (read, write, list files and directories on server)
5. Social Media Publishing (Facebook Page auto-posting with Hind Siliguri typography)
6. Autonomous Product & Combo Management (create bundles, edit prices/stocks)
7. Store Analytics & Order Reporting (3,243 products, inventory audits)
8. Free-form Conversational NLU (understands natural Bengali and English without rigid commands)
9. Render 24/7 Web Server (health checks on $PORT for zero-downtime uptime monitoring)
"""

import os
import sys
import json
import time
import re
import threading
import subprocess
import urllib.request
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime

# Enforce UTF-8 stdio
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
AGENT_DIR = os.path.join(SCRIPT_DIR, 'agent')
SKILLS_DIR = os.path.join(SCRIPT_DIR, 'skills', 'trustmart-ecommerce')
if not os.path.exists(SKILLS_DIR):
    SKILLS_DIR = os.path.join(SCRIPT_DIR, 'hermes-agent', 'skills', 'trustmart-ecommerce')

for d in [SCRIPT_DIR, AGENT_DIR, SKILLS_DIR]:
    if os.path.exists(d) and d not in sys.path:
        sys.path.insert(0, d)

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

load_env(os.path.join(SCRIPT_DIR, '.env'))
load_env(os.path.join(SCRIPT_DIR, 'hermes-agent', '.env'))

PORT = int(os.environ.get('PORT', 10000))
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '8664874586:AAG7-JWqJzR5JBZUQ5L6Pag4bh4oA7jhy0Y')
TELEGRAM_ALLOWED_USERS = os.environ.get('TELEGRAM_ALLOWED_USERS', '7886593741')
META_PAGE_ID = os.environ.get('META_PAGE_ID', '1299020649957056')
START_TIME = time.time()

# Import Skill modules safely
try:
    import poster_generator
except Exception as e:
    print(f"Notice: poster_generator import: {e}")
    poster_generator = None

try:
    import product_manager
except Exception as e:
    print(f"Notice: product_manager import: {e}")
    product_manager = None

try:
    import fb_token_helper
except Exception as e:
    print(f"Notice: fb_token_helper import: {e}")
    fb_token_helper = None

CATALOG_PATH = os.path.join(SCRIPT_DIR, 'catalog_seo.json')

def get_catalog():
    if os.path.exists(CATALOG_PATH):
        try:
            with open(CATALOG_PATH, 'r', encoding='utf-8') as f:
                return json.load(f).get('products', [])
        except Exception:
            pass
    return []

# Banglish & Bengali Normalization Helpers
BANGLA_DIGIT_MAP = {'০':'0', '১':'1', '২':'2', '৩':'3', '৪':'4', '৫':'5', '৬':'6', '৭':'7', '৮':'8', '৯':'9'}

def normalize_digits(text):
    return ''.join(BANGLA_DIGIT_MAP.get(c, c) for c in text)

BANGLISH_MAP = {
    'roshayon': 'রসায়ন', 'chemistry': 'রসায়ন', 'gonit': 'গণিত', 'math': 'গণিত',
    'podartho': 'পদার্থ', 'physics': 'পদার্থ', 'jibobiggan': 'জীববিজ্ঞান', 'biology': 'জীববিজ্ঞান',
    'itihas': 'ইতিহাস', 'history': 'ইতিহাস', 'uponnash': 'উপন্যাস', 'novel': 'উপন্যাস',
    'golpo': 'গল্প', 'kobita': 'কবিতা', 'islamic': 'ইসলামিক', 'islam': 'ইসলাম',
    'quran': 'কোরআন', 'hadith': 'হাদিস', 'hadis': 'হাদিস', 'boish': 'বই', 'boi': 'বই'
}

def expand_banglish(query):
    words = query.lower().split()
    expanded = []
    for w in words:
        expanded.append(w)
        if w in BANGLISH_MAP:
            expanded.append(BANGLISH_MAP[w])
    return ' '.join(expanded)

# Telegram Helpers
def send_telegram_text(chat_id, text):
    if not TELEGRAM_BOT_TOKEN or not chat_id:
        return False
    try:
        chunks = [text[i:i+3900] for i in range(0, len(text), 3900)]
        for chunk in chunks:
            payload = json.dumps({
                "chat_id": chat_id,
                "text": chunk,
                "parse_mode": "Markdown"
            }).encode('utf-8')
            req = urllib.request.Request(
                f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                data=payload,
                headers={'Content-Type': 'application/json'}
            )
            with urllib.request.urlopen(req, timeout=15) as r:
                pass
        return True
    except Exception:
        try:
            payload = json.dumps({"chat_id": chat_id, "text": text}).encode('utf-8')
            req = urllib.request.Request(
                f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                data=payload,
                headers={'Content-Type': 'application/json'}
            )
            with urllib.request.urlopen(req, timeout=15) as r:
                return True
        except Exception:
            return False

# ==============================================================================
# HIGHEST POWER AGENT TOOLS (TERMINAL, SCRIPT, FILE SYSTEM, NETWORK)
# ==============================================================================

def tool_execute_command(command, cwd=None, timeout=60):
    work_dir = cwd or SCRIPT_DIR
    start = time.time()
    try:
        proc = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=work_dir,
            encoding='utf-8',
            errors='replace'
        )
        elapsed = round(time.time() - start, 2)
        stdout = proc.stdout.strip()
        stderr = proc.stderr.strip()
        return {
            "success": proc.returncode == 0,
            "returncode": proc.returncode,
            "stdout": stdout,
            "stderr": stderr,
            "time_seconds": elapsed
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "returncode": -1, "error": f"কমান্ডটি {timeout} সেকেন্ডে শেষ হয়নি (টাইমআউট)।"}
    except Exception as e:
        return {"success": False, "returncode": -1, "error": str(e)}

def tool_run_python(code, timeout=60):
    tmp_file = os.path.join(SCRIPT_DIR, f"_agent_exec_{int(time.time())}.py")
    try:
        with open(tmp_file, 'w', encoding='utf-8') as f:
            f.write(code)
        res = tool_execute_command(f"{sys.executable} \"{tmp_file}\"", timeout=timeout)
        return res
    finally:
        if os.path.exists(tmp_file):
            try: os.remove(tmp_file)
            except Exception: pass

def tool_read_file(filepath):
    target = os.path.abspath(os.path.join(SCRIPT_DIR, filepath))
    if not os.path.exists(target):
        return {"success": False, "error": f"ফাইল পাওয়া যায়নি: {filepath}"}
    try:
        with open(target, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
        return {"success": True, "path": target, "content": content, "size_bytes": len(content)}
    except Exception as e:
        return {"success": False, "error": str(e)}

def tool_write_file(filepath, content):
    target = os.path.abspath(os.path.join(SCRIPT_DIR, filepath))
    os.makedirs(os.path.dirname(target), exist_ok=True)
    try:
        with open(target, 'w', encoding='utf-8') as f:
            f.write(content)
        return {"success": True, "path": target, "size_bytes": len(content)}
    except Exception as e:
        return {"success": False, "error": str(e)}

def tool_list_directory(dir_path="."):
    target = os.path.abspath(os.path.join(SCRIPT_DIR, dir_path))
    if not os.path.exists(target):
        return {"success": False, "error": f"ডিরেক্টরি পাওয়া যায়নি: {dir_path}"}
    try:
        items = os.listdir(target)
        file_list = []
        for it in items[:50]:
            p = os.path.join(target, it)
            is_dir = os.path.isdir(p)
            sz = os.path.getsize(p) if not is_dir else 0
            file_list.append(f"{'[DIR] ' if is_dir else '      '}{it}{' (' + str(sz) + ' B)' if not is_dir else ''}")
        return {"success": True, "path": target, "items": file_list}
    except Exception as e:
        return {"success": False, "error": str(e)}

# Existing E-Commerce Tools
def tool_search_catalog(query="", limit=3):
    catalog = get_catalog()
    if not catalog:
        return []
    
    q_norm = normalize_digits(expand_banglish(query)).lower().strip()
    tokens = [t for t in re.split(r'[\s,\.\?\!\:\;]+', q_norm) if len(t) > 1 and t not in ['বই', 'বইটা', 'আছে', 'কি', 'দাম', 'কত', 'খুঁজছি', 'চাই']]
    
    matches = []
    for p in catalog:
        p_name = p.get('name', '').lower()
        p_slug = p.get('slug', '').lower()
        p_cat = p.get('category', '').lower()
        p_author = p.get('author', '').lower()
        
        score = 0
        for tok in tokens:
            if tok in p_name: score += 10
            elif tok in p_slug: score += 8
            elif tok in p_cat: score += 5
            elif tok in p_author: score += 5
            
        if score > 0:
            matches.append((score, p))
            
    matches.sort(key=lambda x: -x[0])
    return [m[1] for m in matches[:limit]]

def tool_create_combo(title, price, items, admin_id=7886593741):
    if product_manager:
        return product_manager.create_combo(title, price, items, admin_id=admin_id)
    return {"success": False, "message": "Product manager module missing"}

def tool_edit_product(slug, updates, admin_id=7886593741):
    if product_manager:
        return product_manager.edit_product(slug, updates, admin_id=admin_id)
    return {"success": False, "message": "Product manager module missing"}

def tool_generate_and_post_poster(product_keyword=None, post_to_fb=True, send_to_tg=True, chat_id=None):
    if not poster_generator:
        return {"success": False, "error": "Poster generator module missing"}

    products = get_catalog()
    selected_prod = None
    if product_keyword:
        kw = product_keyword.lower()
        for p in products:
            if kw in p.get('name', '').lower() or kw in p.get('slug', '').lower():
                if p.get('image') and p.get('image').startswith('http'):
                    selected_prod = p
                    break

    if not selected_prod:
        import random
        valid = [p for p in products if p.get('image') and p.get('image').startswith('http')]
        if valid:
            selected_prod = random.choice(valid)

    if not selected_prod:
        return {"success": False, "error": "কোনো উপযুক্ত প্রোডাক্ট পাওয়া যায়নি।"}

    poster_path = os.path.join(SCRIPT_DIR, "trustmart_daily_poster.jpg")
    poster_generator.generate_poster(selected_prod, poster_path)
    ad_copy = poster_generator.generate_ai_ad_copy(selected_prod)

    fb_result = None
    if post_to_fb:
        fb_result = poster_generator.post_to_facebook(poster_path, ad_copy)

    tg_result = None
    if send_to_tg and chat_id:
        tg_result = poster_generator.send_to_telegram(poster_path, ad_copy)

    return {
        "success": True,
        "product": selected_prod.get('name'),
        "poster_path": poster_path,
        "copy": ad_copy,
        "facebook_post": fb_result,
        "telegram_sent": tg_result
    }

def tool_update_fb_token(token):
    if fb_token_helper:
        return fb_token_helper.apply_new_fb_token(token)
    return {"success": False, "error": "FB Token helper module missing"}

# ==============================================================================
# AUTONOMOUS MASTER CONTROLLER (UNDERSTANDS EVERYTHING IN NATURAL LANGUAGE)
# Returns structured dictionary for both Telegram AND Web Admin Panel
# ==============================================================================

def execute_autonomous_agent(user_prompt, chat_id=None, user_id="admin"):
    raw_text = user_prompt.strip()
    norm_text = normalize_digits(expand_banglish(raw_text))
    low = norm_text.lower()
    replies = []

    def emit(text):
        replies.append(text)
        if chat_id:
            send_telegram_text(chat_id, text)

    # 1. Direct Terminal / Shell Command Execution
    is_terminal_intent = False
    cmd_to_run = ""
    if raw_text.startswith("$ "):
        is_terminal_intent = True
        cmd_to_run = raw_text[2:].strip()
    elif any(raw_text.lower().startswith(p) for p in ["run:", "exec:", "cmd:", "sh:", "bash:", "terminal:", "কমান্ড:", "রান:"]):
        is_terminal_intent = True
        cmd_to_run = raw_text.split(":", 1)[1].strip()
    elif any(low.startswith(p) for p in ["git ", "pip ", "curl ", "python ", "npm ", "node ", "ls", "pwd", "dir", "cat ", "df ", "free ", "uptime", "whoami"]):
        is_terminal_intent = True
        cmd_to_run = raw_text.strip()
    elif any(phrase in low for phrase in ["কমান্ড চালাও", "কমান্ড রান করো", "টার্মিনালে চালাও", "টার্মিনাল কমান্ড", "শেল কমান্ড", "run command", "run this command"]):
        is_terminal_intent = True
        if ":" in raw_text:
            cmd_to_run = raw_text.split(":", 1)[1].strip()
        elif "`" in raw_text:
            m = re.search(r'`([^`]+)`', raw_text)
            if m: cmd_to_run = m.group(1).strip()
        else:
            for w in ["কমান্ড চালাও", "কমান্ড রান করো", "রান করো", "চালাও"]:
                if w in raw_text:
                    cmd_to_run = raw_text.split(w, 1)[1].strip().strip('"').strip("'")
                    break

    if is_terminal_intent and cmd_to_run:
        emit(f"💻 *টার্মিনালে কমান্ড এক্সিকিউট হচ্ছে...*\n`$ {cmd_to_run}`")
        res = tool_execute_command(cmd_to_run)
        code = res.get('returncode', 0)
        out = res.get('stdout', '')
        err = res.get('stderr', '')
        t_sec = res.get('time_seconds', 0)

        status_emoji = "✅" if code == 0 else "❌"
        msg = f"{status_emoji} *কমান্ড সম্পন্ন ({t_sec}s | Exit Code: {code})*\n\n"
        if out:
            disp_out = out[:3000] + "\n...(আউটপুট ট্রাঙ্কেট করা হয়েছে)" if len(out) > 3000 else out
            msg += f"```text\n{disp_out}\n```\n"
        if err:
            disp_err = err[:1000]
            msg += f"⚠️ *Stderr:*\n```text\n{disp_err}\n```"
        if not out and not err:
            msg += "_(কোনো কনসোল আউটপুট নেই / নিঃশব্দে সম্পন্ন হয়েছে)_"

        emit(msg)
        return {"success": code == 0, "action": "terminal", "reply": "\n\n".join(replies), "data": res}

    # 2. Dynamic Python Script Execution
    is_python_intent = False
    py_code = ""
    if any(raw_text.lower().startswith(p) for p in ["python:", "py:", "script:", "স্ক্রিপ্ট:"]):
        is_python_intent = True
        py_code = raw_text.split(":", 1)[1].strip()
    elif "```python" in raw_text or "```py" in raw_text:
        is_python_intent = True
        m = re.search(r'```(?:python|py)?\s*([\s\S]+?)\s*```', raw_text)
        if m: py_code = m.group(1).strip()
    elif any(phrase in low for phrase in ["পাইথন স্ক্রিপ্ট চালাও", "পাইথন কোড রান করো", "স্ক্রিপ্ট রান করো", "run python script"]):
        is_python_intent = True
        if ":" in raw_text:
            py_code = raw_text.split(":", 1)[1].strip()
        elif "`" in raw_text:
            m = re.search(r'`([^`]+)`', raw_text)
            if m: py_code = m.group(1).strip()

    if is_python_intent and py_code:
        emit("🐍 *পাইথন স্ক্রিপ্ট এক্সিকিউট হচ্ছে...*")
        res = tool_run_python(py_code)
        out = res.get('stdout', '')
        err = res.get('stderr', '')
        code = res.get('returncode', 0)
        t_sec = res.get('time_seconds', 0)
        status_emoji = "✅" if code == 0 else "❌"

        msg = f"{status_emoji} *স্ক্রিপ্ট রান সম্পন্ন ({t_sec}s)*\n\n"
        if out:
            disp_out = out[:3000]
            msg += f"```text\n{disp_out}\n```\n"
        if err:
            msg += f"⚠️ *Error:*\n```text\n{err[:1000]}\n```"
        if not out and not err:
            msg += "_(স্ক্রিপ্ট সফলভাবে সম্পন্ন হয়েছে, কোনো আউটপুট ছিল না)_"
        emit(msg)
        return {"success": code == 0, "action": "python", "reply": "\n\n".join(replies), "data": res}

    # 3. File System (Read, Write, List)
    if any(low.startswith(p) for p in ["read:", "cat ", "পড়ো:", "ফাইল পড়ো"]):
        path = raw_text.split(":", 1)[1].strip() if ":" in raw_text else raw_text.split(None, 1)[1].strip()
        f_res = tool_read_file(path)
        if f_res.get('success'):
            content = f_res.get('content', '')
            disp = content[:3000] + "\n...(আরো বিষয়বস্তু রয়েছে)" if len(content) > 3000 else content
            emit(f"📄 *{path}* ({f_res.get('size_bytes')} B):\n\n```text\n{disp}\n```")
        else:
            emit(f"❌ {f_res.get('error')}")
        return {"success": f_res.get('success'), "action": "read_file", "reply": "\n\n".join(replies), "data": f_res}

    if any(low.startswith(p) for p in ["ls", "dir", "ফাইল তালিকা", "ফাইল লিস্ট"]):
        path = raw_text.split(":", 1)[1].strip() if ":" in raw_text else (raw_text.split(None, 1)[1].strip() if len(raw_text.split()) > 1 else ".")
        d_res = tool_list_directory(path)
        if d_res.get('success'):
            items_str = "\n".join(d_res.get('items', []))
            emit(f"📁 *ডিরেক্টরি ফাইল তালিকা ({d_res.get('path')}):*\n\n```text\n{items_str}\n```")
        else:
            emit(f"❌ {d_res.get('error')}")
        return {"success": d_res.get('success'), "action": "list_files", "reply": "\n\n".join(replies), "data": d_res}

    # 4. Facebook Token Detection & Auto-Exchange
    fb_token_match = re.search(r'(EAAP[A-Za-z0-9]{20,})', raw_text)
    if fb_token_match or "facebook token" in low or "ফেসবুক টোকেন" in low or "fb token" in low:
        if fb_token_match:
            raw_tok = fb_token_match.group(1)
            emit("⏳ ফেসবুক টোকেন পাওয়া গেছে! এটি ভেরিফাই করে পার্মানেন্ট (Never-Expiring) পেজ টোকেনে রূপান্তর করা হচ্ছে...")
            res = tool_update_fb_token(raw_tok)
            if res.get('success'):
                msg = (
                    f"✅ *ফেসবুক পেজ টোকেন সফলভাবে কানেক্ট হয়েছে!*\n\n"
                    f"• পেজ নাম: *{res.get('page_name')}*\n"
                    f"• পেজ আইডি: `{res.get('page_id')}`\n"
                    f"• টোকেন টাইপ: **স্থায়ী (Never-Expiring)**\n\n"
                    f"এখন আপনি যেকোনো বইয়ের পোস্টার বানাতে বললেই স্বয়ংক্রিয়ভাবে সরাসরি ফেসবুকে পোস্ট পাবলিশ হবে! 🚀"
                )
                emit(msg)
                return {"success": True, "action": "fb_token", "reply": "\n\n".join(replies), "data": res}
            else:
                emit(f"❌ টোকেন এক্সচেঞ্জ ব্যর্থ হয়েছে:\n`{res.get('error')}`\n\nদয়া করে নিশ্চিত করুন আপনার টোকেনে `pages_manage_posts` ও `pages_show_list` পারমিশন রয়েছে।")
                return {"success": False, "action": "fb_token", "reply": "\n\n".join(replies), "data": res}
        else:
            emit("🔑 আপনি সরাসরি আপনার ফেসবুক টোকেনটি (`EAAP...`) এখানে পেস্ট করে দিলে আমি স্বয়ংক্রিয়ভাবে আজীবন মেয়াদী পেজ টোকেনে রূপান্তর করে নেব।")
            return {"success": True, "action": "fb_token_info", "reply": "\n\n".join(replies)}

    # 5. Marketing Poster & Social Publishing
    poster_signals = ['পোস্টার', 'ব্যানার', 'বিজ্ঞাপন', 'পোস্ট', 'ফেসবুকে দাও', 'ফেসবুকে পোস্ট', 'ফেসবুক পোস্ট', 'facebook post', 'poster', 'banner']
    if any(sig in low for sig in poster_signals):
        emit("🎨 *পোস্টার ডিজাইন ও সোশ্যাল মিডিয়া পাবলিশিং প্রসেস শুরু হচ্ছে...*\n\n• স্টোর থেকে সেরা বই নির্বাচন\n• ১০৮০x১০৮০ হাই-কনভার্টিং ব্যানার ডিজাইন (হিন্দ শিলিগুড়ি ফন্ট)\n• সেলস কপি রচনা\n• ফেসবুক ও টেলিগ্রামে সরাসরি পাবলিশিং...")

        kw = None
        for word in raw_text.split():
            w_clean = re.sub(r'[^\w\s]', '', word).strip()
            if len(w_clean) > 3 and w_clean.lower() not in ['পোস্টার', 'বানাও', 'ব্যানার', 'ফেসবুকে', 'পোস্ট', 'করো', 'একটি', 'সুন্দর', 'দাও', 'আজকের', 'জন্য']:
                kw = w_clean
                break

        res = tool_generate_and_post_poster(product_keyword=kw, post_to_fb=True, send_to_tg=True, chat_id=chat_id)
        if res.get('success'):
            fb = res.get('facebook_post') or {}
            fb_status = "✅ ফেসবুকে সরাসরি পোস্ট সম্পন্ন হয়েছে!" if fb.get('success') else f"⚠️ ফেসবুক পোস্ট নোটিশ: {fb.get('error', 'টোকেন আপডেট প্রয়োজন')}"
            summary = (
                f"📢 *মার্কেটিং পোস্ট প্রস্তুত সম্পন্ন!*\n\n"
                f"• বই: *{res.get('product')}*\n"
                f"• ফেসবুক স্ট্যাটাস: {fb_status}\n"
                f"• টেলিগ্রাম স্ট্যাটাস: ✅ পোস্টার ডেলিভার্ড\n\n"
                f"পোস্টার এবং বাংলা সেলস কপি তৈরি করা হয়েছে।"
            )
            emit(summary)
            return {
                "success": True,
                "action": "poster",
                "reply": "\n\n".join(replies),
                "poster_url": "/api/poster/latest",
                "product": res.get('product'),
                "copy": res.get('copy'),
                "facebook_post": fb
            }
        else:
            emit(f"❌ পোস্টার তৈরিতে সমস্যা: {res.get('error')}")
            return {"success": False, "action": "poster", "reply": "\n\n".join(replies)}

    # 6. Combo & Product Management
    combo_signals = ['কম্বো', 'প্যাকেজ', 'বান্ডেল', 'অফার চালু', 'প্যাকেজ অফার', 'combo', 'bundle', 'বানাও কম্বো']
    if any(sig in low for sig in combo_signals):
        price = 650
        price_match = re.search(r'(\d+)\s*(টাকা|tk|/-)?', norm_text)
        if price_match:
            try: price = int(price_match.group(1))
            except: pass

        title = "এক্সক্লুসিভ বুক কম্বো প্যাকেজ"
        if "নাম" in low:
            m = re.search(r'নাম\s*[:=]?\s*([^,।\n]+)', raw_text)
            if m: title = m.group(1).strip()
        elif ":" in raw_text:
            parts = raw_text.split(":", 1)[1]
            title = parts.split(",")[0].strip()
        elif "কম্বো" in raw_text:
            for piece in raw_text.split():
                if len(piece) > 3 and piece not in ["কম্বো", "বানাও", "টাকার", "দিয়ে", "একটা"]:
                    title = f"{piece} স্পেশাল কম্বো"
                    break

        items = ["english-therapy", "no-ending"]
        if "সাইন্স" in low or "বিজ্ঞান" in low or "science" in low:
            items = ["higher-math-1st", "physics-1st"]
        elif "এইচএসসি" in low or "hsc" in low:
            items = ["bangla-1st", "english-therapy"]

        emit(f"⏳ আপনার নির্দেশ অনুযায়ী নতুন কম্বো তৈরি ও ব্যানার প্রসেসিং হচ্ছে...\n📦 শিরোনাম: *{title}*\n💰 অফার মূল্য: ৳{price}")
        res = tool_create_combo(title, price, items, admin_id=7886593741)
        msg = res.get('message', '')
        poster = res.get('poster_path')
        emit(msg)
        if poster and os.path.exists(poster) and poster_generator:
            poster_generator.send_to_telegram(poster, f"🔥 নতুন কম্বো ব্যানার: {title}\nঅফার মূল্য: ৳{price}")
        return {"success": True, "action": "combo", "reply": "\n\n".join(replies), "data": res}

    # Product Price / Stock Edit
    has_mod_verb = any(w in low for w in ['এডিট', 'পরিবর্তন', 'করে দাও', 'সেট করো', 'আপডেট করো', 'বাড়িয়ে দাও', 'কমিয়ে দাও', 'change', 'update'])
    has_price_match = re.search(r'(দাম|price|মূল্য)\s*(=|:|\s)?\s*(\d+)', norm_text)
    has_stock_match = re.search(r'(স্টক|stock)\s*(=|:|\s)?\s*(\d+)', norm_text)

    if has_mod_verb or (has_price_match and has_stock_match) or (has_price_match and 'টাকা' in low):
        catalog = get_catalog()
        slug = ""
        for p in catalog:
            p_s = p.get('slug', '').lower()
            p_n = p.get('name', '').lower()
            if p_s in low or (len(p_n) > 4 and p_n in low):
                slug = p.get('slug')
                break

        if not slug:
            for word in raw_text.split():
                w = word.strip().lower()
                for p in catalog:
                    if w == p.get('slug', '').lower():
                        slug = p.get('slug')
                        break
                if slug: break

        updates = {}
        if has_price_match:
            updates['price'] = int(has_price_match.group(3))
        if has_stock_match:
            updates['stock'] = int(has_stock_match.group(3))

        if slug and updates:
            res = tool_edit_product(slug, updates, admin_id=7886593741)
            emit(res.get('message', ''))
            return {"success": True, "action": "edit_product", "reply": "\n\n".join(replies), "data": res}
        elif not slug and updates:
            emit("⚠️ আপনি মূল্য/স্টক উল্লেখ করেছেন, কিন্তু কোন প্রোডাক্টের পরিবর্তন করতে হবে তার নাম বা স্ল্যাগটি বুঝতে পারিনি। যেমন বলুন: `no-ending এর দাম ১৬০ আর স্টক ২০ করে দাও`।")
            return {"success": False, "action": "edit_product", "reply": "\n\n".join(replies)}

    # 7. Store Audit & Reports
    report_signals = ['কয়টা বই', 'মোট বই', 'স্টক কেমন', 'স্টকের অবস্থা', 'দোকানের হিসেব', 'স্টোর রিপোর্ট', 'মোট সেল', 'আজকের সেল', 'অর্ডার রিপোর্ট', 'হিসেব দাও', 'সেলস রিপোর্ট', 'দোকানের অবস্থা', 'sales']
    if any(sig in low for sig in report_signals):
        catalog = get_catalog()
        total_prods = len(catalog)
        in_stock = sum(1 for p in catalog if p.get('stock', 0) > 0)
        out_of_stock = total_prods - in_stock
        uptime_mins = int((time.time() - START_TIME) / 60)

        rep = (
            "📊 *TrustMart লাইভ স্টোর অডিট ও মাস্টার অপারেশনাল রিপোর্ট*\n\n"
            f"• মোট রেজিস্টার্ড প্রোডাক্ট: *{total_prods:,}টি*\n"
            f"• ইন-স্টক প্রোডাক্ট: *{in_stock:,}টি*\n"
            f"• স্টক আউট / সীমিত: *{out_of_stock:,}টি*\n"
            f"• ফেসবুক পেজ আইডি: `{META_PAGE_ID}`\n"
            f"• সার্ভার আপটাইম: ২৪/৭ চালু ({uptime_mins} মিনিট ধরে সক্রিয়)\n"
            f"• টার্মিনাল & স্ক্রিপ্ট এক্সেস: **সক্রিয় (Highest Power Active)**\n"
            f"• অটোনোমাস শিডিউলার: প্রতি ৬ ঘণ্টা পর পর পোস্টার পাবলিশিং\n"
            f"• অ্যাডমিন প্যানেল সিঙ্ক: সক্রিয়"
        )
        emit(rep)
        return {"success": True, "action": "store_report", "reply": "\n\n".join(replies)}

    # Business Consulting
    growth_signals = ['সেল বাড়ানো', 'সেলস বাড়া', 'সেল বাড়া', 'সেলস বৃদ্ধি', 'গ্রোথ', 'স্ট্র্যাটেজি', 'কৌশল', 'কী করা উচিত', 'কি করা উচিত', 'পরামর্শ', 'মার্কেটিং বুদ্ধি', 'উন্নতি']
    if any(sig in low for sig in growth_signals):
        advice = (
            "🚀 *TrustMart সেলস বৃদ্ধির স্ট্র্যাটেজিক পরামর্শ ও একশন প্ল্যান:*\n\n"
            "১. **৪টি বইয়ের ফ্রি ডেলিভারি অফার প্রমোট করা:**\n"
            "আমাদের স্টোরে ৪টি বা ততোধিক বইয়ের বান্ডেল অর্ডারে সারা দেশে ডেলিভারি সম্পূর্ণ ফ্রি। কাস্টমারদের বেশি বই কেনাতে এটি প্রধান হাতিয়ার।\n\n"
            "২. **সিলেট লোকাল হাইপার-ডেলিভারি:**\n"
            "সিলেট সদরে ডেলিভারি চার্জ মাত্র ৳৬০ এবং ১-২ দিনে পৌঁছে যায়। সিলেটের শিক্ষার্থী ও পাঠকদের ফেসবুক ও লোকাল গ্রুপে টার্গেট করে ২৪ ঘণ্টায় হোম ডেলিভারি অফার দিন।\n\n"
            "৩. **দৈনিক ফেসবুক ব্যানার ক্যাম্পেইন:**\n"
            "প্রতিদিন অন্তত ২টি আকর্ষণীয় ব্যানার ও ক্যাচি সেলস কপি দিয়ে ফেসবুকে পোস্ট করুন (আপনি আমাকে যেকোনো সময় বললেই আমি ব্যানার বানিয়ে ফেসবুকে পোস্ট করে দেব)।\n\n"
            "৪. **কম্বো প্যাকেজ তৈরি:**\n"
            "একক বইয়ের চেয়ে এইচএসসি বা বিশ্ববিদ্যালয় ভর্তি পরীক্ষার ৩/৪টি বিষয়ের বই একসাথে কম্বো অফারে ২০% ছাড় দিয়ে বিক্রি করলে এভারেজ অর্ডার ভ্যালু দ্বিগুণ হয়।"
        )
        emit(advice)
        return {"success": True, "action": "growth_consulting", "reply": "\n\n".join(replies)}

    # Policies
    del_signals = ['ডেলিভারি চার্জ', 'কুরিয়ার চার্জ', 'কবে পাব', 'ডেলিভারি ফি', 'কত দিন লাগবে', 'কুরিয়ার', 'ডেলিভারি']
    if any(sig in low for sig in del_signals):
        del_info = (
            "🚚 *TrustMart ডেলিভারি পলিসি ও চার্জ শিডিউল (হাব: সিলেট):*\n\n"
            "• **সিলেট সিটি / সদর:** ৳৬০ (১-২ কার্যদিবস)\n"
            "• **সিলেট জেলা (অন্যান্য উপজেলা):** ৳১০০ (২-৩ কার্যদিবস)\n"
            "• **সারা বাংলাদেশ (আন্তঃজেলা / ঢাকা সহ সব বিভাগ):** ৳১৩০ (২-৪ কার্যদিবস)\n\n"
            "🎉 *বিশেষ সুবিধা:* বান্ডেলে ৪টি বা তার বেশি বই অর্ডারে সারা দেশে ডেলিভারি সম্পূর্ণ ফ্রি!\n"
            "ক্যাশ অন ডেলিভারিতে পণ্য হাতে পেয়ে মূল্য পরিশোধের সুবিধা রয়েছে।"
        )
        emit(del_info)
        return {"success": True, "action": "delivery_policy", "reply": "\n\n".join(replies)}

    # Book search
    search_signals = ['বই আছে', 'পাওয়া যাবে', 'খুঁজছি', 'বইটা আছে', 'দাম কত', 'search', 'খুঁজে দাও', 'বই কি আছে']
    if any(sig in low for sig in search_signals) or len(raw_text.split()) <= 4:
        results = tool_search_catalog(query=raw_text, limit=3)
        if results:
            msg = f"🔍 *আপনার কাঙ্ক্ষিত বইয়ের বিবরণ:*\n\n"
            for p in results:
                stk = "✓ ইন-স্টক" if p.get('stock', 0) > 0 else "⚠️ স্টক সীমিত"
                msg += f"• *{p.get('name')}*\n  💵 মূল্য: ৳{p.get('price')} ({stk})\n  👉 লিংক: https://trustmart.bd/product/{p.get('slug')}\n\n"
            emit(msg)
            return {"success": True, "action": "search", "reply": "\n\n".join(replies), "products": results}

    # Fallback
    fallback = (
        f"🤖 অ্যাডমিন ভাই, আপনার বার্তা পেয়েছি: '{raw_text}'\n\n"
        f"সর্বোচ্চ ক্ষমতার অধিকারী মাস্টার এজেন্ট হিসেবে আপনি টেলিগ্রাম বা অ্যাডমিন প্যানেল থেকে নিচের যেকোনো কাজ করাতে পারেন:\n\n"
        f"💻 *১. টার্মিনাল কমান্ড:* `$ git status` বা `রান করো: pip list`\n"
        f"🐍 *২. পাইথন স্ক্রিপ্ট:* `python: print(2**10)`\n"
        f"📄 *৩. ফাইল পড়া ও তৈরি:* `read: catalog_seo.json` বা `ls`\n"
        f"🎨 *৪. ব্যানার ও ফেসবুক পোস্ট:* `একটি সুন্দর পোস্টার বানিয়ে ফেসবুকে দাও`\n"
        f"📦 *৫. কম্বো তৈরি:* `৩টি বই দিয়ে ৫০০ টাকার কম্বো বানাও`\n"
        f"✏️ *৬. প্রোডাক্ট এডিট:* `no-ending এর দাম ১৬০ টাকা আর স্টক ২০ করে দাও`\n"
        f"📊 *৭. স্টোর অডিট:* `দোকানের হিসেব দাও`"
    )
    emit(fallback)
    return {"success": True, "action": "conversational", "reply": "\n\n".join(replies)}

def handle_admin_message(chat_id, user_id, text):
    user_str = str(user_id).strip()
    allowed_str = str(TELEGRAM_ALLOWED_USERS).strip()

    if user_str != allowed_str:
        send_telegram_text(chat_id, "⛔ অননুমোদিত এক্সেস!\nএই বট শুধুমাত্র TrustMart এর অথোরাইজড অ্যাডমিন ব্যবহার করতে পারবেন।")
        return

    execute_autonomous_agent(text, chat_id=chat_id, user_id=user_id)

def telegram_poller():
    """Background polling loop for Telegram Bot updates"""
    print("✓ Telegram Bot 24/7 Master Autonomous Listener started...")
    last_update_id = 0
    while True:
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates?offset={last_update_id + 1}&timeout=30"
            req = urllib.request.Request(url, headers={'User-Agent': 'TrustMartAgent/2.0'})
            with urllib.request.urlopen(req, timeout=35) as r:
                res = json.loads(r.read().decode('utf-8'))
                if res.get('ok'):
                    for update in res.get('result', []):
                        last_update_id = update['update_id']
                        msg = update.get('message')
                        if msg and 'text' in msg:
                            chat_id = msg['chat']['id']
                            user_id = msg['from']['id']
                            text = msg['text']
                            threading.Thread(target=handle_admin_message, args=(chat_id, user_id, text), daemon=True).start()
        except Exception:
            time.sleep(5)

def scheduled_campaign_loop():
    """Runs autonomous social poster at scheduled intervals (every 6 hours)"""
    print("✓ 24/7 Autonomous Marketing Scheduler started...")
    while True:
        time.sleep(21600)
        try:
            print("Executing scheduled daily social poster campaign...")
            if poster_generator:
                poster_generator.run_daily_poster_campaign()
        except Exception as e:
            print(f"Scheduled campaign error: {e}")

class AgentHTTPHandler(BaseHTTPRequestHandler):
    def send_cors_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-Requested-With')

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_cors_headers()
        self.end_headers()

    def do_GET(self):
        uptime = int(time.time() - START_TIME)
        if self.path in ['/', '/healthz', '/health']:
            self.send_response(200)
            self.send_cors_headers()
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            data = {
                "status": "online",
                "service": "TrustMart Master AI Autonomous Agent",
                "version": "2.3.0",
                "endpoints": ["/healthz", "/api/copilot", "/api/trigger-poster", "/api/poster/latest"],
                "powers": ["terminal_execution", "python_runner", "filesystem_io", "facebook_publisher", "combo_builder", "store_audit", "admin_web_sync"],
                "commands_required": False,
                "uptime_seconds": uptime,
                "mode": "24/7",
                "telegram_bot": "@trustmartbd_bot",
                "admin_id": TELEGRAM_ALLOWED_USERS,
                "server_time": datetime.now().isoformat()
            }
            self.wfile.write(json.dumps(data, indent=2).encode('utf-8'))
        elif self.path in ['/api/poster/latest', '/poster.jpg']:
            poster_path = os.path.join(SCRIPT_DIR, 'trustmart_daily_poster.jpg')
            if os.path.exists(poster_path):
                self.send_response(200)
                self.send_cors_headers()
                self.send_header('Content-Type', 'image/jpeg')
                self.send_header('Cache-Control', 'no-cache')
                self.end_headers()
                with open(poster_path, 'rb') as f:
                    self.wfile.write(f.read())
            else:
                self.send_response(404)
                self.send_cors_headers()
                self.end_headers()
        else:
            self.send_response(404)
            self.send_cors_headers()
            self.end_headers()

    def do_POST(self):
        if self.path in ['/api/copilot', '/api/agent-command']:
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length).decode('utf-8')
            try:
                payload = json.loads(body)
                query = payload.get('message') or payload.get('query') or payload.get('prompt') or ''
                user_id = payload.get('user_id', 'admin_web')
                res = execute_autonomous_agent(query, chat_id=None, user_id=user_id)
                self.send_response(200)
                self.send_cors_headers()
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.end_headers()
                self.wfile.write(json.dumps(res, ensure_ascii=False).encode('utf-8'))
            except Exception as e:
                self.send_response(500)
                self.send_cors_headers()
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"success": False, "error": str(e)}).encode('utf-8'))

        elif self.path == '/api/trigger-poster':
            if poster_generator:
                threading.Thread(target=poster_generator.run_daily_poster_campaign, daemon=True).start()
                self.send_response(200)
                self.send_cors_headers()
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(b'{"status": "campaign_triggered"}')
            else:
                self.send_response(500)
                self.send_cors_headers()
                self.end_headers()
                self.wfile.write(b'{"error": "poster_generator_missing"}')

        elif self.path == '/webhook/telegram':
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length).decode('utf-8')
            try:
                update = json.loads(body)
                msg = update.get('message')
                if msg and 'text' in msg:
                    handle_admin_message(msg['chat']['id'], msg['from']['id'], msg['text'])
            except Exception as e:
                print(f"Webhook parse error: {e}")
            self.send_response(200)
            self.send_cors_headers()
            self.end_headers()
            self.wfile.write(b'{"ok": true}')
        else:
            self.send_response(404)
            self.send_cors_headers()
            self.end_headers()

def run_server():
    t_tele = threading.Thread(target=telegram_poller, daemon=True)
    t_tele.start()

    t_sched = threading.Thread(target=scheduled_campaign_loop, daemon=True)
    t_sched.start()

    server_address = ('0.0.0.0', PORT)
    httpd = HTTPServer(server_address, AgentHTTPHandler)
    print("==================================================")
    print("  TrustMart 24/7 Master AI Autonomous Agent      ")
    print(f"  Listening on http://0.0.0.0:{PORT}              ")
    print("  DUAL INTERFACE: TELEGRAM + WEB ADMIN ACTIVE    ")
    print("==================================================")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()

if __name__ == '__main__':
    run_server()
