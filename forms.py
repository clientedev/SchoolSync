from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, TextAreaField, SelectField, IntegerField, DateTimeField, HiddenField, PasswordField
from wtforms.validators import DataRequired, Email, Optional, Length, EqualTo

class TeacherForm(FlaskForm):
    name = StringField('Nome', validators=[DataRequired(), Length(max=100)])
    area = StringField('Área', validators=[DataRequired(), Length(max=100)])
    subjects = TextAreaField('Disciplinas (separadas por vírgula)', validators=[Optional()])
    workload = IntegerField('Carga Horária (horas/semana)', validators=[Optional()])
    email = StringField('Email', validators=[Optional(), Email(), Length(max=120)])
    phone = StringField('Telefone', validators=[Optional(), Length(max=20)])
    observations = TextAreaField('Observações', validators=[Optional()])

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
    
    period = SelectField('Período', choices=[
        ('Manhã', 'Manhã'),
        ('Tarde', 'Tarde'),
        ('Noite', 'Noite')
    ], validators=[DataRequired()])
    
    class_time = StringField('Horário da Aula', validators=[Optional()])
    
    # Planning section fields
    planning_schedule = SelectField('Elabora cronograma de aula, replaneja quando necessário', 
                                  choices=[('', '---'), ('Sim', 'Sim'), ('Não', 'Não'), ('Não se aplica', 'Não se aplica')])
    planning_lesson_plan = SelectField('Planeja a aula considerando estratégias de avaliação', 
                                     choices=[('', '---'), ('Sim', 'Sim'), ('Não', 'Não'), ('Não se aplica', 'Não se aplica')])
    planning_evaluation = SelectField('Planeja instrumentos de avaliação diversificados', 
                                    choices=[('', '---'), ('Sim', 'Sim'), ('Não', 'Não'), ('Não se aplica', 'Não se aplica')])
    planning_documents = SelectField('Conhece os documentos estruturantes', 
                                   choices=[('', '---'), ('Sim', 'Sim'), ('Não', 'Não'), ('Não se aplica', 'Não se aplica')])
    planning_diversified = SelectField('Utiliza instrumentos diversificados ao longo do período', 
                                     choices=[('', '---'), ('Sim', 'Sim'), ('Não', 'Não'), ('Não se aplica', 'Não se aplica')])
    planning_local_work = SelectField('Prepara previamente o local de trabalho', 
                                    choices=[('', '---'), ('Sim', 'Sim'), ('Não', 'Não'), ('Não se aplica', 'Não se aplica')])
    planning_tools = SelectField('Disponibiliza e acompanha a realização de atividades', 
                               choices=[('', '---'), ('Sim', 'Sim'), ('Não', 'Não'), ('Não se aplica', 'Não se aplica')])
    planning_educational_portal = SelectField('Portal Educacional', 
                                            choices=[('', '---'), ('Sim', 'Sim'), ('Não', 'Não'), ('Não se aplica', 'Não se aplica')])
    
    # Classroom section fields
    class_presentation = SelectField('Demonstra apresentação pessoal e postura adequadas', 
                                   choices=[('', '---'), ('Sim', 'Sim'), ('Não', 'Não'), ('Não se aplica', 'Não se aplica')])
    class_knowledge = SelectField('Demonstra conhecimento dos assuntos que ministra', 
                                choices=[('', '---'), ('Sim', 'Sim'), ('Não', 'Não'), ('Não se aplica', 'Não se aplica')])
    class_student_performance = SelectField('Acompanha o desempenho dos alunos', 
                                          choices=[('', '---'), ('Sim', 'Sim'), ('Não', 'Não'), ('Não se aplica', 'Não se aplica')])
    class_attendance = SelectField('Efetua registros de ocorrências', 
                                 choices=[('', '---'), ('Sim', 'Sim'), ('Não', 'Não'), ('Não se aplica', 'Não se aplica')])
    class_difficulties = SelectField('Realiza levantamento de dificuldades dos alunos', 
                                   choices=[('', '---'), ('Sim', 'Sim'), ('Não', 'Não'), ('Não se aplica', 'Não se aplica')])
    class_theoretical_practical = SelectField('Relaciona o aprendizado teórico e prático', 
                                            choices=[('', '---'), ('Sim', 'Sim'), ('Não', 'Não'), ('Não se aplica', 'Não se aplica')])
    class_previous_lesson = SelectField('Inicia a aula retomando a anterior', 
                                      choices=[('', '---'), ('Sim', 'Sim'), ('Não', 'Não'), ('Não se aplica', 'Não se aplica')])
    class_objectives = SelectField('Explicita objetivos e associados ao curso', 
                                 choices=[('', '---'), ('Sim', 'Sim'), ('Não', 'Não'), ('Não se aplica', 'Não se aplica')])
    class_questions = SelectField('Propõe questões previamente planejadas', 
                                choices=[('', '---'), ('Sim', 'Sim'), ('Não', 'Não'), ('Não se aplica', 'Não se aplica')])
    class_content_assimilation = SelectField('Verifica se o conteúdo está sendo assimilado', 
                                           choices=[('', '---'), ('Sim', 'Sim'), ('Não', 'Não'), ('Não se aplica', 'Não se aplica')])
    class_student_participation = SelectField('Estimula a participação dos alunos durante a aula', 
                                            choices=[('', '---'), ('Sim', 'Sim'), ('Não', 'Não'), ('Não se aplica', 'Não se aplica')])
    class_recovery_process = SelectField('Promove o processo de recuperação', 
                                       choices=[('', '---'), ('Sim', 'Sim'), ('Não', 'Não'), ('Não se aplica', 'Não se aplica')])
    class_school_pedagogy = SelectField('Pedagogia da escola', 
                                      choices=[('', '---'), ('Sim', 'Sim'), ('Não', 'Não'), ('Não se aplica', 'Não se aplica')])
    class_learning_exercises = SelectField('Aplica exercícios de forma a estimular o aprendizado', 
                                         choices=[('', '---'), ('Sim', 'Sim'), ('Não', 'Não'), ('Não se aplica', 'Não se aplica')])
    class_discipline = SelectField('Mantém a disciplina na sala de aula', 
                                 choices=[('', '---'), ('Sim', 'Sim'), ('Não', 'Não'), ('Não se aplica', 'Não se aplica')])
    class_educational_orientation = SelectField('Orientação Educacional', 
                                              choices=[('', '---'), ('Sim', 'Sim'), ('Não', 'Não'), ('Não se aplica', 'Não se aplica')])
    class_teaching_strategies = SelectField('Aplica estratégias de ensino pertinentes aos objetivos da aula', 
                                          choices=[('', '---'), ('Sim', 'Sim'), ('Não', 'Não'), ('Não se aplica', 'Não se aplica')])
    class_machines_equipment = SelectField('Orienta a utilização de máquinas, equipamentos e ferramentas', 
                                         choices=[('', '---'), ('Sim', 'Sim'), ('Não', 'Não'), ('Não se aplica', 'Não se aplica')])
    class_safety_procedures = SelectField('Cumpre e faz cumprir normas e procedimentos de segurança', 
                                        choices=[('', '---'), ('Sim', 'Sim'), ('Não', 'Não'), ('Não se aplica', 'Não se aplica')])
    
    # Observation fields
    planning_observations = TextAreaField('Observações - Planejamento')
    class_observations = TextAreaField('Observações - Período da Aula')
    general_observations = TextAreaField('Observações Gerais')
    
    # File upload
    attachments = FileField('Anexos (fotos, documentos)', 
                          validators=[FileAllowed(['jpg', 'png', 'pdf', 'doc', 'docx'], 
                                                'Apenas arquivos de imagem e documentos são permitidos!')])

class LoginForm(FlaskForm):
    username = StringField('Usuário', validators=[DataRequired()])
    password = PasswordField('Senha', validators=[DataRequired()])

class UserForm(FlaskForm):
    username = StringField('Nome de Usuário', validators=[DataRequired(), Length(min=3, max=80)])
    password = PasswordField('Senha', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirmar Senha', 
                                   validators=[DataRequired(), EqualTo('password', message='As senhas devem ser iguais')])
    name = StringField('Nome Completo', validators=[DataRequired(), Length(max=100)])
    role = SelectField('Função', choices=[('evaluator', 'Avaliador'), ('admin', 'Administrador')], validators=[DataRequired()])
    email = StringField('Email', validators=[Optional(), Email(), Length(max=120)])

class UserEditForm(FlaskForm):
    username = StringField('Nome de Usuário', validators=[DataRequired(), Length(min=3, max=80)])
    name = StringField('Nome Completo', validators=[DataRequired(), Length(max=100)])
    role = SelectField('Função', choices=[('evaluator', 'Avaliador'), ('admin', 'Administrador')], validators=[DataRequired()])
    email = StringField('Email', validators=[Optional(), Email(), Length(max=120)])
    is_active = SelectField('Status', choices=[('True', 'Ativo'), ('False', 'Inativo')], validators=[DataRequired()])

class ChangePasswordForm(FlaskForm):
    password = PasswordField('Nova Senha', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirmar Nova Senha', 
                                   validators=[DataRequired(), EqualTo('password', message='As senhas devem ser iguais')])
