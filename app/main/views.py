from datetime import datetime
from flask import render_template, session, redirect, url_for, flash, request, current_app
from flask_login import current_user, login_required
from . import main
from .forms import PostForm
from .. import db
from ..models import User, Post, Permission

@main.route('/', methods=['GET', 'POST'])
def index():
    # **********************
    # 这里还需要修改，按照标签相关度进行推荐
    page = request.args.get('page', 1, type=int)
    pagination = Post.query.order_by(Post.timestamp.desc()).paginate(page, per_page=current_app.config['FLASKY_POST_PER_PAGE'], error_out=False)
    recent_posts = pagination.items
    return render_template('index.html', posts=recent_posts, pagination=pagination)

# 博客撰写页面
# 目前只是很简单的版本
@main.route('/write', methods=['GET', 'POST'])
@login_required
def write():
    form = PostForm()
    if form.validate_on_submit():
        if current_user.is_able(Permission.WRITE_ARTICLES):
            post = Post(title=form.title.data, body=form.body.data, author=current_user._get_current_object())
            db.session.add(post)
            return redirect(url_for('main.index'))
        flash('You can not write an article without authority.', 'warning')
    flash('Here')
    return render_template('write.html', form=form)

# 用户资料页面
# 暂未实现
@main.route('/user/<username>')
def user(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        abort(404)
    posts = user.posts.all()
    return render_template('user.html', user=user, posts=posts)

# 某位用户的所有博客概览
# ********************
@main.route('/blog_personal/<username>')
def blog(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        abort(404)
    posts = user.posts.order_by(Post.timestamp.desc()).all()
    return render_template('user_blogs.html', user=user, posts=posts)

# 博客具体浏览页面
@main.route('/blog_content/<username>/<post_id>')
def blog_content(username, post_id):
    user = User.query.filter_by(username=username).first()
    if user is None:
        abort(404)
    post = user.posts.filter_by(id=post_id).first()
    return render_template('blog_content.html', user=user, post=post)
