from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from models import db, Post, Comment
from crawler import fetch_link_info

posts_bp = Blueprint('posts', __name__)

CATEGORIES = ['文章', '视频', '图片']


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
            db.or_(Post.link.contains(search), Post.recommendation.contains(search),
                   Post.summary.contains(search), Post.title.contains(search))
        )
    query = query.order_by(Post.created_at.desc())

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    posts = pagination.items

    return render_template('index.html', posts=posts, pagination=pagination,
                           categories=CATEGORIES, current_category=category,
                           search=search)


@posts_bp.route('/post/<int:post_id>')
def detail(post_id):
    post = db.session.get(Post, post_id)
    if not post:
        flash('帖子不存在', 'error')
        return redirect(url_for('posts.index'))
    comments = post.comments.order_by(Comment.created_at.desc()).all()
    return render_template('post_detail.html', post=post, comments=comments,
                           categories=CATEGORIES)


@posts_bp.route('/post/new', methods=['GET', 'POST'])
@login_required
def new_post():
    if request.method == 'POST':
        link = request.form.get('link', '').strip()
        category = request.form.get('category', '文章')
        recommendation = request.form.get('recommendation', '').strip()

        if not link:
            flash('链接不能为空', 'error')
        elif not link.startswith(('http://', 'https://')):
            flash('请输入有效的链接（以 http:// 或 https:// 开头）', 'error')
        elif category not in CATEGORIES:
            flash('无效的分类', 'error')
        else:
            # 爬取链接内容
            title, summary = fetch_link_info(link, category)

            post = Post(link=link, category=category,
                        recommendation=recommendation, summary=summary,
                        title=title, user_id=current_user.id)
            db.session.add(post)
            db.session.commit()
            flash('发布成功！', 'success')
            return redirect(url_for('posts.detail', post_id=post.id))

    return render_template('new_post.html', categories=CATEGORIES)


@posts_bp.route('/post/<int:post_id>/comment', methods=['POST'])
@login_required
def add_comment(post_id):
    post = db.session.get(Post, post_id)
    if not post:
        flash('帖子不存在', 'error')
        return redirect(url_for('posts.index'))
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
