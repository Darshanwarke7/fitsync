from flask import Flask
from flask_cors import CORS

from config import Config
from utils.db import init_pool, close_conn
from utils.auth_utils import current_user


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    CORS(app)

    init_pool(app)
    app.teardown_appcontext(close_conn)

    from routes.auth import bp as auth_bp
    from routes.admin import bp as admin_bp
    from routes.trainer import bp as trainer_bp
    from routes.member import bp as member_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(trainer_bp)
    app.register_blueprint(member_bp)

    @app.context_processor
    def inject_user():
        return {"current_user": current_user()}

    @app.route("/health")
    def health():
        return {"status": "ok"}, 200

    @app.errorhandler(404)
    def not_found(e):
        return "Page not found - 404", 404

    return app


app = create_app()

if __name__ == "__main__":
    import os
    debug_mode = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=debug_mode, host="0.0.0.0", port=port)
