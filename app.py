import os
import json
import logging
from datetime import datetime
from fastapi import FastAPI, Request, HTTPException, Response, BackgroundTasks, status
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

@app.head("/")
def root_head():
    # Respond to Render/UptimeRobot HEAD checks at "/"
    return Response(headers={"X-Root": "1"})

@app.get("/healthz")
def healthz():
    return {"ok": True, "ts": datetime.utcnow().isoformat()}

@app.head("/healthz")
def healthz_head():
    return Response(headers={"X-App": "tv-whatsapp", "X-OK": "1"})

def _send_whatsapp(text: str):
    try:
        msg = client.messages.create(
            from_=FROM_WHATSAPP,
            to=TO_WHATSAPP,
            body=text[:1600],
        )
        logger.info(f"✅ SENT (bg) SID={msg.sid} status={msg.status}")
    except Exception as e:
        logger.exception(f"❌ TWILIO ERROR (bg): {e}")

@app.post("/webhook", status_code=status.HTTP_202_ACCEPTED)
async def webhook(request: Request, background_tasks: BackgroundTasks):
    logger.info("=" * 60)
    logger.info("📥 WEBHOOK RECEIVED!")

    # Optional token check (keep your existing lines if you use a token)
    token = request.headers.get("X-Webhook-Token")
    if WEBHOOK_TOKEN and token != WEBHOOK_TOKEN:
        logger.error("❌ UNAUTHORIZED: Token mismatch!")
        raise HTTPException(status_code=401, detail="Unauthorized")

    payload_text = await request.body()
    try:
        # pretty format if JSON, else raw
        try:
            body_json = json.loads(payload_text)
            text = json.dumps(body_json, indent=2)[:1600]
        except Exception:
            text = payload_text.decode("utf-8", errors="ignore")[:1600]
    except Exception as e:
        logger.exception(f"Failed reading body: {e}")
        text = "(no body)"

    # Queue the actual send so we can ACK immediately
    background_tasks.add_task(_send_whatsapp, text)
    logger.info("🟢 ACK 202 — send scheduled in background")
    return {"accepted": True, "queued_at": datetime.utcnow().isoformat()}

