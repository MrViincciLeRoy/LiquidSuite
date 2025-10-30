# ============================================================================
# lsuite/api/serializers.py
# ============================================================================
"""
API Serializers
"""

def serialize_statement(statement):
    """Serialize email statement"""
    return {
        'id': statement.id,
        'gmail_id': statement.gmail_id,
        'subject': statement.subject,
        'sender': statement.sender,
        'date': statement.date.isoformat() if statement.date else None,
        'bank_name': statement.bank_name,
        'state': statement.state,
        'has_pdf': statement.has_pdf,
        'transaction_count': statement.transaction_count,
        'created_at': statement.created_at.isoformat() if statement.created_at else None
    }


def serialize_transaction(transaction):
    """Serialize bank transaction"""
    return {
        'id': transaction.id,
        'statement_id': transaction.statement_id,
        'date': transaction.date.isoformat() if transaction.date else None,
        'description': transaction.description,
        'amount': float(transaction.amount),
        'transaction_type': transaction.transaction_type,
        'reference': transaction.reference,
        'category': {
            'id': transaction.category.id,
            'name': transaction.category.name
        } if transaction.category else None,
        'is_categorized': transaction.is_categorized,
        'erpnext_synced': transaction.erpnext_synced,
        'erpnext_journal_entry': transaction.erpnext_journal_entry,
        'erpnext_sync_date': transaction.erpnext_sync_date.isoformat() if transaction.erpnext_sync_date else None,
        'state': transaction.state,
        'created_at': transaction.created_at.isoformat() if transaction.created_at else None
    }


def serialize_category(category):
    """Serialize transaction category"""
    return {
        'id': category.id,
        'name': category.name,
        'erpnext_account': category.erpnext_account,
        'transaction_type': category.transaction_type,
        'keywords': category.keywords,
        'active': category.active,
        'transaction_count': category.transactions.count(),
        'created_at': category.created_at.isoformat() if category.created_at else None
    }


def serialize_sync_log(log):
    """Serialize sync log"""
    return {
        'id': log.id,
        'config_id': log.config_id,
        'record_type': log.record_type,
        'record_id': log.record_id,
        'erpnext_doctype': log.erpnext_doctype,
        'erpnext_doc_name': log.erpnext_doc_name,
        'status': log.status,
        'error_message': log.error_message,
        'sync_date': log.sync_date.isoformat() if log.sync_date else None
    }

