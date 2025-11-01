# ============================================================================
# LiquidSuite/tests/conftest.py - FIXED VERSION
# ============================================================================
"""
Pytest Configuration and Fixtures
"""
import sys
import os
import pytest

# Add the parent directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from lsuite import create_app
from lsuite.extensions import db
from lsuite.models import User, TransactionCategory


@pytest.fixture(scope='function')
def app():
    """Create and configure a test application instance."""
    app = create_app('testing')
    
    # Disable CSRF for testing
    app.config['WTF_CSRF_ENABLED'] = False
    
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture(scope='function')
def client(app):
    """Create a test client for the app."""
    return app.test_client()


@pytest.fixture(scope='function')
def runner(app):
    """Create a test CLI runner."""
    return app.test_cli_runner()


@pytest.fixture(scope='function')
def user(app):
    """Create a test user."""
    with app.app_context():
        test_user = User(
            username='testuser',
            email='test@example.com'
        )
        test_user.set_password('testpassword')
        test_user.is_active = True
        
        db.session.add(test_user)
        db.session.commit()
        
        # Refresh to get the ID
        db.session.refresh(test_user)
        
        yield test_user
        
        # Cleanup is handled by app fixture dropping all tables


@pytest.fixture(scope='function')
def auth_client(client, app, user):
    """Create an authenticated test client."""
    # FIXED: Use app context and pass user fixture
    with app.app_context():
        # Log in the user using the client
        response = client.post('/auth/login', data={
            'email': user.email,
            'password': 'testpassword',
            'remember_me': False
        }, follow_redirects=True)
        
        # Verify login was successful
        #assert response.status_code == 200
    
    yield client
    
    # Logout after test
    with app.app_context():
        client.get('/auth/logout', follow_redirects=True)


@pytest.fixture(scope='function')
def sample_categories(app):
    """Create sample transaction categories for testing"""
    with app.app_context():
        categories = [
            TransactionCategory(
                name='Test Transport',
                erpnext_account='Transport - Test',
                transaction_type='expense',
                keywords='uber,taxi,bolt,ride,transport',
                active=True
            ),
            TransactionCategory(
                name='Test Food',
                erpnext_account='Food & Dining - Test',
                transaction_type='expense',
                keywords='restaurant,food,lunch,dinner,meal,eat',
                active=True
            ),
            TransactionCategory(
                name='Test Income',
                erpnext_account='Income - Test',
                transaction_type='income',
                keywords='payment received,salary,income,revenue,client',
                active=True
            )
        ]
        
        for category in categories:
            db.session.add(category)
        
        db.session.commit()
        
        yield categories
        


@pytest.fixture(scope='function')
def reset_db(app):
    """Reset the database before each test."""
    with app.app_context():
        db.drop_all()
        db.create_all()
    yield
    with app.app_context():
        db.session.remove()
        db.drop_all()
# ============================================================================
# ADD THESE FIXTURES TO THE END OF YOUR EXISTING conftest.py
# DO NOT REPLACE - JUST ADD TO THE BOTTOM
# ============================================================================

from lsuite.models import BankAccount, BankTransaction
from datetime import date
from decimal import Decimal


@pytest.fixture(scope='function')
def test_bank_account(app, user):
    """Create a test bank account for transactions"""
    with app.app_context():
        account = BankAccount(
            user_id=user.id,
            account_name='Test Savings Account',
            account_number='1234567890',
            bank_name='Test Bank',
            account_type='Savings',
            currency='ZAR',
            balance=Decimal('10000.00'),
            is_active=True
        )
        db.session.add(account)
        db.session.commit()
        db.session.refresh(account)
        
        yield account


@pytest.fixture(scope='function')
def test_categories(app, sample_categories):
    """Reuse existing sample_categories but with specific test names"""
    with app.app_context():
        # Clear existing and create specific ones for bridge tests
        TransactionCategory.query.delete()
        
        categories = [
            TransactionCategory(
                name='Transport',
                erpnext_account='Transport Expenses - Company',
                transaction_type='expense',
                keywords='uber, taxi, fuel, petrol',
                active=True
            ),
            TransactionCategory(
                name='Food',
                erpnext_account='Food Expenses - Company',
                transaction_type='expense',
                keywords='restaurant, coffee, lunch',
                active=True
            ),
            TransactionCategory(
                name='Bank Fees',
                erpnext_account='Bank Charges - Company',
                transaction_type='expense',
                keywords='bank fee, service charge',
                active=True
            )
        ]
        
        for cat in categories:
            db.session.add(cat)
        db.session.commit()
        
        yield categories


@pytest.fixture(scope='function')
def test_transactions(app, user, test_bank_account):
    """Create test transactions for bridge tests"""
    with app.app_context():
        transactions = [
            BankTransaction(
                user_id=user.id,
                bank_account_id=test_bank_account.id,
                date=date(2024, 1, 1),
                description='UBER TRIP TO AIRPORT',
                withdrawal=Decimal('250.00'),
                deposit=Decimal('0.00'),
                balance=Decimal('5000.00'),
                reference_number='TXN001'
            ),
            BankTransaction(
                user_id=user.id,
                bank_account_id=test_bank_account.id,
                date=date(2024, 1, 2),
                description='STARBUCKS COFFEE SHOP',
                withdrawal=Decimal('45.00'),
                deposit=Decimal('0.00'),
                balance=Decimal('4955.00'),
                reference_number='TXN002'
            ),
            BankTransaction(
                user_id=user.id,
                bank_account_id=test_bank_account.id,
                date=date(2024, 1, 3),
                description='MONTHLY BANK FEE',
                withdrawal=Decimal('65.00'),
                deposit=Decimal('0.00'),
                balance=Decimal('4890.00'),
                reference_number='TXN003'
            ),
            BankTransaction(
                user_id=user.id,
                bank_account_id=test_bank_account.id,
                date=date(2024, 1, 4),
                description='UNKNOWN TRANSACTION',
                withdrawal=Decimal('100.00'),
                deposit=Decimal('0.00'),
                balance=Decimal('4790.00'),
                reference_number='TXN004'
            )
        ]
        
        for txn in transactions:
            db.session.add(txn)
        db.session.commit()
        
        yield transactions
