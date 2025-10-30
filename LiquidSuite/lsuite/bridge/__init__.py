"""
Bridge Blueprint - Transaction Categorization & Sync
"""

# ============================================================================
# lsuite/bridge/__init__.py
# ============================================================================
from flask import Blueprint

bridge_bp = Blueprint('bridge', __name__, template_folder='templates')

from lsuite.bridge import routes