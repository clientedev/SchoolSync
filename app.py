import os
import logging
import sys

# Set UTF-8 encoding for the application
os.environ['PYTHONIOENCODING'] = 'utf-8'

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail
from flask_login import LoginManager
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix

# Configure logging
logging.basicConfig(level=logging.DEBUG)

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)
mail = Mail()
login_manager = LoginManager()

# create the app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key-change-in-production")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# configure the database
database_url = os.environ.get("DATABASE_URL")
if database_url and database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)
app.config["SQLALCHEMY_DATABASE_URI"] = database_url or "sqlite:///teacher_evaluation.db"
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
    "pool_size": 5,
    "max_overflow": 10
}

# configure file uploads
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# configure mail
app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'localhost')
app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', '587'))
app.config['MAIL_USE_TLS'] = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', 'on', '1']
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME', '')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD', '')
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER', 'noreply@school.edu')

# initialize extensions
db.init_app(app)
mail.init_app(app)
login_manager.init_app(app)
login_manager.login_view = 'login'  # type: ignore
login_manager.login_message = 'Faça login para acessar esta página.'

# create upload directory
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

with app.app_context():
    # Import models and routes
    import models
    import routes
    
    # Configure user loader
    @login_manager.user_loader
    def load_user(user_id):
        from models import User
        return User.query.get(int(user_id))
    
    try:
        # Test database connection first
        db.engine.connect()
        print("✅ Database connection successful")
        
        db.create_all()
        print("✅ Database tables created/verified")
        
        # Create admin user if it doesn't exist
        from models import User
        admin_user = User.query.filter_by(username='edson.lemes').first()
        if not admin_user:
            admin_user = User()  # type: ignore
            admin_user.username = 'edson.lemes'
            admin_user.name = 'Edson Lemes'
            admin_user.role = 'admin'
            admin_user.email = 'edson.lemes@senai.br'
            admin_user.set_password('senai103103')
            db.session.add(admin_user)
            db.session.commit()
            print("✅ Admin user created successfully")
    except Exception as e:
        print(f"❌ Database initialization error: {e}")
        print(f"Database URL: {app.config['SQLALCHEMY_DATABASE_URI'][:50]}...")
        # Don't fail completely, let the app start and show the error

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
