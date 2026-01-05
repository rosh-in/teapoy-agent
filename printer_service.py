#!/usr/bin/env python3
"""
PI2PRINTER Thermal Printer Service
Minimal, clean printer interface for Mission Impossible briefings
"""

import os
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
    # Try importing bluetooth module (optional)
    import bluetooth
    HAS_BLUETOOTH = True
except ImportError:
    HAS_BLUETOOTH = False

from escpos.exceptions import USBNotFoundError
import textwrap
import threading
import subprocess
import time

try:
    # Import audio config if available
    from pi_config import AUDIO_CONFIG, AUDIO_TRIGGER
except Exception:
    AUDIO_CONFIG = {
        'enabled': False,
        'audio_file': 'audio/mission_impossible.mp3',
        'pulse_sink': None,
        'pre_print_lead_seconds': 1.0,
    }


# Fallback for webhook trigger if config import fails
try:
    AUDIO_TRIGGER
except NameError:
    AUDIO_TRIGGER = { 'enabled': False, 'webhook_url': None, 'lead_seconds': 1.0 }

class MissionAudioManager:
    """Lightweight audio manager that plays an audio file to PulseAudio (Echo sink).
    Uses paplay/aplay via subprocess to avoid heavy dependencies. Plays async.
    """
    def __init__(self, cfg: dict):
        self.cfg = cfg or {}

    def _play(self):
        audio = self.cfg.get('audio_file')
        if not audio:
            return
        sink = self.cfg.get('pulse_sink')
        # Prefer paplay when available (PulseAudio-native). Fallback to aplay using pulse device.
        if sink:
            cmd = [
                'bash','-lc',
                f"command -v paplay >/dev/null 2>&1 && paplay --device={sink} '{audio}' || aplay -D pulse '{audio}'"
            ]
        else:
            cmd = [
                'bash','-lc',
                "command -v paplay >/dev/null 2>&1 && paplay '"+audio+"' || aplay -D pulse '"+audio+"'"
            ]
        import subprocess as sp
        try:
            sp.Popen(cmd, stdout=sp.DEVNULL, stderr=sp.DEVNULL)
        except Exception:
            pass

    def play_mission_theme_async(self, lead_seconds: float = 0.0):
        if not self.cfg.get('enabled', False):
            return
        import threading, time as _t
        def runner():
            if lead_seconds > 0:
                _t.sleep(lead_seconds)
            self._play()
        t = threading.Thread(target=runner, daemon=True)
        t.start()


class BluetoothDirectPrinter:
    """Direct Bluetooth socket printer (raw socket connection like imf_test_task.py)"""
    def __init__(self, mac_address: str, port: int = 1):
        self.mac_address = mac_address
        self.port = port
        self.sock = None
        self.connected = False
    
    def open(self):
        """Connect to Bluetooth printer"""
        if not hasattr(socket, "AF_BLUETOOTH"):
            raise Exception("Socket module not available")
        
        if self.connected:
            return
            
        self.sock = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
        self.sock.settimeout(10)  # 10 second timeout
        self.sock.connect((self.mac_address, self.port))
        self.connected = True
    
    def text(self, text_data: str):
        """Send text to printer using raw socket (same as your working test)"""
        if not self.connected:
            self.open()
        
        # Initialize printer (same as your working test)
        self.sock.send(b'\x1B\x40')  # ESC @ - Initialize printer
        
        # Send text data line by line
        for line in text_data.split('\n'):
            self.sock.send(line.encode('utf-8') + b'\n')
    
    def cut(self):
        """Cut paper (same command as your working test)"""
        if self.connected and self.sock:
            self.sock.send(b'\x1D\x56\x41\x10')  # GS V A - Cut paper
    
    def close(self):
        """Close connection"""
        if self.sock:
            try:
                self.sock.close()
            except:
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
        """Initialize connection to thermal printer (prioritize working direct Bluetooth)"""
        
        # 1. Try Direct Bluetooth FIRST (your working method)
        # Use your specific MAC address if not provided
        bluetooth_addr = self.bluetooth_addr or "60:6E:41:15:4A:EE"
        
        if bluetooth_addr and hasattr(socket, "AF_BLUETOOTH"):
            try:
                # Try direct Bluetooth socket connection (same as your test script)
                self.printer = BluetoothDirectPrinter(bluetooth_addr)
                # Store configuration for use during printing
                print(f"✅ Bluetooth printer configured: {bluetooth_addr}")
                return
            except Exception as e:
                print(f"❌ Direct Bluetooth failed: {e}")
                # Don't try serial over Bluetooth - it doesn't work with your printer
                pass
        
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
            common_serial_ports = ['/dev/ttyUSB0', '/dev/ttyUSB1', '/dev/ttyAMA0', '/dev/serial0']
            for port in common_serial_ports:
                try:
                    if os.path.exists(port):
                        self.printer = Serial(port, baudrate=9600)
                        return
                except Exception:
                    continue
        
        # 7. Fallback to file output
        if self.fallback_to_file:
            self.printer = File("printed_missions.txt")
        else:
            self.printer = Dummy()
    
    def format_mission_briefing(self, analysis: Dict[str, Any], agent_name: str = "Agent") -> str:
        """Format mission briefing for thermal printing"""
        if not analysis.get('has_task'):
            return None
        
        mission = analysis['mission_briefing']
        
        # Text wrapping helper
        def wrap_text(text: str, width: int = self.print_width) -> str:
            lines = []
            for paragraph in text.split('\n'):
                if paragraph.strip():
                    wrapped = textwrap.fill(paragraph, width=width)
                    lines.append(wrapped)
                else:
                    lines.append('')
            return '\n'.join(lines)
        
        # Format deadline
        deadline_str = mission.get('deadline', 'ASAP')
        if deadline_str and deadline_str != 'ASAP':
            deadline_str = f"DEADLINE: {deadline_str}"
        else:
            deadline_str = "DEADLINE: ASAP"
        
        # Build briefing
        lines = []
        lines.append("=" * self.print_width)
        lines.append("    MISSION BRIEFING")
        lines.append("=" * self.print_width)
        lines.append("")
        lines.append(f"AGENT: {agent_name}")
        lines.append(f"URGENCY: {mission['urgency']}")
        lines.append(f"TIME: {datetime.now().strftime('%H:%M %d/%m/%Y')}")
        lines.append("")
        lines.append("MISSION:")
        lines.append(wrap_text(mission['title']))
        lines.append("")
        
        # People involved (if any)
        people = mission.get('people_involved', [])
        if people and isinstance(people, list) and len(people) > 0:
            lines.append("PEOPLE INVOLVED:")
            lines.append(wrap_text(", ".join(people)))
            lines.append("")
        
        lines.append("YOUR MISSION, SHOULD YOU")
        lines.append("CHOOSE TO ACCEPT IT:")
        lines.append(wrap_text(mission['action_required']))
        lines.append("")
        lines.append("*** THIS MESSAGE WILL")
        lines.append("    SELF-DESTRUCT ***")
        lines.append("")
        lines.append(deadline_str)
        lines.append("")
        lines.append("=" * self.print_width)
        lines.append(f"MISSION ID: {mission['mission_id']}")
        lines.append("=" * self.print_width)
        
        return '\n'.join(lines)
    
    def format_receipt(self, receipt_data: Dict[str, Any]) -> str:
        """Format personal message as a simple ticket/bill"""
        width = self.print_width
        
        def center(text, w=width):
            return text.center(w)
        
        def bold(text):
            return f'\x1B\x45\x01{text}\x1B\x45\x00'  # ESC E 1 (bold on) ... ESC E 0 (bold off)
        
        lines = []
        
        # Header - simple and clean
        lines.append(center("================================"))
        lines.append(center(bold("TICKET")))
        lines.append(center("================================"))
        lines.append("")
        
        # Date/Time/From 
        from datetime import datetime
        now = datetime.now()
        date_str = now.strftime("%Y-%m-%d")
        time_str = now.strftime("%I:%M %p")  # 12-hour format with AM/PM
        
        lines.append(f"{bold('Date')}: {date_str}")
        lines.append(f"{bold('Time')}: {time_str}")
        
        # Extract sender name
        sender_name = receipt_data.get('customer_name', 'UNKNOWN')
        lines.append(f"{bold('From')}: u/{sender_name}")
        lines.append("-" * width)
        lines.append("")
        
        # Message content
        for item in receipt_data.get('items', []):
            message_text = item.get('name', '')
            # Word wrap the message
            wrapped_lines = textwrap.fill(message_text, width=width)
            lines.append(wrapped_lines)
        
        lines.append("")
        lines.append("-" * width)
        lines.append(center("Thank you!"))
        lines.append("")
        
        return '\n'.join(lines)
    
    def print_receipt(self, receipt_data: Dict[str, Any]) -> bool:
        """Print personal message receipt"""
        if not self.printer:
            print("❌ No printer available")
            return False
            
        receipt_text = self.format_receipt(receipt_data)
        
        try:
            print(f"🖨️ Printing receipt via {self.get_printer_info()}...")
            
            # For Bluetooth direct printer, ensure connection if not open
            # (Note: we rely on printer state or open it here)
            if isinstance(self.printer, BluetoothDirectPrinter):
                if not self.printer.connected:
                    self.printer.open()
                
            self.printer.text(receipt_text + "\n\n\n")
            self.printer.cut()
            
            if isinstance(self.printer, BluetoothDirectPrinter):
                self.printer.close()
                
            return True
        except Exception as e:
            print(f"❌ Print receipt failed: {e}")
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
            # Fire webhook BEFORE printing (non-blocking)
            try:
                if AUDIO_TRIGGER.get('enabled') and AUDIO_TRIGGER.get('webhook_url'):
                    _fire_webhook_async(
                        AUDIO_TRIGGER.get('webhook_url'),
                        {'event':'mission_print','source':'pi2printer'},
                        float(AUDIO_TRIGGER.get('lead_seconds', 0.0))
                    )
            except Exception:
                pass
            # Schedule STOP webhook after duration (non-blocking)
            try:
                if AUDIO_TRIGGER.get('enabled') and AUDIO_TRIGGER.get('stop_webhook_url'):
                    _fire_webhook_async(
                        AUDIO_TRIGGER.get('stop_webhook_url'),
                        {'event':'mission_stop','source':'pi2printer'},
                        float(AUDIO_TRIGGER.get('lead_seconds', 0.0)) + float(AUDIO_TRIGGER.get('play_duration_seconds', 25.0))
                    )
            except Exception:
                pass
            # Start theme BEFORE printing (non-blocking)
            try:
                audio_mgr = MissionAudioManager(AUDIO_CONFIG)
                audio_mgr.play_mission_theme_async(
                    lead_seconds=float(AUDIO_CONFIG.get('pre_print_lead_seconds', 0.0))
                )
            except Exception as _e:
                pass
            
            # For Bluetooth direct printer, ensure connection
            if isinstance(self.printer, BluetoothDirectPrinter):
                if not self.printer.connected:
                    self.printer.open()
            
            # Print the briefing
            self.printer.text(briefing_text)
            
            # Try to cut paper
            try:
                self.printer.cut()
                print("✅ Mission printed and cut successfully")
            except Exception as cut_error:
                print(f"⚠️ Print succeeded but cut failed: {cut_error}")
                # Add manual separator for printers without cut support
                self.printer.text('\n' + '─' * self.print_width + '\n\n')
            
            # Close Bluetooth connection to free it up
            if isinstance(self.printer, BluetoothDirectPrinter):
                self.printer.close()
                
            return True
            
        except Exception as e:
            print(f"❌ Printing failed: {e}")
            return False
    
    def get_printer_info(self):
        """Get printer type"""
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
            except:
                pass


import threading
import subprocess
import time

try:
    # Import audio config if available
    from pi_config import AUDIO_CONFIG, AUDIO_TRIGGER
except Exception:
    AUDIO_CONFIG = {
        'enabled': False,
        'audio_file': 'audio/mission_impossible.mp3',
        'pulse_sink': None,
        'pre_print_lead_seconds': 1.0,
    }

import json as _json
import urllib.request as _ur

def _fire_webhook_async(url: str, payload: dict, delay: float = 0.0):
    """Fire webhook in a daemon thread with 1 retry, debounce and simple logging."""
    import threading as _th, time as _t, json as _json, urllib.request as _ur, urllib.error as _ue, os as _os
    # Simple debounce via module-level state
    global _last_webhook_ts
    try:
        _last_webhook_ts
    except NameError:
        _last_webhook_ts = 0.0
    def _go():
        global _last_webhook_ts
        try:
            cd = float(AUDIO_TRIGGER.get('cooldown_seconds', 0.0)) if isinstance(AUDIO_TRIGGER, dict) else 0.0
        except Exception:
            cd = 0.0
        now = _t.time()
        if cd and (now - _last_webhook_ts) < cd:
            return
        if delay and delay > 0:
            _t.sleep(delay)
        if not url:
            return
        body = _json.dumps(payload or {}).encode('utf-8')
        req = _ur.Request(url, data=body, headers={'Content-Type': 'application/json'})
        codes = []
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
            _t.sleep(1.0)
            code = _send()
        # Log
        try:
            line = f"WEBHOOK {{int(_t.time())}} code={{code}} payload={{payload}}\n"
            with open('printed_missions.txt','a') as f:
                f.write(line)
        except Exception:
            pass
        _last_webhook_ts = _t.time()
    _th.Thread(target=_go, daemon=True).start()
