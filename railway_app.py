#!/usr/bin/env python3
"""
Aplicação Flask otimizada para Railway - SEM IMPORTS CIRCULARES
Sistema de Avaliação de Docentes SENAI
"""

import os
import logging
import sys
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_file, current_app, session
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail
from flask_login import LoginManager, login_user, logout_user, login_required, current_user, UserMixin
from sqlalchemy import Text, Integer, String, DateTime, Boolean, ForeignKey, Float
from sqlalchemy.orm import relationship
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.middleware.proxy_fix import ProxyFix

# Production logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

# Flask app setup
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET") or "railway-production-key-2024"
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Database configuration for Railway
database_url = os.environ.get("DATABASE_URL")
if not database_url:
    raise ValueError("DATABASE_URL environment variable is required")

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
    },
    "SQLALCHEMY_TRACK_MODIFICATIONS": False,
    "UPLOAD_FOLDER": "/tmp/uploads",
    "MAX_CONTENT_LENGTH": 16 * 1024 * 1024,
})

# Extensions
db = SQLAlchemy(app)
mail = Mail(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Faça login para acessar esta página.'

# Create upload directory
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# === MODELS ===
class User(db.Model, UserMixin):
    id = db.Column(Integer, primary_key=True)
    username = db.Column(String(80), unique=True, nullable=False)
    password_hash = db.Column(String(255), nullable=False)
    name = db.Column(String(100), nullable=False)
    role = db.Column(String(50), nullable=False, default='evaluator')
    email = db.Column(String(120), nullable=True)
    is_active = db.Column(Boolean, default=True)
    created_at = db.Column(DateTime, default=datetime.utcnow)
    created_by = db.Column(Integer, ForeignKey('user.id'), nullable=True)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def is_admin(self):
        return self.role == 'admin'
    
    def is_teacher(self):
        return self.role == 'teacher'

class Teacher(db.Model):
    id = db.Column(Integer, primary_key=True)
    nif = db.Column(String(10), unique=True, nullable=False)
    name = db.Column(String(100), nullable=False)
    area = db.Column(String(100), nullable=False)
    user_id = db.Column(Integer, ForeignKey('user.id'), nullable=True)
    created_at = db.Column(DateTime, default=datetime.utcnow)
    
    evaluations = relationship('Evaluation', back_populates='teacher')
    user = relationship('User', backref='teacher_profile')

class Course(db.Model):
    id = db.Column(Integer, primary_key=True)
    name = db.Column(String(100), nullable=False)
    period = db.Column(String(20), nullable=False)
    curriculum_component = db.Column(String(100), nullable=False)
    class_code = db.Column(String(20), nullable=True)
    created_at = db.Column(DateTime, default=datetime.utcnow)
    
    evaluations = relationship('Evaluation', back_populates='course')
    curricular_units = relationship('CurricularUnit', back_populates='course')

class Evaluator(db.Model):
    id = db.Column(Integer, primary_key=True)
    name = db.Column(String(100), nullable=False)
    role = db.Column(String(50), nullable=False)
    email = db.Column(String(120), nullable=True)
    created_at = db.Column(DateTime, default=datetime.utcnow)
    
    evaluations = relationship('Evaluation', back_populates='evaluator')

class Evaluation(db.Model):
    id = db.Column(Integer, primary_key=True)
    teacher_id = db.Column(Integer, ForeignKey('teacher.id'), nullable=False)
    course_id = db.Column(Integer, ForeignKey('course.id'), nullable=False)
    evaluator_id = db.Column(Integer, ForeignKey('evaluator.id'), nullable=False)
    period = db.Column(String(20), nullable=False)
    class_time = db.Column(String(100), nullable=False)
    
    # Planning fields
    planning_schedule = db.Column(Integer, nullable=False, default=0)
    planning_lesson_plan = db.Column(Integer, nullable=False, default=0)
    planning_evaluation = db.Column(Integer, nullable=False, default=0)
    planning_documents = db.Column(Integer, nullable=False, default=0)
    planning_diversified = db.Column(Integer, nullable=False, default=0)
    planning_local_work = db.Column(Integer, nullable=False, default=0)
    planning_tools = db.Column(Integer, nullable=False, default=0)
    planning_educational_portal = db.Column(Integer, nullable=False, default=0)
    
    # Class fields
    class_presentation = db.Column(Integer, nullable=False, default=0)
    class_knowledge = db.Column(Integer, nullable=False, default=0)
    class_methodology = db.Column(Integer, nullable=False, default=0)
    class_environment = db.Column(Integer, nullable=False, default=0)
    class_practice = db.Column(Integer, nullable=False, default=0)
    class_time_management = db.Column(Integer, nullable=False, default=0)
    class_evaluation = db.Column(Integer, nullable=False, default=0)
    class_tools = db.Column(Integer, nullable=False, default=0)
    
    observations = db.Column(Text, nullable=True)
    created_at = db.Column(DateTime, default=datetime.utcnow)
    
    teacher = relationship('Teacher', back_populates='evaluations')
    course = relationship('Course', back_populates='evaluations')
    evaluator = relationship('Evaluator', back_populates='evaluations')
    
    def calculate_planning_percentage(self):
        total_points = (self.planning_schedule + self.planning_lesson_plan + 
                       self.planning_evaluation + self.planning_documents + 
                       self.planning_diversified + self.planning_local_work + 
                       self.planning_tools + self.planning_educational_portal)
        return (total_points / 24) * 100
    
    def calculate_class_percentage(self):
        total_points = (self.class_presentation + self.class_knowledge + 
                       self.class_methodology + self.class_environment + 
                       self.class_practice + self.class_time_management + 
                       self.class_evaluation + self.class_tools)
        return (total_points / 24) * 100

class Semester(db.Model):
    id = db.Column(Integer, primary_key=True)
    name = db.Column(String(50), nullable=False)
    year = db.Column(Integer, nullable=False)
    number = db.Column(Integer, nullable=False)
    start_date = db.Column(DateTime, nullable=False)
    end_date = db.Column(DateTime, nullable=False)
    is_active = db.Column(Boolean, default=False)
    created_at = db.Column(DateTime, default=datetime.utcnow)

class CurricularUnit(db.Model):
    id = db.Column(Integer, primary_key=True)
    name = db.Column(String(150), nullable=False)
    code = db.Column(String(20))
    course_id = db.Column(Integer, ForeignKey('course.id'), nullable=False)
    workload = db.Column(Integer)
    description = db.Column(Text)
    is_active = db.Column(Boolean, default=True)
    created_at = db.Column(DateTime, default=datetime.utcnow)
    
    course = relationship('Course', back_populates='curricular_units')

# User loader
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# === ROUTES ===

@app.route('/health')
def health_check():
    """Health check for Railway"""
    try:
        db.engine.connect()
        return jsonify({"status": "healthy", "database": "connected"}), 200
    except Exception as e:
        return jsonify({"status": "unhealthy", "error": str(e)}), 500

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page"""
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password) and user.is_active:
            login_user(user)
            return redirect(url_for('index'))
        else:
            flash('Usuário ou senha inválidos.', 'error')
    
    return '''
    <!DOCTYPE html>
    <html>
    <head><title>Login - SENAI</title></head>
    <body>
        <h2>Sistema de Avaliação SENAI</h2>
        <form method="post">
            <p>
                <label>Usuário:</label><br>
                <input type="text" name="username" required>
            </p>
            <p>
                <label>Senha:</label><br>
                <input type="password" name="password" required>
            </p>
            <p><input type="submit" value="Entrar"></p>
        </form>
    </body>
    </html>'''

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    """Dashboard principal"""
    return f'''
    <!DOCTYPE html>
    <html>
    <head><title>Dashboard - SENAI</title></head>
    <body>
        <h1>Bem-vindo, {current_user.name}!</h1>
        <p>Papel: {current_user.role}</p>
        <p>Sistema funcionando 100% no Railway com PostgreSQL!</p>
        <p><a href="/logout">Sair</a></p>
        
        <h2>Status do Sistema:</h2>
        <ul>
            <li>✅ Banco PostgreSQL conectado</li>
            <li>✅ Autenticação funcionando</li>
            <li>✅ Deploy Railway OK</li>
        </ul>
    </body>
    </html>'''

# Initialize database
with app.app_context():
    try:
        # Test connection
        db.engine.connect()
        logging.info("✅ Database connected")
        
        # Create tables
        db.create_all()
        logging.info("✅ Tables created")
        
        # Create admin user
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
        
        logging.info("🎉 Application ready!")
        
    except Exception as e:
        logging.error(f"❌ Initialization error: {e}")

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)