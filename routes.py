import os
from flask import render_template, request, redirect, url_for, flash, jsonify, send_file, current_app, session
from flask_login import login_user, logout_user, login_required, current_user
from datetime import datetime, timedelta
from app import app, db
from models import Teacher, Course, Evaluator, Evaluation, EvaluationAttachment, User, Semester, CurricularUnit, ScheduledEvaluation, DigitalSignature
from forms import TeacherForm, CourseForm, EvaluatorForm, EvaluationForm, LoginForm, UserForm, UserEditForm, ChangePasswordForm
from utils import save_uploaded_file, send_evaluation_email, generate_evaluation_report, generate_consolidated_report, generate_teachers_excel_template, process_teachers_excel_import, generate_courses_excel_template, process_courses_excel_import, generate_curricular_units_excel_template, process_curricular_units_excel_import, get_or_create_current_semester

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page"""
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data) and user.is_active:
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('index'))
        else:
            flash('Usuário ou senha inválidos.', 'error')
    
    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    """Logout user"""
    logout_user()
    flash('Você foi desconectado com sucesso.', 'info')
    return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    """Dashboard - Main page"""
    # Get or create current semester based on current date
    current_semester = get_or_create_current_semester()
    
    # Get statistics
    total_teachers = Teacher.query.count()
    total_evaluations = Evaluation.query.count()
    total_courses = Course.query.count()
    
    # Semester-based statistics
    semester_scheduled = 0
    semester_completed = 0
    semester_pending = 0
    pending_alerts = []
    overdue_alerts = []
    
    if current_semester:
        # Scheduled evaluations for the semester
        scheduled_evaluations = ScheduledEvaluation.query.filter_by(
            semester_id=current_semester.id
        ).all()
        
        semester_scheduled = len(scheduled_evaluations)
        semester_completed = len([se for se in scheduled_evaluations if se.is_completed])
        semester_pending = semester_scheduled - semester_completed
        
        # Alerts: scheduled evaluations for current and past months that are not completed
        current_month = datetime.now().month
        current_year = datetime.now().year
        
        for scheduled in scheduled_evaluations:
            if not scheduled.is_completed:
                # Check if it's for current/past months
                if (scheduled.scheduled_year < current_year or 
                    (scheduled.scheduled_year == current_year and scheduled.scheduled_month <= current_month)):
                    
                    if scheduled.scheduled_month == current_month:
                        pending_alerts.append(scheduled)
                    else:
                        overdue_alerts.append(scheduled)
    
    # Recent evaluations (completed)
    recent_evaluations = Evaluation.query.filter_by(is_completed=True).order_by(
        Evaluation.evaluation_date.desc()
    ).limit(5).all()
    
    # Teachers without evaluations (not scheduled or no completed evaluations this semester)
    teachers_without_evaluation = []
    if current_semester:
        all_teachers = Teacher.query.all()
        for teacher in all_teachers:
            # Check if teacher has any scheduled evaluation for this semester
            has_scheduled = ScheduledEvaluation.query.filter_by(
                teacher_id=teacher.id,
                semester_id=current_semester.id
            ).first()
            
            if not has_scheduled:
                teachers_without_evaluation.append(teacher)
    
    # Average scores (only completed evaluations)
    completed_evaluations = Evaluation.query.filter_by(is_completed=True).all()
    avg_planning = 0
    avg_class = 0
    
    if completed_evaluations:
        avg_planning = sum(eval.calculate_planning_percentage() for eval in completed_evaluations) / len(completed_evaluations)
        avg_class = sum(eval.calculate_class_percentage() for eval in completed_evaluations) / len(completed_evaluations)
    
    # Create monthly scheduling dashboard data
    monthly_schedule_summary = {}
    current_year = datetime.now().year
    month_names = [
        'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
        'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'
    ]
    
    # Initialize all months
    for i in range(1, 13):
        monthly_schedule_summary[i] = {
            'name': month_names[i-1],
            'scheduled': 0,
            'completed': 0,
            'teachers': []
        }
    
    # Get scheduled evaluations for current semester
    if current_semester:
        scheduled_evaluations = ScheduledEvaluation.query.filter_by(
            semester_id=current_semester.id
        ).all()
        
        for scheduled in scheduled_evaluations:
            month = scheduled.scheduled_month
            if month in monthly_schedule_summary:
                monthly_schedule_summary[month]['scheduled'] += 1
                if scheduled.is_completed:
                    monthly_schedule_summary[month]['completed'] += 1
                
                # Add teacher info
                teacher_info = {
                    'name': scheduled.teacher.name,
                    'curricular_unit': scheduled.curricular_unit.name,
                    'is_completed': scheduled.is_completed,
                    'scheduled_date': scheduled.scheduled_date.strftime('%d/%m') if scheduled.scheduled_date else None
                }
                monthly_schedule_summary[month]['teachers'].append(teacher_info)
    
    return render_template('index.html',
                         total_teachers=total_teachers,
                         total_evaluations=total_evaluations,
                         total_courses=total_courses,
                         current_semester=current_semester,
                         semester_scheduled=semester_scheduled,
                         semester_completed=semester_completed,
                         semester_pending=semester_pending,
                         recent_evaluations=recent_evaluations,
                         teachers_without_evaluation=teachers_without_evaluation,
                         pending_alerts=pending_alerts,
                         overdue_alerts=overdue_alerts,
                         avg_planning=round(avg_planning, 1),
                         avg_class=round(avg_class, 1),
                         monthly_schedule_summary=monthly_schedule_summary)

@app.route('/api/monthly-schedule/<int:month>')
@login_required
def get_monthly_schedule(month):
    """Get detailed schedule for a specific month"""
    current_semester = get_or_create_current_semester()
    
    # Get scheduled evaluations for the specified month
    scheduled_evaluations = ScheduledEvaluation.query.filter_by(
        semester_id=current_semester.id,
        scheduled_month=month
    ).all()
    
    teachers_data = []
    for scheduled in scheduled_evaluations:
        teacher_data = {
            'id': scheduled.id,
            'teacher_name': scheduled.teacher.name,
            'curricular_unit': scheduled.curricular_unit.name,
            'course': scheduled.curricular_unit.course.name,
            'is_completed': scheduled.is_completed,
            'scheduled_date': scheduled.scheduled_date.strftime('%d/%m/%Y') if scheduled.scheduled_date else 'Não definida',
            'notes': scheduled.notes or '',
            'completed_at': scheduled.completed_at.strftime('%d/%m/%Y') if scheduled.completed_at else None
        }
        teachers_data.append(teacher_data)
    
    month_names = [
        'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
        'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'
    ]
    
    return jsonify({
        'month': month,
        'month_name': month_names[month-1] if 1 <= month <= 12 else 'Mês inválido',
        'semester': current_semester.name,
        'teachers': teachers_data,
        'total_scheduled': len(teachers_data),
        'total_completed': len([t for t in teachers_data if t['is_completed']])
    })

@app.route('/users')
@login_required
def users():
    """List all users (admin only)"""
    if not current_user.is_admin():
        flash('Acesso negado. Apenas administradores podem gerenciar usuários.', 'error')
        return redirect(url_for('index'))
    
    users_list = User.query.all()
    return render_template('users.html', users=users_list)

@app.route('/users/add', methods=['GET', 'POST'])
@login_required
def add_user():
    """Add new user (admin only)"""
    if not current_user.is_admin():
        flash('Acesso negado. Apenas administradores podem criar usuários.', 'error')
        return redirect(url_for('index'))
    
    form = UserForm()
    
    if form.validate_on_submit():
        # Check if username already exists
        existing_user = User.query.filter_by(username=form.username.data).first()
        if existing_user:
            flash('Nome de usuário já existe. Escolha outro.', 'error')
            return render_template('users.html', form=form, users=User.query.all())
        
        user = User()  # type: ignore
        user.username = form.username.data
        user.name = form.name.data
        user.role = form.role.data
        user.email = form.email.data
        user.created_by = current_user.id
        user.set_password(form.password.data)
        
        db.session.add(user)
        db.session.commit()
        
        flash(f'Usuário {user.name} criado com sucesso!', 'success')
        return redirect(url_for('users'))
    
    return render_template('users.html', form=form, users=User.query.all())

@app.route('/users/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_user(id):
    """Edit user (admin only)"""
    if not current_user.is_admin():
        flash('Acesso negado. Apenas administradores podem editar usuários.', 'error')
        return redirect(url_for('index'))
    
    user = User.query.get_or_404(id)
    form = UserEditForm(obj=user)
    
    if form.validate_on_submit():
        # Check if username already exists (excluding current user)
        existing_user = User.query.filter(User.username == form.username.data, User.id != user.id).first()
        if existing_user:
            flash('Nome de usuário já existe. Escolha outro.', 'error')
            return render_template('users.html', form=form, user=user, users=User.query.all())
        
        user.username = form.username.data
        user.name = form.name.data
        user.role = form.role.data
        user.email = form.email.data
        user.is_active = form.is_active.data == 'True'
        
        db.session.commit()
        
        flash(f'Usuário {user.name} atualizado com sucesso!', 'success')
        return redirect(url_for('users'))
    
    return render_template('users.html', form=form, user=user, users=User.query.all())

@app.route('/users/change-password/<int:id>', methods=['GET', 'POST'])
@login_required
def change_user_password(id):
    """Change user password (admin only or own password)"""
    user = User.query.get_or_404(id)
    
    # Admin can change any password, user can only change their own
    if not (current_user.is_admin() or current_user.id == user.id):
        flash('Acesso negado.', 'error')
        return redirect(url_for('index'))
    
    form = ChangePasswordForm()
    
    if form.validate_on_submit():
        user.set_password(form.password.data)
        db.session.commit()
        
        flash('Senha alterada com sucesso!', 'success')
        if current_user.is_admin():
            return redirect(url_for('users'))
        else:
            return redirect(url_for('index'))
    
    return render_template('change_password.html', form=form, user=user)

@app.route('/teachers')
@login_required
def teachers():
    """List all teachers"""
    teachers_list = Teacher.query.all()
    form = TeacherForm()  # Always provide form for modal
    return render_template('teachers.html', teachers=teachers_list, form=form)

@app.route('/teachers/add', methods=['GET', 'POST'])
@login_required
def add_teacher():
    """Add new teacher"""
    form = TeacherForm()
    
    if form.validate_on_submit():
        teacher = Teacher()  # type: ignore
        teacher.name = form.name.data
        teacher.area = form.area.data
        teacher.subjects = form.subjects.data
        teacher.workload = form.workload.data
        teacher.email = form.email.data
        teacher.phone = form.phone.data
        teacher.observations = form.observations.data
        
        # Create user account automatically for teacher
        teacher_user = User()  # type: ignore
        
        # Generate username from email or name
        if form.email.data:
            username = form.email.data.split('@')[0].lower().replace('.', '_').replace('-', '_')
        else:
            # Create username from name
            name_parts = (form.name.data or '').lower().split()
            if len(name_parts) >= 2:
                username = f"{name_parts[0]}.{name_parts[-1]}"
            else:
                username = name_parts[0] if name_parts else 'docente'
        
        # Ensure username is unique
        base_username = username
        counter = 1
        while User.query.filter_by(username=username).first():
            username = f"{base_username}_{counter}"
            counter += 1
        
        teacher_user.username = username
        teacher_user.name = form.name.data
        teacher_user.role = 'teacher'
        teacher_user.email = form.email.data
        teacher_user.created_by = current_user.id
        
        # Generate secure password (teacher can change later)
        import secrets
        import string
        password_chars = string.ascii_letters + string.digits
        password = ''.join(secrets.choice(password_chars) for _ in range(10))
        teacher_user.set_password(password)
        
        db.session.add(teacher_user)
        db.session.flush()  # Get user ID
        
        teacher.user_id = teacher_user.id
        db.session.add(teacher)
        db.session.commit()
        
        # Store password for display (in a real system, you might want to email this)
        session['new_teacher_credentials'] = {
            'name': teacher.name,
            'username': username,
            'password': password
        }
        
        flash(f'Professor {teacher.name} cadastrado com sucesso! Conta criada.', 'success')
        return redirect(url_for('show_teacher_credentials'))
    
    return render_template('teachers.html', form=form, teachers=Teacher.query.all())

@app.route('/teacher_credentials')
@login_required
def show_teacher_credentials():
    """Show new teacher credentials"""
    if not current_user.is_admin():
        flash('Acesso negado.', 'error')
        return redirect(url_for('index'))
    
    credentials = session.pop('new_teacher_credentials', None)
    if not credentials:
        flash('Nenhuma credencial de docente disponível.', 'warning')
        return redirect(url_for('teachers'))
    
    return render_template('teacher_credentials.html', credentials=credentials)

@app.route('/manage_accounts')
@login_required
def manage_accounts():
    """Manage teacher accounts - Admin only"""
    if not current_user.is_admin():
        flash('Acesso negado. Apenas administradores podem gerenciar contas.', 'error')
        return redirect(url_for('index'))
    
    # Get all teacher accounts
    teacher_users = User.query.filter_by(role='teacher').order_by(User.name).all()
    
    # Get teachers without accounts
    teachers_without_accounts = Teacher.query.filter(Teacher.user_id.is_(None)).all()
    
    return render_template('manage_accounts.html', 
                         teacher_users=teacher_users,
                         teachers_without_accounts=teachers_without_accounts)

@app.route('/reset_teacher_password/<int:user_id>', methods=['POST'])
@login_required
def reset_teacher_password(user_id):
    """Reset teacher password - Admin only"""
    if not current_user.is_admin():
        return jsonify({'success': False, 'error': 'Acesso negado'})
    
    user = User.query.get_or_404(user_id)
    if user.role != 'teacher':
        return jsonify({'success': False, 'error': 'Usuário não é professor'})
    
    # Generate new password
    import secrets
    import string
    password_chars = string.ascii_letters + string.digits
    new_password = ''.join(secrets.choice(password_chars) for _ in range(10))
    
    user.set_password(new_password)
    db.session.commit()
    
    return jsonify({
        'success': True, 
        'message': 'Senha redefinida com sucesso',
        'new_password': new_password
    })

@app.route('/toggle_teacher_account/<int:user_id>', methods=['POST'])
@login_required
def toggle_teacher_account(user_id):
    """Activate/deactivate teacher account - Admin only"""
    if not current_user.is_admin():
        return jsonify({'success': False, 'error': 'Acesso negado'})
    
    user = User.query.get_or_404(user_id)
    if user.role != 'teacher':
        return jsonify({'success': False, 'error': 'Usuário não é professor'})
    
    user.is_active = not user.is_active
    db.session.commit()
    
    status = 'ativada' if user.is_active else 'desativada'
    return jsonify({
        'success': True, 
        'message': f'Conta {status} com sucesso',
        'is_active': user.is_active
    })

@app.route('/create_account_for_teacher/<int:teacher_id>', methods=['POST'])
@login_required
def create_account_for_teacher(teacher_id):
    """Create account for existing teacher without account - Admin only"""
    if not current_user.is_admin():
        return jsonify({'success': False, 'error': 'Acesso negado'})
    
    teacher = Teacher.query.get_or_404(teacher_id)
    if teacher.user_id:
        return jsonify({'success': False, 'error': 'Professor já possui conta'})
    
    # Create user account
    teacher_user = User()
    
    # Generate username from email or name
    if teacher.email:
        username = teacher.email.split('@')[0].lower().replace('.', '_').replace('-', '_')
    else:
        # Create username from name
        name_parts = (teacher.name or '').lower().split()
        if len(name_parts) >= 2:
            username = f"{name_parts[0]}.{name_parts[-1]}"
        else:
            username = name_parts[0] if name_parts else 'docente'
    
    # Ensure username is unique
    base_username = username
    counter = 1
    while User.query.filter_by(username=username).first():
        username = f"{base_username}_{counter}"
        counter += 1
    
    teacher_user.username = username
    teacher_user.name = teacher.name
    teacher_user.role = 'teacher'
    teacher_user.email = teacher.email
    teacher_user.created_by = current_user.id
    
    # Generate secure password
    import secrets
    import string
    password_chars = string.ascii_letters + string.digits
    password = ''.join(secrets.choice(password_chars) for _ in range(10))
    teacher_user.set_password(password)
    
    db.session.add(teacher_user)
    db.session.flush()  # Get user ID
    
    teacher.user_id = teacher_user.id
    db.session.commit()
    
    return jsonify({
        'success': True, 
        'message': 'Conta criada com sucesso',
        'username': username,
        'password': password
    })

@app.route('/teachers/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_teacher(id):
    """Edit teacher"""
    teacher = Teacher.query.get_or_404(id)
    form = TeacherForm(obj=teacher)
    
    if form.validate_on_submit():
        form.populate_obj(teacher)
        db.session.commit()
        
        flash(f'Professor {teacher.name} atualizado com sucesso!', 'success')
        return redirect(url_for('teachers'))
    
    return render_template('teachers.html', form=form, teacher=teacher, teachers=Teacher.query.all())

@app.route('/teachers/delete/<int:id>')
@login_required
def delete_teacher(id):
    """Delete teacher"""
    teacher = Teacher.query.get_or_404(id)
    
    try:
        db.session.delete(teacher)
        db.session.commit()
        flash(f'Professor {teacher.name} excluído com sucesso!', 'success')
    except Exception as e:
        flash('Erro ao excluir professor. Verifique se não existem avaliações vinculadas.', 'error')
        db.session.rollback()
    
    return redirect(url_for('teachers'))

@app.route('/teachers/template')
@login_required
def download_teachers_template():
    """Download Excel template for teacher import"""
    try:
        template_buffer = generate_teachers_excel_template()
        return send_file(
            template_buffer,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name='modelo_importacao_docentes.xlsx'
        )
    except Exception as e:
        flash(f'Erro ao gerar modelo: {str(e)}', 'error')
        return redirect(url_for('teachers'))

@app.route('/teachers/import', methods=['POST'])
@login_required
def import_teachers_excel():
    """Import teachers from Excel file"""
    if 'excel_file' not in request.files:
        flash('Nenhum arquivo selecionado.', 'error')
        return redirect(url_for('teachers'))
    
    file = request.files['excel_file']
    if file.filename == '':
        flash('Nenhum arquivo selecionado.', 'error')
        return redirect(url_for('teachers'))
    
    if not file.filename or not file.filename.lower().endswith(('.xlsx', '.xls')):
        flash('Por favor, selecione um arquivo Excel (.xlsx ou .xls).', 'error')
        return redirect(url_for('teachers'))
    
    try:
        # Save uploaded file temporarily
        file_info = save_uploaded_file(file)
        if not file_info:
            flash('Erro ao salvar arquivo temporário.', 'error')
            return redirect(url_for('teachers'))
        
        # Process the Excel file
        results = process_teachers_excel_import(file_info['file_path'])
        
        # Clean up temporary file
        try:
            os.remove(file_info['file_path'])
        except:
            pass
        
        # Show results
        if results['success'] > 0:
            flash(f'Importação concluída! {results["success"]} docente(s) importado(s) com sucesso.', 'success')
        
        if results['warnings']:
            for warning in results['warnings'][:5]:  # Show first 5 warnings
                flash(warning, 'warning')
            if len(results['warnings']) > 5:
                flash(f'... e mais {len(results["warnings"]) - 5} avisos.', 'warning')
        
        if results['errors']:
            for error in results['errors'][:5]:  # Show first 5 errors
                flash(error, 'error')
            if len(results['errors']) > 5:
                flash(f'... e mais {len(results["errors"]) - 5} erros.', 'error')
        
        if results['success'] == 0 and results['errors']:
            flash('Nenhum docente foi importado devido aos erros encontrados.', 'error')
        
    except Exception as e:
        flash(f'Erro ao processar arquivo Excel: {str(e)}', 'error')
        current_app.logger.error(f"Excel import error: {str(e)}")
    
    return redirect(url_for('teachers'))

@app.route('/courses')
@login_required
def courses():
    """List all courses"""
    courses_list = Course.query.all()
    form = CourseForm()
    return render_template('courses.html', courses=courses_list, form=form)

@app.route('/courses/add', methods=['GET', 'POST'])
@login_required
def add_course():
    """Add new course"""
    form = CourseForm()
    
    if request.method == 'POST':
        # Check basic form validation
        if form.validate_on_submit():
            course = Course()  # type: ignore
            course.name = form.name.data
            course.period = form.period.data
            course.curriculum_component = form.curriculum_component.data
            course.class_code = form.class_code.data
            
            db.session.add(course)
            db.session.flush()  # Get course ID
            
            # Process curricular units
            curricular_units = request.form.getlist('curricular_units[]')
            curricular_units = [unit.strip() for unit in curricular_units if unit.strip()]
            
            if not curricular_units:
                flash('Pelo menos uma unidade curricular é obrigatória.', 'error')
                return render_template('courses.html', form=form, courses=Course.query.all())
            
            units_added = 0
            for unit_name in curricular_units:
                # Check if unit already exists for this course
                existing_unit = CurricularUnit.query.filter_by(
                    name=unit_name, 
                    course_id=course.id
                ).first()
                
                if not existing_unit:
                    unit = CurricularUnit()  # type: ignore
                    unit.name = unit_name
                    unit.course_id = course.id
                    unit.description = f"Unidade curricular do curso {course.name}"
                    unit.is_active = True
                    db.session.add(unit)
                    units_added += 1
            
            db.session.commit()
            
            flash(f'Curso {course.name} cadastrado com sucesso! {units_added} unidade(s) curricular(es) adicionada(s).', 'success')
            return redirect(url_for('courses'))
        else:
            # Form validation failed
            for field, errors in form.errors.items():
                for error in errors:
                    flash(f'{getattr(form, field).label.text}: {error}', 'error')
    
    return render_template('courses.html', form=form, courses=Course.query.all())

@app.route('/courses/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_course(id):
    """Edit course"""
    course = Course.query.get_or_404(id)
    form = CourseForm(obj=course)
    
    if form.validate_on_submit():
        form.populate_obj(course)
        db.session.commit()
        
        flash(f'Curso {course.name} atualizado com sucesso!', 'success')
        return redirect(url_for('courses'))
    
    return render_template('courses.html', form=form, course=course, courses=Course.query.all())

@app.route('/courses/delete/<int:id>')
@login_required
def delete_course(id):
    """Delete course"""
    course = Course.query.get_or_404(id)
    
    try:
        db.session.delete(course)
        db.session.commit()
        flash(f'Curso {course.name} excluído com sucesso!', 'success')
    except Exception as e:
        flash('Erro ao excluir curso. Verifique se não existem avaliações vinculadas.', 'error')
        db.session.rollback()
    
    return redirect(url_for('courses'))

@app.route('/courses/template')
@login_required
def download_courses_template():
    """Download Excel template for course import"""
    try:
        template_buffer = generate_courses_excel_template()
        return send_file(
            template_buffer,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name='modelo_importacao_cursos.xlsx'
        )
    except Exception as e:
        flash(f'Erro ao gerar modelo: {str(e)}', 'error')
        return redirect(url_for('courses'))

@app.route('/courses/import', methods=['POST'])
@login_required
def import_courses_excel():
    """Import courses from Excel file"""
    if 'excel_file' not in request.files:
        flash('Nenhum arquivo selecionado.', 'error')
        return redirect(url_for('courses'))
    
    file = request.files['excel_file']
    if file.filename == '':
        flash('Nenhum arquivo selecionado.', 'error')
        return redirect(url_for('courses'))
    
    if not file.filename or not file.filename.lower().endswith(('.xlsx', '.xls')):
        flash('Por favor, selecione um arquivo Excel (.xlsx ou .xls).', 'error')
        return redirect(url_for('courses'))
    
    try:
        # Save uploaded file temporarily
        file_info = save_uploaded_file(file)
        if not file_info:
            flash('Erro ao salvar arquivo temporário.', 'error')
            return redirect(url_for('courses'))
        
        # Process the Excel file
        results = process_courses_excel_import(file_info['file_path'])
        
        # Clean up temporary file
        try:
            os.remove(file_info['file_path'])
        except:
            pass
        
        # Show results
        if results['success'] > 0:
            flash(f'Importação concluída! {results["success"]} curso(s) importado(s) com sucesso.', 'success')
        
        if results['warnings']:
            for warning in results['warnings'][:5]:  # Show first 5 warnings
                flash(warning, 'warning')
            if len(results['warnings']) > 5:
                flash(f'... e mais {len(results["warnings"]) - 5} avisos.', 'warning')
        
        if results['errors']:
            for error in results['errors'][:5]:  # Show first 5 errors
                flash(error, 'error')
            if len(results['errors']) > 5:
                flash(f'... e mais {len(results["errors"]) - 5} erros.', 'error')
        
        if results['success'] == 0 and results['errors']:
            flash('Nenhum curso foi importado devido aos erros encontrados.', 'error')
        
    except Exception as e:
        flash(f'Erro ao processar arquivo Excel: {str(e)}', 'error')
        current_app.logger.error(f"Excel import error: {str(e)}")
    
    return redirect(url_for('courses'))

@app.route('/evaluators')
@login_required
def evaluators():
    """List all evaluators"""
    evaluators_list = Evaluator.query.all()
    return render_template('evaluators.html', evaluators=evaluators_list)

@app.route('/evaluators/add', methods=['GET', 'POST'])
@login_required
def add_evaluator():
    """Add new evaluator"""
    form = EvaluatorForm()
    
    if form.validate_on_submit():
        evaluator = Evaluator()  # type: ignore
        evaluator.name = form.name.data
        evaluator.role = form.role.data
        evaluator.email = form.email.data
        
        db.session.add(evaluator)
        db.session.commit()
        
        flash(f'Avaliador {evaluator.name} cadastrado com sucesso!', 'success')
        return redirect(url_for('evaluators'))
    
    return render_template('evaluators.html', form=form, evaluators=Evaluator.query.all())

@app.route('/evaluators/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_evaluator(id):
    """Edit evaluator"""
    evaluator = Evaluator.query.get_or_404(id)
    form = EvaluatorForm(obj=evaluator)
    
    if form.validate_on_submit():
        form.populate_obj(evaluator)
        db.session.commit()
        
        flash(f'Avaliador {evaluator.name} atualizado com sucesso!', 'success')
        return redirect(url_for('evaluators'))
    
    return render_template('evaluators.html', form=form, evaluator=evaluator, evaluators=Evaluator.query.all())

@app.route('/evaluators/delete/<int:id>')
@login_required
def delete_evaluator(id):
    """Delete evaluator"""
    evaluator = Evaluator.query.get_or_404(id)
    
    try:
        db.session.delete(evaluator)
        db.session.commit()
        flash(f'Avaliador {evaluator.name} excluído com sucesso!', 'success')
    except Exception as e:
        flash('Erro ao excluir avaliador. Verifique se não existem avaliações vinculadas.', 'error')
        db.session.rollback()
    
    return redirect(url_for('evaluators'))

@app.route('/evaluations')
@login_required
def evaluations():
    """List all evaluations"""
    page = request.args.get('page', 1, type=int)
    evaluations_list = Evaluation.query.order_by(Evaluation.evaluation_date.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    return render_template('evaluation_form.html', evaluations=evaluations_list)

@app.route('/evaluations/new', methods=['GET', 'POST'])
def new_evaluation():
    """Create new evaluation"""
    form = EvaluationForm()
    
    # Populate choices
    form.teacher_id.choices = [(t.id, t.name) for t in Teacher.query.all()]
    form.course_id.choices = [(c.id, f"{c.name} - {c.period}") for c in Course.query.all()]
    form.curricular_unit_id.choices = [('', 'Nenhuma unidade curricular específica')] + [(u.id, f"{u.name} ({u.course.name})") for u in CurricularUnit.query.join(Course).all()]
    
    if form.validate_on_submit():
        evaluation = Evaluation()  # type: ignore
        evaluation.teacher_id = form.teacher_id.data
        evaluation.course_id = form.course_id.data
        evaluation.curricular_unit_id = form.curricular_unit_id.data if form.curricular_unit_id.data else None
        # Buscar ou criar avaliador padrão (já que o formulário não especifica avaliador)
        default_evaluator = Evaluator.query.filter_by(role='Sistema').first()
        if not default_evaluator:
            default_evaluator = Evaluator()  # type: ignore
            default_evaluator.name = 'Sistema'
            default_evaluator.role = 'Sistema'
            default_evaluator.email = 'sistema@escola.edu'
            db.session.add(default_evaluator)
            db.session.flush()
        evaluation.evaluator_id = default_evaluator.id
        evaluation.period = form.period.data
        evaluation.class_time = form.class_time.data
        
        # Planning fields
        evaluation.planning_schedule = form.planning_schedule.data
        evaluation.planning_lesson_plan = form.planning_lesson_plan.data
        evaluation.planning_evaluation = form.planning_evaluation.data
        evaluation.planning_documents = form.planning_documents.data
        evaluation.planning_diversified = form.planning_diversified.data
        evaluation.planning_local_work = form.planning_local_work.data
        evaluation.planning_tools = form.planning_tools.data
        evaluation.planning_educational_portal = form.planning_educational_portal.data
        
        # Class fields
        evaluation.class_presentation = form.class_presentation.data
        evaluation.class_knowledge = form.class_knowledge.data
        evaluation.class_student_performance = form.class_student_performance.data
        evaluation.class_attendance = form.class_attendance.data
        evaluation.class_difficulties = form.class_difficulties.data
        evaluation.class_theoretical_practical = form.class_theoretical_practical.data
        evaluation.class_previous_lesson = form.class_previous_lesson.data
        evaluation.class_objectives = form.class_objectives.data
        evaluation.class_questions = form.class_questions.data
        evaluation.class_content_assimilation = form.class_content_assimilation.data
        evaluation.class_student_participation = form.class_student_participation.data
        evaluation.class_recovery_process = form.class_recovery_process.data
        evaluation.class_school_pedagogy = form.class_school_pedagogy.data
        evaluation.class_learning_exercises = form.class_learning_exercises.data
        evaluation.class_discipline = form.class_discipline.data
        evaluation.class_educational_orientation = form.class_educational_orientation.data
        evaluation.class_teaching_strategies = form.class_teaching_strategies.data
        evaluation.class_machines_equipment = form.class_machines_equipment.data
        evaluation.class_safety_procedures = form.class_safety_procedures.data
        
        # Observations
        evaluation.planning_observations = form.planning_observations.data
        evaluation.class_observations = form.class_observations.data
        evaluation.general_observations = form.general_observations.data
        
        db.session.add(evaluation)
        db.session.flush()  # Get the ID before commit
        
        # Handle file upload
        if form.attachments.data:
            file_info = save_uploaded_file(form.attachments.data)
            if file_info:
                attachment = EvaluationAttachment()  # type: ignore
                attachment.evaluation_id = evaluation.id
                attachment.filename = file_info['filename']
                attachment.original_filename = file_info['original_filename']
                attachment.file_path = file_info['file_path']
                attachment.file_size = file_info['file_size']
                attachment.mime_type = file_info['mime_type']
                db.session.add(attachment)
        
        db.session.commit()
        
        flash('Avaliação criada com sucesso!', 'success')
        return redirect(url_for('view_evaluation', id=evaluation.id))
    
    return render_template('evaluation_form.html', form=form)

@app.route('/evaluations/view/<int:id>')
def view_evaluation(id):
    """View single evaluation"""
    evaluation = Evaluation.query.get_or_404(id)
    return render_template('evaluation_form.html', evaluation=evaluation, view_only=True)

@app.route('/evaluations/edit/<int:id>', methods=['GET', 'POST'])
def edit_evaluation(id):
    """Edit evaluation"""
    evaluation = Evaluation.query.get_or_404(id)
    form = EvaluationForm(obj=evaluation)
    
    # Populate choices
    form.teacher_id.choices = [(t.id, t.name) for t in Teacher.query.all()]
    form.course_id.choices = [(c.id, f"{c.name} - {c.period}") for c in Course.query.all()]
    form.curricular_unit_id.choices = [('', 'Nenhuma unidade curricular específica')] + [(u.id, f"{u.name} ({u.course.name})") for u in CurricularUnit.query.join(Course).all()]
    
    if form.validate_on_submit():
        form.populate_obj(evaluation)
        evaluation.updated_at = datetime.utcnow()
        
        # Handle new file upload
        if form.attachments.data:
            file_info = save_uploaded_file(form.attachments.data)
            if file_info:
                attachment = EvaluationAttachment()  # type: ignore
                attachment.evaluation_id = evaluation.id
                attachment.filename = file_info['filename']
                attachment.original_filename = file_info['original_filename']
                attachment.file_path = file_info['file_path']
                attachment.file_size = file_info['file_size']
                attachment.mime_type = file_info['mime_type']
                db.session.add(attachment)
        
        db.session.commit()
        
        flash('Avaliação atualizada com sucesso!', 'success')
        return redirect(url_for('view_evaluation', id=evaluation.id))
    
    return render_template('evaluation_form.html', form=form, evaluation=evaluation, edit_mode=True)

@app.route('/evaluations/complete/<int:id>')
def complete_evaluation(id):
    """Complete and finalize evaluation"""
    evaluation = Evaluation.query.get_or_404(id)
    
    evaluation.is_completed = True
    evaluation.teacher_signature_date = datetime.utcnow()
    evaluation.evaluator_signature_date = datetime.utcnow()
    
    db.session.commit()
    
    # Send email notification
    if evaluation.teacher.email:
        try:
            report_buffer = generate_evaluation_report(evaluation)
            report_path = os.path.join(current_app.config['UPLOAD_FOLDER'], f'temp_report_{evaluation.id}.pdf')
            
            with open(report_path, 'wb') as f:
                f.write(report_buffer.read())
            
            send_evaluation_email(evaluation.teacher.email, evaluation, report_path)
            
            # Clean up temp file
            if os.path.exists(report_path):
                os.remove(report_path)
                
            flash('Avaliação finalizada e relatório enviado por email!', 'success')
        except Exception as e:
            flash('Avaliação finalizada, mas houve erro no envio do email.', 'warning')
            current_app.logger.error(f"Email error: {str(e)}")
    else:
        flash('Avaliação finalizada! (Email não cadastrado para o professor)', 'success')
    
    return redirect(url_for('view_evaluation', id=evaluation.id))

@app.route('/reports')
@login_required
def reports():
    """Reports page"""
    teachers = Teacher.query.all()
    return render_template('reports.html', teachers=teachers)

@app.route('/reports/evaluation/<int:id>')
@login_required
def download_evaluation_report(id):
    """Download individual evaluation report"""
    evaluation = Evaluation.query.get_or_404(id)
    
    report_buffer = generate_evaluation_report(evaluation)
    filename = f"avaliacao_{evaluation.teacher.name.replace(' ', '_')}_{evaluation.evaluation_date.strftime('%Y%m%d')}.pdf"
    
    return send_file(
        report_buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=filename
    )

@app.route('/reports/consolidated/<int:teacher_id>')
@login_required
def download_consolidated_report(teacher_id):
    """Download consolidated teacher report"""
    teacher = Teacher.query.get_or_404(teacher_id)
    
    # Get date range from query parameters
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    if start_date:
        start_date = datetime.strptime(start_date, '%Y-%m-%d')
    if end_date:
        end_date = datetime.strptime(end_date, '%Y-%m-%d')
    
    report_buffer = generate_consolidated_report(teacher_id, start_date, end_date)
    
    if not report_buffer:
        flash('Nenhuma avaliação encontrada para o período especificado.', 'warning')
        return redirect(url_for('reports'))
    
    filename = f"consolidado_{teacher.name.replace(' ', '_')}.pdf"
    
    return send_file(
        report_buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=filename
    )

@app.route('/api/dashboard-data')
@login_required
def dashboard_data():
    """API endpoint for dashboard statistics"""
    # Monthly evaluation counts
    months = []
    evaluation_counts = []
    
    for i in range(6):
        month_start = (datetime.now().replace(day=1) - timedelta(days=32*i)).replace(day=1)
        month_end = (month_start.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
        
        count = Evaluation.query.filter(
            Evaluation.evaluation_date >= month_start,
            Evaluation.evaluation_date <= month_end
        ).count()
        
        months.append(month_start.strftime('%b/%Y'))
        evaluation_counts.append(count)
    
    months.reverse()
    evaluation_counts.reverse()
    
    # Top performers
    teachers_performance = []
    for teacher in Teacher.query.all():
        evaluations = teacher.evaluations
        if evaluations:
            avg_planning = sum(eval.calculate_planning_percentage() for eval in evaluations) / len(evaluations)
            avg_class = sum(eval.calculate_class_percentage() for eval in evaluations) / len(evaluations)
            overall = (avg_planning + avg_class) / 2
            
            teachers_performance.append({
                'name': teacher.name,
                'planning': round(avg_planning, 1),
                'class': round(avg_class, 1),
                'overall': round(overall, 1)
            })
    
    teachers_performance.sort(key=lambda x: x['overall'], reverse=True)
    
    return jsonify({
        'monthly_evaluations': {
            'labels': months,
            'data': evaluation_counts
        },
        'top_performers': teachers_performance[:10]
    })

@app.errorhandler(404)
def not_found_error(error):
    return render_template('base.html', error_message="Página não encontrada"), 404

# Teacher Portal Routes
@app.route('/teacher_dashboard')
@login_required
def teacher_dashboard():
    """Dashboard for teachers"""
    if not current_user.is_teacher():
        flash('Acesso negado. Esta área é destinada apenas aos docentes.', 'error')
        return redirect(url_for('index'))
    
    # Get teacher profile
    teacher = Teacher.query.filter_by(user_id=current_user.id).first()
    if not teacher:
        flash('Perfil de docente não encontrado.', 'error')
        return redirect(url_for('logout'))
    
    # Get current semester
    current_semester = Semester.query.filter_by(is_active=True).first()
    
    # Get evaluations for this teacher
    evaluations = Evaluation.query.filter_by(teacher_id=teacher.id).all()
    
    # Get pending evaluations (those not signed by teacher)
    pending_evaluations = [e for e in evaluations if not e.teacher_signed and e.evaluator_signed]
    
    # Get scheduled evaluations
    scheduled = []
    if current_semester:
        scheduled = ScheduledEvaluation.query.filter_by(
            teacher_id=teacher.id,
            semester_id=current_semester.id,
            is_completed=False
        ).all()
    
    return render_template('teacher_dashboard.html', 
                         teacher=teacher,
                         evaluations=evaluations,
                         pending_evaluations=pending_evaluations,
                         scheduled_evaluations=scheduled,
                         current_semester=current_semester)

@app.route('/teacher_evaluation/<int:id>')
@login_required 
def teacher_view_evaluation(id):
    """Teacher views their evaluation"""
    if not current_user.is_teacher():
        flash('Acesso negado.', 'error')
        return redirect(url_for('index'))
    
    teacher = Teacher.query.filter_by(user_id=current_user.id).first()
    if not teacher:
        flash('Perfil de docente não encontrado.', 'error')
        return redirect(url_for('logout'))
    
    evaluation = Evaluation.query.filter_by(id=id, teacher_id=teacher.id).first_or_404()
    
    return render_template('teacher_evaluation_view.html', evaluation=evaluation)

@app.route('/teacher_sign_evaluation/<int:id>', methods=['POST'])
@login_required
def teacher_sign_evaluation(id):
    """Teacher signs their evaluation digitally"""
    if not current_user.is_teacher():
        return jsonify({'error': 'Acesso negado'}), 403
    
    teacher = Teacher.query.filter_by(user_id=current_user.id).first()
    if not teacher:
        return jsonify({'error': 'Perfil de docente não encontrado'}), 404
    
    evaluation = Evaluation.query.filter_by(id=id, teacher_id=teacher.id).first_or_404()
    
    if evaluation.teacher_signed:
        return jsonify({'error': 'Avaliação já foi assinada'}), 400
    
    signature_data = (request.json or {}).get('signature')
    if not signature_data:
        return jsonify({'error': 'Assinatura não fornecida'}), 400
    
    # Save digital signature
    signature = DigitalSignature()  # type: ignore
    signature.evaluation_id = evaluation.id
    signature.user_id = current_user.id
    signature.signature_data = signature_data
    signature.signature_type = 'teacher'
    signature.ip_address = request.environ.get('REMOTE_ADDR')
    
    # Mark evaluation as signed by teacher
    evaluation.teacher_signed = True
    evaluation.teacher_signature_date = datetime.utcnow()
    
    # Check if both teacher and evaluator have signed
    if evaluation.teacher_signed and evaluation.evaluator_signed:
        evaluation.is_completed = True
        
        # Mark scheduled evaluation as completed if exists
        if evaluation.scheduled_evaluation_id:
            scheduled = ScheduledEvaluation.query.get(evaluation.scheduled_evaluation_id)
            if scheduled:
                scheduled.is_completed = True
                scheduled.completed_at = datetime.utcnow()
    
    db.session.add(signature)
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Avaliação assinada com sucesso!'})

@app.route('/evaluator_sign_evaluation/<int:id>', methods=['POST'])
@login_required
def evaluator_sign_evaluation(id):
    """Evaluator signs evaluation digitally"""
    if not (current_user.is_admin() or current_user.role == 'evaluator'):
        return jsonify({'error': 'Acesso negado'}), 403
    
    evaluation = Evaluation.query.get_or_404(id)
    
    if evaluation.evaluator_signed:
        return jsonify({'error': 'Avaliação já foi assinada pelo avaliador'}), 400
    
    signature_data = (request.json or {}).get('signature')
    if not signature_data:
        return jsonify({'error': 'Assinatura não fornecida'}), 400
    
    # Save digital signature
    signature = DigitalSignature()  # type: ignore
    signature.evaluation_id = evaluation.id
    signature.user_id = current_user.id
    signature.signature_data = signature_data
    signature.signature_type = 'evaluator'
    signature.ip_address = request.environ.get('REMOTE_ADDR')
    
    # Mark evaluation as signed by evaluator
    evaluation.evaluator_signed = True
    evaluation.evaluator_signature_date = datetime.utcnow()
    
    # Check if both teacher and evaluator have signed
    if evaluation.teacher_signed and evaluation.evaluator_signed:
        evaluation.is_completed = True
        
        # Mark scheduled evaluation as completed if exists
        if evaluation.scheduled_evaluation_id:
            scheduled = ScheduledEvaluation.query.get(evaluation.scheduled_evaluation_id)
            if scheduled:
                scheduled.is_completed = True
                scheduled.completed_at = datetime.utcnow()
    
    db.session.add(signature)
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Avaliação assinada pelo avaliador com sucesso!'})

# Scheduling Routes
@app.route('/scheduling')
@login_required
def scheduling():
    """Scheduling dashboard"""
    if not current_user.is_admin():
        flash('Acesso negado. Apenas administradores podem gerenciar agendamentos.', 'error')
        return redirect(url_for('index'))
    
    # Get or create current semester based on current date
    current_semester = get_or_create_current_semester()
    
    # Get scheduled evaluations for current semester
    scheduled_evaluations = ScheduledEvaluation.query.filter_by(
        semester_id=current_semester.id
    ).order_by(ScheduledEvaluation.scheduled_month, ScheduledEvaluation.teacher_id).all()
    
    # Get all teachers and curricular units for the form
    teachers = Teacher.query.all()
    curricular_units = CurricularUnit.query.filter_by(is_active=True).all()
    
    # Organize by month
    monthly_schedule = {}
    for i in range(1, 13):
        monthly_schedule[i] = []
    
    for scheduled in scheduled_evaluations:
        monthly_schedule[scheduled.scheduled_month].append(scheduled)
    
    return render_template('scheduling.html',
                         current_semester=current_semester,
                         monthly_schedule=monthly_schedule,
                         teachers=teachers,
                         curricular_units=curricular_units)

@app.route('/scheduling/add', methods=['POST'])
@login_required
def add_scheduled_evaluation():
    """Add new scheduled evaluation"""
    if not current_user.is_admin():
        return jsonify({'error': 'Acesso negado'}), 403
    
    current_semester = get_or_create_current_semester()
    
    data = request.json or {}
    teacher_id = data.get('teacher_id')
    curricular_unit_id = data.get('curricular_unit_id')
    scheduled_month = data.get('scheduled_month')
    scheduled_date = data.get('scheduled_date')
    
    if not teacher_id or not curricular_unit_id or not scheduled_month:
        return jsonify({'error': 'Dados obrigatórios não fornecidos'}), 400
    
    try:
        scheduled_month = int(scheduled_month)
        if not 1 <= scheduled_month <= 12:
            return jsonify({'error': 'Mês inválido'}), 400
    except ValueError:
        return jsonify({'error': 'Mês deve ser um número'}), 400
    
    # Check if already scheduled
    existing = ScheduledEvaluation.query.filter_by(
        teacher_id=teacher_id,
        curricular_unit_id=curricular_unit_id,
        semester_id=current_semester.id,
        scheduled_month=scheduled_month
    ).first()
    
    if existing:
        return jsonify({'error': 'Docente já agendado para esta unidade curricular neste mês'}), 400
    
    # Create scheduled evaluation
    scheduled = ScheduledEvaluation()  # type: ignore
    scheduled.teacher_id = teacher_id
    scheduled.curricular_unit_id = curricular_unit_id
    scheduled.semester_id = current_semester.id
    scheduled.scheduled_month = scheduled_month
    scheduled.scheduled_year = current_semester.year
    scheduled.created_by = current_user.id
    
    if scheduled_date:
        try:
            from datetime import datetime
            scheduled.scheduled_date = datetime.strptime(scheduled_date, '%Y-%m-%d')
        except ValueError:
            return jsonify({'error': 'Formato de data inválido'}), 400
    
    db.session.add(scheduled)
    db.session.commit()
    
    return jsonify({
        'success': True, 
        'message': 'Avaliação agendada com sucesso!',
        'scheduled_id': scheduled.id
    })

@app.route('/scheduling/delete/<int:id>', methods=['DELETE'])
@login_required
def delete_scheduled_evaluation(id):
    """Delete scheduled evaluation"""
    if not current_user.is_admin():
        return jsonify({'error': 'Acesso negado'}), 403
    
    scheduled = ScheduledEvaluation.query.get_or_404(id)
    
    if scheduled.is_completed:
        return jsonify({'error': 'Não é possível excluir avaliação já concluída'}), 400
    
    db.session.delete(scheduled)
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Agendamento excluído com sucesso!'})

@app.route('/semesters')
@login_required
def semesters():
    """Manage semesters"""
    if not current_user.is_admin():
        flash('Acesso negado. Apenas administradores podem gerenciar semestres.', 'error')
        return redirect(url_for('index'))
    
    semesters_list = Semester.query.order_by(Semester.year.desc(), Semester.number.desc()).all()
    return render_template('semesters.html', semesters=semesters_list)

@app.route('/semesters/add', methods=['POST'])
@login_required
def add_semester():
    """Add new semester"""
    if not current_user.is_admin():
        return jsonify({'error': 'Acesso negado'}), 403
    
    data = request.json or {}
    year = data.get('year')
    number = data.get('number')
    start_date = data.get('start_date')
    end_date = data.get('end_date')
    
    if not all([year, number, start_date, end_date]):
        return jsonify({'error': 'Todos os campos são obrigatórios'}), 400
    
    try:
        year_int = int(year) if year else 0
        number_int = int(number) if number else 0
        if number_int not in [1, 2]:
            return jsonify({'error': 'Número do semestre deve ser 1 ou 2'}), 400
    except ValueError:
        return jsonify({'error': 'Ano e número devem ser números'}), 400
    
    # Check if semester already exists
    existing = Semester.query.filter_by(year=year_int, number=number_int).first()
    if existing:
        return jsonify({'error': 'Semestre já existe'}), 400
    
    try:
        from datetime import datetime
        start_date_obj = datetime.strptime(str(start_date), '%Y-%m-%d')
        end_date_obj = datetime.strptime(str(end_date), '%Y-%m-%d')
        
        if start_date_obj >= end_date_obj:
            return jsonify({'error': 'Data de início deve ser anterior à data de fim'}), 400
    except ValueError:
        return jsonify({'error': 'Formato de data inválido'}), 400
    
    # Create semester
    semester = Semester()  # type: ignore
    semester.name = f"{year_int}.{number_int}"
    semester.year = year_int
    semester.number = number_int
    semester.start_date = start_date_obj
    semester.end_date = end_date_obj
    semester.is_active = False
    
    db.session.add(semester)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Semestre criado com sucesso!',
        'semester_id': semester.id
    })

@app.route('/semesters/activate/<int:id>', methods=['POST'])
@login_required
def activate_semester(id):
    """Activate a semester"""
    if not current_user.is_admin():
        return jsonify({'error': 'Acesso negado'}), 403
    
    semester = Semester.query.get_or_404(id)
    
    # Deactivate all semesters first
    Semester.query.update({Semester.is_active: False})
    
    # Activate the selected one
    semester.is_active = True
    db.session.commit()
    
    return jsonify({'success': True, 'message': f'Semestre {semester.name} ativado!'})

# Curricular Units Routes
@app.route('/curricular_units')
@login_required
def curricular_units():
    """Manage curricular units"""
    if not current_user.is_admin():
        flash('Acesso negado. Apenas administradores podem gerenciar unidades curriculares.', 'error')
        return redirect(url_for('index'))
    
    # Check if filtering by course
    course_id = request.args.get('course_id', type=int)
    selected_course = None
    
    if course_id:
        selected_course = Course.query.get_or_404(course_id)
        units = CurricularUnit.query.filter_by(course_id=course_id).order_by(CurricularUnit.name).all()
    else:
        units = CurricularUnit.query.join(Course).order_by(Course.name, CurricularUnit.name).all()
    
    courses = Course.query.all()
    
    return render_template('curricular_units.html', 
                         units=units, 
                         courses=courses,
                         selected_course=selected_course)

@app.route('/curricular_units/add', methods=['POST'])
@login_required
def add_curricular_unit():
    """Add new curricular unit"""
    if not current_user.is_admin():
        return jsonify({'error': 'Acesso negado'}), 403
    
    data = request.json or {}
    name = data.get('name')
    code = data.get('code')
    course_id = data.get('course_id')
    workload = data.get('workload')
    description = data.get('description')
    
    if not name or not course_id:
        return jsonify({'error': 'Nome e curso são obrigatórios'}), 400
    
    # Check if course exists
    course = Course.query.get(course_id)
    if not course:
        return jsonify({'error': 'Curso não encontrado'}), 404
    
    # Check if unit already exists for this course
    existing = CurricularUnit.query.filter_by(name=name, course_id=course_id).first()
    if existing:
        return jsonify({'error': 'Unidade curricular já existe para este curso'}), 400
    
    # Create curricular unit
    unit = CurricularUnit()  # type: ignore
    unit.name = name
    unit.code = code
    unit.course_id = course_id
    unit.workload = int(workload) if workload else None
    unit.description = description
    
    db.session.add(unit)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Unidade curricular criada com sucesso!',
        'unit_id': unit.id
    })

@app.route('/curricular_units/edit/<int:id>', methods=['PUT'])
@login_required
def edit_curricular_unit(id):
    """Edit curricular unit"""
    if not current_user.is_admin():
        return jsonify({'error': 'Acesso negado'}), 403
    
    unit = CurricularUnit.query.get_or_404(id)
    data = request.json or {}
    
    name = data.get('name')
    code = data.get('code')
    course_id = data.get('course_id')
    workload = data.get('workload')
    description = data.get('description')
    
    if not name or not course_id:
        return jsonify({'error': 'Nome e curso são obrigatórios'}), 400
    
    # Check if course exists
    course = Course.query.get(course_id)
    if not course:
        return jsonify({'error': 'Curso não encontrado'}), 404
    
    # Check if unit already exists for this course (excluding current unit)
    existing = CurricularUnit.query.filter(
        CurricularUnit.name == name,
        CurricularUnit.course_id == course_id,
        CurricularUnit.id != unit.id
    ).first()
    if existing:
        return jsonify({'error': 'Unidade curricular já existe para este curso'}), 400
    
    # Update unit
    unit.name = name
    unit.code = code
    unit.course_id = course_id
    unit.workload = int(workload) if workload else None
    unit.description = description
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Unidade curricular atualizada com sucesso!'
    })

@app.route('/curricular_units/delete/<int:id>', methods=['DELETE'])
@login_required
def delete_curricular_unit(id):
    """Delete curricular unit"""
    if not current_user.is_admin():
        return jsonify({'error': 'Acesso negado'}), 403
    
    unit = CurricularUnit.query.get_or_404(id)
    
    # Check if unit has evaluations
    if unit.evaluations:
        return jsonify({'error': 'Não é possível excluir unidade curricular com avaliações vinculadas'}), 400
    
    # Check if unit has scheduled evaluations
    scheduled_count = ScheduledEvaluation.query.filter_by(curricular_unit_id=unit.id).count()
    if scheduled_count > 0:
        return jsonify({'error': 'Não é possível excluir unidade curricular com agendamentos'}), 400
    
    db.session.delete(unit)
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Unidade curricular excluída com sucesso!'})

@app.route('/curricular_units/template')
@login_required
def download_curricular_units_template():
    """Download Excel template for curricular units import"""
    if not current_user.is_admin():
        flash('Acesso negado. Apenas administradores podem gerenciar unidades curriculares.', 'error')
        return redirect(url_for('index'))
    
    try:
        template_buffer = generate_curricular_units_excel_template()
        return send_file(
            template_buffer,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name='modelo_importacao_unidades_curriculares.xlsx'
        )
    except Exception as e:
        flash(f'Erro ao gerar modelo: {str(e)}', 'error')
        return redirect(url_for('curricular_units'))

@app.route('/curricular_units/import', methods=['POST'])
@login_required
def import_curricular_units_excel():
    """Import curricular units from Excel file"""
    if not current_user.is_admin():
        flash('Acesso negado. Apenas administradores podem gerenciar unidades curriculares.', 'error')
        return redirect(url_for('index'))
    
    if 'excel_file' not in request.files:
        flash('Nenhum arquivo selecionado.', 'error')
        return redirect(url_for('curricular_units'))
    
    file = request.files['excel_file']
    if file.filename == '':
        flash('Nenhum arquivo selecionado.', 'error')
        return redirect(url_for('curricular_units'))
    
    if not file.filename or not file.filename.lower().endswith(('.xlsx', '.xls')):
        flash('Por favor, selecione um arquivo Excel (.xlsx ou .xls).', 'error')
        return redirect(url_for('curricular_units'))
    
    try:
        # Save uploaded file temporarily
        file_info = save_uploaded_file(file)
        if not file_info:
            flash('Erro ao salvar arquivo temporário.', 'error')
            return redirect(url_for('curricular_units'))
        
        # Process the Excel file
        results = process_curricular_units_excel_import(file_info['file_path'])
        
        # Clean up temporary file
        try:
            os.remove(file_info['file_path'])
        except:
            pass
        
        # Show results
        if results['success'] > 0:
            flash(f'Importação concluída! {results["success"]} unidade(s) curricular(es) importada(s) com sucesso.', 'success')
        
        if results['warnings']:
            for warning in results['warnings'][:5]:  # Show first 5 warnings
                flash(warning, 'warning')
            if len(results['warnings']) > 5:
                flash(f'... e mais {len(results["warnings"]) - 5} avisos.', 'warning')
        
        if results['errors']:
            for error in results['errors'][:5]:  # Show first 5 errors
                flash(error, 'error')
            if len(results['errors']) > 5:
                flash(f'... e mais {len(results["errors"]) - 5} erros.', 'error')
        
        if results['success'] == 0 and results['errors']:
            flash('Nenhuma unidade curricular foi importada devido aos erros encontrados.', 'error')
        
    except Exception as e:
        flash(f'Erro ao processar arquivo Excel: {str(e)}', 'error')
        current_app.logger.error(f"Excel import error: {str(e)}")
    
    return redirect(url_for('curricular_units'))

@app.route('/curricular_units/toggle_active/<int:id>', methods=['POST'])
@login_required
def toggle_curricular_unit_active(id):
    """Toggle curricular unit active status"""
    if not current_user.is_admin():
        return jsonify({'error': 'Acesso negado'}), 403
    
    unit = CurricularUnit.query.get_or_404(id)
    unit.is_active = not unit.is_active
    db.session.commit()
    
    status = 'ativada' if unit.is_active else 'desativada'
    return jsonify({'success': True, 'message': f'Unidade curricular {status}!'})

@app.errorhandler(404)
def page_not_found(error):
    return render_template('base.html', error_message="Página não encontrada"), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('base.html', error_message="Erro interno do servidor"), 500
