# ============================================================================
# tests/test_auth.py
# ============================================================================
"""
Test Authentication Routes
"""
import pytest
from lsuite.models import User


def test_login_page(client):
    """Test login page loads"""
    response = client.get('/auth/login')
    assert response.status_code == 200
    assert b'Sign In' in response.data


def test_register_page(client):
    """Test registration page loads"""
    response = client.get('/auth/register')
    assert response.status_code == 200
    assert b'Register' in response.data


def test_successful_login(client, user):
    """Test successful login"""
    response = client.post('/auth/login', data={
        'email': user.email,
        'password': 'testpassword',
        'remember_me': False
    }, follow_redirects=True)
    
    assert response.status_code == 200
    assert b'Dashboard' in response.data


def test_failed_login_wrong_password(client, app, user):
    """Test login with wrong password"""
    # Create a user to attempt to log in as
    with app.app_context():
        # The test fixture `user` creates a user, so no need to do it here
        pass

    response = client.post('/auth/login', data={
        'email': user.email,
        'password': 'wrongpassword'
    }, follow_redirects=True)
    
    # Check flash message in the session and that the correct page is loaded
    with client.session_transaction() as sess:
        flashes = sess['_flashes']
        assert flashes and b'Invalid email or password' in flashes[0][1].encode('utf-8')
    assert b'Sign In' in response.data


def test_failed_login_nonexistent_user(client, app):
    """Test login with non-existent user"""
    response = client.post('/auth/login', data={
        'email': 'nonexistent@example.com',
        'password': 'password'
    }, follow_redirects=True)
    
    # Check flash message and final page
    with client.session_transaction() as sess:
        flashes = sess['_flashes']
        assert flashes and b'Invalid email or password' in flashes[0][1].encode('utf-8')
    assert b'Sign In' in response.data


def test_successful_registration(client, app):
    """Test successful user registration"""
    response = client.post('/auth/register', data={
        'username': 'newuser',
        'email': 'newuser@example.com',
        'password': 'password123',
        'password2': 'password123'
    }, follow_redirects=True)
    
    # Check flash message and verify user is created
    assert response.status_code == 200
    with client.session_transaction() as sess:
        flashes = sess['_flashes']
        assert flashes and b'Registration successful! Please log in.' in flashes[0][1].encode('utf-8')
    
    with app.app_context():
        user = User.query.filter_by(email='newuser@example.com').first()
        assert user is not None


def test_registration_duplicate_email(client, app, user):
    """Test registration with duplicate email"""
    response = client.post('/auth/register', data={
        'username': 'anotheruser',
        'email': 'test@example.com',  # Already exists from fixture
        'password': 'password123',
        'password2': 'password123'
    }) # No follow_redirects needed here, validation fails before redirect
    
    # Check that the validation error is present in the response data
    assert b'Email already registered. Please use another.' in response.data


def test_registration_password_mismatch(client):
    """Test registration with mismatched passwords"""
    response = client.post('/auth/register', data={
        'username': 'testuser2',
        'email': 'test2@example.com',
        'password': 'password123',
        'password2': 'differentpassword'
    })
    
    # Check that the validation error is present in the response data
    assert b'Passwords must match' in response.data


def test_logout(auth_client, app):
    """Test logout functionality"""
    response = auth_client.get('/auth/logout', follow_redirects=True)
    
    assert response.status_code == 200
    assert b'Sign In' in response.data
    with client.session_transaction() as sess:
        flashes = sess['_flashes']
        assert flashes and b'You have been logged out.' in flashes[0][1].encode('utf-8')


def test_protected_route_requires_login(client):
    """Test that protected routes redirect to login"""
    response = client.get('/gmail/statements')
    
    # Should redirect to login
    assert response.status_code == 302
    assert '/auth/login' in response.location


def test_profile_page(auth_client, user):
    """Test profile page for authenticated user"""
    response = auth_client.get('/auth/profile')
    
    assert response.status_code == 200
    assert b'Profile' in response.data
    assert b'testuser' in response.data


def test_profile_update(auth_client, app, user):
    """Test profile update"""
    with app.app_context():
        # Manually set original form values for validation
        user.username = 'testuser'
        user.email = 'test@example.com'
        
    response = auth_client.post('/auth/profile', data={
        'username': 'updateduser',
        'email': 'test@example.com'
    }, follow_redirects=True)
    
    with app.app_context():
        user = User.query.filter_by(email='test@example.com').first()
        assert user.username == 'updateduser'


def test_change_password(auth_client, app, user):
    """Test password change"""
    with app.app_context():
        # Ensure the user has the correct password set for the test
        user.set_password('testpassword')
        db.session.commit()

    response = auth_client.post('/auth/change-password', data={
        'current_password': 'testpassword',
        'new_password': 'newpassword123',
        'new_password2': 'newpassword123'
    }, follow_redirects=True)
    
    with app.app_context():
        user_in_db = User.query.filter_by(email=user.email).first()
        assert user_in_db.check_password('newpassword123')
        assert not user_in_db.check_password('testpassword')


def test_change_password_wrong_current(auth_client, app, user):
    """Test password change with wrong current password"""
    response = auth_client.post('/auth/change-password', data={
        'current_password': 'wrongpassword',
        'new_password': 'newpassword123',
        'new_password2': 'newpassword123'
    }, follow_redirects=True)
    
    assert b'Current password is incorrect' in response.data
