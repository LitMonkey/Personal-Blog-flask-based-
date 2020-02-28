from flask import Flask, render_template
from flask_bootstrap import Bootstrap
from flask_mail import Mail
from flask_moment import Moment
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_pagedown import PageDown
from config import config

login_manager = LoginManager()
login_manager.session_protection = 'strong' # 使用不同安全等级来防止用户会话遭到篡改
login_manager.login_view = 'auth.login' # 设置登陆页面的路由
bootstrap = Bootstrap()
mail = Mail()
moment = Moment()
db = SQLAlchemy()
pagedown = PageDown()

# 通过工厂方法来创建程序实例，这样可以创建多个而且可以使用不同的配置
def create_app(config_name):
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)

    login_manager.init_app(app)
    bootstrap.init_app(app)
    mail.init_app(app)
    moment.init_app(app)
    db.init_app(app)
    pagedown.init_app(app)

    # 注册蓝图
    from .main import main as main_blueprint
    from .auth import auth as auth_blueprint

    app.register_blueprint(main_blueprint)
    app.register_blueprint(auth_blueprint, url_prefix='/auth') # 这里设置了url_prefix，注册后的蓝本中定义的所有路由都会加上指定前缀

    return app