#!/usr/bin/env python3
# filepath: /home/joseph/Desktop/QuickSheet/config.py
"""
Configuration settings for the QuickSheet application.
Separating configuration from code improves maintainability and security.
"""

import os
import datetime
import secrets

# Base directory of the application
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Server settings
SERVER = {
    'host': '0.0.0.0',
    'port': 8080,
    'debug': True  # Set to False in production
}

# Flask app configuration
APP = {
    'secret_key': secrets.token_hex(16),  # Generate a secure random secret key for sessions
    'session_type': 'filesystem',
    'session_cookie_httponly': True,
    'session_cookie_secure': False,  # Set to True in production with HTTPS
    'permanent_session_lifetime': datetime.timedelta(minutes=30)
}

# Data storage configuration
DATA = {
    'dir': os.path.join(BASE_DIR, 'data'),
    'orders_file': 'orders.json',
    'topics_file': 'topics.json'
}

# Admin credentials (Consider moving to environment variables in production)
ADMIN = {
    'username': 'admin',
    'password': 'admin123'
}

# Logging configuration
LOGGING = {
    'level': 'DEBUG',
    'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
}