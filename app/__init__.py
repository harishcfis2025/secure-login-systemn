from flask import Flask

def create_app():
    app = Flask(__name__)
    app.secret_key = "your_super_secret_key_here"  # Must be random & secret
    from .routes import main
    app .register_blueprint(main)

    return app