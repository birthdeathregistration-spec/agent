#!/usr/bin/env python3
"""
TrustMart.bd — Meta Facebook Token Exchange & Auto-Renew Helper
Exchanges any user access token for a Never-Expiring Page Access Token
using Meta App ID and App Secret.
"""

import os
import sys
import json
import urllib.request
import urllib.parse

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, '..', '..'))

META_APP_ID = os.environ.get('META_APP_ID', '1075000771919278')
META_APP_SECRET = os.environ.get('META_APP_SECRET', 'a444325748b9fb22bf93f0790122f6f4')
META_PAGE_ID = os.environ.get('META_PAGE_ID', '1299020649957056')

def exchange_user_token_for_permanent_page_token(short_token, app_id=META_APP_ID, app_secret=META_APP_SECRET, page_id=META_PAGE_ID):
    """
    1. Exchanges short-lived user token for 60-day Long-Lived User Token.
    2. Queries /me/accounts with that token.
    3. The Page Access Token returned from /me/accounts NEVER EXPIRES.
    """
    if not short_token:
        return {"success": False, "error": "No token provided"}

    # Step 1: Exchange for long-lived user token
    params = urllib.parse.urlencode({
        'grant_type': 'fb_exchange_token',
        'client_id': app_id,
        'client_secret': app_secret,
        'fb_exchange_token': short_token
    })
    url = f"https://graph.facebook.com/v19.0/oauth/access_token?{params}"
    
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'TrustMartAgent/2.0'})
        with urllib.request.urlopen(req, timeout=15) as r:
            res = json.loads(r.read().decode('utf-8'))
            long_user_token = res.get('access_token')
            if not long_user_token:
                return {"success": False, "error": "Could not obtain long-lived user token"}
    except Exception as e:
        err_detail = ""
        if hasattr(e, 'read'):
            try:
                err_detail = json.loads(e.read().decode('utf-8')).get('error', {}).get('message', '')
            except Exception:
                pass
        return {"success": False, "error": f"Step 1 exchange failed: {e} | {err_detail}"}

    # Step 2: Fetch permanent Page Access Token from /me/accounts
    url2 = f"https://graph.facebook.com/v19.0/me/accounts?access_token={long_user_token}"
    try:
        req2 = urllib.request.Request(url2, headers={'User-Agent': 'TrustMartAgent/2.0'})
        with urllib.request.urlopen(req2, timeout=15) as r:
            res2 = json.loads(r.read().decode('utf-8'))
            pages = res2.get('data', [])
            if not pages:
                return {"success": False, "error": "No pages found under this user account"}

            target_page = None
            for p in pages:
                if str(p.get('id')) == str(page_id):
                    target_page = p
                    break
            if not target_page:
                target_page = pages[0] # Fallback to first page

            page_token = target_page.get('access_token')
            page_name = target_page.get('name')
            p_id = target_page.get('id')

            # Verify permissions on this page token
            verify_url = f"https://graph.facebook.com/v19.0/{p_id}?fields=name,tasks&access_token={page_token}"
            req_v = urllib.request.Request(verify_url, headers={'User-Agent': 'TrustMartAgent/2.0'})
            tasks = []
            try:
                with urllib.request.urlopen(req_v, timeout=10) as rv:
                    v_data = json.loads(rv.read().decode('utf-8'))
                    tasks = v_data.get('tasks', [])
            except Exception:
                pass

            return {
                "success": True,
                "page_id": p_id,
                "page_name": page_name,
                "permanent_page_token": page_token,
                "tasks": tasks,
                "message": f"Successfully generated permanent Page Access Token for '{page_name}' (ID: {p_id})"
            }

    except Exception as e:
        err_detail = ""
        if hasattr(e, 'read'):
            try:
                err_detail = json.loads(e.read().decode('utf-8')).get('error', {}).get('message', '')
            except Exception:
                pass
        return {"success": False, "error": f"Step 2 page fetch failed: {e} | {err_detail}"}

def update_env_file(env_path, key, value):
    """Safely updates or adds a key in .env file"""
    if not os.path.exists(env_path):
        with open(env_path, 'w', encoding='utf-8') as f:
            f.write(f"{key}={value}\n")
        return

    lines = []
    found = False
    with open(env_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip().startswith(f"{key}=") or line.strip().startswith(f"{key} ="):
                lines.append(f"{key}={value}\n")
                found = True
            else:
                lines.append(line)
    if not found:
        lines.append(f"{key}={value}\n")

    with open(env_path, 'w', encoding='utf-8') as f:
        f.writelines(lines)

def apply_new_fb_token(token):
    """Exchanges and applies token across all .env files and current process"""
    res = exchange_user_token_for_permanent_page_token(token)
    if res.get('success'):
        perm_token = res.get('permanent_page_token')
        os.environ['META_PAGE_ACCESS_TOKEN'] = perm_token
        # Update root .env and hermes-agent .env if present
        for env_file in [
            os.path.join(ROOT_DIR, '.env'),
            os.path.join(ROOT_DIR, 'hermes-agent', '.env'),
            os.path.join(SCRIPT_DIR, '..', '..', '.env')
        ]:
            if os.path.exists(os.path.dirname(env_file)):
                try:
                    update_env_file(env_file, 'META_PAGE_ACCESS_TOKEN', perm_token)
                except Exception:
                    pass
    return res

if __name__ == '__main__':
    if len(sys.argv) > 1:
        tok = sys.argv[1].strip()
        print(f"Exchanging token: {tok[:15]}...")
        r = apply_new_fb_token(tok)
        print(json.dumps(r, indent=2))
    else:
        print("Usage: python fb_token_helper.py <short_or_long_user_token>")
