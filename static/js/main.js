/**
 * Multi-Plant Document Management System - Main JavaScript
 */

// Global variables
let csrfToken = null;

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Get CSRF token from meta tag if available
    const csrfMeta = document.querySelector('meta[name="csrf-token"]');
    if (csrfMeta) {
        csrfToken = csrfMeta.getAttribute('content');
    }
    
    // Initialize tooltips
    initializeTooltips();
    
    // Initialize file upload drag and drop
    initializeFileUpload();
    
    // Initialize form validation
    initializeFormValidation();
    
    // Initialize auto-save functionality
    initializeAutoSave();
});

/**
 * Initialize Bootstrap tooltips
 */
function initializeTooltips() {
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

/**
 * Initialize file upload with drag and drop
 */
function initializeFileUpload() {
    const fileInput = document.getElementById('file');
    const uploadArea = document.querySelector('.file-upload-area');
    
    if (fileInput && uploadArea) {
        // Drag and drop events
        uploadArea.addEventListener('dragover', function(e) {
            e.preventDefault();
            uploadArea.classList.add('dragover');
        });
        
        uploadArea.addEventListener('dragleave', function(e) {
            e.preventDefault();
            uploadArea.classList.remove('dragover');
        });
        
        uploadArea.addEventListener('drop', function(e) {
            e.preventDefault();
            uploadArea.classList.remove('dragover');
            
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                fileInput.files = files;
                updateFilePreview(files[0]);
            }
        });
        
        // Click to upload
        uploadArea.addEventListener('click', function() {
            fileInput.click();
        });
        
        // File input change
        fileInput.addEventListener('change', function(e) {
            if (e.target.files.length > 0) {
                updateFilePreview(e.target.files[0]);
            }
        });
    }
}

/**
 * Update file preview
 */
function updateFilePreview(file) {
    const preview = document.getElementById('filePreview');
    if (preview) {
        const fileIcon = getFileIcon(file.type);
        const fileSize = formatFileSize(file.size);
        
        preview.innerHTML = `
            <div class="d-flex align-items-center">
                <i class="${fileIcon} me-2"></i>
                <div>
                    <div class="fw-bold">${file.name}</div>
                    <small class="text-muted">${fileSize}</small>
                </div>
            </div>
        `;
        preview.style.display = 'block';
    }
}

/**
 * Get file icon based on MIME type
 */
function getFileIcon(mimeType) {
    if (mimeType.includes('pdf')) return 'fas fa-file-pdf text-danger';
    if (mimeType.includes('word')) return 'fas fa-file-word text-primary';
    if (mimeType.includes('excel') || mimeType.includes('spreadsheet')) return 'fas fa-file-excel text-success';
    if (mimeType.includes('powerpoint') || mimeType.includes('presentation')) return 'fas fa-file-powerpoint text-warning';
    if (mimeType.includes('image')) return 'fas fa-file-image text-info';
    return 'fas fa-file text-muted';
}

/**
 * Format file size
 */
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

/**
 * Initialize form validation
 */
function initializeFormValidation() {
    const forms = document.querySelectorAll('.needs-validation');
    
    Array.from(forms).forEach(form => {
        form.addEventListener('submit', function(event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        });
    });
}

/**
 * Initialize auto-save functionality
 */
function initializeAutoSave() {
    const autoSaveForms = document.querySelectorAll('[data-auto-save]');
    
    autoSaveForms.forEach(form => {
        const inputs = form.querySelectorAll('input, textarea, select');
        let saveTimeout;
        
        inputs.forEach(input => {
            input.addEventListener('input', function() {
                clearTimeout(saveTimeout);
                saveTimeout = setTimeout(() => {
                    autoSaveForm(form);
                }, 2000); // Auto-save after 2 seconds of inactivity
            });
        });
    });
}

/**
 * Auto-save form data
 */
function autoSaveForm(form) {
    const formData = new FormData(form);
    const autoSaveUrl = form.getAttribute('data-auto-save');
    
    if (autoSaveUrl) {
        fetch(autoSaveUrl, {
            method: 'POST',
            body: formData,
            headers: {
                'X-CSRFToken': csrfToken
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showNotification('Auto-saved successfully', 'success');
            }
        })
        .catch(error => {
            console.error('Auto-save error:', error);
        });
    }
}

/**
 * Show notification
 */
function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
    notification.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
    notification.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    document.body.appendChild(notification);
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
        if (notification.parentNode) {
            notification.remove();
        }
    }, 5000);
}

/**
 * Confirm dialog
 */
function confirmDialog(message, callback) {
    if (confirm(message)) {
        callback();
    }
}

/**
 * Loading state management
 */
function setLoadingState(element, loading = true) {
    if (loading) {
        element.disabled = true;
        element.classList.add('loading');
        const originalText = element.innerHTML;
        element.setAttribute('data-original-text', originalText);
        element.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Loading...';
    } else {
        element.disabled = false;
        element.classList.remove('loading');
        const originalText = element.getAttribute('data-original-text');
        if (originalText) {
            element.innerHTML = originalText;
            element.removeAttribute('data-original-text');
        }
    }
}

/**
 * API helper functions
 */
const API = {
    /**
     * Make API request
     */
    request: async function(url, options = {}) {
        const defaultOptions = {
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            }
        };
        
        const mergedOptions = { ...defaultOptions, ...options };
        if (mergedOptions.body && typeof mergedOptions.body === 'object') {
            mergedOptions.body = JSON.stringify(mergedOptions.body);
        }
        
        try {
            const response = await fetch(url, mergedOptions);
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.error || 'API request failed');
            }
            
            return data;
        } catch (error) {
            console.error('API request error:', error);
            throw error;
        }
    },
    
    /**
     * Get documents
     */
    getDocuments: function(params = {}) {
        const queryString = new URLSearchParams(params).toString();
        return this.request(`/api/documents?${queryString}`);
    },
    
    /**
     * Upload document
     */
    uploadDocument: function(formData) {
        return this.request('/documents/upload', {
            method: 'POST',
            body: formData,
            headers: {
                'X-CSRFToken': csrfToken
            }
        });
    },
    
    /**
     * Delete document
     */
    deleteDocument: function(documentId) {
        return this.request(`/documents/${documentId}`, {
            method: 'DELETE'
        });
    }
};

/**
 * Search functionality
 */
function initializeSearch() {
    const searchInput = document.getElementById('search');
    const searchForm = document.getElementById('filterForm');
    
    if (searchInput && searchForm) {
        let searchTimeout;
        
        searchInput.addEventListener('input', function() {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {
                searchForm.submit();
            }, 500); // Search after 500ms of inactivity
        });
    }
}

/**
 * Auto-submit filter form on change
 */
function initializeFilterForm() {
    const filterForm = document.getElementById('filterForm');
    if (filterForm) {
        const plantSelect = document.getElementById('plant_id');
        const departmentSelect = document.getElementById('department_id');

        const submitForm = () => {
            filterForm.submit();
        };

        if (plantSelect) {
            plantSelect.addEventListener('change', submitForm);
        }
        if (departmentSelect) {
            departmentSelect.addEventListener('change', submitForm);
        }
    }
}

/**
 * Initialize search on page load
 */
document.addEventListener('DOMContentLoaded', function() {
    initializeSearch();
    initializeFilterForm();
});

/**
 * Utility functions
 */
const Utils = {
    /**
     * Debounce function
     */
    debounce: function(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    },
    
    /**
     * Format date
     */
    formatDate: function(date) {
        return new Date(date).toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    },
    
    /**
     * Copy to clipboard
     */
    copyToClipboard: function(text) {
        navigator.clipboard.writeText(text).then(() => {
            showNotification('Copied to clipboard', 'success');
        }).catch(() => {
            showNotification('Failed to copy to clipboard', 'danger');
        });
    }
};

// Export for use in other scripts
window.DMS = {
    API,
    Utils,
    showNotification,
    confirmDialog,
    setLoadingState
};
