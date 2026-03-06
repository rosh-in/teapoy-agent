#!/usr/bin/env python3
"""Pi2Printer Configuration - Hardware and System Settings"""

import os
from dotenv import load_dotenv

load_dotenv()

# Detect if running on Raspberry Pi
def is_raspberry_pi():
    try:
        with open('/proc/cpuinfo', 'r') as f:
            cpuinfo = f.read()
        return 'Raspberry Pi' in cpuinfo or 'BCM' in cpuinfo
    except:
        return False

IS_PI = is_raspberry_pi()

# Printer Configuration
PRINTER_CONFIG = {
    'usb': {
        'enabled': False,
        'vendor_id': None,  # Auto-detect
        'product_id': None  # Auto-detect
    },
    'bluetooth': {
        'enabled': True,
        'address': '60:6E:41:15:4A:EE',
        'port': '/dev/rfcomm0',
        'baudrate': 9600,
        'direct_socket': True
    },
    'serial': {
        'enabled': True,
        'port': '/dev/ttyUSB0',
        'baudrate': 9600,
        'timeout': 1
    },
    'network': {
        'enabled': False,
        'host': None,
        'port': 9100
    }
}

# Performance configuration based on Pi model
PERFORMANCE_CONFIG = {
    'check_interval_minutes': 10 if IS_PI else 5,
    'max_emails_per_check': 10 if IS_PI else 20,
    'gemini_timeout': 60 if IS_PI else 30,
    'enable_logging': True,
    'log_level': 'INFO'
}

# Pi-specific optimizations
PI_OPTIMIZATIONS = {
    'gpu_mem_split': 16,
    'disable_camera': True,
    'disable_bluetooth': False,
    'enable_uart': True,
    'reduce_cpu_freq': False
}

# Auto-configure based on Pi model
try:
    with open('/proc/device-tree/model', 'r') as f:
        model = f.read()
        if 'Pi Zero' in model:
            PERFORMANCE_CONFIG['check_interval_minutes'] = 15
            PERFORMANCE_CONFIG['max_emails_per_check'] = 5
            PI_OPTIMIZATIONS['reduce_cpu_freq'] = True
        elif 'Pi 4' in model:
            PERFORMANCE_CONFIG['check_interval_minutes'] = 5
            PERFORMANCE_CONFIG['max_emails_per_check'] = 20
except FileNotFoundError:
    pass

# System paths
SYSTEM_PATHS = {
    'log_dir': '/var/log/pi2printer' if IS_PI else './logs',
    'data_dir': '/var/lib/pi2printer' if IS_PI else './data',
    'config_dir': '/etc/pi2printer' if IS_PI else './config',
    'systemd_service': '/etc/systemd/system/pi2printer.service'
}

def get_printer_config():
    """Get printer configuration with fallback"""
    return {
        'fallback_to_file': not any([
            PRINTER_CONFIG['usb']['enabled'],
            PRINTER_CONFIG['bluetooth']['enabled'],
            PRINTER_CONFIG['serial']['enabled'],
            PRINTER_CONFIG['network']['enabled']
        ]),
        'bluetooth_addr': PRINTER_CONFIG['bluetooth']['address'],
        'serial_port': PRINTER_CONFIG['serial']['port'],
        'network_host': PRINTER_CONFIG['network']['host']
    }

def get_performance_config():
    """Get performance settings"""
    return PERFORMANCE_CONFIG.copy()

# Environment variable overrides
ENV_VARS = {
    'check_interval': 'PI2PRINTER_CHECK_INTERVAL',
    'log_level': 'PI2PRINTER_LOG_LEVEL',
    'max_emails': 'PI2PRINTER_MAX_EMAILS'
}

# Load webhooks from environment
AUDIO_TRIGGER = {
    'enabled': True,
    'webhook_url': os.getenv('ZAPIER_WEBHOOK_URL', ''),
    'stop_webhook_url': os.getenv('ZAPIER_STOP_WEBHOOK_URL', ''),
    'lead_seconds': 5.0,
    'play_duration_seconds': 28.0,
}

AUDIO_TRIGGER['cooldown_seconds'] = 5


# ------------------------------------------------------------
# Identity
# ------------------------------------------------------------
AGENT_NAME = os.getenv('AGENT_NAME', 'Roshin')

# ------------------------------------------------------------
# Quiet Hours (24-hour local time)
# Printing is deferred during this window; missions still created in DB.
# ------------------------------------------------------------
QUIET_START = int(os.getenv('QUIET_START', '22'))  # 10 PM default
QUIET_END   = int(os.getenv('QUIET_END',   '6'))   #  6 AM default

if __name__ == '__main__':
    print(f"Running on Raspberry Pi: {IS_PI}")
    if IS_PI:
        print(f"Check interval: {PERFORMANCE_CONFIG['check_interval_minutes']} minutes")
        print(f"Max emails per check: {PERFORMANCE_CONFIG['max_emails_per_check']}")
    
    enabled_types = [k for k, v in PRINTER_CONFIG.items() if v.get('enabled')]
    print(f"Enabled printer types: {', '.join(enabled_types) if enabled_types else 'None (fallback to file)'}")
    
    config = get_printer_config()
    print(f"Fallback to file: {config['fallback_to_file']}")
