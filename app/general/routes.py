from flask import render_template
from flask_login import login_required, current_user
from app.general import bp


@bp.route('/')
@bp.route('/index')
def index():
    return render_template('index.html', title='Home')
