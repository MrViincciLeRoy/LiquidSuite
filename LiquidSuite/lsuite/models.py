"""
LSuite Database Models
"""
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from lsuite.extensions import db


class User(UserMixin, db.Model):
    """User model for authentication"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255))
    is_active = db.Column(db.Boolean, default=True)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    google_credentials = db.relationship('GoogleCredential', backref='user', lazy='dynamic')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.username}>'


class GoogleCredential(db.Model):
    """Google OAuth credentials storage"""
    __tablename__ = 'google_credentials'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    client_id = db.Column(db.String(255), nullable=False)
    client_secret = db.Column(db.String(255), nullable=False)
    access_token = db.Column(db.Text)
    refresh_token = db.Column(db.Text)
    token_expiry = db.Column(db.DateTime)
    is_authenticated = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<GoogleCredential {self.name}>'


class EmailStatement(db.Model):
    """Email bank statement"""
    __tablename__ = 'email_statements'
    
    id = db.Column(db.Integer, primary_key=True)
    gmail_id = db.Column(db.String(100), unique=True, nullable=False, index=True)
    subject = db.Column(db.String(500), nullable=False)
    sender = db.Column(db.String(200))
    date = db.Column(db.DateTime, nullable=False, index=True)
    bank_name = db.Column(db.String(50))
    body_html = db.Column(db.Text)
    body_text = db.Column(db.Text)
    has_pdf = db.Column(db.Boolean, default=False)
    pdf_password = db.Column(db.String(100))
    parsing_log = db.Column(db.Text)
    state = db.Column(db.String(20), default='draft')  # draft, parsed, imported
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    transactions = db.relationship('BankTransaction', backref='statement', lazy='dynamic', 
                                   cascade='all, delete-orphan')
    
    @property
    def transaction_count(self):
        return self.transactions.count()
    
    def __repr__(self):
        return f'<EmailStatement {self.subject}>'


class BankTransaction(db.Model):
    """Bank transaction record"""
    __tablename__ = 'bank_transactions'
    
    id = db.Column(db.Integer, primary_key=True)
    statement_id = db.Column(db.Integer, db.ForeignKey('email_statements.id'), nullable=False)
    date = db.Column(db.Date, nullable=False, index=True)
    description = db.Column(db.Text, nullable=False)
    amount = db.Column(db.Numeric(15, 2), nullable=False)
    transaction_type = db.Column(db.String(20), nullable=False)  # credit, debit
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
    def is_categorized(self):
        return self.category_id is not None
    
    def __repr__(self):
        return f'<BankTransaction {self.date} {self.amount}>'


class TransactionCategory(db.Model):
    """Transaction categorization for ERPNext mapping"""
    __tablename__ = 'transaction_categories'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    erpnext_account = db.Column(db.String(200), nullable=False)
    transaction_type = db.Column(db.String(20), nullable=False)  # expense, income, transfer
    keywords = db.Column(db.Text)  # Comma-separated
    active = db.Column(db.Boolean, default=True)
    color = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    transactions = db.relationship('BankTransaction', backref='category', lazy='dynamic')
    
    def get_keywords_list(self):
        """Return keywords as a list"""
        if not self.keywords:
            return []
        return [k.strip().lower() for k in self.keywords.split(',')]
    
    def matches_description(self, description):
        """Check if any keyword matches the description"""
        if not description:
            return False
        description_lower = description.lower()
        return any(keyword in description_lower for keyword in self.get_keywords_list())
    
    def __repr__(self):
        return f'<TransactionCategory {self.name}>'


class ERPNextConfig(db.Model):
    """ERPNext API configuration"""
    __tablename__ = 'erpnext_configs'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    base_url = db.Column(db.String(255), nullable=False)
    api_key = db.Column(db.String(255), nullable=False)
    api_secret = db.Column(db.String(255), nullable=False)
    default_company = db.Column(db.String(100), nullable=False)
    bank_account = db.Column(db.String(200), nullable=False)
    default_cost_center = db.Column(db.String(200))
    active = db.Column(db.Boolean, default=True)
    last_sync = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    sync_logs = db.relationship('ERPNextSyncLog', backref='config', lazy='dynamic')
    
    def __repr__(self):
        return f'<ERPNextConfig {self.name}>'


class ERPNextSyncLog(db.Model):
    """Log of ERPNext sync operations"""
    __tablename__ = 'erpnext_sync_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    config_id = db.Column(db.Integer, db.ForeignKey('erpnext_configs.id'))
    record_type = db.Column(db.String(50))  # bank_transaction, etc.
    record_id = db.Column(db.Integer)
    erpnext_doctype = db.Column(db.String(100))
    erpnext_doc_name = db.Column(db.String(100))
    status = db.Column(db.String(20), default='pending')  # success, failed, pending
    error_message = db.Column(db.Text)
    sync_date = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<ERPNextSyncLog {self.status} {self.record_type}>'
