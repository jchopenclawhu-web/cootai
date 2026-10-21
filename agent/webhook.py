#!/usr/bin/env python3
"""CooTai LINE auto-reply agent webhook (text + Chinese voice messages)."""
import base64
import hashlib
import hmac
import json
import os
import subprocess
import tempfile
import time
import urllib.request
import wave

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


def send_reply(reply_token, text):
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
    with urllib.request.urlopen(req, timeout=10) as resp:
        return resp.status


CATCH_ALL = (
    "您好！感謝您聯繫我們 😊\n"
    "我們會在營業時間內儘快回覆您。\n"
    "如需快速預約或查詢，也可以直接說明您想了解的內容喔。"
)

INTENTS = {
    "greet": (
        "您好！歡迎來到 CooTai 酷台 🙌\n"
        "請問有什麼可以為您服務？"
    ),
    "price": (
        "我們的服務採月費訂閱制：\n"
        "・入門方案 NT$15,000/月起\n"
        "・標準方案 NT$25,000/月\n"
        "方便告訴我您的需求嗎？我可以為您搭配最適合的方案。"
    ),
    "location": (
        "我們位於新北市林口區。\n"
        "需要我傳送地圖或地址給您嗎？"
    ),
    "hours": (
        "我們的服務團隊於週一至週五 09:00–18:00 提供服務。\n"
        "若您在營業時間外留言，我們會在上班後第一時間回覆。"
    ),
    "booking": (
        "可以的！請問您希望預約哪一天、哪個時段呢？\n"
        "我幫您確認並保留。"
    ),
    "emotion": (
        "很抱歉讓您有此感受。\n"
        "請讓我了解一下情況，我會盡力為您處理。"
    ),
}

KW = {
    "greet": ["你好", "您好", "hello", "hi", "嗨", "哈囉"],
    "price": ["多少", "價格", "費用", "多少錢", "價錢", "收費", "月費", "方案", "怎麼算", "price", "cost"],
    "location": ["地址", "哪裡", "位置", "在哪", "地圖", "location", "address", "where"],
    "hours": ["時間", "營業", "幾點", "幾號", "hours", "open", "時間表"],
    "booking": ["預約", "掛號", "報名", "預定", "booking", "book", "登記", "排"],
    "emotion": ["很糟", "糟", "很差", "差勁", "不好", "不滿", "投訴", "客訴",
                "生氣", "離譜", "太慢", "太貴", "抱怨", "失望", "爛"],
}


def match_intent(text):
    t = text.lower()
    for intent, words in KW.items():
        for w in words:
            if w in t:
                return intent
    return None


def handle(event):
    if event.get("type") != "message":
        return
    msg = event.get("message", {})
    mtype = msg.get("type")
    token = event.get("replyToken")

    if mtype == "text":
        text = msg.get("text", "")
        log(f"TEXT  <- {text!r}")
    elif mtype == "audio":
        # Voice message: download -> transcribe (Chinese) -> treat as text
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
        log(f"AUDIO -> transcribed {text!r}")
        # Fall through: reply based on transcribed intent
        intent = match_intent(text)
        reply = INTENTS.get(intent, CATCH_ALL) if intent else CATCH_ALL
        log(f"AUDIO -> intent={intent or 'catch_all'}")
        # Prefix so the user knows we heard them
        reply = f"（我聽到的是：「{text}」）\n\n" + reply
        if token:
            send_reply(token, reply)
        return
    else:
        log(f"OTHER <- unsupported message type={mtype!r}")
        if token:
            send_reply(token, "目前我可以處理文字與語音訊息，請用文字或語音輸入，謝謝！")
        return

    intent = match_intent(text)
    reply = INTENTS.get(intent, CATCH_ALL) if intent else CATCH_ALL
    log(f"TEXT  -> intent={intent or 'catch_all'}")
    if token:
        send_reply(token, reply)


def app(environ, start_response):
    if environ["REQUEST_METHOD"] != "POST":
        start_response("405 Method Not Allowed", [("Content-Type", "text/plain")])
        return [b"POST only"]

    clen = int(environ.get("CONTENT_LENGTH") or 0)
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
    from wsgiref.simple_server import make_server
    import threading

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

    threading.Thread(target=_warm, daemon=True, name="whisper-warmup").start()

    server = make_server("0.0.0.0", port, app)
    server.serve_forever()