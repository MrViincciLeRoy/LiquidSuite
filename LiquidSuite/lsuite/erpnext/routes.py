# ============================================================================
# lsuite/erpnext/routes.py
# ============================================================================
"""
ERPNext Routes - Configuration and Sync Management
"""
from flask import render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from lsuite.extensions import db
from lsuite.models import ERPNextConfig, ERPNextSyncLog, BankTransaction
from lsuite.erpnext.services import ERPNextService
from lsuite.erpnext import erpnext_bp


@erpnext_bp.route('/configs')
@login_required
def configs():
    """List ERPNext configurations"""
    configs = ERPNextConfig.query.all()
    return render_template('erpnext/configs.html', configs=configs)


@erpnext_bp.route('/configs/new', methods=['GET', 'POST'])
@login_required
def new_config():
    """Create new ERPNext configuration"""
    if request.method == 'POST':
        config = ERPNextConfig(
            name=request.form['name'],
            base_url=request.form['base_url'].rstrip('/'),
            api_key=request.form['api_key'],
            api_secret=request.form['api_secret'],
            default_company=request.form['default_company'],
            bank_account=request.form['bank_account'],
            default_cost_center=request.form.get('default_cost_center', ''),
            active=request.form.get('active', 'true') == 'true'
        )
        
        db.session.add(config)
        db.session.commit()
        
        flash('ERPNext configuration created successfully!', 'success')
        return redirect(url_for('erpnext.configs'))
    
    return render_template('erpnext/config_form.html')


@erpnext_bp.route('/configs/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_config(id):
    """Edit ERPNext configuration"""
    config = ERPNextConfig.query.get_or_404(id)
    
    if request.method == 'POST':
        config.name = request.form['name']
        config.base_url = request.form['base_url'].rstrip('/')
        config.api_key = request.form['api_key']
        config.api_secret = request.form['api_secret']
        config.default_company = request.form['default_company']
        config.bank_account = request.form['bank_account']
        config.default_cost_center = request.form.get('default_cost_center', '')
        config.active = request.form.get('active', 'true') == 'true'
        
        db.session.commit()
        
        flash('Configuration updated successfully!', 'success')
        return redirect(url_for('erpnext.configs'))
    
    return render_template('erpnext/config_form.html', config=config)


@erpnext_bp.route('/configs/<int:id>/test', methods=['POST'])
@login_required
def test_connection(id):
    """Test ERPNext connection"""
    config = ERPNextConfig.query.get_or_404(id)
    service = ERPNextService(config)
    
    success, message = service.test_connection()
    
    if success:
        flash(f'✅ Connection successful! {message}', 'success')
    else:
        flash(f'❌ Connection failed: {message}', 'danger')
    
    return redirect(url_for('erpnext.configs'))


@erpnext_bp.route('/configs/<int:id>/delete', methods=['POST'])
@login_required
def delete_config(id):
    """Delete ERPNext configuration"""
    config = ERPNextConfig.query.get_or_404(id)
    
    # Check if there are synced transactions
    synced_count = BankTransaction.query.filter_by(erpnext_synced=True).count()
    
    if synced_count > 0:
        flash(f'Cannot delete: {synced_count} transactions are synced with this configuration', 'warning')
        return redirect(url_for('erpnext.configs'))
    
    db.session.delete(config)
    db.session.commit()
    
    flash('Configuration deleted successfully!', 'success')
    return redirect(url_for('erpnext.configs'))


@erpnext_bp.route('/sync-logs')
@login_required
def sync_logs():
    """View sync logs"""
    page = request.args.get('page', 1, type=int)
    
    query = ERPNextSyncLog.query.order_by(ERPNextSyncLog.sync_date.desc())
    
    # Filters
    status = request.args.get('status')
    if status:
        query = query.filter_by(status=status)
    
    config_id = request.args.get('config_id', type=int)
    if config_id:
        query = query.filter_by(config_id=config_id)
    
    logs = query.paginate(
        page=page,
        per_page=current_app.config['ITEMS_PER_PAGE']
    )
    
    configs = ERPNextConfig.query.all()
    
    return render_template('erpnext/sync_logs.html', logs=logs, configs=configs)


@erpnext_bp.route('/sync-logs/<int:id>')
@login_required
def sync_log_detail(id):
    """View sync log details"""
    log = ERPNextSyncLog.query.get_or_404(id)
    
    # Get related transaction if applicable
    transaction = None
    if log.record_type == 'bank_transaction':
        transaction = BankTransaction.query.get(log.record_id)
    
    return render_template('erpnext/sync_log_detail.html', log=log, transaction=transaction)


@erpnext_bp.route('/sync-logs/<int:id>/retry', methods=['POST'])
@login_required
def retry_sync(id):
    """Retry failed sync"""
    log = ERPNextSyncLog.query.get_or_404(id)
    
    if log.status != 'failed':
        flash('Only failed syncs can be retried', 'warning')
        return redirect(url_for('erpnext.sync_logs'))
    
    if log.record_type == 'bank_transaction':
        transaction = BankTransaction.query.get(log.record_id)
        if not transaction:
            flash('Transaction not found', 'danger')
            return redirect(url_for('erpnext.sync_logs'))
        
        config = log.config or ERPNextConfig.query.filter_by(active=True).first()
        if not config:
            flash('No active ERPNext configuration found', 'danger')
            return redirect(url_for('erpnext.sync_logs'))
        
        service = ERPNextService(config)
        
        try:
            service.create_journal_entry(transaction)
            flash('Transaction synced successfully!', 'success')
        except Exception as e:
            flash(f'Sync failed: {str(e)}', 'danger')
    
    return redirect(url_for('erpnext.sync_logs'))
