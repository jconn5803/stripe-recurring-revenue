import sqlalchemy as sa
import sqlalchemy.orm as so
from datetime import datetime, date
from flask import render_template, redirect, url_for, flash, request, session, current_app
from flask_login import current_user, login_user, logout_user, login_required
from app.auth import bp
from app.auth.forms import LoginForm, RegistrationForm
from app import db
from app.models import User

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('general.index'))

    form = LoginForm()
    if form.validate_on_submit():
        user = db.session.scalar(
            sa.select(User).where(User.email == form.email.data.lower())
        )
        if user is None or not user.check_password(form.password.data):
            flash('Invalid email or password.')
            return redirect(url_for('auth.login'))

        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get('next')
        if not next_page or not next_page.startswith('/'):
            next_page = url_for('general.index')
        return redirect(next_page)

    return render_template('login.html', title='Sign in', form=form)


@bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('general.index'))

    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(
            email=form.email.data.lower(),
            name=form.name.data
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Registration successful. You can now log in.')
        return redirect(url_for('auth.login'))

    return render_template('register.html', title='Register', form=form)

@bp.route('/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    flash('You have been signed out.')
    return redirect(url_for('general.index'))
