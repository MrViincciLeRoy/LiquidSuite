"""
Updated LSuite Database Models - Match CSV Format
Replace the BankTransaction class in lsuite/models.py with this version
"""
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from lsuite.extensions import db


class BankTransaction(db.Model):
    """Bank transaction record - matches Capitec CSV format"""
    __tablename__ = 'bank_transactions'
    
    id = db.Column(db.Integer, primary_key=True)
    statement_id = db.Column(db.Integer, db.ForeignKey('email_statements.id'), nullable=True)
    
    # Core transaction fields matching CSV format
    transaction_date = db.Column(db.Date, nullable=False, index=True)
    posting_date = db.Column(db.Date, nullable=True, index=True)
    description = db.Column(db.Text, nullable=False)
    debits = db.Column(db.Numeric(15, 2), nullable=True)  # Money out
    credits = db.Column(db.Numeric(15, 2), nullable=True)  # Money in
    balance = db.Column(db.Numeric(15, 2), nullable=True)
    bank_account = db.Column(db.String(200), nullable=True)
    
    # Additional fields for processing
    reference = db.Column(db.String(100))
    
    # Category and sync fields
    category_id = db.Column(db.Integer, db.ForeignKey('transaction_categories.id'))
    erpnext_synced = db.Column(db.Boolean, default=False)
    erpnext_journal_entry = db.Column(db.String(100))
    erpnext_sync_date = db.Column(db.DateTime)
    erpnext_error = db.Column(db.Text)
    
    state = db.Column(db.String(20), default='draft')  # draft, matched, posted
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    @property
    def transaction_type(self):
        """Determine transaction type from debits/credits"""
        if self.debits and float(self.debits) > 0:
            return 'debit'
        elif self.credits and float(self.credits) > 0:
            return 'credit'
        return 'unknown'
    
    @property
    def amount(self):
        """Get the transaction amount (debits or credits)"""
        if self.debits and float(self.debits) > 0:
            return float(self.debits)
        elif self.credits and float(self.credits) > 0:
            return float(self.credits)
        return 0
    
    @property
    def date(self):
        """Alias for transaction_date for backward compatibility"""
        return self.transaction_date
    
    @property
    def is_categorized(self):
        return self.category_id is not None
    
    def __repr__(self):
        return f'<BankTransaction {self.transaction_date} {self.description[:30]}>'
