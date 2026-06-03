from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from models import db, Post, Comment

posts_bp = Blueprint('posts', __name__)

CATEGORIES = ['综合', '技术', '生活', '问答', '分享']


@posts_bp.route('/')
def index():
    page = request.args.get('page', 1, type=int)
    per_page = 10
    category = request.args.get('category')
    search = request.args.get('search', '').strip()

    query = Post.query
    if category and category in CATEGORIES:
        query = query.filter_by(category=category)
    if search:
        query = query.filter(
            db.or_(Post.title.contains(search), Post.content.contains(search))
        )
    query = query.order_by(Post.created_at.desc())

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    posts = pagination.items

    return render_template('index.html', posts=posts, pagination=pagination,
                           categories=CATEGORIES, current_category=category,
                           search=search)


@posts_bp.route('/post/<int:post_id>')
def detail(post_id):
    post = Post.query.get_or_404(post_id)
    comments = post.comments.order_by(Comment.created_at.desc()).all()
    return render_template('post_detail.html', post=post, comments=comments,
                           categories=CATEGORIES)


@posts_bp.route('/post/new', methods=['GET', 'POST'])
@login_required
def new_post():
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        content = request.form.get('content', '').strip()
        category = request.form.get('category', '综合')

        if not title or not content:
            flash('标题和内容不能为空', 'error')
        elif len(title) > 200:
            flash('标题不能超过200个字符', 'error')
        elif category not in CATEGORIES:
            flash('无效的分类', 'error')
        else:
            post = Post(title=title, content=content, category=category,
                        user_id=current_user.id)
            db.session.add(post)
            db.session.commit()
            flash('发帖成功！', 'success')
            return redirect(url_for('posts.detail', post_id=post.id))

    return render_template('new_post.html', categories=CATEGORIES)


@posts_bp.route('/post/<int:post_id>/comment', methods=['POST'])
@login_required
def add_comment(post_id):
    post = Post.query.get_or_404(post_id)
    content = request.form.get('content', '').strip()

    if not content:
        flash('评论内容不能为空', 'error')
    else:
        comment = Comment(content=content, post_id=post.id,
                          user_id=current_user.id)
        db.session.add(comment)
        db.session.commit()
        flash('评论成功！', 'success')

    return redirect(url_for('posts.detail', post_id=post.id))
