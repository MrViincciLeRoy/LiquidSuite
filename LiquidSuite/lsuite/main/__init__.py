# ============================================================================
# lsuite/main/__init__.py
# ============================================================================
from flask import Blueprint

main_bp = Blueprint('main', __name__)

from lsuite.main import routes
