# CooTai AI Agent — Project State

Last updated: 2026-10-18

## Live systems
- **cootai.tw** — landing page on GitHub Pages (repo `jchopenclawhu-web/cootai`, branch `main`)
- **LINE Official Account** @127bwuyu — auto-replies via Messaging API
- **Webhook** — `agent/webhook.py` (Python, wsgiref), rule-based auto-replies

## LINE Messaging API
- Channel ID: `2012071190`
- Bot user ID: `U00db8719faeaa0924827359997bf9214`
- Credentials live in `agent/credentials.json` — **NEVER commit** (secret; .gitignore'd)
- Webhook URL: quick Cloudflare tunnel (temporary — see below)

## Agent behavior (rule-based)
| Trigger | Reply |
|---------|-------|
| 你好/hi/hello | Greeting |
| 價格/多少錢/方案 | Pricing tiers (NT$15K/25K/40K) |
| 地址/哪裡 | Location (Linkou) |
| 營業時間 | Business hours |
| 預約 | Booking flow |
| complaint words | Empathetic response |
| anything else | Friendly catch-all |

## Known next steps (TODO)
1. **Make webhook permanent**: current URL is a `trycloudflare.com` quick tunnel (changes on restart).
   → Set up a **named Cloudflare tunnel** with stable custom domain (e.g. `bot.cootai.tw`).
2. **Customize reply wording**: real hours/address/service tiers once finalized.
3. (Optional) Swap rule-based → **LLM-generated replies** for natural conversation.
4. (Optional) **Booking logic** — forward bookings via email/notification.
5. (Optional) Privacy Policy + Terms pages at cootai.tw for LINE provider compliance.

## Deployment notes
- Run agent: `cd agent && python webhook.py  (PORT=8080 default)`
- Expose: `cloudflared tunnel --url http://localhost:8080`
- Tunnel creds: account-less quick tunnel; for production use named tunnel.