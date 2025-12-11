# Pi2Printer Implementation Plan

## Phase 1: Core System (Current)
- ✅ Gmail API integration
- ✅ Google Gemini AI for task extraction  
- ✅ SQLite database for task storage
- ✅ Google Tasks API for completion tracking
- ✅ FastAPI web framework
- ✅ Thermal printer integration (ESC/POS)

## Phase 2: Home Assistant Integration for Call Monitoring

### 2.1 Home Assistant Setup
**Target Platform:** Raspberry Pi Zero 2W (same device as pi2printer)

**Installation Method Decision:**
- **Chosen:** Python virtual environment installation
- **Reasoning:** 
  - Pi Zero 2W has limited 512MB RAM
  - Docker overhead (~50-100MB) significant on constrained hardware
  - Better performance with direct Python execution
  - More memory available for both Home Assistant and pi2printer

### 2.2 Call Log Integration Architecture
```
Phone (Android) → Home Assistant Companion App → Home Assistant Core → Webhook → Pi2Printer API → AI Analysis → Task Creation → Thermal Print
```

### 2.3 Implementation Steps

#### Step 1: Home Assistant Installation
```bash
# On Raspberry Pi Zero 2W
python3 -m venv homeassistant_venv
source homeassistant_venv/bin/activate
pip install homeassistant
hass --config /home/pi/homeassistant_config
```

#### Step 2: Phone Integration
- Install Home Assistant Companion App on Android device
- Configure call sensor integration
- Enable call log permissions
- Set up real-time call state monitoring

#### Step 3: Automation Configuration
Create Home Assistant automation in `configuration.yaml`:
```yaml
automation:
  - alias: "Missed Call Task Creation"
    trigger:
      platform: state
      entity_id: sensor.phone_call_state
      to: 'missed'
    action:
      service: rest_command.create_pi2printer_task
      data:
        caller_name: "{{ state_attr('sensor.last_call', 'caller_name') }}"
        caller_number: "{{ state_attr('sensor.last_call', 'caller_number') }}"
        call_time: "{{ state_attr('sensor.last_call', 'call_time') }}"
        call_type: "missed"
```

#### Step 4: Pi2Printer API Extension
Add new endpoint to handle call-based tasks:
```python
@app.post("/api/call-task")
async def create_call_task(call_data: CallData):
    # AI analysis of call pattern
    # Generate appropriate task urgency
    # Create mission briefing
    # Send to printer
```

### 2.4 Call Log Task Examples

**High Priority (Multiple Missed Calls):**
```
========================================
    MISSION BRIEFING - HIGH PRIORITY
========================================

AGENT: Roshin
MISSION: Return urgent call from John Smith

SOURCE: Phone Call Log
TIME RECEIVED: 2:30 PM
DEADLINE: End of business day

INTELLIGENCE REPORT:
John Smith called 3 times in last 2 hours.
No voicemail left. Marked as urgent by pattern.

YOUR MISSION, SHOULD YOU CHOOSE TO
ACCEPT IT:
Call back John Smith at +1-555-0123

⚠️  THIS MESSAGE WILL SELF-DESTRUCT
    IN 4 HOURS

========================================
MISSION ID: CALL-001-20231211
========================================
```

**Medium Priority (Single Missed Call):**
```
========================================
    MISSION BRIEFING - MEDIUM
========================================

AGENT: Roshin  
MISSION: Return call from Mom

SOURCE: Phone Call Log
TIME RECEIVED: 11:45 AM
DEADLINE: Today

YOUR MISSION:
Call back Mom at +1-555-0456

========================================
MISSION ID: CALL-002-20231211
========================================
```

### 2.5 Advanced Call Pattern Analysis

**AI Prompt for Call Tasks:**
```
Analyze this call log data and determine task urgency:

CALLER: {caller_name}
NUMBER: {caller_number} 
CALL_TYPE: {missed/answered/declined}
TIMESTAMP: {call_time}
RECENT_PATTERN: {calls_from_same_number_last_24h}
CONTACT_RELATIONSHIP: {family/work/unknown}

Determine:
1. Should this generate a task? (yes/no)
2. If yes:
   - Urgency: CRITICAL/HIGH/MEDIUM/LOW
   - Task description
   - Suggested deadline
   - Context for user

Urgency guidelines:
- CRITICAL: 3+ missed calls in 1 hour, known emergency contacts
- HIGH: 2+ missed calls same day, work contacts during business hours
- MEDIUM: 1 missed call from known contact
- LOW: Unknown numbers, spam likely
```

### 2.6 Resource Management
**Memory Optimization for Pi Zero 2W:**
- Home Assistant: ~200MB RAM usage
- Pi2Printer: ~50MB RAM usage  
- System overhead: ~150MB
- Available: ~100MB buffer (safe operation)

**Process Management:**
- Run both services with systemd
- Configure automatic restart on failure
- Monitor resource usage with scripts
- Implement graceful degradation if memory low

### 2.7 Configuration Options
Users can configure:
- Call urgency thresholds (how many calls = HIGH priority)
- VIP caller list (always HIGH/CRITICAL)
- Quiet hours for call task generation
- Call type filters (missed only vs all calls)
- Integration with existing contacts for context

## Phase 3: Future Expansions
- Additional IoT sensors (door, motion, temperature)
- Voice interface integration
- Multiple phone monitoring
- Call recording analysis for context
- Integration with calendar for call scheduling