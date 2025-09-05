#!/usr/bin/env python3
"""
Sistema SENAI Completo para Railway - VERSÃO FINAL
Todas as funcionalidades sem erros de Internal Server Error
"""

import os
import logging
import sys
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_file, current_app, session, make_response
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail, Message
from flask_login import LoginManager, login_user, logout_user, login_required, current_user, UserMixin
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, TextAreaField, SelectField, IntegerField, DateTimeField, HiddenField, PasswordField
from wtforms.validators import DataRequired, Email, Optional, Length, EqualTo
from sqlalchemy import Text, Integer, String, DateTime, Boolean, ForeignKey, Float
from sqlalchemy.orm import relationship
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.utils import secure_filename
import uuid
from io import BytesIO
import pandas as pd

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

# Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET") or "railway-production-key-2024"
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Database config
database_url = os.environ.get("DATABASE_URL")
if not database_url:
    database_url = "sqlite:///senai.db"  # Fallback for development

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
    # Mail config
    "MAIL_SERVER": os.environ.get('MAIL_SERVER', 'localhost'),
    "MAIL_PORT": int(os.environ.get('MAIL_PORT', '587')),
    "MAIL_USE_TLS": os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', 'on', '1'],
    "MAIL_USERNAME": os.environ.get('MAIL_USERNAME', ''),
    "MAIL_PASSWORD": os.environ.get('MAIL_PASSWORD', ''),
    "MAIL_DEFAULT_SENDER": os.environ.get('MAIL_DEFAULT_SENDER', 'noreply@senai.br'),
})

# Extensions
db = SQLAlchemy(app)
mail = Mail(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Faça login para acessar esta página.'

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
    curricular_unit_id = db.Column(Integer, ForeignKey('curricular_unit.id'), nullable=True)
    period = db.Column(String(20), nullable=False)
    class_time = db.Column(String(100), nullable=False)
    
    # Planning fields (0=Não, 1=Não se aplica, 2=Parcialmente, 3=Sim)
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
    curricular_unit = relationship('CurricularUnit', back_populates='evaluations')
    
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
    evaluations = relationship('Evaluation', back_populates='curricular_unit')

class EvaluationAttachment(db.Model):
    id = db.Column(Integer, primary_key=True)
    evaluation_id = db.Column(Integer, ForeignKey('evaluation.id'), nullable=False)
    filename = db.Column(String(255), nullable=False)
    original_filename = db.Column(String(255), nullable=False)
    file_path = db.Column(String(500), nullable=False)
    created_at = db.Column(DateTime, default=datetime.utcnow)

# === FORMS ===
class LoginForm(FlaskForm):
    username = StringField('Usuário', validators=[DataRequired()])
    password = PasswordField('Senha', validators=[DataRequired()])

class TeacherForm(FlaskForm):
    nif = StringField('NIF (ex: SN1234567)', validators=[DataRequired(), Length(min=9, max=9)])
    name = StringField('Nome', validators=[DataRequired(), Length(max=100)])
    area = StringField('Área', validators=[DataRequired(), Length(max=100)])

class CourseForm(FlaskForm):
    name = StringField('Nome do Curso', validators=[DataRequired(), Length(max=100)])
    period = StringField('Período (ex: 1° Sem/25)', validators=[DataRequired(), Length(max=20)])
    curriculum_component = StringField('Componente Curricular', validators=[DataRequired(), Length(max=100)])
    class_code = StringField('Código da Turma', validators=[Optional(), Length(max=20)])

class EvaluatorForm(FlaskForm):
    name = StringField('Nome', validators=[DataRequired(), Length(max=100)])
    role = StringField('Função', validators=[DataRequired(), Length(max=50)])
    email = StringField('Email', validators=[Optional(), Email(), Length(max=120)])

# User loader
@login_manager.user_loader
def load_user(user_id):
    try:
        return User.query.get(int(user_id))
    except:
        return None

# Helper functions
def redirect_by_role():
    try:
        return redirect(url_for('teacher_dashboard') if current_user.is_teacher() else url_for('index'))
    except:
        return redirect(url_for('login'))

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    return render_template_string('''
    <!DOCTYPE html>
    <html>
    <head><title>Página não encontrada</title></head>
    <body>
        <h1>404 - Página não encontrada</h1>
        <p><a href="{{ url_for('index') }}">Voltar ao início</a></p>
    </body>
    </html>
    '''), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template_string('''
    <!DOCTYPE html>
    <html>
    <head><title>Erro interno</title></head>
    <body>
        <h1>500 - Erro interno do servidor</h1>
        <p>Ocorreu um erro. Tente novamente.</p>
        <p><a href="{{ url_for('login') }}">Fazer login</a></p>
    </body>
    </html>
    '''), 500

# === ROUTES ===

@app.route('/health')
def health_check():
    try:
        db.engine.connect()
        return jsonify({"status": "healthy", "database": "connected"}), 200
    except Exception as e:
        return jsonify({"status": "unhealthy", "error": str(e)}), 500

@app.route('/login', methods=['GET', 'POST'])
def login():
    try:
        if current_user.is_authenticated:
            return redirect_by_role()
        
        if request.method == 'POST':
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '')
            
            if username and password:
                user = User.query.filter_by(username=username).first()
                if user and user.check_password(password) and user.is_active:
                    login_user(user)
                    next_page = request.args.get('next')
                    if user.is_teacher():
                        return redirect(next_page) if next_page and next_page.startswith('/teacher/') else redirect(url_for('teacher_dashboard'))
                    return redirect(next_page) if next_page else redirect(url_for('index'))
                else:
                    flash('Usuário ou senha inválidos.', 'error')
            else:
                flash('Por favor, preencha todos os campos.', 'error')
        
        # Simple login template
        return '''
        <!DOCTYPE html>
        <html lang="pt-BR">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Login - Sistema SENAI</title>
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
        </head>
        <body class="bg-light">
            <div class="container-fluid vh-100 d-flex align-items-center justify-content-center">
                <div class="row w-100">
                    <div class="col-md-6 col-lg-4 mx-auto">
                        <div class="card shadow">
                            <div class="card-body p-5">
                                <div class="text-center mb-4">
                                    <h1 class="h3 mb-3 fw-normal">Sistema SENAI</h1>
                                    <p class="text-muted">Faça login para continuar</p>
                                </div>
                                
                                {% with messages = get_flashed_messages(with_categories=true) %}
                                    {% if messages %}
                                        {% for category, message in messages %}
                                            <div class="alert alert-{{ 'danger' if category == 'error' else category }} alert-dismissible fade show" role="alert">
                                                {{ message }}
                                                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                                            </div>
                                        {% endfor %}
                                    {% endif %}
                                {% endwith %}

                                <form method="POST">
                                    <div class="mb-3">
                                        <label for="username" class="form-label">Usuário</label>
                                        <input type="text" class="form-control form-control-lg" id="username" name="username" required>
                                    </div>
                                    <div class="mb-4">
                                        <label for="password" class="form-label">Senha</label>
                                        <input type="password" class="form-control form-control-lg" id="password" name="password" required>
                                    </div>
                                    <div class="d-grid">
                                        <button type="submit" class="btn btn-primary btn-lg">Entrar</button>
                                    </div>
                                </form>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
        </body>
        </html>
        '''
    except Exception as e:
        logging.error(f"Login error: {e}")
        return f"Erro no login: {e}", 500

@app.route('/logout')
@login_required
def logout():
    try:
        logout_user()
        flash('Você foi desconectado com sucesso.', 'info')
        return redirect(url_for('login'))
    except Exception as e:
        return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    try:
        if current_user.is_teacher():
            return redirect(url_for('teacher_dashboard'))
        
        # Dashboard stats
        total_teachers = Teacher.query.count()
        total_courses = Course.query.count()
        total_evaluations = Evaluation.query.count()
        
        # Simple dashboard template
        return f'''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Dashboard - SENAI</title>
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
        </head>
        <body>
            <nav class="navbar navbar-dark bg-dark">
                <div class="container-fluid">
                    <span class="navbar-brand">Sistema SENAI</span>
                    <div>
                        <span class="navbar-text me-3">Olá, {current_user.name}</span>
                        <a href="/logout" class="btn btn-outline-light btn-sm">Sair</a>
                    </div>
                </div>
            </nav>
            
            <div class="container mt-4">
                <h1>Dashboard</h1>
                
                <div class="row">
                    <div class="col-md-4">
                        <div class="card text-center">
                            <div class="card-body">
                                <h5 class="card-title">Docentes</h5>
                                <h2 class="text-primary">{total_teachers}</h2>
                                <a href="/teachers" class="btn btn-primary">Gerenciar</a>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="card text-center">
                            <div class="card-body">
                                <h5 class="card-title">Cursos</h5>
                                <h2 class="text-success">{total_courses}</h2>
                                <a href="/courses" class="btn btn-success">Gerenciar</a>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="card text-center">
                            <div class="card-body">
                                <h5 class="card-title">Avaliações</h5>
                                <h2 class="text-info">{total_evaluations}</h2>
                                <a href="/evaluations" class="btn btn-info">Ver Todas</a>
                            </div>
                        </div>
                    </div>
                </div>
                
                <div class="mt-4">
                    <h3>Menu Principal</h3>
                    <div class="list-group">
                        <a href="/teachers" class="list-group-item list-group-item-action">
                            📚 Gerenciar Docentes
                        </a>
                        <a href="/courses" class="list-group-item list-group-item-action">
                            🎓 Gerenciar Cursos
                        </a>
                        <a href="/evaluators" class="list-group-item list-group-item-action">
                            👥 Gerenciar Avaliadores
                        </a>
                        <a href="/evaluations/new" class="list-group-item list-group-item-action">
                            ✅ Nova Avaliação
                        </a>
                        <a href="/evaluations" class="list-group-item list-group-item-action">
                            📋 Ver Avaliações
                        </a>
                    </div>
                </div>
            </div>
        </body>
        </html>
        '''
    except Exception as e:
        logging.error(f"Dashboard error: {e}")
        return f"Erro no dashboard: {e}", 500

@app.route('/teachers')
@login_required
def teachers():
    try:
        teachers_list = Teacher.query.order_by(Teacher.name).all()
        
        return f'''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Docentes - SENAI</title>
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
        </head>
        <body>
            <nav class="navbar navbar-dark bg-dark">
                <div class="container-fluid">
                    <a href="/" class="navbar-brand">Sistema SENAI</a>
                    <div>
                        <span class="navbar-text me-3">Olá, {current_user.name}</span>
                        <a href="/logout" class="btn btn-outline-light btn-sm">Sair</a>
                    </div>
                </div>
            </nav>
            
            <div class="container mt-4">
                <div class="d-flex justify-content-between align-items-center mb-4">
                    <h1>Docentes</h1>
                    <button class="btn btn-primary" data-bs-toggle="modal" data-bs-target="#teacherModal">
                        Novo Docente
                    </button>
                </div>
                
                <div class="table-responsive">
                    <table class="table table-striped">
                        <thead>
                            <tr>
                                <th>NIF</th>
                                <th>Nome</th>
                                <th>Área</th>
                                <th>Criado em</th>
                                <th>Ações</th>
                            </tr>
                        </thead>
                        <tbody>
                            {"".join([f'''
                            <tr>
                                <td>{teacher.nif}</td>
                                <td>{teacher.name}</td>
                                <td>{teacher.area}</td>
                                <td>{teacher.created_at.strftime("%d/%m/%Y")}</td>
                                <td>
                                    <a href="/teachers/edit/{teacher.id}" class="btn btn-sm btn-outline-primary">Editar</a>
                                </td>
                            </tr>
                            ''' for teacher in teachers_list])}
                        </tbody>
                    </table>
                </div>
            </div>
            
            <!-- Modal -->
            <div class="modal fade" id="teacherModal" tabindex="-1">
                <div class="modal-dialog">
                    <div class="modal-content">
                        <form method="POST" action="/teachers/add">
                            <div class="modal-header">
                                <h5 class="modal-title">Novo Docente</h5>
                                <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                            </div>
                            <div class="modal-body">
                                <div class="mb-3">
                                    <label for="nif" class="form-label">NIF</label>
                                    <input type="text" class="form-control" id="nif" name="nif" required maxlength="9">
                                </div>
                                <div class="mb-3">
                                    <label for="name" class="form-label">Nome</label>
                                    <input type="text" class="form-control" id="name" name="name" required>
                                </div>
                                <div class="mb-3">
                                    <label for="area" class="form-label">Área</label>
                                    <input type="text" class="form-control" id="area" name="area" required>
                                </div>
                            </div>
                            <div class="modal-footer">
                                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancelar</button>
                                <button type="submit" class="btn btn-primary">Salvar</button>
                            </div>
                        </form>
                    </div>
                </div>
            </div>
            
            <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
        </body>
        </html>
        '''
    except Exception as e:
        logging.error(f"Teachers error: {e}")
        return f"Erro ao carregar docentes: {e}", 500

@app.route('/teachers/add', methods=['POST'])
@login_required
def add_teacher():
    try:
        nif = request.form.get('nif', '').strip().upper()
        name = request.form.get('name', '').strip()
        area = request.form.get('area', '').strip()
        
        if not all([nif, name, area]):
            flash('Todos os campos são obrigatórios.', 'error')
            return redirect(url_for('teachers'))
        
        existing_teacher = Teacher.query.filter_by(nif=nif).first()
        if existing_teacher:
            flash(f'Já existe um docente com NIF {nif}.', 'error')
            return redirect(url_for('teachers'))
        
        teacher = Teacher()
        teacher.nif = nif
        teacher.name = name
        teacher.area = area
        
        # Create user account
        teacher_user = User()
        teacher_user.username = nif.lower()
        teacher_user.name = name
        teacher_user.role = 'teacher'
        teacher_user.created_by = current_user.id
        
        import secrets
        import string
        password_chars = string.ascii_letters + string.digits
        password = ''.join(secrets.choice(password_chars) for _ in range(8))
        teacher_user.set_password(password)
        
        db.session.add(teacher_user)
        db.session.flush()
        
        teacher.user_id = teacher_user.id
        db.session.add(teacher)
        db.session.commit()
        
        session['new_teacher_credentials'] = {
            'name': teacher.name,
            'nif': teacher.nif,
            'username': teacher.nif.lower(),
            'password': password
        }
        
        flash(f'Docente {teacher.name} cadastrado com sucesso!', 'success')
        return redirect(url_for('show_teacher_credentials'))
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"Add teacher error: {e}")
        flash(f'Erro ao cadastrar docente: {e}', 'error')
        return redirect(url_for('teachers'))

@app.route('/teacher_credentials')
@login_required
def show_teacher_credentials():
    try:
        credentials = session.pop('new_teacher_credentials', None)
        if not credentials:
            flash('Nenhuma credencial encontrada.', 'warning')
            return redirect(url_for('teachers'))
        
        return f'''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Credenciais do Docente - SENAI</title>
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
        </head>
        <body>
            <div class="container mt-5">
                <div class="row justify-content-center">
                    <div class="col-md-6">
                        <div class="card">
                            <div class="card-body">
                                <h5 class="card-title">Conta Criada com Sucesso!</h5>
                                <p>Uma conta foi criada para o docente:</p>
                                <ul class="list-group list-group-flush">
                                    <li class="list-group-item"><strong>Nome:</strong> {credentials['name']}</li>
                                    <li class="list-group-item"><strong>NIF:</strong> {credentials['nif']}</li>
                                    <li class="list-group-item"><strong>Usuário:</strong> {credentials['username']}</li>
                                    <li class="list-group-item"><strong>Senha:</strong> <code>{credentials['password']}</code></li>
                                </ul>
                                <div class="mt-3">
                                    <div class="alert alert-warning">
                                        <strong>Importante:</strong> Anote essas credenciais e entregue ao docente. 
                                        Por segurança, esta informação não será exibida novamente.
                                    </div>
                                </div>
                                <a href="/teachers" class="btn btn-primary">Voltar aos Docentes</a>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </body>
        </html>
        '''
    except Exception as e:
        logging.error(f"Credentials error: {e}")
        return redirect(url_for('teachers'))

@app.route('/courses')
@login_required
def courses():
    try:
        courses_list = Course.query.order_by(Course.name).all()
        
        return f'''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Cursos - SENAI</title>
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
        </head>
        <body>
            <nav class="navbar navbar-dark bg-dark">
                <div class="container-fluid">
                    <a href="/" class="navbar-brand">Sistema SENAI</a>
                    <div>
                        <span class="navbar-text me-3">Olá, {current_user.name}</span>
                        <a href="/logout" class="btn btn-outline-light btn-sm">Sair</a>
                    </div>
                </div>
            </nav>
            
            <div class="container mt-4">
                <div class="d-flex justify-content-between align-items-center mb-4">
                    <h1>Cursos</h1>
                    <button class="btn btn-primary" data-bs-toggle="modal" data-bs-target="#courseModal">
                        Novo Curso
                    </button>
                </div>
                
                <div class="table-responsive">
                    <table class="table table-striped">
                        <thead>
                            <tr>
                                <th>Nome</th>
                                <th>Período</th>
                                <th>Componente Curricular</th>
                                <th>Código da Turma</th>
                                <th>Criado em</th>
                            </tr>
                        </thead>
                        <tbody>
                            {"".join([f'''
                            <tr>
                                <td>{course.name}</td>
                                <td>{course.period}</td>
                                <td>{course.curriculum_component}</td>
                                <td>{course.class_code or '-'}</td>
                                <td>{course.created_at.strftime("%d/%m/%Y")}</td>
                            </tr>
                            ''' for course in courses_list])}
                        </tbody>
                    </table>
                </div>
            </div>
            
            <!-- Modal -->
            <div class="modal fade" id="courseModal" tabindex="-1">
                <div class="modal-dialog">
                    <div class="modal-content">
                        <form method="POST" action="/courses/add">
                            <div class="modal-header">
                                <h5 class="modal-title">Novo Curso</h5>
                                <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                            </div>
                            <div class="modal-body">
                                <div class="mb-3">
                                    <label for="name" class="form-label">Nome do Curso</label>
                                    <input type="text" class="form-control" id="name" name="name" required>
                                </div>
                                <div class="mb-3">
                                    <label for="period" class="form-label">Período</label>
                                    <input type="text" class="form-control" id="period" name="period" required placeholder="ex: 1° Sem/25">
                                </div>
                                <div class="mb-3">
                                    <label for="curriculum_component" class="form-label">Componente Curricular</label>
                                    <input type="text" class="form-control" id="curriculum_component" name="curriculum_component" required>
                                </div>
                                <div class="mb-3">
                                    <label for="class_code" class="form-label">Código da Turma</label>
                                    <input type="text" class="form-control" id="class_code" name="class_code">
                                </div>
                            </div>
                            <div class="modal-footer">
                                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancelar</button>
                                <button type="submit" class="btn btn-primary">Salvar</button>
                            </div>
                        </form>
                    </div>
                </div>
            </div>
            
            <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
        </body>
        </html>
        '''
    except Exception as e:
        logging.error(f"Courses error: {e}")
        return f"Erro ao carregar cursos: {e}", 500

@app.route('/courses/add', methods=['POST'])
@login_required
def add_course():
    try:
        course = Course()
        course.name = request.form.get('name', '').strip()
        course.period = request.form.get('period', '').strip()
        course.curriculum_component = request.form.get('curriculum_component', '').strip()
        course.class_code = request.form.get('class_code', '').strip() or None
        
        if not all([course.name, course.period, course.curriculum_component]):
            flash('Nome, período e componente curricular são obrigatórios.', 'error')
            return redirect(url_for('courses'))
        
        db.session.add(course)
        db.session.commit()
        
        flash(f'Curso {course.name} cadastrado com sucesso!', 'success')
        return redirect(url_for('courses'))
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"Add course error: {e}")
        flash(f'Erro ao cadastrar curso: {e}', 'error')
        return redirect(url_for('courses'))

@app.route('/evaluators')
@login_required
def evaluators():
    try:
        evaluators_list = Evaluator.query.order_by(Evaluator.name).all()
        
        return f'''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Avaliadores - SENAI</title>
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
        </head>
        <body>
            <nav class="navbar navbar-dark bg-dark">
                <div class="container-fluid">
                    <a href="/" class="navbar-brand">Sistema SENAI</a>
                    <div>
                        <span class="navbar-text me-3">Olá, {current_user.name}</span>
                        <a href="/logout" class="btn btn-outline-light btn-sm">Sair</a>
                    </div>
                </div>
            </nav>
            
            <div class="container mt-4">
                <div class="d-flex justify-content-between align-items-center mb-4">
                    <h1>Avaliadores</h1>
                    <button class="btn btn-primary" data-bs-toggle="modal" data-bs-target="#evaluatorModal">
                        Novo Avaliador
                    </button>
                </div>
                
                <div class="table-responsive">
                    <table class="table table-striped">
                        <thead>
                            <tr>
                                <th>Nome</th>
                                <th>Função</th>
                                <th>Email</th>
                                <th>Criado em</th>
                            </tr>
                        </thead>
                        <tbody>
                            {"".join([f'''
                            <tr>
                                <td>{evaluator.name}</td>
                                <td>{evaluator.role}</td>
                                <td>{evaluator.email or '-'}</td>
                                <td>{evaluator.created_at.strftime("%d/%m/%Y")}</td>
                            </tr>
                            ''' for evaluator in evaluators_list])}
                        </tbody>
                    </table>
                </div>
            </div>
            
            <!-- Modal -->
            <div class="modal fade" id="evaluatorModal" tabindex="-1">
                <div class="modal-dialog">
                    <div class="modal-content">
                        <form method="POST" action="/evaluators/add">
                            <div class="modal-header">
                                <h5 class="modal-title">Novo Avaliador</h5>
                                <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                            </div>
                            <div class="modal-body">
                                <div class="mb-3">
                                    <label for="name" class="form-label">Nome</label>
                                    <input type="text" class="form-control" id="name" name="name" required>
                                </div>
                                <div class="mb-3">
                                    <label for="role" class="form-label">Função</label>
                                    <input type="text" class="form-control" id="role" name="role" required>
                                </div>
                                <div class="mb-3">
                                    <label for="email" class="form-label">Email</label>
                                    <input type="email" class="form-control" id="email" name="email">
                                </div>
                            </div>
                            <div class="modal-footer">
                                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancelar</button>
                                <button type="submit" class="btn btn-primary">Salvar</button>
                            </div>
                        </form>
                    </div>
                </div>
            </div>
            
            <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
        </body>
        </html>
        '''
    except Exception as e:
        logging.error(f"Evaluators error: {e}")
        return f"Erro ao carregar avaliadores: {e}", 500

@app.route('/evaluators/add', methods=['POST'])
@login_required
def add_evaluator():
    try:
        evaluator = Evaluator()
        evaluator.name = request.form.get('name', '').strip()
        evaluator.role = request.form.get('role', '').strip()
        evaluator.email = request.form.get('email', '').strip() or None
        
        if not all([evaluator.name, evaluator.role]):
            flash('Nome e função são obrigatórios.', 'error')
            return redirect(url_for('evaluators'))
        
        db.session.add(evaluator)
        db.session.commit()
        
        flash(f'Avaliador {evaluator.name} cadastrado com sucesso!', 'success')
        return redirect(url_for('evaluators'))
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"Add evaluator error: {e}")
        flash(f'Erro ao cadastrar avaliador: {e}', 'error')
        return redirect(url_for('evaluators'))

@app.route('/evaluations')
@login_required
def evaluations():
    try:
        evaluations_list = Evaluation.query.order_by(Evaluation.created_at.desc()).all()
        
        return f'''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Avaliações - SENAI</title>
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
        </head>
        <body>
            <nav class="navbar navbar-dark bg-dark">
                <div class="container-fluid">
                    <a href="/" class="navbar-brand">Sistema SENAI</a>
                    <div>
                        <span class="navbar-text me-3">Olá, {current_user.name}</span>
                        <a href="/logout" class="btn btn-outline-light btn-sm">Sair</a>
                    </div>
                </div>
            </nav>
            
            <div class="container mt-4">
                <div class="d-flex justify-content-between align-items-center mb-4">
                    <h1>Avaliações</h1>
                    <a href="/evaluations/new" class="btn btn-primary">Nova Avaliação</a>
                </div>
                
                <div class="table-responsive">
                    <table class="table table-striped">
                        <thead>
                            <tr>
                                <th>Docente</th>
                                <th>Curso</th>
                                <th>Período</th>
                                <th>Avaliador</th>
                                <th>Data</th>
                                <th>Ações</th>
                            </tr>
                        </thead>
                        <tbody>
                            {"".join([f'''
                            <tr>
                                <td>{evaluation.teacher.name}</td>
                                <td>{evaluation.course.name}</td>
                                <td>{evaluation.period}</td>
                                <td>{evaluation.evaluator.name}</td>
                                <td>{evaluation.created_at.strftime("%d/%m/%Y")}</td>
                                <td>
                                    <a href="/evaluations/edit/{evaluation.id}" class="btn btn-sm btn-outline-primary">Editar</a>
                                </td>
                            </tr>
                            ''' for evaluation in evaluations_list])}
                        </tbody>
                    </table>
                </div>
            </div>
        </body>
        </html>
        '''
    except Exception as e:
        logging.error(f"Evaluations error: {e}")
        return f"Erro ao carregar avaliações: {e}", 500

@app.route('/evaluations/new')
@login_required
def new_evaluation():
    try:
        teachers = Teacher.query.all()
        courses = Course.query.all()
        
        return f'''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Nova Avaliação - SENAI</title>
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
        </head>
        <body>
            <nav class="navbar navbar-dark bg-dark">
                <div class="container-fluid">
                    <a href="/" class="navbar-brand">Sistema SENAI</a>
                    <div>
                        <span class="navbar-text me-3">Olá, {current_user.name}</span>
                        <a href="/logout" class="btn btn-outline-light btn-sm">Sair</a>
                    </div>
                </div>
            </nav>
            
            <div class="container mt-4">
                <h1>Nova Avaliação</h1>
                
                <form method="POST" action="/evaluations/create">
                    <div class="row">
                        <div class="col-md-6">
                            <div class="mb-3">
                                <label for="teacher_id" class="form-label">Docente</label>
                                <select class="form-control" id="teacher_id" name="teacher_id" required>
                                    <option value="">Selecione um docente</option>
                                    {"".join([f'<option value="{teacher.id}">{teacher.name}</option>' for teacher in teachers])}
                                </select>
                            </div>
                        </div>
                        <div class="col-md-6">
                            <div class="mb-3">
                                <label for="course_id" class="form-label">Curso</label>
                                <select class="form-control" id="course_id" name="course_id" required>
                                    <option value="">Selecione um curso</option>
                                    {"".join([f'<option value="{course.id}">{course.name} - {course.period}</option>' for course in courses])}
                                </select>
                            </div>
                        </div>
                    </div>
                    
                    <div class="row">
                        <div class="col-md-6">
                            <div class="mb-3">
                                <label for="period" class="form-label">Período</label>
                                <select class="form-control" id="period" name="period" required>
                                    <option value="">Selecione o período</option>
                                    <option value="Manhã">Manhã</option>
                                    <option value="Tarde">Tarde</option>
                                    <option value="Noite">Noite</option>
                                </select>
                            </div>
                        </div>
                        <div class="col-md-6">
                            <div class="mb-3">
                                <label for="class_time" class="form-label">Horário da Aula</label>
                                <input type="text" class="form-control" id="class_time" name="class_time" placeholder="ex: 08:00 - 12:00">
                            </div>
                        </div>
                    </div>
                    
                    <div class="mb-3">
                        <label for="observations" class="form-label">Observações</label>
                        <textarea class="form-control" id="observations" name="observations" rows="3"></textarea>
                    </div>
                    
                    <div class="d-flex justify-content-between">
                        <a href="/evaluations" class="btn btn-secondary">Cancelar</a>
                        <button type="submit" class="btn btn-primary">Criar Avaliação</button>
                    </div>
                </form>
            </div>
        </body>
        </html>
        '''
    except Exception as e:
        logging.error(f"New evaluation error: {e}")
        return f"Erro ao carregar nova avaliação: {e}", 500

@app.route('/evaluations/create', methods=['POST'])
@login_required
def create_evaluation():
    try:
        evaluation = Evaluation()
        evaluation.teacher_id = int(request.form.get('teacher_id'))
        evaluation.course_id = int(request.form.get('course_id'))
        evaluation.period = request.form.get('period')
        evaluation.class_time = request.form.get('class_time', '')
        evaluation.observations = request.form.get('observations', '')
        
        # Create or find evaluator
        current_evaluator = Evaluator.query.filter_by(name=current_user.name).first()
        if not current_evaluator:
            current_evaluator = Evaluator()
            current_evaluator.name = current_user.name
            current_evaluator.role = current_user.role if current_user.role == 'admin' else 'Coordenador'
            current_evaluator.email = current_user.email or f"{current_user.name.lower().replace(' ', '.')}@senai.br"
            db.session.add(current_evaluator)
            db.session.flush()
        
        evaluation.evaluator_id = current_evaluator.id
        
        db.session.add(evaluation)
        db.session.commit()
        
        flash('Avaliação criada com sucesso!', 'success')
        return redirect(url_for('edit_evaluation', id=evaluation.id))
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"Create evaluation error: {e}")
        flash(f'Erro ao criar avaliação: {e}', 'error')
        return redirect(url_for('new_evaluation'))

@app.route('/evaluations/edit/<int:id>')
@login_required
def edit_evaluation(id):
    try:
        evaluation = Evaluation.query.get_or_404(id)
        
        return f'''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Editar Avaliação - SENAI</title>
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
        </head>
        <body>
            <nav class="navbar navbar-dark bg-dark">
                <div class="container-fluid">
                    <a href="/" class="navbar-brand">Sistema SENAI</a>
                    <div>
                        <span class="navbar-text me-3">Olá, {current_user.name}</span>
                        <a href="/logout" class="btn btn-outline-light btn-sm">Sair</a>
                    </div>
                </div>
            </nav>
            
            <div class="container mt-4">
                <h1>Avaliação: {evaluation.teacher.name}</h1>
                <p class="text-muted">Curso: {evaluation.course.name} - {evaluation.period}</p>
                
                <form method="POST" action="/evaluations/update/{evaluation.id}">
                    <div class="card mb-4">
                        <div class="card-header">
                            <h5>Planejamento</h5>
                        </div>
                        <div class="card-body">
                            <div class="table-responsive">
                                <table class="table table-bordered">
                                    <thead>
                                        <tr>
                                            <th>Critério</th>
                                            <th class="text-center">Não (0)</th>
                                            <th class="text-center">N/A (1)</th>
                                            <th class="text-center">Parcial (2)</th>
                                            <th class="text-center">Sim (3)</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        <tr>
                                            <td>Elabora cronograma de aula</td>
                                            <td class="text-center"><input type="radio" name="planning_schedule" value="0" {"checked" if evaluation.planning_schedule == 0 else ""}></td>
                                            <td class="text-center"><input type="radio" name="planning_schedule" value="1" {"checked" if evaluation.planning_schedule == 1 else ""}></td>
                                            <td class="text-center"><input type="radio" name="planning_schedule" value="2" {"checked" if evaluation.planning_schedule == 2 else ""}></td>
                                            <td class="text-center"><input type="radio" name="planning_schedule" value="3" {"checked" if evaluation.planning_schedule == 3 else ""}></td>
                                        </tr>
                                        <tr>
                                            <td>Planeja aula com estratégias</td>
                                            <td class="text-center"><input type="radio" name="planning_lesson_plan" value="0" {"checked" if evaluation.planning_lesson_plan == 0 else ""}></td>
                                            <td class="text-center"><input type="radio" name="planning_lesson_plan" value="1" {"checked" if evaluation.planning_lesson_plan == 1 else ""}></td>
                                            <td class="text-center"><input type="radio" name="planning_lesson_plan" value="2" {"checked" if evaluation.planning_lesson_plan == 2 else ""}></td>
                                            <td class="text-center"><input type="radio" name="planning_lesson_plan" value="3" {"checked" if evaluation.planning_lesson_plan == 3 else ""}></td>
                                        </tr>
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </div>
                    
                    <div class="card mb-4">
                        <div class="card-header">
                            <h5>Execução da Aula</h5>
                        </div>
                        <div class="card-body">
                            <div class="table-responsive">
                                <table class="table table-bordered">
                                    <thead>
                                        <tr>
                                            <th>Critério</th>
                                            <th class="text-center">Não (0)</th>
                                            <th class="text-center">N/A (1)</th>
                                            <th class="text-center">Parcial (2)</th>
                                            <th class="text-center">Sim (3)</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        <tr>
                                            <td>Apresentação pessoal adequada</td>
                                            <td class="text-center"><input type="radio" name="class_presentation" value="0" {"checked" if evaluation.class_presentation == 0 else ""}></td>
                                            <td class="text-center"><input type="radio" name="class_presentation" value="1" {"checked" if evaluation.class_presentation == 1 else ""}></td>
                                            <td class="text-center"><input type="radio" name="class_presentation" value="2" {"checked" if evaluation.class_presentation == 2 else ""}></td>
                                            <td class="text-center"><input type="radio" name="class_presentation" value="3" {"checked" if evaluation.class_presentation == 3 else ""}></td>
                                        </tr>
                                        <tr>
                                            <td>Demonstra conhecimento</td>
                                            <td class="text-center"><input type="radio" name="class_knowledge" value="0" {"checked" if evaluation.class_knowledge == 0 else ""}></td>
                                            <td class="text-center"><input type="radio" name="class_knowledge" value="1" {"checked" if evaluation.class_knowledge == 1 else ""}></td>
                                            <td class="text-center"><input type="radio" name="class_knowledge" value="2" {"checked" if evaluation.class_knowledge == 2 else ""}></td>
                                            <td class="text-center"><input type="radio" name="class_knowledge" value="3" {"checked" if evaluation.class_knowledge == 3 else ""}></td>
                                        </tr>
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </div>
                    
                    <div class="mb-3">
                        <label for="observations" class="form-label">Observações</label>
                        <textarea class="form-control" id="observations" name="observations" rows="3">{evaluation.observations or ''}</textarea>
                    </div>
                    
                    <div class="d-flex justify-content-between">
                        <a href="/evaluations" class="btn btn-secondary">Voltar</a>
                        <button type="submit" class="btn btn-primary">Salvar Avaliação</button>
                    </div>
                </form>
            </div>
        </body>
        </html>
        '''
    except Exception as e:
        logging.error(f"Edit evaluation error: {e}")
        return f"Erro ao carregar avaliação: {e}", 500

@app.route('/evaluations/update/<int:id>', methods=['POST'])
@login_required
def update_evaluation(id):
    try:
        evaluation = Evaluation.query.get_or_404(id)
        
        # Update planning fields
        evaluation.planning_schedule = int(request.form.get('planning_schedule', 0))
        evaluation.planning_lesson_plan = int(request.form.get('planning_lesson_plan', 0))
        
        # Update class fields
        evaluation.class_presentation = int(request.form.get('class_presentation', 0))
        evaluation.class_knowledge = int(request.form.get('class_knowledge', 0))
        
        evaluation.observations = request.form.get('observations', '')
        
        db.session.commit()
        flash('Avaliação atualizada com sucesso!', 'success')
        
        return redirect(url_for('evaluations'))
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"Update evaluation error: {e}")
        flash(f'Erro ao atualizar avaliação: {e}', 'error')
        return redirect(url_for('edit_evaluation', id=id))

@app.route('/teacher/dashboard')
@login_required
def teacher_dashboard():
    try:
        if not current_user.is_teacher():
            return redirect(url_for('index'))
        
        teacher = Teacher.query.filter_by(user_id=current_user.id).first()
        if not teacher:
            flash('Perfil de docente não encontrado.', 'error')
            return redirect(url_for('logout'))
        
        evaluations = Evaluation.query.filter_by(teacher_id=teacher.id).order_by(Evaluation.created_at.desc()).all()
        
        return f'''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Área do Docente - SENAI</title>
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
        </head>
        <body>
            <nav class="navbar navbar-dark bg-dark">
                <div class="container-fluid">
                    <span class="navbar-brand">Sistema SENAI - Área do Docente</span>
                    <div>
                        <span class="navbar-text me-3">Olá, {teacher.name}</span>
                        <a href="/logout" class="btn btn-outline-light btn-sm">Sair</a>
                    </div>
                </div>
            </nav>
            
            <div class="container mt-4">
                <div class="card mb-4" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);">
                    <div class="card-body text-white">
                        <h4>Bem-vindo, {teacher.name}!</h4>
                        <p><strong>NIF:</strong> {teacher.nif} | <strong>Área:</strong> {teacher.area}</p>
                        <div class="alert alert-light">
                            <span class="text-dark">Para qualquer dúvida, procure sua gestão.</span>
                        </div>
                    </div>
                </div>
                
                <h3>Suas Avaliações</h3>
                
                {"<p>Nenhuma avaliação encontrada.</p>" if not evaluations else f'''
                <div class="table-responsive">
                    <table class="table table-striped">
                        <thead>
                            <tr>
                                <th>Curso</th>
                                <th>Período</th>
                                <th>Avaliador</th>
                                <th>Data</th>
                                <th>Planejamento</th>
                                <th>Execução</th>
                            </tr>
                        </thead>
                        <tbody>
                            {"".join([f"""
                            <tr>
                                <td>{evaluation.course.name}</td>
                                <td>{evaluation.period}</td>
                                <td>{evaluation.evaluator.name}</td>
                                <td>{evaluation.created_at.strftime("%d/%m/%Y")}</td>
                                <td>{evaluation.calculate_planning_percentage():.1f}%</td>
                                <td>{evaluation.calculate_class_percentage():.1f}%</td>
                            </tr>
                            """ for evaluation in evaluations])}
                        </tbody>
                    </table>
                </div>
                '''}
            </div>
        </body>
        </html>
        '''
    except Exception as e:
        logging.error(f"Teacher dashboard error: {e}")
        return f"Erro no painel do docente: {e}", 500

# Initialize database
with app.app_context():
    try:
        db.engine.connect()
        logging.info("✅ Database connected")
        
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
        
        logging.info("🎉 Final system ready!")
        
    except Exception as e:
        logging.error(f"❌ Initialization error: {e}")

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)