#!/usr/bin/env python3
"""
PI2PRINTER Thermal Printer Service
Formats and prints Mission Impossible briefings on physical thermal printer
"""

import os
import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from escpos.printer import Usb, File, Dummy
from escpos.exceptions import USBNotFoundError, BarcodeTypeError
import textwrap

class PrinterService:
    def __init__(self, vendor_id: int = None, product_id: int = None, fallback_to_file: bool = True):
        """
        Initialize printer service with physical USB thermal printer
        
        Args:
            vendor_id: USB vendor ID (will auto-detect if None)
            product_id: USB product ID (will auto-detect if None) 
            fallback_to_file: Use file output if USB printer not found
        """
        self.printer = None
        self.fallback_to_file = fallback_to_file
        self.print_width = 32  # Characters per line for 58mm paper
        
        self._initialize_printer(vendor_id, product_id)
    
    def _initialize_printer(self, vendor_id: int = None, product_id: int = None):
        """Initialize connection to physical USB thermal printer"""
        print("🖨️  Connecting to USB thermal printer...")
        
        # If specific IDs provided, try those first
        if vendor_id and product_id:
            try:
                self.printer = Usb(vendor_id, product_id, 0)
                print(f"   ✅ Connected to thermal printer ({hex(vendor_id)}, {hex(product_id)})")
                return
            except USBNotFoundError:
                print(f"   ⚠️  Printer not found at {hex(vendor_id)}, {hex(product_id)}")
        
        # Auto-detect common thermal printer USB IDs
        print("   🔍 Auto-detecting thermal printer...")
        common_thermal_printers = [
            # Epson thermal printers
            (0x04b8, 0x0202, "Epson TM series"),
            (0x04b8, 0x0e15, "Epson TM-T20"),
            (0x04b8, 0x0e28, "Epson TM-T20II"),
            (0x04b8, 0x0e27, "Epson TM-T20III"),
            (0x04b8, 0x0e2a, "Epson TM-T82"),
            
            # Star thermal printers
            (0x0519, 0x0001, "Star TSP100"),
            (0x0519, 0x0003, "Star TSP143"),
            
            # Generic POS/thermal printers
            (0x0fe6, 0x811e, "ITP Printer"),
            (0x28e9, 0x0289, "Generic POS Printer"),
            (0x1fc9, 0x2016, "Generic Thermal Printer"),
            (0x1659, 0x8965, "Thermal Printer"),
            
            # Citizen thermal printers
            (0x1d90, 0x2168, "Citizen CT-S310"),
            (0x1d90, 0x2174, "Citizen CT-S4000"),
            
            # Bixolon thermal printers  
            (0x1504, 0x0006, "Bixolon SRP-275"),
            (0x1504, 0x0011, "Bixolon SRP-350"),
        ]
        
        for vendor_id, product_id, name in common_thermal_printers:
            try:
                print(f"   🔍 Trying {name}...")
                printer = Usb(vendor_id, product_id, 0)
                # Test if we can actually open it
                printer.open()
                printer.close()
                self.printer = printer
                print(f"   ✅ Connected to {name} ({hex(vendor_id)}:{hex(product_id)})")
                return
            except (USBNotFoundError, Exception) as e:
                print(f"   ⚠️  {name} not accessible: {e}")
                continue
        
        # If no printer found, handle fallback
        print("   ❌ No thermal printer detected via USB")
        if self.fallback_to_file:
            print("   📄 Falling back to file output for testing")
            self.printer = File("printed_missions.txt")
            print("   ✅ File printer ready - check printed_missions.txt for output")
        else:
            print("   ❌ No printer available - using dummy printer")
            self.printer = Dummy()
    
    def test_printer(self):
        """Test printer connection and basic functionality"""
        if not self.printer:
            print("❌ No printer initialized")
            return False
        
        try:
            print("🧪 Testing printer...")
            
            # Test basic text printing
            self.printer.text("🧪 PRINTER TEST\n")
            self.printer.text("=" * self.print_width + "\n")
            self.printer.text("PI2PRINTER SYSTEM CHECK\n")
            self.printer.text(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
            self.printer.text("-" * self.print_width + "\n")
            self.printer.text("If you can read this clearly,\n")
            self.printer.text("your thermal printer is\n")
            self.printer.text("working correctly!\n")
            self.printer.text("=" * self.print_width + "\n")
            
            # Test formatting
            try:
                self.printer.set('emphasized', True)  # Bold
                self.printer.text("BOLD TEXT TEST\n")
                self.printer.set('emphasized', False)
                
                self.printer.set(align='center')
                self.printer.text("CENTERED TEXT\n")
                self.printer.set(align='left')
            except:
                self.printer.text("FORMATTING TEST COMPLETE\n")
            
            # Try to cut paper (might not work on all printers)
            try:
                self.printer.cut()
                print("   ✅ Paper cut successful")
            except:
                self.printer.text("\n" + "─" * 10 + " CUT HERE " + "─" * 10 + "\n\n")
                print("   ⚠️  Auto-cut not supported, added cut line")
            
            print("✅ Printer test completed successfully!")
            return True
            
        except Exception as e:
            print(f"❌ Printer test failed: {e}")
            return False
    
    def format_mission_briefing(self, analysis: Dict[str, Any], agent_name: str = "Agent") -> str:
        """Format mission briefing for thermal printing with Mission Impossible style"""
        if not analysis.get('has_task'):
            return None
        
        mission = analysis['mission_briefing']
        
        # Helper function to wrap text properly
        def wrap_text(text: str, width: int = self.print_width) -> str:
            lines = []
            for paragraph in text.split('\n'):
                if paragraph.strip():
                    wrapped = textwrap.fill(paragraph, width=width)
                    lines.append(wrapped)
                else:
                    lines.append('')
            return '\n'.join(lines)
        
        # Calculate deadline display
        deadline_str = mission.get('deadline', 'ASAP')
        if deadline_str and deadline_str != 'ASAP':
            deadline_str = f"DEADLINE: {deadline_str}"
        else:
            deadline_str = "DEADLINE: ASAP"
        
        # Build the mission briefing
        lines = []
        
        # Header with border
        lines.append("=" * self.print_width)
        lines.append("  🎯 MISSION BRIEFING 🎯")
        lines.append("=" * self.print_width)
        lines.append("")
        
        # Basic mission info
        lines.append(f"AGENT: {agent_name}")
        lines.append(f"URGENCY: {mission['urgency']}")
        lines.append(f"TIME: {datetime.now().strftime('%H:%M %d/%m/%Y')}")
        lines.append("")
        
        # Mission title
        lines.append("MISSION:")
        lines.append(wrap_text(mission['title']))
        lines.append("")
        
        # Intelligence report  
        lines.append("INTELLIGENCE REPORT:")
        lines.append(wrap_text(mission['context']))
        lines.append("")
        
        # People involved (if any)
        people = mission.get('people_involved', [])
        if people and isinstance(people, list) and len(people) > 0:
            lines.append("PEOPLE INVOLVED:")
            lines.append(wrap_text(", ".join(people)))
            lines.append("")
        
        # Action required
        lines.append("YOUR MISSION, SHOULD YOU")
        lines.append("CHOOSE TO ACCEPT IT:")
        lines.append(wrap_text(mission['action_required']))
        lines.append("")
        
        # Warning and self-destruct
        lines.append("⚠️  THIS MESSAGE WILL")
        lines.append("    SELF-DESTRUCT")
        lines.append("")
        lines.append(deadline_str)
        lines.append("")
        
        # Mission ID footer
        lines.append("=" * self.print_width)
        lines.append(f"MISSION ID: {mission['mission_id']}")
        lines.append("=" * self.print_width)
        
        return '\n'.join(lines)
    
    def print_mission(self, analysis: Dict[str, Any], agent_name: str = "Agent") -> bool:
        """Print Mission Impossible briefing on thermal printer"""
        if not self.printer:
            print("❌ No printer available")
            return False
        
        briefing_text = self.format_mission_briefing(analysis, agent_name)
        if not briefing_text:
            print("📋 No actionable mission to print")
            return False
        
        try:
            print("🖨️  Printing mission briefing...")
            
            # Print the formatted briefing text
            self.printer.text(briefing_text)
            
            # Final formatting and cut
            try:
                self.printer.cut()
            except:
                self.printer.text('\n' + '─' * self.print_width + '\n\n')
            
            print("✅ Mission briefing printed successfully!")
            return True
            
        except Exception as e:
            print(f"❌ Print failed: {e}")
            return False
    
    def get_printer_info(self):
        """Get information about connected printer"""
        if isinstance(self.printer, Usb):
            return "USB Thermal Printer connected"
        elif isinstance(self.printer, File):
            return "File output mode (printed_missions.txt)"
        elif isinstance(self.printer, Dummy):
            return "No printer connected (dummy mode)"
        else:
            return "Unknown printer type"
    
    def close(self):
        """Close printer connection"""
        if self.printer:
            try:
                self.printer.close()
                print("🖨️  Printer connection closed")
            except:
                pass

def test_printer_with_mission():
    """Test the printer with a sample mission"""
    print("🧪 Testing thermal printer with sample mission...")
    
    # Initialize printer
    printer = PrinterService(fallback_to_file=True)
    
    print(f"📄 Printer status: {printer.get_printer_info()}")
    
    # Basic printer test
    printer.test_printer()
    
    # Test mission printing
    sample_analysis = {
        'has_task': True,
        'mission_briefing': {
            'mission_id': 'MI-TEST001',
            'title': 'Verify Unauthorized Warp Login Attempt',
            'urgency': 'HIGH',
            'deadline': 'ASAP',
            'action_required': 'Click the provided "Sign in to Warp" link IF and ONLY IF you initiated this login request. Otherwise, ignore the email and report suspicious activity.',
            'context': 'An unauthorized attempt to sign into your Warp account has been detected. This is a security alert requiring immediate verification. Failure to act could compromise your account.',
            'people_involved': ['security@warp.dev']
        }
    }
    
    success = printer.print_mission(sample_analysis, "Agent Roshin")
    
    if success:
        print("🎉 Mission printing test successful!")
        if isinstance(printer.printer, File):
            print("   Check printed_missions.txt to see the formatted output")
    
    printer.close()

if __name__ == '__main__':
    test_printer_with_mission()