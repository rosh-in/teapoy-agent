# Teapoy Agent

> *Your mission, should you choose to accept it.*

My email inbox is a graveyard for deadlines and reminders. It has always felt overwhelming to keep up with. So I've reduced doing that by making an AI agent that reframes emails into Mission Impossible styled briefing printouts & plays the Mission Impossible theme score every time it prints the task. It doesn't make the tasks easier but it adds some fun and smiles into my daily life now.

---

## Sample Output

```
================================
        ROGUE NATION
================================
                      MI-9c1f5a7d

AGENT: Agent Roshin                HIGH
                 07:45 MON 09 MAR

PERSONS OF INTEREST:
- Netflix

YOUR MISSION, SHOULD YOU
CHOOSE TO ACCEPT IT:
  Ethan held his breath for
  6 minutes underwater. Roshin
  cannot renew a subscription
  before losing access mid-way
  through a season finale.

INTEL:
Expires at midnight.

      IN 0 DAYS — MON 09 MAR
================================
  *** THIS MESSAGE WILL
  SELF-DESTRUCT ***
================================
```

---

## Hardware

- Raspberry Pi Zero 2W
- 58mm Bluetooth thermal printer
- Amazon Echo Dot (3rd generation)
- 3D printed enclosure to house everything

---

*Your mission, should you choose to accept it.*

---

## Model Evaluation

Inference runs on a laptop over the network — the Pi just makes HTTP calls to an Ollama server. Tried a few models before switching to Gemini.

### gemma3:4b
> good output quality, actually understood email context and urgency well
> needs 4GB RAM minimum — ollama keeps it loaded in memory the whole time
> warm_up_ollama.sh kept it alive in 30 min windows to skip cold starts, but the RAM cost never goes away
> not practical to have your laptop donating 4GB 24/7 to an email monitor

### gemma2:2b
> only ~2GB RAM, fine to run on a laptop 24/7
> cannot run on the Pi Zero 2W directly — it only has 512MB RAM, so inference still stays on the laptop
> the intelligence just isn't there — missed implied deadlines, misread tone, turned noise into missions
> works for simple stuff, falls apart when emails need actual judgment

### LFM 2.5:1.2B (Liquid AI)
> designed for edge/on-device deployment, runs under 1GB RAM
> would fit a Pi 4 or Pi 5 but not the Pi Zero 2W (512MB)
> built for tool-calling and agentic tasks — not knowledge-intensive classification
> results were poor, couldn't reliably turn even simple emails into tasks
> interesting experiment, wrong tool for this

### Gemini 2.5 Flash Lite
> handles email classification reliably — gets context, urgency, and intent right
> $0.10 per million input tokens, $0.40 output — costs almost nothing at this scale
> free tier covers up to 1,000 requests/day, which is more than enough here
> no laptop dependency — Pi calls the API directly and works standalone
> this is the default
