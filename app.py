
import os
import json
import logging
from datetime import datetime, timezone

from fastapi import FastAPI, Request, Response, BackgroundTasks, HTTPException, status
from fastapi.responses import JSONResponse

from twilio.rest import Client

# =============================
# Structured logging
# =============================
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=LOG_LEVEL, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("tv-whatsapp")

# =============================
# Env vars
# =============================
FROM_WHATSAPP = os.getenv("FROM_WHATSAPP", "whatsapp:+14155238886")  # Twilio sandbox sender
TO_WHATSAPP   = os.getenv("TO_WHATSAPP", "whatsapp:+910000000000")   # your WhatsApp
ACCOUNT_SID   = os.getenv("TWILIO_ACCOUNT_SID", "")
AUTH_TOKEN    = os.getenv("TWILIO_AUTH_TOKEN", "")
WEBHOOK_TOKEN = os.getenv("WEBHOOK_TOKEN", "")  # optional shared secret for /webhook

if not ACCOUNT_SID or not AUTH_TOKEN:
    logger.warning("⚠️ TWILIO CREDS missing. Set TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN env vars.")
else:
    logger.info("✅ Twilio credentials detected")

logger.info("📱 FROM: %s", FROM_WHATSAPP)
logger.info("📱 TO:   %s", TO_WHATSAPP)
logger.info("🔑 Webhook Token: %s", "set" if WEBHOOK_TOKEN else "not-set")

client = Client(ACCOUNT_SID, AUTH_TOKEN)

app = FastAPI(title="TradingView → WhatsApp", version="1.0.0")

# =============================
# Helpers
# =============================
def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def _send_whatsapp(text: str):
    """Background task: send WhatsApp message via Twilio."""
    try:
        text = (text or "").strip()
        if not text:
            text = "(empty body)"
        text = text[:1600]  # Safety trim
        msg = client.messages.create(from_=FROM_WHATSAPP, to=TO_WHATSAPP, body=text)
        logger.info("✅ SENT (bg) SID=%s status=%s", getattr(msg, "sid", "?"), getattr(msg, "status", "?"))
    except Exception as e:
        logger.exception("❌ TWILIO ERROR (bg): %s", e)

# =============================
# Root & Health
# =============================
@app.get("/")
def root():
    logger.info("📥 GET /")
    return {
        "ok": True,
        "now": utcnow_iso(),
        "service": "tv-to-whatsapp",
        "health": "/healthz",
        "webhook": "/webhook",
        "docs": "/docs"
    }

@app.head("/")
def root_head():
    # Respond to HEAD / from Render or monitors
    return Response(headers={"X-Root": "1"})

@app.get("/healthz")
def healthz():
    return {"ok": True, "now": utcnow_iso()}

@app.head("/healthz")
def healthz_head():
    return Response(headers={"X-App": "tv-whatsapp", "X-OK": "1"})

# =============================
# Manual test sender
# =============================
@app.get("/send/test")
def send_test(q: str = "Hello from /send/test!"):
    try:
        msg = client.messages.create(from_=FROM_WHATSAPP, to=TO_WHATSAPP, body=q[:1600])
        return {"ok": True, "sid": getattr(msg, "sid", "?"), "status": getattr(msg, "status", "?")}
    except Exception as e:
        logger.exception("❌ /send/test failed")
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)

# =============================
# Webhook — ACK fast, process later
# =============================
@app.post("/webhook", status_code=status.HTTP_202_ACCEPTED)
async def webhook(request: Request, background_tasks: BackgroundTasks):
    """Receives TradingView alert and sends to WhatsApp in background."""
    logger.info("📨 WEBHOOK RECEIVED")

    # Read body (raw and json-friendly)
    body_bytes = await request.body()
    text = ""
    try:
        payload = await request.json()
        text = json.dumps(payload, indent=2)
    except Exception:
        try:
            text = body_bytes.decode("utf-8", errors="ignore")
        except Exception:
            text = "(no body)"
    text = text[:1600]

    # Queue background send and ACK immediately
    background_tasks.add_task(_send_whatsapp, text)
    logger.info("🟢 ACK 202 — queued background send")
    return {"accepted": True, "queued_at": utcnow_iso()}
