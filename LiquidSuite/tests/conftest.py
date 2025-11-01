# ============================================================================
# tests/conftest.py - COMPLETE WORKING VERSION
# ============================================================================
"""
Pytest configuration and fixtures for LSuite tests
"""
import pytest
import os
import sys
from datetime import date
from decimal import Decimal

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lsuite import create_app
from lsuite.extensions import db as _db
from lsuite.models import User, BankAccount, BankTransaction, TransactionCategory


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


@pytest.fixture(scope='function', autouse=True)
def session(app, db):
    """Create a new database session for each test"""
    with app.app_context():
        connection = db.engine.connect()
        transaction = connection.begin()
        
        session_options = dict(bind=connection, binds={})
        session = db.create_scoped_session(options=session_options)
        
        db.session = session
        
        yield session
        
        session.remove()
        transaction.rollback()
        connection.close()


@pytest.fixture
def client(app):
    """Create test client"""
    return app.test_client()


@pytest.fixture
def runner(app):
    """Create test CLI runner"""
    return app.test_cli_runner()


@pytest.fixture
def test_user(app, db):
    """Create a test user"""
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
        db.session.refresh(user)
        
        yield user


@pytest.fixture
def test_admin_user(app, db):
    """Create a test admin user"""
    with app.app_context():
        admin = User(
            username='admin',
            email='admin@example.com',
            first_name='Admin',
            last_name='User',
            is_active=True,
            is_admin=True
        )
        admin.set_password('adminpassword123')
        
        db.session.add(admin)
        db.session.commit()
        db.session.refresh(admin)
        
        yield admin


@pytest.fixture
def test_bank_account(app, db, test_user):
    """Create a test bank account"""
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
        db.session.refresh(account)
        
        yield account


@pytest.fixture
def authenticated_client(client, test_user):
    """Create authenticated test client"""
    with client:
        client.post('/auth/login', data={
            'email': test_user.email,
            'password': 'testpassword123'
        }, follow_redirects=True)
        
        yield client


@pytest.fixture
def admin_client(client, test_admin_user):
    """Create authenticated admin client"""
    with client:
        client.post('/auth/login', data={
            'email': test_admin_user.email,
            'password': 'adminpassword123'
        }, follow_redirects=True)
        
        yield client


@pytest.fixture
def sample_transactions(app, db, test_user, test_bank_account):
    """Create sample transactions for testing"""
    with app.app_context():
        transactions = [
            BankTransaction(
                user_id=test_user.id,
                bank_account_id=test_bank_account.id,
                date=date(2024, 1, 1),
                description='SALARY DEPOSIT',
                deposit=Decimal('15000.00'),
                withdrawal=Decimal('0.00'),
                balance=Decimal('25000.00'),
                reference_number='SAL001'
            ),
            BankTransaction(
                user_id=test_user.id,
                bank_account_id=test_bank_account.id,
                date=date(2024, 1, 5),
                description='RENT PAYMENT',
                deposit=Decimal('0.00'),
                withdrawal=Decimal('8000.00'),
                balance=Decimal('17000.00'),
                reference_number='RENT001'
            ),
            BankTransaction(
                user_id=test_user.id,
                bank_account_id=test_bank_account.id,
                date=date(2024, 1, 10),
                description='GROCERY SHOPPING',
                deposit=Decimal('0.00'),
                withdrawal=Decimal('1500.00'),
                balance=Decimal('15500.00'),
                reference_number='GROC001'
            )
        ]
        
        for txn in transactions:
            db.session.add(txn)
        db.session.commit()
        
        for txn in transactions:
            db.session.refresh(txn)
        
        yield transactions


@pytest.fixture
def sample_categories(app, db):
    """Create sample transaction categories"""
    with app.app_context():
        categories = [
            TransactionCategory(
                name='Salaries',
                erpnext_account='Salaries - Company',
                transaction_type='income',
                keywords='salary, wages, payment',
                active=True
            ),
            TransactionCategory(
                name='Rent',
                erpnext_account='Rent - Company',
                transaction_type='expense',
                keywords='rent, lease, rental',
                active=True
            ),
            TransactionCategory(
                name='Groceries',
                erpnext_account='Food & Beverage - Company',
                transaction_type='expense',
                keywords='grocery, food, shopping, woolworths, checkers, pick n pay',
                active=True
            )
        ]
        
        for cat in categories:
            db.session.add(cat)
        db.session.commit()
        
        for cat in categories:
            db.session.refresh(cat)
        
        yield categories


# Helper functions for tests
def login(client, email, password):
    """Helper to log in a user"""
    return client.post('/auth/login', data={
        'email': email,
        'password': password
    }, follow_redirects=True)


def logout(client):
    """Helper to log out a user"""
    return client.get('/auth/logout', follow_redirects=True)
