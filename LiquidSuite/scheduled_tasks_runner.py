#!/usr/bin/env python
"""
Scheduled Tasks Runner for GitHub Actions
Runs background jobs like auto-categorization and sync
"""
import os
import sys
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# Import after logging setup
from lsuite import create_app
from lsuite.extensions import db
from lsuite.models import (
    BankTransaction, TransactionCategory, 
    ERPNextConfig, GoogleCredential
)
from lsuite.bridge.services import CategorizationService, BulkSyncService
from lsuite.gmail.services import GmailService


def run_auto_categorization():
    """Auto-categorize uncategorized transactions"""
    logger.info("=" * 60)
    logger.info("Task: Auto-Categorization")
    logger.info("=" * 60)
    
    try:
        service = CategorizationService()
        categorized, total = service.auto_categorize_all()
        
        logger.info(f"✓ Categorized {categorized} of {total} transactions")
        
        if categorized > 0:
            logger.info(f"Success rate: {(categorized/total)*100:.1f}%")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ Auto-categorization failed: {str(e)}")
        return False


def run_erpnext_sync():
    """Sync categorized transactions to ERPNext"""
    logger.info("=" * 60)
    logger.info("Task: ERPNext Sync")
    logger.info("=" * 60)
    
    try:
        # Get active ERPNext config
        config = ERPNextConfig.query.filter_by(active=True).first()
        
        if not config:
            logger.warning("⚠ No active ERPNext configuration found - skipping sync")
            return False
        
        logger.info(f"Using config: {config.name}")
        
        service = BulkSyncService(config)
        success, failed, total = service.sync_all_ready()
        
        logger.info(f"✓ Synced {success} transactions")
        
        if failed > 0:
            logger.warning(f"⚠ {failed} transactions failed to sync")
        
        if total == 0:
            logger.info("ℹ No transactions ready to sync")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ ERPNext sync failed: {str(e)}")
        return False


def run_gmail_import():
    """Import new statements from Gmail"""
    logger.info("=" * 60)
    logger.info("Task: Gmail Import")
    logger.info("=" * 60)
    
    try:
        # Get authenticated credentials
        credentials = GoogleCredential.query.filter_by(
            is_authenticated=True
        ).all()
        
        if not credentials:
            logger.warning("⚠ No authenticated Google credentials found - skipping import")
            return False
        
        from flask import current_app
        service = GmailService(current_app)
        
        total_imported = 0
        total_skipped = 0
        
        for cred in credentials:
            logger.info(f"Processing credential: {cred.name}")
            
            try:
                imported, skipped = service.fetch_statements(cred)
                total_imported += imported
                total_skipped += skipped
                
                logger.info(f"  Imported: {imported}, Skipped: {skipped}")
                
            except Exception as e:
                logger.error(f"  ✗ Failed: {str(e)}")
                continue
        
        logger.info(f"✓ Total imported: {total_imported}")
        logger.info(f"ℹ Total skipped: {total_skipped}")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ Gmail import failed: {str(e)}")
        return False


def run_statistics():
    """Log current statistics"""
    logger.info("=" * 60)
    logger.info("Statistics")
    logger.info("=" * 60)
    
    try:
        total_trans = BankTransaction.query.count()
        categorized = BankTransaction.query.filter(
            BankTransaction.category_id.isnot(None)
        ).count()
        synced = BankTransaction.query.filter_by(
            erpnext_synced=True
        ).count()
        
        logger.info(f"Total transactions: {total_trans}")
        logger.info(f"Categorized: {categorized} ({(categorized/total_trans)*100:.1f}%)")
        logger.info(f"Synced to ERPNext: {synced} ({(synced/total_trans)*100:.1f}%)")
        
        # Category breakdown
        categories = TransactionCategory.query.all()
        logger.info(f"\nActive categories: {len(categories)}")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ Statistics failed: {str(e)}")
        return False


def main():
    """Main entry point"""
    logger.info("\n" + "=" * 60)
    logger.info("LSuite Scheduled Tasks Runner")
    logger.info(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60 + "\n")
    
    # Create app context
    app = create_app(os.getenv('FLASK_ENV', 'production'))
    
    with app.app_context():
        results = {
            'auto_categorization': False,
            'erpnext_sync': False,
            'gmail_import': False,
            'statistics': False
        }
        
        # Run tasks
        results['statistics'] = run_statistics()
        results['gmail_import'] = run_gmail_import()
        results['auto_categorization'] = run_auto_categorization()
        results['erpnext_sync'] = run_erpnext_sync()
        
        # Final statistics
        run_statistics()
        
        # Summary
        logger.info("\n" + "=" * 60)
        logger.info("Summary")
        logger.info("=" * 60)
        
        for task, success in results.items():
            status = "✓ Success" if success else "✗ Failed"
            logger.info(f"{task.replace('_', ' ').title()}: {status}")
        
        logger.info(f"\nCompleted at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 60 + "\n")
        
        # Exit with error code if any task failed
        if not all(results.values()):
            sys.exit(1)


if __name__ == '__main__':
    main()
