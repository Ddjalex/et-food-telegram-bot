// Super Admin Dashboard JavaScript
let adminData = [];
let restaurantData = [];
let charts = {};

// Initialize dashboard
document.addEventListener('DOMContentLoaded', function() {
    initializeTabs();
    loadDashboardData();
    initializeCharts();
    loadRestaurantOptions();
});

// Tab navigation
function initializeTabs() {
    const tabLinks = document.querySelectorAll('#adminTabs a');
    
    tabLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            
            // Remove active class from all links and contents
            tabLinks.forEach(l => l.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(content => {
                content.classList.remove('active');
            });
            
            // Add active class to clicked link
            this.classList.add('active');
            
            // Show corresponding tab content
            const tabId = this.getAttribute('data-tab');
            document.getElementById(tabId).classList.add('active');
            
            // Load tab-specific data
            switch(tabId) {
                case 'overview':
                    loadOverviewData();
                    break;
                case 'admins':
                    loadAdminsData();
                    break;
                case 'restaurants':
                    loadRestaurantsData();
                    break;
                case 'analytics':
                    loadAnalyticsData();
                    break;
            }
        });
    });
}

// Load dashboard overview data
async function loadDashboardData() {
    try {
        const response = await fetch('/api/super-admin/dashboard-stats');
        if (response.ok) {
            const data = await response.json();
            updateDashboardStats(data);
        }
    } catch (error) {
        console.error('Error loading dashboard data:', error);
    }
}

// Update dashboard statistics
function updateDashboardStats(data) {
    document.getElementById('totalAdmins').textContent = data.totalAdmins || 0;
    document.getElementById('totalRestaurants').textContent = data.totalRestaurants || 0;
    document.getElementById('todayOrders').textContent = data.todayOrders || 0;
    document.getElementById('totalRevenue').textContent = `${data.totalRevenue || 0} ETB`;
}

// Load overview data
async function loadOverviewData() {
    try {
        const response = await fetch('/api/super-admin/overview');
        if (response.ok) {
            const data = await response.json();
            updateOverviewCharts(data);
        }
    } catch (error) {
        console.error('Error loading overview data:', error);
    }
}

// Load admins data
async function loadAdminsData() {
    showLoading('adminTable');
    
    try {
        const response = await fetch('/api/super-admin/admins');
        if (response.ok) {
            const data = await response.json();
            adminData = data.admins;
            renderAdminsTable(adminData);
        } else {
            showError('Failed to load admins data');
        }
    } catch (error) {
        console.error('Error loading admins:', error);
        showError('Network error while loading admins');
    }
}

// Render admins table
function renderAdminsTable(admins) {
    const tableBody = document.getElementById('adminTable');
    
    if (admins.length === 0) {
        tableBody.innerHTML = `
            <tr>
                <td colspan="7" class="text-center py-4">
                    <i class="fas fa-users"></i> No admins found
                </td>
            </tr>
        `;
        return;
    }
    
    const rows = admins.map(admin => {
        const performanceClass = getPerformanceClass(admin.average_response_time);
        const statusBadge = admin.is_blocked ? 
            '<span class="badge bg-danger">Blocked</span>' :
            admin.is_active ? 
                '<span class="badge bg-success">Active</span>' : 
                '<span class="badge bg-secondary">Inactive</span>';
        
        return `
            <tr>
                <td>
                    <div class="d-flex align-items-center">
                        <div class="admin-avatar me-3">
                            ${getInitials(admin.full_name || admin.username)}
                        </div>
                        <div>
                            <div class="fw-bold">${admin.full_name || admin.username}</div>
                            <small class="text-muted">${admin.email || 'No email'}</small>
                        </div>
                    </div>
                </td>
                <td>
                    <span class="role-badge role-${admin.role}">${formatRole(admin.role)}</span>
                </td>
                <td>${admin.restaurant_name || 'Not assigned'}</td>
                <td>
                    <span class="performance-indicator ${performanceClass}"></span>
                    ${admin.orders_processed || 0} orders
                    <br>
                    <small class="text-muted">${admin.recent_activities || 0} recent activities</small>
                </td>
                <td>
                    ${admin.last_login ? formatDate(admin.last_login) : 'Never'}
                </td>
                <td>${statusBadge}</td>
                <td>
                    <button class="btn btn-sm btn-outline-primary action-btn" 
                            onclick="viewPerformance(${admin.id})" 
                            title="View Performance">
                        <i class="fas fa-chart-line"></i>
                    </button>
                    <button class="btn btn-sm btn-outline-warning action-btn" 
                            onclick="resetPassword(${admin.id})" 
                            title="Reset Password">
                        <i class="fas fa-key"></i>
                    </button>
                    <button class="btn btn-sm btn-outline-${admin.is_blocked ? 'success' : 'danger'} action-btn" 
                            onclick="toggleBlock(${admin.id}, ${admin.is_blocked})" 
                            title="${admin.is_blocked ? 'Unblock' : 'Block'} Admin">
                        <i class="fas fa-${admin.is_blocked ? 'unlock' : 'ban'}"></i>
                    </button>
                </td>
            </tr>
        `;
    }).join('');
    
    tableBody.innerHTML = rows;
}

// Create new admin
async function createAdmin() {
    const form = document.getElementById('addAdminForm');
    const formData = new FormData(form);
    
    // Validate passwords match
    if (formData.get('password') !== formData.get('confirm_password')) {
        showAlert('Passwords do not match', 'danger');
        return;
    }
    
    // Convert FormData to JSON
    const data = {};
    formData.forEach((value, key) => {
        if (key !== 'confirm_password') {
            data[key] = value;
        }
    });
    
    try {
        const response = await fetch('/api/super-admin/admins', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data)
        });
        
        const result = await response.json();
        
        if (result.success) {
            showAlert('Admin created successfully', 'success');
            bootstrap.Modal.getInstance(document.getElementById('addAdminModal')).hide();
            form.reset();
            loadAdminsData(); // Refresh table
        } else {
            showAlert(result.message || 'Failed to create admin', 'danger');
        }
    } catch (error) {
        console.error('Error creating admin:', error);
        showAlert('Network error while creating admin', 'danger');
    }
}

// Toggle admin block status
async function toggleBlock(adminId, isBlocked) {
    const action = isBlocked ? 'unblock' : 'block';
    
    if (!confirm(`Are you sure you want to ${action} this admin?`)) {
        return;
    }
    
    try {
        const response = await fetch(`/api/super-admin/admins/${adminId}/block`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ blocked: !isBlocked })
        });
        
        const result = await response.json();
        
        if (result.success) {
            showAlert(result.message, 'success');
            loadAdminsData(); // Refresh table
        } else {
            showAlert(result.message || 'Failed to update admin status', 'danger');
        }
    } catch (error) {
        console.error('Error toggling admin block:', error);
        showAlert('Network error while updating admin status', 'danger');
    }
}

// Reset admin password
async function resetPassword(adminId) {
    const newPassword = prompt('Enter new password for this admin:');
    
    if (!newPassword) {
        return;
    }
    
    if (newPassword.length < 6) {
        showAlert('Password must be at least 6 characters long', 'danger');
        return;
    }
    
    try {
        const response = await fetch(`/api/super-admin/admins/${adminId}/reset-password`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ password: newPassword })
        });
        
        const result = await response.json();
        
        if (result.success) {
            showAlert('Password reset successfully', 'success');
        } else {
            showAlert(result.message || 'Failed to reset password', 'danger');
        }
    } catch (error) {
        console.error('Error resetting password:', error);
        showAlert('Network error while resetting password', 'danger');
    }
}

// View admin performance
async function viewPerformance(adminId) {
    try {
        const response = await fetch(`/api/super-admin/admins/${adminId}/performance`);
        if (response.ok) {
            const data = await response.json();
            renderPerformanceModal(data);
        } else {
            showAlert('Failed to load performance data', 'danger');
        }
    } catch (error) {
        console.error('Error loading performance:', error);
        showAlert('Network error while loading performance data', 'danger');
    }
}

// Render performance modal
function renderPerformanceModal(data) {
    const admin = data.admin;
    const modalBody = document.getElementById('performanceModalBody');
    
    modalBody.innerHTML = `
        <div class="row mb-4">
            <div class="col-md-4">
                <div class="text-center">
                    <div class="admin-avatar mx-auto mb-3" style="width: 80px; height: 80px; font-size: 2rem;">
                        ${getInitials(admin.full_name || admin.username)}
                    </div>
                    <h5>${admin.full_name || admin.username}</h5>
                    <span class="role-badge role-${admin.role}">${formatRole(admin.role)}</span>
                </div>
            </div>
            <div class="col-md-8">
                <div class="row">
                    <div class="col-md-6">
                        <div class="stat-card">
                            <h6>Orders Processed</h6>
                            <h3 class="text-primary">${admin.orders_processed || 0}</h3>
                        </div>
                    </div>
                    <div class="col-md-6">
                        <div class="stat-card">
                            <h6>Average Response Time</h6>
                            <h3 class="text-warning">${data.avg_response_time || 0} min</h3>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="row mb-4">
            <div class="col-md-6">
                <div class="chart-container">
                    <h6>Activity Breakdown</h6>
                    <canvas id="activityBreakdownChart"></canvas>
                </div>
            </div>
            <div class="col-md-6">
                <div class="chart-container">
                    <h6>Daily Activity</h6>
                    <canvas id="dailyActivityChart"></canvas>
                </div>
            </div>
        </div>
        
        <div class="table-container">
            <div class="table-header">
                <h6 class="mb-0">Recent Sessions</h6>
            </div>
            <div class="table-responsive">
                <table class="table table-sm">
                    <thead>
                        <tr>
                            <th>Login Time</th>
                            <th>Duration</th>
                            <th>Actions</th>
                            <th>IP Address</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${data.recent_sessions.map(session => `
                            <tr>
                                <td>${formatDate(session.login_time)}</td>
                                <td>${session.session_duration || 0} min</td>
                                <td>${session.actions_performed || 0}</td>
                                <td><code>${session.ip_address || 'N/A'}</code></td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
        </div>
    `;
    
    // Show modal
    new bootstrap.Modal(document.getElementById('performanceModal')).show();
    
    // Initialize charts after modal is shown
    setTimeout(() => {
        initializePerformanceCharts(data);
    }, 500);
}

// Initialize performance charts
function initializePerformanceCharts(data) {
    // Activity breakdown chart
    const activityCtx = document.getElementById('activityBreakdownChart').getContext('2d');
    const activityData = data.activity_counts;
    
    new Chart(activityCtx, {
        type: 'doughnut',
        data: {
            labels: Object.keys(activityData),
            datasets: [{
                data: Object.values(activityData),
                backgroundColor: ['#3498db', '#27ae60', '#f39c12', '#e74c3c', '#9b59b6']
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom'
                }
            }
        }
    });
    
    // Daily activity chart
    const dailyCtx = document.getElementById('dailyActivityChart').getContext('2d');
    const dailyData = data.daily_activities;
    
    new Chart(dailyCtx, {
        type: 'line',
        data: {
            labels: dailyData.map(d => d.date),
            datasets: [{
                label: 'Activities',
                data: dailyData.map(d => d.count),
                borderColor: '#3498db',
                backgroundColor: 'rgba(52, 152, 219, 0.1)',
                fill: true
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true
                }
            }
        }
    });
}

// Load restaurant options for admin creation
async function loadRestaurantOptions() {
    try {
        const response = await fetch('/api/restaurants');
        if (response.ok) {
            const data = await response.json();
            const select = document.getElementById('restaurantSelect');
            
            data.restaurants.forEach(restaurant => {
                const option = document.createElement('option');
                option.value = restaurant.id;
                option.textContent = restaurant.name;
                select.appendChild(option);
            });
        }
    } catch (error) {
        console.error('Error loading restaurants:', error);
    }
}

// Initialize charts
function initializeCharts() {
    // Admin activity chart
    const activityCtx = document.getElementById('adminActivityChart').getContext('2d');
    charts.adminActivity = new Chart(activityCtx, {
        type: 'bar',
        data: {
            labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
            datasets: [{
                label: 'Admin Activities',
                data: [12, 19, 3, 5, 2, 3],
                backgroundColor: 'rgba(52, 152, 219, 0.8)'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false
        }
    });
    
    // Performance chart
    const performanceCtx = document.getElementById('performanceChart').getContext('2d');
    charts.performance = new Chart(performanceCtx, {
        type: 'pie',
        data: {
            labels: ['Excellent', 'Good', 'Average', 'Poor'],
            datasets: [{
                data: [30, 45, 20, 5],
                backgroundColor: ['#27ae60', '#f39c12', '#3498db', '#e74c3c']
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom'
                }
            }
        }
    });
}

// Utility functions
function getInitials(name) {
    return name.split(' ').map(n => n[0]).join('').toUpperCase();
}

function formatRole(role) {
    return role.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase());
}

function formatDate(dateString) {
    return new Date(dateString).toLocaleDateString();
}

function getPerformanceClass(responseTime) {
    if (responseTime < 5) return 'performance-excellent';
    if (responseTime < 15) return 'performance-good';
    return 'performance-poor';
}

function showLoading(elementId) {
    const element = document.getElementById(elementId);
    element.innerHTML = `
        <tr>
            <td colspan="7" class="text-center py-4">
                <i class="fas fa-spinner fa-spin"></i> Loading...
            </td>
        </tr>
    `;
}

function showError(message) {
    showAlert(message, 'danger');
}

function showAlert(message, type) {
    const alert = document.createElement('div');
    alert.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
    alert.style.top = '20px';
    alert.style.right = '20px';
    alert.style.zIndex = '9999';
    alert.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    document.body.appendChild(alert);
    
    setTimeout(() => {
        if (alert.parentElement) {
            alert.remove();
        }
    }, 5000);
}

// Load restaurants data
async function loadRestaurantsData() {
    // This would load restaurant data for the restaurants tab
    console.log('Loading restaurants data...');
}

// Load analytics data
async function loadAnalyticsData() {
    // This would load analytics data
    console.log('Loading analytics data...');
}