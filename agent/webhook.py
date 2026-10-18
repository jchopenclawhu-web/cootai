#!/usr/bin/env python3
"""CooTai LINE auto-reply agent webhook."""
import base64
import hashlib
import hmac
import json
import os
import urllib.request

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CREDS = json.load(open(os.path.join(BASE_DIR, "credentials.json"), encoding="utf-8"))
CHANNEL_SECRET = CREDS["channel_secret"]
ACCESS_TOKEN = CREDS["channel_access_token"]
API = "https://api.line.me/v2/bot/message/reply"


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
    "emotion": ["很糟", "不滿", "投訴", "生氣", "糟糕", "太慢", "問題", "客訴"],
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
    if msg.get("type") != "text":
        reply = "目前我只能回覆文字訊息，請以文字輸入您的問題，謝謝！"
    else:
        text = msg.get("text", "")
        intent = match_intent(text)
        reply = INTENTS.get(intent, CATCH_ALL) if intent else CATCH_ALL
    token = event.get("replyToken")
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

    port = int(os.environ.get("PORT", 8080))
    server = make_server("0.0.0.0", port, app)
    print(f"CooTai LINE agent listening on :{port}", flush=True)
    server.serve_forever()