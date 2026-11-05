"""Authentication and narrow store proxies for the standalone TrustMart service."""

import hmac
import json
import os
import urllib.request


def store_request(payload, timeout=20):
    url = os.environ.get('SCRIPT_URL', '').strip()
    if not url.startswith('https://script.google.com/macros/s/') or not url.endswith('/exec'):
        raise ValueError('SCRIPT_URL must be the deployed Google Apps Script HTTPS URL')
    request = urllib.request.Request(
        url, data=json.dumps(payload).encode('utf-8'),
        headers={'Content-Type': 'application/json'}, method='POST',
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        data = json.loads(response.read().decode('utf-8'))
    if not isinstance(data, dict):
        raise ValueError('Invalid store response')
    return data


def bearer_token(headers):
    authorization = headers.get('Authorization', '')
    return authorization[7:].strip() if authorization.lower().startswith('bearer ') else ''


def matches_secret(received, expected):
    return bool(isinstance(received, str) and expected and
                hmac.compare_digest(received.encode('utf-8'), expected.encode('utf-8')))


def is_admin_request(headers, payload):
    supplied = headers.get('x-admin-key') or headers.get('X-Admin-Key') or bearer_token(headers)
    supplied = supplied or payload.get('admin_key') or payload.get('token') or payload.get('admin_token')
    for key in ('ADMIN_SECRET', 'ADMIN_KEY'):
        if matches_secret(supplied, os.environ.get(key, '')):
            return True
    if not isinstance(supplied, str) or not supplied:
        return False
    try:
        result = store_request({'action': 'getProfile', 'token': supplied}, timeout=10)
    except (OSError, ValueError):
        return False
    user = result.get('user') or {}
    role = str(user.get('role') or result.get('role') or '').lower()
    status = str(user.get('status') or '').lower()
    return result.get('success') is True and role == 'admin' and status == 'active'


def telegram_webhook_authorized(headers):
    return matches_secret(headers.get('X-Telegram-Bot-Api-Secret-Token', ''),
                          os.environ.get('TELEGRAM_WEBHOOK_SECRET', ''))


def proxy_store_action(path, payload, headers):
    routes = {
        '/api/payments/verify': ('verifyPayment', None, None),
        '/api/payments/webhook': ('paymentWebhook', 'SMS_WEBHOOK_SECRET', 'X-Webhook-Secret'),
        '/api/courier/steadfast-webhook': ('steadfastWebhook', 'STEADFAST_WEBHOOK_TOKEN', 'X-Signature'),
    }
    if path not in routes:
        return 404, {'success': False, 'message': 'Not found'}
    action, secret_name, secret_header = routes[path]
    body = dict(payload)
    body['action'] = action
    if secret_name:
        expected = os.environ.get(secret_name, '')
        if not expected:
            return 503, {'success': False, 'message': 'Webhook authentication is not configured'}
        supplied = bearer_token(headers) or headers.get(secret_header, '')
        if not matches_secret(supplied, expected):
            return 401, {'success': False, 'message': 'Unauthorized webhook'}
        body['secret'] = expected
        body['token'] = expected
    try:
        result = store_request(body)
    except (OSError, ValueError):
        return 502, {'success': False, 'message': 'Store service unavailable; retry the request'}
    if result.get('success') is not True:
        code = result.get('statusCode', 400)
        status = code if isinstance(code, int) and 400 <= code <= 599 else 400
        return status, result
    return 200, result


def redact_response(value):
    """Keep raw tool data subject to the same credential policy as display text."""
    if isinstance(value, dict):
        return {key: ('[REDACTED]' if any(term in key.lower() for term in
                ('password', 'secret', 'api_key', 'access_token', 'credential')) else redact_response(item))
                for key, item in value.items()}
    if isinstance(value, list):
        return [redact_response(item) for item in value]
    if isinstance(value, str):
        for name, secret in os.environ.items():
            if len(secret) >= 8 and any(term in name.upper() for term in
                    ('TOKEN', 'SECRET', 'PASSWORD', 'API_KEY', 'ACCESS_KEY')):
                value = value.replace(secret, '[REDACTED]')
    return value
