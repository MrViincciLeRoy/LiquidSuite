# ============================================================================
# tests/test_auth.py
# ============================================================================
"""
Test Authentication Routes
"""
import pytest
from lsuite.models import User
from lsuite.extensions import db


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
    response = client.post('/auth/login', data={
        'email': user.email,
        'password': 'wrongpassword'
    }, follow_redirects=True)
    
    # Check for flash message and login page
    assert b'Invalid email or password' in response.data
    assert b'Sign In' in response.data


def test_failed_login_nonexistent_user(client, app):
    """Test login with non-existent user"""
    response = client.post('/auth/login', data={
        'email': 'nonexistent@example.com',
        'password': 'password'
    }, follow_redirects=True)
    
    # Check for flash message and login page
    assert b'Invalid email or password' in response.data
    assert b'Sign In' in response.data


def test_successful_registration(client, app):
    """Test successful user registration"""
    response = client.post('/auth/register', data={
        'username': 'newuser',
        'email': 'newuser@example.com',
        'password': 'password123',
        'password2': 'password123'
    }, follow_redirects=True)
    
    # Check for success message and verify user is created
    assert response.status_code == 200
    assert b'Registration successful! Please log in.' in response.data
    
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
    })
    
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


def test_logout(auth_client):
    """Test logout functionality"""
    response = auth_client.get('/auth/logout', follow_redirects=True)
    
    assert response.status_code == 200
    assert b'You have been logged out.' in response.data
    assert b'Sign In' in response.data


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
    response = auth_client.post('/auth/profile', data={
        'username': 'updateduser',
        'email': 'test@example.com'
    }, follow_redirects=True)
    
    assert b'Profile updated successfully!' in response.data
    
    with app.app_context():
        updated_user = User.query.filter_by(email='test@example.com').first()
        assert updated_user.username == 'updateduser'


def test_change_password(auth_client, app, user):
    """Test password change"""
    response = auth_client.post('/auth/change-password', data={
        'current_password': 'testpassword',
        'new_password': 'newpassword123',
        'new_password2': 'newpassword123'
    }, follow_redirects=True)
    
    assert b'Password changed successfully!' in response.data
    
    with app.app_context():
        user_in_db = User.query.filter_by(email='test@example.com').first()
        assert user_in_db.check_password('newpassword123')
        assert not user_in_db.check_password('testpassword')


def test_change_password_wrong_current(auth_client, user):
    """Test password change with wrong current password"""
    response = auth_client.post('/auth/change-password', data={
        'current_password': 'wrongpassword',
        'new_password': 'newpassword123',
        'new_password2': 'newpassword123'
    }, follow_redirects=True)
    
    assert b'Current password is incorrect' in response.data