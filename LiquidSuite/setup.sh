#!/bin/bash
# ============================================================================
# LSuite Setup Script
# Complete automated setup for LSuite Flask application
# ============================================================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Banner
echo "=============================================="
echo "  LSuite - Ledger Suite Setup"
echo "  Complete Flask Application Installation"
echo "=============================================="
echo ""

# Check if running as root for system setup
if [[ $EUID -eq 0 ]] && [[ "$1" != "--system" ]]; then
   log_error "Don't run this script as root unless using --system flag"
   exit 1
fi

# Setup mode
SETUP_MODE=${1:-"dev"}

case $SETUP_MODE in
    "dev")
        log_info "Setting up DEVELOPMENT environment"
        ;;
    "prod")
        log_info "Setting up PRODUCTION environment"
        ;;
    "--system")
        log_info "Setting up SYSTEM-WIDE installation (requires root)"
        ;;
    *)
        log_error "Unknown setup mode: $SETUP_MODE"
        log_info "Usage: ./setup.sh [dev|prod|--system]"
        exit 1
        ;;
esac

# ============================================================================
# 1. Check System Requirements
# ============================================================================
log_info "Checking system requirements..."

# Check Python version
if ! command -v python3 &> /dev/null; then
    log_error "Python 3 is not installed"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
REQUIRED_VERSION="3.9"

if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then 
    log_error "Python 3.9+ required, found $PYTHON_VERSION"
    exit 1
fi

log_success "Python $PYTHON_VERSION found"

# Check PostgreSQL
if ! command -v psql &> /dev/null; then
    log_warning "PostgreSQL client not found. Install with:"
    log_info "  Ubuntu/Debian: sudo apt install postgresql-client"
    log_info "  macOS: brew install postgresql"
fi

# Check Redis
if ! command -v redis-cli &> /dev/null; then
    log_warning "Redis not found. Install with:"
    log_info "  Ubuntu/Debian: sudo apt install redis-server"
    log_info "  macOS: brew install redis"
fi

# ============================================================================
# 2. Create Virtual Environment
# ============================================================================
log_info "Creating virtual environment..."

if [ -d "venv" ]; then
    log_warning "Virtual environment already exists. Skipping..."
else
    python3 -m venv venv
    log_success "Virtual environment created"
fi

# Activate virtual environment
source venv/bin/activate
log_success "Virtual environment activated"

# ============================================================================
# 3. Install Python Dependencies
# ============================================================================
log_info "Installing Python dependencies..."

pip install --upgrade pip
pip install -r requirements.txt

log_success "Dependencies installed"

# ============================================================================
# 4. Environment Configuration
# ============================================================================
log_info "Setting up environment configuration..."

if [ ! -f ".env" ]; then
    cp .env.example .env
    
    # Generate secret key
    SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
    
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        sed -i '' "s/your-secret-key-here-change-in-production/$SECRET_KEY/" .env
    else
        # Linux
        sed -i "s/your-secret-key-here-change-in-production/$SECRET_KEY/" .env
    fi
    
    log_success ".env file created with generated SECRET_KEY"
    log_warning "Please edit .env and add your:"
    log_info "  - Database credentials"
    log_info "  - Google OAuth credentials"
    log_info "  - ERPNext configuration (optional)"
    
    read -p "Press Enter to continue after editing .env..."
else
    log_warning ".env file already exists. Skipping..."
fi

# ============================================================================
# 5. Database Setup
# ============================================================================
log_info "Setting up database..."

# Load environment variables
export $(cat .env | grep -v '^#' | xargs)

# Check if database exists
if psql "$DATABASE_URL" -c '\q' 2>/dev/null; then
    log_success "Database connection successful"
else
    log_error "Cannot connect to database. Please check DATABASE_URL in .env"
    log_info "Example: postgresql://username:password@localhost:5432/lsuite"
    exit 1
fi

# Initialize database
log_info "Initializing database schema..."

if [ ! -d "migrations" ]; then
    flask db init
    log_success "Migrations initialized"
fi

flask db migrate -m "Initial schema"
flask db upgrade

log_success "Database schema created"

# ============================================================================
# 6. Seed Default Data
# ============================================================================
log_info "Seeding default data..."

flask seed-categories

log_success "Default categories seeded"

# ============================================================================
# 7. Create Admin User
# ============================================================================
log_info "Creating admin user..."

read -p "Create admin user now? (y/n): " CREATE_ADMIN

if [ "$CREATE_ADMIN" = "y" ] || [ "$CREATE_ADMIN" = "Y" ]; then
    flask create-admin
    log_success "Admin user created"
else
    log_warning "Admin user creation skipped. Run 'flask create-admin' later."
fi

# ============================================================================
# 8. Production Setup
# ============================================================================
if [ "$SETUP_MODE" = "prod" ]; then
    log_info "Setting up production environment..."
    
    # Create log directory
    mkdir -p logs
    
    # Set permissions
    chmod 755 logs
    
    # Install production server
    pip install gunicorn
    
    log_info "Production setup complete. To run:"
    log_info "  gunicorn -w 4 -b 0.0.0.0:5000 app:app"
    
    # Systemd setup
    read -p "Setup systemd services? (requires sudo) (y/n): " SETUP_SYSTEMD
    
    if [ "$SETUP_SYSTEMD" = "y" ] || [ "$SETUP_SYSTEMD" = "Y" ]; then
        log_info "Creating systemd service files..."
        
        sudo cp systemd/lsuite.service /etc/systemd/system/
        sudo cp systemd/lsuite-celery-worker.service /etc/systemd/system/
        sudo cp systemd/lsuite-celery-beat.service /etc/systemd/system/
        
        sudo systemctl daemon-reload
        sudo systemctl enable lsuite
        sudo systemctl enable lsuite-celery-worker
        sudo systemctl enable lsuite-celery-beat
        
        log_success "Systemd services configured"
        log_info "Start services with:"
        log_info "  sudo systemctl start lsuite"
        log_info "  sudo systemctl start lsuite-celery-worker"
        log_info "  sudo systemctl start lsuite-celery-beat"
    fi
fi

# ============================================================================
# 9. Docker Setup
# ============================================================================
if command -v docker &> /dev/null && command -v docker-compose &> /dev/null; then
    read -p "Setup Docker environment? (y/n): " SETUP_DOCKER
    
    if [ "$SETUP_DOCKER" = "y" ] || [ "$SETUP_DOCKER" = "Y" ]; then
        log_info "Building Docker containers..."
        docker-compose build
        log_success "Docker containers built"
        
        log_info "To start with Docker:"
        log_info "  docker-compose up -d"
    fi
fi

# ============================================================================
# 10. Final Steps
# ============================================================================
log_info "Running final checks..."

# Test imports
python3 -c "from lsuite import create_app; app = create_app('development'); print('✓ Application imports successful')"

log_success "Setup complete!"
echo ""
echo "=============================================="
echo "  Next Steps:"
echo "=============================================="
echo ""
echo "1. Configure Google OAuth:"
echo "   - Go to https://console.cloud.google.com"
echo "   - Enable Gmail API"
echo "   - Create OAuth credentials"
echo "   - Add credentials to .env"
echo ""
echo "2. Start the application:"
if [ "$SETUP_MODE" = "dev" ]; then
    echo "   source venv/bin/activate"
    echo "   flask run"
else
    echo "   gunicorn -w 4 -b 0.0.0.0:5000 app:app"
fi
echo ""
echo "3. (Optional) Start Celery workers:"
echo "   celery -A lsuite.celery worker --loglevel=info"
echo "   celery -A lsuite.celery beat --loglevel=info"
echo ""
echo "4. Access the application:"
echo "   http://localhost:5000"
echo ""
echo "5. Login with your admin credentials"
echo ""
echo "=============================================="
echo "  Documentation"
echo "=============================================="
echo ""
echo "  README.md       - General documentation"
echo "  QUICKSTART.md   - Quick setup guide"
echo "  docs/           - Detailed documentation"
echo ""
echo "For support: https://github.com/yourusername/lsuite"
echo ""


# ============================================================================
# Create Helper Scripts
# ============================================================================
log_info "Creating helper scripts..."

# Start script
cat > start.sh << 'EOF'
#!/bin/bash
source venv/bin/activate
export FLASK_ENV=development
flask run --debug
EOF
chmod +x start.sh

# Stop script
cat > stop.sh << 'EOF'
#!/bin/bash
pkill -f "flask run"
pkill -f "celery"
EOF
chmod +x stop.sh

# Backup script
cat > backup.sh << 'EOF'
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="backups/$DATE"
mkdir -p "$BACKUP_DIR"

# Backup database
pg_dump "$DATABASE_URL" > "$BACKUP_DIR/database.sql"

# Backup .env
cp .env "$BACKUP_DIR/.env"

echo "Backup created: $BACKUP_DIR"
EOF
chmod +x backup.sh

log_success "Helper scripts created: start.sh, stop.sh, backup.sh"

echo ""
log_success "🎉 LSuite setup completed successfully!"
