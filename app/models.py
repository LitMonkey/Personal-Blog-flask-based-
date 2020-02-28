from flask import current_app
from datetime import datetime
from flask_login import UserMixin, login_required, AnonymousUserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from markdown import markdown
import bleach
from . import db
from . import login_manager

class Permission:
    FOLLOW = 0x01
    COMMENT = 0x02
    WRITE_ARTICLES = 0x04
    MODERATE_COMMENTS = 0x08
    ADMINISTER = 0x80

# 关联表
class Follow(db.Model):
    __tablename__ = 'follows'
    follower_id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)
    followed_id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class Role(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True)
    default = db.Column(db.Boolean, default=False, index=True)
    # 表示操作权限等级，通过位标志来确定
    permissions = db.Column(db.Integer)

    # 定义反向关系，在User中添加一个role属性，获取到的是role对象
    users = db.relationship('User', backref='role', lazy='dynamic')

    @staticmethod
    def insert_roles():
        roles = {
            'User': (Permission.FOLLOW | Permission.COMMENT | Permission.WRITE_ARTICLES, True),
            'Moderator': (Permission.FOLLOW | Permission.COMMENT | Permission.WRITE_ARTICLES | Permission.MODERATE_COMMENTS, False),
            'Administrator': (0xff, False)
        }
        for r in roles:
            role = Role.query.filter_by(name=r).first()
            # 如果数据库中没有此角色，则添加到数据库
            if role is None:
                role = Role(name=r)
            role.permissions = roles[r][0]
            role.default = roles[r][1]
            db.session.add(role)
        db.session.commit()

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(64), index=True, unique=True)
    username = db.Column(db.String(64), index=True, unique=True)
    password_hash = db.Column(db.String(128))
    confirmed = db.Column(db.Boolean, default=False)

    rold_id = db.Column(db.Integer, db.ForeignKey('roles.id'))
    posts = db.relationship('Post', backref='author', lazy='dynamic')
    followed = db.relationship('Follow', foreign_keys=[Follow.follower_id], backref=db.backref('follower', lazy='joined'), lazy='dynamic', cascade='all, delete-orphan')
    followers = db.relationship('Follow', foreign_keys=[Follow.followed_id], backref=db.backref('followed', lazy='joined'), lazy='dynamic', cascade='all, delete-orphan')

    name = db.Column(db.String(64))
    profile_photo_url = db.Column(db.String(64))
    location = db.Column(db.String(64))
    about_me = db.Column(db.Text())
    member_since = db.Column(db.DateTime(), default=datetime.utcnow)
    last_seen = db.Column(db.DateTime(), default=datetime.utcnow)

    # 通过构造函数赋予角色
    def __init__(self, **kwargs):
        super(User, self).__init__(**kwargs)
        if self.role is None:
            if self.email == current_app.config['FLASKY_ADMIN']:
                self.role = Role.query.filter_by(permissions=0xff).first()
            else:
                self.role = Role.query.filter_by(default=True).first()

    # 获取密码
    # 原密码不可见，因为已经转码
    @property
    def password(self):
        raise AttributeError('Password is not a readable attrbute')

    # 设置密码
    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)
    
    # 验证密码
    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

    # 生成验证令牌
    # 设置过期时间为一小时
    def generate_confirmation_token(self, expiration=3600):
        s = Serializer(current_app.config['SECRET_KEY'])
        return s.dumps({'confirm':self.id}) # 传入用户id来生成令牌

    def confirm(self, token):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token) # 解码令牌
        except:
            return False
        if data.get('confirm') != self.id:
            return False
        self.confirmed = True
        db.session.add(self)
        return True

    # 查询用户是否有特定权限
    def is_able(self, permission):
        print(self.role)
        return self.role is not None and (self.role.permissions & permission) == permission

    # 判断用户是否是超级管理员
    def is_administrator(self):
        return self.is_able(Permission.ADMINISTER)

    def ping(self):
        self.last_seen = datetime.utcnow()
        db.session.add(self)
    
    def follow(self, user):
        if not self.is_following(user):
            f = Follow(follower=self, folllowed=user)
            db.session.add(f)
    
    def unfollow(self, user):
        f = self.followed.filter_by(followed_id=user.id).first()
        if f:
            db.session.delete(f)
    
    def is_following(self, user):
        return self.followed.filter_by(followed_id=user.id).first() is not None
    
    def is_followed_by(self, user):
        return self.followers.filter_by(follower_id=uer.id).first() is not None

    # 自动化方法生成虚拟用户
    @staticmethod
    def generate_fake(count=100):
        from sqlalchemy.exc import IntegrityError
        from random import seed
        import forgery_py

        seed()
        for i in range(count):
            u = User(email=forgery_py.internet.email_address(), username=forgery_py.internet.user_name(True), password=forgery_py.lorem_ipsum.word(), confirmed=True, name=forgery_py.name.full_name(), location=forgery_py.lorem_ipsum.sentence(), member_since=forgery_py.date.date(True))
            db.session.add(u)
            try:
                db.session.commit()
            except IntegrityError:
                db.session.rollback()

# 匿名用户
class AnonymousUser(AnonymousUserMixin):
    def is_able(self, permission):
        return False

    def is_administrator(self):
        return False

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))   # 通过id来获取数据库中用户数据

# 构建login_manager
login_manager.anonymous_user = AnonymousUser

# 博客类
class Post(db.Model):
    __tablename__ = 'posts'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(128))
    body = db.Column(db.Text)
    body_html = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    # *************************
    # tag
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))

    @staticmethod
    def generate_fake(count=100):
        from random import seed, randint
        import forgery_py
        
        seed()
        user_count = User.query.count()
        for i in range(count):
            # 随机选择一个虚拟用户
            u = User.query.offset(randint(0, user_count-1)).first()
            p = Post(title=forgery_py.lorem_ipsum.sentences(randint(1, 3)), body=forgery_py.lorem_ipsum.sentences(randint(1, 50)), timestamp=forgery_py.date.date(True), author=u)

            db.session.add(p)
            db.session.commit()
    
    @staticmethod
    def on_changed_body(target, value, oldvalue, initiator):
        allowed_tags = ['a', 'abbr', 'acronym', 'b', 'blockquote', 'code', 'em', 'i', 'li', 'ol', 'pre', 'strong', 'ul', 'h1', 'h2', 'h3', 'p']

        target.body_html = bleach.linkify(bleach.clean(markdown(value, output_format="html"), tags=allowed_tags, strip=True))
        
db.event.listen(Post.body, 'set', Post.on_changed_body)
