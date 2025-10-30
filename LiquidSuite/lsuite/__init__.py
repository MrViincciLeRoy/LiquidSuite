"""
LSuite Application Factory
"""
import logging
from flask import Flask, render_template
from config import config
from lsuite.extensions import db, migrate, login_manager, cors


def create_app(config_name='default'):
    """Application factory pattern"""
    
    app = Flask(__name__)
    
    # Load configuration
    app.config.from_object(config[config_name])
    
    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    cors.init_app(app)
    
    # Configure logging
    configure_logging(app)
    
    # Register blueprints
    register_blueprints(app)
    
    # Register error handlers
    register_error_handlers(app)
    
    # Shell context for flask shell
    @app.shell_context_processor
    def make_shell_context():
        from lsuite import models
        return {
            'db': db,
            'User': models.User,
            'GoogleCredential': models.GoogleCredential,
            'EmailStatement': models.EmailStatement,
            'BankTransaction': models.BankTransaction,
            'TransactionCategory': models.TransactionCategory,
            'ERPNextConfig': models.ERPNextConfig,
            'ERPNextSyncLog': models.ERPNextSyncLog,
        }
    
    return app


def register_blueprints(app):
    """Register Flask blueprints"""
    from lsuite.auth import auth_bp
    from lsuite.gmail import gmail_bp
    from lsuite.erpnext import erpnext_bp
    from lsuite.bridge import bridge_bp
    from lsuite.api import api_bp
    from lsuite.main import main_bp
    
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(gmail_bp, url_prefix='/gmail')
    app.register_blueprint(erpnext_bp, url_prefix='/erpnext')
    app.register_blueprint(bridge_bp, url_prefix='/bridge')
    app.register_blueprint(api_bp, url_prefix='/api')


def register_error_handlers(app):
    """Register error handlers"""
    
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('errors/404.html'), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return render_template('errors/500.html'), 500
    
    @app.errorhandler(403)
    def forbidden_error(error):
        return render_template('errors/403.html'), 403


def configure_logging(app):
    """Configure application logging"""
    
    if not app.debug and not app.testing:
        # Production logging
        file_handler = logging.FileHandler(app.config['LOG_FILE'])
        file_handler.setLevel(getattr(logging, app.config['LOG_LEVEL']))
        
        formatter = logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        )
        file_handler.setFormatter(formatter)
        
        app.logger.addHandler(file_handler)
        app.logger.setLevel(getattr(logging, app.config['LOG_LEVEL']))
        app.logger.info('LSuite startup')
