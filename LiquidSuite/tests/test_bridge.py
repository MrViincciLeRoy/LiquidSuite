# ============================================================================
# tests/test_bridge.py - FIXED VERSION
# ============================================================================
"""
Tests for Bridge functionality (categorization and sync)
"""
import pytest
from lsuite.models import TransactionCategory, BankTransaction
from lsuite.bridge.services import CategorizationService
from lsuite.extensions import db
from datetime import date
from decimal import Decimal


@pytest.fixture
def test_categories(test_user):
    """Create test categories"""
    categories = [
        TransactionCategory(
            name='Transport',
            erpnext_account='Transport Expenses - Company',
            transaction_type='expense',
            keywords='uber, taxi, fuel, petrol',
            active=True
        ),
        TransactionCategory(
            name='Food',
            erpnext_account='Food Expenses - Company',
            transaction_type='expense',
            keywords='restaurant, coffee, lunch',
            active=True
        ),
        TransactionCategory(
            name='Bank Fees',
            erpnext_account='Bank Charges - Company',
            transaction_type='expense',
            keywords='bank fee, service charge',
            active=True
        )
    ]
    
    for cat in categories:
        db.session.add(cat)
    db.session.commit()
    
    return categories


@pytest.fixture
def test_transactions(test_user, test_bank_account, test_categories):
    """Create test transactions"""
    transactions = [
        BankTransaction(
            user_id=test_user.id,
            bank_account_id=test_bank_account.id,
            date=date(2024, 1, 1),
            description='UBER TRIP TO AIRPORT',
            withdrawal=Decimal('250.00'),
            deposit=Decimal('0.00'),
            balance=Decimal('5000.00'),
            reference_number='TXN001'
        ),
        BankTransaction(
            user_id=test_user.id,
            bank_account_id=test_bank_account.id,
            date=date(2024, 1, 2),
            description='STARBUCKS COFFEE SHOP',
            withdrawal=Decimal('45.00'),
            deposit=Decimal('0.00'),
            balance=Decimal('4955.00'),
            reference_number='TXN002'
        ),
        BankTransaction(
            user_id=test_user.id,
            bank_account_id=test_bank_account.id,
            date=date(2024, 1, 3),
            description='MONTHLY BANK FEE',
            withdrawal=Decimal('65.00'),
            deposit=Decimal('0.00'),
            balance=Decimal('4890.00'),
            reference_number='TXN003'
        ),
        BankTransaction(
            user_id=test_user.id,
            bank_account_id=test_bank_account.id,
            date=date(2024, 1, 4),
            description='UNKNOWN TRANSACTION',
            withdrawal=Decimal('100.00'),
            deposit=Decimal('0.00'),
            balance=Decimal('4790.00'),
            reference_number='TXN004'
        )
    ]
    
    for txn in transactions:
        db.session.add(txn)
    db.session.commit()
    
    return transactions


def test_suggest_category(app, test_categories):
    """Test category suggestion based on description"""
    with app.app_context():
        service = CategorizationService()
        
        # Test transport match
        category = service.suggest_category('Uber ride to town')
        assert category is not None
        assert category.name == 'Transport'
        
        # Test food match
        category = service.suggest_category('Lunch at restaurant')
        assert category is not None
        assert category.name == 'Food'
        
        # Test no match
        category = service.suggest_category('Random transaction')
        assert category is None


def test_category_keywords_matching(app, test_categories):
    """Test keyword matching logic"""
    with app.app_context():
        transport_cat = TransactionCategory.query.filter_by(name='Transport').first()
        
        # Test exact keyword match
        assert transport_cat.matches_description('Uber trip')
        assert transport_cat.matches_description('Fuel purchase')
        
        # Test case insensitive
        assert transport_cat.matches_description('UBER TRIP')
        assert transport_cat.matches_description('taxi ride')
        
        # Test no match
        assert not transport_cat.matches_description('Coffee shop')


def test_auto_categorize_all(app, test_transactions, test_categories):
    """Test automatic categorization of all transactions"""
    with app.app_context():
        service = CategorizationService()
        
        # Verify initial state - no transactions categorized
        uncategorized = BankTransaction.query.filter_by(category_id=None).count()
        assert uncategorized == 4
        
        # Run auto-categorization
        categorized, total = service.auto_categorize_all()
        
        # Refresh session to get updated data
        db.session.expire_all()
        
        # Check results
        assert total == 4  # Total uncategorized transactions
        assert categorized == 3  # Should categorize 3 out of 4
        
        # Verify specific categorizations
        uber_txn = BankTransaction.query.filter(
            BankTransaction.description.like('%UBER%')
        ).first()
        assert uber_txn.category_id is not None
        assert uber_txn.category.name == 'Transport'
        
        coffee_txn = BankTransaction.query.filter(
            BankTransaction.description.like('%COFFEE%')
        ).first()
        assert coffee_txn.category_id is not None
        assert coffee_txn.category.name == 'Food'
        
        fee_txn = BankTransaction.query.filter(
            BankTransaction.description.like('%BANK FEE%')
        ).first()
        assert fee_txn.category_id is not None
        assert fee_txn.category.name == 'Bank Fees'
        
        # Unknown transaction should remain uncategorized
        unknown_txn = BankTransaction.query.filter(
            BankTransaction.description.like('%UNKNOWN%')
        ).first()
        assert unknown_txn.category_id is None


def test_find_matching_category(app, test_transactions, test_categories):
    """Test finding matching category for a transaction"""
    with app.app_context():
        service = CategorizationService()
        
        # Get active categories
        categories = TransactionCategory.query.filter_by(active=True).all()
        assert len(categories) == 3
        
        # Test matching for each transaction type
        transactions = BankTransaction.query.all()
        
        # UBER transaction
        uber_txn = next(t for t in transactions if 'UBER' in t.description)
        match = service._find_matching_category(uber_txn, categories)
        assert match is not None
        assert match.name == 'Transport'
        
        # COFFEE transaction
        coffee_txn = next(t for t in transactions if 'COFFEE' in t.description)
        match = service._find_matching_category(coffee_txn, categories)
        assert match is not None
        assert match.name == 'Food'
        
        # BANK FEE transaction
        fee_txn = next(t for t in transactions if 'BANK FEE' in t.description)
        match = service._find_matching_category(fee_txn, categories)
        assert match is not None
        assert match.name == 'Bank Fees'
        
        # UNKNOWN transaction
        unknown_txn = next(t for t in transactions if 'UNKNOWN' in t.description)
        match = service._find_matching_category(unknown_txn, categories)
        assert match is None


def test_preview_categorization(app, test_transactions, test_categories):
    """Test categorization preview"""
    with app.app_context():
        service = CategorizationService()
        
        preview = service.preview_categorization()
        
        assert len(preview['uncategorized']) == 4
        assert len(preview['matches']) == 3
        assert len(preview['no_match']) == 1
        
        # Check that matches have correct structure
        for match in preview['matches']:
            assert 'transaction' in match
            assert 'category' in match
            assert 'keyword' in match


def test_category_statistics(app, test_transactions, test_categories):
    """Test category usage statistics"""
    with app.app_context():
        service = CategorizationService()
        
        # Categorize transactions
        service.auto_categorize_all()
        
        # Refresh session
        db.session.expire_all()
        
        # Check statistics
        transport_cat = TransactionCategory.query.filter_by(name='Transport').first()
        assert transport_cat.transactions.count() == 1
        
        food_cat = TransactionCategory.query.filter_by(name='Food').first()
        assert food_cat.transactions.count() == 1
        
        fee_cat = TransactionCategory.query.filter_by(name='Bank Fees').first()
        assert fee_cat.transactions.count() == 1


def test_recategorize_transaction(app, test_transactions, test_categories):
    """Test changing a transaction's category"""
    with app.app_context():
        # Auto-categorize first
        service = CategorizationService()
        service.auto_categorize_all()
        
        # Get the UBER transaction
        uber_txn = BankTransaction.query.filter(
            BankTransaction.description.like('%UBER%')
        ).first()
        
        # Verify it's categorized as Transport
        assert uber_txn.category.name == 'Transport'
        
        # Manually recategorize as Food (incorrect but testing functionality)
        food_cat = TransactionCategory.query.filter_by(name='Food').first()
        uber_txn.category_id = food_cat.id
        db.session.commit()
        
        # Verify change
        db.session.expire_all()
        uber_txn = BankTransaction.query.filter(
            BankTransaction.description.like('%UBER%')
        ).first()
        assert uber_txn.category.name == 'Food'


def test_inactive_categories_not_used(app, test_transactions, test_categories):
    """Test that inactive categories are not used for auto-categorization"""
    with app.app_context():
        # Deactivate Transport category
        transport_cat = TransactionCategory.query.filter_by(name='Transport').first()
        transport_cat.active = False
        db.session.commit()
        
        # Run auto-categorization
        service = CategorizationService()
        categorized, total = service.auto_categorize_all()
        
        # UBER transaction should NOT be categorized
        uber_txn = BankTransaction.query.filter(
            BankTransaction.description.like('%UBER%')
        ).first()
        assert uber_txn.category_id is None
        
        # But COFFEE and BANK FEE should still be categorized
        assert categorized == 2
