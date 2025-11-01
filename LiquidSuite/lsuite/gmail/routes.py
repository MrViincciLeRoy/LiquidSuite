"""
CSV Upload Routes
Add these routes to lsuite/gmail/routes.py
"""
from flask import render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
import os
from lsuite.extensions import db
from lsuite.models import BankTransaction, EmailStatement
from lsuite.gmail.csv_parser import CSVParser
from lsuite.gmail import gmail_bp


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
                    gmail_id=f"CSV-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}",
                    subject=f"CSV Import: {secure_filename(file.filename)}",
                    sender='CSV Upload',
                    date=datetime.utcnow(),
                    bank_name='capitec',
                    state='parsed',
                    has_pdf=False
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
                    transaction_date=trans_data['transaction_date'],
                    description=trans_data['description'],
                ).filter(
                    (BankTransaction.debits == trans_data['debits']) |
                    (BankTransaction.credits == trans_data['credits'])
                ).first()
                
                if existing:
                    skipped_count += 1
                    continue
                
                # Create transaction
                transaction = BankTransaction(
                    statement_id=statement_id,
                    transaction_date=trans_data['transaction_date'],
                    posting_date=trans_data['posting_date'],
                    description=trans_data['description'],
                    debits=trans_data['debits'],
                    credits=trans_data['credits'],
                    balance=trans_data['balance'],
                    bank_account=trans_data['bank_account'] or bank_account,
                    reference=trans_data['reference']
                )
                db.session.add(transaction)
                imported_count += 1
            
            db.session.commit()
            
            flash(f'? Successfully imported {imported_count} transactions ({skipped_count} duplicates skipped)', 'success')
            return redirect(url_for('gmail.transactions'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'? Error importing CSV: {str(e)}', 'danger')
            logger.error(f"CSV import error: {str(e)}")
            return redirect(request.url)
    
    return render_template('gmail/upload_csv.html')


@gmail_bp.route('/download-csv-template')
@login_required
def download_csv_template():
    """Download CSV template"""
    from flask import make_response
    
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
                    gmail_id=f"CSV-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}-{files_processed}",
                    subject=f"CSV Import: {secure_filename(file.filename)}",
                    sender='Bulk CSV Upload',
                    date=datetime.utcnow(),
                    bank_name='capitec',
                    state='parsed',
                    has_pdf=False
                )
                db.session.add(statement)
                db.session.flush()
                
                imported = 0
                skipped = 0
                
                for trans_data in transactions:
                    # Check for duplicates
                    existing = BankTransaction.query.filter_by(
                        transaction_date=trans_data['transaction_date'],
                        description=trans_data['description'],
                    ).filter(
                        (BankTransaction.debits == trans_data['debits']) |
                        (BankTransaction.credits == trans_data['credits'])
                    ).first()
                    
                    if existing:
                        skipped += 1
                        continue
                    
                    transaction = BankTransaction(
                        statement_id=statement.id,
                        transaction_date=trans_data['transaction_date'],
                        posting_date=trans_data['posting_date'],
                        description=trans_data['description'],
                        debits=trans_data['debits'],
                        credits=trans_data['credits'],
                        balance=trans_data['balance'],
                        bank_account=trans_data['bank_account'],
                        reference=trans_data['reference']
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
        
        flash(f'? Processed {files_processed} files: {total_imported} imported, {total_skipped} skipped', 'success')
        return redirect(url_for('gmail.transactions'))
    
    return render_template('gmail/bulk_csv_import.html')
