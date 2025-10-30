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
from lsuite.models import User


@pytest.fixture(scope='function')
def app():
    """Create and configure a test application instance."""
    app = create_app('testing')
    
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
def reset_db(app):
    """Reset the database before each test."""
    with app.app_context():
        db.drop_all()
        db.create_all()
    yield
    with app.app_context():
        db.session.remove()
        db.drop_all()
"""```
**Alternative solution:** If the above doesn't work, you might need to check your project structure. Based on the error path, it looks like your structure is:

LiquidSuite/
├── LiquidSuite/
│   ├── lsuite/
│   │   ├── __init__.py
│   │   ├── models.py
│   │   └── ...
│   └── tests/
│       ├── conftest.py
│       └── test_auth.py''' """
