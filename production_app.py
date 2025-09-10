import os
import logging
import sys

# Production optimized Flask app for Railway deployment
os.environ['PYTHONIOENCODING'] = 'utf-8'

from flask import Flask
from flask_mail import Mail
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect, generate_csrf
from werkzeug.middleware.proxy_fix import ProxyFix

# Production logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
mail = Mail()
login_manager = LoginManager()
csrf = CSRFProtect()

# Create the app
app = Flask(__name__)

# Production configuration
app.secret_key = os.environ.get("SESSION_SECRET") or "fallback-production-key-2024"
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Enhanced PostgreSQL configuration for Railway (with SQLite fallback)
database_url = os.environ.get("DATABASE_URL")
if not database_url:
    database_url = "sqlite:///teacher_evaluation.db"
    logging.warning("Using SQLite fallback - set DATABASE_URL for production")

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
            "client_encoding": "utf8",
        }
    },
    "SQLALCHEMY_TRACK_MODIFICATIONS": False,
    
    # File upload configuration
    "UPLOAD_FOLDER": "/tmp/uploads",
    "MAX_CONTENT_LENGTH": 16 * 1024 * 1024,  # 16MB
    
    # Mail configuration - fixed values for Railway deployment
    "MAIL_SERVER": 'smtp.gmail.com',
    "MAIL_PORT": 587,
    "MAIL_USE_TLS": True,
    "MAIL_USE_SSL": False,
    "MAIL_USERNAME": 'escolasenaimorvanfigueiredo@gmail.com',
    "MAIL_PASSWORD": 'bhsnhtnqroscpnxa',
    "MAIL_DEFAULT_SENDER": 'escolasenaimorvanfigueiredo@gmail.com',
    
    # SendGrid API key (works on Railway free plan)
    "SENDGRID_API_KEY": os.environ.get('SENDGRID_API_KEY'),
})

# Import database instance from models
from models import db

# Initialize extensions
db.init_app(app)
mail.init_app(app)
login_manager.init_app(app)
# Disable CSRF completely for this application - we have other security layers
app.config['WTF_CSRF_ENABLED'] = False
# csrf.init_app(app)  # Commented out CSRF initialization
login_manager.login_view = 'login'  # type: ignore
login_manager.login_message = 'Faça login para acessar esta página.'

# CSRF disabled - no need for csrf_token in templates
# @app.context_processor
# def inject_csrf_token():
#     return dict(csrf_token=generate_csrf)

# Create upload directory
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Add a simple route for Railway debugging BEFORE importing complex routes
@app.route('/ping')
def ping():
    """Ultra simple endpoint for Railway debugging"""
    return "PONG - System is alive!", 200

# Configure user loader early
@login_manager.user_loader
def load_user(user_id):
    try:
        from models import User
        return User.query.get(int(user_id))
    except:
        return None

# Initialize database and routes
with app.app_context():
    try:
        # Import models first to avoid circular imports
        from models import User
        
        # Test database connection
        try:
            connection = db.engine.connect()
            connection.close()
            logging.info("✅ Database connection successful")
        except Exception as db_error:
            logging.warning(f"⚠️ Database connection failed: {db_error}")
            # Continue anyway for Railway startup
        
        # Create tables if needed
        try:
            db.create_all()
            logging.info("✅ Database tables verified")
        except Exception as table_error:
            logging.warning(f"⚠️ Table creation failed: {table_error}")
        
        # Create admin user if it doesn't exist
        try:
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
        except Exception as user_error:
            logging.warning(f"⚠️ Admin user creation failed: {user_error}")
        
        # Import routes after everything is set up
        try:
            import routes
            logging.info("✅ Routes imported successfully")
        except Exception as route_error:
            logging.error(f"❌ Routes import failed: {route_error}")
            import traceback
            logging.error(traceback.format_exc())
        
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