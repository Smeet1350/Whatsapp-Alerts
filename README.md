# 📱 TradingView WhatsApp Alerts

A production-ready FastAPI service that forwards TradingView alerts to WhatsApp via Twilio.

## 🚀 Features

- Receives webhook alerts from TradingView
- Sends instant WhatsApp notifications via Twilio
- Secure webhook token authentication
- Supports both JSON and plain text payloads
- Production-ready with comprehensive logging
- Easy deployment to Render.com

## 📋 Prerequisites

- Python 3.10+
- Twilio account with WhatsApp-enabled number
- TradingView account with alert capabilities

## 🛠️ Local Development Setup

1. **Clone the repository**
```bash
git clone https://github.com/YOUR_USERNAME/Whatsapp-Alerts.git
cd Whatsapp-Alerts
```

2. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Configure environment variables**
```bash
cp .env.example .env
```

Edit `.env` with your credentials:
- `TWILIO_ACCOUNT_SID`: Your Twilio Account SID
- `TWILIO_AUTH_TOKEN`: Your Twilio Auth Token
- `TWILIO_FROM_WHATSAPP`: Your Twilio WhatsApp number (e.g., `whatsapp:+14155238886`)
- `TWILIO_TO_WHATSAPP`: Your WhatsApp number (e.g., `whatsapp:+919876543210`)
- `WEBHOOK_TOKEN`: A strong random secret string

5. **Run locally**
```bash
uvicorn app:app --reload --port 8000
```

Server will be available at `http://localhost:8000`

## 🌐 Deploy to Render

### 1. Prepare Repository
- Ensure all changes are committed to GitHub
- Keep secrets in environment variables only (never commit `.env`)

### 2. Create Render Web Service

1. Go to [Render Dashboard](https://dashboard.render.com/)
2. Click **New → Web Service**
3. Connect your GitHub repository
4. Configure:

**Environment**: Python 3.11

**Build Command**:
```bash
pip install -r requirements.txt
```

**Start Command**:
```bash
gunicorn -k uvicorn.workers.UvicornWorker app:app --bind 0.0.0.0:$PORT
```

**Health Check Path**: `/`

### 3. Add Environment Variables

In Render Settings → Environment, add:

| Key | Value |
|-----|-------|
| `TWILIO_ACCOUNT_SID` | Your Twilio Account SID |
| `TWILIO_AUTH_TOKEN` | Your Twilio Auth Token |
| `TWILIO_FROM_WHATSAPP` | `whatsapp:+14155238886` |
| `TWILIO_TO_WHATSAPP` | `whatsapp:+919876543210` |
| `WEBHOOK_TOKEN` | Strong random secret |

### 4. Deploy

Click **Deploy** and wait for build to complete.

Your service URL: `https://your-service.onrender.com`

## 🔧 TradingView Configuration

### Set up Alert Webhook

1. Open your TradingView chart with strategy/indicator
2. Create Alert
3. Configure Webhook:

**Webhook URL**:
```
https://your-service.onrender.com/webhook
```

**Add Header**:
```
X-Webhook-Token: your-secret-token
```

**Message** (JSON example):
```json
{
  "message": "📈 {{ticker}} | {{interval}} | {{strategy.order.action}} @ {{close}}\nSize: {{strategy.position_size}}\nTime: {{time}}"
}
```

Or plain text:
```
📈 ALERT: {{ticker}} {{strategy.order.action}} @ {{close}}
```

## 🧪 Testing

### Test with curl:
```bash
curl -X POST "https://your-service.onrender.com/webhook" \
  -H "Content-Type: application/json" \
  -H "X-Webhook-Token: your-secret" \
  -d '{"message":"✅ Test alert from TradingView"}'
```

### Test locally:
```bash
curl -X POST "http://localhost:8000/webhook" \
  -H "Content-Type: application/json" \
  -H "X-Webhook-Token: your-secret" \
  -d '{"message":"✅ Local test"}'
```

## 📊 API Endpoints

### `GET /`
Health check endpoint. Returns server status.

**Response**:
```json
{
  "ok": true,
  "msg": "Server is running! Use POST /webhook for alerts"
}
```

### `POST /webhook`
Receives TradingView alerts and sends to WhatsApp.

**Headers**:
- `X-Webhook-Token`: Your webhook secret (required)
- `Content-Type`: `application/json` or `text/plain`

**Body** (JSON):
```json
{
  "message": "Your alert message here"
}
```

**Body** (Plain text):
```
Your alert message here
```

**Response**:
```json
{
  "status": "sent",
  "sid": "SM..."
}
```

## 🔒 Security

- Never commit `.env` file or secrets to Git
- Use strong random strings for `WEBHOOK_TOKEN`
- Keep Twilio credentials secure in Render environment variables
- Webhook token validation is enforced on all requests

## 📝 Notes

### Free Tier Considerations
- **Render Free Tier**: Service may sleep after inactivity. First alert after idle may have ~30s delay while service wakes.
- **Upgrade**: For always-on service, upgrade to a paid Render plan.

### Multiple Recipients
To send to multiple WhatsApp numbers, set `TWILIO_TO_WHATSAPP` as comma-separated and modify `app.py`:

```python
TO_NUMBERS = TO_WHATSAPP.split(',')
for number in TO_NUMBERS:
    client.messages.create(
        from_=FROM_WHATSAPP,
        to=number.strip(),
        body=text[:1600]
    )
```

### Message Limits
- WhatsApp messages are limited to 1600 characters
- Messages are automatically truncated if longer

## 🐛 Troubleshooting

### Check Render Logs
View logs in Render Dashboard → Your Service → Logs

### Common Issues

1. **Webhook not receiving alerts**: Verify TradingView webhook URL and token
2. **Twilio errors**: Check Account SID, Auth Token, and phone number format
3. **Cold start delays**: Consider upgrading from free tier
4. **Message not arriving**: Verify WhatsApp sandbox activation (sandbox numbers only)

## 📄 License

MIT License - feel free to use for personal or commercial projects.

## 🤝 Contributing

Contributions welcome! Please open an issue or submit a PR.

## ⭐ Show Your Support

If this project helped you, give it a star! ⭐

