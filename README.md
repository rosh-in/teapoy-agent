# Pi2Printer Email Monitor 🎯📧🖨️

Transform your Gmail into Mission Impossible briefings on thermal paper! This system monitors your Gmail, uses AI to extract actionable tasks, and prints them as physical mission briefings.

## Current Status ✅

The system is **working and ready** with these components:

- ✅ **Gmail API integration** - Monitoring your emails
- ✅ **Gemini AI analysis** - Smart task extraction 
- ✅ **SQLite database** - Mission tracking
- ✅ **Thermal printer support** - Physical briefings (fallback to file for testing)
- ✅ **Mission Impossible formatting** - Proper briefing style

## Quick Start 🚀

### 1. Check System Status
```bash
python3 pi2printer_cli.py status
```

### 2. Run One Email Check
```bash
python3 pi2printer_cli.py check
```

### 3. Start Continuous Monitoring
```bash
./start_monitoring.sh
# OR
python3 email_monitor.py --interval 5
```

### 4. View Your Missions
```bash
python3 pi2printer_cli.py list
python3 pi2printer_cli.py show MI-12345678
```

## Available Commands 📋

### Email Monitor Commands
```bash
# Run single check cycle
python3 email_monitor.py --check-once

# Start continuous monitoring (5 min intervals)
python3 email_monitor.py --interval 5

# Show system status
python3 email_monitor.py --status
```

### CLI Management Commands
```bash
# System status
python3 pi2printer_cli.py status

# List recent missions
python3 pi2printer_cli.py list
python3 pi2printer_cli.py list --status NEW --limit 5

# Show mission details  
python3 pi2printer_cli.py show MI-12345678

# Mark missions complete/cancelled
python3 pi2printer_cli.py complete MI-12345678
python3 pi2printer_cli.py cancel MI-12345678

# Test printer
python3 pi2printer_cli.py test-printer

# Reprint mission
python3 pi2printer_cli.py print MI-12345678

# Start monitoring
python3 pi2printer_cli.py monitor --interval 5
```

## How It Works 🧠

1. **Email Monitoring**: Checks Gmail every 5 minutes for new emails
2. **AI Analysis**: Uses Gemini 2.5 Flash Lite to analyze emails for actionable tasks
3. **Smart Filtering**: Skips newsletters, promotions, automated notifications
4. **Mission Creation**: Creates database entries for actionable tasks
5. **Physical Printing**: Prints Mission Impossible style briefings on thermal paper
6. **Tracking**: Stores missions with status tracking (NEW → COMPLETED)

## Mission Briefing Format 📄

```
================================
    MISSION BRIEFING
================================

AGENT: Agent Roshin
URGENCY: HIGH
TIME: 14:11 13/12/2025

MISSION:
Experiment with Warp Terminal AI Agent

PEOPLE INVOLVED:
Eric from Warp

YOUR MISSION, SHOULD YOU
CHOOSE TO ACCEPT IT:
Open Warp and use the AI agent with the 
provided prompt.

*** THIS MESSAGE WILL
    SELF-DESTRUCT ***

DEADLINE: ASAP

================================
MISSION ID: MI-19b12dd7
================================
```

## Current Stats 📊

Based on your current system:
- **1 mission** created (LOW urgency)
- **1 email** processed with task
- **File output mode** (thermal printer fallback)
- **Last check**: Working properly

## Configuration 🔧

The system uses:
- **Gmail API** with readonly permissions (`token.json`)
- **Gemini API** for AI analysis (`.env` file)
- **SQLite database** (`pi2printer.db`)
- **Thermal printer** (USB, fallback to `printed_missions.txt`)

## Urgency Levels 🚨

- **🔥 CRITICAL**: Response needed within 2 hours
- **⚠️ HIGH**: Response needed today/tomorrow  
- **⭐ MEDIUM**: Response needed within 3-7 days
- **📋 LOW**: Can be addressed when convenient
- **ℹ️ INFO**: No action required, reference only

## Next Steps 🎯

### For Production Use:
1. **Connect thermal printer**: USB 58mm thermal receipt printer
2. **Run on Raspberry Pi**: Deploy to Pi Zero 2W for 24/7 monitoring
3. **Add Google Tasks**: Link missions to Google Tasks for mobile completion
4. **Customize filters**: Adjust AI prompts for your specific needs

### For Testing:
- Missions print to `printed_missions.txt`
- Monitor with `python3 pi2printer_cli.py monitor`
- Check status with `python3 pi2printer_cli.py status`

## File Structure 📁

```
pi2printer/
├── email_monitor.py      # Main monitoring service
├── pi2printer_cli.py     # Command line interface  
├── database.py           # SQLite database management
├── printer_service.py    # Thermal printer handling
├── start_monitoring.sh   # Easy startup script
├── gmail_test.py         # Gmail API testing
├── gemini_test.py        # AI analysis testing
├── requirements.txt      # Python dependencies
├── .env                  # API keys (GEMINI_API_KEY)
├── token.json           # Gmail credentials
├── pi2printer.db        # Mission database
├── printed_missions.txt # Printer output (testing)
└── email_monitor.log    # System logs
```

## Troubleshooting 🔧

### Common Issues:

1. **No new emails detected**: Check `email_monitor.log` for Gmail API issues
2. **AI analysis fails**: Verify `GEMINI_API_KEY` in `.env`
3. **Database errors**: Check file permissions on `pi2printer.db`
4. **Printer issues**: System falls back to file output automatically

### Logs:
- System logs: `email_monitor.log`
- Database status: `python3 pi2printer_cli.py status`
- Mission details: `python3 pi2printer_cli.py show MI-XXXXXXXX`

---

**Ready for Mission Impossible productivity! 🕵️‍♂️**

*This system transforms your chaotic inbox into focused, physical action items. No more checking email - let the AI check for you and deliver only what matters.*