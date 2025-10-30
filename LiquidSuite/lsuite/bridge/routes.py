
# ============================================================================
# lsuite/bridge/routes.py
# ============================================================================
"""
Bridge Routes - Categorization and Bulk Operations
"""
from flask import render_template, redirect, url_for, flash, request, current_app, jsonify
from flask_login import login_required
from lsuite.extensions import db
from lsuite.models import TransactionCategory, BankTransaction, ERPNextConfig
from lsuite.bridge.services import CategorizationService, BulkSyncService
from lsuite.bridge import bridge_bp


@bridge_bp.route('/categories')
@login_required
def categories():
    """List transaction categories"""
    categories = TransactionCategory.query.order_by(TransactionCategory.name).all()
    
    # Get usage statistics
    category_stats = {}
    for category in categories:
        category_stats[category.id] = {
            'total': category.transactions.count(),
            'synced': category.transactions.filter_by(erpnext_synced=True).count(),
            'pending': category.transactions.filter_by(erpnext_synced=False).count()
        }
    
    return render_template('bridge/categories.html', 
                         categories=categories, 
                         category_stats=category_stats)


@bridge_bp.route('/categories/new', methods=['GET', 'POST'])
@login_required
def new_category():
    """Create new category"""
    if request.method == 'POST':
        category = TransactionCategory(
            name=request.form['name'],
            erpnext_account=request.form['erpnext_account'],
            transaction_type=request.form['transaction_type'],
            keywords=request.form.get('keywords', ''),
            active=request.form.get('active', 'true') == 'true',
            color=request.form.get('color', type=int)
        )
        
        db.session.add(category)
        db.session.commit()
        
        flash('Category created successfully!', 'success')
        return redirect(url_for('bridge.categories'))
    
    return render_template('bridge/category_form.html')


@bridge_bp.route('/categories/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_category(id):
    """Edit category"""
    category = TransactionCategory.query.get_or_404(id)
    
    if request.method == 'POST':
        category.name = request.form['name']
        category.erpnext_account = request.form['erpnext_account']
        category.transaction_type = request.form['transaction_type']
        category.keywords = request.form.get('keywords', '')
        category.active = request.form.get('active', 'true') == 'true'
        category.color = request.form.get('color', type=int)
        
        db.session.commit()
        
        flash('Category updated successfully!', 'success')
        return redirect(url_for('bridge.categories'))
    
    return render_template('bridge/category_form.html', category=category)


@bridge_bp.route('/categories/<int:id>/delete', methods=['POST'])
@login_required
def delete_category(id):
    """Delete category"""
    category = TransactionCategory.query.get_or_404(id)
    
    # Check if category is in use
    transaction_count = category.transactions.count()
    if transaction_count > 0:
        flash(f'Cannot delete: {transaction_count} transactions use this category', 'warning')
        return redirect(url_for('bridge.categories'))
    
    db.session.delete(category)
    db.session.commit()
    
    flash('Category deleted successfully!', 'success')
    return redirect(url_for('bridge.categories'))


@bridge_bp.route('/categories/<int:id>/transactions')
@login_required
def category_transactions(id):
    """View transactions in category"""
    category = TransactionCategory.query.get_or_404(id)
    page = request.args.get('page', 1, type=int)
    
    transactions = category.transactions.order_by(
        BankTransaction.date.desc()
    ).paginate(
        page=page,
        per_page=current_app.config['ITEMS_PER_PAGE']
    )
    
    return render_template('bridge/category_transactions.html', 
                         category=category, 
                         transactions=transactions)


@bridge_bp.route('/bulk-operations')
@login_required
def bulk_operations():
    """Bulk operations dashboard"""
    
    # Get statistics
    stats = {
        'total': BankTransaction.query.count(),
        'uncategorized': BankTransaction.query.filter_by(category_id=None).count(),
        'categorized': BankTransaction.query.filter(BankTransaction.category_id.isnot(None)).count(),
        'synced': BankTransaction.query.filter_by(erpnext_synced=True).count(),
        'ready_to_sync': BankTransaction.query.filter(
            BankTransaction.category_id.isnot(None),
            BankTransaction.erpnext_synced == False
        ).count(),
    }
    
    # Get ERPNext config status
    erpnext_config = ERPNextConfig.query.filter_by(active=True).first()
    
    # Recent activity
    recent_transactions = BankTransaction.query.order_by(
        BankTransaction.date.desc()
    ).limit(10).all()
    
    return render_template('bridge/bulk_operations.html',
                         stats=stats,
                         erpnext_config=erpnext_config,
                         recent_transactions=recent_transactions)


@bridge_bp.route('/bulk-operations/auto-categorize', methods=['POST'])
@login_required
def auto_categorize():
    """Auto-categorize all uncategorized transactions"""
    service = CategorizationService()
    
    try:
        categorized, total = service.auto_categorize_all()
        
        if categorized > 0:
            flash(f'✅ Successfully categorized {categorized} of {total} transactions', 'success')
        else:
            flash(f'ℹ️ No transactions could be auto-categorized. Consider adding keywords to categories.', 'info')
        
    except Exception as e:
        flash(f'❌ Error during categorization: {str(e)}', 'danger')
    
    return redirect(url_for('bridge.bulk_operations'))


@bridge_bp.route('/bulk-operations/sync-to-erpnext', methods=['POST'])
@login_required
def bulk_sync():
    """Bulk sync transactions to ERPNext"""
    
    config = ERPNextConfig.query.filter_by(active=True).first()
    if not config:
        flash('❌ No active ERPNext configuration found', 'danger')
        return redirect(url_for('bridge.bulk_operations'))
    
    service = BulkSyncService(config)
    
    try:
        success, failed, total = service.sync_all_ready()
        
        if success > 0:
            if failed == 0:
                flash(f'✅ Successfully synced all {success} transactions!', 'success')
            else:
                flash(f'⚠️ Synced {success} transactions, {failed} failed. Check sync logs for details.', 'warning')
        else:
            if total == 0:
                flash('ℹ️ No transactions ready to sync. Categorize transactions first.', 'info')
            else:
                flash(f'❌ Failed to sync {failed} transactions. Check sync logs for details.', 'danger')
        
    except Exception as e:
        flash(f'❌ Error during sync: {str(e)}', 'danger')
    
    return redirect(url_for('bridge.bulk_operations'))


@bridge_bp.route('/bulk-operations/preview-categorization', methods=['POST'])
@login_required
def preview_categorization():
    """Preview what will be categorized"""
    service = CategorizationService()
    
    preview = service.preview_categorization()
    
    return jsonify({
        'total_uncategorized': len(preview['uncategorized']),
        'will_be_categorized': len(preview['matches']),
        'no_match': len(preview['no_match']),
        'matches': [
            {
                'transaction_id': m['transaction'].id,
                'description': m['transaction'].description[:50],
                'category': m['category'].name,
                'keyword': m['keyword']
            }
            for m in preview['matches'][:20]  # First 20 for preview
        ]
    })


@bridge_bp.route('/transactions/<int:id>/categorize', methods=['POST'])
@login_required
def categorize_transaction(id):
    """Manually categorize a single transaction"""
    transaction = BankTransaction.query.get_or_404(id)
    
    category_id = request.form.get('category_id', type=int)
    if not category_id:
        flash('Please select a category', 'warning')
        return redirect(request.referrer or url_for('gmail.transactions'))
    
    category = TransactionCategory.query.get_or_404(category_id)
    
    transaction.category_id = category_id
    db.session.commit()
    
    flash(f'Transaction categorized as "{category.name}"', 'success')
    return redirect(request.referrer or url_for('gmail.transactions'))


@bridge_bp.route('/transactions/<int:id>/uncategorize', methods=['POST'])
@login_required
def uncategorize_transaction(id):
    """Remove category from transaction"""
    transaction = BankTransaction.query.get_or_404(id)
    
    if transaction.erpnext_synced:
        flash('Cannot uncategorize synced transaction', 'warning')
        return redirect(request.referrer or url_for('gmail.transactions'))
    
    transaction.category_id = None
    db.session.commit()
    
    flash('Transaction uncategorized', 'info')
    return redirect(request.referrer or url_for('gmail.transactions'))

