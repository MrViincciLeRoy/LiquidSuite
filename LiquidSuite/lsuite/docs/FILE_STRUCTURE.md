"""
LSuite Flask Application - Complete Structure
A modern Flask app that reimagines the Odoo addons as a web application

Directory Structure:
==================
lsuite/
├── app.py                          # Main application entry point
├── config.py                       # Configuration management
├── requirements.txt                # Python dependencies
├── .env.example                    # Environment variables template
├── instance/
│   └── config.py                   # Instance-specific config (gitignored)
├── lsuite/
│   ├── __init__.py                 # App factory
│   ├── models.py                   # SQLAlchemy models
│   ├── extensions.py               # Flask extensions
│   ├── auth/
│   │   ├── __init__.py
│   │   ├── routes.py               # Authentication routes
│   │   └── forms.py                # Auth forms
│   ├── gmail/
│   │   ├── __init__.py
│   │   ├── routes.py               # Gmail integration routes
│   │   ├── services.py             # Gmail API services
│   │   ├── parsers.py              # PDF/email parsers
│   │   └── templates/
│   │       ├── credentials.html
│   │       ├── statements.html
│   │       └── transactions.html
│   ├── erpnext/
│   │   ├── __init__.py
│   │   ├── routes.py               # ERPNext integration routes
│   │   ├── services.py             # ERPNext API services
│   │   └── templates/
│   │       ├── config.html
│   │       └── sync_logs.html
│   ├── bridge/
│   │   ├── __init__.py
│   │   ├── routes.py               # Bridge functionality routes
│   │   ├── services.py             # Categorization logic
│   │   └── templates/
│   │       ├── categories.html
│   │       └── bulk_operations.html
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes.py               # REST API endpoints
│   ├── static/
│   │   ├── css/
│   │   │   └── style.css
│   │   └── js/
│   │       └── app.js
│   └── templates/
│       ├── base.html
│       ├── index.html
│       └── components/
│           ├── navbar.html
│           └── flash_messages.html
├── migrations/                      # Alembic migrations
├── tests/
│   ├── __init__.py
│   ├── test_gmail.py
│   ├── test_erpnext.py
│   └── test_bridge.py
└── scripts/
    ├── init_db.py
    └── seed_categories.py
"""

# This is a documentation file showing the complete structure.
# Individual implementation files follow below.
