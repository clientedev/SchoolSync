from app import db
from datetime import datetime
from sqlalchemy import Text, Integer, String, DateTime, Boolean, ForeignKey, Float
from sqlalchemy.orm import relationship

class Teacher(db.Model):
    id = db.Column(Integer, primary_key=True)
    name = db.Column(String(100), nullable=False)
    area = db.Column(String(100), nullable=False)
    subjects = db.Column(Text, nullable=True)  # Comma-separated subjects
    workload = db.Column(Integer, nullable=True)  # Hours per week
    email = db.Column(String(120), nullable=True)
    phone = db.Column(String(20), nullable=True)
    created_at = db.Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    evaluations = relationship('Evaluation', back_populates='teacher')
    
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
    evaluator_id = db.Column(Integer, ForeignKey('evaluator.id'), nullable=False)
    
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
    
    created_at = db.Column(DateTime, default=datetime.utcnow)
    updated_at = db.Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    teacher = relationship('Teacher', back_populates='evaluations')
    course = relationship('Course', back_populates='evaluations')
    evaluator = relationship('Evaluator', back_populates='evaluations')
    attachments = relationship('EvaluationAttachment', back_populates='evaluation', cascade='all, delete-orphan')
    
    def calculate_planning_percentage(self):
        """Calculate percentage of 'Sim' responses in planning section"""
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
