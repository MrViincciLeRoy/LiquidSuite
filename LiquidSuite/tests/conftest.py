# ============================================================================
# tests/conftest.py - MINIMAL FIX - DON'T BREAK WORKING TESTS
# ============================================================================
"""
Pytest configuration and fixtures
"""
import pytest
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lsuite import create_app
from lsuite.extensions import db as _db
from lsuite.models import User, BankAccount, TransactionCategory, BankTransaction
from datetime import date
from decimal import Decimal


@pytest.fixture(scope='session')
def app():
    """Create application for testing"""
    os.environ['FLASK_ENV'] = 'testing'
    os.environ['TESTING'] = 'true'
    
    app = create_app('testing')
    
    with app.app_context():
        yield app


@pytest.fixture(scope='session')
def db(app):
    """Create database for testing"""
    with app.app_context():
        _db.drop_all()
        _db.create_all()
        yield _db
        _db.session.remove()
        _db.drop_all()


@pytest.fixture
def client(app):
    """Create test client"""
    return app.test_client()


@pytest.fixture
def test_user(app, db):
    """Create test user"""
    with app.app_context():
        user = User(
            username='testuser',
            email='test@example.com',
            first_name='Test',
            last_name='User',
            is_active=True
        )
        user.set_password('testpassword123')
        db.session.add(user)
        db.session.commit()
        yield user


@pytest.fixture
def test_bank_account(app, db, test_user):
    """Create test bank account"""
    with app.app_context():
        account = BankAccount(
            user_id=test_user.id,
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
        yield account


@pytest.fixture
def test_categories(app, db):
    """Create test categories"""
    with app.app_context():
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


@pytest.fixture
def test_transactions(app, db, test_user, test_bank_account):
    """Create test transactions"""
    with app.app_context():
        transactions = [
            BankTransaction(
                user_id=test_user.id,
                bank_account_id=test_bank_account.id,
                date=date(2024, 1, 1),
                description='UBER TRIP TO AIRPORT',
                withdrawal=Decimal('250.00'),
                deposit=Decimal('0.00'),
                balance=Decimal('5000.00'),
                reference_number='TXN001'
            ),
            BankTransaction(
                user_id=test_user.id,
                bank_account_id=test_bank_account.id,
                date=date(2024, 1, 2),
                description='STARBUCKS COFFEE SHOP',
                withdrawal=Decimal('45.00'),
                deposit=Decimal('0.00'),
                balance=Decimal('4955.00'),
                reference_number='TXN002'
            ),
            BankTransaction(
                user_id=test_user.id,
                bank_account_id=test_bank_account.id,
                date=date(2024, 1, 3),
                description='MONTHLY BANK FEE',
                withdrawal=Decimal('65.00'),
                deposit=Decimal('0.00'),
                balance=Decimal('4890.00'),
                reference_number='TXN003'
            ),
            BankTransaction(
                user_id=test_user.id,
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
