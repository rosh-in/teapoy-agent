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

I tried 3 small language models locally before deciding to use Gemini 2.5 Flash Lite as the model. 
<br><br>Since my Pi Zero 2W only has 512MB RAM, I ran these models on my laptop and the Pi made HTTP calls to an Ollama server on my laptop for inference.

### Gemma 3:4B
Good output quality for my specific needs, but requires 4GB RAM minimum. That made it impractical for a 24/7 running email agent like mine.

### Gemma 2:2B
Ran fine on 2GB RAM, which made it a better option given my limited resources. But it often fell apart when emails needed any judgment or the tone was even slightly complex.

### LFM 2.5:1.2B
Lightweight enough to run locally on a Pi 4 or Pi 5 (it needs around 1GB RAM, so it can't run on my Pi Zero). But it's made to be a tool-calling model and isn't that suited for text generation. So it's far less suitable for my needs, although it can be run locally on a better Pi.

---

It's promising to see single-purpose models moving toward being small enough to run on a Raspberry Pi locally. I'll hopefully find one worth switching to.
