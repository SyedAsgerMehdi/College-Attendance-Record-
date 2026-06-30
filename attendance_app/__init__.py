from flask import Flask

from .extensions import db, login_manager
from .models import User
from .routes import main_bp


def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "change-this-in-production"
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///attendance.db"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)
    login_manager.init_app(app)

    with app.app_context():
        db.create_all()
        if User.query.count() == 0:
            admin = User(username="admin", role="admin")
            admin.set_password("admin123")
            db.session.add(admin)
            db.session.commit()

    app.register_blueprint(main_bp)
    return app
