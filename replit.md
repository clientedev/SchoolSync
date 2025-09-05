# Sistema de Ação Docente SENAI Morvan Figueiredo

## Overview

This is a web-based teacher evaluation and monitoring system designed for SENAI Morvan Figueiredo educational institution. The system digitizes the traditional paper-based teacher evaluation process, providing a comprehensive platform for coordinators to register, track, and analyze teaching performance. The application supports teacher evaluation workflows, automatic report generation, user management with role-based access control, and digital signature capabilities for evaluation approvals.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Frontend Architecture
The application uses a server-side rendered architecture built with Flask and Jinja2 templates. The frontend follows a Bootstrap 5 dark theme design system with Font Awesome icons for consistent UI elements. The template structure includes a base template hierarchy with specialized templates for different user roles (admin/evaluator vs teacher). Custom CSS and JavaScript enhance the user experience with features like signature capture, form validation, and responsive design optimized for tablets and mobile devices.

### Backend Architecture  
The system is built using Flask as the web framework with SQLAlchemy ORM for database operations. The architecture follows a traditional MVC pattern with clear separation of concerns:
- **Models**: Define database entities for users, teachers, courses, evaluations, etc.
- **Routes**: Handle HTTP requests and business logic
- **Forms**: WTForms for form validation and rendering
- **Utils**: Utility functions for file handling, report generation, and email services

The application supports both development and production configurations, with the production setup optimized for Railway deployment using Gunicorn as the WSGI server.

### Data Storage Solutions
The system uses PostgreSQL as the primary database in production with SQLite fallback for development. Database schema includes entities for:
- User management (User model with role-based access)
- Teacher profiles (Teacher model with NIF identification)
- Course and curricular unit management
- Evaluation records with comprehensive criteria tracking
- Digital signatures and file attachments
- Semester management for academic periods

Connection pooling and proper database optimization are implemented for production environments.

### Authentication and Authorization
Flask-Login handles user session management with role-based access control implemented through three user roles:
- **Admin**: Full system access including user management
- **Evaluator**: Can create and manage evaluations, generate reports
- **Teacher**: Read-only access to their own evaluation records

Password hashing uses Werkzeug's security utilities, and sessions are managed with secure secret keys. Teachers can be linked to user accounts for portal access.

## External Dependencies

### Core Framework Dependencies
- **Flask**: Web framework with extensions for SQLAlchemy, Mail, Login, and WTF forms
- **PostgreSQL/SQLite**: Database systems with psycopg2 for PostgreSQL connectivity
- **Gunicorn**: Production WSGI server for Railway deployment

### UI and Frontend Libraries
- **Bootstrap 5**: CSS framework with dark theme implementation
- **Font Awesome**: Icon library for consistent UI elements
- **Jinja2**: Template engine for server-side rendering

### Document Generation and Processing
- **ReportLab**: PDF generation for evaluation reports and consolidated analytics
- **Pandas**: Excel file processing for bulk data imports/exports
- **Openpyxl**: Excel file manipulation for template downloads

### Email and Communication
- **Flask-Mail**: Email service integration for sending evaluation notifications and reports to teachers

### File Handling
- **Werkzeug**: Secure filename handling and file upload processing
- File upload system supports evaluation attachments with 16MB size limits

### Deployment Platform
- **Railway**: Cloud hosting platform with automated deployment via railway.json configuration
- ProxyFix middleware for proper header handling behind Railway's proxy

The system is designed to reduce paper usage, increase evaluation efficiency, and provide comprehensive analytics for educational quality improvement at SENAI Morvan Figueiredo.