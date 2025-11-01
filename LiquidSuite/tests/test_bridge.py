"""
Fixed tests/test_bridge.py - Simplified and robust version
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


# ============================================================================
# Simple fixtures that work within each test's app context
# ============================================================================

def create_test_user(app):
    """Helper to create a test user"""
    user = User(
        username='testuser',
        email='test@example.com'
    )
    user.set_password('testpass123')
    db.session.add(user)
    db.session.commit()
    return user.id


def create_test_categories(app):
    """Helper to create test categories"""
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
    return [cat.id for cat in categories]


def create_test_transactions(app, user_id):
    """Helper to create test transactions"""
    from lsuite.models import BankAccount
    
    # Create a bank account first (required for transactions)
    bank_account = BankAccount(
        user_id=user_id,
        account_name='Test Bank Account',
        account_number='12345',
        bank_name='Test Bank',
        account_type='Savings',
        balance=Decimal('10000.00')
    )
    db.session.add(bank_account)
    db.session.flush()
    
    # Create statement
    statement = EmailStatement(
        user_id=user_id,
        email_id='test-statement-1',
        subject='Bank Statement',
        sender='bank@example.com',
        received_date=datetime.utcnow(),
        bank_name='testbank',
        is_processed=True
    )
    db.session.add(statement)
    db.session.flush()
    
    # Create transactions
    transactions = [
        BankTransaction(
            user_id=user_id,
            bank_account_id=bank_account.id,
            statement_id=statement.id,
            date=date.today(),
            description='Uber trip to office',
            withdrawal=Decimal('150.00'),
            deposit=Decimal('0.00'),
            balance=Decimal('5000.00'),
            reference_number='REF001'
        ),
        BankTransaction(
            user_id=user_id,
            bank_account_id=bank_account.id,
            statement_id=statement.id,
            date=date.today(),
            description='Coffee at Starbucks',
            withdrawal=Decimal('45.00'),
            deposit=Decimal('0.00'),
            balance=Decimal('4955.00'),
            reference_number='REF002'
        ),
        BankTransaction(
            user_id=user_id,
            bank_account_id=bank_account.id,
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
    return [trans.id for trans in transactions]


# ============================================================================
# Tests
# ============================================================================

def test_suggest_category(app):
    """Test category suggestion based on description"""
    with app.app_context():
        # Setup
        create_test_categories(app)
        
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


def test_category_keywords_matching(app):
    """Test keyword matching logic"""
    with app.app_context():
        # Setup
        create_test_categories(app)
        
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


def test_auto_categorize_all(app):
    """Test automatic categorization of all transactions"""
    with app.app_context():
        # Setup
        user_id = create_test_user(app)
        create_test_categories(app)
        create_test_transactions(app, user_id)
        
        service = CategorizationService()
        
        # Run auto-categorization
        categorized, total = service.auto_categorize_all()
        
        # Should categorize 2 out of 3 transactions
        assert total == 3
        assert categorized == 2
        
        # Verify specific transactions were categorized correctly
        uber_trans = BankTransaction.query.filter(
            BankTransaction.description.like('%Uber%')
        ).first()
        assert uber_trans is not None
        assert uber_trans.category_id is not None
        assert uber_trans.category.name == 'Transport'
        
        coffee_trans = BankTransaction.query.filter(
            BankTransaction.description.like('%Coffee%')
        ).first()
        assert coffee_trans is not None
        assert coffee_trans.category_id is not None
        assert coffee_trans.category.name == 'Food'
        
        unknown_trans = BankTransaction.query.filter(
            BankTransaction.description.like('%Unknown%')
        ).first()
        assert unknown_trans is not None
        assert unknown_trans.category_id is None


def test_find_matching_category(app):
    """Test finding matching category for transaction"""
    with app.app_context():
        # Setup
        user_id = create_test_user(app)
        create_test_categories(app)
        create_test_transactions(app, user_id)
        
        service = CategorizationService()
        categories = TransactionCategory.query.all()
        
        # Get first transaction (Uber)
        transaction = BankTransaction.query.filter(
            BankTransaction.description.like('%Uber%')
        ).first()
        
        assert transaction is not None
        
        category = service._find_matching_category(transaction, categories)
        assert category is not None
        assert category.name == 'Transport'


def test_preview_categorization(app):
    """Test categorization preview"""
    with app.app_context():
        # Setup
        user_id = create_test_user(app)
        create_test_categories(app)
        create_test_transactions(app, user_id)
        
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


def test_categorization_preserves_existing(app):
    """Test that auto-categorization doesn't override manual categories"""
    with app.app_context():
        # Setup
        user_id = create_test_user(app)
        create_test_categories(app)
        create_test_transactions(app, user_id)
        
        # Get the Uber transaction and manually categorize it as Food
        transaction = BankTransaction.query.filter(
            BankTransaction.description.like('%Uber%')
        ).first()
        
        food_category = TransactionCategory.query.filter_by(name='Food').first()
        transaction.category_id = food_category.id
        db.session.commit()
        
        original_category_id = transaction.category_id
        
        # Run auto-categorization
        service = CategorizationService()
        categorized, total = service.auto_categorize_all()
        
        # Should only categorize the Coffee transaction (1 out of 2 remaining)
        assert categorized == 1
        
        # Uber transaction should still have Food category (not changed to Transport)
        db.session.refresh(transaction)
        assert transaction.category_id == original_category_id
        assert transaction.category.name == 'Food'


def test_categorization_case_insensitive(app):
    """Test that keyword matching is case-insensitive"""
    with app.app_context():
        # Setup
        user_id = create_test_user(app)
        create_test_categories(app)
        
        # Create a statement
        statement = EmailStatement(
            user_id=user_id,
            email_id='test-case-statement',
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
            user_id=user_id,
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


def test_empty_description(app):
    """Test handling of transactions with empty descriptions"""
    with app.app_context():
        # Setup
        user_id = create_test_user(app)
        create_test_categories(app)
        
        statement = EmailStatement(
            user_id=user_id,
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
            user_id=user_id,
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


def test_multiple_keyword_matches(app):
    """Test transaction matching multiple category keywords"""
    with app.app_context():
        # Setup
        user_id = create_test_user(app)
        create_test_categories(app)
        
        statement = EmailStatement(
            user_id=user_id,
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
            user_id=user_id,
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
        
        # Should match one of the categories
        db.session.refresh(transaction)
        assert transaction.category_id is not None
        # Either Transport or Food is acceptable
        assert transaction.category.name in ['Transport', 'Food']
