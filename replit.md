# Overview

The SENAI Teacher Evaluation System is a web-based platform designed to digitize and streamline the process of teacher evaluation and monitoring in educational institutions. The system replaces paper-based forms with a comprehensive digital solution that allows coordinators to register teacher evaluations, generate automated reports, and track teaching performance over time. Built with Flask and SQLAlchemy, the application provides role-based functionality for managing teachers, courses, evaluators, and detailed evaluation criteria with file attachments and automated email notifications.

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Web Framework Architecture
The application follows the Flask MVC pattern with clear separation of concerns. The main application is configured in `app.py` with extensions for database (SQLAlchemy), email (Flask-Mail), and file uploads. The routing logic is separated into `routes.py`, while business logic utilities are contained in `utils.py`. This modular approach allows for easy maintenance and feature extension.

## Database Design
The system uses SQLAlchemy ORM with a relational database structure supporting four main entities: Teachers (storing personal and professional information), Courses (curriculum components and class details), Evaluators (coordinators and supervisors), and Evaluations (detailed assessment records with foreign key relationships). The database supports both SQLite for development and PostgreSQL for production through environment configuration.

## Form Handling and Validation
Flask-WTF forms provide server-side validation for all user inputs, including teacher registration, course management, evaluator setup, and comprehensive evaluation forms. The forms support file uploads with size restrictions and type validation, ensuring data integrity and security throughout the application.

## File Management System
The application implements secure file upload functionality for evaluation attachments, using UUID-based naming conventions to prevent conflicts and ensure security. Files are stored in a dedicated uploads directory with configurable size limits and type restrictions.

## Report Generation System
The system generates PDF reports using ReportLab, providing both individual teacher evaluations and consolidated institutional reports. Reports include statistical analysis, visual formatting, and can be automatically emailed to relevant stakeholders.

## Frontend Architecture
The user interface is built with Bootstrap 5 and custom CSS for responsive design across devices. JavaScript enhancements provide interactive features like signature capture, auto-save functionality, and dynamic form elements. The template system uses Jinja2 inheritance for consistent layout and maintainable code.

# External Dependencies

## Core Framework Dependencies
- **Flask**: Web framework providing routing, templating, and request handling
- **SQLAlchemy/Flask-SQLAlchemy**: ORM for database operations and model definitions
- **Flask-WTF/WTForms**: Form handling, validation, and CSRF protection
- **Flask-Mail**: Email functionality for automated notifications

## Frontend Libraries
- **Bootstrap 5**: CSS framework for responsive design and UI components
- **Font Awesome**: Icon library for consistent visual elements
- **Custom CSS/JavaScript**: Application-specific styling and interactive features

## Report Generation
- **ReportLab**: PDF generation library for creating formatted evaluation reports
- **Python standard libraries**: DateTime, OS, UUID for utility functions

## File Processing
- **Werkzeug**: Secure filename handling and file upload utilities
- **Python standard libraries**: File system operations and MIME type detection

## Development and Deployment
- **Python 3.x**: Core runtime environment
- **Environment variables**: Configuration management for database URLs, email settings, and security keys
- **WSGI compatibility**: Production deployment support with proxy middleware

## Database Support
- **SQLite**: Development database (default)
- **PostgreSQL**: Production database (configurable via DATABASE_URL)
- **Connection pooling**: Configured for production reliability and performance