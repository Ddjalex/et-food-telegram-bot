// Super Admin Dashboard with Real-time Location Monitoring
let autoRefreshInterval;
let isAutoRefreshEnabled = true;

// Initialize dashboard when document is ready
document.addEventListener('DOMContentLoaded', function() {
    initializeDashboard();
    setupTabNavigation();
    startAutoRefresh();
    setupChangePasswordForm();
    
    // Setup modal event listeners
    const addAdminModal = document.getElementById('addAdminModal');
    if (addAdminModal) {
        addAdminModal.addEventListener('show.bs.modal', function() {
            loadRestaurantsDropdown();
        });
    }
});

function initializeDashboard() {
    loadDashboardStats();
    loadDriverStats();
    loadAdmins();
    loadRestaurants();
    loadDriverApprovals();
}

// Enhanced real-time monitoring functions
function startAutoRefresh() {
    // Auto-refresh dashboard data every 10 seconds for real-time updates
    if (autoRefreshInterval) clearInterval(autoRefreshInterval);
    
    autoRefreshInterval = setInterval(() => {
        loadDashboardStats();
        loadDriverApprovals(); // Real-time driver applications
        checkForNewDriverApplications(); // Check for new applications
    }, 10000); // Refresh every 10 seconds for real-time updates
}

// Track driver applications for real-time notifications
let lastDriverApplicationCount = 0;

function checkForNewDriverApplications() {
    fetch('/api/super-admin/drivers/pending')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                const currentCount = data.drivers.length;
                
                // Check if there are new applications
                if (currentCount > lastDriverApplicationCount && lastDriverApplicationCount > 0) {
                    const newApplications = currentCount - lastDriverApplicationCount;
                    showNewApplicationNotification(newApplications);
                    
                    // Flash the pending applications section
                    flashPendingApplicationsSection();
                }
                
                lastDriverApplicationCount = currentCount;
                updatePendingDriversBadge(currentCount);
            }
        })
        .catch(error => {
            console.error('Error checking for new driver applications:', error);
        });
}

function showNewApplicationNotification(count) {
    // Play notification sound
    playNotificationSound();
    
    // Create notification toast
    const notification = document.createElement('div');
    notification.className = 'alert alert-success alert-dismissible fade show position-fixed';
    notification.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px; box-shadow: 0 5px 20px rgba(0,0,0,0.3);';
    notification.innerHTML = `
        <div class="d-flex align-items-center">
            <i class="fas fa-bell text-success me-2"></i>
            <div>
                <strong>🚗 New Driver Application${count > 1 ? 's' : ''}!</strong>
                <div class="small">${count} new application${count > 1 ? 's' : ''} received</div>
            </div>
        </div>
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    document.body.appendChild(notification);
    
    // Auto-remove after 7 seconds
    setTimeout(() => {
        if (notification.parentNode) {
            notification.remove();
        }
    }, 7000);
}

function playNotificationSound() {
    try {
        // Create notification sound using Web Audio API
        const audioContext = new (window.AudioContext || window.webkitAudioContext)();
        const oscillator = audioContext.createOscillator();
        const gainNode = audioContext.createGain();
        
        oscillator.connect(gainNode);
        gainNode.connect(audioContext.destination);
        
        oscillator.frequency.setValueAtTime(800, audioContext.currentTime);
        oscillator.frequency.setValueAtTime(600, audioContext.currentTime + 0.1);
        
        gainNode.gain.setValueAtTime(0.3, audioContext.currentTime);
        gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.3);
        
        oscillator.start(audioContext.currentTime);
        oscillator.stop(audioContext.currentTime + 0.3);
    } catch (error) {
        console.log('Audio notification not available:', error);
    }
}

function flashPendingApplicationsSection() {
    const section = document.querySelector('#driver-approval .stat-card');
    if (section) {
        section.classList.add('flash-highlight');
        setTimeout(() => {
            section.classList.remove('flash-highlight');
        }, 2000);
    }
}

function updatePendingDriversBadge(count) {
    // Update the tab badge if it exists
    const driverTab = document.querySelector('[data-target="driver-approval"]');
    if (driverTab && count > 0) {
        let badge = driverTab.querySelector('.badge');
        if (!badge) {
            badge = document.createElement('span');
            badge.className = 'badge bg-warning ms-1';
            driverTab.appendChild(badge);
        }
        badge.textContent = count;
    } else if (driverTab) {
        const badge = driverTab.querySelector('.badge');
        if (badge) {
            badge.remove();
        }
    }
}

function updateLastRefreshTime() {
    const now = new Date();
    const timeString = now.toLocaleTimeString();
    const lastUpdateEl = document.getElementById('lastUpdate');
    if (lastUpdateEl) {
        lastUpdateEl.textContent = `Last updated: ${timeString}`;
    }
}

// Load basic driver statistics
function loadDriverStats() {
    fetch('/api/super-admin/drivers/stats')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                updateDriverStatsUI(data.stats);
            } else {
                console.error('Failed to load driver stats:', data.error);
            }
        })
        .catch(error => {
            console.error('Error loading driver stats:', error);
        });
}

function updateDriverStatsUI(stats) {
    // Update driver statistics
    const totalDriversEl = document.getElementById('totalDrivers');
    if (totalDriversEl) {
        totalDriversEl.textContent = stats.total || 0;
    }
    
    const liveLocationDriversEl = document.getElementById('liveLocationDrivers');
    if (liveLocationDriversEl) {
        liveLocationDriversEl.textContent = stats.approved || 0;
    }
}

function updateDriverLocationTable(drivers) {
    const tableBody = document.getElementById('driversLocationTable');
    
    if (drivers.length === 0) {
        tableBody.innerHTML = `
            <tr>
                <td colspan="6" class="text-center text-muted">
                    <i class="fas fa-info-circle me-2"></i>No approved drivers found
                </td>
            </tr>
        `;
        return;
    }
    
    tableBody.innerHTML = drivers.map(driver => {
        const locationStatus = getLocationStatus(driver);
        const overallStatus = getOverallStatus(driver);
        const lastUpdate = getLastUpdateText(driver.last_location_update);
        
        return `
            <tr>
                <td>
                    <div class="d-flex align-items-center">
                        <div class="avatar-circle bg-primary text-white me-2">
                            ${driver.name.charAt(0)}
                        </div>
                        <div>
                            <div class="fw-bold">${driver.name}</div>
                            <small class="text-muted">${driver.phone_number}</small>
                        </div>
                    </div>
                </td>
                <td>
                    <span class="badge" style="background-color: ${overallStatus.color}">
                        <i class="fas fa-circle me-1"></i>${overallStatus.text}
                    </span>
                </td>
                <td>
                    <span class="badge" style="background-color: ${locationStatus.color}">
                        <i class="fas fa-map-marker-alt me-1"></i>${locationStatus.text}
                    </span>
                </td>
                <td>
                    <span class="text-muted">${lastUpdate}</span>
                </td>
                <td>
                    <i class="fas fa-${getVehicleIcon(driver.vehicle_type)} me-1"></i>
                    ${driver.vehicle_type}
                </td>
                <td>
                    <div class="btn-group btn-group-sm">
                        ${driver.current_lat && driver.current_lng ? 
                            `<button class="btn btn-outline-primary btn-sm" onclick="viewDriverLocation(${driver.current_lat}, ${driver.current_lng}, '${driver.name}')">
                                <i class="fas fa-map"></i>
                            </button>` : ''
                        }
                        <button class="btn btn-outline-info btn-sm" onclick="requestDriverLocation(${driver.id})">
                            <i class="fas fa-location-arrow"></i>
                        </button>
                        <button class="btn btn-outline-danger btn-sm" onclick="deleteDriver(${driver.id}, '${driver.name}')">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                </td>
            </tr>
        `;
    }).join('');
}

function getLocationStatus(driver) {
    // Use location_status from API if available
    if (driver.location_status) {
        switch(driver.location_status) {
            case 'live':
                return { text: 'Live Location', color: '#28a745' };
            case 'active':
                return { text: 'Active Location', color: '#28a745' };
            case 'recent':
                return { text: 'Recent Location', color: '#ffc107' };
            case 'inactive':
                return { text: 'Location Inactive', color: '#dc3545' };
            default:
                return { text: 'No Location', color: '#dc3545' };
        }
    }
    
    // Fallback to client-side calculation
    if (!driver.last_location_update) {
        return { text: 'No Location', color: '#dc3545' };
    }
    
    const now = new Date();
    const lastUpdate = new Date(driver.last_location_update);
    const diffMinutes = (now - lastUpdate) / (1000 * 60);
    
    // More aggressive real-time detection
    if (diffMinutes < 2) {
        return { text: 'Live Location', color: '#28a745' };
    } else if (diffMinutes < 10) {
        return { text: 'Recent Location', color: '#28a745' };
    } else if (diffMinutes < 60) {
        return { text: 'Outdated Location', color: '#ffc107' };
    } else {
        return { text: 'Location Inactive', color: '#dc3545' };
    }
}

function getOverallStatus(driver) {
    if (!driver.is_active) {
        return { text: 'Offline', color: '#6c757d' };
    }
    
    const locationStatus = getLocationStatus(driver);
    
    if (driver.is_available && locationStatus.text === 'Live Location') {
        return { text: 'Available', color: '#28a745' };
    } else if (driver.is_available) {
        return { text: 'Online (No Location)', color: '#ffc107' };
    } else {
        return { text: 'Busy', color: '#fd7e14' };
    }
}

function getLastUpdateText(lastUpdate) {
    if (!lastUpdate) return 'Never';
    
    const now = new Date();
    const updateTime = new Date(lastUpdate);
    const diffMinutes = Math.floor((now - updateTime) / (1000 * 60));
    
    if (diffMinutes < 1) return 'Just now';
    if (diffMinutes < 60) return `${diffMinutes}m ago`;
    
    const diffHours = Math.floor(diffMinutes / 60);
    if (diffHours < 24) return `${diffHours}h ago`;
    
    const diffDays = Math.floor(diffHours / 24);
    return `${diffDays}d ago`;
}

function getVehicleIcon(vehicleType) {
    switch (vehicleType) {
        case 'bicycle': return 'bicycle';
        case 'motorcycle': return 'motorcycle';
        case 'car': return 'car';
        default: return 'car';
    }
}

function viewDriverLocation(lat, lng, driverName) {
    const googleMapsUrl = `https://www.google.com/maps?q=${lat},${lng}&z=15&t=m`;
    window.open(googleMapsUrl, '_blank');
}

function requestDriverLocation(driverId) {
    fetch(`/api/super-admin/drivers/${driverId}/request-location`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showAlert('success', data.message);
            // Refresh driver data after a short delay
            setTimeout(() => {
                loadDriverLocationDetails();
            }, 2000);
        } else {
            showAlert('error', data.message);
        }
    })
    .catch(error => {
        console.error('Error requesting driver location:', error);
        showAlert('error', 'Failed to request driver location');
    });
}

function updateSystemStatus(status) {
    const statusEl = document.getElementById('systemStatus');
    
    switch (status) {
        case 'healthy':
            statusEl.textContent = 'Online';
            statusEl.className = 'badge bg-success ms-2';
            break;
        case 'warning':
            statusEl.textContent = 'Warning';
            statusEl.className = 'badge bg-warning ms-2';
            break;
        case 'error':
            statusEl.textContent = 'Error';
            statusEl.className = 'badge bg-danger ms-2';
            break;
    }
}

// Load dashboard statistics
function loadDashboardStats() {
    fetch('/api/dashboard-stats')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                document.getElementById('totalAdmins').textContent = data.totalAdmins;
                document.getElementById('totalRestaurants').textContent = data.totalRestaurants;
                document.getElementById('todayOrders').textContent = data.todayOrders;
                document.getElementById('totalRevenue').textContent = data.totalRevenue.toFixed(2);
                
                // Also initialize charts with overview data
                loadOverviewCharts();
            }
        })
        .catch(error => {
            console.error('Error loading dashboard stats:', error);
        });
}

function loadOverviewCharts() {
    fetch('/api/overview-data')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                updateCharts(data);
            }
        })
        .catch(error => {
            console.error('Error loading overview data:', error);
        });
}

function updateCharts(data) {
    // Update revenue chart if canvas exists
    const revenueCanvas = document.getElementById('revenueChart');
    if (revenueCanvas && typeof Chart !== 'undefined') {
        const ctx = revenueCanvas.getContext('2d');
        
        new Chart(ctx, {
            type: 'line',
            data: {
                labels: data.revenue_data.map(item => item.date),
                datasets: [{
                    label: 'Daily Revenue (ETB)',
                    data: data.revenue_data.map(item => item.amount),
                    borderColor: 'rgb(75, 192, 192)',
                    backgroundColor: 'rgba(75, 192, 192, 0.1)',
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            }
        });
    }
    
    // Update status chart if canvas exists
    const statusCanvas = document.getElementById('orderStatusChart');
    if (statusCanvas && typeof Chart !== 'undefined') {
        const ctx = statusCanvas.getContext('2d');
        
        new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: Object.keys(data.status_data),
                datasets: [{
                    data: Object.values(data.status_data),
                    backgroundColor: [
                        '#FF6384',
                        '#36A2EB',
                        '#FFCE56',
                        '#4BC0C0',
                        '#9966FF',
                        '#FF9F40'
                    ]
                }]
            },
            options: {
                responsive: true
            }
        });
    }
}

// Tab navigation setup
function setupTabNavigation() {
    document.querySelectorAll('#adminTabs .nav-link').forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            
            // Remove active class from all tabs and content
            document.querySelectorAll('#adminTabs .nav-link').forEach(l => l.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
            
            // Add active class to clicked tab and corresponding content
            this.classList.add('active');
            const targetTab = this.getAttribute('data-tab');
            document.getElementById(targetTab).classList.add('active');
            
            // Load tab-specific data
            switch (targetTab) {
                case 'admins':
                    loadAdmins();
                    break;
                case 'restaurants':
                    loadRestaurants();
                    break;
                case 'driver-approval':
                    loadDriverApprovals();
                    break;
                case 'analytics':
                    loadAnalytics();
                    break;
                case 'overview':
                    loadDashboardStats();
                    loadRealTimeStats();
                    break;
            }
        });
    });
}

// Load admins (placeholder - implement based on existing functionality)
function loadAdmins() {
    fetch('/api/super-admin/admins')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                updateAdminsTable(data.admins);
            } else {
                console.error('Error loading admins:', data.error);
                showAdminError('Failed to load admins');
            }
        })
        .catch(error => {
            console.error('Error loading admins:', error);
            showAdminError('Failed to load admins');
        });
}

// Load restaurants with enhanced functionality
function loadRestaurants() {
    fetch('/api/restaurants/super-admin')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                updateRestaurantsTable(data.restaurants);
            } else {
                console.error('Error loading restaurants:', data.error);
                showRestaurantError('Failed to load restaurants');
            }
        })
        .catch(error => {
            console.error('Error loading restaurants:', error);
            showRestaurantError('Failed to load restaurants');
        });
}

function updateRestaurantsTable(restaurants) {
    const tableBody = document.getElementById('restaurantTable');
    
    if (restaurants.length === 0) {
        tableBody.innerHTML = `
            <tr>
                <td colspan="7" class="text-center text-muted">
                    <i class="fas fa-info-circle me-2"></i>No restaurants found
                </td>
            </tr>
        `;
        return;
    }
    
    tableBody.innerHTML = restaurants.map(restaurant => {
        const statusBadge = restaurant.is_active ? 
            '<span class="badge bg-success">Active</span>' : 
            '<span class="badge bg-secondary">Inactive</span>';
        
        return `
            <tr>
                <td>
                    <div class="d-flex align-items-center">
                        <div class="avatar-circle bg-primary text-white me-2">
                            ${restaurant.name.charAt(0)}
                        </div>
                        <div>
                            <div class="fw-bold">${restaurant.name}</div>
                            <small class="text-muted">${restaurant.menu_items_count || 0} menu items</small>
                        </div>
                    </div>
                </td>
                <td>
                    ${restaurant.logo_url ? 
                        `<img src="${restaurant.logo_url}" alt="Logo" style="width: 40px; height: 40px; border-radius: 8px; object-fit: cover;">` : 
                        '<span class="text-muted small">No logo</span>'}
                </td>
                <td>
                    ${restaurant.cover_image_url ? 
                        `<img src="${restaurant.cover_image_url}" alt="Cover" style="width: 60px; height: 40px; border-radius: 8px; object-fit: cover;">` : 
                        '<span class="text-muted small">No cover</span>'}
                </td>
                <td>
                    <div class="text-muted small">
                        ${restaurant.address}
                    </div>
                </td>
                <td>
                    <div class="fw-bold text-primary">${restaurant.orders_today || 0}</div>
                </td>
                <td>
                    ${statusBadge}
                </td>
                <td>
                    <div class="btn-group btn-group-sm">
                        <button class="btn btn-outline-primary" onclick="viewRestaurantDetails(${restaurant.id})">
                            <i class="fas fa-eye"></i>
                        </button>
                        <button class="btn btn-outline-success" onclick="uploadRestaurantImages(${restaurant.id}, '${restaurant.name}')">
                            <i class="fas fa-images"></i>
                        </button>
                        <button class="btn btn-outline-warning" onclick="editRestaurant(${restaurant.id})">
                            <i class="fas fa-edit"></i>
                        </button>
                        <button class="btn btn-outline-danger" onclick="deleteRestaurant(${restaurant.id}, '${restaurant.name}')">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                </td>
            </tr>
        `;
    }).join('');
}

function deleteRestaurant(restaurantId, restaurantName) {
    if (confirm(`Are you sure you want to delete "${restaurantName}"?\n\nThis action will:\n• Remove all menu items and categories\n• Unassign admin users and drivers\n• Cannot be undone\n\nClick OK to proceed with deletion.`)) {
        // Show loading message
        showAlert('info', 'Cleaning up restaurant dependencies...');
        
        // First clean up dependencies
        fetch(`/api/admin/restaurants/${restaurantId}/cleanup`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showAlert('info', 'Dependencies cleaned up. Deleting restaurant...');
                
                // Now delete the restaurant
                return fetch(`/api/admin/restaurants/${restaurantId}`, {
                    method: 'DELETE',
                    headers: {
                        'Content-Type': 'application/json'
                    }
                });
            } else {
                throw new Error(data.error || 'Failed to cleanup dependencies');
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showAlert('success', `Restaurant "${restaurantName}" deleted successfully!`);
                loadRestaurants(); // Reload the table
            } else {
                showAlert('error', data.error || 'Failed to delete restaurant');
            }
        })
        .catch(error => {
            console.error('Error deleting restaurant:', error);
            showAlert('error', error.message || 'Failed to delete restaurant');
        });
    }
}

// Restaurant image upload function
function uploadRestaurantImages(restaurantId, restaurantName) {
    // Create modal dynamically
    const modalHTML = `
        <div class="modal fade" id="uploadImagesModal" tabindex="-1">
            <div class="modal-dialog modal-lg">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">
                            <i class="fas fa-images"></i> Upload Images for ${restaurantName}
                        </h5>
                        <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <form id="uploadImagesForm" enctype="multipart/form-data">
                            <div class="row">
                                <div class="col-md-6">
                                    <div class="mb-3">
                                        <label class="form-label">Restaurant Logo</label>
                                        <input type="file" class="form-control" name="logo" accept="image/*" onchange="previewUploadImage(this, 'logoUploadPreview')">
                                        <div id="logoUploadPreview" class="mt-2" style="display: none;">
                                            <img id="logoUploadImage" src="" alt="Logo Preview" style="max-width: 100px; max-height: 100px; border-radius: 8px;">
                                        </div>
                                        <small class="text-muted">Recommended: Square image, min 200x200px</small>
                                    </div>
                                </div>
                                <div class="col-md-6">
                                    <div class="mb-3">
                                        <label class="form-label">Cover Image</label>
                                        <input type="file" class="form-control" name="cover_image" accept="image/*" onchange="previewUploadImage(this, 'coverUploadPreview')">
                                        <div id="coverUploadPreview" class="mt-2" style="display: none;">
                                            <img id="coverUploadImage" src="" alt="Cover Preview" style="max-width: 150px; max-height: 100px; border-radius: 8px;">
                                        </div>
                                        <small class="text-muted">Recommended: 16:9 ratio, min 800x450px</small>
                                    </div>
                                </div>
                            </div>
                        </form>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                        <button type="button" class="btn btn-gradient" onclick="submitImageUpload(${restaurantId})">
                            <i class="fas fa-upload"></i> Upload Images
                        </button>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    // Remove existing modal if any
    const existingModal = document.getElementById('uploadImagesModal');
    if (existingModal) {
        existingModal.remove();
    }
    
    // Add modal to page
    document.body.insertAdjacentHTML('beforeend', modalHTML);
    
    // Show modal
    const modal = new bootstrap.Modal(document.getElementById('uploadImagesModal'));
    modal.show();
}

function previewUploadImage(input, previewId) {
    const preview = document.getElementById(previewId);
    const imageElement = preview.querySelector('img');
    
    if (input.files && input.files[0]) {
        const reader = new FileReader();
        reader.onload = function(e) {
            imageElement.src = e.target.result;
            preview.style.display = 'block';
        };
        reader.readAsDataURL(input.files[0]);
    } else {
        preview.style.display = 'none';
    }
}

function submitImageUpload(restaurantId) {
    const form = document.getElementById('uploadImagesForm');
    const formData = new FormData(form);
    
    // Show loading state
    const uploadBtn = document.querySelector('#uploadImagesModal .btn-gradient');
    const originalText = uploadBtn.innerHTML;
    uploadBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Uploading...';
    uploadBtn.disabled = true;
    
    fetch(`/api/super-admin/restaurants/${restaurantId}/upload-images`, {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showAlert('success', data.message);
            loadRestaurants(); // Reload the table
            
            // Close modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('uploadImagesModal'));
            modal.hide();
        } else {
            showAlert('error', data.message || 'Failed to upload images');
        }
    })
    .catch(error => {
        console.error('Error uploading images:', error);
        showAlert('error', 'Failed to upload images');
    })
    .finally(() => {
        // Restore button state
        uploadBtn.innerHTML = originalText;
        uploadBtn.disabled = false;
    });
}

function viewRestaurantDetails(restaurantId) {
    // Implementation for viewing restaurant details
    console.log('Viewing restaurant details for ID:', restaurantId);
}

function editRestaurant(restaurantId) {
    // Implementation for editing restaurant
    console.log('Editing restaurant with ID:', restaurantId);
}

function showRestaurantError(message) {
    const tableBody = document.getElementById('restaurantTable');
    tableBody.innerHTML = `
        <tr>
            <td colspan="7" class="text-center text-danger">
                <i class="fas fa-exclamation-triangle me-2"></i>${message}
            </td>
        </tr>
    `;
}

function updateAdminsTable(admins) {
    const tableBody = document.getElementById('adminTable');
    
    if (admins.length === 0) {
        tableBody.innerHTML = `
            <tr>
                <td colspan="7" class="text-center text-muted">
                    <i class="fas fa-info-circle me-2"></i>No admins found
                </td>
            </tr>
        `;
        return;
    }
    
    tableBody.innerHTML = admins.map(admin => {
        const statusBadge = admin.is_active ? 
            (admin.is_blocked ? '<span class="badge bg-danger">Blocked</span>' : '<span class="badge bg-success">Active</span>') : 
            '<span class="badge bg-secondary">Inactive</span>';
        
        const performanceScore = Math.round((admin.recent_activities * 10 + admin.sessions_this_week * 5) / 15);
        const performanceBadge = performanceScore > 7 ? 'bg-success' : (performanceScore > 4 ? 'bg-warning' : 'bg-danger');
        
        return `
            <tr>
                <td>
                    <div class="d-flex align-items-center">
                        <div class="admin-avatar me-2">
                            ${admin.full_name ? admin.full_name.charAt(0) : admin.username.charAt(0)}
                        </div>
                        <div>
                            <div class="fw-bold">${admin.full_name || admin.username}</div>
                            <small class="text-muted">@${admin.username}</small>
                        </div>
                    </div>
                </td>
                <td>
                    <span class="badge ${admin.role === 'admin' ? 'bg-primary' : 'bg-info'}">${admin.role}</span>
                </td>
                <td>
                    <div class="text-muted small">
                        ${admin.restaurant_name || 'No restaurant assigned'}
                    </div>
                </td>
                <td>
                    <div class="d-flex align-items-center">
                        <span class="badge ${performanceBadge} me-2">${performanceScore}/10</span>
                        <small class="text-muted">${admin.recent_activities} activities</small>
                    </div>
                </td>
                <td>
                    <div class="text-muted small">
                        ${admin.last_login ? new Date(admin.last_login).toLocaleDateString() : 'Never'}
                    </div>
                </td>
                <td>
                    ${statusBadge}
                </td>
                <td>
                    <div class="btn-group btn-group-sm">
                        <button class="btn btn-outline-primary" onclick="viewAdminPerformance(${admin.id})">
                            <i class="fas fa-chart-line"></i>
                        </button>
                        <button class="btn btn-outline-warning" onclick="editAdmin(${admin.id})">
                            <i class="fas fa-edit"></i>
                        </button>
                        <button class="btn btn-outline-${admin.is_blocked ? 'success' : 'danger'}" 
                                onclick="toggleAdminBlock(${admin.id}, ${admin.is_blocked})">
                            <i class="fas fa-${admin.is_blocked ? 'unlock' : 'lock'}"></i>
                        </button>
                        <button class="btn btn-outline-danger" onclick="deleteAdmin(${admin.id}, '${admin.username}')">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                </td>
            </tr>
        `;
    }).join('');
}

function showAdminError(message) {
    const tableBody = document.getElementById('adminTable');
    tableBody.innerHTML = `
        <tr>
            <td colspan="7" class="text-center text-danger">
                <i class="fas fa-exclamation-triangle me-2"></i>${message}
            </td>
        </tr>
    `;
}

function viewAdminPerformance(adminId) {
    // Implementation for viewing admin performance
    console.log('Viewing admin performance for ID:', adminId);
}

function editAdmin(adminId) {
    // Implementation for editing admin
    console.log('Editing admin with ID:', adminId);
}

function toggleAdminBlock(adminId, isBlocked) {
    const action = isBlocked ? 'unblock' : 'block';
    const confirmText = isBlocked ? 'unblock' : 'block';
    
    if (confirm(`Are you sure you want to ${confirmText} this admin?`)) {
        fetch(`/api/super-admin/admins/${adminId}/block`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                blocked: !isBlocked
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showAlert('success', data.message);
                loadAdmins(); // Reload the table
            } else {
                showAlert('error', data.error);
            }
        })
        .catch(error => {
            console.error('Error toggling admin block:', error);
            showAlert('error', 'Failed to update admin status');
        });
    }
}

function deleteAdmin(adminId, adminUsername) {
    if (confirm(`Are you sure you want to delete admin "${adminUsername}"?\n\nThis action will:\n• Permanently delete the admin account\n• Force logout from all active sessions\n• Remove all associated data and activities\n• Cannot be undone\n\nClick OK to proceed with deletion.`)) {
        fetch(`/api/super-admin/admins/${adminId}`, {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json'
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showAlert('success', data.message);
                loadAdmins(); // Reload the table
            } else {
                showAlert('error', data.message || 'Failed to delete admin');
            }
        })
        .catch(error => {
            console.error('Error deleting admin:', error);
            showAlert('error', 'Failed to delete admin');
        });
    }
}

function createRestaurant() {
    const form = document.getElementById('addRestaurantForm');
    const formData = new FormData(form);
    
    // Basic validation
    const name = formData.get('name');
    const phone = formData.get('phone');
    const address = formData.get('address');
    
    if (!name || !phone || !address) {
        showAlert('error', 'Please fill in all required fields (Name, Phone, Address)');
        return;
    }
    
    // Show loading state on button
    const createBtn = document.querySelector('#addRestaurantModal .btn-gradient');
    const originalText = createBtn.innerHTML;
    createBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Creating...';
    createBtn.disabled = true;
    
    // First create the restaurant with all data including images
    fetch('/api/restaurants/super-admin', {
        method: 'POST',
        body: formData // Send FormData directly to handle both text and files
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showAlert('success', data.message || 'Restaurant created successfully!');
            
            // Close modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('addRestaurantModal'));
            modal.hide();
            
            // Reset form
            form.reset();
            
            // Clear image previews
            const logoPreview = document.getElementById('logoPreview');
            const coverPreview = document.getElementById('coverPreview');
            if (logoPreview) logoPreview.style.display = 'none';
            if (coverPreview) coverPreview.style.display = 'none';
            
            // Reload restaurants table
            loadRestaurants();
        } else {
            showAlert('error', data.message || data.error || 'Failed to create restaurant');
        }
    })
    .catch(error => {
        console.error('Error creating restaurant:', error);
        showAlert('error', 'Network error: Failed to create restaurant');
    })
    .finally(() => {
        // Restore button state
        createBtn.innerHTML = originalText;
        createBtn.disabled = false;
    });
}

// Load driver approvals
function loadDriverApprovals() {
    console.log('Loading driver approvals...');
    loadPendingDrivers();
    loadApprovedDrivers();
    initializeDriverApplicationTracking();
}

function initializeDriverApplicationTracking() {
    // Initialize the counter for real-time tracking
    fetch('/api/super-admin/drivers/pending')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                lastDriverApplicationCount = data.drivers.length;
                updatePendingDriversBadge(lastDriverApplicationCount);
            }
        })
        .catch(error => {
            console.error('Error initializing driver application tracking:', error);
        });
}

function refreshRealTimeData() {
    loadDashboardStats();
    loadDriverApprovals();
    updateLastRefreshTime();
    showAlert('success', 'Data refreshed successfully');
}

// Load restaurants into dropdown when modal opens
function loadRestaurantsDropdown() {
    fetch('/api/restaurants/super-admin')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                const restaurantSelect = document.getElementById('restaurantSelect');
                restaurantSelect.innerHTML = '<option value="">Select Restaurant</option>';
                
                data.restaurants.forEach(restaurant => {
                    const option = document.createElement('option');
                    option.value = restaurant.id;
                    option.textContent = restaurant.name;
                    restaurantSelect.appendChild(option);
                });
            } else {
                console.error('Error loading restaurants for dropdown:', data.error);
            }
        })
        .catch(error => {
            console.error('Error loading restaurants for dropdown:', error);
        });
}

// Create new admin
function createAdmin() {
    const form = document.getElementById('addAdminForm');
    const formData = new FormData(form);
    
    // Validate passwords match
    if (formData.get('password') !== formData.get('confirm_password')) {
        showAlert('error', 'Passwords do not match');
        return;
    }
    
    // Prepare data
    const data = {
        username: formData.get('username'),
        email: formData.get('email'),
        full_name: formData.get('full_name'),
        phone: formData.get('phone'),
        role: formData.get('role'),
        restaurant_id: formData.get('restaurant_id') || null,
        password: formData.get('password')
    };
    
    // Basic validation
    if (!data.username || !data.password || !data.full_name) {
        showAlert('error', 'Please fill in all required fields');
        return;
    }
    
    fetch('/api/super-admin/admins', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showAlert('success', data.message);
            
            // Close modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('addAdminModal'));
            modal.hide();
            
            // Reset form
            form.reset();
            
            // Reload admins table
            loadAdmins();
        } else {
            showAlert('error', data.message || data.error);
        }
    })
    .catch(error => {
        console.error('Error creating admin:', error);
        showAlert('error', 'Failed to create admin');
    });
}

function loadPendingDrivers() {
    fetch('/api/super-admin/drivers/pending')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                updatePendingDriversTable(data.drivers);
                document.getElementById('pendingDrivers').textContent = data.drivers.length;
            } else {
                console.error('Error loading pending drivers:', data.error);
            }
        })
        .catch(error => {
            console.error('Error loading pending drivers:', error);
        });
}

function loadApprovedDrivers() {
    fetch('/api/super-admin/drivers/approved')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                const approvedCount = data.drivers.length;
                const activeCount = data.drivers.filter(d => d.is_active).length;
                const availableCount = data.drivers.filter(d => d.is_active && d.is_available).length;
                
                const approvedEl = document.getElementById('approvedDrivers');
                const activeEl = document.getElementById('activeDrivers');
                const availableEl = document.getElementById('availableDrivers');
                
                if (approvedEl) approvedEl.textContent = approvedCount;
                if (activeEl) activeEl.textContent = activeCount;
                if (availableEl) availableEl.textContent = availableCount;
                
                updateApprovedDriversTable(data.drivers);
            } else {
                console.error('Error loading approved drivers:', data.error);
            }
        })
        .catch(error => {
            console.error('Error loading approved drivers:', error);
        });
}

function updatePendingDriversTable(drivers) {
    const tableBody = document.getElementById('pendingDriversTable');
    
    if (drivers.length === 0) {
        tableBody.innerHTML = `
            <tr>
                <td colspan="6" class="text-center text-muted">
                    <i class="fas fa-info-circle me-2"></i>No pending driver applications
                </td>
            </tr>
        `;
        return;
    }
    
    tableBody.innerHTML = drivers.map(driver => {
        return `
            <tr>
                <td>
                    <div class="fw-bold">${driver.name}</div>
                </td>
                <td>
                    <span class="text-muted">${driver.phone_number}</span>
                </td>
                <td>
                    <i class="fas fa-${getVehicleIcon(driver.vehicle_type)} me-1"></i>
                    ${driver.vehicle_type}
                </td>
                <td>
                    <span class="text-muted">${formatDate(driver.created_at)}</span>
                </td>
                <td>
                    <button class="btn btn-sm btn-outline-info" onclick="viewDriverDocuments('${driver.id}')">
                        <i class="fas fa-eye"></i> View
                    </button>
                </td>
                <td>
                    <div class="btn-group btn-group-sm">
                        <button class="btn btn-success" onclick="approveDriver('${driver.id}')">
                            <i class="fas fa-check"></i> Approve
                        </button>
                        <button class="btn btn-danger" onclick="rejectDriver('${driver.id}')">
                            <i class="fas fa-times"></i> Reject
                        </button>
                    </div>
                </td>
            </tr>
        `;
    }).join('');
}

function updateApprovedDriversTable(drivers) {
    // This will be called from the driver approval management section
    const approvedTableBody = document.getElementById('approvedDriversTable');
    
    if (!approvedTableBody) {
        // Table doesn't exist yet, will be created when needed
        return;
    }
    
    if (drivers.length === 0) {
        approvedTableBody.innerHTML = `
            <tr>
                <td colspan="6" class="text-center text-muted">
                    <i class="fas fa-info-circle me-2"></i>No approved drivers found
                </td>
            </tr>
        `;
        return;
    }
    
    approvedTableBody.innerHTML = drivers.map(driver => {
        const statusBadge = driver.is_active ? 
            (driver.is_available ? '<span class="badge bg-success">Available</span>' : '<span class="badge bg-warning">Busy</span>') : 
            '<span class="badge bg-secondary">Inactive</span>';
        
        return `
            <tr>
                <td>
                    <div class="d-flex align-items-center">
                        <div class="avatar-circle bg-success text-white me-2">
                            ${driver.name.charAt(0)}
                        </div>
                        <div>
                            <div class="fw-bold">${driver.name}</div>
                            <small class="text-muted">${driver.phone_number}</small>
                        </div>
                    </div>
                </td>
                <td>
                    ${statusBadge}
                </td>
                <td>
                    <i class="fas fa-${getVehicleIcon(driver.vehicle_type)} me-1"></i>
                    ${driver.vehicle_type}
                </td>
                <td>
                    <span class="text-muted">${formatDate(driver.created_at)}</span>
                </td>
                <td>
                    <div class="btn-group btn-group-sm">
                        <button class="btn btn-outline-info" onclick="viewDriverDocuments('${driver.id}')">
                            <i class="fas fa-eye"></i> View
                        </button>
                        <button class="btn btn-outline-danger" onclick="deleteDriver('${driver.id}', '${driver.name}')">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                </td>
            </tr>
        `;
    }).join('');
}

function deleteDriver(driverId, driverName) {
    if (confirm(`Are you sure you want to delete driver "${driverName}"? This action cannot be undone.`)) {
        fetch(`/api/super-admin/drivers/${driverId}`, {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json'
            }
        })
        .then(response => {
            // Check if response is a redirect (authentication issue)
            if (response.redirected && response.url.includes('/superadmin/login')) {
                showAlert('error', 'Session expired. Please log in again.');
                window.location.href = '/superadmin/login';
                return;
            }
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            return response.json();
        })
        .then(data => {
            if (!data) return; // Handle redirect case
            
            if (data.success) {
                showAlert('success', `Driver "${driverName}" deleted successfully`);
                loadDriverApprovals();
                loadDriverLocationDetails();
            } else {
                showAlert('error', data.message || data.error || 'Failed to delete driver');
            }
        })
        .catch(error => {
            console.error('Error deleting driver:', error);
            showAlert('error', `Failed to delete driver: ${error.message}`);
        });
    }
}

function approveDriver(driverId) {
    fetch(`/api/super-admin/drivers/${driverId}/approve`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showAlert('success', 'Driver approved successfully');
            loadDriverApprovals();
        } else {
            showAlert('error', data.message || 'Failed to approve driver');
        }
    })
    .catch(error => {
        console.error('Error approving driver:', error);
        showAlert('error', 'Failed to approve driver');
    });
}

function rejectDriver(driverId) {
    const reason = prompt('Please provide a reason for rejection:');
    if (reason) {
        fetch(`/api/super-admin/drivers/${driverId}/reject`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ reason })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showAlert('success', 'Driver rejected successfully');
                loadDriverApprovals();
            } else {
                showAlert('error', data.message || 'Failed to reject driver');
            }
        })
        .catch(error => {
            console.error('Error rejecting driver:', error);
            showAlert('error', 'Failed to reject driver');
        });
    }
}

function viewDriverDocuments(driverId) {
    fetch(`/api/super-admin/drivers/${driverId}/documents`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showDriverDocumentsModal(data);
            } else {
                showAlert('error', data.message || 'Failed to load driver documents');
            }
        })
        .catch(error => {
            console.error('Error loading driver documents:', error);
            showAlert('error', 'Failed to load driver documents');
        });
}

function showDriverDocumentsModal(data) {
    const documents = data.documents || [];
    const driverInfo = data.driver_info || {};
    
    const modalHtml = `
        <div class="modal fade" id="driverDocumentsModal" tabindex="-1">
            <div class="modal-dialog modal-lg">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">
                            <i class="fas fa-file-alt"></i> Driver Documents
                            ${driverInfo.driver_name ? ` - ${driverInfo.driver_name}` : ''}
                        </h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        ${driverInfo.driver_name ? `
                            <div class="card mb-3">
                                <div class="card-header">
                                    <h6 class="mb-0"><i class="fas fa-user"></i> Driver Information</h6>
                                </div>
                                <div class="card-body">
                                    <div class="row">
                                        <div class="col-md-6">
                                            <p><strong>Name:</strong> ${driverInfo.driver_name}</p>
                                            <p><strong>Phone:</strong> ${driverInfo.phone_number || 'Not provided'}</p>
                                        </div>
                                        <div class="col-md-6">
                                            <p><strong>Vehicle Type:</strong> ${driverInfo.vehicle_type || 'Not specified'}</p>
                                            <p><strong>Status:</strong> 
                                                <span class="badge ${driverInfo.approval_status === 'approved' ? 'bg-success' : 
                                                    driverInfo.approval_status === 'pending' ? 'bg-warning' : 'bg-danger'}">
                                                    ${driverInfo.approval_status || 'Unknown'}
                                                </span>
                                            </p>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        ` : ''}
                        
                        <div class="row">
                            ${documents.length > 0 ? documents.map(doc => `
                                <div class="col-md-6 mb-3">
                                    <div class="card">
                                        <div class="card-header">
                                            <h6 class="mb-0">
                                                <i class="fas fa-file"></i> ${doc.document_type}
                                            </h6>
                                        </div>
                                        <div class="card-body text-center">
                                            ${doc.document_url ? `
                                                <img src="${doc.document_url}" class="img-fluid rounded" alt="${doc.document_type}" 
                                                     style="max-height: 200px; cursor: pointer;" 
                                                     onclick="window.open('${doc.document_url}', '_blank')">
                                                <p class="mt-2 mb-0">
                                                    <small class="text-muted">Click to view full size</small>
                                                </p>
                                            ` : `
                                                <div class="text-muted">
                                                    <i class="fas fa-file-times fa-3x"></i>
                                                    <p class="mt-2">No document uploaded</p>
                                                </div>
                                            `}
                                        </div>
                                    </div>
                                </div>
                            `).join('') : `
                                <div class="col-12">
                                    <div class="alert alert-info text-center">
                                        <i class="fas fa-info-circle"></i>
                                        No documents have been uploaded for this driver.
                                    </div>
                                </div>
                            `}
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
    
    // Add new modal
    document.body.insertAdjacentHTML('beforeend', modalHtml);
    
    // Show modal
    const modal = new bootstrap.Modal(document.getElementById('driverDocumentsModal'));
    modal.show();
}

function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString();
}

// Load analytics (placeholder - implement based on existing functionality)
function loadAnalytics() {
    // Implementation will be similar to existing analytics loading
    console.log('Loading analytics...');
}

// Utility function to show alerts
function showAlert(type, message) {
    const alertHtml = `
        <div class="alert alert-${type === 'error' ? 'danger' : type} alert-dismissible fade show position-fixed" 
             style="top: 20px; right: 20px; z-index: 9999; min-width: 300px;">
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `;
    
    const alertContainer = document.createElement('div');
    alertContainer.innerHTML = alertHtml;
    document.body.appendChild(alertContainer);
    
    // Auto-remove alert after 5 seconds
    setTimeout(() => {
        const alert = alertContainer.querySelector('.alert');
        if (alert) {
            alert.remove();
        }
        alertContainer.remove();
    }, 5000);
}

// Initialize real-time updates when page loads
window.addEventListener('load', function() {
    updateLastRefreshTime();
});

// Setup change password form handler
function setupChangePasswordForm() {
    const form = document.getElementById('changePasswordForm');
    if (form) {
        form.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const currentPassword = document.getElementById('currentPassword').value;
            const newPassword = document.getElementById('newPassword').value;
            const confirmPassword = document.getElementById('confirmPassword').value;
            
            // Validate passwords
            if (newPassword !== confirmPassword) {
                showAlert('error', 'New passwords do not match');
                return;
            }
            
            if (newPassword.length < 6) {
                showAlert('error', 'Password must be at least 6 characters long');
                return;
            }
            
            // Submit password change
            fetch('/api/super-admin/change-password', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    current_password: currentPassword,
                    new_password: newPassword
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    showAlert('success', 'Password changed successfully');
                    form.reset();
                } else {
                    showAlert('error', data.message || 'Failed to change password');
                }
            })
            .catch(error => {
                console.error('Error changing password:', error);
                showAlert('error', 'Failed to change password');
            });
        });
    }
}