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
    assert b'Login' in response.data


def test_register_page(client):
    """Test registration page loads"""
    response = client.get('/auth/register')
    assert response.status_code == 200
    assert b'Register' in response.data or b'Create Account' in response.data


def test_successful_login(client, app):
    """Test successful login"""
    response = client.post('/auth/login', data={
        'email': 'test@example.com',
        'password': 'testpassword',
        'remember_me': False
    }, follow_redirects=True)
    
    assert response.status_code == 200
    assert b'Dashboard' in response.data or b'Welcome' in response.data


def test_failed_login_wrong_password(client):
    """Test login with wrong password"""
    response = client.post('/auth/login', data={
        'email': 'test@example.com',
        'password': 'wrongpassword'
    }, follow_redirects=True)
    
    assert b'Invalid' in response.data or b'incorrect' in response.data.lower()


def test_failed_login_nonexistent_user(client):
    """Test login with non-existent user"""
    response = client.post('/auth/login', data={
        'email': 'nonexistent@example.com',
        'password': 'password'
    }, follow_redirects=True)
    
    assert b'Invalid' in response.data or b'incorrect' in response.data.lower()


def test_successful_registration(client, app):
    """Test successful user registration"""
    response = client.post('/auth/register', data={
        'username': 'newuser',
        'email': 'newuser@example.com',
        'password': 'password123',
        'password2': 'password123'
    }, follow_redirects=True)
    
    with app.app_context():
        user = User.query.filter_by(email='newuser@example.com').first()
        assert user is not None
        assert user.username == 'newuser'


def test_registration_duplicate_email(client):
    """Test registration with duplicate email"""
    response = client.post('/auth/register', data={
        'username': 'anotheruser',
        'email': 'test@example.com',  # Already exists
        'password': 'password123',
        'password2': 'password123'
    }, follow_redirects=True)
    
    assert b'already' in response.data.lower() or b'registered' in response.data.lower()


def test_registration_password_mismatch(client):
    """Test registration with mismatched passwords"""
    response = client.post('/auth/register', data={
        'username': 'testuser2',
        'email': 'test2@example.com',
        'password': 'password123',
        'password2': 'differentpassword'
    }, follow_redirects=True)
    
    assert b'match' in response.data.lower() or b'must match' in response.data.lower()


def test_logout(auth_client):
    """Test logout functionality"""
    response = auth_client.get('/auth/logout', follow_redirects=True)
    
    assert response.status_code == 200
    assert b'logged out' in response.data.lower() or b'login' in response.data.lower()


def test_protected_route_requires_login(client):
    """Test that protected routes redirect to login"""
    response = client.get('/gmail/statements')
    
    # Should redirect to login
    assert response.status_code == 302
    assert '/auth/login' in response.location


def test_profile_page(auth_client):
    """Test profile page for authenticated user"""
    response = auth_client.get('/auth/profile')
    
    assert response.status_code == 200
    assert b'Profile' in response.data
    assert b'testuser' in response.data


def test_profile_update(auth_client, app):
    """Test profile update"""
    response = auth_client.post('/auth/profile', data={
        'username': 'updateduser',
        'email': 'test@example.com'
    }, follow_redirects=True)
    
    with app.app_context():
        user = User.query.filter_by(email='test@example.com').first()
        assert user.username == 'updateduser'


def test_change_password(auth_client, app):
    """Test password change"""
    response = auth_client.post('/auth/change-password', data={
        'current_password': 'testpassword',
        'new_password': 'newpassword123',
        'new_password2': 'newpassword123'
    }, follow_redirects=True)
    
    with app.app_context():
        user = User.query.filter_by(email='test@example.com').first()
        assert user.check_password('newpassword123')
        assert not user.check_password('testpassword')


def test_change_password_wrong_current(auth_client):
    """Test password change with wrong current password"""
    response = auth_client.post('/auth/change-password', data={
        'current_password': 'wrongpassword',
        'new_password': 'newpassword123',
        'new_password2': 'newpassword123'
    }, follow_redirects=True)
    
    assert b'incorrect' in response.data.lower() or b'wrong' in response.data.lower()
