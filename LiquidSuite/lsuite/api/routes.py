# ============================================================================
# lsuite/api/routes.py
# ============================================================================
"""
REST API Routes
"""
from flask import jsonify, request, current_app
from flask_login import login_required, current_user
from lsuite.models import (
    EmailStatement, BankTransaction, TransactionCategory,
    ERPNextConfig, ERPNextSyncLog
)
from lsuite.api.serializers import (
    serialize_statement, serialize_transaction,
    serialize_category, serialize_sync_log
)
from lsuite.gmail.services import GmailService
from lsuite.bridge.services import CategorizationService, BulkSyncService
from lsuite.api import api_bp


@api_bp.route('/health')
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'version': '1.0.0'}), 200


# ============================================================================
# Statements API
# ============================================================================

@api_bp.route('/statements')
@login_required
def get_statements():
    """Get all statements"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', current_app.config['ITEMS_PER_PAGE'], type=int)
    
    statements = EmailStatement.query.order_by(
        EmailStatement.date.desc()
    ).paginate(page=page, per_page=per_page)
    
    return jsonify({
        'items': [serialize_statement(s) for s in statements.items],
        'total': statements.total,
        'page': page,
        'pages': statements.pages
    })


@api_bp.route('/statements/<int:id>')
@login_required
def get_statement(id):
    """Get statement by ID"""
    statement = EmailStatement.query.get_or_404(id)
    return jsonify(serialize_statement(statement))


@api_bp.route('/statements/import', methods=['POST'])
@login_required
def import_statements():
    """Import statements from Gmail"""
    from lsuite.models import GoogleCredential
    
    cred = GoogleCredential.query.filter_by(
        user_id=current_user.id,
        is_authenticated=True
    ).first()
    
    if not cred:
        return jsonify({'error': 'No authenticated Google credential found'}), 400
    
    service = GmailService(current_app)
    imported, skipped = service.fetch_statements(cred)
    
    return jsonify({
        'imported': imported,
        'skipped': skipped,
        'message': f'Imported {imported} statements ({skipped} already existed)'
    })


# ============================================================================
# Transactions API
# ============================================================================

@api_bp.route('/transactions')
@login_required
def get_transactions():
    """Get all transactions"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', current_app.config['ITEMS_PER_PAGE'], type=int)
    
    query = BankTransaction.query.order_by(BankTransaction.date.desc())
    
    # Filters
    if request.args.get('uncategorized') == 'true':
        query = query.filter_by(category_id=None)
    
    if request.args.get('not_synced') == 'true':
        query = query.filter_by(erpnext_synced=False)
    
    category_id = request.args.get('category_id', type=int)
    if category_id:
        query = query.filter_by(category_id=category_id)
    
    transactions = query.paginate(page=page, per_page=per_page)
    
    return jsonify({
        'items': [serialize_transaction(t) for t in transactions.items],
        'total': transactions.total,
        'page': page,
        'pages': transactions.pages
    })


@api_bp.route('/transactions/<int:id>')
@login_required
def get_transaction(id):
    """Get transaction by ID"""
    transaction = BankTransaction.query.get_or_404(id)
    return jsonify(serialize_transaction(transaction))


@api_bp.route('/transactions/<int:id>/categorize', methods=['POST'])
@login_required
def categorize_transaction_api(id):
    """Categorize a transaction"""
    from lsuite.extensions import db
    
    transaction = BankTransaction.query.get_or_404(id)
    data = request.get_json()
    
    category_id = data.get('category_id')
    if not category_id:
        return jsonify({'error': 'category_id required'}), 400
    
    category = TransactionCategory.query.get_or_404(category_id)
    
    transaction.category_id = category_id
    db.session.commit()
    
    return jsonify({
        'message': f'Transaction categorized as {category.name}',
        'transaction': serialize_transaction(transaction)
    })


@api_bp.route('/transactions/auto-categorize', methods=['POST'])
@login_required
def auto_categorize_api():
    """Auto-categorize all transactions"""
    service = CategorizationService()
    categorized, total = service.auto_categorize_all()
    
    return jsonify({
        'categorized': categorized,
        'total': total,
        'message': f'Categorized {categorized} of {total} transactions'
    })


@api_bp.route('/transactions/sync', methods=['POST'])
@login_required
def sync_transactions_api():
    """Sync transactions to ERPNext"""
    # ? FIXED: Use is_active instead of active
    config = ERPNextConfig.query.filter_by(is_active=True).first()
    
    if not config:
        return jsonify({'error': 'No active ERPNext configuration found'}), 400
    
    service = BulkSyncService(config)
    success, failed, total = service.sync_all_ready()
    
    return jsonify({
        'success': success,
        'failed': failed,
        'total': total,
        'message': f'Synced {success} transactions, {failed} failed'
    })


# ============================================================================
# Categories API
# ============================================================================

@api_bp.route('/categories')
@login_required
def get_categories():
    """Get all categories"""
    categories = TransactionCategory.query.order_by(TransactionCategory.name).all()
    
    return jsonify({
        'items': [serialize_category(c) for c in categories]
    })


@api_bp.route('/categories/<int:id>')
@login_required
def get_category(id):
    """Get category by ID"""
    category = TransactionCategory.query.get_or_404(id)
    return jsonify(serialize_category(category))


@api_bp.route('/categories', methods=['POST'])
@login_required
def create_category():
    """Create new category"""
    from lsuite.extensions import db
    
    data = request.get_json()
    
    category = TransactionCategory(
        name=data['name'],
        erpnext_account=data['erpnext_account'],
        transaction_type=data['transaction_type'],
        keywords=data.get('keywords', ''),
        active=data.get('active', True)
    )
    
    db.session.add(category)
    db.session.commit()
    
    return jsonify({
        'message': 'Category created',
        'category': serialize_category(category)
    }), 201


@api_bp.route('/categories/<int:id>', methods=['PUT'])
@login_required
def update_category(id):
    """Update category"""
    from lsuite.extensions import db
    
    category = TransactionCategory.query.get_or_404(id)
    data = request.get_json()
    
    category.name = data.get('name', category.name)
    category.erpnext_account = data.get('erpnext_account', category.erpnext_account)
    category.transaction_type = data.get('transaction_type', category.transaction_type)
    category.keywords = data.get('keywords', category.keywords)
    category.active = data.get('active', category.active)
    
    db.session.commit()
    
    return jsonify({
        'message': 'Category updated',
        'category': serialize_category(category)
    })


# ============================================================================
# Statistics API
# ============================================================================

@api_bp.route('/stats')
@login_required
def get_stats():
    """Get dashboard statistics"""
    stats = {
        'statements': {
            'total': EmailStatement.query.count(),
            'parsed': EmailStatement.query.filter_by(state='parsed').count()
        },
        'transactions': {
            'total': BankTransaction.query.count(),
            'categorized': BankTransaction.query.filter(
                BankTransaction.category_id.isnot(None)
            ).count(),
            'synced': BankTransaction.query.filter_by(erpnext_synced=True).count()
        },
        'categories': TransactionCategory.query.filter_by(active=True).count(),
        'sync_logs': {
            'total': ERPNextSyncLog.query.count(),
            'success': ERPNextSyncLog.query.filter_by(status='success').count(),
            'failed': ERPNextSyncLog.query.filter_by(status='failed').count()
        }
    }
    
    return jsonify(stats)
