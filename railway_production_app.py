#!/usr/bin/env python3
"""
Sistema SENAI - Versão otimizada para Railway
Sem importações circulares, com tudo integrado
"""

import os
import logging
import sys
from datetime import datetime

# Configure logging first
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

# Production optimized Flask app for Railway deployment
os.environ['PYTHONIOENCODING'] = 'utf-8'

from flask import Flask
from flask_mail import Mail
from flask_login import LoginManager
from werkzeug.middleware.proxy_fix import ProxyFix

# Import database from models
from models import db

# Create the app
app = Flask(__name__)

# Production configuration
app.secret_key = os.environ.get("SESSION_SECRET") or "railway-production-key-2024"
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Enhanced PostgreSQL configuration for Railway
database_url = os.environ.get("DATABASE_URL")
if not database_url:
    # Fallback for development
    database_url = "sqlite:///senai.db"
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
mail = Mail()
login_manager = LoginManager()

db.init_app(app)
mail.init_app(app)
login_manager.init_app(app)
login_manager.login_view = 'login'  # type: ignore
login_manager.login_message = 'Faça login para acessar esta página.'

# Create upload directory
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize database and routes
with app.app_context():
    try:
        # Import models to register them with SQLAlchemy
        from models import User, Teacher, Course, Evaluator, Evaluation, EvaluationAttachment
        from models import Semester, CurricularUnit, ScheduledEvaluation, DigitalSignature
        
        # Test database connection
        try:
            connection = db.engine.connect()
            connection.close()
            logging.info("✅ Database connection successful")
        except Exception as e:
            logging.error(f"❌ Database connection failed: {e}")
            # Continue anyway for Railway health checks
        
        # Configure user loader for Flask-Login
        @login_manager.user_loader
        def load_user(user_id):
            try:
                return User.query.get(int(user_id))
            except:
                return None
        
        # Create tables if needed
        try:
            db.create_all()
            logging.info("✅ Database tables verified")
        except Exception as e:
            logging.error(f"❌ Database tables creation failed: {e}")
        
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
        except Exception as e:
            logging.error(f"❌ Admin user creation failed: {e}")
        
        # Import routes after everything is set up
        try:
            import routes
            logging.info("✅ Routes loaded successfully")
        except Exception as e:
            logging.error(f"❌ Routes loading failed: {e}")
            import traceback
            logging.error(traceback.format_exc())
        
        logging.info("✅ Application initialized successfully")
        
    except Exception as e:
        logging.error(f"❌ Application initialization error: {e}")
        import traceback
        logging.error(traceback.format_exc())
        # Allow app to start for debugging

# Health check endpoint will be loaded from routes.py

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug_mode = os.environ.get('FLASK_ENV') == 'development'
    
    logging.info(f"Starting application on port {port}")
    app.run(host='0.0.0.0', port=port, debug=debug_mode)