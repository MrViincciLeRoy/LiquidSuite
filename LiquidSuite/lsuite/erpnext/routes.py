# ============================================================================
# LiquidSuite/lsuite/erpnext/routes.py - CORRECTED VERSION
# ============================================================================
"""
ERPNext Routes - Configuration and Sync Management
"""
from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from lsuite.extensions import db
from lsuite.models import ERPNextConfig, ERPNextSyncLog, BankTransaction
from lsuite.erpnext.services import ERPNextService
from lsuite.erpnext import erpnext_bp


@erpnext_bp.route('/configs')
@login_required
def configs():
    """List ERPNext configurations"""
    configs = ERPNextConfig.query.filter_by(user_id=current_user.id).all()
    return render_template('erpnext/configs.html', configs=configs)


@erpnext_bp.route('/configs/new', methods=['GET', 'POST'])
@login_required
def new_config():
    """Create new ERPNext configuration"""
    if request.method == 'POST':
        config = ERPNextConfig(
            user_id=current_user.id,
            name=request.form['name'],
            base_url=request.form['base_url'],
            api_key=request.form['api_key'],
            api_secret=request.form['api_secret'],
            default_company=request.form.get('default_company', ''),
            bank_account=request.form.get('bank_account', ''),
            default_cost_center=request.form.get('default_cost_center', ''),
            is_active=request.form.get('is_active', 'false') == 'true'
        )
        
        # Test connection
        service = ERPNextService(config)
        success, message = service.test_connection()
        
        if not success:
            flash(f'Connection test failed: {message}', 'danger')
            return render_template('erpnext/config_form.html', config=config)
        
        db.session.add(config)
        db.session.commit()
        
        flash(f'Configuration created successfully! {message}', 'success')
        return redirect(url_for('erpnext.configs'))
    
    return render_template('erpnext/config_form.html')


@erpnext_bp.route('/configs/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_config(id):
    """Edit ERPNext configuration"""
    config = ERPNextConfig.query.get_or_404(id)
    
    if config.user_id != current_user.id:
        flash('Unauthorized', 'danger')
        return redirect(url_for('erpnext.configs'))
    
    if request.method == 'POST':
        config.name = request.form['name']
        config.base_url = request.form['base_url']
        config.api_key = request.form['api_key']
        config.api_secret = request.form['api_secret']
        config.default_company = request.form.get('default_company', '')
        config.bank_account = request.form.get('bank_account', '')
        config.default_cost_center = request.form.get('default_cost_center', '')
        config.is_active = request.form.get('is_active', 'false') == 'true'
        
        # Test connection
        service = ERPNextService(config)
        success, message = service.test_connection()
        
        if not success:
            flash(f'Connection test failed: {message}', 'warning')
        
        db.session.commit()
        
        flash('Configuration updated successfully!', 'success')
        return redirect(url_for('erpnext.configs'))
    
    return render_template('erpnext/config_form.html', config=config)


@erpnext_bp.route('/configs/<int:id>/test', methods=['POST'])
@login_required
def test_config(id):
    """Test ERPNext connection"""
    config = ERPNextConfig.query.get_or_404(id)
    
    if config.user_id != current_user.id:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    service = ERPNextService(config)
    success, message = service.test_connection()
    
    return jsonify({'success': success, 'message': message})


@erpnext_bp.route('/configs/<int:id>/delete', methods=['POST'])
@login_required
def delete_config(id):
    """Delete ERPNext configuration"""
    config = ERPNextConfig.query.get_or_404(id)
    
    if config.user_id != current_user.id:
        flash('Unauthorized', 'danger')
        return redirect(url_for('erpnext.configs'))
    
    db.session.delete(config)
    db.session.commit()
    
    flash('Configuration deleted successfully!', 'success')
    return redirect(url_for('erpnext.configs'))


@erpnext_bp.route('/configs/<int:id>/activate', methods=['POST'])
@login_required
def activate_config(id):
    """Set configuration as active"""
    config = ERPNextConfig.query.get_or_404(id)
    
    if config.user_id != current_user.id:
        flash('Unauthorized', 'danger')
        return redirect(url_for('erpnext.configs'))
    
    # Deactivate all other configs
    ERPNextConfig.query.filter_by(user_id=current_user.id).update({'is_active': False})
    
    # Activate this config
    config.is_active = True
    db.session.commit()
    
    flash(f'"{config.name}" is now the active configuration', 'success')
    return redirect(url_for('erpnext.configs'))


@erpnext_bp.route('/sync-logs')
@login_required
def sync_logs():
    """View sync logs"""
    page = request.args.get('page', 1, type=int)
    per_page = 50
    
    logs = ERPNextSyncLog.query.join(ERPNextConfig).filter(
        ERPNextConfig.user_id == current_user.id
    ).order_by(
        ERPNextSyncLog.sync_date.desc()
    ).paginate(page=page, per_page=per_page, error_out=False)
    
    return render_template('erpnext/sync_logs.html', logs=logs)


@erpnext_bp.route('/transactions/<int:id>/sync', methods=['POST'])
@login_required
def sync_transaction(id):
    """Sync single transaction to ERPNext"""
    transaction = BankTransaction.query.get_or_404(id)
    
    if transaction.user_id != current_user.id:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    if not transaction.category_id:
        return jsonify({'success': False, 'message': 'Transaction must be categorized first'}), 400
    
    config = ERPNextConfig.query.filter_by(
        user_id=current_user.id,
        is_active=True
    ).first()
    
    if not config:
        return jsonify({'success': False, 'message': 'No active ERPNext configuration'}), 400
    
    try:
        service = ERPNextService(config)
        journal_entry_name = service.create_journal_entry(transaction)
        
        return jsonify({
            'success': True,
            'message': f'Synced successfully: {journal_entry_name}',
            'journal_entry': journal_entry_name
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@erpnext_bp.route('/fetch-accounts')
@login_required
def fetch_accounts():
    """Fetch chart of accounts from ERPNext"""
    config = ERPNextConfig.query.filter_by(
        user_id=current_user.id,
        is_active=True
    ).first()
    
    if not config:
        return jsonify({'success': False, 'message': 'No active ERPNext configuration'}), 400
    
    try:
        service = ERPNextService(config)
        accounts = service.get_chart_of_accounts()
        
        return jsonify({
            'success': True,
            'accounts': accounts
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@erpnext_bp.route('/fetch-cost-centers')
@login_required
def fetch_cost_centers():
    """Fetch cost centers from ERPNext"""
    config = ERPNextConfig.query.filter_by(
        user_id=current_user.id,
        is_active=True
    ).first()
    
    if not config:
        return jsonify({'success': False, 'message': 'No active ERPNext configuration'}), 400
    
    try:
        service = ERPNextService(config)
        cost_centers = service.get_cost_centers()
        
        return jsonify({
            'success': True,
            'cost_centers': cost_centers
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500
