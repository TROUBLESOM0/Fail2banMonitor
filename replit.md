# Fail2ban Banned IPs Monitor

## Overview

This is a Flask-based web application that monitors and displays IP addresses banned by Fail2ban in real-time. The application provides a dashboard for system administrators to track security incidents and manage banned IPs across different jails. It features a responsive web interface with automated background updates and integration with abuse reporting services.

![Fail2ban Monitor Dashboard](https://github.com/user-attachments/assets/screenshot-placeholder)
*Current dashboard showing the v1.0.0 interface with custom favicon, version control, and Central Time display*

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Frontend Architecture
- **Technology Stack**: Bootstrap 5 with dark theme, DataTables for tabular data, Font Awesome icons
- **Design Pattern**: Server-side rendered templates with AJAX enhancements
- **Responsive Design**: Mobile-first approach using Bootstrap's grid system
- **Interactive Features**: Real-time data refresh, sortable/searchable tables, clickable IP addresses linking to AbuseIPDB

### Backend Architecture
- **Framework**: Flask web framework with SQLAlchemy ORM
- **Database Layer**: SQLAlchemy with declarative base for model definitions
- **Service Layer**: Dedicated Fail2banService class for system integration
- **Background Processing**: APScheduler for automated IP monitoring tasks
- **Middleware**: ProxyFix for proper header handling in deployed environments

### Data Storage Solutions
- **Primary Database**: SQLite (configurable via DATABASE_URL environment variable)
- **Connection Management**: Connection pooling with health checks and automatic reconnection
- **Schema Design**: BannedIP model with composite indexes for performance optimization
- **Data Retention**: Timestamped records with efficient querying capabilities

### Authentication and Authorization
- **Session Management**: Flask sessions with configurable secret key
- **Security Considerations**: Environment-based configuration for production deployments
- **Access Control**: Currently designed for internal/administrative use

### Background Task Management
- **Scheduler**: BackgroundScheduler for periodic IP list updates
- **Task Isolation**: Application context management for database operations
- **Error Handling**: Comprehensive logging and exception management
- **Lifecycle Management**: Proper scheduler shutdown on application exit

## External Dependencies

### System Integration
- **Fail2ban Client**: Direct integration with fail2ban-client command-line tool
- **Subprocess Management**: Controlled execution with timeout and error handling
- **Service Discovery**: Automatic detection of Fail2ban installation and status

### Third-Party Services
- **AbuseIPDB**: Integration for IP reputation checking and reporting
- **CDN Resources**: Bootstrap CSS/JS, DataTables, Font Awesome from public CDNs

### Development and Deployment
- **Environment Configuration**: DATABASE_URL and SESSION_SECRET environment variables
- **Database Flexibility**: Support for SQLite (default) and PostgreSQL via connection string
- **Logging**: Structured logging with configurable levels
- **Process Management**: WSGI-compatible with proxy header support