# LSuite - Ledger Suite

A modern Flask-based financial management system that integrates Gmail bank statements with ERPNext accounting.

## Features

- 🔐 **Google OAuth Integration**: Securely connect to Gmail
- 📧 **Email Statement Import**: Automatically fetch bank statements from Gmail
- 📄 **PDF Parsing**: Extract transactions from bank statement PDFs
- 🏷️ **Auto-Categorization**: Intelligent transaction categorization
- ⬆️ **ERPNext Sync**: Seamlessly sync transactions to ERPNext
- 📊 **Dashboard**: Overview of financial data
- 🔄 **Bulk Operations**: Process multiple transactions at once

## Architecture

LSuite is built using Flask blueprints for modularity:

- **auth**: User authentication and authorization
- **gmail**: Gmail integration and statement import
- **erpnext**: ERPNext API integration
- **bridge**: Transaction categorization and sync logic
- **api**: RESTful API endpoints

## Prerequisites

- Python 3.9+
- PostgreSQL 12+
- Redis (for background tasks)
- Google Cloud Platform account with Gmail API enabled
- ERPNext instance (optional)

## Installation

### 1. Clone the repository

```bash
git clone <repository-url>
cd lsuite
```

### 2. Create virtual environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Set up environment variables

```bash
cp .env.example .env
# Edit .env with your configuration
```

### 5. Initialize database

```bash
flask db init
flask db migrate -m "Initial migration"
flask db upgrade
```

### 6. Seed default data

```bash
flask seed-categories
flask create-admin
```

### 7. Run the application

```bash
# Development
flask run

# Production with Gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

## Google Cloud Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project
3. Enable Gmail API
4. Create OAuth 2.0 credentials
5. Add authorized redirect URI: `http://localhost:5000/gmail/oauth/callback`
6. Copy Client ID and Client Secret to `.env`

## Database Schema

```
users
├── google_credentials (1:N)
│
email_statements
├── bank_transactions (1:N)
    ├── transaction_categories (N:1)
    └── erpnext_sync_logs (1:N)

erpnext_configs
└── erpnext_sync_logs (1:N)
```

## Usage

### 1. Authenticate with Google

1. Navigate to **Gmail > Credentials**
2. Create new credential with your Google OAuth details
3. Click **Authenticate** to authorize Gmail access

### 2. Import Statements

1. Go to **Gmail > Statements**
2. Click **Import from Gmail**
3. Statements will be fetched automatically

### 3. Parse Transactions

1. Open a statement
2. Click **Download & Parse PDF**
3. Enter PDF password if protected
4. Transactions will be extracted

### 4. Categorize & Sync

1. Go to **Transactions**
2. Click **Auto-Categorize All** to categorize transactions
3. Review categories
4. Click **Sync to ERPNext** to push to ERPNext

## API Documentation

### Authentication

All API endpoints require authentication via JWT token.

```bash
POST /api/auth/login
{
  "email": "user@example.com",
  "password": "password"
}
```

### Endpoints

```
GET    /api/statements          # List statements
GET    /api/statements/:id      # Get statement details
POST   /api/statements/import   # Import from Gmail
GET    /api/transactions        # List transactions
POST   /api/transactions/categorize  # Auto-categorize
POST   /api/transactions/sync   # Sync to ERPNext
GET    /api/categories          # List categories
POST   /api/categories          # Create category
```

## Configuration

### Transaction Categories

Categories are used to map transactions to ERPNext accounts. Configure in:

**Bridge > Categories**

Each category has:
- Name
- ERPNext Account
- Transaction Type (expense/income/transfer)
- Auto-match Keywords

### ERPNext Configuration

Configure ERPNext connection in:

**ERPNext > Configuration**

Required fields:
- Base URL
- API Key
- API Secret
- Default Company
- Bank Account

## Development

### Running tests

```bash
pytest
pytest --cov=lsuite tests/
```

### Code formatting

```bash
black lsuite/
flake8 lsuite/
```

### Database migrations

```bash
flask db migrate -m "Description"
flask db upgrade
```

## Background Tasks

LSuite uses Celery for background tasks like periodic statement imports.

Start Celery worker:

```bash
celery -A lsuite.celery worker --loglevel=info
```

Start Celery beat (scheduler):

```bash
celery -A lsuite.celery beat --loglevel=info
```

## Deployment

### Docker

```bash
docker-compose up -d
```

### Manual Deployment

1. Set up PostgreSQL database
2. Set up Redis
3. Configure environment variables
4. Run database migrations
5. Start Gunicorn
6. Start Celery worker
7. Configure Nginx reverse proxy

Example Nginx configuration:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## Troubleshooting

### OAuth redirect mismatch

Ensure the redirect URI in Google Cloud Console exactly matches your configured URI.

### PDF parsing fails

- Check if PDF is password protected
- Try different PDF parsing libraries (PyPDF2 vs pdfplumber)
- Check parsing logs in statement details

### ERPNext sync fails

- Verify ERPNext credentials
- Check ERPNext account names exist
- Review sync logs for detailed errors

## Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## License

MIT License - see LICENSE file

## Support

For issues and questions:
- GitHub Issues: [repository-url]/issues
- Email: support@yourdomain.com

## Roadmap

- [ ] Multi-currency support
- [ ] Bank reconciliation
- [ ] Receipt attachment
- [ ] Mobile app
- [ ] Machine learning categorization
- [ ] Multi-bank support
- [ ] Real-time notifications
- [ ] Advanced reporting
