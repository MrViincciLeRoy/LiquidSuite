"""
Test Database Models
"""
import pytest
from datetime import datetime, date
from lsuite.models import (
    User, GoogleCredential, EmailStatement, BankTransaction,
    TransactionCategory, ERPNextConfig, ERPNextSyncLog
)
from lsuite.extensions import db


def test_user_model(app):
    """Test User model"""
    with app.app_context():
        user = User(username='newuser', email='new@example.com')
        user.set_password('password123')
        
        assert user.check_password('password123')
        assert not user.check_password('wrongpassword')
        assert user.is_active
        assert not user.is_admin


def test_transaction_category_model(app):
    """Test TransactionCategory model"""
    with app.app_context():
        category = TransactionCategory(
            name='Test Category',
            erpnext_account='Test Account',
            transaction_type='expense',
            keywords='test, keyword, match'
        )
        db.session.add(category)
        db.session.commit()
        
        # Test keyword matching
        assert category.matches_description('This is a test transaction')
        assert category.matches_description('keyword found here')
        assert not category.matches_description('no match here')
        
        # Test keywords list
        keywords = category.get_keywords_list()
        assert 'test' in keywords
        assert 'keyword' in keywords
        assert 'match' in keywords


def test_bank_transaction_model(app):
    """Test BankTransaction model"""
    with app.app_context():
        # Create statement first
        statement = EmailStatement(
            gmail_id='test123',
            subject='Test Statement',
            sender='test@bank.com',
            date=datetime.utcnow(),
            bank_name='test'
        )
        db.session.add(statement)
        db.session.commit()
        
        # Create transaction
        transaction = BankTransaction(
            statement_id=statement.id,
            date=date.today(),
            description='Test transaction',
            amount=100.50,
            transaction_type='debit'
        )
        db.session.add(transaction)
        db.session.commit()
        
        assert not transaction.is_categorized
        assert not transaction.erpnext_synced
        
        # Add category
        category = TransactionCategory.query.first()
        transaction.category_id = category.id
        db.session.commit()
        
        assert transaction.is_categorized


def test_email_statement_model(app):
    """Test EmailStatement model"""
    with app.app_context():
        statement = EmailStatement(
            gmail_id='unique123',
            subject='Bank Statement',
            sender='bank@test.com',
            date=datetime.utcnow(),
            bank_name='testbank'
        )
        db.session.add(statement)
        db.session.commit()
        
        assert statement.transaction_count == 0
        assert statement.state == 'draft'
        
        # Add transactions
        for i in range(5):
            trans = BankTransaction(
                statement_id=statement.id,
                date=date.today(),
                description=f'Transaction {i}',
                amount=10.00 * i,
                transaction_type='debit'
            )
            db.session.add(trans)
        
        db.session.commit()
        
        assert statement.transaction_count == 5


def test_erpnext_config_model(app):
    """Test ERPNextConfig model"""
    with app.app_context():
        config = ERPNextConfig(
            name='Test Config',
            base_url='https://test.erpnext.com',
            api_key='test_key',
            api_secret='test_secret',
            default_company='Test Company',
            bank_account='Test Bank - TC'
        )
        db.session.add(config)
        db.session.commit()
        
        assert config.active
        assert config.last_sync is None


def test_sync_log_model(app):
    """Test ERPNextSyncLog model"""
    with app.app_context():
        config = ERPNextConfig(
            name='Log Test Config',
            base_url='https://test.com',
            api_key='key',
            api_secret='secret',
            default_company='Company',
            bank_account='Bank'
        )
        db.session.add(config)
        db.session.commit()
        
        log = ERPNextSyncLog(
            config_id=config.id,
            record_type='bank_transaction',
            record_id=1,
            erpnext_doctype='Journal Entry',
            status='success'
        )
        db.session.add(log)
        db.session.commit()
        
        assert log.status == 'success'
        assert log.error_message is None


def test_google_credential_model(app):
    """Test GoogleCredential model"""
    with app.app_context():
        user = User.query.filter_by(email='test@example.com').first()
        
        cred = GoogleCredential(
            user_id=user.id,
            name='Test Credential',
            client_id='test_client_id',
            client_secret='test_client_secret'
        )
        db.session.add(cred)
        db.session.commit()
        
        assert not cred.is_authenticated
        assert cred.access_token is None
        
        # Simulate authentication
        cred.access_token = 'test_token'
        cred.refresh_token = 'refresh_token'
        cred.is_authenticated = True
        db.session.commit()
        
        assert cred.is_authenticated
        assert cred.access_token == 'test_token'
