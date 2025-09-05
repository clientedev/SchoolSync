#!/usr/bin/env python3
"""
App Railway - Versão DEFINITIVA para Railway
Tudo em um arquivo, sem importações complexas, funcionamento garantido
"""

import os
import logging
import sys
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

# Basic Flask imports
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.middleware.proxy_fix import ProxyFix

# Create Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "railway-ultimate-key-2024")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Database configuration
database_url = os.environ.get("DATABASE_URL")
if not database_url:
    database_url = "sqlite:///railway_app.db"
    logging.warning("Using SQLite fallback - set DATABASE_URL for production")

if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config.update({
    "SQLALCHEMY_DATABASE_URI": database_url,
    "SQLALCHEMY_TRACK_MODIFICATIONS": False,
    "SQLALCHEMY_ENGINE_OPTIONS": {
        "pool_size": 10,
        "pool_recycle": 300,
        "pool_pre_ping": True,
        "max_overflow": 20,
        "pool_timeout": 30,
    },
})

# Initialize extensions
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Faça login para acessar esta página.'

# Simple User model
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    role = db.Column(db.String(20), default='admin')
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def is_teacher(self):
        return self.role == 'teacher'

# Simple Login Form
class LoginForm(FlaskForm):
    username = StringField('Usuário', validators=[DataRequired()])
    password = PasswordField('Senha', validators=[DataRequired()])
    submit = SubmitField('Entrar')

# User loader
@login_manager.user_loader
def load_user(user_id):
    try:
        return User.query.get(int(user_id))
    except:
        return None

# Routes
@app.route('/health')
def health():
    """Health check for Railway"""
    try:
        # Test database connection
        db.engine.connect()
        return jsonify({"status": "healthy", "database": "connected", "app": "railway_app"}), 200
    except Exception as e:
        return jsonify({"status": "unhealthy", "error": str(e)}), 500

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    form = LoginForm()
    error_message = ""
    
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data) and user.is_active:
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('dashboard'))
        else:
            error_message = "Usuário ou senha inválidos."
    
    # Get CSRF token
    csrf_token = form.csrf_token._value() if hasattr(form.csrf_token, '_value') else ""
    
    return f'''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Login - Sistema SENAI</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    </head>
    <body class="bg-light">
        <div class="container">
            <div class="row justify-content-center mt-5">
                <div class="col-md-6">
                    <div class="card">
                        <div class="card-header">
                            <h3 class="text-center">Sistema SENAI - Login</h3>
                        </div>
                        <div class="card-body">
                            {f'<div class="alert alert-danger">{error_message}</div>' if error_message else ''}
                            
                            <form method="POST">
                                <input type="hidden" name="csrf_token" value="{csrf_token}">
                                
                                <div class="mb-3">
                                    <label for="username" class="form-label">Usuário</label>
                                    <input type="text" class="form-control" id="username" name="username" required>
                                </div>
                                
                                <div class="mb-3">
                                    <label for="password" class="form-label">Senha</label>
                                    <input type="password" class="form-control" id="password" name="password" required>
                                </div>
                                
                                <div class="d-grid">
                                    <button type="submit" class="btn btn-primary">Entrar</button>
                                </div>
                            </form>
                            
                            <div class="mt-3 text-center">
                                <small class="text-muted">
                                    <strong>Credenciais de teste:</strong><br>
                                    Usuário: edson.lemes<br>
                                    Senha: senai103103
                                </small>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </body>
    </html>
    '''

@app.route('/logout')
@login_required
def logout():
    """Logout user"""
    logout_user()
    flash('Você foi desconectado com sucesso.', 'info')
    return redirect(url_for('login'))

@app.route('/')
@login_required
def dashboard():
    """Main dashboard"""
    try:
        # Simple stats
        total_users = User.query.count()
        
        return f'''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Dashboard - Sistema SENAI</title>
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
        </head>
        <body>
            <nav class="navbar navbar-dark bg-dark">
                <div class="container-fluid">
                    <span class="navbar-brand">Sistema SENAI - Railway</span>
                    <div>
                        <span class="navbar-text me-3">Olá, {current_user.name}!</span>
                        <a href="/logout" class="btn btn-outline-light btn-sm">Sair</a>
                    </div>
                </div>
            </nav>
            
            <div class="container mt-4">
                <div class="row">
                    <div class="col-12">
                        <h1>🎉 Sistema Funcionando no Railway!</h1>
                        <div class="alert alert-success">
                            <h4>✅ Status do Sistema:</h4>
                            <ul class="mb-0">
                                <li>✅ Aplicação carregada com sucesso</li>
                                <li>✅ Banco de dados conectado</li>
                                <li>✅ Login funcionando</li>
                                <li>✅ Usuário logado: {current_user.name}</li>
                                <li>✅ Total de usuários: {total_users}</li>
                            </ul>
                        </div>
                        
                        <div class="card mt-4">
                            <div class="card-header">
                                <h3>Dashboard Principal</h3>
                            </div>
                            <div class="card-body">
                                <p>Bem-vindo ao Sistema SENAI rodando no Railway!</p>
                                <p><strong>Usuário:</strong> {current_user.username}</p>
                                <p><strong>Nome:</strong> {current_user.name}</p>
                                <p><strong>Email:</strong> {current_user.email}</p>
                                <p><strong>Papel:</strong> {current_user.role}</p>
                                <p><strong>Data de criação:</strong> {current_user.created_at}</p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </body>
        </html>
        '''
    except Exception as e:
        logging.error(f"Dashboard error: {e}")
        return f"Erro no dashboard: {e}", 500

# Initialize database and create admin user
with app.app_context():
    try:
        # Create tables
        db.create_all()
        logging.info("✅ Database tables created/verified")
        
        # Create admin user if it doesn't exist
        admin_user = User.query.filter_by(username='edson.lemes').first()
        if not admin_user:
            admin_user = User()
            admin_user.username = 'edson.lemes'
            admin_user.name = 'Edson Lemes'
            admin_user.email = 'edson.lemes@senai.br'
            admin_user.role = 'admin'
            admin_user.set_password('senai103103')
            db.session.add(admin_user)
            db.session.commit()
            logging.info("✅ Admin user created")
        else:
            logging.info("✅ Admin user already exists")
            
        logging.info("✅ Application initialized successfully")
        
    except Exception as e:
        logging.error(f"❌ Initialization error: {e}")
        # Continue anyway for Railway deployment

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    logging.info(f"🚀 Starting Railway app on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)