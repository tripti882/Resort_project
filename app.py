from flask import Flask
from flask_login import LoginManager
from sqlalchemy import inspect, text

from models import db, User


def _migrate_schema():
    """Add new columns on existing SQLite DBs (create_all does not alter tables)."""
    try:
        inspector = inspect(db.engine)
        if "menu_items" not in inspector.get_table_names():
            return
        cols = {c["name"] for c in inspector.get_columns("menu_items")}
        if "image_path" in cols:
            return
        with db.engine.begin() as conn:
            conn.execute(text("ALTER TABLE menu_items ADD COLUMN image_path VARCHAR(255)"))
        with db.engine.begin() as conn:
            conn.execute(
                text(
                    "UPDATE menu_items SET image_path = :p WHERE image_path IS NULL OR TRIM(IFNULL(image_path,'')) = ''"
                ),
                {"p": "images/pizza.jpg"},
            )
    except Exception:
        pass

app = Flask(__name__)
app.config["SECRET_KEY"] = "serenity-secret-2024-xyz"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)
login_manager = LoginManager(app)
login_manager.login_view = "auth.login"
login_manager.login_message = "Please log in."
login_manager.login_message_category = "info"

@login_manager.user_loader
def load_user(user_id):
    if not user_id or not str(user_id).isdigit():
        return None
    return User.query.get(int(user_id))

from routes.auth import auth_bp
from routes.main import main_bp
from routes.staff import staff_bp

app.register_blueprint(auth_bp)
app.register_blueprint(main_bp)
app.register_blueprint(staff_bp, url_prefix="/staff")

with app.app_context():
    db.create_all()
    _migrate_schema()

if __name__ == "__main__":
    app.run(debug=True, port=5000)
