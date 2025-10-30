#!/usr/bin/env python
"""
Database Migration Script
Run this to initialize and manage database migrations
"""
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask_migrate import Migrate, init, migrate, upgrade
from app import app
from lsuite.extensions import db


def init_migrations():
    """Initialize migrations directory"""
    print("Initializing migrations...")
    with app.app_context():
        init()
    print("✓ Migrations initialized")


def create_migration(message="Auto migration"):
    """Create a new migration"""
    print(f"Creating migration: {message}")
    with app.app_context():
        migrate(message=message)
    print("✓ Migration created")


def apply_migrations():
    """Apply all pending migrations"""
    print("Applying migrations...")
    with app.app_context():
        upgrade()
    print("✓ Migrations applied")


def main():
    if len(sys.argv) < 2:
        print("Usage: python migrate.py [init|create|upgrade]")
        print("  init    - Initialize migrations directory")
        print("  create  - Create a new migration")
        print("  upgrade - Apply all pending migrations")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "init":
        init_migrations()
    elif command == "create":
        message = sys.argv[2] if len(sys.argv) > 2 else "Auto migration"
        create_migration(message)
    elif command == "upgrade":
        apply_migrations()
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
