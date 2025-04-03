// Main JavaScript file

document.addEventListener('DOMContentLoaded', function() {
    // Enable tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Alert auto-close
    setTimeout(function() {
        $('.alert').alert('close');
    }, 5000);
    
    // Setup AJAX CSRF token
    setupAjaxCSRF();
    
    // Initialize any charts
    initializeCharts();
});

// AJAX CSRF Token Setup
function setupAjaxCSRF() {
    // Get CSRF token from meta tag
    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
    
    if (csrfToken) {
        // Set up AJAX CSRF token for jQuery
        $.ajaxSetup({
            beforeSend: function(xhr, settings) {
                if (!/^(GET|HEAD|OPTIONS|TRACE)$/i.test(settings.type) && !this.crossDomain) {
                    xhr.setRequestHeader("X-CSRFToken", csrfToken);
                }
            }
        });
    }
}

// Initialize Chart.js charts
function initializeCharts() {
    // Look for chart canvases
    const chartElements = document.querySelectorAll('.chart-canvas');
    
    if (!chartElements.length) {
        return;
    }
    
    // Check if Chart.js is loaded
    if (typeof Chart === 'undefined') {
        console.warn('Chart.js not loaded');
        return;
    }
    
    // Set default chart colors
    Chart.defaults.color = '#666';
    Chart.defaults.borderColor = 'rgba(0, 0, 0, 0.1)';
    
    // Common chart options
    const commonOptions = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: {
                position: 'top',
            },
            tooltip: {
                mode: 'index',
                intersect: false,
            }
        }
    };
    
    // Process each chart element
    chartElements.forEach(function(canvas) {
        const ctx = canvas.getContext('2d');
        const chartType = canvas.getAttribute('data-chart-type') || 'line';
        const chartData = JSON.parse(canvas.getAttribute('data-chart-data') || '{}');
        
        // Create chart
        new Chart(ctx, {
            type: chartType,
            data: chartData,
            options: commonOptions
        });
    });
}

// API Helper Functions
const API = {
    get: function(endpoint, successCallback, errorCallback) {
        $.ajax({
            url: endpoint,
            type: 'GET',
            dataType: 'json',
            success: function(response) {
                if (response.success) {
                    if (successCallback) successCallback(response.data);
                } else {
                    if (errorCallback) errorCallback(response.message);
                }
            },
            error: function(xhr) {
                const errorMsg = xhr.responseJSON?.message || 'An error occurred';
                if (errorCallback) errorCallback(errorMsg);
            }
        });
    },
    
    post: function(endpoint, data, successCallback, errorCallback) {
        $.ajax({
            url: endpoint,
            type: 'POST',
            contentType: 'application/json',
            data: JSON.stringify(data),
            dataType: 'json',
            success: function(response) {
                if (response.success) {
                    if (successCallback) successCallback(response.data, response.message);
                } else {
                    if (errorCallback) errorCallback(response.message);
                }
            },
            error: function(xhr) {
                const errorMsg = xhr.responseJSON?.message || 'An error occurred';
                if (errorCallback) errorCallback(errorMsg);
            }
        });
    }
};

// Utility Functions
function showNotification(message, type = 'success') {
    const alertHtml = `
        <div class="alert alert-${type} alert-dismissible fade show notification-alert">
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        </div>
    `;
    
    const alertContainer = document.querySelector('.notification-container');
    if (alertContainer) {
        alertContainer.innerHTML += alertHtml;
    } else {
        const newContainer = document.createElement('div');
        newContainer.className = 'notification-container position-fixed top-0 end-0 p-3';
        newContainer.style.zIndex = 1050;
        newContainer.innerHTML = alertHtml;
        document.body.appendChild(newContainer);
    }
    
    // Auto-remove after 5 seconds
    setTimeout(function() {
        const alerts = document.querySelectorAll('.notification-alert');
        alerts.forEach(function(alert) {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        });
    }, 5000);
} 