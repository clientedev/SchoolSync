import os
import uuid
from werkzeug.utils import secure_filename
from flask import current_app
from flask_mail import Message
from app import mail
from io import BytesIO
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from datetime import datetime

def save_uploaded_file(file):
    """Save uploaded file and return file info"""
    if file and file.filename:
        # Generate unique filename
        filename = secure_filename(file.filename)
        unique_filename = str(uuid.uuid4()) + '_' + filename
        
        # Save file
        file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], unique_filename)
        file.save(file_path)
        
        return {
            'filename': unique_filename,
            'original_filename': filename,
            'file_path': file_path,
            'file_size': os.path.getsize(file_path),
            'mime_type': file.mimetype
        }
    return None

def send_evaluation_email(teacher_email, evaluation, report_path=None):
    """Send evaluation notification email"""
    if not teacher_email:
        return False
        
    try:
        msg = Message(
            subject=f'Relatório de Acompanhamento Docente - {evaluation.evaluation_date.strftime("%d/%m/%Y")}',
            recipients=[teacher_email]
        )
        
        msg.body = f"""
Prezado(a) {evaluation.teacher.name},

Seu acompanhamento docente foi finalizado com as seguintes informações:

Curso: {evaluation.course.name}
Data: {evaluation.evaluation_date.strftime("%d/%m/%Y")}
Período: {evaluation.period}
Avaliador: {evaluation.evaluator.name}

Planejamento: {evaluation.calculate_planning_percentage()}% atendido
Condução da aula: {evaluation.calculate_class_percentage()}% atendido

Observações gerais:
{evaluation.general_observations or 'Nenhuma observação adicional.'}

Atenciosamente,
Coordenação Pedagógica
"""
        
        if report_path and os.path.exists(report_path):
            with open(report_path, 'rb') as f:
                msg.attach(f"relatorio_{evaluation.teacher.name.replace(' ', '_')}.pdf", 
                          "application/pdf", f.read())
        
        mail.send(msg)
        return True
    except Exception as e:
        current_app.logger.error(f"Error sending email: {str(e)}")
        return False

def generate_evaluation_report(evaluation):
    """Generate PDF report for a single evaluation"""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []
    
    # Title
    title_style = ParagraphStyle('CustomTitle', parent=styles['Title'], 
                                fontSize=16, spaceAfter=30, alignment=1)
    story.append(Paragraph("RELATÓRIO DE ACOMPANHAMENTO DOCENTE", title_style))
    story.append(Spacer(1, 20))
    
    # Basic Info Table
    basic_info = [
        ['Docente:', evaluation.teacher.name],
        ['Curso:', evaluation.course.name],
        ['Período:', evaluation.period],
        ['Data:', evaluation.evaluation_date.strftime("%d/%m/%Y")],
        ['Avaliador:', evaluation.evaluator.name]
    ]
    
    basic_table = Table(basic_info, colWidths=[2*inch, 4*inch])
    basic_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.grey),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('BACKGROUND', (1, 0), (1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    story.append(basic_table)
    story.append(Spacer(1, 20))
    
    # Results Summary
    planning_pct = evaluation.calculate_planning_percentage()
    class_pct = evaluation.calculate_class_percentage()
    
    results = [
        ['RESUMO DOS RESULTADOS', ''],
        ['Planejamento:', f'{planning_pct}% atendido'],
        ['Condução da aula:', f'{class_pct}% atendido'],
    ]
    
    results_table = Table(results, colWidths=[2*inch, 4*inch])
    results_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('BACKGROUND', (0, 1), (0, -1), colors.grey),
        ('TEXTCOLOR', (0, 1), (0, -1), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('BACKGROUND', (1, 1), (1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    story.append(results_table)
    story.append(Spacer(1, 20))
    
    # Observations
    if evaluation.planning_observations:
        story.append(Paragraph("<b>Observações - Planejamento:</b>", styles['Heading3']))
        story.append(Paragraph(evaluation.planning_observations, styles['Normal']))
        story.append(Spacer(1, 12))
    
    if evaluation.class_observations:
        story.append(Paragraph("<b>Observações - Período da Aula:</b>", styles['Heading3']))
        story.append(Paragraph(evaluation.class_observations, styles['Normal']))
        story.append(Spacer(1, 12))
    
    if evaluation.general_observations:
        story.append(Paragraph("<b>Observações Gerais:</b>", styles['Heading3']))
        story.append(Paragraph(evaluation.general_observations, styles['Normal']))
        story.append(Spacer(1, 12))
    
    # Footer
    story.append(Spacer(1, 30))
    story.append(Paragraph(f"Relatório gerado em {datetime.now().strftime('%d/%m/%Y às %H:%M')}", 
                          styles['Normal']))
    
    doc.build(story)
    buffer.seek(0)
    return buffer

def generate_consolidated_report(teacher_id, start_date=None, end_date=None):
    """Generate consolidated report for a teacher"""
    from models import Evaluation, Teacher
    
    teacher = Teacher.query.get(teacher_id)
    if not teacher:
        return None
    
    query = Evaluation.query.filter_by(teacher_id=teacher_id)
    if start_date:
        query = query.filter(Evaluation.evaluation_date >= start_date)
    if end_date:
        query = query.filter(Evaluation.evaluation_date <= end_date)
    
    evaluations = query.order_by(Evaluation.evaluation_date.desc()).all()
    
    if not evaluations:
        return None
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []
    
    # Title
    title_style = ParagraphStyle('CustomTitle', parent=styles['Title'], 
                                fontSize=16, spaceAfter=30, alignment=1)
    story.append(Paragraph(f"RELATÓRIO CONSOLIDADO - {teacher.name.upper()}", title_style))
    story.append(Spacer(1, 20))
    
    # Teacher info
    teacher_info = [
        ['Docente:', teacher.name],
        ['Área:', teacher.area],
        ['Disciplinas:', teacher.subjects or 'Não informado'],
        ['Total de Acompanhamentos:', str(len(evaluations))]
    ]
    
    teacher_table = Table(teacher_info, colWidths=[2*inch, 4*inch])
    teacher_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.grey),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('BACKGROUND', (1, 0), (1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    story.append(teacher_table)
    story.append(Spacer(1, 20))
    
    # Evolution table
    evolution_data = [['Data', 'Curso', 'Planejamento', 'Condução da Aula']]
    
    for eval in evaluations:
        evolution_data.append([
            eval.evaluation_date.strftime("%d/%m/%Y"),
            eval.course.name,
            f"{eval.calculate_planning_percentage()}%",
            f"{eval.calculate_class_percentage()}%"
        ])
    
    evolution_table = Table(evolution_data, colWidths=[1.5*inch, 2*inch, 1.2*inch, 1.3*inch])
    evolution_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])
    ]))
    
    story.append(Paragraph("<b>Evolução dos Acompanhamentos:</b>", styles['Heading3']))
    story.append(evolution_table)
    story.append(Spacer(1, 20))
    
    # Average performance
    avg_planning = sum(eval.calculate_planning_percentage() for eval in evaluations) / len(evaluations)
    avg_class = sum(eval.calculate_class_percentage() for eval in evaluations) / len(evaluations)
    
    avg_data = [
        ['DESEMPENHO MÉDIO', ''],
        ['Planejamento:', f'{avg_planning:.1f}%'],
        ['Condução da aula:', f'{avg_class:.1f}%']
    ]
    
    avg_table = Table(avg_data, colWidths=[2*inch, 4*inch])
    avg_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('BACKGROUND', (0, 1), (0, -1), colors.grey),
        ('TEXTCOLOR', (0, 1), (0, -1), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('BACKGROUND', (1, 1), (1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    story.append(avg_table)
    
    # Footer
    story.append(Spacer(1, 30))
    story.append(Paragraph(f"Relatório gerado em {datetime.now().strftime('%d/%m/%Y às %H:%M')}", 
                          styles['Normal']))
    
    doc.build(story)
    buffer.seek(0)
    return buffer
