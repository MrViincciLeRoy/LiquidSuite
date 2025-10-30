"""
Gmail Blueprint - Handles Gmail integration
"""
from flask import Blueprint

gmail_bp = Blueprint('gmail', __name__, template_folder='templates')

from lsuite.gmail import routes

# ============================================================================
# gmail/routes.py
# ============================================================================
"""
Gmail Routes
"""
from flask import render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from lsuite.extensions import db
from lsuite.models import GoogleCredential, EmailStatement, BankTransaction
from lsuite.gmail.services import GmailService
from lsuite.gmail import gmail_bp


@gmail_bp.route('/credentials')
@login_required
def credentials():
    """List Google credentials"""
    creds = GoogleCredential.query.filter_by(user_id=current_user.id).all()
    return render_template('gmail/credentials.html', credentials=creds)


@gmail_bp.route('/credentials/new', methods=['GET', 'POST'])
@login_required
def new_credential():
    """Create new Google credential"""
    if request.method == 'POST':
        cred = GoogleCredential(
            user_id=current_user.id,
            name=request.form['name'],
            client_id=request.form['client_id'],
            client_secret=request.form['client_secret']
        )
        db.session.add(cred)
        db.session.commit()
        flash('Credential created successfully!', 'success')
        return redirect(url_for('gmail.credentials'))
    
    return render_template('gmail/credential_form.html')


@gmail_bp.route('/credentials/<int:id>/authenticate')
@login_required
def authenticate(id):
    """Start OAuth flow"""
    cred = GoogleCredential.query.get_or_404(id)
    
    if cred.user_id != current_user.id:
        flash('Unauthorized', 'danger')
        return redirect(url_for('gmail.credentials'))
    
    service = GmailService(current_app)
    auth_url = service.get_auth_url(cred)
    
    return redirect(auth_url)


@gmail_bp.route('/oauth/callback')
@login_required
def oauth_callback():
    """Handle OAuth callback"""
    code = request.args.get('code')
    state = request.args.get('state')
    
    if not code or not state:
        flash('OAuth failed', 'danger')
        return redirect(url_for('gmail.credentials'))
    
    cred = GoogleCredential.query.get(int(state))
    
    if not cred or cred.user_id != current_user.id:
        flash('Invalid state', 'danger')
        return redirect(url_for('gmail.credentials'))
    
    service = GmailService(current_app)
    success = service.exchange_code_for_tokens(cred, code)
    
    if success:
        flash('Successfully authenticated with Google!', 'success')
    else:
        flash('Authentication failed', 'danger')
    
    return redirect(url_for('gmail.credentials'))


@gmail_bp.route('/statements')
@login_required
def statements():
    """List email statements"""
    page = request.args.get('page', 1, type=int)
    statements = EmailStatement.query.order_by(
        EmailStatement.date.desc()
    ).paginate(
        page=page, 
        per_page=current_app.config['ITEMS_PER_PAGE']
    )
    
    return render_template('gmail/statements.html', statements=statements)


@gmail_bp.route('/statements/import', methods=['POST'])
@login_required
def import_statements():
    """Import statements from Gmail"""
    cred = GoogleCredential.query.filter_by(
        user_id=current_user.id,
        is_authenticated=True
    ).first()
    
    if not cred:
        flash('No authenticated Google credential found', 'warning')
        return redirect(url_for('gmail.credentials'))
    
    service = GmailService(current_app)
    imported_count, skipped_count = service.fetch_statements(cred)
    
    flash(f'Imported {imported_count} statements ({skipped_count} already existed)', 'success')
    return redirect(url_for('gmail.statements'))


@gmail_bp.route('/statements/<int:id>')
@login_required
def statement_detail(id):
    """View statement details"""
    statement = EmailStatement.query.get_or_404(id)
    return render_template('gmail/statement_detail.html', statement=statement)


@gmail_bp.route('/statements/<int:id>/parse', methods=['POST'])
@login_required
def parse_statement(id):
    """Parse PDF and extract transactions"""
    statement = EmailStatement.query.get_or_404(id)
    
    cred = GoogleCredential.query.filter_by(
        user_id=current_user.id,
        is_authenticated=True
    ).first()
    
    if not cred:
        flash('No authenticated Google credential found', 'warning')
        return redirect(url_for('gmail.credentials'))
    
    service = GmailService(current_app)
    
    try:
        count = service.download_and_parse_pdf(cred, statement)
        flash(f'Successfully parsed {count} transactions!', 'success')
    except Exception as e:
        flash(f'Parsing failed: {str(e)}', 'danger')
    
    return redirect(url_for('gmail.statement_detail', id=id))


@gmail_bp.route('/transactions')
@login_required
def transactions():
    """List all transactions"""
    page = request.args.get('page', 1, type=int)
    
    query = BankTransaction.query.order_by(BankTransaction.date.desc())
    
    # Filters
    if request.args.get('uncategorized'):
        query = query.filter_by(category_id=None)
    
    if request.args.get('not_synced'):
        query = query.filter_by(erpnext_synced=False)
    
    transactions = query.paginate(
        page=page,
        per_page=current_app.config['ITEMS_PER_PAGE']
    )
    
    return render_template('gmail/transactions.html', transactions=transactions)
