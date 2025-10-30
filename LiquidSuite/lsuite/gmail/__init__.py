"""
Gmail Blueprint - Handles Gmail integration
"""
from flask import Blueprint

gmail_bp = Blueprint('gmail', __name__, template_folder='templates')

from lsuite.gmail import routes
