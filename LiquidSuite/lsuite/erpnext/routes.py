# ============================================================================
# FILE 5: LiquidSuite/lsuite/gmail/routes.py - CSV UPLOAD FIX
# ============================================================================
"""
Gmail Routes - Including CSV Upload
FIXED: Proper field mapping for BankTransaction
"""
from flask import render_template, redirect, url_for, flash, request, current_app, make_response
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from datetime import datetime
import logging
from lsuite.extensions import db
from lsuite.models import BankTransaction, EmailStatement
from lsuite.gmail.csv_parser import CSVParser
from lsuite.gmail import gmail_bp

logger = logging.getLogger(__name__)


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
                    email_id=f"CSV-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}",
                    subject=f"CSV Import: {secure_filename(file.filename)}",
                    sender='CSV Upload',
                    received_date=datetime.utcnow(),
                    bank_name='capitec',
                    is_processed=True,
                    has_attachments=False
                )
                db.session.add(statement)
                db.session.flush()
                statement_id = statement.id
            
            # Import transactions
            imported_count = 0
            skipped_count = 0
            
            for trans_data in transactions:
                # Check for duplicates (same date, description, and amount)
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
                
                # ✅ FIXED: Proper field mapping
                transaction = BankTransaction(
                    user_id=current_user.id,
                    statement_id=statement_id,
                    date=trans_data['transaction_date'],           # ✅ date (not transaction_date)
                    posting_date=trans_data['posting_date'],
                    description=trans_data['description'],
                    withdrawal=trans_data['debits'],               # ✅ debits → withdrawal
                    deposit=trans_data['credits'],                 # ✅ credits → deposit
                    balance=trans_data['balance'],
                    reference_number=trans_data['reference']       # ✅ reference → reference_number
                )
                db.session.add(transaction)
                imported_count += 1
            
            db.session.commit()
            
            flash(f'✅ Successfully imported {imported_count} transactions ({skipped_count} duplicates skipped)', 'success')
            return redirect(url_for('gmail.transactions'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'❌ Error importing CSV: {str(e)}', 'danger')
            logger.error(f"CSV import error: {str(e)}")
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
    
    # Order and paginate
    transactions = query.order_by(BankTransaction.date.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return render_template('gmail/transactions.html', transactions=transactions)
