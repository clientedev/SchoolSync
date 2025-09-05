#!/usr/bin/env python3
"""
Sistema SENAI - Versão ULTRA SIMPLES para Railway
Carregamento mínimo e rápido, debug completo
"""

import os
import logging
import sys

# Configure logging FIRST
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logging.info("🚀 STARTING RAILWAY APP...")

try:
    from flask import Flask, jsonify
    logging.info("✅ Flask imported")
    
    from werkzeug.middleware.proxy_fix import ProxyFix
    logging.info("✅ ProxyFix imported")
    
    from models import db
    logging.info("✅ Database imported")
    
except Exception as e:
    logging.error(f"❌ Import error: {e}")
    sys.exit(1)

# Create app
app = Flask(__name__)
logging.info("✅ Flask app created")

# Basic config
app.secret_key = os.environ.get("SESSION_SECRET", "railway-key-2024")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)
logging.info("✅ Basic config set")

# Database config
database_url = os.environ.get("DATABASE_URL")
if not database_url:
    database_url = "sqlite:///test.db"
    logging.warning("Using SQLite fallback")

if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
logging.info("✅ Database config set")

# Initialize database
try:
    db.init_app(app)
    logging.info("✅ Database initialized")
except Exception as e:
    logging.error(f"❌ Database init failed: {e}")

# Simple health check
@app.route('/health')
def health():
    """Ultra simple health check"""
    try:
        # Test basic app functionality
        return jsonify({"status": "healthy", "app": "running"}), 200
    except Exception as e:
        return jsonify({"status": "unhealthy", "error": str(e)}), 500

@app.route('/')
def home():
    """Simple home page"""
    return jsonify({"message": "SENAI System - Railway Version", "status": "running"})

# Initialize everything inside app context
with app.app_context():
    try:
        logging.info("🔧 Initializing in app context...")
        
        # Test database connection
        try:
            db.engine.connect()
            logging.info("✅ Database connection OK")
        except Exception as e:
            logging.error(f"❌ Database connection failed: {e}")
        
        # Create tables
        try:
            # Import models to register them
            from models import User, Teacher, Course, Evaluator, Evaluation
            logging.info("✅ Models imported")
            
            db.create_all()
            logging.info("✅ Database tables created")
        except Exception as e:
            logging.error(f"❌ Table creation failed: {e}")
        
        # Create admin user
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
        
        # Load routes LAST
        try:
            from flask_login import LoginManager
            login_manager = LoginManager()
            login_manager.init_app(app)
            login_manager.login_view = 'login'
            
            @login_manager.user_loader
            def load_user(user_id):
                return User.query.get(int(user_id))
            
            logging.info("✅ Login manager configured")
            
            # Import routes
            import routes
            logging.info("✅ Routes imported successfully")
            
        except Exception as e:
            logging.error(f"❌ Routes/Login setup failed: {e}")
            import traceback
            logging.error(traceback.format_exc())
        
        logging.info("🎉 APPLICATION READY!")
        
    except Exception as e:
        logging.error(f"❌ App context initialization failed: {e}")
        import traceback
        logging.error(traceback.format_exc())

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    logging.info(f"🚀 Starting on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)