# ============================================================================
# lsuite/erpnext/services.py
# ============================================================================
"""
ERPNext Service - API Integration
"""
import logging
import requests
from datetime import datetime
from lsuite.extensions import db
from lsuite.models import ERPNextSyncLog

logger = logging.getLogger(__name__)


class ERPNextService:
    """ERPNext API service"""
    
    def __init__(self, config):
        self.config = config
    
    def _get_headers(self):
        """Get API headers with authentication"""
        return {
            'Authorization': f'token {self.config.api_key}:{self.config.api_secret}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
    
    def test_connection(self):
        """Test ERPNext connection"""
        try:
            url = f"{self.config.base_url}/api/method/frappe.auth.get_logged_user"
            response = requests.get(url, headers=self._get_headers(), timeout=10)
            response.raise_for_status()
            
            user = response.json().get('message', 'Unknown')
            return True, f"Connected as: {user}"
            
        except requests.exceptions.ConnectionError:
            return False, "Cannot connect to ERPNext server. Check URL."
        except requests.exceptions.Timeout:
            return False, "Connection timeout. Server not responding."
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                return False, "Authentication failed. Check API credentials."
            return False, f"HTTP {e.response.status_code}: {e.response.text}"
        except Exception as e:
            return False, str(e)
    
    def create_journal_entry(self, transaction):
        """Create Journal Entry in ERPNext from bank transaction"""
        
        posting_date = transaction.date.strftime('%Y-%m-%d')
        
        # Determine debit/credit based on transaction type
        if transaction.transaction_type == 'debit':
            # Money out: Credit bank, Debit expense
            bank_credit = abs(float(transaction.amount))
            bank_debit = 0
            expense_credit = 0
            expense_debit = abs(float(transaction.amount))
        else:  # credit
            # Money in: Debit bank, Credit income
            bank_credit = 0
            bank_debit = abs(float(transaction.amount))
            expense_credit = abs(float(transaction.amount))
            expense_debit = 0
        
        # Get ERPNext account from category
        if not transaction.category_id:
            raise ValueError("Transaction must be categorized before syncing")
        
        erpnext_account = transaction.category.erpnext_account
        
        # Prepare journal entry data
        journal_data = {
            'doctype': 'Journal Entry',
            'company': self.config.default_company,
            'posting_date': posting_date,
            'accounts': [
                {
                    'account': self.config.bank_account,
                    'debit_in_account_currency': bank_debit,
                    'credit_in_account_currency': bank_credit,
                },
                {
                    'account': erpnext_account,
                    'debit_in_account_currency': expense_debit,
                    'credit_in_account_currency': expense_credit,
                    'cost_center': self.config.default_cost_center or None,
                }
            ],
            'user_remark': transaction.description or '',
            'reference_number': transaction.reference or '',
        }
        
        url = f"{self.config.base_url}/api/resource/Journal Entry"
        
        try:
            response = requests.post(
                url,
                headers=self._get_headers(),
                json=journal_data,
                timeout=30
            )
            response.raise_for_status()
            result = response.json()
            
            journal_entry_name = result.get('data', {}).get('name')
            
            # Update transaction
            transaction.erpnext_synced = True
            transaction.erpnext_journal_entry = journal_entry_name
            transaction.erpnext_sync_date = datetime.utcnow()
            transaction.erpnext_error = None
            
            # Log sync
            log = ERPNextSyncLog(
                config_id=self.config.id,
                record_type='bank_transaction',
                record_id=transaction.id,
                erpnext_doctype='Journal Entry',
                erpnext_doc_name=journal_entry_name,
                status='success'
            )
            db.session.add(log)
            db.session.commit()
            
            logger.info(f"Synced transaction {transaction.id} to ERPNext: {journal_entry_name}")
            
            return journal_entry_name
            
        except requests.exceptions.HTTPError as e:
            error_message = f"HTTP {e.response.status_code}: {e.response.text}"
            self._handle_sync_error(transaction, error_message)
            raise
        except Exception as e:
            error_message = str(e)
            self._handle_sync_error(transaction, error_message)
            raise
    
    def _handle_sync_error(self, transaction, error_message):
        """Handle sync error"""
        logger.error(f"Failed to create journal entry: {error_message}")
        
        # Update transaction with error
        transaction.erpnext_error = error_message
        
        # Log failure
        log = ERPNextSyncLog(
            config_id=self.config.id,
            record_type='bank_transaction',
            record_id=transaction.id,
            status='failed',
            error_message=error_message
        )
        db.session.add(log)
        db.session.commit()
    
    def get_chart_of_accounts(self):
        """Fetch chart of accounts from ERPNext"""
        try:
            url = f"{self.config.base_url}/api/resource/Account"
            params = {
                'fields': '["name", "account_type", "is_group"]',
                'filters': f'[["company", "=", "{self.config.default_company}"]]',
                'limit_page_length': 1000
            }
            
            response = requests.get(
                url,
                headers=self._get_headers(),
                params=params,
                timeout=30
            )
            response.raise_for_status()
            
            accounts = response.json().get('data', [])
            return accounts
            
        except Exception as e:
            logger.error(f"Failed to fetch accounts: {str(e)}")
            return []
    
    def get_cost_centers(self):
        """Fetch cost centers from ERPNext"""
        try:
            url = f"{self.config.base_url}/api/resource/Cost Center"
            params = {
                'fields': '["name", "cost_center_name"]',
                'filters': f'[["company", "=", "{self.config.default_company}"]]',
                'limit_page_length': 1000
            }
            
            response = requests.get(
                url,
                headers=self._get_headers(),
                params=params,
                timeout=30
            )
            response.raise_for_status()
            
            cost_centers = response.json().get('data', [])
            return cost_centers
            
        except Exception as e:
            logger.error(f"Failed to fetch cost centers: {str(e)}")
            return []
