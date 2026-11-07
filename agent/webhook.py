#!/usr/bin/env python3
"""CooTai LINE auto-reply agent webhook (text + Chinese voice messages)."""
import base64
import csv
import hashlib
import hmac
import io
import json
import os
import subprocess
import tempfile
import time
import urllib.request
import urllib.parse
import urllib.error
import wave
from collections import OrderedDict
from urllib.parse import parse_qs

import numpy as np

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CREDS = json.load(open(os.path.join(BASE_DIR, "credentials.json"), encoding="utf-8"))
CHANNEL_SECRET = CREDS["channel_secret"]
ACCESS_TOKEN = CREDS["channel_access_token"]
API = "https://api.line.me/v2/bot/message/reply"
CONTENT_API = "https://api-data.line.me/v2/bot/message/{}/content"
FFMPEG = os.environ.get("FFMPEG_BIN",
    "/home/educator/.hermes/tools/ffmpeg-9.0.1-linux-x64/bin/ffmpeg")
MODEL_DIR = os.path.join(BASE_DIR, "models")

# ---- LLM fallback (OpenRouter / DeepSeek) ----
LLM_URL = "https://openrouter.ai/api/v1/chat/completions"
LLM_MODEL = os.environ.get("LLM_MODEL", "deepseek/deepseek-v4.1-flash-1017")

# Only facts we actually know. The model must never invent beyond this.
COMPANY_FACTS = """\
補習班名稱：仁僾文理語文短期補習班
地址：244 新北市林口區湖南里仁愛路二段630號
電話：(02) 2608-5425
立案字號：北府教社字第1013076096號（政府立案、安檢合格）
國小部課程：全科數學、康軒英語、美語、作文
國中部課程：數學、英文、理化、全科班
說明：
- 學費依年級與科目不同，未公開價目。若家長詢問學費，請說明需依年級與科目
  由老師說明，並邀請來電 (02) 2608-5425 或到班了解。絕對不要報出任何金額。
- 各班上課時間不同，未提供課表。若詢問上課時間，請轉由老師確認。
- 師資、榜單、教材版本等細節未提供，一律不猜測、不編造，轉真人回覆。
"""

SYSTEM_PROMPT = (
    "你是「仁僾文理語文短期補習班」的 LINE 客服助理，對象是家長與學生。\n"
    "你代表補習班對外說話，家長不知道你有「資料」這回事。\n\n"
    "【最重要規則】\n"
    "1. 只能根據下方【公司資料】回答。\n"
    "2. 若資料中沒有答案（例如政府補助、折扣、特定合約條件、客戶案例、\n"
    "   尚未提供的功能），絕對不可以猜測、承諾或編造。\n"
    "3. 遇到這種情況，請用自然的說法帶過，例如：\n"
    "   「這部分我需要請專人為您確認」或「詳細內容我請同事跟您說明」，\n"
    "   然後邀請對方留下聯絡方式或預約。\n"
    "4. 【絕對不要】說出「公司資料」「資料中沒有」「根據我的資料」等字眼，\n"
    "   也不要提到你是 AI 或語言模型。\n\n"
    "【語氣】\n"
    "- 一律使用繁體中文（台灣用語）。\n"
    "- 親切、專業、簡短。每次回覆最多 3 句話或 80 字。\n"
    "- 不要使用 Markdown 語法（LINE 不支援）。\n"
    "- 結尾可自然地引導下一步（詢問需求、邀請預約或留聯絡方式）。\n\n"
    "【公司資料】\n" + COMPANY_FACTS
)

_llm_key = None


def get_llm_key():
    """Read the OpenRouter key once from env or ~/.hermes/.env."""
    global _llm_key
    if _llm_key is not None:
        return _llm_key
    _llm_key = os.environ.get("OPENROUTER_API_KEY", "")
    if not _llm_key:
        for p in (os.path.expanduser("~/.hermes/.env"), os.path.expanduser("~/.env")):
            try:
                with open(p, encoding="utf-8") as f:
                    for line in f:
                        if line.startswith("OPENROUTER_API_KEY="):
                            _llm_key = line.split("=", 1)[1].strip().strip('"').strip("'")
                            break
            except OSError:
                continue
            if _llm_key:
                break
    return _llm_key


def notify_owner(text, user_id=None, kind="inquiry"):
    """Push a Telegram alert to the owner when something needs attention."""
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat = os.environ.get("COOTAI_NOTIFY_CHAT", "8345157605")
    if not token:
        for p in (os.path.expanduser("~/.hermes/.env"),):
            try:
                with open(p, encoding="utf-8") as f:
                    for line in f:
                        if line.startswith("TELEGRAM_BOT_TOKEN="):
                            token = line.split("=", 1)[1].strip().strip('"').strip("'")
                            break
            except OSError:
                pass
    if not token:
        log("notify: no TELEGRAM_BOT_TOKEN, skipping")
        return
    emoji = {"inquiry": "💬", "unanswered": "❓", "booking": "📅"}.get(kind, "💬")
    body = f"{emoji} CooTai LINE 新訊息 ({kind})\n\n{text}"
    if user_id:
        body += f"\n\nuserId: {user_id}"
    payload = json.dumps({"chat_id": chat, "text": body[:3500]}).encode()
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=payload, headers={"Content-Type": "application/json"}, method="POST")
    try:
        urllib.request.urlopen(req, timeout=15).read()
        log(f"notify: sent {kind} to owner")
    except Exception as e:
        log(f"notify error: {e!r}")


def log_inquiry(user_id, text, src, reply):
    """Append every conversation to a JSONL log for review / feature requests."""
    path = os.path.join(BASE_DIR, "inquiries.jsonl")
    rec = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "userId": user_id,
           "text": text, "source": src, "reply": reply[:400]}
    try:
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except OSError as e:
        log(f"inquiry log error: {e!r}")


RETENTION_DAYS = int(os.environ.get("RETENTION_DAYS", "90"))


def purge_old_inquiries():
    """Delete inquiry records older than RETENTION_DAYS (privacy policy §4)."""
    path = os.path.join(BASE_DIR, "inquiries.jsonl")
    if not os.path.exists(path):
        return 0
    cutoff = time.time() - RETENTION_DAYS * 86400
    kept, removed = [], 0
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    ts = json.loads(line).get("ts", "")
                    when = time.mktime(time.strptime(ts, "%Y-%m-%dT%H:%M:%S"))
                except (ValueError, KeyError):
                    kept.append(line)
                    continue
                if when >= cutoff:
                    kept.append(line)
                else:
                    removed += 1
        if removed:
            tmp = path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                f.write("\n".join(kept) + ("\n" if kept else ""))
            os.replace(tmp, path)
            log(f"retention: purged {removed} record(s) older than {RETENTION_DAYS}d")
    except OSError as e:
        log(f"retention purge error: {e!r}")
    return removed


def llm_reply(text, history=None):
    """Ask the LLM for a grounded answer. Returns None on any failure."""
    key = get_llm_key()
    if not key:
        log("LLM: no OPENROUTER_API_KEY found")
        return None
    msgs = [{"role": "system", "content": SYSTEM_PROMPT}]
    for h in (history or [])[-4:]:
        msgs.append(h)
    msgs.append({"role": "user", "content": text})
    payload = json.dumps({
        "model": LLM_MODEL,
        "messages": msgs,
        "max_tokens": 700,
        "temperature": 0.3,
    }).encode()
    req = urllib.request.Request(
        LLM_URL, data=payload,
        headers={"Authorization": "Bearer " + key,
                 "Content-Type": "application/json",
                 "HTTP-Referer": "https://cootai.tw",
                 "X-Title": "CooTai LINE Agent"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            data = json.loads(resp.read())
        msg = data["choices"][0]["message"]
        content = (msg.get("content") or "").strip()
        if not content:
            log(f"LLM: empty content (finish={data['choices'][0].get('finish_reason')})")
            return None
        return content
    except Exception as e:
        log(f"LLM error: {e!r}")
        return None



_whisper = None


def log(msg):
    """Timestamped, unbuffered log line (systemd captures stderr)."""
    import sys
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}", file=sys.stderr, flush=True)


def get_whisper():
    """Lazy-load the Chinese-capable Whisper model once."""
    global _whisper
    if _whisper is None:
        from faster_whisper import WhisperModel
        _whisper = WhisperModel("small", device="cpu", compute_type="int8",
                                download_root=MODEL_DIR)
    return _whisper


def download_content(message_id):
    """Download an audio message's bytes from LINE's content API."""
    req = urllib.request.Request(
        CONTENT_API.format(message_id),
        headers={"Authorization": "Bearer " + ACCESS_TOKEN},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read()


def transcribe_audio(raw_bytes):
    """Transcribe Chinese (or mixed) audio bytes -> text.
    Converts to 16k mono WAV via ffmpeg, decodes with stdlib wave,
    passes a float32 numpy array to Whisper (per audio-transcription skill).
    """
    with tempfile.TemporaryDirectory() as td:
        src = os.path.join(td, "in.m4a")
        wav = os.path.join(td, "out.wav")
        with open(src, "wb") as f:
            f.write(raw_bytes)
        subprocess.run(
            [FFMPEG, "-y", "-v", "error", "-i", src,
             "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", wav],
            check=True, timeout=60,
        )
        with wave.open(wav, "rb") as w:
            sr = w.getframerate()
            raw = w.readframes(w.getnframes())
    audio = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    model = get_whisper()
    segments, info = model.transcribe(audio, language="zh", beam_size=5,
                                      vad_filter=True)
    return "".join(s.text for s in segments).strip()



def verify_signature(channel_secret, body, signature):
    """LINE signs webhook bodies with HMAC-SHA256 using the Channel Secret."""
    if not signature:
        return False
    digest = hmac.new(channel_secret.encode(), body, hashlib.sha256).digest()
    computed = base64.b64encode(digest).decode()
    return hmac.compare_digest(computed, signature)


PUSH_API = "https://api.line.me/v2/bot/message/push"


def send_push(user_id, text):
    """Push costs monthly quota; only used when the reply token has expired."""
    payload = {"to": user_id, "messages": [{"type": "text", "text": text}]}
    req = urllib.request.Request(
        PUSH_API,
        data=json.dumps(payload).encode(),
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer " + ACCESS_TOKEN,
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return resp.status


def send_reply(reply_token, text, user_id=None):
    """Reply tokens are free but expire; fall back to a push when they do."""
    payload = {
        "replyToken": reply_token,
        "messages": [{"type": "text", "text": text}],
    }
    req = urllib.request.Request(
        API,
        data=json.dumps(payload).encode(),
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer " + ACCESS_TOKEN,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status
    except urllib.error.HTTPError as e:
        if e.code == 400 and user_id:
            log("reply token rejected -> push fallback")
            return send_push(user_id, text)
        raise


# --- Hermes agent bridge -------------------------------------------------
# Users in this allowlist get the real agent (tools, web, research), not the
# scripted FAQ. Everyone else stays on the rule engine. This is the security
# boundary: an unlisted LINE user can never reach a tool.
OWNER_IDS = {
    u.strip() for u in os.environ.get(
        "OWNER_IDS",
        "U7b2a333bd2eaa58b8c751c65b96d7259",   # Chun
    ).split(",") if u.strip()
}

HERMES_BIN = os.environ.get("HERMES_BIN",
                            os.path.expanduser("~/.local/bin/hermes"))
# Research queries (search + extract + synthesise) routinely need 60-90s on
# 2 vCPU. The reply token expires before that, so send_reply falls back to a
# push; this budget is what actually bounds the turn.
AGENT_TIMEOUT = int(os.environ.get("AGENT_TIMEOUT", "110"))

AGENT_BUSY = (
    "這題要查的資料比較多，處理超過兩分鐘了。\n"
    "可以先把範圍縮小一點，例如指定一家、或指定要看的項目，我再幫您查。"
)


def agent_reply(text, user_id):
    """Run the full Hermes agent for one turn. None means it didn't finish."""
    if not os.path.exists(HERMES_BIN):
        log(f"AGENT missing binary {HERMES_BIN}")
        return None

    session = "line-" + user_id[-12:]
    cmd = [HERMES_BIN, "chat", "-Q", "--oneshot",
           "--continue", session, "--create-if-missing",
           "-q", text]

    env = dict(os.environ)
    env["PATH"] = os.path.dirname(HERMES_BIN) + ":" + env.get("PATH", "")
    env.setdefault("HOME", os.path.expanduser("~"))

    started = time.time()
    try:
        p = subprocess.run(cmd, capture_output=True, text=True,
                           timeout=AGENT_TIMEOUT, env=env)
    except subprocess.TimeoutExpired:
        log(f"AGENT timeout after {AGENT_TIMEOUT}s")
        return None
    except Exception as e:                      # noqa: BLE001
        log(f"AGENT spawn failed: {e}")
        return None

    elapsed = time.time() - started
    if p.returncode != 0:
        log(f"AGENT rc={p.returncode} in {elapsed:.1f}s "
            f"err={(p.stderr or '')[:200].strip()}")

    out = "\n".join(
        line for line in (p.stdout or "").splitlines()
        if not line.startswith("session_id:")
    ).strip()

    log(f"AGENT reply in {elapsed:.1f}s len={len(out)}")
    return out or None


# Physical location used by the "location" / "map" intents. Swap this per client.
# Resolved by Google at tap time, so no coordinates are stored (and none can be wrong).
MAP_QUERY = os.environ.get("MAP_QUERY", "新北市林口區仁愛路二段630號")
MAP_URL = "https://www.google.com/maps/search/?api=1&query=" + \
          urllib.parse.quote(MAP_QUERY)

CATCH_ALL = (
    "您好！這裡是仁僾文理語文短期補習班 😊\n"
    "這個問題我請老師為您確認，會儘快回覆您。\n"
    "如果想直接詢問，也可以來電 (02) 2608-5425。"
)

INTENTS = {
    "greet": (
        "您好！這裡是仁僾文理語文短期補習班 🙌\n"
        "請問想了解課程，還是要幫孩子預約試聽呢？"
    ),
    "price": (
        "學費依年級與科目不同，我們沒有公開的價目表。\n"
        "方便告訴我孩子的年級，以及想加強的科目嗎？\n"
        "我請老師直接跟您說明，或您也可以來電 (02) 2608-5425。"
    ),
    "location": (
        "我們在 244 新北市林口區湖南里仁愛路二段 630 號，電話 (02) 2608-5425。\n"
        "地圖在這裡 👉 " + MAP_URL + "\n"
        "歡迎到班參觀，建議先來電確認時段。"
    ),
    "hours": (
        "各班上課時間不同，方便的話我請老師跟您確認。\n"
        "也可以直接來電 (02) 2608-5425 詢問。"
    ),
    "booking": (
        "好的！請問孩子是幾年級、想試聽哪一個科目呢？\n"
        "我請老師跟您確認時段，也歡迎先來電 (02) 2608-5425。"
    ),
    "emotion": (
        "很抱歉讓您有此感受。\n"
        "請讓我知道是哪一門課或哪位老師，我會請班主任盡快跟您聯繫。"
    ),
    "services": (
        "我們有國小部與國中部：\n"
        "・國小部：全科數學、康軒英語、美語、作文\n"
        "・國中部：數學、英文、理化、全科班\n\n"
        "請問孩子目前幾年級？想加強哪一科呢？"
    ),
    "about": (
        "仁僾文理語文短期補習班位於林口仁愛路二段，政府立案、安檢合格。\n"
        "我們從國小到國中一路陪孩子打好基礎，小班制教學。\n\n"
        "需要我為您介紹課程，或幫孩子安排試聽嗎？"
    ),
}

KW = {
    "greet": ["你好", "您好", "hello", "hi", "嗨", "哈囉"],
    "price": ["多少", "價格", "費用", "多少錢", "價錢", "收費", "月費", "方案", "怎麼算", "price", "cost"],
    "location": ["地址", "哪裡", "位置", "在哪", "地圖", "地圖連結", "怎麼去",
                 "怎麼走", "google map", "maps", "map", "location", "address", "where"],
    "hours": ["時間", "營業", "幾點", "幾號", "hours", "open", "時間表"],
    "booking": ["預約", "掛號", "報名", "預定", "booking", "book", "登記", "排"],
    "emotion": ["很糟", "糟", "很差", "差勁", "不好", "不滿", "投訴", "客訴",
                "生氣", "離譜", "太慢", "太貴", "抱怨", "失望", "爛"],
    "services": ["服務包含", "服務內容", "服務項目", "有哪些服務", "什麼服務",
                 "提供什麼", "做什麼", "能做什麼", "怎麼幫", "幫我什麼",
                 "service", "offer"],
    "about": ["你們是誰", "你們是甚麼", "你們是什麼", "公司簡介", "介紹你們",
              "介紹一下", "你們公司", "誰是", "about", "who are you"],
}


def match_intent(text):
    t = text.lower()
    for intent, words in KW.items():
        for w in words:
            if w in t:
                return intent
    return None


# ---- per-user short conversation memory (in-process, last few turns) ----
_HISTORY = {}
_HISTORY_MAX = 4  # keep 4 messages = 2 exchanges


def _remember(user_id, role, content):
    if not user_id:
        return
    h = _HISTORY.setdefault(user_id, [])
    h.append({"role": role, "content": content})
    del h[:-_HISTORY_MAX]


def _history(user_id):
    return list(_HISTORY.get(user_id, []))


# LINE hard limit is 5000 chars; keep well under it.
MAX_REPLY = 1500

# Hard cap on request body size, enforced before reading and before
# signature verification. LINE webhook payloads are far smaller than this.
MAX_BODY_BYTES = 65536


# ---- rate limiting: paid model calls and owner notifications ----
# Both buckets are bounded so this cannot become the unbounded-growth bug it fixes.
_LIMIT_MAX_USERS = 5000
_LIMITS = {
    "llm":    (OrderedDict(), int(os.environ.get("MAX_LLM_PER_HOUR", "20"))),
    "notify": (OrderedDict(), int(os.environ.get("MAX_NOTIFY_PER_HOUR", "10"))),
}


def _allowed(kind, user_id):
    """Per-user hourly token bucket, checked immediately before the spend."""
    # Events without a userId (rare on a 1:1 account) share one fallback bucket
    # rather than being refused outright, so they stay usable but still bounded.
    key = user_id or "__anonymous__"
    bucket, cap = _LIMITS[kind]
    now = time.time()
    start, count = bucket.get(key, (now, 0))
    if now - start > 3600:
        start, count = now, 0
    ok = count < cap
    bucket[key] = (start, count + 1) if ok else (start, count)
    bucket.move_to_end(key)
    while len(bucket) > _LIMIT_MAX_USERS:
        bucket.popitem(last=False)
    return ok


RATE_LIMITED = (
    "謝謝您的訊息！為了確保回覆品質，今天的訊息量先到這邊。\n"
    "需要專人協助的話，請留下聯絡方式，我們會在上班時間儘快與您聯繫。"
)


def compose_reply(text, user_id=None):
    """Owner -> full agent. Everyone else -> rules, then grounded LLM."""
    if user_id and user_id in OWNER_IDS:
        _remember(user_id, "user", text)
        out = agent_reply(text, user_id)
        if out:
            _remember(user_id, "assistant", out)
            return out, "agent"
        return AGENT_BUSY, "agent_busy"

    intent = match_intent(text)
    if intent:
        _remember(user_id, "user", text)
        reply = INTENTS[intent]
        _remember(user_id, "assistant", reply)
        return reply, f"rule:{intent}"

    # No rule matched -> paid model. Gate it before spending.
    if not _allowed("llm", user_id):
        log("LLM: rate limited")
        return RATE_LIMITED, "rate_limited"

    llm = llm_reply(text, history=_history(user_id))
    if llm:
        _remember(user_id, "user", text)
        _remember(user_id, "assistant", llm)
        return llm, "llm"

    # LLM unavailable -> safe fallback
    return CATCH_ALL, "catch_all"


def handle(event):
    if event.get("type") != "message":
        return
    msg = event.get("message", {})
    mtype = msg.get("type")
    token = event.get("replyToken")
    user_id = (event.get("source") or {}).get("userId")

    if mtype == "text":
        text = msg.get("text", "")
        # Metadata only: the message body lives in inquiries.jsonl, which the
        # retention routine prunes. Writing it to the journal too created a
        # second copy that outlived the stated 90-day retention.
        log(f"TEXT  <- len={len(text)}")
        reply, src = compose_reply(text, user_id)
        log(f"TEXT  -> {src}")
        log_inquiry(user_id, text, src, reply)
        if src == "llm":
            # Unscripted question = genuine inquiry -> alert the owner
            if _allowed("notify", user_id):
                notify_owner(text, user_id, "inquiry")
        elif src == "rule:booking":
            if _allowed("notify", user_id):
                notify_owner(text, user_id, "booking")
        if token:
            send_reply(token, reply[:MAX_REPLY], user_id)
        return

    if mtype == "audio":
        log(f"AUDIO <- id={msg.get('id')} dur={msg.get('duration')}ms downloading...")
        try:
            raw = download_content(msg.get("id"))
            text = transcribe_audio(raw)
        except Exception as e:
            log(f"voice transcribe error: {e!r}")
            if token:
                send_reply(token, "不好意思，語音訊息處理失敗，請再試一次或用文字輸入，謝謝！")
            return
        if not text:
            log("AUDIO -> empty transcript")
            if token:
                send_reply(token, "不好意思，我沒聽清楚，可以再說一次嗎？")
            return
        # Metadata only, same reason as the text branch: no second copy outside
        # the pruned inquiry log.
        log(f"AUDIO -> transcribed len={len(text)}")
        reply, src = compose_reply(text, user_id)
        log(f"AUDIO -> {src}")
        log_inquiry(user_id, text, f"voice:{src}", reply)
        if src == "llm":
            if _allowed("notify", user_id):
                notify_owner(f"（語音）{text}", user_id, "inquiry")
        elif src == "rule:booking":
            if _allowed("notify", user_id):
                notify_owner(f"（語音）{text}", user_id, "booking")
        # Echo the transcript so the user knows we heard them correctly
        reply = f"（我聽到的是：「{text}」）\n\n" + reply
        if token:
            send_reply(token, reply[:MAX_REPLY], user_id)
        return

    log(f"OTHER <- unsupported message type={mtype!r}")
    if token:
        send_reply(token, "目前我可以處理文字與語音訊息，請用文字或語音輸入，謝謝！",
                   user_id)


def _export_csv():
    """Render inquiries.jsonl as a UTF-8 CSV for the client's data-portability right.

    Required by the 商業發展署 智慧轉型方案 推廣計畫書 (店家資料自主權).
    All rows we hold come back, including the userId, so the client receives the
    complete record rather than a curated summary.
    """
    path = os.path.join(BASE_DIR, "inquiries.jsonl")
    rows = [["時間", "使用者ID", "訊息內容", "來源", "回覆摘要"]]
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    r = json.loads(line)
                except ValueError:
                    continue
                rows.append([r.get("ts", ""), r.get("userId", ""), r.get("text", ""),
                             r.get("source", ""), r.get("reply", "")])
    except FileNotFoundError:
        pass
    buf = io.StringIO()
    # BOM so Excel opens Traditional Chinese correctly instead of mojibake
    buf.write("\ufeff")
    csv.writer(buf).writerows(rows)
    return buf.getvalue().encode("utf-8")


def app(environ, start_response):
    path = environ.get("PATH_INFO", "/")

    # Data portability endpoint (GET /export?token=...). Disabled unless a token
    # is configured, so an unconfigured deployment cannot leak conversations.
    if path == "/export":
        if environ["REQUEST_METHOD"] != "GET":
            start_response("405 Method Not Allowed", [("Content-Type", "text/plain")])
            return [b"GET only"]
        want = os.environ.get("EXPORT_TOKEN", "") or CREDS.get("export_token", "")
        if not want:
            start_response("403 Forbidden", [("Content-Type", "text/plain")])
            return [b"export disabled"]
        got = parse_qs(environ.get("QUERY_STRING", "")).get("token", [""])[0]
        if not hmac.compare_digest(want, got):
            log("export: rejected bad token")
            start_response("403 Forbidden", [("Content-Type", "text/plain")])
            return [b"forbidden"]
        payload = _export_csv()
        log(f"export: served {len(payload)} bytes")
        start_response("200 OK", [
            ("Content-Type", "text/csv; charset=utf-8"),
            ("Content-Disposition", 'attachment; filename="cootai-conversations.csv"'),
            ("Content-Length", str(len(payload))),
            ("Cache-Control", "no-store"),
        ])
        return [payload]

    if environ["REQUEST_METHOD"] != "POST":
        start_response("405 Method Not Allowed", [("Content-Type", "text/plain")])
        return [b"POST only"]

    # Bound the body BEFORE reading it and before signature verification.
    # An unbounded read here let an unauthenticated attacker stall the
    # single-threaded server with a large Content-Length and no body.
    # LINE webhook payloads are well under this cap.
    raw_len = environ.get("CONTENT_LENGTH") or "0"
    if not raw_len.isdigit() or int(raw_len) > MAX_BODY_BYTES:
        log(f"reject: bad CONTENT_LENGTH={raw_len!r}")
        start_response("413 Payload Too Large", [("Content-Type", "text/plain")])
        return [b"bad content length"]
    clen = int(raw_len)
    body = environ["wsgi.input"].read(clen)
    signature = environ.get("HTTP_X_LINE_SIGNATURE", "")

    if not verify_signature(CHANNEL_SECRET, body, signature):
        start_response("400 Bad Request", [("Content-Type", "text/plain")])
        return [b"signature mismatch"]

    data = json.loads(body)
    for event in data.get("events", []):
        try:
            handle(event)
        except Exception as e:
            print("handler error:", e, flush=True)

    start_response("200 OK", [("Content-Type", "text/plain")])
    return [b"OK"]


if __name__ == "__main__":
    from wsgiref.simple_server import make_server, WSGIServer
    from socketserver import ThreadingMixIn
    import threading

    # The default wsgiref server is single-threaded: one slow request blocks
    # every other client. Thread it so a stalled connection cannot deny
    # service to real customers.
    class ThreadingWSGIServer(ThreadingMixIn, WSGIServer):
        daemon_threads = True

    port = int(os.environ.get("PORT", 8080))
    log(f"CooTai LINE agent listening on :{port}")
    log("warming Whisper model in background (first voice msg will be faster)...")

    def _warm():
        t0 = time.time()
        try:
            get_whisper()
            log(f"Whisper model ready in {time.time()-t0:.1f}s")
        except Exception as e:
            log(f"Whisper warmup failed: {e!r}")

    def _retention_loop():
        # Purge at boot, then every 24h (privacy policy §4: 90-day retention)
        while True:
            try:
                purge_old_inquiries()
            except Exception as e:
                log(f"retention loop error: {e!r}")
            time.sleep(86400)

    threading.Thread(target=_warm, daemon=True, name="whisper-warmup").start()
    threading.Thread(target=_retention_loop, daemon=True, name="retention").start()

    server = make_server("0.0.0.0", port, app, ThreadingWSGIServer)
    server.serve_forever()