/**
 * SENAI Teacher Evaluation System - Main JavaScript
 * Enhanced user experience and form interactions
 */

// Global application state
window.SenaiApp = {
    version: '1.0.0',
    currentUser: null,
    settings: {
        autoSave: false,
        autoSaveInterval: 120000, // 2 minutes
        confirmDelete: true,
        showTooltips: true
    }
};

// Initialize application when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
});

/**
 * Initialize the application
 */
function initializeApp() {
    console.log('Initializing SENAI Teacher Evaluation System v' + SenaiApp.version);
    
    // Initialize tooltips
    initializeTooltips();
    
    // Initialize form enhancements
    initializeFormEnhancements();
    
    // Initialize evaluation form specific features
    if (document.querySelector('.evaluation-form')) {
        initializeEvaluationForm();
    }
    
    // Initialize dashboard features
    if (document.querySelector('#dashboardContent')) {
        initializeDashboard();
    }
    
    // Initialize auto-save if enabled
    if (SenaiApp.settings.autoSave) {
        initializeAutoSave();
    }
    
    // Initialize accessibility features
    initializeAccessibility();
    
    console.log('Application initialized successfully');
}

/**
 * Initialize Bootstrap tooltips
 */
function initializeTooltips() {
    if (!SenaiApp.settings.showTooltips) return;
    
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    const tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

/**
 * Initialize form enhancements
 */
function initializeFormEnhancements() {
    // Add loading states to form submissions
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            const submitBtn = form.querySelector('button[type="submit"]');
            if (submitBtn) {
                submitBtn.classList.add('loading');
                submitBtn.disabled = true;
            }
        });
    });

    // Auto-resize textareas
    const textareas = document.querySelectorAll('textarea');
    textareas.forEach(textarea => {
        autoResizeTextarea(textarea);
        textarea.addEventListener('input', function() {
            autoResizeTextarea(this);
        });
    });

    // Enhanced form validation
    const requiredFields = document.querySelectorAll('input[required], select[required], textarea[required]');
    requiredFields.forEach(field => {
        field.addEventListener('blur', function() {
            validateField(this);
        });
    });
}

/**
 * Initialize evaluation form specific features
 */
function initializeEvaluationForm() {
    console.log('Initializing evaluation form features');
    
    // Add visual feedback for radio button selection
    initializeEvaluationCriteria();
    
    // Initialize progress tracking
    initializeProgressTracking();
    
    // Initialize file upload enhancements
    initializeFileUpload();
    
    // Initialize form navigation
    initializeFormNavigation();
    
    // Initialize course filter for curricular units
    initializeCourseFilter();
}

/**
 * Initialize course filter to dynamically load curricular units
 */
function initializeCourseFilter() {
    const courseSelect = document.getElementById('course_id');
    const unitSelect = document.getElementById('curricular_unit_id');
    
    if (courseSelect && unitSelect) {
        courseSelect.addEventListener('change', function() {
            const courseId = this.value;
            
            // Clear current options
            unitSelect.innerHTML = '<option value="">Carregando...</option>';
            
            if (courseId) {
                fetch(`/api/curricular-units/${courseId}`)
                    .then(response => response.json())
                    .then(data => {
                        unitSelect.innerHTML = '';
                        data.forEach(unit => {
                            const option = document.createElement('option');
                            option.value = unit.id;
                            option.textContent = unit.name;
                            unitSelect.appendChild(option);
                        });
                    })
                    .catch(error => {
                        console.error('Erro ao carregar unidades curriculares:', error);
                        unitSelect.innerHTML = '<option value="0">Erro ao carregar unidades</option>';
                    });
            } else {
                unitSelect.innerHTML = '<option value="0">Selecione um curso primeiro</option>';
            }
        });
    }
}

/**
 * Initialize evaluation criteria interactions
 */
function initializeEvaluationCriteria() {
    const radioButtons = document.querySelectorAll('input[type="radio"]');
    let criteriaData = {
        planning: { total: 0, yes: 0, no: 0, na: 0 },
        classroom: { total: 0, yes: 0, no: 0, na: 0 }
    };
    
    radioButtons.forEach(radio => {
        radio.addEventListener('change', function() {
            const row = this.closest('tr');
            if (row) {
                // Reset row styling
                row.classList.remove('table-success', 'table-danger', 'table-warning');
                
                // Add appropriate styling based on selection
                switch(this.value) {
                    case 'Sim':
                        row.classList.add('table-success');
                        break;
                    case 'Não':
                        row.classList.add('table-danger');
                        break;
                    case 'Não se aplica':
                        row.classList.add('table-warning');
                        break;
                }
                
                // Update progress
                updateCriteriaProgress();
            }
        });
    });

    // Initialize existing selections
    radioButtons.forEach(radio => {
        if (radio.checked) {
            radio.dispatchEvent(new Event('change'));
        }
    });
}

/**
 * Update criteria progress indicators
 */
function updateCriteriaProgress() {
    const planningRadios = document.querySelectorAll('input[name^="planning_"]:checked');
    const classRadios = document.querySelectorAll('input[name^="class_"]:checked');
    
    let planningStats = { total: 0, yes: 0 };
    let classStats = { total: 0, yes: 0 };
    
    // Count planning criteria
    planningRadios.forEach(radio => {
        if (radio.value !== 'Não se aplica') {
            planningStats.total++;
            if (radio.value === 'Sim') {
                planningStats.yes++;
            }
        }
    });
    
    // Count class criteria
    classRadios.forEach(radio => {
        if (radio.value !== 'Não se aplica') {
            classStats.total++;
            if (radio.value === 'Sim') {
                classStats.yes++;
            }
        }
    });
    
    // Update progress bars if they exist
    updateProgressBar('planning', planningStats);
    updateProgressBar('classroom', classStats);
}

/**
 * Update progress bar
 */
function updateProgressBar(section, stats) {
    const progressBar = document.querySelector(`#${section}Progress .progress-bar`);
    if (progressBar && stats.total > 0) {
        const percentage = Math.round((stats.yes / stats.total) * 100);
        progressBar.style.width = percentage + '%';
        progressBar.textContent = percentage + '%';
        
        // Update progress bar color based on percentage
        progressBar.className = 'progress-bar';
        if (percentage >= 80) {
            progressBar.classList.add('bg-success');
        } else if (percentage >= 60) {
            progressBar.classList.add('bg-warning');
        } else {
            progressBar.classList.add('bg-danger');
        }
    }
}

/**
 * Initialize progress tracking
 */
function initializeProgressTracking() {
    // Create progress indicator if it doesn't exist
    const progressContainer = document.createElement('div');
    progressContainer.className = 'progress-container mb-3';
    progressContainer.innerHTML = `
        <div class="row">
            <div class="col-md-6">
                <label class="form-label">Progresso - Planejamento:</label>
                <div id="planningProgress" class="progress">
                    <div class="progress-bar" role="progressbar" style="width: 0%">0%</div>
                </div>
            </div>
            <div class="col-md-6">
                <label class="form-label">Progresso - Condução da Aula:</label>
                <div id="classroomProgress" class="progress">
                    <div class="progress-bar" role="progressbar" style="width: 0%">0%</div>
                </div>
            </div>
        </div>
    `;
    
    // Insert progress container after basic information card
    const basicInfoCard = document.querySelector('.card');
    if (basicInfoCard && !document.querySelector('.progress-container')) {
        basicInfoCard.insertAdjacentElement('afterend', progressContainer);
    }
    
    // Update initial progress
    setTimeout(updateCriteriaProgress, 100);
}

/**
 * Initialize file upload enhancements
 */
function initializeFileUpload() {
    const fileInputs = document.querySelectorAll('input[type="file"]');
    
    fileInputs.forEach(input => {
        input.addEventListener('change', function() {
            const file = this.files[0];
            if (file) {
                // Validate file size (16MB max)
                if (file.size > 16 * 1024 * 1024) {
                    showAlert('Erro: O arquivo deve ter no máximo 16MB.', 'danger');
                    this.value = '';
                    return;
                }
                
                // Validate file type
                const allowedTypes = ['image/jpeg', 'image/png', 'application/pdf', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'];
                if (!allowedTypes.includes(file.type)) {
                    showAlert('Erro: Tipo de arquivo não permitido. Use JPG, PNG, PDF, DOC ou DOCX.', 'danger');
                    this.value = '';
                    return;
                }
                
                // Show file info
                const fileInfo = document.createElement('div');
                fileInfo.className = 'file-info mt-2';
                fileInfo.innerHTML = `
                    <small class="text-success">
                        <i class="fas fa-check-circle me-1"></i>
                        Arquivo selecionado: ${file.name} (${formatFileSize(file.size)})
                    </small>
                `;
                
                // Remove previous file info
                const existingInfo = this.parentNode.querySelector('.file-info');
                if (existingInfo) {
                    existingInfo.remove();
                }
                
                this.parentNode.appendChild(fileInfo);
            }
        });
    });
}

/**
 * Initialize form navigation
 */
function initializeFormNavigation() {
    // Add smooth scrolling to form sections
    const sectionLinks = document.querySelectorAll('a[href^="#"]');
    sectionLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
        });
    });
}

/**
 * Initialize dashboard features
 */
function initializeDashboard() {
    console.log('Initializing dashboard features');
    
    // Initialize charts if Chart.js is available
    if (typeof Chart !== 'undefined') {
        initializeDashboardCharts();
    }
    
    // Initialize dashboard cards animations
    const cards = document.querySelectorAll('.card');
    cards.forEach((card, index) => {
        card.style.animationDelay = (index * 0.1) + 's';
        card.classList.add('fade-in');
    });
}

/**
 * Initialize dashboard charts
 */
function initializeDashboardCharts() {
    // This function is called by the template scripts
    // Additional chart configurations can be added here
}

/**
 * Initialize auto-save functionality
 */
function initializeAutoSave() {
    if (!SenaiApp.settings.autoSave) return;
    
    console.log('Auto-save enabled with interval:', SenaiApp.settings.autoSaveInterval);
    
    setInterval(() => {
        const form = document.querySelector('form[method="POST"]');
        if (form && !form.classList.contains('no-autosave')) {
            autoSaveForm(form);
        }
    }, SenaiApp.settings.autoSaveInterval);
}

/**
 * Auto-save form data
 */
function autoSaveForm(form) {
    const formData = new FormData(form);
    const data = {};
    
    for (let [key, value] of formData.entries()) {
        data[key] = value;
    }
    
    // Save to localStorage
    const saveKey = 'senai_autosave_' + form.getAttribute('action');
    localStorage.setItem(saveKey, JSON.stringify(data));
    
    // Show auto-save indicator
    showAutoSaveIndicator();
}

/**
 * Show auto-save indicator
 */
function showAutoSaveIndicator() {
    const indicator = document.createElement('div');
    indicator.className = 'autosave-indicator';
    indicator.innerHTML = '<i class="fas fa-cloud-upload-alt me-1"></i>Salvo automaticamente';
    indicator.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: var(--bs-success);
        color: white;
        padding: 8px 16px;
        border-radius: 4px;
        z-index: 9999;
        font-size: 0.875rem;
        opacity: 0;
        transition: opacity 0.3s ease;
    `;
    
    document.body.appendChild(indicator);
    
    // Animate in
    setTimeout(() => {
        indicator.style.opacity = '1';
    }, 100);
    
    // Remove after 3 seconds
    setTimeout(() => {
        indicator.style.opacity = '0';
        setTimeout(() => {
            indicator.remove();
        }, 300);
    }, 3000);
}

/**
 * Initialize accessibility features
 */
function initializeAccessibility() {
    // Add skip to content link
    const skipLink = document.createElement('a');
    skipLink.href = '#main-content';
    skipLink.className = 'skip-to-content';
    skipLink.textContent = 'Pular para o conteúdo principal';
    document.body.insertBefore(skipLink, document.body.firstChild);
    
    // Add main content ID if it doesn't exist
    const mainContent = document.querySelector('main');
    if (mainContent && !mainContent.id) {
        mainContent.id = 'main-content';
    }
    
    // Enhance keyboard navigation
    const focusableElements = document.querySelectorAll('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])');
    focusableElements.forEach(element => {
        element.addEventListener('keydown', function(e) {
            // Add custom keyboard shortcuts here if needed
        });
    });
}

/**
 * Utility Functions
 */

/**
 * Auto-resize textarea based on content
 */
function autoResizeTextarea(textarea) {
    textarea.style.height = 'auto';
    textarea.style.height = textarea.scrollHeight + 'px';
}

/**
 * Validate form field
 */
function validateField(field) {
    const isValid = field.checkValidity();
    
    // Remove existing validation classes
    field.classList.remove('is-valid', 'is-invalid');
    
    // Add appropriate validation class
    if (isValid) {
        field.classList.add('is-valid');
    } else {
        field.classList.add('is-invalid');
    }
    
    return isValid;
}

/**
 * Format file size
 */
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
}

/**
 * Show alert message
 */
function showAlert(message, type = 'info', duration = 5000) {
    const alertContainer = document.querySelector('.container') || document.body;
    const alert = document.createElement('div');
    alert.className = `alert alert-${type} alert-dismissible fade show`;
    alert.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    alertContainer.insertBefore(alert, alertContainer.firstChild);
    
    // Auto-dismiss after duration
    if (duration > 0) {
        setTimeout(() => {
            alert.classList.remove('show');
            setTimeout(() => alert.remove(), 150);
        }, duration);
    }
}

/**
 * Confirm action with custom message
 */
function confirmAction(message, callback) {
    if (SenaiApp.settings.confirmDelete) {
        if (confirm(message)) {
            callback();
        }
    } else {
        callback();
    }
}

/**
 * Show loading overlay
 */
function showLoading(element = document.body) {
    const overlay = document.createElement('div');
    overlay.className = 'loading-overlay';
    overlay.innerHTML = `
        <div class="spinner-border text-primary" role="status">
            <span class="visually-hidden">Carregando...</span>
        </div>
    `;
    overlay.style.cssText = `
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: rgba(0, 0, 0, 0.5);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 9999;
    `;
    
    element.style.position = 'relative';
    element.appendChild(overlay);
}

/**
 * Hide loading overlay
 */
function hideLoading(element = document.body) {
    const overlay = element.querySelector('.loading-overlay');
    if (overlay) {
        overlay.remove();
    }
}

/**
 * Export functions for global use
 */
window.SenaiApp.utils = {
    autoResizeTextarea,
    validateField,
    formatFileSize,
    showAlert,
    confirmAction,
    showLoading,
    hideLoading
};

/**
 * Handle form submissions with loading states
 */
document.addEventListener('submit', function(e) {
    const form = e.target;
    if (form.tagName === 'FORM') {
        showLoading(form);
    }
});

/**
 * Handle page unload to clean up
 */
window.addEventListener('beforeunload', function() {
    // Clean up any running intervals or timeouts
    console.log('Cleaning up SENAI application');
});

/**
 * Error handling
 */
window.addEventListener('error', function(e) {
    console.error('Application error:', e.error);
    showAlert('Ocorreu um erro inesperado. Tente recarregar a página.', 'danger');
});

// Service Worker registration for offline support (if needed)
if ('serviceWorker' in navigator) {
    window.addEventListener('load', function() {
        // Service worker registration can be added here for offline functionality
    });
}

console.log('SENAI Teacher Evaluation System JavaScript loaded successfully');
