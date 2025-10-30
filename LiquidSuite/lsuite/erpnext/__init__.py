"""
ERPNext Blueprint - Complete Implementation
"""

# ============================================================================
# lsuite/erpnext/__init__.py
# ============================================================================
from flask import Blueprint

erpnext_bp = Blueprint('erpnext', __name__, template_folder='templates')

from lsuite.erpnext import routes
