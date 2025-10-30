# ============================================================================
# lsuite/bridge/services.py
# ============================================================================
"""
Bridge Services - Categorization and Bulk Operations
"""
import logging
from lsuite.extensions import db
from lsuite.models import TransactionCategory, BankTransaction
from lsuite.erpnext.services import ERPNextService

logger = logging.getLogger(__name__)


class CategorizationService:
    """Transaction categorization service"""
    
    def auto_categorize_all(self):
        """Auto-categorize all uncategorized transactions"""
        
        # Get uncategorized transactions
        uncategorized = BankTransaction.query.filter_by(
            category_id=None,
            erpnext_synced=False
        ).all()
        
        if not uncategorized:
            return 0, 0
        
        # Get active categories
        categories = TransactionCategory.query.filter_by(active=True).all()
        
        categorized_count = 0
        
        for transaction in uncategorized:
            category = self._find_matching_category(transaction, categories)
            
            if category:
                transaction.category_id = category.id
                categorized_count += 1
                logger.info(f"Auto-categorized transaction {transaction.id} as {category.name}")
        
        db.session.commit()
        
        return categorized_count, len(uncategorized)
    
    def _find_matching_category(self, transaction, categories):
        """Find matching category for transaction"""
        if not transaction.description:
            return None
        
        description_lower = transaction.description.lower()
        
        # Try to find exact keyword matches
        for category in categories:
            if category.matches_description(description_lower):
                return category
        
        return None
    
    def preview_categorization(self):
        """Preview what will be categorized"""
        uncategorized = BankTransaction.query.filter_by(
            category_id=None,
            erpnext_synced=False
        ).all()
        
        categories = TransactionCategory.query.filter_by(active=True).all()
        
        matches = []
        no_match = []
        
        for transaction in uncategorized:
            category = self._find_matching_category(transaction, categories)
            
            if category:
                # Find which keyword matched
                matched_keyword = None
                description_lower = transaction.description.lower()
                for keyword in category.get_keywords_list():
                    if keyword in description_lower:
                        matched_keyword = keyword
                        break
                
                matches.append({
                    'transaction': transaction,
                    'category': category,
                    'keyword': matched_keyword
                })
            else:
                no_match.append(transaction)
        
        return {
            'uncategorized': uncategorized,
            'matches': matches,
            'no_match': no_match
        }
    
    def suggest_category(self, description):
        """Suggest category based on description"""
        if not description:
            return None
        
        categories = TransactionCategory.query.filter_by(active=True).all()
        return self._find_matching_category(
            type('Transaction', (), {'description': description})(),
            categories
        )


class BulkSyncService:
    """Bulk sync service"""
    
    def __init__(self, erpnext_config):
        self.config = erpnext_config
        self.service = ERPNextService(erpnext_config)
    
    def sync_all_ready(self):
        """Sync all ready transactions"""
        
        # Get transactions ready to sync
        ready_transactions = BankTransaction.query.filter(
            BankTransaction.category_id.isnot(None),
            BankTransaction.erpnext_synced == False
        ).all()
        
        if not ready_transactions:
            return 0, 0, 0
        
        success_count = 0
        failed_count = 0
        
        for transaction in ready_transactions:
            try:
                self.service.create_journal_entry(transaction)
                success_count += 1
                logger.info(f"Synced transaction {transaction.id}")
                
            except Exception as e:
                failed_count += 1
                logger.error(f"Failed to sync transaction {transaction.id}: {str(e)}")
                continue
        
        return success_count, failed_count, len(ready_transactions)
    
    def sync_by_category(self, category_id):
        """Sync all transactions in a category"""
        
        transactions = BankTransaction.query.filter_by(
            category_id=category_id,
            erpnext_synced=False
        ).all()
        
        success_count = 0
        failed_count = 0
        
        for transaction in transactions:
            try:
                self.service.create_journal_entry(transaction)
                success_count += 1
            except Exception as e:
                failed_count += 1
                logger.error(f"Failed to sync transaction {transaction.id}: {str(e)}")
                continue
        
        return success_count, failed_count, len(transactions)
    
    def sync_by_date_range(self, start_date, end_date):
        """Sync transactions within date range"""
        
        transactions = BankTransaction.query.filter(
            BankTransaction.category_id.isnot(None),
            BankTransaction.erpnext_synced == False,
            BankTransaction.date >= start_date,
            BankTransaction.date <= end_date
        ).all()
        
        success_count = 0
        failed_count = 0
        
        for transaction in transactions:
            try:
                self.service.create_journal_entry(transaction)
                success_count += 1
            except Exception as e:
                failed_count += 1
                logger.error(f"Failed to sync transaction {transaction.id}: {str(e)}")
                continue
        
        return success_count, failed_count, len(transactions)
