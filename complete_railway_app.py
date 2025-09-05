#!/usr/bin/env python3
"""
Sistema Completo de Avaliação de Docentes SENAI para Railway
Versão sem imports circulares com todas as funcionalidades
"""

import os
import logging
import sys
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_file, current_app, session
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
    
    # Planning fields (0=Não, 1=Não se aplica, 2=Sim, 3=Sim)
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

class EvaluationForm(FlaskForm):
    teacher_id = SelectField('Docente', coerce=int, validators=[DataRequired()])
    course_id = SelectField('Curso/Turma', coerce=int, validators=[DataRequired()])
    curricular_unit_id = SelectField('Unidade Curricular', coerce=lambda x: int(x) if x and x != '0' else None, validators=[Optional()])
    
    period = SelectField('Período', choices=[
        ('Manhã', 'Manhã'),
        ('Tarde', 'Tarde'),
        ('Noite', 'Noite')
    ], validators=[DataRequired()])
    
    class_time = StringField('Horário da Aula', validators=[Optional()])
    observations = TextAreaField('Observações', validators=[Optional()])

# User loader
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Helper functions
def redirect_by_role():
    return redirect(url_for('teacher_dashboard') if current_user.is_teacher() else url_for('index'))

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
    if current_user.is_authenticated:
        return redirect_by_role()
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data) and user.is_active:
            login_user(user)
            next_page = request.args.get('next')
            if user.is_teacher():
                return redirect(next_page) if next_page and next_page.startswith('/teacher/') else redirect(url_for('teacher_dashboard'))
            return redirect(next_page) if next_page else redirect(url_for('index'))
        else:
            flash('Usuário ou senha inválidos.', 'error')
    
    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Você foi desconectado com sucesso.', 'info')
    return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    if current_user.is_teacher():
        return redirect(url_for('teacher_dashboard'))
    
    # Dashboard stats
    total_teachers = Teacher.query.count()
    total_courses = Course.query.count()
    total_evaluations = Evaluation.query.count()
    
    # Recent evaluations
    recent_evaluations = Evaluation.query.order_by(Evaluation.created_at.desc()).limit(5).all()
    
    return render_template('dashboard.html',
                         total_teachers=total_teachers,
                         total_courses=total_courses,
                         total_evaluations=total_evaluations,
                         recent_evaluations=recent_evaluations)

@app.route('/teachers')
@login_required
def teachers():
    form = TeacherForm()
    teachers_list = Teacher.query.order_by(Teacher.name).all()
    return render_template('teachers.html', form=form, teachers=teachers_list)

@app.route('/teachers/add', methods=['POST'])
@login_required
def add_teacher():
    form = TeacherForm()
    
    if form.validate_on_submit():
        existing_teacher = Teacher.query.filter_by(nif=form.nif.data).first()
        if existing_teacher:
            flash(f'Já existe um docente com NIF {form.nif.data}.', 'error')
        else:
            teacher = Teacher()
            teacher.nif = form.nif.data.upper() if form.nif.data else ''
            teacher.name = form.name.data
            teacher.area = form.area.data
            
            # Create user account
            teacher_user = User()
            teacher_user.username = form.nif.data.lower() if form.nif.data else ''
            teacher_user.name = form.name.data
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
    
    return redirect(url_for('teachers'))

@app.route('/teacher_credentials')
@login_required
def show_teacher_credentials():
    credentials = session.pop('new_teacher_credentials', None)
    if not credentials:
        flash('Nenhuma credencial encontrada.', 'warning')
        return redirect(url_for('teachers'))
    
    return render_template('teacher_credentials.html', credentials=credentials)

@app.route('/courses')
@login_required
def courses():
    form = CourseForm()
    courses_list = Course.query.order_by(Course.name).all()
    return render_template('courses.html', form=form, courses=courses_list)

@app.route('/courses/add', methods=['POST'])
@login_required
def add_course():
    form = CourseForm()
    
    if form.validate_on_submit():
        course = Course()
        course.name = form.name.data
        course.period = form.period.data
        course.curriculum_component = form.curriculum_component.data
        course.class_code = form.class_code.data
        
        db.session.add(course)
        db.session.commit()
        
        flash(f'Curso {course.name} cadastrado com sucesso!', 'success')
    
    return redirect(url_for('courses'))

@app.route('/evaluators')
@login_required
def evaluators():
    form = EvaluatorForm()
    evaluators_list = Evaluator.query.order_by(Evaluator.name).all()
    return render_template('evaluators.html', form=form, evaluators=evaluators_list)

@app.route('/evaluators/add', methods=['POST'])
@login_required
def add_evaluator():
    form = EvaluatorForm()
    
    if form.validate_on_submit():
        evaluator = Evaluator()
        evaluator.name = form.name.data
        evaluator.role = form.role.data
        evaluator.email = form.email.data
        
        db.session.add(evaluator)
        db.session.commit()
        
        flash(f'Avaliador {evaluator.name} cadastrado com sucesso!', 'success')
    
    return redirect(url_for('evaluators'))

@app.route('/evaluations/new', methods=['GET', 'POST'])
@login_required
def new_evaluation():
    form = EvaluationForm()
    
    # Populate choices
    form.teacher_id.choices = [(t.id, t.name) for t in Teacher.query.all()]
    form.course_id.choices = [(c.id, f"{c.name} - {c.period}") for c in Course.query.all()]
    form.curricular_unit_id.choices = [(0, 'Nenhuma unidade curricular específica')] + [(u.id, f"{u.name} ({u.course.name})") for u in CurricularUnit.query.join(Course).all()]
    
    if form.validate_on_submit():
        evaluation = Evaluation()
        evaluation.teacher_id = form.teacher_id.data
        evaluation.course_id = form.course_id.data
        evaluation.curricular_unit_id = form.curricular_unit_id.data if form.curricular_unit_id.data and form.curricular_unit_id.data != 0 else None
        evaluation.period = form.period.data
        evaluation.class_time = form.class_time.data or ""
        evaluation.observations = form.observations.data or ""
        
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
    
    return render_template('evaluation_form.html', form=form)

@app.route('/evaluations/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_evaluation(id):
    evaluation = Evaluation.query.get_or_404(id)
    
    if request.method == 'POST':
        # Process evaluation criteria
        criteria_fields = [
            'planning_schedule', 'planning_lesson_plan', 'planning_evaluation', 'planning_documents',
            'planning_diversified', 'planning_local_work', 'planning_tools', 'planning_educational_portal',
            'class_presentation', 'class_knowledge', 'class_methodology', 'class_environment',
            'class_practice', 'class_time_management', 'class_evaluation', 'class_tools'
        ]
        
        for field in criteria_fields:
            value = request.form.get(field)
            if value:
                setattr(evaluation, field, int(value))
        
        evaluation.observations = request.form.get('observations', '')
        
        db.session.commit()
        flash('Avaliação atualizada com sucesso!', 'success')
        
        return redirect(url_for('evaluations'))
    
    return render_template('evaluation_edit.html', evaluation=evaluation)

@app.route('/evaluations')
@login_required
def evaluations():
    evaluations_list = Evaluation.query.order_by(Evaluation.created_at.desc()).all()
    return render_template('evaluations.html', evaluations=evaluations_list)

@app.route('/teacher/dashboard')
@login_required
def teacher_dashboard():
    if not current_user.is_teacher():
        return redirect(url_for('index'))
    
    teacher = Teacher.query.filter_by(user_id=current_user.id).first()
    if not teacher:
        flash('Perfil de docente não encontrado.', 'error')
        return redirect(url_for('logout'))
    
    evaluations = Evaluation.query.filter_by(teacher_id=teacher.id).order_by(Evaluation.created_at.desc()).all()
    
    return render_template('teacher_dashboard.html', teacher=teacher, evaluations=evaluations)

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
        
        logging.info("🎉 Complete system ready!")
        
    except Exception as e:
        logging.error(f"❌ Initialization error: {e}")

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)