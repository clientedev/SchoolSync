from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)
from datetime import datetime
from sqlalchemy import Text, Integer, String, DateTime, Boolean, ForeignKey, Float
from sqlalchemy.orm import relationship
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin

class User(db.Model, UserMixin):
    id = db.Column(Integer, primary_key=True)
    username = db.Column(String(80), unique=True, nullable=False)
    password_hash = db.Column(String(255), nullable=False)
    plain_password = db.Column(String(255), nullable=True)  # Store plain password for email notifications
    name = db.Column(String(100), nullable=False)
    role = db.Column(String(50), nullable=False, default='evaluator')  # 'admin', 'evaluator', or 'teacher'
    email = db.Column(String(120), nullable=True)
    is_active = db.Column(Boolean, default=True)  # type: ignore[override]
    created_at = db.Column(DateTime, default=datetime.utcnow)
    created_by = db.Column(Integer, ForeignKey('user.id'), nullable=True)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        self.plain_password = password  # Store plain password for email notifications
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def is_admin(self):
        return self.role == 'admin'
    
    def is_teacher(self):
        return self.role == 'teacher'
    
    def get_id(self):
        """Required method for Flask-Login"""
        return str(self.id)
    
    def __repr__(self):
        return f'<User {self.username}>'

class Teacher(db.Model):
    id = db.Column(Integer, primary_key=True)
    nif = db.Column(String(10), unique=True, nullable=False)  # NIF format: SN1234567
    name = db.Column(String(100), nullable=False)
    area = db.Column(String(100), nullable=False)
    user_id = db.Column(Integer, ForeignKey('user.id'), nullable=True)  # Linked user account
    created_at = db.Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    evaluations = relationship('Evaluation', back_populates='teacher')
    user = relationship('User', backref='teacher_profile')
    
    def __repr__(self):
        return f'<Teacher {self.name}>'

class Course(db.Model):
    id = db.Column(Integer, primary_key=True)
    name = db.Column(String(100), nullable=False)
    period = db.Column(String(20), nullable=False)  # e.g., "1° Sem/25"
    curriculum_component = db.Column(String(100), nullable=False)
    class_code = db.Column(String(20), nullable=True)
    created_at = db.Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    evaluations = relationship('Evaluation', back_populates='course')
    curricular_units = relationship('CurricularUnit', back_populates='course')
    
    def __repr__(self):
        return f'<Course {self.name}>'

class Evaluator(db.Model):
    id = db.Column(Integer, primary_key=True)
    name = db.Column(String(100), nullable=False)
    role = db.Column(String(50), nullable=False)  # e.g., "Coordinator", "Supervisor"
    email = db.Column(String(120), nullable=True)
    created_at = db.Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    evaluations = relationship('Evaluation', back_populates='evaluator')
    
    def __repr__(self):
        return f'<Evaluator {self.name}>'

class Evaluation(db.Model):
    id = db.Column(Integer, primary_key=True)
    teacher_id = db.Column(Integer, ForeignKey('teacher.id'), nullable=False)
    course_id = db.Column(Integer, ForeignKey('course.id'), nullable=False)
    evaluator_id = db.Column(Integer, ForeignKey('evaluator.id'), nullable=True)
    
    # Evaluation period info
    evaluation_date = db.Column(DateTime, default=datetime.utcnow)
    period = db.Column(String(20), nullable=False)  # e.g., "Manhã", "Tarde", "Noite"
    class_time = db.Column(String(20), nullable=True)
    
    # Planning aspects (Yes/No/Not Applicable)
    planning_schedule = db.Column(String(20), nullable=True)  # Elabora cronograma de aula
    planning_lesson_plan = db.Column(String(20), nullable=True)  # Planeja a aula
    planning_evaluation = db.Column(String(20), nullable=True)  # Planeja instrumentos de avaliação
    planning_documents = db.Column(String(20), nullable=True)  # Conhece documentos estruturantes
    planning_diversified = db.Column(String(20), nullable=True)  # Utiliza instrumentos diversificados
    planning_local_work = db.Column(String(20), nullable=True)  # Prepara previamente o local
    planning_tools = db.Column(String(20), nullable=True)  # Disponibiliza ferramentas
    planning_educational_portal = db.Column(String(20), nullable=True)  # Portal Educacional
    
    # Classroom aspects (Yes/No/Not Applicable)  
    class_presentation = db.Column(String(20), nullable=True)  # Apresentação pessoal
    class_knowledge = db.Column(String(20), nullable=True)  # Conhecimento dos assuntos
    class_student_performance = db.Column(String(20), nullable=True)  # Acompanha desempenho
    class_attendance = db.Column(String(20), nullable=True)  # Registra ocorrências
    class_difficulties = db.Column(String(20), nullable=True)  # Realiza levantamento de dificuldades
    class_theoretical_practical = db.Column(String(20), nullable=True)  # Aprendizado teórico e prático
    class_previous_lesson = db.Column(String(20), nullable=True)  # Retoma aula anterior
    class_objectives = db.Column(String(20), nullable=True)  # Explicita objetivos
    class_questions = db.Column(String(20), nullable=True)  # Propõe questões
    class_content_assimilation = db.Column(String(20), nullable=True)  # Verifica assimilação
    class_student_participation = db.Column(String(20), nullable=True)  # Estimula participação
    class_recovery_process = db.Column(String(20), nullable=True)  # Processo de recuperação
    class_school_pedagogy = db.Column(String(20), nullable=True)  # Pedagogia da escola
    class_learning_exercises = db.Column(String(20), nullable=True)  # Exercícios para estimular
    class_discipline = db.Column(String(20), nullable=True)  # Mantém disciplina
    class_educational_orientation = db.Column(String(20), nullable=True)  # Orientação Educacional
    class_teaching_strategies = db.Column(String(20), nullable=True)  # Estratégias de ensino
    class_machines_equipment = db.Column(String(20), nullable=True)  # Orienta utilização
    class_safety_procedures = db.Column(String(20), nullable=True)  # Cumpre procedimentos de segurança
    
    # Text observations
    planning_observations = db.Column(Text, nullable=True)
    class_observations = db.Column(Text, nullable=True)
    general_observations = db.Column(Text, nullable=True)
    
    # Signatures and completion
    teacher_signature_date = db.Column(DateTime, nullable=True)
    evaluator_signature_date = db.Column(DateTime, nullable=True)
    is_completed = db.Column(Boolean, default=False)
    
    # New fields for enhanced functionality
    semester_id = db.Column(Integer, ForeignKey('semester.id'), nullable=True)
    curricular_unit_id = db.Column(Integer, ForeignKey('curricular_unit.id'), nullable=True)
    scheduled_evaluation_id = db.Column(Integer, ForeignKey('scheduled_evaluation.id'), nullable=True)
    teacher_signed = db.Column(Boolean, default=False)
    evaluator_signed = db.Column(Boolean, default=False)
    
    created_at = db.Column(DateTime, default=datetime.utcnow)
    updated_at = db.Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    teacher = relationship('Teacher', back_populates='evaluations')
    course = relationship('Course', back_populates='evaluations')
    evaluator = relationship('Evaluator', back_populates='evaluations')
    attachments = relationship('EvaluationAttachment', back_populates='evaluation', cascade='all, delete-orphan')
    semester = relationship('Semester', back_populates='evaluations')
    curricular_unit = relationship('CurricularUnit', back_populates='evaluations')
    scheduled_evaluation = relationship('ScheduledEvaluation', back_populates='evaluation')
    signatures = relationship('DigitalSignature', back_populates='evaluation', cascade='all, delete-orphan')
    checklist_items = relationship('EvaluationChecklistItem', back_populates='evaluation', cascade='all, delete-orphan', lazy='selectin', order_by='EvaluationChecklistItem.display_order')
    
    def calculate_planning_percentage(self):
        """Calculate percentage of 'Sim' responses in planning section"""
        # Try to use dynamic checklist items first (check if list has items, not just truthy)
        planning_items = [item for item in self.checklist_items if item.category == 'planning'] if self.checklist_items and len(self.checklist_items) > 0 else []
        
        if planning_items:
            # Use dynamic checklist items
            values = [item.value for item in planning_items]
            total_applicable = len([v for v in values if v and v != 'Não se aplica'])
            if total_applicable == 0:
                return 0
            yes_count = len([v for v in values if v == 'Sim'])
            return round((yes_count / total_applicable) * 100, 1)
        
        # Fallback to column-based fields for backwards compatibility
        planning_fields = [
            self.planning_schedule, self.planning_lesson_plan, self.planning_evaluation,
            self.planning_documents, self.planning_diversified, self.planning_local_work,
            self.planning_tools, self.planning_educational_portal
        ]
        
        total_applicable = len([f for f in planning_fields if f and f != 'Não se aplica'])
        if total_applicable == 0:
            return 0
        
        yes_count = len([f for f in planning_fields if f == 'Sim'])
        return round((yes_count / total_applicable) * 100, 1)
    
    def calculate_class_percentage(self):
        """Calculate percentage of 'Sim' responses in classroom section"""
        # Try to use dynamic checklist items first (check if list has items, not just truthy)
        class_items = [item for item in self.checklist_items if item.category == 'class'] if self.checklist_items and len(self.checklist_items) > 0 else []
        
        if class_items:
            # Use dynamic checklist items
            values = [item.value for item in class_items]
            total_applicable = len([v for v in values if v and v != 'Não se aplica'])
            if total_applicable == 0:
                return 0
            yes_count = len([v for v in values if v == 'Sim'])
            return round((yes_count / total_applicable) * 100, 1)
        
        # Fallback to column-based fields for backwards compatibility
        class_fields = [
            self.class_presentation, self.class_knowledge, self.class_student_performance,
            self.class_attendance, self.class_difficulties, self.class_theoretical_practical,
            self.class_previous_lesson, self.class_objectives, self.class_questions,
            self.class_content_assimilation, self.class_student_participation,
            self.class_recovery_process, self.class_school_pedagogy, self.class_learning_exercises,
            self.class_discipline, self.class_educational_orientation, self.class_teaching_strategies,
            self.class_machines_equipment, self.class_safety_procedures
        ]
        
        total_applicable = len([f for f in class_fields if f and f != 'Não se aplica'])
        if total_applicable == 0:
            return 0
        
        yes_count = len([f for f in class_fields if f == 'Sim'])
        return round((yes_count / total_applicable) * 100, 1)
    
    def __repr__(self):
        return f'<Evaluation {self.teacher.name} - {self.evaluation_date}>'

class EvaluationAttachment(db.Model):
    id = db.Column(Integer, primary_key=True)
    evaluation_id = db.Column(Integer, ForeignKey('evaluation.id'), nullable=False)
    filename = db.Column(String(255), nullable=False)
    original_filename = db.Column(String(255), nullable=False)
    file_path = db.Column(String(500), nullable=False)
    file_size = db.Column(Integer, nullable=True)
    mime_type = db.Column(String(100), nullable=True)
    uploaded_at = db.Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    evaluation = relationship('Evaluation', back_populates='attachments')
    
    def __repr__(self):
        return f'<EvaluationAttachment {self.original_filename}>'

# New models for enhanced functionality
class Semester(db.Model):
    id = db.Column(Integer, primary_key=True)
    name = db.Column(String(50), nullable=False)  # e.g., "2025.1", "2025.2"
    year = db.Column(Integer, nullable=False)
    number = db.Column(Integer, nullable=False)  # 1 or 2
    start_date = db.Column(DateTime, nullable=False)
    end_date = db.Column(DateTime, nullable=False)
    is_active = db.Column(Boolean, default=False)
    created_at = db.Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    scheduled_evaluations = relationship('ScheduledEvaluation', back_populates='semester')
    evaluations = relationship('Evaluation', back_populates='semester')
    
    def __repr__(self):
        return f'<Semester {self.name}>'

class CurricularUnit(db.Model):
    id = db.Column(Integer, primary_key=True)
    name = db.Column(String(150), nullable=False)
    code = db.Column(String(20), nullable=True)
    course_id = db.Column(Integer, ForeignKey('course.id'), nullable=False)
    workload = db.Column(Integer, nullable=True)  # Hours
    description = db.Column(Text, nullable=True)
    is_active = db.Column(Boolean, default=True)
    created_at = db.Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    course = relationship('Course', back_populates='curricular_units')
    evaluations = relationship('Evaluation', back_populates='curricular_unit')
    
    def __repr__(self):
        return f'<CurricularUnit {self.name}>'

class ScheduledEvaluation(db.Model):
    id = db.Column(Integer, primary_key=True)
    teacher_id = db.Column(Integer, ForeignKey('teacher.id'), nullable=False)
    curricular_unit_id = db.Column(Integer, ForeignKey('curricular_unit.id'), nullable=False)
    semester_id = db.Column(Integer, ForeignKey('semester.id'), nullable=False)
    scheduled_month = db.Column(Integer, nullable=False)  # 1-12
    scheduled_year = db.Column(Integer, nullable=False)
    scheduled_date = db.Column(DateTime, nullable=True)  # Specific date if set
    is_completed = db.Column(Boolean, default=False)
    completed_at = db.Column(DateTime, nullable=True)
    notes = db.Column(Text, nullable=True)
    created_at = db.Column(DateTime, default=datetime.utcnow)
    created_by = db.Column(Integer, ForeignKey('user.id'), nullable=False)
    
    # Relationships
    teacher = relationship('Teacher')
    curricular_unit = relationship('CurricularUnit')
    semester = relationship('Semester', back_populates='scheduled_evaluations')
    creator = relationship('User')
    evaluation = relationship('Evaluation', back_populates='scheduled_evaluation', uselist=False)
    
    def __repr__(self):
        return f'<ScheduledEvaluation {self.teacher.name} - {self.scheduled_month}/{self.scheduled_year}>'

class DigitalSignature(db.Model):
    id = db.Column(Integer, primary_key=True)
    evaluation_id = db.Column(Integer, ForeignKey('evaluation.id'), nullable=False)
    user_id = db.Column(Integer, ForeignKey('user.id'), nullable=False)
    signature_data = db.Column(Text, nullable=False)  # Base64 encoded signature image
    signature_type = db.Column(String(20), nullable=False)  # 'teacher' or 'evaluator'
    signed_at = db.Column(DateTime, default=datetime.utcnow)
    ip_address = db.Column(String(45), nullable=True)
    
    # Relationships
    evaluation = relationship('Evaluation', back_populates='signatures')
    user = relationship('User')
    
    def __repr__(self):
        return f'<DigitalSignature {self.user.name} - {self.signature_type}>'

class TemporaryCredential(db.Model):
    """Secure token-based storage for temporary teacher credentials"""
    id = db.Column(Integer, primary_key=True)
    token = db.Column(String(64), unique=True, nullable=False, index=True)
    teacher_id = db.Column(Integer, ForeignKey('teacher.id'), nullable=False)
    user_id = db.Column(Integer, ForeignKey('user.id'), nullable=False)
    encrypted_password = db.Column(String(255), nullable=False)  # Encrypted password
    created_at = db.Column(DateTime, default=datetime.utcnow)
    expires_at = db.Column(DateTime, nullable=False)
    is_used = db.Column(Boolean, default=False)
    created_by = db.Column(Integer, ForeignKey('user.id'), nullable=False)
    
    # Relationships
    teacher = relationship('Teacher')
    user = relationship('User', foreign_keys=[user_id])
    creator = relationship('User', foreign_keys=[created_by])
    
    def is_expired(self):
        """Check if the token has expired"""
        return datetime.utcnow() > self.expires_at
    
    def is_valid(self):
        """Check if token is valid (not used and not expired)"""
        return not self.is_used and not self.is_expired()
    
    def mark_as_used(self):
        """Mark token as used"""
        self.is_used = True
        db.session.commit()
    
    def __repr__(self):
        return f'<TemporaryCredential {self.teacher.name} - {self.token[:8]}...>'


class EvaluationChecklistItem(db.Model):
    """Dynamic checklist items for evaluations - supports both default and custom items"""
    id = db.Column(Integer, primary_key=True)
    evaluation_id = db.Column(Integer, ForeignKey('evaluation.id'), nullable=False)
    label = db.Column(Text, nullable=False)
    category = db.Column(String(50), nullable=False)  # 'planning' or 'class'
    is_default = db.Column(Boolean, default=False)  # True for system default items that cannot be deleted
    value = db.Column(String(20), nullable=True)  # 'Sim', 'Não', 'Não se aplica', or None
    display_order = db.Column(Integer, default=0)
    created_at = db.Column(DateTime, default=datetime.utcnow)
    updated_at = db.Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    evaluation = relationship('Evaluation', back_populates='checklist_items')
    
    def __repr__(self):
        return f'<EvaluationChecklistItem {self.label[:30]}... - {self.value}>'


# Default checklist items - these are always created for new evaluations
DEFAULT_CHECKLIST_ITEMS = {
    'planning': [
        "Elabora cronograma de aula, replaneja quando necessário",
        "Planeja a aula considerando estratégias de avaliação pertinentes aos objetivos da aula em conformidade com os documentos estruturantes (MSEP e Plano de Curso)",
        "Planeja instrumentos de avaliação diversificados ao longo do período letivo",
        "Conhece os documentos estruturantes (MSEP e Plano de Curso)",
        "Utiliza instrumentos diversificados ao longo do período letivo",
        "Prepara previamente o local de trabalho, máquinas, equipamentos e ferramentas",
        "Disponibiliza e acompanha a realização de atividades pertinentes no Portal Educacional",
    ],
    'class': [
        "Demonstra apresentação pessoal e postura adequadas",
        "Demonstra conhecimento dos assuntos que ministra",
        "Acompanha o desempenho dos alunos e realiza os registros de ocorrências, quando necessário",
        "Efetua registros de ocorrências, quando necessário",
        "Realiza levantamento de dificuldades dos alunos quanto ao aprendizado teórico e prático, alinhado com SAEP",
        "Relaciona o aprendizado teórico e prático, alinhado com SAEP",
        "Inicia a aula retomando a anterior, explicitando objetivos e associando-os ao projeto do curso",
        "Explicita objetivos e associa-os ao projeto do curso",
        "Propõe questões, previamente planejadas, que permite verificar se o conteúdo ministrado está sendo assimilado",
        "Verifica se o conteúdo ministrado está sendo assimilado",
        "Estimula a participação dos alunos durante a aula",
        "Promove o processo de recuperação, atendendo à Proposta Pedagógica da escola",
        "Aplica exercícios de forma a estimular o aprendizado",
        "Mantém a disciplina na sala de aula, encaminhando ocorrências à Orientação Educacional",
        "Aplica estratégias de ensino pertinentes aos objetivos da aula",
        "Orienta a utilização de máquinas, equipamentos e ferramentas durante a aula",
        "Cumpre e faz cumprir normas e procedimentos de segurança e uso dos EPI's/EPC's",
    ]
}


def create_default_checklist_items(evaluation_id):
    """Create default checklist items for a new evaluation"""
    items = []
    
    # Planning items
    for order, label in enumerate(DEFAULT_CHECKLIST_ITEMS['planning']):
        item = EvaluationChecklistItem()
        item.evaluation_id = evaluation_id
        item.label = label
        item.category = 'planning'
        item.is_default = True
        item.display_order = order
        items.append(item)
    
    # Class items
    for order, label in enumerate(DEFAULT_CHECKLIST_ITEMS['class']):
        item = EvaluationChecklistItem()
        item.evaluation_id = evaluation_id
        item.label = label
        item.category = 'class'
        item.is_default = True
        item.display_order = order
        items.append(item)
    
    return items
