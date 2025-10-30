# ============================================================================
# tests/conftest.py
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
def auth_client(client, user):
    """Create an authenticated test client."""
    # Log in the user
    client.post('/auth/login', data={
        'email': user.email,
        'password': 'testpassword',
        'remember_me': False
    }, follow_redirects=True)
    
    yield client
    
    # Logout after test
    client.get('/auth/logout', follow_redirects=True)


@pytest.fixture(scope='function')
def sample_categories(app):
    """Create sample transaction categories for testing"""
    with app.app_context():
        categories = [
            TransactionCategory(
                name='Test Transport',
                keywords='uber,taxi,bolt,ride,transport'
            ),
            TransactionCategory(
                name='Test Food',
                keywords='restaurant,food,lunch,dinner,meal,eat'
            ),
            TransactionCategory(
                name='Test Income',
                keywords='payment received,salary,income,revenue,client'
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
