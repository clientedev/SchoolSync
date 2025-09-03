import os
from flask import render_template, request, redirect, url_for, flash, jsonify, send_file, current_app
from datetime import datetime, timedelta
from app import app, db
from models import Teacher, Course, Evaluator, Evaluation, EvaluationAttachment
from forms import TeacherForm, CourseForm, EvaluatorForm, EvaluationForm
from utils import save_uploaded_file, send_evaluation_email, generate_evaluation_report, generate_consolidated_report, generate_teachers_excel_template, process_teachers_excel_import

@app.route('/')
def index():
    """Dashboard - Main page"""
    # Get statistics
    total_teachers = Teacher.query.count()
    total_evaluations = Evaluation.query.count()
    total_courses = Course.query.count()
    
    # Recent evaluations
    recent_evaluations = Evaluation.query.order_by(Evaluation.evaluation_date.desc()).limit(5).all()
    
    # Teachers with no evaluations this month
    start_of_month = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    teachers_without_evaluation = Teacher.query.filter(
        ~Teacher.evaluations.any(Evaluation.evaluation_date >= start_of_month)
    ).all()
    
    # Average scores
    evaluations = Evaluation.query.all()
    avg_planning = 0
    avg_class = 0
    
    if evaluations:
        avg_planning = sum(eval.calculate_planning_percentage() for eval in evaluations) / len(evaluations)
        avg_class = sum(eval.calculate_class_percentage() for eval in evaluations) / len(evaluations)
    
    return render_template('dashboard.html',
                         total_teachers=total_teachers,
                         total_evaluations=total_evaluations,
                         total_courses=total_courses,
                         recent_evaluations=recent_evaluations,
                         teachers_without_evaluation=teachers_without_evaluation,
                         avg_planning=round(avg_planning, 1),
                         avg_class=round(avg_class, 1))

@app.route('/teachers')
def teachers():
    """List all teachers"""
    teachers_list = Teacher.query.all()
    return render_template('teachers.html', teachers=teachers_list)

@app.route('/teachers/add', methods=['GET', 'POST'])
def add_teacher():
    """Add new teacher"""
    form = TeacherForm()
    
    if form.validate_on_submit():
        teacher = Teacher(
            name=form.name.data,
            area=form.area.data,
            subjects=form.subjects.data,
            workload=form.workload.data,
            email=form.email.data,
            phone=form.phone.data
        )
        
        db.session.add(teacher)
        db.session.commit()
        
        flash(f'Professor {teacher.name} cadastrado com sucesso!', 'success')
        return redirect(url_for('teachers'))
    
    return render_template('teachers.html', form=form, teachers=Teacher.query.all())

@app.route('/teachers/edit/<int:id>', methods=['GET', 'POST'])
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
def import_teachers_excel():
    """Import teachers from Excel file"""
    if 'excel_file' not in request.files:
        flash('Nenhum arquivo selecionado.', 'error')
        return redirect(url_for('teachers'))
    
    file = request.files['excel_file']
    if file.filename == '':
        flash('Nenhum arquivo selecionado.', 'error')
        return redirect(url_for('teachers'))
    
    if not file.filename.lower().endswith(('.xlsx', '.xls')):
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
def courses():
    """List all courses"""
    courses_list = Course.query.all()
    return render_template('courses.html', courses=courses_list)

@app.route('/courses/add', methods=['GET', 'POST'])
def add_course():
    """Add new course"""
    form = CourseForm()
    
    if form.validate_on_submit():
        course = Course(
            name=form.name.data,
            period=form.period.data,
            curriculum_component=form.curriculum_component.data,
            class_code=form.class_code.data
        )
        
        db.session.add(course)
        db.session.commit()
        
        flash(f'Curso {course.name} cadastrado com sucesso!', 'success')
        return redirect(url_for('courses'))
    
    return render_template('courses.html', form=form, courses=Course.query.all())

@app.route('/courses/edit/<int:id>', methods=['GET', 'POST'])
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

@app.route('/evaluators')
def evaluators():
    """List all evaluators"""
    evaluators_list = Evaluator.query.all()
    return render_template('evaluators.html', evaluators=evaluators_list)

@app.route('/evaluators/add', methods=['GET', 'POST'])
def add_evaluator():
    """Add new evaluator"""
    form = EvaluatorForm()
    
    if form.validate_on_submit():
        evaluator = Evaluator(
            name=form.name.data,
            role=form.role.data,
            email=form.email.data
        )
        
        db.session.add(evaluator)
        db.session.commit()
        
        flash(f'Avaliador {evaluator.name} cadastrado com sucesso!', 'success')
        return redirect(url_for('evaluators'))
    
    return render_template('evaluators.html', form=form, evaluators=Evaluator.query.all())

@app.route('/evaluators/edit/<int:id>', methods=['GET', 'POST'])
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
    form.evaluator_id.choices = [(e.id, e.name) for e in Evaluator.query.all()]
    
    if form.validate_on_submit():
        evaluation = Evaluation(
            teacher_id=form.teacher_id.data,
            course_id=form.course_id.data,
            evaluator_id=form.evaluator_id.data,
            period=form.period.data,
            class_time=form.class_time.data,
            
            # Planning fields
            planning_schedule=form.planning_schedule.data,
            planning_lesson_plan=form.planning_lesson_plan.data,
            planning_evaluation=form.planning_evaluation.data,
            planning_documents=form.planning_documents.data,
            planning_diversified=form.planning_diversified.data,
            planning_local_work=form.planning_local_work.data,
            planning_tools=form.planning_tools.data,
            planning_educational_portal=form.planning_educational_portal.data,
            
            # Class fields
            class_presentation=form.class_presentation.data,
            class_knowledge=form.class_knowledge.data,
            class_student_performance=form.class_student_performance.data,
            class_attendance=form.class_attendance.data,
            class_difficulties=form.class_difficulties.data,
            class_theoretical_practical=form.class_theoretical_practical.data,
            class_previous_lesson=form.class_previous_lesson.data,
            class_objectives=form.class_objectives.data,
            class_questions=form.class_questions.data,
            class_content_assimilation=form.class_content_assimilation.data,
            class_student_participation=form.class_student_participation.data,
            class_recovery_process=form.class_recovery_process.data,
            class_school_pedagogy=form.class_school_pedagogy.data,
            class_learning_exercises=form.class_learning_exercises.data,
            class_discipline=form.class_discipline.data,
            class_educational_orientation=form.class_educational_orientation.data,
            class_teaching_strategies=form.class_teaching_strategies.data,
            class_machines_equipment=form.class_machines_equipment.data,
            class_safety_procedures=form.class_safety_procedures.data,
            
            # Observations
            planning_observations=form.planning_observations.data,
            class_observations=form.class_observations.data,
            general_observations=form.general_observations.data
        )
        
        db.session.add(evaluation)
        db.session.flush()  # Get the ID before commit
        
        # Handle file upload
        if form.attachments.data:
            file_info = save_uploaded_file(form.attachments.data)
            if file_info:
                attachment = EvaluationAttachment(
                    evaluation_id=evaluation.id,
                    filename=file_info['filename'],
                    original_filename=file_info['original_filename'],
                    file_path=file_info['file_path'],
                    file_size=file_info['file_size'],
                    mime_type=file_info['mime_type']
                )
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
    form.evaluator_id.choices = [(e.id, e.name) for e in Evaluator.query.all()]
    
    if form.validate_on_submit():
        form.populate_obj(evaluation)
        evaluation.updated_at = datetime.utcnow()
        
        # Handle new file upload
        if form.attachments.data:
            file_info = save_uploaded_file(form.attachments.data)
            if file_info:
                attachment = EvaluationAttachment(
                    evaluation_id=evaluation.id,
                    filename=file_info['filename'],
                    original_filename=file_info['original_filename'],
                    file_path=file_info['file_path'],
                    file_size=file_info['file_size'],
                    mime_type=file_info['mime_type']
                )
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
def reports():
    """Reports page"""
    teachers = Teacher.query.all()
    return render_template('reports.html', teachers=teachers)

@app.route('/reports/evaluation/<int:id>')
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

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('base.html', error_message="Erro interno do servidor"), 500
