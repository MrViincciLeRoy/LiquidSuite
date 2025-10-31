#!/usr/bin/env python
"""
Database Initialization Script
Initializes the database schema for LSuite application
"""
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lsuite import create_app
from lsuite.extensions import db
from lsuite.models import (
    User, GoogleCredential, EmailStatement, BankTransaction,
    TransactionCategory, ERPNextConfig, ERPNextSyncLog
)


def init_database():
    """Initialize database tables"""
    print("🔧 Initializing LSuite Database...")
    print("=" * 50)
    
    # Create app context
    app = create_app(os.getenv('FLASK_ENV', 'development'))
    
    with app.app_context():
        print("\n📊 Creating database tables...")
        
        try:
            # Create all tables
            db.create_all()
            
            print("✅ Database tables created successfully!")
            print("\nCreated tables:")
            print("  - users")
            print("  - google_credentials")
            print("  - email_statements")
            print("  - bank_transactions")
            print("  - transaction_categories")
            print("  - erpnext_configs")
            print("  - erpnext_sync_logs")
            
            # Verify tables
            inspector = db.inspect(db.engine)
            tables = inspector.get_table_names()
            
            print(f"\n✓ Total tables created: {len(tables)}")
            
            return True
            
        except Exception as e:
            print(f"\n❌ Error creating database: {str(e)}")
            return False


def drop_database():
    """Drop all database tables (WARNING: Destructive)"""
    print("⚠️  WARNING: This will delete all data!")
    confirm = input("Type 'DELETE ALL DATA' to confirm: ")
    
    if confirm != 'DELETE ALL DATA':
        print("❌ Aborted. No changes made.")
        return
    
    app = create_app(os.getenv('FLASK_ENV', 'development'))
    
    with app.app_context():
        print("\n🗑️  Dropping all tables...")
        db.drop_all()
        print("✅ All tables dropped successfully!")


def reset_database():
    """Drop and recreate database"""
    print("🔄 Resetting Database...")
    print("=" * 50)
    
    app = create_app(os.getenv('FLASK_ENV', 'development'))
    
    with app.app_context():
        print("\n🗑️  Dropping existing tables...")
        db.drop_all()
        print("✅ Tables dropped")
        
        print("\n📊 Creating fresh tables...")
        db.create_all()
        print("✅ Tables created")
        
        print("\n✅ Database reset complete!")


def check_database():
    """Check database connection and tables"""
    print("🔍 Checking Database Status...")
    print("=" * 50)
    
    app = create_app(os.getenv('FLASK_ENV', 'development'))
    
    with app.app_context():
        try:
            # Test connection
            db.session.execute(db.text('SELECT 1'))
            print("\n✅ Database connection: OK")
            
            # Get table info
            inspector = db.inspect(db.engine)
            tables = inspector.get_table_names()
            
            print(f"✅ Tables found: {len(tables)}")
            
            if tables:
                print("\nExisting tables:")
                for table in sorted(tables):
                    print(f"  - {table}")
                    
                # Count records
                print("\nRecord counts:")
                print(f"  Users: {User.query.count()}")
                print(f"  Categories: {TransactionCategory.query.count()}")
                print(f"  Statements: {EmailStatement.query.count()}")
                print(f"  Transactions: {BankTransaction.query.count()}")
                print(f"  ERPNext Configs: {ERPNextConfig.query.count()}")
            else:
                print("\n⚠️  No tables found. Run init to create them.")
            
            return True
            
        except Exception as e:
            print(f"\n❌ Database error: {str(e)}")
            return False


def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("LSuite Database Management")
        print("=" * 50)
        print("\nUsage: python init_db.py [command]")
        print("\nCommands:")
        print("  init    - Initialize database (create tables)")
        print("  drop    - Drop all tables (WARNING: destructive)")
        print("  reset   - Drop and recreate all tables")
        print("  check   - Check database status")
        print("\nExamples:")
        print("  python scripts/init_db.py init")
        print("  python scripts/init_db.py check")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    if command == 'init':
        success = init_database()
        sys.exit(0 if success else 1)
    elif command == 'drop':
        drop_database()
    elif command == 'reset':
        reset_database()
    elif command == 'check':
        success = check_database()
        sys.exit(0 if success else 1)
    else:
        print(f"❌ Unknown command: {command}")
        print("Run 'python init_db.py' for usage information")
        sys.exit(1)


if __name__ == '__main__':
    main()
