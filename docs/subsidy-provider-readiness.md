# CooTai — 政府補助「方案上架」Readyness Checklist

**Target:** 經濟部商業發展署「提升商業服務業營運效能強化韌性計畫」— 方案上架（成為合格服務提供者）
**Next window:** 第四梯 **2027-02-15 → 2027-03-10 17:00**（第五梯暫定 2027-05-17 → 06-04）
**Why it matters:** once listed, every client becomes eligible for **50% subsidy, max NT$100,000 per store**. That turns NT$15,000/month into NT$7,500/month in the client's mind — and the government validates the product.

> Verify everything against the live 申請須知 on https://www.smebiz.org.tw before submitting.
> Rules change between batches. This document records what was true as of 2026-10-28.

---

## 1. What the program actually requires (verified)

### On the buyer side (單店導入 — what your clients claim)

- 補助 **50% of the solution total**, capped at **NT$100,000 per store**, once per store
- Must subscribe **≥ 6 months**
- Must actually use it **3 months** before claiming
- Client pays first, claims later → to receive NT$100k, the solution must cost **NT$200,000**
- Client registers with their **統一編號** on the program system
- Client must sign a 受國際經貿局勢變動影響聲明書
- 受理期間：2026-04-20 → 2027-10-20 or until funds exhausted

### On the supplier side (方案上架 — what CooTai must do)

Submitted materials, **up to 10 separate solutions per application round**:

1. **智慧轉型方案申請書**（簡章附件6）
2. **智慧轉型方案技術特性說明書**（簡章附件7）
3. **智慧轉型方案推廣計畫書**（簡章附件8）— must contain:
   - 訓練推廣計畫：how you onboard and train the store
   - **店家資料自主權**：data portability / client can download their data
   - **技術服務層級 (SLA) 與能量說明**
4. **方案操作演示說明影片**：2–5 minutes, link submitted online
5. **服務提供者資格文件**（company registration etc.）

Review is **two-stage**: 資格審查 (document check, 3 working days to correct defects) then **會議審查** — you present in person.

---

## 2. Gap analysis — where CooTai stands

### ✅ Already have

| Requirement | Status |
|---|---|
| Working, demoable product | LINE agent @127bwuyu, text + Chinese voice |
| Real operating reference | 珊蒂美語 uses the same system daily |
| Privacy/data policy | `privacy.html` — 11 sections, data location, retention, DPO rights |
| Data retention implemented | 90-day auto-purge actually runs (`purge_old_inquiries`) |
| Measured performance | 4–5s warm voice latency; 24/7; rule replies instant |
| Demo hosting plan | Oracle free tier for demos; migration runbook written |
| Brand + materials | Logo, OG card, landing page, rich menu |

### ❌ Missing — blocking

| Gap | Why it blocks | Effort |
|---|---|---|
| **公司登記 + 稅籍登記 + 統一編號** | Hard eligibility requirement | 2–4 weeks via 記帳士 |
| ~~資料匯出功能~~ | **DONE 2026-10-28** — see §3.2(b) | — |
| **SLA 文件** | Explicitly required, with 能量說明 | ~1 day + hosting decision |
| **技術特性說明書** | Required document | ~1 day |
| **推廣/訓練計畫書** | Required document | ~1 day |
| **2–5 分鐘演示影片** | Required, with link | ~1 day to script + record |
| **SLA-grade hosting** | Can't promise uptime on a homelab desktop with no backups | tied to VPS decision |

### ⚠️ Weak spots to fix honestly

- **No backups on the current host.** An SLA commitment with no backup is a liability.
- **No formal 服務合約 template.** Clients need terms, and the program expects an SLA.
- **Single reference site.** One cram school is thin; acceptable but say so plainly.

---

## 3. The three documents — content outline

### 3.1 技術特性說明書 (technical spec)

Cover, factually:

- **Product**: AI 接待員 / AI 客服 for 商業服務業, delivered over LINE
- **Channels**: LINE 官方帳號 (Messaging API)
- **Languages**: 繁體中文 (text + voice input)
- **Input modes**: text; voice via Whisper ASR (Traditional Chinese)
- **Response logic**: rules-first (instant, deterministic, controlled wording) → LLM fallback for unscripted questions, grounded to a fixed company-facts set with anti-fabrication constraints
- **Capabilities**: 服務說明, 價格諮詢, 營業時間/地點, 預約諮詢, 情緒偵測與轉人工, 常見問答
- **Data location**: Taiwan (state the final host honestly once decided)
- **Retention**: 90 days, automatic purge
- **Security**: HTTPS/TLS, webhook HMAC-SHA256 signature verification, no directly exposed ports (tunnel-only ingress), dedicated service account
- **Performance**: measured text reply latency, measured voice latency, 24/7 availability
- **Limits**: what it does NOT do — no POS, no 健保, no 外送 platform integration, no medical advice

> Do not claim encryption-at-rest, ISO certification, or pen-test results unless they exist. The 2026-10 audit found no disk encryption — never write it again.

### 3.2 推廣計畫書 (deployment plan) — three mandatory components

**(a) 訓練推廣計畫 — how a store gets onboarded**

Proposed 4-step onboarding, ~2 weeks:

- Day 1 – 2｜需求盤點: collect business hours, pricing, services, FAQs, booking rules → populate `COMPANY_FACTS`
- Day 3 – 4｜建置: create LINE channel, deploy agent, set rich menu, configure tunnel
- Day 5｜測試: 20 test questions incl. edge cases; owner reviews exact wording
- Day 6 – 7｜訓練: 30-minute session with counter staff — what to do when the AI escalates; how to read inquiry notifications
- Week 2｜上線 + 觀察: monitor first-week inquiries, tune keywords

Ongoing: monthly review of unscripted questions → update `COMPANY_FACTS`.

**(b) 店家資料自主權 — data portability** ✅ **implemented 2026-10-28**

Live endpoint in `agent/webhook.py`:

- `GET /export?token=<EXPORT_TOKEN>` returns all conversation records as UTF-8 CSV
- Columns: 時間 / 使用者ID / 訊息內容 / 來源 / 回覆摘要
- Includes BOM so Excel opens Traditional Chinese without mojibake
- Correctly quotes multi-line replies and embedded commas
- `Cache-Control: no-store`, `Content-Disposition: attachment`

**Security:** disabled (403) unless `EXPORT_TOKEN` env var or an `export_token` key in
`credentials.json` is set. Token compared with `hmac.compare_digest`. Missing or wrong
token → 403; POST → 405.

Verified 2026-10-28: no-token→403, wrong-token→403, missing-token→403, correct-token→200
with correct headers and escaping. A seeded Chinese row with an embedded comma round-tripped intact.

Set the token per client at deploy time:
```bash
echo 'EXPORT_TOKEN=<random-40-chars>' >> /etc/systemd/system/cootai-agent@<slug>.service.d/export.conf
```
Documented in the contract: 「店家可隨時要求匯出全部對話紀錄，格式為 CSV，於 3 個工作天內提供」

**(c) SLA 與能量說明**

This is the one to think hardest about. Do not promise what a single box cannot deliver.

Realistic, defensible draft:

- **服務可用性**: 99% monthly (allows ~7h/month downtime). Achievable only on a VPS with monitoring — **not** on the current homelab desktop.
- **回應時間**: text p95 < 5s; voice p95 < 10s (measured 4–5s warm today, allow headroom)
- **服務時間**: 24/7 automated; human support 週一至週五 09:00–18:00
- **故障通報**: within 1 business hour of detection
- **資料保留**: 90 days, auto-purged; export on request within 3 business days
- **備份**: daily (must actually be implemented before signing)
- **能量說明**: current capacity, and how many concurrent clients per host

### 3.3 申請書 (application form)

Company identity, solution name, category, pricing structure, target industries, expected store count. Straightforward — but it must match the spec sheet exactly.

---

## 4. Demo video — 2–5 minute script

Constraint: 2–5 minutes. Show, don't narrate slides.

- **0:00–0:20｜問題**: 櫃檯在忙，家長訊息沒人回，晚上 10 點才看到
- **0:20–0:50｜導入**: 掃 QR code 加入 LINE，直接問「你們的收費怎麼算？」
- **0:50–1:40｜文字示範**: 價格 → 服務項目 → 營業時間 → 預約，全部秒回
- **1:40–2:20｜語音示範**: 按住麥克風說中文，顯示逐字稿與回答
- **2:20–2:50｜後台**: 業主收到 Telegram 通知，看到未回答問題
- **2:50–3:20｜資料自主權**: 匯出對話紀錄 CSV
- **3:20–3:50｜成果**: 24/7、秒回、4–5 秒語音回應

Record on a phone screen capture. No stock footage, no music bed needed — authenticity beats production value here.

---

## 5. Workback timeline to 2027-02-15

| By when | Milestone |
|---|---|
| **2026-11-30** | Decide hosting (AWS Taipei / Taiwan VPS); engage 記帳士 |
| **2026-12-15** | 公司設立送件 |
| **2026-12-31** | 公司登記 + 稅籍登記 complete; 統一編號 in hand |
| **2027-01-10** | 資料匯出功能 built + tested |
| **2027-01-15** | SLA 文件 drafted, hosting verified against it |
| **2027-01-20** | 技術特性說明書 done |
| **2027-01-25** | 推廣/訓練計畫書 done |
| **2027-01-31** | Demo video recorded |
| **2027-02-05** | All docs reviewed; 服務合約 template ready |
| **2027-02-15** | **第四梯 opens — submit** |
| **2027-03-10 17:00** | Hard deadline |

If 公司設立 slips past early January, you miss this window and wait until May.

---

## 6. Honest risks

1. **SLA vs. infrastructure.** Promising 99% uptime while running on a desktop in a spare room is a promise you cannot keep. Fix hosting first, or state a lower, truthful number.
2. **The 50% framing cuts both ways.** If a client expects NT$100k and the solution costs NT$15,000/month (NT$90,000 for 6 months), they get NT$45,000 — not NT$100,000. Be explicit about the math or you create disappointment.
3. **Funds can run out.** The program says 「經費用罄即停止」. Never promise a client they *will* get the subsidy — only that they're eligible.
4. **This is a 6-month subscription commitment.** It locks clients in, which is good, but refund/exit terms must be in the contract.
5. **The first review is a document check with 3 working days to fix defects.** Miss it and you're out of the batch. Submit a week early and keep a corrections folder ready.
6. **One reference customer is thin.** Your own cram school counts, but expect the 會議審查 panel to ask how you'll handle a client with no technical staff.

---

## 7. Immediate next actions

- [ ] Ask aiga.tw for their **方案編號** on smebiz.org.tw (tests whether the FB ad is substantive)
- [ ] Check **小型企業人力提升計畫** for 珊蒂美語 (open now, labor ministry, 就保50人以下)
- [ ] Decide hosting before writing the SLA
- [x] ~~Build the data export feature~~ — done 2026-10-28, `GET /export?token=`
- [ ] Book 記帳士 — ask about 借址 + 記帳 + 設立 as a bundle
