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

## Voice messages (Chinese) — added 2026-10-20
- LINE voice messages (`message.type == "audio"`) are downloaded via the content API,
  converted to 16k mono WAV (ffmpeg), and transcribed with **faster-whisper `small` int8**
  (Chinese `zh`, beam 5, VAD on). Model cached in `agent/models/` (gitignored).
- The reply echoes what was heard, then answers by intent.
- Verified: Chinese sample transcribed correctly, language prob 1.0.
- Model preloads at startup (~1.5s) so the first voice message isn't slow.
- Measured: ~4–5s per voice message warm, CPU only.

## Reply pipeline (2026-10-21)
1. **Rule engine first** — exact keyword match, instant (0.000s), 8 intents:
   greet / price / location / hours / booking / emotion / services / about.
   Keyword order matters: `emotion` is checked before `services` so 「服務很差」
   stays an apology rather than an offering.
2. **LLM fallback** — on no rule match, call DeepSeek via OpenRouter
   (`deepseek/deepseek-v4.1-flash-1017`), ~0.7–1.8s.
   Prompt is grounded in `COMPANY_FACTS` and forbids invention; on unknown topics
   it routes to 「請專人為您確認」 without leaking words like 「公司資料」.
3. **Safe fallback** — if the LLM errors (no key, 401, timeout), send CATCH_ALL.
   Never crashes, never blocks a reply.
- Per-user conversation memory: last 4 messages in-process (`_HISTORY`).
  Not persisted across restarts — fine for now, SQLite if it needs to survive.
- Replies truncated to 1500 chars (LINE's hard limit is 5000).

## LINE app surface (2026-10-21)
- **Profile photo**: `brand/line_profile.png` (plus mark + COOTAI, square 640px).
  Line profile photos cannot be set via API — uploaded manually in Manager → 帳號資訊.
- **Rich menu**: `CooTai Main Menu`, id `richmenu-50de382eee6534d198073f365aabba53`,
  2500x843, 3 buttons, set as **default for all users**.
  Buttons send text that hits the rule engine:
  - 服務內容 → 「服務包含什麼?」 → services
  - 價格方案 → 「你們的價格怎麼算」 → price
  - 預約諮詢 → 「我想預約諮詢」 → booking
  Regenerate with `brand/gen_line_assets.py`; recreate + re-upload via the
  rich menu API, then `POST /v2/bot/user/all/richmenu/{id}`.

## Owner notifications (2026-10-21)
- `notify_owner()` pushes to Telegram (`COOTAI_NOTIFY_CHAT`, default 8345157605).
- Fires ONLY on genuine inquiries: `src == "llm"` (unscripted question) and
  `rule:booking`. Deliberately silent on greetings/pricing to avoid noise.
- Every message is appended to `agent/inquiries.jsonl` (gitignored) for review.
- **Growth loop**: new request → AI defers → owner alerted → owner decides →
  if we offer it, add to `COMPANY_FACTS` and the AI starts selling it.
  That log becomes the product roadmap, driven by real demand.

## Adding company knowledge
Edit `COMPANY_FACTS` in `webhook.py` — that is the single source of truth the LLM
is allowed to speak from. Add services/prices/FAQ there before promising anything
to a client.

## Service management (24/7)
systemd **user** units (no sudo; `loginctl` Linger=yes so they start at boot without login):
- `cootai-agent.service` — runs `webhook.py` on :8080, Restart=always
- `cootai-tunnel.service` — runs the named cloudflared tunnel, Restart=always
Commands: `systemctl --user status|restart cootai-agent cootai-tunnel`

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