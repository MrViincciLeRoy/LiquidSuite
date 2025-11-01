# ============================================================================
# lsuite/main/routes.py - FIXED VERSION
# ============================================================================
"""
Main Blueprint - Dashboard and Home
"""
from flask import render_template
from flask_login import login_required
from lsuite.models import (
    EmailStatement, BankTransaction, TransactionCategory,
    ERPNextConfig, ERPNextSyncLog
)
from sqlalchemy import func
from datetime import datetime, timedelta
from lsuite.main import main_bp


@main_bp.route('/')
@login_required
def index():
    """Dashboard home page"""
    
    # Get statistics
    stats = {
        'statements': EmailStatement.query.count(),
        'transactions': BankTransaction.query.count(),
        'categorized': BankTransaction.query.filter(
            BankTransaction.category_id.isnot(None)
        ).count(),
        'synced': BankTransaction.query.filter_by(erpnext_synced=True).count(),
    }
    
    # Recent statements - FIXED: Use received_date instead of date
    recent_statements = EmailStatement.query.order_by(
        EmailStatement.received_date.desc()
    ).limit(5).all()
    
    # Recent transactions
    recent_transactions = BankTransaction.query.order_by(
        BankTransaction.date.desc()
    ).limit(10).all()
    
    # Category breakdown
    from lsuite.extensions import db
    category_stats = db.session.query(
        TransactionCategory.name,
        func.count(BankTransaction.id).label('count'),
        func.sum(BankTransaction.withdrawal).label('total_withdrawals'),
        func.sum(BankTransaction.deposit).label('total_deposits')
    ).join(
        BankTransaction, BankTransaction.category_id == TransactionCategory.id
    ).group_by(
        TransactionCategory.name
    ).all()
    
    # Recent sync logs
    recent_syncs = ERPNextSyncLog.query.order_by(
        ERPNextSyncLog.sync_date.desc()
    ).limit(5).all()
    
    # ERPNext config status - FIXED: Use is_active instead of active
    erpnext_config = ERPNextConfig.query.filter_by(is_active=True).first()
    
    # Calculate ready to sync
    ready_to_sync = BankTransaction.query.filter(
        BankTransaction.category_id.isnot(None),
        BankTransaction.erpnext_synced == False
    ).count()
    
    return render_template(
        'main/index.html',
        stats=stats,
        recent_statements=recent_statements,
        recent_transactions=recent_transactions,
        category_stats=category_stats,
        recent_syncs=recent_syncs,
        erpnext_config=erpnext_config,
        ready_to_sync=ready_to_sync
    )


@main_bp.route('/api/health')
def health_check():
    """Health check endpoint for monitoring"""
    try:
        # Check database connection
        from lsuite.extensions import db
        db.session.execute(db.text('SELECT 1'))
        db_status = 'healthy'
    except Exception as e:
        db_status = f'unhealthy: {str(e)}'
    
    return {
        'status': 'ok',
        'database': db_status,
        'timestamp': datetime.utcnow().isoformat()
    }, 200


@main_bp.route('/about')
def about():
    """About page"""
    return render_template('main/about.html')
