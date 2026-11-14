import os
from typing import Any

from chat.extensions import db
from chat.routes import chat_bp
from chat.services import ConversationService
from chat.ws import room_broker
from dotenv import find_dotenv, load_dotenv
from flask import Flask
from flask_sock import Sock
from sqlalchemy import event

# Load environment variables from .env if present
load_dotenv(find_dotenv(usecwd=True))


def create_app(database_uri: str | None = None) -> Flask:
    """Application factory for the chat microservice."""
    app = Flask(__name__)

    if database_uri:
        app.config["SQLALCHEMY_DATABASE_URI"] = database_uri
    else:
        default_db = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "chat.db")
        db_path = os.getenv("CHAT_DB_PATH", default_db)
        try:
            os.makedirs(os.path.dirname(db_path), exist_ok=True)
        except (PermissionError, OSError):
            db_path = default_db
            os.makedirs(os.path.dirname(db_path), exist_ok=True)
        app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"

    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)

    with app.app_context():
        if app.config["SQLALCHEMY_DATABASE_URI"].startswith("sqlite:///") and (
            ":memory:" not in app.config["SQLALCHEMY_DATABASE_URI"]
        ):

            @event.listens_for(db.engine, "connect")
            def _set_sqlite_pragma(dbapi_conn: Any, _connection_record: Any) -> None:
                cursor = dbapi_conn.cursor()
                cursor.execute("PRAGMA journal_mode=WAL;")
                cursor.execute("PRAGMA busy_timeout=5000;")
                cursor.close()

        db.create_all()

    app.register_blueprint(chat_bp)

    sock = Sock(app)

    @sock.route("/ws/conversations/<int:conv_id>")
    def conversation_ws(ws: Any, conv_id: int) -> None:
        """WebSocket endpoint streaming real-time messages for a conversation."""
        with app.app_context():
            if not ConversationService.get_by_id(conv_id):
                ws.close()
                return

        room_broker.subscribe(conv_id, ws)
        try:
            while True:
                data = ws.receive()
                if data is None:
                    break
        finally:
            room_broker.unsubscribe(conv_id, ws)

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
