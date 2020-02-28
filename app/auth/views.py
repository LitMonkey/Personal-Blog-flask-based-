from flask import render_template, redirect, request, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from ..email import send_email
from . import auth
from .. import db
from ..models import User
from .forms import LoginForm, RegistrationForm

@auth.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user is not None and user.verify_password(form.password.data):
            login_user(user, form.remember_me.data)
            return redirect(url_for('main.index'))
        flash('Invalid username or password.', 'warning')
    return render_template('auth/login.html', form=form)

@auth.route('/logout', methods=['GET', 'POST'])
def logout():
    logout_user()
    flash('You have been loged out.', 'success')
    return redirect(url_for('main.index'))

@auth.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        if form.validate_email(form.email):
            if form.validate_username(form.username):
                # 新建表项
                user = User(email=form.email.data, username=form.username.data, password=form.password.data)
                db.session.add(user)
                db.session.commit()
                # 发送确认邮件
                token = user.generate_confirmation_token()
                send_email(user.email, 'Confirm Your Account', 'auth/email/confirm', user=user, token=token)
                flash('A confirmation email has been sent to you by email.', 'success')
                flash('You can now log in!', 'success')
                login_user(user)
                return redirect(url_for('main.index'))
    return render_template('auth/register.html', form=form)

@auth.route('/confirm/<token>')
@login_required
def confirm(token):
    if current_user.confirmed:
        return redirect(url_for('main.index'))
    if current_user.confirm(token):
        flash('You have confirmed your account. Thanks!', 'success')
    else:
        flash('The confirmation link is invalid or has expired.', 'err')
    return redirect(url_for('main.index'))

# 重新发送确认邮件
@auth.route('/resend')
def resend_confirmation():
    token = current_user.generate_confirmation_token()
    send_email(current_user.email, 'Confirm Your Account', 'auth/email/confirm', user=current_user, token=token)
    flash('A new confirmation email has been sent to you by email.', 'success')
    return redirect(url_for('auth.login'))

@auth.before_app_request
def before_request():
    if current_user.is_authenticated:
        current_user.ping()
        if not current_user.confirmed and request.endpoint[:5] != 'auth.' and request.endpoint != 'static':
            return redirect(url_for('auth.unconfirmed'))
    
@auth.route('/unconfirmed')
def unconfirmed():
    if current_user.is_anonymous or current_user.confirmed:
        return redirect(url_for('main.index'))
    return render_template('auth/unconfirmed.html', username=current_user.username)