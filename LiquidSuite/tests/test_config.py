"""
Pytest Configuration and Fixtures
"""
import pytest
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lsuite import create_app
from lsuite.extensions import db
from lsuite.models import User, TransactionCategory


@pytest.fixture
def app():
    """Create and configure a test Flask application"""
    app = create_app('testing')
    
    with app.app_context():
        db.create_all()
        
        # Seed test data
        seed_test_data()
        
        yield app
        
        # Cleanup
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Create test client"""
    return app.test_client()


@pytest.fixture
def runner(app):
    """Create test CLI runner"""
    return app.test_cli_runner()


@pytest.fixture
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


def seed_test_data():
    """Seed test database with initial data"""
    # Create test user
    user = User(
        username='testuser',
        email='test@example.com',
        is_admin=False
    )
    user.set_password('testpassword')
    db.session.add(user)
    
    # Create admin user
    admin = User(
        username='admin',
        email='admin@example.com',
        is_admin=True
    )
    admin.set_password('adminpassword')
    db.session.add(admin)
    
    # Create test categories
    categories = [
        TransactionCategory(
            name='Test Transport',
            erpnext_account='Transport Expenses - Test',
            transaction_type='expense',
            keywords='uber, taxi, bolt'
        ),
        TransactionCategory(
            name='Test Food',
            erpnext_account='Food Expenses - Test',
            transaction_type='expense',
            keywords='restaurant, food, lunch'
        ),
        TransactionCategory(
            name='Test Income',
            erpnext_account='Sales - Test',
            transaction_type='income',
            keywords='payment received, deposit'
        )
    ]
    
    for category in categories:
        db.session.add(category)
    
    db.session.commit()
