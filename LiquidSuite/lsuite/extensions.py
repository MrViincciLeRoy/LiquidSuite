"""
Flask Extensions
Initialize extensions here to avoid circular imports
"""
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_cors import CORS

# Initialize extensions
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
cors = CORS()

# Configure login manager
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'


@login_manager.user_loader
def load_user(user_id):
    """Load user by ID"""
    from lsuite.models import User
    return User.query.get(int(user_id))
