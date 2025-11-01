# lsuite/models.py
"""
Database models for LiquidSuite
Maintains backwards compatibility for all imports
"""

from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from lsuite import db

# =============================================================================
# User Models
# =============================================================================

class User(UserMixin, db.Model):
    """User account model"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    first_name = db.Column(db.String(50))
    last_name = db.Column(db.String(50))
    is_active = db.Column(db.Boolean, default=True)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    bank_accounts = db.relationship('BankAccount', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    transactions = db.relationship('Transaction', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    bank_transactions = db.relationship('BankTransaction', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    invoices = db.relationship('Invoice', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    email_statements = db.relationship('EmailStatement', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    
    def set_password(self, password):
        """Hash and set password"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check password against hash"""
        return check_password_hash(self.password_hash, password)
    
    @property
    def full_name(self):
        """Get full name"""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.username
    
    def __repr__(self):
        return f'<User {self.username}>'


# =============================================================================
# Banking Models
# =============================================================================

class BankAccount(db.Model):
    """Bank account model"""
    __tablename__ = 'bank_accounts'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    account_name = db.Column(db.String(200), nullable=False)
    account_number = db.Column(db.String(100))
    bank_name = db.Column(db.String(100))
    account_type = db.Column(db.String(50))  # Savings, Checking, etc.
    currency = db.Column(db.String(3), default='ZAR')
    balance = db.Column(db.Numeric(15, 2), default=0.00)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    transactions = db.relationship('Transaction', backref='bank_account', lazy='dynamic', cascade='all, delete-orphan')
    bank_transactions = db.relationship('BankTransaction', backref='bank_account', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<BankAccount {self.account_name}>'


class Transaction(db.Model):
    """Bank transaction model (legacy)"""
    __tablename__ = 'transactions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    bank_account_id = db.Column(db.Integer, db.ForeignKey('bank_accounts.id'), nullable=False)
    
    transaction_date = db.Column(db.Date, nullable=False, index=True)
    posting_date = db.Column(db.Date)
    description = db.Column(db.String(500), nullable=False)
    reference_number = db.Column(db.String(100), index=True)
    
    # Amount fields
    debit = db.Column(db.Numeric(15, 2), default=0.00)
    credit = db.Column(db.Numeric(15, 2), default=0.00)
    balance = db.Column(db.Numeric(15, 2))
    
    # Categorization
    category = db.Column(db.String(100))
    tags = db.Column(db.String(500))  # Comma-separated tags
    notes = db.Column(db.Text)
    
    # Reconciliation
    is_reconciled = db.Column(db.Boolean, default=False)
    reconciled_date = db.Column(db.DateTime)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoices.id'))
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    @property
    def amount(self):
        """Get transaction amount (credit - debit)"""
        return float(self.credit or 0) - float(self.debit or 0)
    
    @property
    def transaction_type(self):
        """Get transaction type"""
        if self.credit and self.credit > 0:
            return 'credit'
        elif self.debit and self.debit > 0:
            return 'debit'
        return 'unknown'
    
    def __repr__(self):
        return f'<Transaction {self.reference_number or self.id}>'


class BankTransaction(db.Model):
    """Bank transaction model for ERPNext integration"""
    __tablename__ = 'bank_transactions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    bank_account_id = db.Column(db.Integer, db.ForeignKey('bank_accounts.id'), nullable=False)
    
    # Transaction details
    date = db.Column(db.Date, nullable=False, index=True)
    posting_date = db.Column(db.Date, index=True)
    description = db.Column(db.String(500), nullable=False)
    reference_number = db.Column(db.String(100), index=True)
    
    # Amounts
    deposit = db.Column(db.Numeric(15, 2), default=0.00)  # Credits
    withdrawal = db.Column(db.Numeric(15, 2), default=0.00)  # Debits
    balance = db.Column(db.Numeric(15, 2))
    
    # Additional fields
    currency = db.Column(db.String(3), default='ZAR')
    unallocated_amount = db.Column(db.Numeric(15, 2))
    
    # Categorization
    category = db.Column(db.String(100))
    tags = db.Column(db.String(500))
    notes = db.Column(db.Text)
    
    # Reconciliation
    is_reconciled = db.Column(db.Boolean, default=False)
    reconciled_date = db.Column(db.DateTime)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoices.id'))
    
    # ERPNext integration
    erpnext_id = db.Column(db.String(100), index=True)
    erpnext_synced = db.Column(db.Boolean, default=False)
    erpnext_sync_date = db.Column(db.DateTime)
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    @property
    def amount(self):
        """Get transaction amount"""
        return float(self.deposit or 0) - float(self.withdrawal or 0)
    
    @property
    def transaction_type(self):
        """Get transaction type"""
        if self.deposit and self.deposit > 0:
            return 'deposit'
        elif self.withdrawal and self.withdrawal > 0:
            return 'withdrawal'
        return 'unknown'
    
    def to_erpnext_format(self):
        """Convert to ERPNext format"""
        return {
            "date": self.date.strftime('%Y-%m-%d') if self.date else None,
            "posting_date": self.posting_date.strftime('%Y-%m-%d') if self.posting_date else None,
            "description": self.description,
            "deposit": float(self.deposit or 0),
            "withdrawal": float(self.withdrawal or 0),
            "currency": self.currency,
            "bank_account": self.bank_account.account_name if self.bank_account else None,
            "reference_number": self.reference_number,
            "unallocated_amount": float(self.unallocated_amount or 0)
        }
    
    def __repr__(self):
        return f'<BankTransaction {self.reference_number or self.id}>'


# =============================================================================
# Email Statement Models
# =============================================================================

class EmailStatement(db.Model):
    """Email statement model for Gmail integration"""
    __tablename__ = 'email_statements'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Email details
    email_id = db.Column(db.String(255), unique=True, nullable=False, index=True)
    thread_id = db.Column(db.String(255), index=True)
    subject = db.Column(db.String(500))
    sender = db.Column(db.String(255))
    received_date = db.Column(db.DateTime, index=True)
    
    # Statement details
    statement_date = db.Column(db.Date, index=True)
    bank_name = db.Column(db.String(100))
    account_number = db.Column(db.String(100))
    
    # Attachment info
    has_attachments = db.Column(db.Boolean, default=False)
    attachment_count = db.Column(db.Integer, default=0)
    attachment_names = db.Column(db.Text)  # JSON list of filenames
    
    # Processing status
    is_processed = db.Column(db.Boolean, default=False)
    processed_date = db.Column(db.DateTime)
    transactions_extracted = db.Column(db.Integer, default=0)
    
    # Content
    body_text = db.Column(db.Text)
    body_html = db.Column(db.Text)
    
    # Errors
    error_message = db.Column(db.Text)
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    attachments = db.relationship('EmailAttachment', backref='email_statement', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<EmailStatement {self.email_id}>'


class EmailAttachment(db.Model):
    """Email attachment model"""
    __tablename__ = 'email_attachments'
    
    id = db.Column(db.Integer, primary_key=True)
    email_statement_id = db.Column(db.Integer, db.ForeignKey('email_statements.id'), nullable=False)
    
    filename = db.Column(db.String(255), nullable=False)
    content_type = db.Column(db.String(100))
    size = db.Column(db.Integer)  # Size in bytes
    
    # File storage
    file_path = db.Column(db.String(500))  # Path to stored file
    file_data = db.Column(db.LargeBinary)  # Binary data if stored in DB
    
    # Processing
    is_processed = db.Column(db.Boolean, default=False)
    processed_date = db.Column(db.DateTime)
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<EmailAttachment {self.filename}>'


# =============================================================================
# Invoice Models
# =============================================================================

class Invoice(db.Model):
    """Invoice model"""
    __tablename__ = 'invoices'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Invoice details
    invoice_number = db.Column(db.String(100), unique=True, nullable=False, index=True)
    invoice_date = db.Column(db.Date, nullable=False, index=True)
    due_date = db.Column(db.Date)
    
    # Customer/Supplier
    customer_name = db.Column(db.String(200), nullable=False)
    customer_email = db.Column(db.String(120))
    customer_address = db.Column(db.Text)
    
    # Financial details
    subtotal = db.Column(db.Numeric(15, 2), nullable=False, default=0.00)
    tax_amount = db.Column(db.Numeric(15, 2), default=0.00)
    tax_rate = db.Column(db.Numeric(5, 2), default=0.00)
    discount_amount = db.Column(db.Numeric(15, 2), default=0.00)
    total_amount = db.Column(db.Numeric(15, 2), nullable=False, default=0.00)
    paid_amount = db.Column(db.Numeric(15, 2), default=0.00)
    outstanding_amount = db.Column(db.Numeric(15, 2), default=0.00)
    
    currency = db.Column(db.String(3), default='ZAR')
    
    # Status
    status = db.Column(db.String(50), default='draft', index=True)  # draft, sent, paid, overdue, cancelled
    
    # ERPNext integration
    erpnext_id = db.Column(db.String(100), index=True)
    erpnext_synced = db.Column(db.Boolean, default=False)
    erpnext_sync_date = db.Column(db.DateTime)
    
    # Metadata
    notes = db.Column(db.Text)
    terms = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    items = db.relationship('InvoiceItem', backref='invoice', lazy='dynamic', cascade='all, delete-orphan')
    transactions = db.relationship('Transaction', backref='invoice', lazy='dynamic')
    bank_transactions = db.relationship('BankTransaction', backref='invoice', lazy='dynamic')
    
    @property
    def is_paid(self):
        """Check if invoice is fully paid"""
        return self.outstanding_amount <= 0
    
    @property
    def is_overdue(self):
        """Check if invoice is overdue"""
        if self.due_date and self.status not in ['paid', 'cancelled']:
            return datetime.now().date() > self.due_date
        return False
    
    def calculate_totals(self):
        """Recalculate invoice totals from items"""
        self.subtotal = sum(item.total for item in self.items)
        self.tax_amount = self.subtotal * (self.tax_rate / 100)
        self.total_amount = self.subtotal + self.tax_amount - self.discount_amount
        self.outstanding_amount = self.total_amount - self.paid_amount
    
    def __repr__(self):
        return f'<Invoice {self.invoice_number}>'


class InvoiceItem(db.Model):
    """Invoice line item model"""
    __tablename__ = 'invoice_items'
    
    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoices.id'), nullable=False)
    
    item_code = db.Column(db.String(100))
    description = db.Column(db.String(500), nullable=False)
    quantity = db.Column(db.Numeric(10, 2), nullable=False, default=1)
    unit_price = db.Column(db.Numeric(15, 2), nullable=False)
    total = db.Column(db.Numeric(15, 2), nullable=False)
    
    # Metadata
    notes = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def calculate_total(self):
        """Calculate line item total"""
        self.total = self.quantity * self.unit_price
    
    def __repr__(self):
        return f'<InvoiceItem {self.description[:30]}>'


# =============================================================================
# ERPNext Integration Models
# =============================================================================

class ERPNextConfig(db.Model):
    """ERPNext configuration model"""
    __tablename__ = 'erpnext_configs'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, unique=True)
    
    site_url = db.Column(db.String(255), nullable=False)
    api_key = db.Column(db.String(255), nullable=False)
    api_secret = db.Column(db.String(255), nullable=False)
    
    is_active = db.Column(db.Boolean, default=True)
    last_sync = db.Column(db.DateTime)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<ERPNextConfig {self.site_url}>'


class SyncLog(db.Model):
    """Synchronization log model"""
    __tablename__ = 'sync_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    sync_type = db.Column(db.String(50), nullable=False)  # transaction, invoice
    direction = db.Column(db.String(20), nullable=False)  # upload, download
    status = db.Column(db.String(20), nullable=False)  # success, failed, partial
    
    records_processed = db.Column(db.Integer, default=0)
    records_successful = db.Column(db.Integer, default=0)
    records_failed = db.Column(db.Integer, default=0)
    
    error_message = db.Column(db.Text)
    sync_data = db.Column(db.JSON)  # Store sync details
    
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
    
    def __repr__(self):
        return f'<SyncLog {self.sync_type} {self.status}>'


# =============================================================================
# Backwards Compatibility Exports
# =============================================================================

# Ensure all models are exported for backwards compatibility
__all__ = [
    'User',
    'BankAccount',
    'Transaction',
    'BankTransaction',
    'EmailStatement',
    'EmailAttachment',
    'Invoice',
    'InvoiceItem',
    'ERPNextConfig',
    'SyncLog',
]
