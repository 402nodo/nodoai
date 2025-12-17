# Self-Hosting Guide

This guide covers running NODO on your own infrastructure.

---

## Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| Python | 3.10 | 3.11+ |
| RAM | 512MB | 2GB |
| Storage | 1GB | 5GB |
| Database | SQLite | PostgreSQL 14+ |

**Required accounts:**
- Telegram Bot (free via @BotFather)
- OpenRouter API key (free tier available)

---

## Quick Start

### Step 1: Clone Repository

```bash
git clone https://github.com/nodo-ai/nodo
cd nodo
```

### Step 2: Create Virtual Environment

Virtual environment isolates dependencies from your system Python.

```bash
# Create venv
python -m venv venv

# Activate (Linux/Mac)
source venv/bin/activate

# Activate (Windows)
venv\Scripts\activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

If you see errors about `lru-dict`, you may need C++ build tools. Or simply remove web3-related packages from requirements.txt if you don't need blockchain features.

### Step 4: Configure Environment

Create a `.env` file with your API keys:

```bash
# Copy example
cp .env.example .env

# Edit with your values
nano .env  # or use any text editor
```

Required variables:

```bash
# Telegram bot token from @BotFather
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHI...

# OpenRouter API key from openrouter.ai
OPENROUTER_API_KEY=sk-or-v1-abc123...
```

### Step 5: Run

```bash
python bot/telegram_bot.py
```

You should see:
```
NODO Bot Started
Scanning markets...
```

---

## Configuration Options

### Environment Variables

All configuration is done via environment variables (or `.env` file).

```bash
# === REQUIRED ===
TELEGRAM_BOT_TOKEN=your_bot_token
OPENROUTER_API_KEY=your_openrouter_key

# === OPTIONAL: Additional AI providers ===
# For direct API access (bypassing OpenRouter)
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...

# === OPTIONAL: Scanning settings ===
SCAN_INTERVAL=300        # Seconds between scans (default: 5 min)
MIN_VOLUME=5000          # Minimum market volume in USD
MAX_MARKETS=500          # Markets to fetch per scan

# === OPTIONAL: Database ===
DATABASE_URL=postgresql://user:pass@localhost:5432/nodo
# If not set, uses in-memory storage (data lost on restart)

# === OPTIONAL: Caching ===
REDIS_URL=redis://localhost:6379
# If not set, no caching (slightly slower)
```

### Customizing Models

Edit `bot/config.py` to change which AI models are used:

```python
# Default models for each tier
MODELS = {
    "quick": ["mistralai/mistral-7b-instruct"],
    "standard": [
        "anthropic/claude-3.5-sonnet",
        "openai/gpt-4o",
        "mistralai/mistral-large"
    ],
    "deep": [
        "anthropic/claude-3.5-sonnet",
        "openai/gpt-4o",
        "google/gemini-pro",
        "meta-llama/llama-3.1-70b-instruct",
        "deepseek/deepseek-chat",
        "mistralai/mistral-large"
    ]
}
```

You can use any model available on OpenRouter. See [openrouter.ai/models](https://openrouter.ai/models) for the full list.

---

## Running in Production

### Using systemd (Linux)

Create a service file to run the bot automatically:

```bash
sudo nano /etc/systemd/system/nodo.service
```

Content:

```ini
[Unit]
Description=NODO Prediction Market Bot
After=network.target

[Service]
Type=simple
User=nodo
WorkingDirectory=/home/nodo/nodo
EnvironmentFile=/home/nodo/nodo/.env
ExecStart=/home/nodo/nodo/venv/bin/python bot/telegram_bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl enable nodo
sudo systemctl start nodo

# Check status
sudo systemctl status nodo

# View logs
journalctl -u nodo -f
```

### Using Docker

Dockerfile:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Run bot
CMD ["python", "bot/telegram_bot.py"]
```

Build and run:

```bash
# Build image
docker build -t nodo .

# Run container
docker run -d \
  --name nodo \
  --restart unless-stopped \
  -e TELEGRAM_BOT_TOKEN=your_token \
  -e OPENROUTER_API_KEY=your_key \
  nodo
```

### Docker Compose (Recommended)

For production with database and caching:

```yaml
version: '3.8'

services:
  bot:
    build: .
    restart: unless-stopped
    env_file: .env
    depends_on:
      - db
      - redis

  db:
    image: postgres:15-alpine
    restart: unless-stopped
    environment:
      POSTGRES_DB: nodo
      POSTGRES_USER: nodo
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    restart: unless-stopped
    volumes:
      - redis_data:/data

volumes:
  postgres_data:
  redis_data:
```

Run:

```bash
docker-compose up -d
```

---

## Monitoring

### Health Checks

Add a simple health endpoint if running the API server:

```python
@app.get("/health")
async def health():
    checks = {}
    
    # Check Polymarket API
    try:
        r = await httpx.get("https://gamma-api.polymarket.com/markets?limit=1")
        checks["polymarket"] = r.status_code == 200
    except:
        checks["polymarket"] = False
    
    # Check database
    try:
        await db.execute("SELECT 1")
        checks["database"] = True
    except:
        checks["database"] = False
    
    status = "healthy" if all(checks.values()) else "degraded"
    return {"status": status, "checks": checks}
```

### Logging

Configure logging in `bot/telegram_bot.py`:

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),           # Console
        logging.FileHandler("nodo.log")    # File
    ]
)

# Reduce noise from libraries
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram").setLevel(logging.WARNING)
```

### Alerts

For critical errors, you can send Telegram alerts to yourself:

```python
async def send_alert(message: str):
    """Send alert to admin."""
    admin_chat_id = os.getenv("ADMIN_CHAT_ID")
    if admin_chat_id:
        await bot.send_message(admin_chat_id, f"⚠️ ALERT: {message}")
```

---

## Troubleshooting

### Bot not responding

1. Check if process is running:
```bash
ps aux | grep telegram_bot
```

2. Check logs:
```bash
tail -f nodo.log
# or
journalctl -u nodo -f
```

3. Verify bot token:
```bash
curl "https://api.telegram.org/bot<YOUR_TOKEN>/getMe"
```

### "No markets found"

1. Test Polymarket API directly:
```bash
curl "https://gamma-api.polymarket.com/markets?limit=5"
```

2. Check if you're filtering too aggressively (MIN_VOLUME too high)

### OpenRouter errors

1. Check API key is valid:
```bash
curl https://openrouter.ai/api/v1/models \
  -H "Authorization: Bearer $OPENROUTER_API_KEY"
```

2. Check you have credits (free tier has limits)

3. Verify model name exists (they change sometimes)

### Database connection failed

1. Test connection:
```bash
psql $DATABASE_URL -c "SELECT 1"
```

2. Check firewall allows connection

3. Verify credentials in `.env`

---

## Scaling

### For Higher Load

If you're processing many requests:

**1. Add caching** (reduces API calls):
```python
# Cache market data for 60 seconds
markets = cache.get("markets")
if not markets:
    markets = await scanner.fetch()
    cache.set("markets", markets, ttl=60)
```

**2. Run multiple workers** (Docker Compose):
```yaml
services:
  bot:
    deploy:
      replicas: 3
```

**3. Use connection pooling** (database):
```python
pool = await asyncpg.create_pool(
    DATABASE_URL,
    min_size=5,
    max_size=20
)
```

### Cost Optimization

AI API calls are the main cost. To reduce:

1. **Cache analysis results** for popular markets
2. **Use cheaper models** for initial screening
3. **Batch requests** where possible
