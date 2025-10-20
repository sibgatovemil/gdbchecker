#!/usr/bin/env python3
"""Initialize database schema"""

from models import init_database
import time
import sys

def wait_for_db():
    """Wait for database to be ready"""
    max_retries = 30
    retry_count = 0

    while retry_count < max_retries:
        try:
            init_database()
            print("Database connection successful!")
            return True
        except Exception as e:
            retry_count += 1
            print(f"Waiting for database... ({retry_count}/{max_retries})")
            time.sleep(2)

    print("Failed to connect to database after maximum retries")
    sys.exit(1)

if __name__ == '__main__':
    wait_for_db()
