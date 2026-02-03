from flask import Blueprint

bp = Blueprint('general', __name__)

from app.general import routes