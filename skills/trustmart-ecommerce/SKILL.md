---
name: trustmart-ecommerce
description: Autonomous E-Commerce Operations, SEO Optimization, Facebook Posting, and Order Management for TrustMart.bd
---

# TrustMart E-Commerce Autonomous Skill

This skill empowers Hermes Agent to operate as the Chief AI Operations & SEO Manager for TrustMart (https://trustmart.bd).

## Capabilities

1. **Product SEO Optimizer**:
   - Fetches product data from `https://trustmart.bd/catalog_seo.json`
   - Analyzes product names, categories, and descriptions
   - Produces high-ranking Bengali SEO Titles, 160-character Meta Descriptions, and Rich Snippet Schema
   - Target keyword formats: `[বইয়ের নাম] - আসল প্রিন্ট ও দ্রুত ক্যাশ অন ডেলিভারি | TrustMart`

2. **Facebook Social Publisher**:
   - Crafts high-converting sales copies with emotional hooks, key selling points, emojis, and WhatsApp order links
   - Dispatches posts via Facebook Graph API to the official TrustMart Facebook Page

3. **Courier & Order Fulfillment**:
   - Queries pending orders awaiting Steadfast / Pathao courier dispatch
   - Verifies Cash on Delivery (COD) phone numbers and customer details

4. **Daily Executive Store Audit**:
   - Summarizes daily gross sales, pending deliveries, and low stock items (Stock <= 5)
   - Delivers automated morning digests via Telegram

## Configuration

Hermes Agent connects to TrustMart using:
- `GEMINI_API_KEY`: Google Gemini API Key for generation
- `TELEGRAM_BOT_TOKEN`: Telegram bot token for executive alerts
- `TRUSTMART_API_BASE`: `https://trustmart.bd`
