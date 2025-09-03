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
import pandas as pd
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils.dataframe import dataframe_to_rows

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
        ['Data:', evaluation.evaluation_date.strftime("%d/%m/%Y")]
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

def generate_teachers_excel_template():
    """Generate Excel template for teacher import"""
    buffer = BytesIO()
    
    # Create sample data with headers
    data = {
        'Nome': ['João Silva', 'Maria Santos'],
        'Área': ['Eletrônica', 'Informática'],
        'Disciplinas': ['Eletrônica Digital, Circuitos Elétricos', 'Programação, Banco de Dados'],
        'Carga Horária': [40, 30],
        'Email': ['joao.silva@senai.br', 'maria.santos@senai.br'],
        'Telefone': ['11987654321', '11876543210'],
        'Observações': ['Excelente didática, pontual', 'Muito dedicada, inovadora'],
        'Cursos': ['Técnico em Eletrônica, Técnico em Automação', 'Técnico em Informática']
    }
    
    df = pd.DataFrame(data)
    
    # Create workbook and worksheet
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Docentes"
    
    # Add header row
    for r in dataframe_to_rows(df, index=False, header=True):
        ws.append(r)
    
    # Style the header row
    header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
    header_font = Font(color="FFFFFF", bold=True)
    
    for cell in ws[1]:
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center")
    
    # Auto-adjust column widths
    for column in ws.columns:
        max_length = 0
        column_letter = column[0].column_letter
        for cell in column:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except:
                pass
        adjusted_width = min(max_length + 2, 50)
        ws.column_dimensions[column_letter].width = adjusted_width
    
    # Add instructions sheet
    instructions_ws = wb.create_sheet("Instruções")
    instructions = [
        ["INSTRUÇÕES PARA IMPORTAÇÃO DE DOCENTES"],
        [""],
        ["1. Preencha os dados dos docentes na aba 'Docentes'"],
        ["2. Campos obrigatórios: Nome, Área"],
        ["3. Disciplinas: separe por vírgula (ex: Matemática, Física)"],
        ["4. Cursos: separe por vírgula os nomes dos cursos que o docente ministra"],
        ["5. Carga Horária: número de horas por semana"],
        ["6. Email: formato válido (ex: nome@senai.br)"],
        ["7. Telefone: apenas números (ex: 11987654321)"],
        ["8. Observações: informações adicionais sobre o docente"],
        [""],
        ["IMPORTANTE:"],
        ["- Não altere os nomes das colunas"],
        ["- Mantenha o formato Excel (.xlsx)"],
        ["- Remova as linhas de exemplo antes de importar seus dados"],
        ["- Os cursos mencionados devem estar previamente cadastrados no sistema"],
    ]
    
    for row in instructions:
        instructions_ws.append(row)
    
    # Style instructions
    instructions_ws['A1'].font = Font(bold=True, size=14)
    instructions_ws['A1'].fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
    instructions_ws['A1'].font = Font(color="FFFFFF", bold=True, size=14)
    
    for i in range(11, 16):  # Important section
        instructions_ws[f'A{i}'].font = Font(bold=True)
    
    # Auto-adjust column width for instructions
    for column in instructions_ws.columns:
        max_length = 0
        column_letter = column[0].column_letter
        for cell in column:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except:
                pass
        adjusted_width = min(max_length + 2, 80)
        instructions_ws.column_dimensions[column_letter].width = adjusted_width
    
    # Save to buffer
    wb.save(buffer)
    buffer.seek(0)
    return buffer

def process_teachers_excel_import(file_path):
    """Process Excel file and import teachers"""
    from models import Teacher, Course
    from app import db
    
    try:
        # Read Excel file
        df = pd.read_excel(file_path, sheet_name='Docentes')
        
        # Clean column names
        df.columns = df.columns.str.strip()
        
        results = {
            'success': 0,
            'errors': [],
            'warnings': []
        }
        
        for index, row in df.iterrows():
            try:
                # Skip empty rows
                if pd.isna(row.get('Nome', '')) or str(row.get('Nome', '')).strip() == '':
                    continue
                
                # Extract data with defaults
                name = str(row['Nome']).strip()
                area = str(row.get('Área', '')).strip() if not pd.isna(row.get('Área')) else ''
                subjects = str(row.get('Disciplinas', '')).strip() if not pd.isna(row.get('Disciplinas')) else ''
                
                # Handle workload conversion safely
                workload_raw = row.get('Carga Horária', '')
                workload = None
                if not pd.isna(workload_raw) and str(workload_raw).strip():
                    try:
                        workload = int(float(str(workload_raw)))
                    except (ValueError, TypeError):
                        pass
                
                email = str(row.get('Email', '')).strip() if not pd.isna(row.get('Email')) else ''
                phone = str(row.get('Telefone', '')).strip() if not pd.isna(row.get('Telefone')) else ''
                observations = str(row.get('Observações', '')).strip() if not pd.isna(row.get('Observações')) else ''
                courses_str = str(row.get('Cursos', '')).strip() if not pd.isna(row.get('Cursos')) else ''
                
                # Validate required fields
                if not name:
                    results['errors'].append(f'Linha {index + 2}: Nome é obrigatório')
                    continue
                
                if not area:
                    results['errors'].append(f'Linha {index + 2}: Área é obrigatória')
                    continue
                
                # Check if teacher already exists
                existing_teacher = Teacher.query.filter_by(name=name).first()
                if existing_teacher:
                    results['warnings'].append(f'Linha {index + 2}: Docente "{name}" já existe, pulando...')
                    continue
                
                # Create new teacher
                teacher = Teacher(
                    name=name,
                    area=area,
                    subjects=subjects,
                    workload=workload if workload and workload > 0 else None,
                    email=email if email and '@' in email else None,
                    phone=phone if phone else None,
                    observations=observations if observations else None
                )
                
                db.session.add(teacher)
                db.session.flush()  # Get teacher ID before commit
                
                # Process courses if provided
                if courses_str:
                    course_names = [c.strip() for c in courses_str.split(',') if c.strip()]
                    for course_name in course_names:
                        course = Course.query.filter_by(name=course_name).first()
                        if not course:
                            results['warnings'].append(f'Linha {index + 2}: Curso "{course_name}" não encontrado para o docente "{name}"')
                
                results['success'] += 1
                
            except Exception as e:
                results['errors'].append(f'Linha {index + 2}: Erro ao processar - {str(e)}')
        
        # Commit all changes
        if results['success'] > 0:
            db.session.commit()
        
        return results
        
    except Exception as e:
        db.session.rollback()
        return {
            'success': 0,
            'errors': [f'Erro ao processar arquivo Excel: {str(e)}'],
            'warnings': []
        }

def generate_courses_excel_template():
    """Generate Excel template for course import"""
    buffer = BytesIO()
    
    # Create sample data with headers
    data = {
        'Nome': ['Técnico em Eletrônica', 'Técnico em Informática'],
        'Período': ['1° Sem/25', '2° Sem/25'],
        'Componente Curricular': ['Eletrônica Digital', 'Programação Web'],
        'Código da Turma': ['ELT001', 'INF002']
    }
    
    df = pd.DataFrame(data)
    
    # Create workbook and worksheet
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Cursos"
    
    # Add header row
    for r in dataframe_to_rows(df, index=False, header=True):
        ws.append(r)
    
    # Style the header row
    header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
    header_font = Font(color="FFFFFF", bold=True)
    
    for cell in ws[1]:
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center")
    
    # Auto-adjust column widths
    for column in ws.columns:
        max_length = 0
        column_letter = column[0].column_letter
        for cell in column:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except:
                pass
        adjusted_width = min(max_length + 2, 50)
        ws.column_dimensions[column_letter].width = adjusted_width
    
    # Add instructions sheet
    instructions_ws = wb.create_sheet("Instruções")
    instructions = [
        ["INSTRUÇÕES PARA IMPORTAÇÃO DE CURSOS"],
        [""],
        ["1. Preencha os dados dos cursos na aba 'Cursos'"],
        ["2. Campos obrigatórios: Nome, Período, Componente Curricular"],
        ["3. Nome: nome completo do curso (ex: Técnico em Eletrônica)"],
        ["4. Período: período letivo (ex: 1° Sem/25, 2° Sem/25)"],
        ["5. Componente Curricular: disciplina específica"],
        ["6. Código da Turma: código identificador da turma (opcional)"],
        [""],
        ["IMPORTANTE:"],
        ["- Não altere os nomes das colunas"],
        ["- Mantenha o formato Excel (.xlsx)"],
        ["- Remova as linhas de exemplo antes de importar seus dados"],
        ["- Evite duplicação de cursos com mesmo nome e período"],
    ]
    
    for row in instructions:
        instructions_ws.append(row)
    
    # Style instructions
    instructions_ws['A1'].font = Font(bold=True, size=14)
    instructions_ws['A1'].fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
    instructions_ws['A1'].font = Font(color="FFFFFF", bold=True, size=14)
    
    for i in range(10, 14):  # Important section
        instructions_ws[f'A{i}'].font = Font(bold=True)
    
    # Auto-adjust column width for instructions
    for column in instructions_ws.columns:
        max_length = 0
        column_letter = column[0].column_letter
        for cell in column:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except:
                pass
        adjusted_width = min(max_length + 2, 80)
        instructions_ws.column_dimensions[column_letter].width = adjusted_width
    
    # Save to buffer
    wb.save(buffer)
    buffer.seek(0)
    return buffer

def process_courses_excel_import(file_path):
    """Process Excel file and import courses"""
    from models import Course
    from app import db
    
    try:
        # Read Excel file
        df = pd.read_excel(file_path, sheet_name='Cursos')
        
        # Clean column names
        df.columns = df.columns.str.strip()
        
        results = {
            'success': 0,
            'errors': [],
            'warnings': []
        }
        
        for index, row in df.iterrows():
            try:
                # Skip empty rows
                if pd.isna(row.get('Nome', '')) or str(row.get('Nome', '')).strip() == '':
                    continue
                
                # Extract data with defaults
                name = str(row['Nome']).strip()
                period = str(row.get('Período', '')).strip() if not pd.isna(row.get('Período')) else ''
                curriculum_component = str(row.get('Componente Curricular', '')).strip() if not pd.isna(row.get('Componente Curricular')) else ''
                class_code = str(row.get('Código da Turma', '')).strip() if not pd.isna(row.get('Código da Turma')) else ''
                
                # Validate required fields
                if not name:
                    results['errors'].append(f'Linha {index + 2}: Nome é obrigatório')
                    continue
                
                if not period:
                    results['errors'].append(f'Linha {index + 2}: Período é obrigatório')
                    continue
                
                if not curriculum_component:
                    results['errors'].append(f'Linha {index + 2}: Componente Curricular é obrigatório')
                    continue
                
                # Check if course already exists (same name and period)
                existing_course = Course.query.filter_by(name=name, period=period).first()
                if existing_course:
                    results['warnings'].append(f'Linha {index + 2}: Curso "{name}" no período "{period}" já existe, pulando...')
                    continue
                
                # Create new course
                course = Course(
                    name=name,
                    period=period,
                    curriculum_component=curriculum_component,
                    class_code=class_code if class_code else None
                )
                
                db.session.add(course)
                results['success'] += 1
                
            except Exception as e:
                results['errors'].append(f'Linha {index + 2}: Erro ao processar - {str(e)}')
        
        # Commit all changes
        if results['success'] > 0:
            db.session.commit()
        
        return results
        
    except Exception as e:
        db.session.rollback()
        return {
            'success': 0,
            'errors': [f'Erro ao processar arquivo Excel: {str(e)}'],
            'warnings': []
        }

def generate_curricular_units_excel_template():
    """Generate Excel template for curricular units import"""
    from io import BytesIO
    import pandas as pd
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment
    from openpyxl.utils.dataframe import dataframe_to_rows
    
    buffer = BytesIO()
    
    # Create sample data with headers
    data = {
        "Nome": ["Eletrônica Digital I", "Programação Web I", "Circuitos Elétricos"],
        "Código": ["ELD001", "PWB001", "CEL001"],
        "Curso": ["Técnico em Eletrônica", "Técnico em Informática", "Técnico em Eletrônica"],
        "Carga Horária": [80, 60, 120],
        "Descrição": ["Fundamentos de eletrônica digital", "Desenvolvimento de páginas web", "Conceitos básicos de circuitos elétricos"]
    }
    
    df = pd.DataFrame(data)
    
    # Create workbook and worksheet
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Unidades Curriculares"
    
    # Add header row
    for r in dataframe_to_rows(df, index=False, header=True):
        ws.append(r)
    
    # Style the header row
    header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
    header_font = Font(color="FFFFFF", bold=True)
    
    for cell in ws[1]:
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center")
    
    # Save to buffer
    wb.save(buffer)
    buffer.seek(0)
    return buffer

def process_curricular_units_excel_import(file_path):
    """Process Excel file and import curricular units"""
    import pandas as pd
    from models import CurricularUnit, Course
    from app import db
    
    try:
        # Read Excel file
        df = pd.read_excel(file_path, sheet_name="Unidades Curriculares")
        
        results = {
            "success": 0,
            "errors": [],
            "warnings": []
        }
        
        for index, row in df.iterrows():
            try:
                # Skip empty rows
                if pd.isna(row.get("Nome", "")) or str(row.get("Nome", "")).strip() == "":
                    continue
                
                # Extract data
                name = str(row["Nome"]).strip()
                code = str(row.get("Código", "")).strip() if not pd.isna(row.get("Código")) else ""
                course_name = str(row.get("Curso", "")).strip() if not pd.isna(row.get("Curso")) else ""
                description = str(row.get("Descrição", "")).strip() if not pd.isna(row.get("Descrição")) else ""
                
                # Validate required fields
                if not name:
                    results["errors"].append(f"Linha {index + 2}: Nome é obrigatório")
                    continue
                
                if not course_name:
                    results["errors"].append(f"Linha {index + 2}: Curso é obrigatório")
                    continue
                
                # Find course
                course = Course.query.filter_by(name=course_name).first()
                if not course:
                    results["errors"].append(f"Linha {index + 2}: Curso \"{course_name}\" não encontrado")
                    continue
                
                # Check if curricular unit already exists
                existing_unit = CurricularUnit.query.filter_by(name=name, course_id=course.id).first()
                if existing_unit:
                    results["warnings"].append(f"Linha {index + 2}: Unidade curricular \"{name}\" já existe para o curso \"{course_name}\", pulando...")
                    continue
                
                # Create new curricular unit
                unit = CurricularUnit(
                    name=name,
                    code=code if code else None,
                    course_id=course.id,
                    description=description if description else None,
                    is_active=True
                )
                
                db.session.add(unit)
                results["success"] += 1
                
            except Exception as e:
                results["errors"].append(f"Linha {index + 2}: Erro ao processar - {str(e)}")
        
        # Commit all changes
        if results["success"] > 0:
            db.session.commit()
        
        return results
        
    except Exception as e:
        db.session.rollback()
        return {
            "success": 0,
            "errors": [f"Erro ao processar arquivo Excel: {str(e)}"],
            "warnings": []
        }

