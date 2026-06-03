from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('posts.index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            next_page = request.args.get('next')
            flash('登录成功！', 'success')
            return redirect(next_page or url_for('posts.index'))
        else:
            flash('用户名或密码错误', 'error')

    return render_template('login.html')


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('posts.index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        if not username or not password:
            flash('用户名和密码不能为空', 'error')
        elif len(username) < 2 or len(username) > 20:
            flash('用户名长度需在2-20个字符之间', 'error')
        elif len(password) < 6:
            flash('密码长度不能少于6个字符', 'error')
        elif password != confirm_password:
            flash('两次输入的密码不一致', 'error')
        elif User.query.filter_by(username=username).first():
            flash('该用户名已被注册', 'error')
        else:
            user = User(
                username=username,
                password_hash=generate_password_hash(password)
            )
            db.session.add(user)
            db.session.commit()
            flash('注册成功，请登录', 'success')
            return redirect(url_for('auth.login'))

    return render_template('register.html')


@auth_bp.route('/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    flash('已退出登录', 'success')
    return redirect(url_for('posts.index'))
