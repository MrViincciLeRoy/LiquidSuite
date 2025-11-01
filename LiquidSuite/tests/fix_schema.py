# ============================================================================
# FILE 6: LiquidSuite/scripts/fix_schema.py (NEW FILE)
# ============================================================================
#!/usr/bin/env python
"""
Fix Schema Script
Fixes database schema issues for existing deployments
"""
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text


def fix_database_schema():
    """Fix database schema issues"""
    print("🔧 Fixing Database Schema...")
    print("=" * 50)
    
    # Get database URL from environment
    db_url = os.getenv('DATABASE_URL') or os.getenv('SQLALCHEMY_DATABASE_URI')
    
    if not db_url:
        print("❌ DATABASE_URL not set!")
        return False
    
    # Fix postgres:// to postgresql:// for SQLAlchemy 2.x
    if db_url.startswith('postgres://'):
        db_url = db_url.replace('postgres://', 'postgresql://', 1)
        print("ℹ️  Converted postgres:// to postgresql://")
    
    try:
        engine = create_engine(db_url)
        
        with engine.connect() as conn:
            trans = conn.begin()
            
            try:
                print("\n1️⃣ Fixing ERPNextConfig table...")
                
                # Check if 'active' column exists (old schema)
                result = conn.execute(text("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'erpnext_configs' 
                    AND column_name = 'active'
                """))
                
                if result.fetchone():
                    print("   Renaming 'active' → 'is_active'...")
                    conn.execute(text("""
                        ALTER TABLE erpnext_configs 
                        RENAME COLUMN active TO is_active
                    """))
                    print("   ✅ Fixed!")
                else:
                    print("   ✅ Already correct!")
                
                print("\n2️⃣ Fixing BankTransaction table...")
                
                # Check current columns
                result = conn.execute(text("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'bank_transactions' 
                    AND column_name IN ('category', 'debits', 'credits', 'transaction_date')
                """))
                
                old_columns = [row[0] for row in result]
                
                if 'category' in old_columns:
                    print("   Fixing: category → category_id...")
                    conn.execute(text("""
                        ALTER TABLE bank_transactions 
                        DROP COLUMN category CASCADE
                    """))
                    conn.execute(text("""
                        ALTER TABLE bank_transactions 
                        ADD COLUMN category_id INTEGER
                    """))
                    conn.execute(text("""
                        ALTER TABLE bank_transactions 
                        ADD CONSTRAINT fk_bank_transactions_category_id 
                        FOREIGN KEY (category_id) 
                        REFERENCES transaction_categories(id) 
                        ON DELETE SET NULL
                    """))
                    print("   ✅ Fixed!")
                
                if 'debits' in old_columns:
                    print("   Fixing: debits/credits → withdrawal/deposit...")
                    conn.execute(text("""
                        ALTER TABLE bank_transactions 
                        RENAME COLUMN debits TO withdrawal
                    """))
                    conn.execute(text("""
                        ALTER TABLE bank_transactions 
                        RENAME COLUMN credits TO deposit
                    """))
                    print("   ✅ Fixed!")
                
                if 'transaction_date' in old_columns:
                    print("   Fixing: transaction_date → date...")
                    conn.execute(text("""
                        ALTER TABLE bank_transactions 
                        RENAME COLUMN transaction_date TO date
                    """))
                    print("   ✅ Fixed!")
                
                trans.commit()
                print("\n" + "=" * 50)
                print("✅ Schema fixes complete!")
                return True
                
            except Exception as e:
                trans.rollback()
                print(f"\n❌ Error during migration: {e}")
                import traceback
                traceback.print_exc()
                return False
                
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return False


if __name__ == '__main__':
    success = fix_database_schema()
    sys.exit(0 if success else 1)

