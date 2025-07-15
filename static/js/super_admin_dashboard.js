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
                case 'driver-approval':
                    loadDriverApprovalData();
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

// Driver Approval Functions
async function loadDriverApprovalData() {
    loadPendingDrivers();
    loadApprovedDrivers();
    loadDriverStats();
}

// Load pending drivers
async function loadPendingDrivers() {
    try {
        const response = await fetch('/api/super-admin/drivers/pending');
        if (response.ok) {
            const data = await response.json();
            renderPendingDrivers(data.drivers);
        }
    } catch (error) {
        console.error('Error loading pending drivers:', error);
    }
}

// Load approved drivers
async function loadApprovedDrivers() {
    try {
        const response = await fetch('/api/super-admin/drivers/approved');
        if (response.ok) {
            const data = await response.json();
            renderApprovedDrivers(data.drivers);
        }
    } catch (error) {
        console.error('Error loading approved drivers:', error);
    }
}

// Load driver statistics
async function loadDriverStats() {
    try {
        const [pendingResponse, approvedResponse] = await Promise.all([
            fetch('/api/super-admin/drivers/pending'),
            fetch('/api/super-admin/drivers/approved')
        ]);
        
        if (pendingResponse.ok && approvedResponse.ok) {
            const pendingData = await pendingResponse.json();
            const approvedData = await approvedResponse.json();
            
            const activeDrivers = approvedData.drivers.filter(d => d.location_status === 'active').length;
            const availableDrivers = approvedData.drivers.filter(d => d.is_available && d.location_status === 'active').length;
            
            document.getElementById('pendingDrivers').textContent = pendingData.drivers.length;
            document.getElementById('approvedDrivers').textContent = approvedData.drivers.length;
            document.getElementById('activeDrivers').textContent = activeDrivers;
            document.getElementById('availableDrivers').textContent = availableDrivers;
        }
    } catch (error) {
        console.error('Error loading driver stats:', error);
    }
}

// Render pending drivers table
function renderPendingDrivers(drivers) {
    const tbody = document.getElementById('pendingDriversTable');
    
    if (drivers.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="6" class="text-center py-4">
                    <div class="text-muted">
                        <i class="fas fa-inbox"></i> No pending driver applications
                    </div>
                </td>
            </tr>
        `;
        return;
    }
    
    tbody.innerHTML = drivers.map(driver => `
        <tr>
            <td>
                <div class="d-flex align-items-center">
                    <div class="avatar-circle bg-primary text-white me-2">
                        ${getInitials(driver.name)}
                    </div>
                    <div>
                        <div class="fw-bold">${driver.name}</div>
                        <small class="text-muted">ID: ${driver.id}</small>
                    </div>
                </div>
            </td>
            <td>
                <i class="fas fa-phone text-primary me-1"></i>
                ${driver.phone_number}
            </td>
            <td>
                <span class="badge bg-info">
                    <i class="fas fa-${getVehicleIcon(driver.vehicle_type)}"></i>
                    ${driver.vehicle_type}
                </span>
            </td>
            <td>
                <small class="text-muted">
                    ${formatDate(driver.created_at)}
                </small>
            </td>
            <td>
                <button class="btn btn-sm btn-outline-info" onclick="viewDriverDocuments(${driver.id})">
                    <i class="fas fa-file-alt"></i> View
                </button>
            </td>
            <td>
                <div class="btn-group">
                    <button class="btn btn-sm btn-success" onclick="approveDriver(${driver.id})">
                        <i class="fas fa-check"></i> Approve
                    </button>
                    <button class="btn btn-sm btn-danger" onclick="rejectDriver(${driver.id})">
                        <i class="fas fa-times"></i> Reject
                    </button>
                </div>
            </td>
        </tr>
    `).join('');
}

// Render approved drivers table
function renderApprovedDrivers(drivers) {
    const tbody = document.getElementById('approvedDriversTable');
    
    if (drivers.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="7" class="text-center py-4">
                    <div class="text-muted">
                        <i class="fas fa-inbox"></i> No approved drivers
                    </div>
                </td>
            </tr>
        `;
        return;
    }
    
    tbody.innerHTML = drivers.map(driver => `
        <tr>
            <td>
                <div class="d-flex align-items-center">
                    <div class="avatar-circle bg-success text-white me-2">
                        ${getInitials(driver.name)}
                    </div>
                    <div>
                        <div class="fw-bold">${driver.name}</div>
                        <small class="text-muted">ID: ${driver.id}</small>
                    </div>
                </div>
            </td>
            <td>
                <i class="fas fa-phone text-primary me-1"></i>
                ${driver.phone_number}
            </td>
            <td>
                <span class="badge bg-info">
                    <i class="fas fa-${getVehicleIcon(driver.vehicle_type)}"></i>
                    ${driver.vehicle_type}
                </span>
            </td>
            <td>
                <span class="badge bg-${getLocationStatusColor(driver.location_status)}">
                    <i class="fas fa-map-marker-alt"></i>
                    ${driver.location_status.toUpperCase()}
                </span>
            </td>
            <td>
                <small class="text-muted">
                    ${driver.last_location_update ? formatDate(driver.last_location_update) : 'Never'}
                </small>
            </td>
            <td>
                <div class="d-flex gap-1">
                    <span class="badge bg-${driver.is_active ? 'success' : 'secondary'}">
                        ${driver.is_active ? 'Active' : 'Inactive'}
                    </span>
                    <span class="badge bg-${driver.is_available ? 'primary' : 'warning'}">
                        ${driver.is_available ? 'Available' : 'Busy'}
                    </span>
                </div>
            </td>
            <td>
                <div class="btn-group">
                    ${driver.current_lat && driver.current_lng ? `
                        <button class="btn btn-sm btn-outline-primary" onclick="viewDriverLocation(${driver.current_lat}, ${driver.current_lng})">
                            <i class="fas fa-map-marker-alt"></i> View
                        </button>
                    ` : ''}
                    <button class="btn btn-sm btn-outline-info" onclick="viewDriverDocuments(${driver.id})">
                        <i class="fas fa-file-alt"></i> Docs
                    </button>
                </div>
            </td>
        </tr>
    `).join('');
}

// Approve driver function
async function approveDriver(driverId) {
    if (!confirm('Are you sure you want to approve this driver?')) return;
    
    try {
        const response = await fetch(`/api/super-admin/drivers/${driverId}/approve`, {
            method: 'POST'
        });
        
        if (response.ok) {
            const data = await response.json();
            alert('Driver approved successfully! They will receive a congratulations notification.');
            loadDriverApprovalData();
        } else {
            alert('Failed to approve driver');
        }
    } catch (error) {
        console.error('Error approving driver:', error);
        alert('Error approving driver');
    }
}

// Reject driver function
async function rejectDriver(driverId) {
    const reason = prompt('Please provide a reason for rejection:');
    if (!reason) return;
    
    try {
        const response = await fetch(`/api/super-admin/drivers/${driverId}/reject`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ reason })
        });
        
        if (response.ok) {
            const data = await response.json();
            alert('Driver rejected successfully! They will receive a notification.');
            loadDriverApprovalData();
        } else {
            alert('Failed to reject driver');
        }
    } catch (error) {
        console.error('Error rejecting driver:', error);
        alert('Error rejecting driver');
    }
}

// View driver documents
async function viewDriverDocuments(driverId) {
    try {
        const response = await fetch(`/api/super-admin/drivers/${driverId}/documents`);
        if (response.ok) {
            const data = await response.json();
            showDriverDocumentsModal(data.documents);
        }
    } catch (error) {
        console.error('Error loading driver documents:', error);
    }
}

// Show driver documents modal
function showDriverDocumentsModal(documents) {
    const modalHtml = `
        <div class="modal fade" id="driverDocumentsModal" tabindex="-1">
            <div class="modal-dialog modal-lg">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">Driver Documents - ${documents.driver_name}</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <div class="row">
                            <div class="col-md-6">
                                <h6>Driver Information</h6>
                                <p><strong>Name:</strong> ${documents.driver_name}</p>
                                <p><strong>Phone:</strong> ${documents.phone_number}</p>
                                <p><strong>Vehicle:</strong> ${documents.vehicle_type}</p>
                                <p><strong>Status:</strong> ${documents.approval_status}</p>
                            </div>
                            <div class="col-md-6">
                                <h6>Documents</h6>
                                ${documents.license_document ? `
                                    <p><strong>License:</strong> 
                                        <a href="${documents.license_document}" target="_blank" class="btn btn-sm btn-outline-primary">
                                            <i class="fas fa-eye"></i> View
                                        </a>
                                    </p>
                                ` : '<p>License: Not provided</p>'}
                                
                                ${documents.id_document ? `
                                    <p><strong>ID Document:</strong> 
                                        <a href="${documents.id_document}" target="_blank" class="btn btn-sm btn-outline-primary">
                                            <i class="fas fa-eye"></i> View
                                        </a>
                                    </p>
                                ` : '<p>ID Document: Not provided</p>'}
                                
                                ${documents.vehicle_document ? `
                                    <p><strong>Vehicle Document:</strong> 
                                        <a href="${documents.vehicle_document}" target="_blank" class="btn btn-sm btn-outline-primary">
                                            <i class="fas fa-eye"></i> View
                                        </a>
                                    </p>
                                ` : '<p>Vehicle Document: Not provided</p>'}
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    // Remove existing modal if any
    const existingModal = document.getElementById('driverDocumentsModal');
    if (existingModal) {
        existingModal.remove();
    }
    
    // Add modal to body
    document.body.insertAdjacentHTML('beforeend', modalHtml);
    
    // Show modal
    new bootstrap.Modal(document.getElementById('driverDocumentsModal')).show();
}

// View driver location
function viewDriverLocation(lat, lng) {
    window.open(`https://maps.google.com/maps?q=${lat},${lng}&z=15`, '_blank');
}

// Utility functions for driver management
function getVehicleIcon(vehicleType) {
    const icons = {
        bicycle: 'bicycle',
        motorcycle: 'motorcycle',
        car: 'car'
    };
    return icons[vehicleType] || 'car';
}

function getLocationStatusColor(status) {
    const colors = {
        active: 'success',
        recent: 'warning',
        inactive: 'secondary'
    };
    return colors[status] || 'secondary';
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
    showLoading('restaurantTable');
    
    try {
        const response = await fetch('/api/admin/restaurants');
        if (response.ok) {
            const data = await response.json();
            restaurantData = data.restaurants;
            renderRestaurantsTable(restaurantData);
        } else {
            showError('Failed to load restaurants data');
        }
    } catch (error) {
        console.error('Error loading restaurants:', error);
        showError('Network error while loading restaurants');
    }
}

// Render restaurants table
function renderRestaurantsTable(restaurants) {
    const tableBody = document.getElementById('restaurantTable');
    
    if (restaurants.length === 0) {
        tableBody.innerHTML = `
            <tr>
                <td colspan="7" class="text-center py-4">
                    <i class="fas fa-store"></i> No restaurants found
                </td>
            </tr>
        `;
        return;
    }
    
    const rows = restaurants.map(restaurant => {
        const statusBadge = restaurant.is_active ? 
            '<span class="badge bg-success">Active</span>' :
            '<span class="badge bg-secondary">Inactive</span>';
        
        return `
            <tr>
                <td>
                    <div class="d-flex align-items-center">
                        <img src="${restaurant.logo_url || '/static/uploads/default-restaurant.svg'}" 
                             alt="${restaurant.name}" 
                             class="rounded me-3" 
                             style="width: 40px; height: 40px; object-fit: cover;"
                             onerror="this.src='/static/uploads/default-restaurant.svg'">
                        <div>
                            <div class="fw-bold">${restaurant.name}</div>
                            <small class="text-muted">${restaurant.description || 'No description'}</small>
                        </div>
                    </div>
                </td>
                <td>
                    <div>
                        <div>${restaurant.address}</div>
                        <small class="text-muted">${restaurant.phone || 'No phone'}</small>
                    </div>
                </td>
                <td>Admin User</td>
                <td>0</td>
                <td>0 ETB</td>
                <td>${statusBadge}</td>
                <td>
                    <button class="btn btn-sm btn-outline-primary action-btn" 
                            onclick="viewRestaurant(${restaurant.id})" 
                            title="View Details">
                        <i class="fas fa-eye"></i>
                    </button>
                    <button class="btn btn-sm btn-outline-warning action-btn" 
                            onclick="editRestaurant(${restaurant.id})" 
                            title="Edit Restaurant">
                        <i class="fas fa-edit"></i>
                    </button>
                </td>
            </tr>
        `;
    }).join('');
    
    tableBody.innerHTML = rows;
}

// Load analytics data
async function loadAnalyticsData() {
    try {
        // Delay to ensure tab is visible before initializing charts
        setTimeout(() => {
            initializeAnalyticsCharts();
            console.log('Analytics data loaded');
        }, 100);
    } catch (error) {
        console.error('Error loading analytics:', error);
        showError('Network error while loading analytics');
    }
}

// Initialize analytics charts
function initializeAnalyticsCharts() {
    // Destroy existing charts to prevent canvas reuse error
    Chart.helpers.each(Chart.instances, function(instance) {
        instance.destroy();
    });
    
    // Revenue Chart
    const revenueCtx = document.getElementById('revenueChart');
    if (revenueCtx) {
        new Chart(revenueCtx, {
            type: 'line',
            data: {
                labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
                datasets: [{
                    label: 'Revenue (ETB)',
                    data: [12000, 19000, 15000, 25000, 22000, 30000],
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
    
    // Order Status Chart
    const orderStatusCtx = document.getElementById('orderStatusChart');
    if (orderStatusCtx) {
        new Chart(orderStatusCtx, {
            type: 'doughnut',
            data: {
                labels: ['Delivered', 'Preparing', 'Pending', 'Cancelled'],
                datasets: [{
                    data: [45, 25, 20, 10],
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
    
    // Restaurant Performance Chart
    const restaurantPerformanceCtx = document.getElementById('restaurantPerformanceChart');
    if (restaurantPerformanceCtx) {
        new Chart(restaurantPerformanceCtx, {
            type: 'bar',
            data: {
                labels: ['Restaurant A', 'Restaurant B', 'Restaurant C', 'Restaurant D'],
                datasets: [{
                    label: 'Orders',
                    data: [65, 59, 80, 45],
                    backgroundColor: 'rgba(52, 152, 219, 0.8)'
                }, {
                    label: 'Revenue (ETB)',
                    data: [28000, 48000, 40000, 25000],
                    backgroundColor: 'rgba(39, 174, 96, 0.8)'
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
}

// Additional restaurant functions
function viewRestaurant(restaurantId) {
    console.log(`Viewing restaurant ${restaurantId}`);
    showAlert('Restaurant details will be implemented soon', 'info');
}

function editRestaurant(restaurantId) {
    console.log(`Editing restaurant ${restaurantId}`);
    showAlert('Restaurant editing will be implemented soon', 'info');
}