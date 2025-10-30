#!/usr/bin/env python
"""
Seed Transaction Categories Script
Populates the database with default transaction categories
"""
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lsuite import create_app
from lsuite.extensions import db
from lsuite.models import TransactionCategory


# Default categories with common South African expense patterns
DEFAULT_CATEGORIES = [
    {
        'name': 'Transport & Fuel',
        'erpnext_account': 'Transport Expenses - Company',
        'transaction_type': 'expense',
        'keywords': 'uber, bolt, taxi, transport, fuel, petrol, diesel, garage, shell, engen, bp, total, sasol',
        'color': 1,  # Blue
        'active': True
    },
    {
        'name': 'Food & Beverages',
        'erpnext_account': 'Food & Beverage Expenses - Company',
        'transaction_type': 'expense',
        'keywords': 'restaurant, coffee, lunch, dinner, food, cafe, starbucks, mugg & bean, nandos, kfc, mcdonalds, steers, pizza, spur, ocean basket, woolworths food',
        'color': 2,  # Green
        'active': True
    },
    {
        'name': 'Office Supplies',
        'erpnext_account': 'Office Supplies - Company',
        'transaction_type': 'expense',
        'keywords': 'stationery, office, supplies, printer, paper, ink, makro, waltons, office national, croxley',
        'color': 3,  # Yellow
        'active': True
    },
    {
        'name': 'Utilities',
        'erpnext_account': 'Utilities - Company',
        'transaction_type': 'expense',
        'keywords': 'electricity, water, internet, mobile, telkom, vodacom, mtn, cell c, eskom, municipality, city of',
        'color': 4,  # Orange
        'active': True
    },
    {
        'name': 'Telecommunications',
        'erpnext_account': 'Telecommunications - Company',
        'transaction_type': 'expense',
        'keywords': 'airtime, data, cell phone, mobile, telkom, vodacom, mtn, cell c, phone contract',
        'color': 5,  # Purple
        'active': True
    },
    {
        'name': 'Software & Subscriptions',
        'erpnext_account': 'Software Expenses - Company',
        'transaction_type': 'expense',
        'keywords': 'software, subscription, saas, microsoft, office 365, adobe, dropbox, google workspace, hosting, domain',
        'color': 6,  # Cyan
        'active': True
    },
    {
        'name': 'Bank Charges & Fees',
        'erpnext_account': 'Bank Charges - Company',
        'transaction_type': 'expense',
        'keywords': 'bank fee, bank charge, service fee, monthly fee, transaction fee, atm fee, account fee',
        'color': 7,  # Red
        'active': True
    },
    {
        'name': 'Professional Fees',
        'erpnext_account': 'Professional Fees - Company',
        'transaction_type': 'expense',
        'keywords': 'lawyer, attorney, accountant, consultant, professional services, legal fees, audit',
        'color': 8,  # Pink
        'active': True
    },
    {
        'name': 'Marketing & Advertising',
        'erpnext_account': 'Marketing Expenses - Company',
        'transaction_type': 'expense',
        'keywords': 'marketing, advertising, facebook ads, google ads, social media, promotion, campaign',
        'color': 9,  # Teal
        'active': True
    },
    {
        'name': 'Insurance',
        'erpnext_account': 'Insurance - Company',
        'transaction_type': 'expense',
        'keywords': 'insurance, premium, cover, policy, old mutual, discovery, sanlam, momentum',
        'color': 10,  # Indigo
        'active': True
    },
    {
        'name': 'Rent & Lease',
        'erpnext_account': 'Rent - Company',
        'transaction_type': 'expense',
        'keywords': 'rent, lease, rental, office space, property',
        'color': 11,  # Brown
        'active': True
    },
    {
        'name': 'Repairs & Maintenance',
        'erpnext_account': 'Repairs & Maintenance - Company',
        'transaction_type': 'expense',
        'keywords': 'repair, maintenance, fix, service, plumber, electrician, handyman',
        'color': 12,  # Gray
        'active': True
    },
    {
        'name': 'Salaries & Wages',
        'erpnext_account': 'Salaries - Company',
        'transaction_type': 'expense',
        'keywords': 'salary, wage, payment, payroll, staff, employee',
        'color': 13,  # Dark Blue
        'active': True
    },
    {
        'name': 'Customer Payments',
        'erpnext_account': 'Sales - Company',
        'transaction_type': 'income',
        'keywords': 'payment received, deposit, income, customer payment, invoice payment, receipt',
        'color': 14,  # Lime
        'active': True
    },
    {
        'name': 'Interest Income',
        'erpnext_account': 'Interest Income - Company',
        'transaction_type': 'income',
        'keywords': 'interest earned, interest credit, bank interest',
        'color': 15,  # Light Blue
        'active': True
    },
    {
        'name': 'Bank Transfers',
        'erpnext_account': 'Bank Account - Company',
        'transaction_type': 'transfer',
        'keywords': 'transfer, own account, internal transfer, move funds, between accounts',
        'color': 16,  # Light Gray
        'active': True
    },
    {
        'name': 'Entertainment',
        'erpnext_account': 'Entertainment - Company',
        'transaction_type': 'expense',
        'keywords': 'entertainment, cinema, movies, theatre, event, tickets, ster kinekor, nu metro',
        'color': 17,  # Magenta
        'active': True
    },
    {
        'name': 'Training & Development',
        'erpnext_account': 'Training Expenses - Company',
        'transaction_type': 'expense',
        'keywords': 'training, course, education, learning, workshop, seminar, udemy, coursera',
        'color': 18,  # Amber
        'active': True
    },
    {
        'name': 'Shipping & Courier',
        'erpnext_account': 'Shipping Expenses - Company',
        'transaction_type': 'expense',
        'keywords': 'courier, shipping, delivery, postnet, aramex, dhl, fedex, post office',
        'color': 19,  # Deep Orange
        'active': True
    },
    {
        'name': 'Miscellaneous',
        'erpnext_account': 'Miscellaneous Expenses - Company',
        'transaction_type': 'expense',
        'keywords': 'miscellaneous, other, general, sundry',
        'color': 20,  # Blue Gray
        'active': True
    }
]


def seed_categories(overwrite=False):
    """Seed transaction categories"""
    print("🌱 Seeding Transaction Categories...")
    print("=" * 50)
    
    app = create_app(os.getenv('FLASK_ENV', 'development'))
    
    with app.app_context():
        added = 0
        skipped = 0
        updated = 0
        
        for cat_data in DEFAULT_CATEGORIES:
            existing = TransactionCategory.query.filter_by(
                name=cat_data['name']
            ).first()
            
            if existing:
                if overwrite:
                    # Update existing category
                    existing.erpnext_account = cat_data['erpnext_account']
                    existing.transaction_type = cat_data['transaction_type']
                    existing.keywords = cat_data['keywords']
                    existing.color = cat_data.get('color')
                    existing.active = cat_data.get('active', True)
                    updated += 1
                    print(f"  🔄 Updated: {cat_data['name']}")
                else:
                    skipped += 1
                    print(f"  ⏭️  Skipped: {cat_data['name']} (already exists)")
            else:
                # Create new category
                category = TransactionCategory(
                    name=cat_data['name'],
                    erpnext_account=cat_data['erpnext_account'],
                    transaction_type=cat_data['transaction_type'],
                    keywords=cat_data['keywords'],
                    color=cat_data.get('color'),
                    active=cat_data.get('active', True)
                )
                db.session.add(category)
                added += 1
                print(f"  ✅ Added: {cat_data['name']}")
        
        try:
            db.session.commit()
            
            print("\n" + "=" * 50)
            print("📊 Summary:")
            print(f"  ✅ Added: {added}")
            print(f"  🔄 Updated: {updated}")
            print(f"  ⏭️  Skipped: {skipped}")
            print(f"  📋 Total: {len(DEFAULT_CATEGORIES)}")
            print("\n✅ Categories seeded successfully!")
            
            return True
            
        except Exception as e:
            db.session.rollback()
            print(f"\n❌ Error seeding categories: {str(e)}")
            return False


def list_categories():
    """List all categories in database"""
    print("📋 Transaction Categories")
    print("=" * 50)
    
    app = create_app(os.getenv('FLASK_ENV', 'development'))
    
    with app.app_context():
        categories = TransactionCategory.query.order_by(
            TransactionCategory.name
        ).all()
        
        if not categories:
            print("\n⚠️  No categories found. Run 'seed' command first.")
            return
        
        print(f"\n✅ Found {len(categories)} categories:\n")
        
        for cat in categories:
            status = "✓" if cat.active else "✗"
            print(f"  [{status}] {cat.name}")
            print(f"      Account: {cat.erpnext_account}")
            print(f"      Type: {cat.transaction_type}")
            print(f"      Keywords: {cat.keywords[:60]}...")
            print(f"      Transactions: {cat.transactions.count()}")
            print()


def delete_all_categories():
    """Delete all categories (WARNING: Destructive)"""
    print("⚠️  WARNING: This will delete all categories!")
    confirm = input("Type 'DELETE ALL CATEGORIES' to confirm: ")
    
    if confirm != 'DELETE ALL CATEGORIES':
        print("❌ Aborted. No changes made.")
        return
    
    app = create_app(os.getenv('FLASK_ENV', 'development'))
    
    with app.app_context():
        print("\n🗑️  Deleting all categories...")
        
        # Check for transactions
        categories_with_trans = []
        for cat in TransactionCategory.query.all():
            if cat.transactions.count() > 0:
                categories_with_trans.append(cat.name)
        
        if categories_with_trans:
            print("\n⚠️  These categories have transactions:")
            for name in categories_with_trans:
                print(f"  - {name}")
            print("\nCannot delete categories in use.")
            return
        
        count = TransactionCategory.query.delete()
        db.session.commit()
        
        print(f"✅ Deleted {count} categories")


def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("LSuite Category Management")
        print("=" * 50)
        print("\nUsage: python seed_categories.py [command]")
        print("\nCommands:")
        print("  seed      - Add default categories (skip existing)")
        print("  update    - Update all categories (overwrite existing)")
        print("  list      - List all categories in database")
        print("  delete    - Delete all categories (WARNING: destructive)")
        print("\nExamples:")
        print("  python scripts/seed_categories.py seed")
        print("  python scripts/seed_categories.py list")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    if command == 'seed':
        success = seed_categories(overwrite=False)
        sys.exit(0 if success else 1)
    elif command == 'update':
        success = seed_categories(overwrite=True)
        sys.exit(0 if success else 1)
    elif command == 'list':
        list_categories()
    elif command == 'delete':
        delete_all_categories()
    else:
        print(f"❌ Unknown command: {command}")
        print("Run 'python seed_categories.py' for usage information")
        sys.exit(1)


if __name__ == '__main__':
    main()
