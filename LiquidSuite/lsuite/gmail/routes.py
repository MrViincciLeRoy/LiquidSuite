# ============================================================================
# LiquidSuite/lsuite/gmail/routes.py - COMPLETE FIXED VERSION
# ============================================================================
"""
Gmail Routes - OAuth, Statement Import, CSV Upload
"""
from flask import render_template, redirect, url_for, flash, request, current_app, make_response
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from datetime import datetime
import logging

from lsuite.extensions import db
from lsuite.models import (
    GoogleCredential, EmailStatement, BankTransaction, 
    TransactionCategory
)
from lsuite.gmail.services import GmailService
from lsuite.gmail.csv_parser import CSVParser
from lsuite.gmail import gmail_bp

logger = logging.getLogger(__name__)


# ============================================================================
# Google OAuth Routes
# ============================================================================

@gmail_bp.route('/credentials')
@login_required
def credentials():
    """List Google OAuth credentials"""
    creds = GoogleCredential.query.filter_by(user_id=current_user.id).all()
    return render_template('gmail/credentials.html', credentials=creds)


@gmail_bp.route('/credentials/new', methods=['GET', 'POST'])
@login_required
def new_credential():
    """Create new Google OAuth credential"""
    if request.method == 'POST':
        credential = GoogleCredential(
            user_id=current_user.id,
            name=request.form['name'],
            client_id=request.form['client_id'],
            client_secret=request.form['client_secret']
        )
        
        db.session.add(credential)
        db.session.commit()
        
        flash('Google credential created! Now authorize access.', 'success')
        return redirect(url_for('gmail.authorize', id=credential.id))
    
    return render_template('gmail/credential_form.html')


@gmail_bp.route('/credentials/<int:id>/authorize')
@login_required
def authorize(id):
    """Start OAuth authorization flow"""
    credential = GoogleCredential.query.get_or_404(id)
    
    if credential.user_id != current_user.id:
        flash('Unauthorized', 'danger')
        return redirect(url_for('gmail.credentials'))
    
    service = GmailService(current_app)
    auth_url = service.get_auth_url(credential)
    
    return redirect(auth_url)


@gmail_bp.route('/oauth/callback')
@login_required
def oauth_callback():
    """OAuth callback handler"""
    code = request.args.get('code')
    state = request.args.get('state')
    
    if not code or not state:
        flash('OAuth authorization failed', 'danger')
        return redirect(url_for('gmail.credentials'))
    
    credential = GoogleCredential.query.get(int(state))
    
    if not credential or credential.user_id != current_user.id:
        flash('Invalid credential', 'danger')
        return redirect(url_for('gmail.credentials'))
    
    service = GmailService(current_app)
    success = service.exchange_code_for_tokens(credential, code)
    
    if success:
        flash('✅ Gmail access authorized!', 'success')
    else:
        flash('❌ Authorization failed', 'danger')
    
    return redirect(url_for('gmail.credentials'))


@gmail_bp.route('/credentials/<int:id>/delete', methods=['POST'])
@login_required
def delete_credential(id):
    """Delete Google OAuth credential"""
    credential = GoogleCredential.query.get_or_404(id)
    
    if credential.user_id != current_user.id:
        flash('Unauthorized', 'danger')
        return redirect(url_for('gmail.credentials'))
    
    db.session.delete(credential)
    db.session.commit()
    
    flash('Credential deleted', 'success')
    return redirect(url_for('gmail.credentials'))


# ============================================================================
# Email Statement Routes
# ============================================================================

@gmail_bp.route('/statements')
@login_required
def statements():
    """List email statements"""
    page = request.args.get('page', 1, type=int)
    per_page = current_app.config.get('ITEMS_PER_PAGE', 20)
    
    statements = EmailStatement.query.filter_by(
        user_id=current_user.id
    ).order_by(
        EmailStatement.received_date.desc()
    ).paginate(page=page, per_page=per_page, error_out=False)
    
    return render_template('gmail/statements.html', statements=statements)


@gmail_bp.route('/statements/import', methods=['POST'])
@login_required
def import_statements():
    """Import statements from Gmail"""
    credential = GoogleCredential.query.filter_by(
        user_id=current_user.id,
        is_authenticated=True
    ).first()
    
    if not credential:
        flash('No authenticated Google credential found', 'danger')
        return redirect(url_for('gmail.credentials'))
    
    try:
        service = GmailService(current_app)
        imported, skipped = service.fetch_statements(credential)
        
        flash(f'✅ Imported {imported} statements ({skipped} already existed)', 'success')
    except Exception as e:
        flash(f'❌ Import failed: {str(e)}', 'danger')
        logger.error(f"Statement import error: {str(e)}")
    
    return redirect(url_for('gmail.statements'))


@gmail_bp.route('/statements/<int:id>')
@login_required
def statement_detail(id):
    """View statement details"""
    statement = EmailStatement.query.get_or_404(id)
    
    if statement.user_id != current_user.id:
        flash('Unauthorized', 'danger')
        return redirect(url_for('gmail.statements'))
    
    transactions = BankTransaction.query.filter_by(
        statement_id=statement.id
    ).order_by(BankTransaction.date.desc()).all()
    
    return render_template('gmail/statement_detail.html', 
                         statement=statement, 
                         transactions=transactions)


@gmail_bp.route('/statements/<int:id>/parse', methods=['POST'])
@login_required
def parse_statement(id):
    """Parse PDF from statement with password support - FIXED VERSION"""
    statement = EmailStatement.query.get_or_404(id)
    
    if statement.user_id != current_user.id:
        flash('Unauthorized', 'danger')
        return redirect(url_for('gmail.statements'))
    
    credential = GoogleCredential.query.filter_by(
        user_id=current_user.id,
        is_authenticated=True
    ).first()
    
    if not credential:
        flash('No authenticated Google credential', 'danger')
        return redirect(url_for('gmail.statements'))
    
    # ✅ FIX: Get password from form - check for 'yes' value
    pdf_password = request.form.get('pdf_password', '').strip()
    save_password = request.form.get('save_password') == 'yes'
    
    logger.info(f"Parse request for statement {id}")
    logger.info(f"Password provided: {'Yes' if pdf_password else 'No'} (length: {len(pdf_password) if pdf_password else 0})")
    logger.info(f"Save password: {save_password}")
    logger.info(f"Existing saved password: {'Yes' if statement.pdf_password else 'No'}")
    
    # Determine which password to use: new password takes priority, then saved password
    password_to_use = pdf_password if pdf_password else statement.pdf_password
    
    # Save password if requested and provided
    if save_password and pdf_password:
        statement.pdf_password = pdf_password
        db.session.commit()
        logger.info(f"Saved password for statement {id}")
    
    # Log what we're using
    if password_to_use:
        logger.info(f"Using password for parsing (length: {len(password_to_use)})")
    else:
        logger.warning(f"No password available for statement {id}")
    
    try:
        service = GmailService(current_app)
        
        # ✅ FIX: Temporarily update statement password for parsing
        old_password = statement.pdf_password
        statement.pdf_password = password_to_use
        
        # Parse the PDF
        transaction_count = service.download_and_parse_pdf(credential, statement)
        
        # Restore old password if we didn't save the new one
        if not save_password and pdf_password:
            statement.pdf_password = old_password
            db.session.commit()
        
        flash(f'✅ Successfully extracted {transaction_count} transactions', 'success')
        logger.info(f"Successfully parsed {transaction_count} transactions from statement {id}")
        
    except ValueError as e:
        # ✅ FIX: Better error handling for password-related errors
        error_msg = str(e)
        if 'password' in error_msg.lower():
            flash(f'❌ {error_msg}. Please enter the correct PDF password.', 'danger')
            logger.error(f"Password error for statement {id}: {error_msg}")
        else:
            flash(f'❌ Parse failed: {error_msg}', 'danger')
            logger.error(f"Parse error for statement {id}: {error_msg}")
    except Exception as e:
        flash(f'❌ Parse failed: {str(e)}', 'danger')
        logger.error(f"Unexpected error parsing statement {id}: {str(e)}", exc_info=True)
    
    return redirect(url_for('gmail.statement_detail', id=id))


# ============================================================================
# Transaction Routes
# ============================================================================

@gmail_bp.route('/transactions')
@login_required
def transactions():
    """List all transactions"""
    page = request.args.get('page', 1, type=int)
    per_page = current_app.config.get('ITEMS_PER_PAGE', 20)
    
    query = BankTransaction.query.filter_by(user_id=current_user.id)
    
    # Apply filters
    if request.args.get('uncategorized'):
        query = query.filter_by(category_id=None)
    
    if request.args.get('not_synced'):
        query = query.filter_by(erpnext_synced=False)
    
    category_id = request.args.get('category_id', type=int)
    if category_id:
        query = query.filter_by(category_id=category_id)
    
    statement_id = request.args.get('statement_id', type=int)
    if statement_id:
        query = query.filter_by(statement_id=statement_id)
    
    # Order and paginate
    transactions = query.order_by(
        BankTransaction.date.desc()
    ).paginate(page=page, per_page=per_page, error_out=False)
    
    # Get categories for filter dropdown
    categories = TransactionCategory.query.filter_by(active=True).all()
    
    return render_template('gmail/transactions.html', 
                         transactions=transactions,
                         categories=categories)


@gmail_bp.route('/transactions/<int:id>')
@login_required
def transaction_detail(id):
    """View transaction details"""
    transaction = BankTransaction.query.get_or_404(id)
    
    if transaction.user_id != current_user.id:
        flash('Unauthorized', 'danger')
        return redirect(url_for('gmail.transactions'))
    
    return render_template('gmail/transaction_detail.html', transaction=transaction)


# ============================================================================
# CSV Upload Routes
# ============================================================================

@gmail_bp.route('/upload-csv', methods=['GET', 'POST'])
@login_required
def upload_csv():
    """Upload and import CSV transactions"""
    if request.method == 'POST':
        # Check if file was uploaded
        if 'csv_file' not in request.files:
            flash('No file selected', 'warning')
            return redirect(request.url)
        
        file = request.files['csv_file']
        
        if file.filename == '':
            flash('No file selected', 'warning')
            return redirect(request.url)
        
        if not file.filename.endswith('.csv'):
            flash('Please upload a CSV file', 'warning')
            return redirect(request.url)
        
        try:
            # Read CSV data
            csv_data = file.read()
            
            # Get optional parameters
            bank_account = request.form.get('bank_account', '').strip()
            create_statement = request.form.get('create_statement') == 'on'
            
            # Parse CSV
            parser = CSVParser()
            transactions = parser.parse_csv(csv_data)
            
            if not transactions:
                flash('No valid transactions found in CSV file', 'warning')
                return redirect(request.url)
            
            # Create statement if requested
            statement_id = None
            if create_statement:
                statement = EmailStatement(
                    user_id=current_user.id,
                    gmail_id=f"CSV-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}",
                    subject=f"CSV Import: {secure_filename(file.filename)}",
                    sender='CSV Upload',
                    received_date=datetime.utcnow(),
                    bank_name='capitec',
                    is_processed=True,
                    has_pdf=False
                )
                db.session.add(statement)
                db.session.flush()
                statement_id = statement.id
            
            # Import transactions
            imported_count = 0
            skipped_count = 0
            
            for trans_data in transactions:
                # Check for duplicates
                existing = BankTransaction.query.filter_by(
                    user_id=current_user.id,
                    date=trans_data['transaction_date'],
                    description=trans_data['description'],
                ).filter(
                    (BankTransaction.withdrawal == trans_data['debits']) |
                    (BankTransaction.deposit == trans_data['credits'])
                ).first()
                
                if existing:
                    skipped_count += 1
                    continue
                
                # Create transaction with proper field mapping
                transaction = BankTransaction(
                    user_id=current_user.id,
                    statement_id=statement_id,
                    date=trans_data['transaction_date'],
                    posting_date=trans_data['posting_date'],
                    description=trans_data['description'],
                    withdrawal=trans_data['debits'],
                    deposit=trans_data['credits'],
                    balance=trans_data['balance'],
                    reference_number=trans_data['reference']
                )
                db.session.add(transaction)
                imported_count += 1
            
            db.session.commit()
            
            flash(f'✅ Successfully imported {imported_count} transactions ({skipped_count} duplicates skipped)', 'success')
            return redirect(url_for('gmail.transactions'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'❌ Error importing CSV: {str(e)}', 'danger')
            logger.error(f"CSV import error: {str(e)}", exc_info=True)
            return redirect(request.url)
    
    return render_template('gmail/upload_csv.html')


@gmail_bp.route('/download-csv-template')
@login_required
def download_csv_template():
    """Download CSV template"""
    template = """Transaction Date,Posting Date,Description,Debits,Credits,Balance,Bank account
2025/09/23,2025/09/23,Sample Transaction,,1000.00,5000.00,5443 - Capitec Savings Account
2025/09/24,2025/09/24,Sample Payment,500.00,,4500.00,5443 - Capitec Savings Account"""
    
    response = make_response(template)
    response.headers['Content-Type'] = 'text/csv'
    response.headers['Content-Disposition'] = 'attachment; filename=transaction_template.csv'
    
    return response


@gmail_bp.route('/bulk-csv-import', methods=['GET', 'POST'])
@login_required
def bulk_csv_import():
    """Bulk import multiple CSV files"""
    if request.method == 'POST':
        files = request.files.getlist('csv_files')
        
        if not files:
            flash('No files selected', 'warning')
            return redirect(request.url)
        
        total_imported = 0
        total_skipped = 0
        files_processed = 0
        
        parser = CSVParser()
        
        for file in files:
            if not file.filename.endswith('.csv'):
                continue
            
            try:
                csv_data = file.read()
                transactions = parser.parse_csv(csv_data)
                
                # Create statement for this file
                statement = EmailStatement(
                    user_id=current_user.id,
                    gmail_id=f"CSV-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}-{files_processed}",
                    subject=f"CSV Import: {secure_filename(file.filename)}",
                    sender='Bulk CSV Upload',
                    received_date=datetime.utcnow(),
                    bank_name='capitec',
                    is_processed=True,
                    has_pdf=False
                )
                db.session.add(statement)
                db.session.flush()
                
                imported = 0
                skipped = 0
                
                for trans_data in transactions:
                    # Check for duplicates
                    existing = BankTransaction.query.filter_by(
                        user_id=current_user.id,
                        date=trans_data['transaction_date'],
                        description=trans_data['description'],
                    ).filter(
                        (BankTransaction.withdrawal == trans_data['debits']) |
                        (BankTransaction.deposit == trans_data['credits'])
                    ).first()
                    
                    if existing:
                        skipped += 1
                        continue
                    
                    transaction = BankTransaction(
                        user_id=current_user.id,
                        statement_id=statement.id,
                        date=trans_data['transaction_date'],
                        posting_date=trans_data['posting_date'],
                        description=trans_data['description'],
                        withdrawal=trans_data['debits'],
                        deposit=trans_data['credits'],
                        balance=trans_data['balance'],
                        reference_number=trans_data['reference']
                    )
                    db.session.add(transaction)
                    imported += 1
                
                total_imported += imported
                total_skipped += skipped
                files_processed += 1
                
            except Exception as e:
                logger.error(f"Error processing {file.filename}: {str(e)}")
                continue
        
        db.session.commit()
        
        flash(f'✅ Processed {files_processed} files: {total_imported} imported, {total_skipped} skipped', 'success')
        return redirect(url_for('gmail.transactions'))
    
    return render_template('gmail/bulk_csv_import.html')
