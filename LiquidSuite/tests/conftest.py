"""
Pytest Configuration and Fixtures
Place this in: LiquidSuite/tests/conftest.py
"""
import pytest
import os
import sys
from datetime import datetime, date

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lsuite import create_app
from lsuite.extensions import db
from lsuite.models import (
    User, TransactionCategory, GoogleCredential,
    EmailStatement, BankTransaction, ERPNextConfig
)


@pytest.fixture(scope='session')
def app():
    """Create and configure a test Flask application"""
    app = create_app('testing')
    
    with app.app_context():
        # Create all tables
        db.create_all()
        
        # Seed test data
        seed_test_data()
        
        yield app
        
        # Cleanup
        db.session.remove()
        db.drop_all()


@pytest.fixture(scope='function')
def client(app):
    """Create test client for each test"""
    return app.test_client()


@pytest.fixture(scope='function')
def runner(app):
    """Create test CLI runner"""
    return app.test_cli_runner()


@pytest.fixture(scope='function')
def auth_client(client, app):
    """Create authenticated test client"""
    with app.app_context():
        user = User.query.filter_by(email='test@example.com').first()
        if not user:
            user = User(
                username='testuser',
                email='test@example.com'
            )
            user.set_password('testpassword')
            db.session.add(user)
            db.session.commit()
    
    # Login
    client.post('/auth/login', data={
        'email': 'test@example.com',
        'password': 'testpassword'
    }, follow_redirects=True)
    
    return client


@pytest.fixture(scope='function')
def sample_statement(app):
    """Create a sample email statement"""
    with app.app_context():
        statement = EmailStatement(
            gmail_id=f'test_statement_{datetime.now().timestamp()}',
            subject='Test Bank Statement',
            sender='test@bank.com',
            date=datetime.utcnow(),
            bank_name='test'
        )
        db.session.add(statement)
        db.session.commit()
        
        yield statement
        
        # Cleanup
        db.session.delete(statement)
        db.session.commit()


@pytest.fixture(scope='function')
def sample_transactions(app, sample_statement):
    """Create sample transactions"""
    with app.app_context():
        transactions = [
            BankTransaction(
                statement_id=sample_statement.id,
                date=date.today(),
                description='Uber ride to office',
                amount=50.00,
                transaction_type='debit'
            ),
            BankTransaction(
                statement_id=sample_statement.id,
                date=date.today(),
                description='Restaurant lunch payment',
                amount=120.00,
                transaction_type='debit'
            ),
            BankTransaction(
                statement_id=sample_statement.id,
                date=date.today(),
                description='Payment received from client',
                amount=5000.00,
                transaction_type='credit'
            )
        ]
        
        for trans in transactions:
            db.session.add(trans)
        
        db.session.commit()
        
        yield transactions
        
        # Cleanup
        for trans in transactions:
            db.session.delete(trans)
        db.session.commit()


def seed_test_data():
    """Seed test database with initial data"""
    # Create test user
    if not User.query.filter_by(email='test@example.com').first():
        user = User(
            username='testuser',
            email='test@example.com',
            is_admin=False
        )
        user.set_password('testpassword')
        db.session.add(user)
    
    # Create admin user
    if not User.query.filter_by(email='admin@example.com').first():
        admin = User(
            username='admin',
            email='admin@example.com',
            is_admin=True
        )
        admin.set_password('adminpassword')
        db.session.add(admin)
    
    # Create test categories
    categories_data = [
        {
            'name': 'Test Transport',
            'erpnext_account': 'Transport Expenses - Test',
            'transaction_type': 'expense',
            'keywords': 'uber, taxi, bolt, transport'
        },
        {
            'name': 'Test Food',
            'erpnext_account': 'Food Expenses - Test',
            'transaction_type': 'expense',
            'keywords': 'restaurant, food, lunch, dinner'
        },
        {
            'name': 'Test Income',
            'erpnext_account': 'Sales - Test',
            'transaction_type': 'income',
            'keywords': 'payment received, deposit, client payment'
        }
    ]
    
    for cat_data in categories_data:
        if not TransactionCategory.query.filter_by(name=cat_data['name']).first():
            category = TransactionCategory(**cat_data)
            db.session.add(category)
    
    db.session.commit()


@pytest.fixture(autouse=True)
def reset_db(app):
    """Reset database between tests"""
    yield
    
    with app.app_context():
        # Don't delete users and categories (needed for tests)
        # Only delete transactions and statements
        BankTransaction.query.delete()
        EmailStatement.query.delete()
        db.session.commit()
