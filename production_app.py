import os
import logging
import sys

# Production optimized Flask app for Railway deployment
os.environ['PYTHONIOENCODING'] = 'utf-8'

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail
from flask_login import LoginManager
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix

# Production logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)
mail = Mail()
login_manager = LoginManager()

# Create the app
app = Flask(__name__)

# Production configuration
app.secret_key = os.environ.get("SESSION_SECRET") or "fallback-production-key-2024"
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Enhanced PostgreSQL configuration for Railway
database_url = os.environ.get("DATABASE_URL")
if not database_url:
    raise ValueError("DATABASE_URL environment variable is required for production")

# Fix PostgreSQL URL format if needed
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config.update({
    "SQLALCHEMY_DATABASE_URI": database_url,
    "SQLALCHEMY_ENGINE_OPTIONS": {
        "pool_size": 10,
        "pool_recycle": 300,
        "pool_pre_ping": True,
        "max_overflow": 20,
        "pool_timeout": 30,
        "connect_args": {
            "application_name": "senai_evaluation_system",
            "connect_timeout": 10,
        }
    },
    "SQLALCHEMY_TRACK_MODIFICATIONS": False,
    
    # File upload configuration
    "UPLOAD_FOLDER": "/tmp/uploads",
    "MAX_CONTENT_LENGTH": 16 * 1024 * 1024,  # 16MB
    
    # Mail configuration
    "MAIL_SERVER": os.environ.get('MAIL_SERVER', 'localhost'),
    "MAIL_PORT": int(os.environ.get('MAIL_PORT', '587')),
    "MAIL_USE_TLS": os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', 'on', '1'],
    "MAIL_USERNAME": os.environ.get('MAIL_USERNAME', ''),
    "MAIL_PASSWORD": os.environ.get('MAIL_PASSWORD', ''),
    "MAIL_DEFAULT_SENDER": os.environ.get('MAIL_DEFAULT_SENDER', 'noreply@senai.br'),
})

# Initialize extensions
db.init_app(app)
mail.init_app(app)
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Faça login para acessar esta página.'

# Create upload directory
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize database and routes
with app.app_context():
    try:
        # Import models first
        import models
        
        # Test database connection
        connection = db.engine.connect()
        connection.close()
        logging.info("✅ Database connection successful")
        
        # Configure user loader
        @login_manager.user_loader
        def load_user(user_id):
            from models import User
            return User.query.get(int(user_id))
        
        # Create tables if needed
        db.create_all()
        logging.info("✅ Database tables verified")
        
        # Create admin user if it doesn't exist
        from models import User
        admin_user = User.query.filter_by(username='edson.lemes').first()
        if not admin_user:
            admin_user = User()
            admin_user.username = 'edson.lemes'
            admin_user.name = 'Edson Lemes'
            admin_user.role = 'admin'
            admin_user.email = 'edson.lemes@senai.br'
            admin_user.set_password('senai103103')
            db.session.add(admin_user)
            db.session.commit()
            logging.info("✅ Admin user created")
        
        # Import routes after everything is set up
        import routes
        
        logging.info("✅ Application initialized successfully")
        
    except Exception as e:
        logging.error(f"❌ Application initialization error: {e}")
        # Log the full traceback for debugging
        import traceback
        logging.error(traceback.format_exc())
        # Still allow the app to start to see error pages

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug_mode = os.environ.get('FLASK_ENV') == 'development'
    
    logging.info(f"Starting application on port {port}")
    app.run(host='0.0.0.0', port=port, debug=debug_mode)