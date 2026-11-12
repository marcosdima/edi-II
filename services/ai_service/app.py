from ai.routes import ai_bp
from dotenv import find_dotenv, load_dotenv
from flask import Flask

# Load environment variables from .env if present
load_dotenv(find_dotenv(usecwd=True))


def create_app() -> Flask:
    """Application factory for the AI microservice."""
    app = Flask(__name__)
    app.register_blueprint(ai_bp)
    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
