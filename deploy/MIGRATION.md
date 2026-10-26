# CooTai — Deployment & Migration Runbook

How to run demo agents and move them to production VPS without touching the
client's LINE configuration.

---

## The core idea: keep the hostname, move the machine

Every agent is fronted by a **Cloudflare tunnel** on a stable hostname, e.g.

```
clinic-abc.cootai.tw  ->  tunnel  ->  http://localhost:8080 on whatever host
```

The client's LINE webhook URL is `https://clinic-abc.cootai.tw`.

**Because the hostname never changes, migration = repointing DNS.** LINE never
learns the agent moved. No re-verification, no webhook edit, no downtime window
the client can notice.

This is the whole reason to use a tunnel instead of an IP or a host-provided
domain. Do not put the agent on `123.45.67.89:8080` or
`vps123.hostinger.com`.

---

## Part 1 — Demo environment (Oracle Always Free)

Good fit for demos: costs nothing, and if Oracle reclaims an idle instance the
demo simply goes dark (acceptable for a prospect who hasn't paid).

**Naming:** give each prospect their own subdomain from day one.

```
demo-clinic-abc.cootai.tw     (Oracle, ARM)
demo-dental-xyz.cootai.tw     (Oracle, ARM)
```

**Rules for the demo host:**

- **Synthetic data only.** Never put a real prospect's customer data on the
  Oracle box — Oracle has **no Taiwan region**, so this would break the
  privacy policy's "主機在台灣" claim. Demo data must be fake.
- Convert the Oracle account to **Pay-As-You-Go** if you want it to survive —
  free-tier instances idle below 20% (CPU/network/memory over 7 days) get
  **stopped/reclaimed**. PAYG keeps Always Free limits free but is not reclaimed.
- 2 OCPU / 12 GB ARM, 200 GB storage, 10 TB egress. Plenty for one demo agent.
- Budget alert in OCI Billing → set at NT$0-ish threshold so you never get billed.
- ARM64: `faster-whisper` works but whisper wheels differ. Expect a slower first
  voice message.

---

## Part 2 — Production environment

**Hard requirement from our own privacy policy:** the agent host must be in
**Taiwan** (we published: 「主機位於台灣，由我們自行管理，不租用境外雲端主機」).

⚠️ **Hostinger has no Taiwan datacenter.** Their locations include Singapore,
Malaysia, and Europe/US. Hosting clients there would make the privacy page false.

### Taiwan-region options

| Option | Region | Approx cost | Notes |
|---|---|---|---|
| **AWS ap-east-2 (Taipei)** | Taipei, 3 AZs | pay-as-you-go, ~US$8–15 for t3.small | Real Taiwan region, launched 2025 |
| **GCP asia-east1** | Changhua, Taiwan | ~US$13–25 for e2-small | Real Taiwan region, mature |
| **hicloud (中華電信)** | Taiwan | quote-based | SLA 99.95%, ISO 27001/27701, 資料落地台灣 |
| **台灣本地 VPS**（戰國策／捕夢網／遠振／ServerZoo） | Taiwan | NT$600–2,400/mo | Cheapest Taiwan option; quality varies by provider |

### Practical recommendation

- **Cheapest path that keeps the privacy promise:** a Taiwan local VPS,
  ~NT$1,200–1,800/mo for 2 cores / 4 GB / 50–100 GB. Verify they offer
  **root SSH + Ubuntu** and that the box is genuinely in a Taiwan IDC.
- **If you want managed reliability + a real hyperscaler region:** AWS Taipei or
  GCP asia-east1. More setup, stronger SLAs.
- **If you decide Taiwan residency doesn't matter for a particular client:**
  Hostinger Singapore is ~NT$480/mo and fine — **but you must update the
  privacy policy first**, and say so honestly.

**Do not skip this decision.** It's the difference between your clinic pitch
being true or being a liability.

---

## Part 3 — Migration procedure (demo → production)

**Downtime: a single DNS flip. Realistically 1–5 minutes. LINE never notices.**

### 0. Pre-flight (before you touch anything)

```bash
# On the demo host — record what you need to carry over
cat /srv/cootai/clients/<slug>/agent/credentials.json   # LINE tokens (same channel)
cat /srv/cootai/clients/<slug>/agent/.richmenu_id       # if a rich menu exists
wc -l /srv/cootai/clients/<slug>/agent/inquiries.jsonl  # conversation history
```

Decide: **keep the same LINE channel** (recommended — the client's @ID and
friends list stay intact) or issue a new one. Same channel = only the webhook
URL matters, and that stays identical.

### 1. Provision the new host

```bash
# On the NEW VPS, as root
cd /opt
git clone https://github.com/jchopenclawhu-web/cootai.git
cd cootai/deploy
./provision-client.sh <slug> <channel-access-token> <channel-secret>
```

This installs python/ffmpeg/cloudflared, creates a venv with faster-whisper,
writes per-client credentials, allocates a port, and starts
`cootai-agent@<slug>`.

Add the LLM key:
```bash
echo 'OPENROUTER_API_KEY=sk-or-v1-...' > /etc/cootai/llm.env
chmod 600 /etc/cootai/llm.env
systemctl restart cootai-agent@<slug>
```

### 2. Create the tunnel on the new host

```bash
cloudflared tunnel login                       # once per host
cloudflared tunnel create <slug>
```

Write `/root/.cloudflared/config.yml`:

```yaml
tunnel: <NEW-TUNNEL-ID>
credentials-file: /root/.cloudflared/<NEW-TUNNEL-ID>.json

ingress:
  - hostname: <slug>.cootai.tw
    service: http://localhost:<PORT>
  - service: http_status:404
```

Run it under systemd:

```bash
cloudflared service install
systemctl enable --now cloudflared
systemctl status cloudflared --no-pager
```

**Do NOT run `cloudflared tunnel route dns` yet** — that would flip DNS
immediately, before you've verified anything.

### 3. Verify the new host BEFORE the switch

From the new host:

```bash
curl -s -o /dev/null -w '%{http_code}\n' -H 'User-Agent: Mozilla/5.0' http://127.0.0.1:<PORT>/
# expect 405 (Method Not Allowed) = server is up and rejecting GET

systemctl is-active cootai-agent@<slug>
journalctl -u cootai-agent@<slug> -n 20 --no-pager | grep -i whisper
# expect: "Whisper model ready in Xs"
```

Test the tunnel path works by temporarily pointing a **throwaway** hostname at
it (`cloudflared tunnel route dns <slug> test-<slug>.cootai.tw`) and hitting
that. Only once that returns 405 do you proceed.

### 4. Copy the data

```bash
# From the demo host
rsync -avz /srv/cootai/clients/<slug>/agent/inquiries.jsonl \
           /srv/cootai/clients/<slug>/agent/.richmenu_id \
           root@<new-vps-ip>:/srv/cootai/clients/<slug>/agent/

# If the client already has a rich menu, keep it
```

### 5. The switch — one DNS change

```bash
cloudflared tunnel route dns <slug> <slug>.cootai.tw
```

Then immediately confirm:

```bash
curl -s -o /dev/null -w '%{http_code}\n' -H 'User-Agent: Mozilla/5.0' https://<slug>.cootai.tw/
# expect 405
```

If it returns 530/502, DNS hasn't propagated or the new tunnel is down — the old
host is still up, so **you can revert by pointing DNS back**. This reversibility
is the point.

### 6. Confirm with a real LINE message

Send a message to the client's LINE account. Check it landed on the **new** host:

```bash
journalctl -u cootai-agent@<slug> -n 20 --no-pager | grep -E 'TEXT|AUDIO'
```

### 7. Decommission the demo

```bash
# On the demo host
systemctl disable --now cootai-agent@<slug>
cloudflared tunnel delete <old-tunnel-id>   # if dedicated
```

Then in Oracle, terminate the instance so it stops counting against the free
allowance (and can't be reclaimed mid-demo).

---

## Part 4 — Rollback

Because DNS is the only switch:

```bash
# Repoint back to the old tunnel
cloudflared tunnel route dns <old-tunnel> <slug>.cootai.tw
```

Keep the demo host **running and provisioned for 7 days** after migration. Costs
nothing and buys you a clean rollback.

---

## Part 5 — Checklist (print this)

Before cutover:
- [ ] Privacy policy host location matches the NEW host's country
- [ ] New agent returns **405** on localhost
- [ ] Whisper warm-up logged
- [ ] Tunnel test hostname returns 405
- [ ] `credentials.json` on new host (chmod 600)
- [ ] `OPENROUTER_API_KEY` in `/etc/cootai/llm.env`
- [ ] `inquiries.jsonl` copied
- [ ] Swap file created (KVM 1/2 boxes)
- [ ] Weekly backup enabled on the VPS provider

After cutover:
- [ ] `https://<slug>.cootai.tw` returns 405
- [ ] Real LINE message hits the new host's journal
- [ ] Old host kept alive 7 days
- [ ] Demo instance terminated

---

## Anti-patterns — do not do these

1. **Don't use the VPS provider's own hostname/subdomain.** You'd be stuck with
   them forever.
2. **Don't change the LINE channel unless forced.** A new channel = the client
   loses their @ID, friends, and chat history.
3. **Don't run two agents on the same webhook URL.** LINE will deliver to one;
   you get split-brain replies.
4. **Don't migrate without a swap file on small VPSes.** Whisper + 2 GB RAM
   without swap = OOM kill mid-conversation.
5. **Don't put real customer data on a non-Taiwan host** while the privacy page
   promises Taiwan.
