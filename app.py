import os
import json
import logging
from datetime import datetime
from fastapi import FastAPI, Request, HTTPException, Response
from pydantic import BaseModel
from twilio.rest import Client
from dotenv import load_dotenv

load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Config
ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
FROM_WHATSAPP = os.getenv("TWILIO_FROM_WHATSAPP", "whatsapp:+14155238886")
TO_WHATSAPP = os.getenv("TWILIO_TO_WHATSAPP")
WEBHOOK_TOKEN = os.getenv("WEBHOOK_TOKEN")

if not all([ACCOUNT_SID, AUTH_TOKEN, FROM_WHATSAPP, TO_WHATSAPP, WEBHOOK_TOKEN]):
    missing = [k for k, v in {
        "TWILIO_ACCOUNT_SID": ACCOUNT_SID,
        "TWILIO_AUTH_TOKEN": AUTH_TOKEN,
        "TWILIO_FROM_WHATSAPP": FROM_WHATSAPP,
        "TWILIO_TO_WHATSAPP": TO_WHATSAPP,
        "WEBHOOK_TOKEN": WEBHOOK_TOKEN
    }.items() if not v]
    raise RuntimeError(f"Missing env vars: {', '.join(missing)}")

client = Client(ACCOUNT_SID, AUTH_TOKEN)
app = FastAPI(title="TradingView → WhatsApp")

# Log startup info
@app.on_event("startup")
async def startup_event():
    logger.info("=" * 60)
    logger.info("🚀 TradingView → WhatsApp Server Starting...")
    logger.info("=" * 60)
    logger.info(f"📱 FROM: {FROM_WHATSAPP}")
    logger.info(f"📱 TO: {TO_WHATSAPP}")
    logger.info(f"🔑 Webhook Token: {WEBHOOK_TOKEN}")
    logger.info(f"✅ Twilio Client initialized")
    logger.info("=" * 60)

class TVPayload(BaseModel):
    # TradingView often sends arbitrary JSON; accept anything
    # but keep a conventional 'message' field if provided.
    message: str | None = None

@app.get("/")
def root():
    logger.info("📥 GET request to root /")
    return {"ok": True, "msg": "Server is running! Use POST /webhook for alerts"}

@app.post("/")
async def root_post():
    logger.warning("⚠️ POST to root / - should use /webhook instead")
    return {"error": "Use POST /webhook endpoint, not /"}

@app.get("/healthz")
def healthz():
    return {"ok": True, "ts": datetime.utcnow().isoformat()}

@app.head("/healthz")
def healthz_head():
    # minimal HEAD response without body
    return Response(headers={"X-App": "tv-whatsapp", "X-OK": "1"})

@app.post("/webhook")
async def webhook(request: Request):
    logger.info("=" * 60)
    logger.info("📥 WEBHOOK RECEIVED!")
    
    # Optional token check - only validate if token is provided
    token = request.headers.get("X-Webhook-Token")
    if token:
        logger.info(f"🔑 Received token: {token[:10]}...")
        logger.info(f"🔑 Expected token: {WEBHOOK_TOKEN[:10]}...")
        if token != WEBHOOK_TOKEN:
            logger.error("❌ UNAUTHORIZED: Token mismatch!")
            raise HTTPException(status_code=401, detail="Unauthorized")
        logger.info("✅ Token verified")
    else:
        logger.info("⚠️ No token provided - allowing request (TradingView alert)")

    # Accept both JSON and raw text payloads
    text = None
    try:
        # Try JSON first
        body = await request.json()
        logger.info(f"📄 Received JSON: {body}")
        # If a message field is present, prefer it; else pretty-print JSON
        text = body.get("message") if isinstance(body, dict) else None
        if not text:
            text = json.dumps(body, indent=2)
    except:
        # Fallback to raw text (TradingView alert() sends plain text)
        raw = await request.body()
        text = raw.decode('utf-8', errors='ignore')
        logger.info(f"📄 Received raw text (TradingView alert): {text[:200]}...")

    logger.info(f"📤 Sending to WhatsApp: {TO_WHATSAPP}")
    logger.info(f"📝 Message preview: {text[:100]}...")
    
    try:
        # Send WhatsApp message
        msg = client.messages.create(
            from_=FROM_WHATSAPP,
            to=TO_WHATSAPP,
            body=text[:1600]  # keep under WA/SMS-friendly limits
        )
        logger.info(f"✅ SUCCESS! Message sent with SID: {msg.sid}")
        logger.info(f"📊 Message status: {msg.status}")
        logger.info("=" * 60)
        return {"status": "sent", "sid": msg.sid}
    except Exception as e:
        logger.error(f"❌ TWILIO ERROR: {str(e)}")
        logger.error("=" * 60)
        raise HTTPException(status_code=500, detail=f"Twilio error: {str(e)}")

