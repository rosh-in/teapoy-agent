# Teapoy Agent 🕵️

> *A sleeper agent on your tea table.*

Teapoy Agent monitors your Gmail, uses Gemini AI to classify every incoming email, and prints actionable ones as Mission Impossible-style briefings on a Bluetooth thermal printer — all running silently on a Raspberry Pi.

No more checking your inbox. The agent checks for you, decides what matters, and hands you a physical briefing.

---

## Sample Output

```
================================
         DARK INVOICE
================================
                      MI-3f9a1c2b

AGENT: Agent Roshin          HIGH
                 14:23 SAT 07 MAR

PERSONS OF INTEREST:
- John Smith

YOUR MISSION, SHOULD YOU
CHOOSE TO ACCEPT IT:
  Secure the payment before the
  deadline expires.

INTEL:
Account suspended if not paid
by Friday.

         IN 2 DAYS — MON 09 MAR
================================
     *** THIS MESSAGE WILL
         SELF-DESTRUCT ***
================================
```

---

## Features

- **Gmail label pre-filter** — promotional, social, update, and forum emails are discarded instantly, no AI call wasted
- **Gemini AI classification** — every real email is classified as a `MISSION` (actionable), `MESSAGE` (personal note), or `IGNORE`
- **Parallel processing** — up to 4 emails analysed concurrently; Bluetooth access is serialised to prevent conflicts
- **Quiet hours** — printing is deferred during configurable hours (default 22:00–06:00); deferred missions flush automatically at wake
- **Mission tracking** — SQLite database with full status lifecycle: `NEW → COMPLETED / CANCELLED`
- **Retry logic** — exponential backoff on Gmail API rate limits and Bluetooth busy errors
- **systemd service** — runs 24/7, restarts automatically on failure

---

## Hardware

- Raspberry Pi (any model with Bluetooth — tested on Pi Zero 2W and Pi 4)
- 58mm Bluetooth thermal receipt printer

---

## Prerequisites

- Python 3.9+
- A [Google Cloud project](https://console.cloud.google.com/) with the **Gmail API** enabled and OAuth 2.0 credentials downloaded as `credentials.json`
- A [Gemini API key](https://aistudio.google.com/app/apikey)
- Bluetooth paired with your thermal printer (`bluetoothctl`)

---

## Installation

```bash
git clone https://github.com/rosh-in/teapoy-agent.git
cd teapoy-agent

python3 -m venv agent-teapoy-env
source agent-teapoy-env/bin/activate

pip install -r requirements.txt
```

### 1. Gmail authentication

```bash
python3 -c "from utils import setup_gmail_auth; setup_gmail_auth()"
```

Follow the prompts — you'll open a URL in any browser, authorise, then paste the redirect URL back. This creates `token.json`.

### 2. Environment variables

Create a `.env` file:

```env
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.5-flash-lite

AGENT_NAME=YourName

# Quiet hours (24h local time) — printing deferred during this window
QUIET_START=22
QUIET_END=6

# Optional: Zapier webhook for audio trigger on print
ZAPIER_WEBHOOK_URL=
ZAPIER_STOP_WEBHOOK_URL=
```

### 3. Printer configuration

Edit `pi_config.py` — set your printer's Bluetooth MAC address:

```python
'bluetooth': {
    'enabled': True,
    'address': 'XX:XX:XX:XX:XX:XX',   # ← your printer's MAC
    ...
}
```

---

## Running as a systemd service

```bash
sudo cp pi2printer.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable pi2printer
sudo systemctl start pi2printer
```

Check logs:

```bash
sudo journalctl -u pi2printer -f
```

---

## CLI Reference

```bash
# System status and database stats
python3 pi2printer_cli.py status

# List recent missions
python3 pi2printer_cli.py list
python3 pi2printer_cli.py list --status NEW --limit 20

# Show full mission details
python3 pi2printer_cli.py show MI-3f9a1c2b

# Update mission status
python3 pi2printer_cli.py complete MI-3f9a1c2b
python3 pi2printer_cli.py cancel MI-3f9a1c2b

# Printer
python3 pi2printer_cli.py test-printer
python3 pi2printer_cli.py print MI-3f9a1c2b

# Manual monitoring (one cycle or continuous)
python3 email_monitor.py --check-once
python3 email_monitor.py --interval 0.5   # 30-second polling
```

---

## How It Works

```
Gmail inbox
    │
    ▼
Label pre-filter ──► CATEGORY_PROMOTIONS/SOCIAL/UPDATES/FORUMS → skip
    │
    ▼
Gemini AI (parallel, up to 4 concurrent)
    │
    ├── MISSION → create DB entry → queue for print → Bluetooth printer
    ├── MESSAGE → print personal note
    └── IGNORE  → mark processed, move on
```

Quiet hours: missions are created in the database immediately but printing is held until the window ends. The next cycle after quiet hours flushes the queue.

---

## File Structure

```
teapoy-agent/
├── email_monitor.py      # Core monitoring loop and check cycle
├── pi2printer_cli.py     # CLI for mission management
├── database.py           # SQLite schema and queries
├── printer_service.py    # Bluetooth printer driver and briefing formatter
├── utils.py              # Gmail auth, Gemini wrapper, email parser
├── pi_config.py          # Hardware and environment configuration
├── pi2printer.service    # systemd unit file
├── start_monitoring.sh   # Interactive startup menu
├── requirements.txt
├── .env                  # API keys and agent config (not committed)
├── token.json            # Gmail OAuth token (not committed)
└── agent_teapoy.db       # Mission database (not committed)
```

---

## Troubleshooting

**No emails detected**
Check `email_monitor.log` — the most common cause is an expired Gmail token. Re-run `setup_gmail_auth()` to refresh it.

**Bluetooth printer not connecting**
Verify the MAC address in `pi_config.py` matches your printer. Confirm it's paired: `bluetoothctl devices`. The service retries with exponential backoff on busy errors.

**Gemini API errors**
Confirm `GEMINI_API_KEY` is set in `.env`. Test with:
```bash
python3 utils.py
```

**Missed prints after quiet hours**
Deferred missions are flushed automatically at the start of the first cycle after quiet hours end. You can also trigger manually with `--check-once`.

---

*Your mission, should you choose to accept it.*
