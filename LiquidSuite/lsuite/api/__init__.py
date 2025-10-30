"""
API and Main Blueprints
"""

# ============================================================================
# lsuite/api/__init__.py
# ============================================================================
from flask import Blueprint

api_bp = Blueprint('api', __name__)

from lsuite.api import routes