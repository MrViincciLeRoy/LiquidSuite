"""
Fixed tests/test_bridge.py
"""
import pytest
from datetime import datetime, date
from decimal import Decimal

from lsuite.models import (
    User, EmailStatement, BankTransaction, 
    TransactionCategory
)
from lsuite.bridge.services import CategorizationService
from lsuite.extensions import db


@pytest.fixture
def test_user(app):
    """Create a test user"""
    with app.app_context():
        user = User(
            username='testuser',
            email='test@example.com'
        )
        user.set_password('testpass123')
        db.session.add(user)
        db.session.commit()
        user_id = user.id  # Get ID before session closes
        
    # Return ID instead of object to avoid detached instance
    return user_id


@pytest.fixture
def sample_categories(app):
    """Create sample transaction categories"""
    with app.app_context():
        categories = [
            TransactionCategory(
                name='Transport',
                erpnext_account='Transport Expenses - Company',
                transaction_type='expense',
                keywords='uber, bolt, taxi, fuel',
                active=True
            ),
            TransactionCategory(
                name='Food',
                erpnext_account='Food Expenses - Company',
                transaction_type='expense',
                keywords='restaurant, coffee, lunch',
                active=True
            ),
        ]
        
        for cat in categories:
            db.session.add(cat)
        
        db.session.commit()
        return categories


@pytest.fixture
def sample_transactions(app, test_user, sample_categories):
    """Create sample transactions for testing"""
    with app.app_context():
        # test_user is now an ID, not an object
        statement = EmailStatement(
            user_id=test_user,  # Use ID directly
            email_id='test-statement-1',
            subject='Bank Statement',
            sender='bank@example.com',
            received_date=datetime.utcnow(),
            bank_name='testbank',
            is_processed=True
        )
        db.session.add(statement)
        db.session.flush()
        
        transactions = [
            BankTransaction(
                user_id=test_user,  # Use ID directly
                statement_id=statement.id,
                date=date.today(),
                description='Uber trip to office',
                withdrawal=Decimal('150.00'),
                deposit=Decimal('0.00'),
                balance=Decimal('5000.00'),
                reference_number='REF001'
            ),
            BankTransaction(
                user_id=test_user,  # Use ID directly
                statement_id=statement.id,
                date=date.today(),
                description='Coffee at Starbucks',
                withdrawal=Decimal('45.00'),
                deposit=Decimal('0.00'),
                balance=Decimal('4955.00'),
                reference_number='REF002'
            ),
            BankTransaction(
                user_id=test_user,  # Use ID directly
                statement_id=statement.id,
                date=date.today(),
                description='Unknown transaction',
                withdrawal=Decimal('100.00'),
                deposit=Decimal('0.00'),
                balance=Decimal('4855.00'),
                reference_number='REF003'
            ),
        ]
        
        for trans in transactions:
            db.session.add(trans)
        
        db.session.commit()
        return transactions


# ============================================================================
# Tests
# ============================================================================

def test_suggest_category(app, sample_categories):
    """Test category suggestion based on description"""
    with app.app_context():
        service = CategorizationService()
        
        # Test transport keyword
        suggested = service.suggest_category('Uber trip downtown')
        assert suggested is not None
        assert suggested.name == 'Transport'
        
        # Test food keyword
        suggested = service.suggest_category('Lunch at restaurant')
        assert suggested is not None
        assert suggested.name == 'Food'
        
        # Test no match
        suggested = service.suggest_category('Random description')
        assert suggested is None


def test_category_keywords_matching(app, sample_categories):
    """Test keyword matching logic"""
    with app.app_context():
        transport_cat = TransactionCategory.query.filter_by(name='Transport').first()
        
        # Test keyword list parsing
        keywords = transport_cat.get_keywords_list()
        assert 'uber' in keywords
        assert 'bolt' in keywords
        assert 'taxi' in keywords
        
        # Test description matching
        assert transport_cat.matches_description('Paid for Uber ride')
        assert transport_cat.matches_description('BOLT taxi service')
        assert not transport_cat.matches_description('Restaurant meal')


def test_auto_categorize_all(app, test_user, sample_transactions, sample_categories):
    """Test automatic categorization of all transactions"""
    with app.app_context():
        service = CategorizationService()
        
        # Run auto-categorization
        categorized, total = service.auto_categorize_all()
        
        # Should categorize 2 out of 3 transactions
        assert total == 3
        assert categorized == 2
        
        # Verify specific transactions
        uber_trans = BankTransaction.query.filter(
            BankTransaction.description.like('%Uber%')
        ).first()
        assert uber_trans.category_id is not None
        assert uber_trans.category.name == 'Transport'
        
        coffee_trans = BankTransaction.query.filter(
            BankTransaction.description.like('%Coffee%')
        ).first()
        assert coffee_trans.category_id is not None
        assert coffee_trans.category.name == 'Food'
        
        unknown_trans = BankTransaction.query.filter(
            BankTransaction.description.like('%Unknown%')
        ).first()
        assert unknown_trans.category_id is None


def test_find_matching_category(app, sample_transactions, sample_categories):
    """Test finding matching category for transaction"""
    with app.app_context():
        service = CategorizationService()
        categories = TransactionCategory.query.all()
        
        # Get first transaction (Uber)
        transaction = BankTransaction.query.first()
        
        category = service._find_matching_category(transaction, categories)
        assert category is not None
        assert category.name == 'Transport'


def test_preview_categorization(app, test_user, sample_transactions, sample_categories):
    """Test categorization preview"""
    with app.app_context():
        service = CategorizationService()
        
        preview = service.preview_categorization()
        
        # Should have 3 uncategorized transactions
        assert len(preview['uncategorized']) == 3
        
        # Should have 2 matches
        assert len(preview['matches']) == 2
        
        # Should have 1 no match
        assert len(preview['no_match']) == 1
        
        # Verify match details
        match = preview['matches'][0]
        assert 'transaction' in match
        assert 'category' in match
        assert 'keyword' in match


def test_categorization_preserves_existing(app, test_user, sample_transactions, sample_categories):
    """Test that auto-categorization doesn't override manual categories"""
    with app.app_context():
        # Manually set category on first transaction
        transaction = BankTransaction.query.first()
        food_category = TransactionCategory.query.filter_by(name='Food').first()
        transaction.category_id = food_category.id
        db.session.commit()
        
        # Run auto-categorization
        service = CategorizationService()
        categorized, total = service.auto_categorize_all()
        
        # Should only categorize uncategorized ones
        assert categorized == 1  # Only the coffee transaction
        
        # First transaction should still have Food category
        db.session.refresh(transaction)
        assert transaction.category_id == food_category.id


def test_categorization_case_insensitive(app, test_user, sample_categories):
    """Test that keyword matching is case-insensitive"""
    with app.app_context():
        # FIXED: Add user_id, use email_id
        statement = EmailStatement(
            user_id=test_user.id,  # ADDED
            email_id='test-case-statement',  # FIXED
            subject='Test',
            sender='test@test.com',
            received_date=datetime.utcnow(),
            bank_name='testbank',
            is_processed=True
        )
        db.session.add(statement)
        db.session.flush()
        
        # Create transaction with uppercase description
        transaction = BankTransaction(
            user_id=test_user.id,  # ADDED
            statement_id=statement.id,
            date=date.today(),
            description='UBER TRIP TO AIRPORT',
            withdrawal=Decimal('300.00'),
            deposit=Decimal('0.00'),
            balance=Decimal('5000.00'),
            reference_number='REF999'
        )
        db.session.add(transaction)
        db.session.commit()
        
        # Run categorization
        service = CategorizationService()
        service.auto_categorize_all()
        
        # Should match Transport category despite uppercase
        db.session.refresh(transaction)
        assert transaction.category_id is not None
        assert transaction.category.name == 'Transport'


# ============================================================================
# Additional Edge Case Tests
# ============================================================================

def test_empty_description(app, test_user, sample_categories):
    """Test handling of transactions with empty descriptions"""
    with app.app_context():
        statement = EmailStatement(
            user_id=test_user.id,
            email_id='test-empty-desc',
            subject='Test',
            sender='test@test.com',
            received_date=datetime.utcnow(),
            bank_name='testbank',
            is_processed=True
        )
        db.session.add(statement)
        db.session.flush()
        
        transaction = BankTransaction(
            user_id=test_user.id,
            statement_id=statement.id,
            date=date.today(),
            description='',  # Empty description
            withdrawal=Decimal('100.00'),
            deposit=Decimal('0.00'),
            balance=Decimal('5000.00'),
            reference_number='REF888'
        )
        db.session.add(transaction)
        db.session.commit()
        
        service = CategorizationService()
        service.auto_categorize_all()
        
        # Should not categorize empty descriptions
        db.session.refresh(transaction)
        assert transaction.category_id is None


def test_multiple_keyword_matches(app, test_user, sample_categories):
    """Test transaction matching multiple category keywords"""
    with app.app_context():
        statement = EmailStatement(
            user_id=test_user.id,
            email_id='test-multi-match',
            subject='Test',
            sender='test@test.com',
            received_date=datetime.utcnow(),
            bank_name='testbank',
            is_processed=True
        )
        db.session.add(statement)
        db.session.flush()
        
        # Description matches both categories
        transaction = BankTransaction(
            user_id=test_user.id,
            statement_id=statement.id,
            date=date.today(),
            description='Uber Eats lunch delivery',  # Has both uber and lunch
            withdrawal=Decimal('150.00'),
            deposit=Decimal('0.00'),
            balance=Decimal('5000.00'),
            reference_number='REF777'
        )
        db.session.add(transaction)
        db.session.commit()
        
        service = CategorizationService()
        service.auto_categorize_all()
        
        # Should match first category found (Transport in this case)
        db.session.refresh(transaction)
        assert transaction.category_id is not None
        # Either Transport or Food is acceptable
        assert transaction.category.name in ['Transport', 'Food']
