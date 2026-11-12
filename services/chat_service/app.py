import os

from flask import Flask
from src.extensions import db
from src.routes import chat_bp


def create_app(database_uri: str | None = None) -> Flask:
    """Application factory for the chat microservice."""
    app = Flask(__name__)

    if database_uri:
        app.config["SQLALCHEMY_DATABASE_URI"] = database_uri
    else:
        default_db = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "chat.db")
        db_path = os.getenv("CHAT_DB_PATH", default_db)
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"

    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)

    with app.app_context():
        db.create_all()

    app.register_blueprint(chat_bp)
    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
