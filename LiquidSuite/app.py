"""
LSuite - Main Application Entry Point
Run with: python app.py or flask run
"""
import os
from lsuite import create_app
from lsuite.extensions import db
from lsuite.models import (
    User, GoogleCredential, EmailStatement, BankTransaction,
    TransactionCategory, ERPNextConfig, ERPNextSyncLog
)

# Create app instance
app = create_app(os.getenv('FLASK_ENV', 'development'))


@app.cli.command()
def init_db():
    """Initialize the database"""
    db.create_all()
    print('Database initialized!')


@app.cli.command()
def seed_categories():
    """Seed default transaction categories"""
    categories = [
        {
            'name': 'Transport',
            'erpnext_account': 'Transport Expenses - Company',
            'transaction_type': 'expense',
            'keywords': 'uber, bolt, taxi, transport, fuel, petrol'
        },
        {
            'name': 'Food & Beverages',
            'erpnext_account': 'Food Expenses - Company',
            'transaction_type': 'expense',
            'keywords': 'restaurant, coffee, lunch, dinner, food, cafe'
        },
        {
            'name': 'Office Supplies',
            'erpnext_account': 'Office Expenses - Company',
            'transaction_type': 'expense',
            'keywords': 'stationery, office, supplies, printer'
        },
        {
            'name': 'Utilities',
            'erpnext_account': 'Utilities - Company',
            'transaction_type': 'expense',
            'keywords': 'electricity, water, internet, mobile, telkom'
        },
        {
            'name': 'Salary Payment',
            'erpnext_account': 'Salary - Company',
            'transaction_type': 'expense',
            'keywords': 'salary, wages, payment'
        },
        {
            'name': 'Customer Payment',
            'erpnext_account': 'Sales - Company',
            'transaction_type': 'income',
            'keywords': 'payment received, deposit, income'
        },
        {
            'name': 'Bank Transfer',
            'erpnext_account': 'Bank Account - Company',
            'transaction_type': 'transfer',
            'keywords': 'transfer, own account'
        }
    ]
    
    for cat_data in categories:
        if not TransactionCategory.query.filter_by(name=cat_data['name']).first():
            category = TransactionCategory(**cat_data)
            db.session.add(category)
    
    db.session.commit()
    print(f'Seeded {len(categories)} categories!')


@app.cli.command()
def create_admin():
    """Create an admin user"""
    import getpass
    
    email = input('Admin email: ')
    username = input('Admin username: ')
    password = getpass.getpass('Admin password: ')
    
    if User.query.filter_by(email=email).first():
        print('User with this email already exists!')
        return
    
    user = User(
        email=email,
        username=username,
        is_admin=True
    )
    user.set_password(password)
    
    db.session.add(user)
    db.session.commit()
    
    print(f'Admin user {username} created successfully!')


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
