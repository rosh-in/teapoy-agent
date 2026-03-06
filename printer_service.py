#!/usr/bin/env python3
"""
PI2PRINTER Thermal Printer Service
Minimal, clean printer interface for Mission Impossible briefings
"""

import os
import json as _json
import urllib.request as _ur
import threading
import time
from datetime import datetime
from typing import Dict, Any, Optional
from escpos.printer import Usb, File, Dummy
try:
    from escpos.printer import Serial, Network
    HAS_SERIAL = True
except ImportError:
    HAS_SERIAL = False

# Import socket - always available
import socket

try:
    import bluetooth
    HAS_BLUETOOTH = True
except ImportError:
    HAS_BLUETOOTH = False

from escpos.exceptions import USBNotFoundError
import textwrap

# Webhook config - imported once at module level
try:
    from pi_config import AUDIO_TRIGGER
except Exception:
    AUDIO_TRIGGER = {'enabled': False, 'webhook_url': None, 'lead_seconds': 1.0}

# Ensure AUDIO_TRIGGER is always defined (guard against partial pi_config imports)
if 'AUDIO_TRIGGER' not in dir():
    AUDIO_TRIGGER = {'enabled': False, 'webhook_url': None, 'lead_seconds': 1.0}

# Module-level debounce timestamp for webhook calls
_last_webhook_ts: float = 0.0



class BluetoothDirectPrinter:
    """Direct Bluetooth socket printer (raw socket connection)"""
    def __init__(self, mac_address: str, port: int = 1):
        self.mac_address = mac_address
        self.port = port
        self.sock = None
        self.connected = False

    def open(self):
        """Connect to Bluetooth printer"""
        if not hasattr(socket, "AF_BLUETOOTH"):
            raise Exception("AF_BLUETOOTH not available on this platform")
        if self.connected:
            return
        self.sock = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
        self.sock.settimeout(10)
        self.sock.connect((self.mac_address, self.port))
        self.connected = True

    def text(self, text_data: str):
        """Send plain text to printer via raw socket"""
        if not self.connected:
            self.open()
        self.sock.send(b'\x1B\x40')  # ESC @ - Initialize printer
        for line in text_data.split('\n'):
            self.sock.send(line.encode('utf-8') + b'\n')

    def cut(self):
        """Cut paper"""
        if self.connected and self.sock:
            self.sock.send(b'\x1D\x56\x41\x10')  # GS V A

    def close(self):
        """Close connection"""
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass
            self.sock = None
            self.connected = False


class PrinterService:
    def __init__(self, vendor_id: int = None, product_id: int = None,
                 bluetooth_addr: str = None, serial_port: str = None,
                 network_host: str = None, fallback_to_file: bool = True):
        """Initialize printer service with multiple connection options"""
        self.printer = None
        self.fallback_to_file = fallback_to_file
        self.print_width = 32  # Characters per line for 58mm paper
        self.bluetooth_addr = bluetooth_addr
        self.serial_port = serial_port
        self.network_host = network_host
        self._initialize_printer(vendor_id, product_id)

    def _initialize_printer(self, vendor_id: int = None, product_id: int = None):
        """Initialize connection to thermal printer (prioritize Bluetooth)"""

        # 1. Try Direct Bluetooth FIRST
        bluetooth_addr = self.bluetooth_addr or "60:6E:41:15:4A:EE"
        if bluetooth_addr and hasattr(socket, "AF_BLUETOOTH"):
            try:
                self.printer = BluetoothDirectPrinter(bluetooth_addr)
                print(f"✅ Bluetooth printer configured: {bluetooth_addr}")
                return
            except Exception as e:
                print(f"❌ Direct Bluetooth failed: {e}")

        # 2. Try Serial port if provided
        if self.serial_port and HAS_SERIAL:
            try:
                self.printer = Serial(self.serial_port, baudrate=9600)
                return
            except Exception:
                pass

        # 3. Try Network printer if provided
        if self.network_host:
            try:
                self.printer = Network(self.network_host)
                return
            except Exception:
                pass

        # 4. Try specific USB IDs first
        if vendor_id and product_id:
            try:
                self.printer = Usb(vendor_id, product_id, 0)
                return
            except USBNotFoundError:
                pass

        # 5. Auto-detect common USB thermal printers
        common_thermal_printers = [
            (0x04b8, 0x0202, "Epson TM series"),
            (0x04b8, 0x0e15, "Epson TM-T20"),
            (0x04b8, 0x0e28, "Epson TM-T20II"),
            (0x04b8, 0x0e27, "Epson TM-T20III"),
            (0x04b8, 0x0e2a, "Epson TM-T82"),
            (0x0519, 0x0001, "Star TSP100"),
            (0x0519, 0x0003, "Star TSP143"),
            (0x0fe6, 0x811e, "ITP Printer"),
            (0x28e9, 0x0289, "Generic POS Printer"),
            (0x1fc9, 0x2016, "Generic Thermal Printer"),
            (0x1659, 0x8965, "Thermal Printer"),
            (0x1d90, 0x2168, "Citizen CT-S310"),
            (0x1d90, 0x2174, "Citizen CT-S4000"),
            (0x1504, 0x0006, "Bixolon SRP-275"),
            (0x1504, 0x0011, "Bixolon SRP-350"),
        ]
        for vid, pid, name in common_thermal_printers:
            try:
                printer = Usb(vid, pid, 0)
                printer.open()
                printer.close()
                self.printer = printer
                return
            except (USBNotFoundError, Exception):
                continue

        # 6. Try common serial ports (Pi-specific)
        if HAS_SERIAL:
            for port in ['/dev/ttyUSB0', '/dev/ttyUSB1', '/dev/ttyAMA0', '/dev/serial0']:
                try:
                    if os.path.exists(port):
                        self.printer = Serial(port, baudrate=9600)
                        return
                except Exception:
                    continue

        # 7. Fallback to file output
        if self.fallback_to_file:
            self.printer = File("webhook_log.txt")
        else:
            self.printer = Dummy()

    def format_mission_briefing(self, analysis: Dict[str, Any], agent_name: str = "Agent") -> str:
        """Format mission briefing for thermal printing"""
        if not analysis.get('has_task'):
            return None

        mission = analysis['mission_briefing']

        def wrap_text(text: str, width: int = self.print_width) -> str:
            lines = []
            for paragraph in text.split('\n'):
                if paragraph.strip():
                    lines.append(textwrap.fill(paragraph, width=width))
                else:
                    lines.append('')
            return '\n'.join(lines)

        deadline_str = mission.get('deadline') or ''
        deadline_label = "IMMEDIATE"
        if deadline_str and deadline_str.lower() not in ('null', 'none', 'asap', 'immediate', ''):
            try:
                from datetime import date as _date
                deadline_date = _date.fromisoformat(str(deadline_str)[:10])
                today = datetime.now().date()
                delta = (deadline_date - today).days
                if delta < 0:
                    deadline_label = f"{deadline_date.strftime('%a %d %b').upper()} — OVERDUE"
                elif delta == 0:
                    deadline_label = "EOD TODAY"
                elif delta == 1:
                    deadline_label = "EOD TOMORROW"
                elif delta <= 6:
                    deadline_label = f"IN {delta} DAYS — {deadline_date.strftime('%a %d %b').upper()}"
                else:
                    deadline_label = deadline_date.strftime('%a %d %b %Y').upper()
            except (ValueError, TypeError):
                deadline_label = str(deadline_str)

        codename = mission.get('title', 'MISSION BRIEFING')
        # Truncate and center the codename within print width
        codename_line = codename[:self.print_width].center(self.print_width)

        lines = []
        lines.append("=" * self.print_width)
        lines.append(codename_line)
        lines.append("=" * self.print_width)
        lines.append(mission['mission_id'].rjust(self.print_width))
        lines.append("")
        agent_label = f"AGENT: Agent {agent_name}"
        lines.append(agent_label + mission['urgency'].rjust(self.print_width - len(agent_label)))
        now = datetime.now()
        time_str = now.strftime('%H:%M ') + now.strftime('%a %d %b').upper()
        lines.append(time_str.rjust(self.print_width))
        lines.append("")

        people = mission.get('people_involved', [])
        if people and isinstance(people, list) and len(people) > 0:
            lines.append("PERSONS OF INTEREST:")
            for person in people:
                lines.append(f"- {person}"[:self.print_width])
            lines.append("")

        lines.append("YOUR MISSION, SHOULD YOU")
        lines.append("CHOOSE TO ACCEPT IT:")
        for _al in textwrap.fill(mission['action_required'], width=self.print_width - 2).split('\n'):
            lines.append(f"  {_al}")
        lines.append("")

        context = mission.get('context') or ''
        if context and context.lower() not in ('null', 'none', ''):
            lines.append("INTEL:")
            lines.append(wrap_text(context))

        lines.append(deadline_label.rjust(self.print_width))
        lines.append("=" * self.print_width)
        sd_pad = " " * ((self.print_width - len("*** THIS MESSAGE WILL")) // 2)
        lines.append(sd_pad + "*** THIS MESSAGE WILL")
        lines.append(sd_pad + "SELF-DESTRUCT ***")
        lines.append("=" * self.print_width)

        return '\n'.join(lines)

    def format_personal_note(self, message_note: Dict[str, Any]) -> str:
        """Format a personal/conversational message as a printed note."""
        width = self.print_width

        def wrap_text(text: str) -> str:
            return textwrap.fill(text, width=width)

        from_name = message_note.get('from_name', 'UNKNOWN').upper()
        summary = message_note.get('summary', '')

        lines = []
        lines.append("=" * width)
        lines.append("   INCOMING MESSAGE")
        lines.append("=" * width)
        lines.append("")
        lines.append(f"FROM: {from_name}")
        lines.append(f"TIME: {datetime.now().strftime('%H:%M %d/%m/%Y')}")
        lines.append("")
        lines.append(wrap_text(summary))
        lines.append("")
        lines.append("=" * width)

        return '\n'.join(lines)

    def print_personal_note(self, message_note: Dict[str, Any]) -> bool:
        """Print a personal/conversational message note"""
        if not self.printer:
            print("❌ No printer available")
            return False

        note_text = self.format_personal_note(message_note)
        try:
            print(f"🖨️ Printing personal note via {self.get_printer_info()}...")
            if isinstance(self.printer, BluetoothDirectPrinter):
                if not self.printer.connected:
                    self.printer.open()
            self.printer.text(note_text + "\n\n\n")
            self.printer.cut()
            if isinstance(self.printer, BluetoothDirectPrinter):
                self.printer.close()
            return True
        except Exception as e:
            print(f"❌ Print personal note failed: {e}")
            if isinstance(self.printer, BluetoothDirectPrinter):
                self.printer.close()
            return False

    def print_mission(self, analysis: Dict[str, Any], agent_name: str = "Agent") -> bool:
        if not self.printer:
            print("❌ No printer available")
            return False

        briefing_text = self.format_mission_briefing(analysis, agent_name)
        if not briefing_text:
            print("❌ No briefing text generated")
            return False

        try:
            print(f"🖨️ Printing mission via {self.get_printer_info()}...")

            # Fire start webhook immediately (non-blocking)
            try:
                if AUDIO_TRIGGER.get('enabled') and AUDIO_TRIGGER.get('webhook_url'):
                    _fire_webhook_async(
                        AUDIO_TRIGGER.get('webhook_url'),
                        {'event': 'mission_print', 'source': 'pi2printer'},
                        0.0
                    )
            except Exception:
                pass

            # Schedule stop webhook after track duration (non-blocking)
            try:
                if AUDIO_TRIGGER.get('enabled') and AUDIO_TRIGGER.get('stop_webhook_url'):
                    _fire_webhook_async(
                        AUDIO_TRIGGER.get('stop_webhook_url'),
                        {'event': 'mission_stop', 'source': 'pi2printer'},
                        float(AUDIO_TRIGGER.get('lead_seconds', 5.0)) + float(AUDIO_TRIGGER.get('play_duration_seconds', 25.0))
                    )
            except Exception:
                pass

            # Wait for music lead before printing
            lead_wait = float(AUDIO_TRIGGER.get('lead_seconds', 5.0))
            if AUDIO_TRIGGER.get('enabled') and lead_wait > 0:
                print(f"⏳ Waiting {lead_wait}s for music to start...")
                time.sleep(lead_wait)

            if isinstance(self.printer, BluetoothDirectPrinter):
                if not self.printer.connected:
                    self.printer.open()

            self.printer.text(briefing_text + "\n\n")

            try:
                self.printer.cut()
                print("✅ Mission printed and cut successfully")
            except Exception as cut_error:
                print(f"⚠️ Print succeeded but cut failed: {cut_error}")
                self.printer.text('\n' + '─' * self.print_width + '\n\n')

            if isinstance(self.printer, BluetoothDirectPrinter):
                self.printer.close()

            return True

        except Exception as e:
            print(f"❌ Printing failed: {e}")
            return False

    def get_printer_info(self) -> str:
        """Get printer type description"""
        if isinstance(self.printer, BluetoothDirectPrinter):
            return f"Bluetooth Printer ({self.printer.mac_address})"
        elif isinstance(self.printer, Usb):
            return "USB Thermal Printer"
        elif isinstance(self.printer, File):
            return "File Output"
        elif isinstance(self.printer, Dummy):
            return "No Printer"
        elif HAS_SERIAL and isinstance(self.printer, Serial):
            return "Serial Printer"
        elif hasattr(self.printer, '__class__') and 'Network' in str(self.printer.__class__):
            return "Network Printer"
        else:
            return "Unknown"

    def close(self):
        """Close printer connection"""
        if self.printer:
            try:
                self.printer.close()
            except Exception:
                pass


def _fire_webhook_async(url: str, payload: dict, delay: float = 0.0):
    """Fire a webhook in a daemon thread with 1 retry, debounce, and simple logging."""
    import urllib.error as _ue

    global _last_webhook_ts

    def _go():
        global _last_webhook_ts
        try:
            cd = float(AUDIO_TRIGGER.get('cooldown_seconds', 0.0)) if isinstance(AUDIO_TRIGGER, dict) else 0.0
        except Exception:
            cd = 0.0

        now = time.time()
        if cd and (now - _last_webhook_ts) < cd:
            return

        if delay and delay > 0:
            time.sleep(delay)

        if not url:
            return

        body = _json.dumps(payload or {}).encode('utf-8')
        req = _ur.Request(url, data=body, headers={'Content-Type': 'application/json'})

        def _send():
            try:
                with _ur.urlopen(req, timeout=2) as resp:
                    return resp.getcode()
            except _ue.HTTPError as e:
                return e.code
            except Exception:
                return None

        code = _send()
        if code is None or (code // 100) != 2:
            time.sleep(1.0)
            code = _send()

        try:
            line = f"WEBHOOK {int(time.time())} code={code} payload={payload}\n"
            with open('webhook_log.txt', 'a') as f:
                f.write(line)
        except Exception:
            pass

        _last_webhook_ts = time.time()

    threading.Thread(target=_go, daemon=True).start()
