// Enhanced Admin Dashboard JavaScript
let dashboardCharts = {};
let dashboardData = {
    totalOrders: 0,
    totalRevenue: 0,
    pendingOrders: 0,
    activeDrivers: 0,
    recentOrders: []
};

// Initialize Dashboard
function initializeDashboard() {
    loadDashboardData();
    loadOrdersTab();
    setupCharts();
    updateDateTime();
    setInterval(updateDateTime, 60000);
    
    // Load categories if function exists
    if (typeof loadCategories === 'function') {
        loadCategories();
    }
<<<<<<< HEAD
=======
    
    // Start live location tracking
    startLiveLocationTracking();
}

// Live Location Tracking System
let liveLocationMap = null;
let driverMarkers = {};

function startLiveLocationTracking() {
    // Update driver locations every 30 seconds
    setInterval(updateDriverLocations, 30000);
    updateDriverLocations(); // Initial load
}

async function updateDriverLocations() {
    try {
        const response = await fetch('/api/drivers/live-locations');
        const data = await response.json();
        
        if (data.locations && data.locations.length > 0) {
            // Update driver location indicators in the dashboard
            updateDriverLocationIndicators(data.locations);
            
            // Update live tracking map if visible
            if (liveLocationMap) {
                updateLiveTrackingMap(data.locations);
            }
        }
    } catch (error) {
        console.error('Error updating driver locations:', error);
    }
}

function updateDriverLocationIndicators(locations) {
    // Update active drivers count with location info
    const activeDriversWithLocation = locations.filter(loc => loc.is_available).length;
    const activeDriversElement = document.getElementById('activeDrivers');
    if (activeDriversElement) {
        activeDriversElement.textContent = activeDriversWithLocation;
    }
    
    // Show live tracking button if drivers are active
    const trackingButton = document.getElementById('liveTrackingButton');
    if (!trackingButton && locations.length > 0) {
        const dashboardStats = document.querySelector('.row.mb-4');
        if (dashboardStats) {
            const trackingCard = document.createElement('div');
            trackingCard.className = 'col-md-3 mb-3';
            trackingCard.innerHTML = `
                <div class="card stat-card h-100">
                    <div class="card-body text-center">
                        <i class="fas fa-map-marked-alt fa-2x mb-3"></i>
                        <h3 class="mb-1">${locations.length}</h3>
                        <p class="mb-0">Live Tracking</p>
                        <button class="btn btn-sm btn-primary mt-2" id="liveTrackingButton" onclick="showLiveTrackingMap()">
                            <i class="fas fa-eye"></i> View Map
                        </button>
                    </div>
                </div>
            `;
            dashboardStats.appendChild(trackingCard);
        }
    }
}

function showLiveTrackingMap() {
    const mapModal = document.createElement('div');
    mapModal.className = 'modal fade';
    mapModal.id = 'liveTrackingModal';
    mapModal.innerHTML = `
        <div class="modal-dialog modal-xl">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title">
                        <i class="fas fa-map-marked-alt text-primary me-2"></i>
                        Live Driver Tracking
                    </h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                </div>
                <div class="modal-body">
                    <div id="liveTrackingMap" style="height: 500px; width: 100%;"></div>
                    <div class="mt-3">
                        <h6>Active Drivers:</h6>
                        <div id="driverList" class="row"></div>
                    </div>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                    <button type="button" class="btn btn-primary" onclick="refreshDriverLocations()">
                        <i class="fas fa-sync"></i> Refresh
                    </button>
                </div>
            </div>
        </div>
    `;
    
    // Remove existing modal if any
    const existingModal = document.getElementById('liveTrackingModal');
    if (existingModal) {
        existingModal.remove();
    }
    
    // Add modal to page
    document.body.appendChild(mapModal);
    
    // Show modal
    const modal = new bootstrap.Modal(mapModal);
    modal.show();
    
    // Initialize map when modal is shown
    mapModal.addEventListener('shown.bs.modal', function() {
        initializeLiveTrackingMap();
    });
    
    // Clean up when modal is hidden
    mapModal.addEventListener('hidden.bs.modal', function() {
        if (liveLocationMap) {
            liveLocationMap.remove();
            liveLocationMap = null;
        }
        driverMarkers = {};
        mapModal.remove();
    });
}

function initializeLiveTrackingMap() {
    // Create map centered on Addis Ababa
    liveLocationMap = L.map('liveTrackingMap').setView([9.145, 40.489658], 12);
    
    // Add tile layer
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors'
    }).addTo(liveLocationMap);
    
    // Load and display current driver locations
    updateDriverLocations();
}

function updateLiveTrackingMap(locations) {
    if (!liveLocationMap) return;
    
    // Clear existing markers
    Object.values(driverMarkers).forEach(marker => marker.remove());
    driverMarkers = {};
    
    // Add markers for each driver
    locations.forEach(driver => {
        const icon = L.divIcon({
            html: `<div style="background: ${driver.is_available ? '#28a745' : '#dc3545'}; color: white; border-radius: 50%; width: 30px; height: 30px; display: flex; align-items: center; justify-content: center; font-size: 12px; font-weight: bold;">${driver.driver_name.charAt(0)}</div>`,
            className: 'driver-marker',
            iconSize: [30, 30]
        });
        
        const marker = L.marker([driver.latitude, driver.longitude], { icon })
            .addTo(liveLocationMap);
        
        const popupContent = `
            <div>
                <h6><strong>${driver.driver_name}</strong></h6>
                <p><strong>Vehicle:</strong> ${driver.vehicle_type}</p>
                <p><strong>Status:</strong> ${driver.is_available ? 'Available' : 'Busy'}</p>
                ${driver.current_order ? `
                    <p><strong>Current Order:</strong> #${driver.current_order.id}</p>
                    <p><strong>Customer:</strong> ${driver.current_order.customer_name}</p>
                ` : ''}
                <p><strong>Last Update:</strong> ${new Date(driver.last_update).toLocaleTimeString()}</p>
                <button class="btn btn-sm btn-primary" onclick="requestLocationUpdate(${driver.driver_id})">
                    <i class="fas fa-sync"></i> Request Update
                </button>
            </div>
        `;
        
        marker.bindPopup(popupContent);
        driverMarkers[driver.driver_id] = marker;
    });
    
    // Update driver list
    updateDriverList(locations);
}

function updateDriverList(locations) {
    const driverList = document.getElementById('driverList');
    if (!driverList) return;
    
    driverList.innerHTML = '';
    
    locations.forEach(driver => {
        const driverCard = document.createElement('div');
        driverCard.className = 'col-md-4 mb-2';
        driverCard.innerHTML = `
            <div class="card">
                <div class="card-body p-2">
                    <h6 class="card-title mb-1">${driver.driver_name}</h6>
                    <p class="card-text small mb-1">
                        <span class="badge bg-${driver.is_available ? 'success' : 'danger'}">${driver.is_available ? 'Available' : 'Busy'}</span>
                        ${driver.vehicle_type}
                    </p>
                    ${driver.current_order ? `<p class="card-text small mb-0">Order #${driver.current_order.id}</p>` : ''}
                    <button class="btn btn-sm btn-outline-primary" onclick="focusOnDriver(${driver.driver_id}, ${driver.latitude}, ${driver.longitude})">
                        <i class="fas fa-crosshairs"></i> Focus
                    </button>
                </div>
            </div>
        `;
        driverList.appendChild(driverCard);
    });
}

function focusOnDriver(driverId, lat, lng) {
    if (liveLocationMap && driverMarkers[driverId]) {
        liveLocationMap.setView([lat, lng], 15);
        driverMarkers[driverId].openPopup();
    }
}

async function requestLocationUpdate(driverId) {
    try {
        const response = await fetch(`/api/drivers/${driverId}/request-location`, {
            method: 'POST'
        });
        
        const result = await response.json();
        
        if (response.ok) {
            alert('Location update requested successfully!');
        } else {
            alert(`Error: ${result.error}`);
        }
    } catch (error) {
        console.error('Error requesting location update:', error);
        alert('Failed to request location update');
    }
}

function refreshDriverLocations() {
    updateDriverLocations();
    if (liveLocationMap) {
        setTimeout(() => {
            liveLocationMap.invalidateSize();
        }, 100);
    }
>>>>>>> 6dd25ab (Initial commit from Replit)
}

// Load Dashboard Data
async function loadDashboardData() {
    try {
        // Load orders data
        const ordersResponse = await fetch('/api/orders');
        const ordersData = await ordersResponse.json();
        
        // Load drivers data
        const driversResponse = await fetch('/api/drivers');
        const driversData = await driversResponse.json();
        
        // Process data
        processDashboardData(ordersData.orders || [], driversData || []);
        updateDashboardStats();
        updateCharts();
        updateRecentOrders();
        
    } catch (error) {
        console.error('Error loading dashboard data:', error);
    }
}

// Process Dashboard Data
function processDashboardData(orders, drivers) {
    dashboardData.totalOrders = orders.length;
    dashboardData.totalRevenue = orders.reduce((sum, order) => sum + order.total_amount, 0);
    dashboardData.pendingOrders = orders.filter(order => order.status === 'pending').length;
    dashboardData.activeDrivers = drivers.filter(driver => driver.is_active && driver.is_available).length;
    dashboardData.recentOrders = orders.slice(0, 5); // Last 5 orders
}

// Update Dashboard Stats
function updateDashboardStats() {
    document.getElementById('totalOrders').textContent = dashboardData.totalOrders;
    document.getElementById('totalRevenue').textContent = `ETB ${dashboardData.totalRevenue.toFixed(2)}`;
    document.getElementById('pendingOrders').textContent = dashboardData.pendingOrders;
    document.getElementById('activeDrivers').textContent = dashboardData.activeDrivers;
}

// Setup Charts
function setupCharts() {
    // Sales Chart
    const salesCtx = document.getElementById('salesChart');
    if (salesCtx) {
        dashboardCharts.sales = new Chart(salesCtx, {
            type: 'line',
            data: {
                labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
                datasets: [{
                    label: 'Sales (ETB)',
                    data: [1200, 1900, 3000, 5000, 2000, 3000],
                    borderColor: '#667eea',
                    backgroundColor: 'rgba(102, 126, 234, 0.1)',
                    tension: 0.4
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

    // Status Chart
    const statusCtx = document.getElementById('statusChart');
    if (statusCtx) {
        dashboardCharts.status = new Chart(statusCtx, {
            type: 'doughnut',
            data: {
                labels: ['Pending', 'Confirmed', 'Preparing', 'Delivered', 'Cancelled'],
                datasets: [{
                    data: [12, 19, 8, 25, 3],
                    backgroundColor: [
                        '#ffc107',
                        '#198754',
                        '#0dcaf0',
                        '#0d6efd',
                        '#dc3545'
                    ]
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
}

// Update Charts with Real Data
function updateCharts() {
    // Update status chart with real data
    if (dashboardCharts.status) {
        const statusCounts = {
            pending: 0,
            confirmed: 0,
            preparing: 0,
            delivered: 0,
            cancelled: 0
        };
        
        // Count orders by status (you'll need to pass orders data here)
        // For now, using sample data
        dashboardCharts.status.data.datasets[0].data = [
            statusCounts.pending || 5,
            statusCounts.confirmed || 8,
            statusCounts.preparing || 3,
            statusCounts.delivered || 15,
            statusCounts.cancelled || 2
        ];
        dashboardCharts.status.update();
    }
}

// Show Customer Location Function
function showCustomerLocation(lat, lng, customerName) {
    const mapModal = document.createElement('div');
    mapModal.className = 'modal fade';
    mapModal.id = 'locationModal';
    mapModal.innerHTML = `
        <div class="modal-dialog modal-lg">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title">
                        <i class="fas fa-map-marker-alt text-success me-2"></i>
                        ${customerName}'s Location
                    </h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                </div>
                <div class="modal-body">
                    <div class="mb-3">
                        <strong>Coordinates:</strong> ${lat.toFixed(6)}, ${lng.toFixed(6)}
                    </div>
                    <div class="row">
                        <div class="col-md-6 mb-3">
                            <a href="https://www.google.com/maps?q=${lat},${lng}" target="_blank" class="btn btn-primary w-100">
                                <i class="fab fa-google me-2"></i>Open in Google Maps
                            </a>
                        </div>
                        <div class="col-md-6 mb-3">
                            <a href="https://maps.google.com/maps?q=${lat},${lng}&t=k&z=18" target="_blank" class="btn btn-info w-100">
                                <i class="fas fa-satellite me-2"></i>Open in Google Satellite
                            </a>
                        </div>
                    </div>
                    <div class="mb-3">
                        <button onclick="copyCoordinates('${lat},${lng}')" class="btn btn-outline-secondary">
                            <i class="fas fa-copy me-2"></i>Copy Coordinates
                        </button>
                    </div>
                    <div class="embed-responsive" style="height: 400px;">
                        <iframe 
                            src="https://maps.google.com/maps?q=${lat},${lng}&t=k&z=18&ie=UTF8&iwloc=&output=embed"
                            style="border: 1px solid black; width: 100%; height: 100%;"
                            frameborder="0"
                            scrolling="no"
                            marginheight="0"
                            marginwidth="0">
                        </iframe>
                    </div>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                </div>
            </div>
        </div>
    `;
    
    // Remove existing modal if any
    const existingModal = document.getElementById('locationModal');
    if (existingModal) {
        existingModal.remove();
    }
    
    // Add modal to page
    document.body.appendChild(mapModal);
    
    // Show modal
    const modal = new bootstrap.Modal(mapModal);
    modal.show();
    
    // Clean up when modal is hidden
    mapModal.addEventListener('hidden.bs.modal', function () {
        mapModal.remove();
    });
}

// Copy coordinates to clipboard
function copyCoordinates(coordinates) {
    navigator.clipboard.writeText(coordinates).then(function() {
        // Show temporary success message
        const btn = event.target.closest('button');
        const originalText = btn.innerHTML;
        btn.innerHTML = '<i class="fas fa-check me-2"></i>Copied!';
        btn.classList.add('btn-success');
        btn.classList.remove('btn-outline-secondary');
        
        setTimeout(() => {
            btn.innerHTML = originalText;
            btn.classList.remove('btn-success');
            btn.classList.add('btn-outline-secondary');
        }, 2000);
    }).catch(function(err) {
        alert('Failed to copy coordinates: ' + err);
    });
}

// Show payment image in modal
function showPaymentImage(imageUrl) {
    const imageModal = document.createElement('div');
    imageModal.className = 'modal fade';
    imageModal.id = 'paymentImageModal';
    imageModal.innerHTML = `
        <div class="modal-dialog modal-lg">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title">
                        <i class="fas fa-receipt text-success me-2"></i>
                        Payment Screenshot
                    </h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                </div>
                <div class="modal-body text-center">
                    <img src="${imageUrl}" alt="Payment Screenshot" style="max-width: 100%; height: auto; border-radius: 8px;">
                    <div class="mt-3">
                        <a href="${imageUrl}" target="_blank" class="btn btn-primary">
                            <i class="fas fa-external-link-alt me-2"></i>Open Full Size
                        </a>
                    </div>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                </div>
            </div>
        </div>
    `;
    
    // Remove existing modal if any
    const existingModal = document.getElementById('paymentImageModal');
    if (existingModal) {
        existingModal.remove();
    }
    
    // Add modal to page
    document.body.appendChild(imageModal);
    
    // Show modal
    const modal = new bootstrap.Modal(imageModal);
    modal.show();
    
    // Clean up when modal is hidden
    imageModal.addEventListener('hidden.bs.modal', function () {
        imageModal.remove();
    });
}

// Update Recent Orders Table
function updateRecentOrders() {
    const tbody = document.getElementById('recentOrdersTable');
    if (!tbody) return;
    
    tbody.innerHTML = '';
    
    if (dashboardData.recentOrders.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="6" class="text-center py-4 text-muted">
                    No recent orders found
                </td>
            </tr>
        `;
        return;
    }
    
    dashboardData.recentOrders.forEach(order => {
        const row = document.createElement('tr');
        const statusBadge = getStatusBadge(order.status);
        const timeAgo = getTimeAgo(new Date(order.created_at));
        
        // Check if order has location data
        const hasLocation = order.location_lat && order.location_lng;
        const locationButton = hasLocation ? 
            `<button class="btn btn-sm btn-outline-success me-1" onclick="showCustomerLocation(${order.location_lat}, ${order.location_lng}, '${order.customer_name}')" title="View Location">
                <i class="fas fa-map-marker-alt"></i>
            </button>` : '';

        row.innerHTML = `
            <td>#${order.id}</td>
            <td>${order.customer_name}</td>
            <td>ETB ${order.total_amount.toFixed(2)}</td>
            <td>${statusBadge}</td>
            <td>${timeAgo}</td>
            <td>
                ${locationButton}
                <button class="btn btn-sm btn-outline-primary" onclick="viewOrderDetails(${order.id})">
                    <i class="fas fa-eye"></i>
                </button>
            </td>
        `;
        tbody.appendChild(row);
    });
}

// Get Status Badge
function getStatusBadge(status) {
    const badges = {
        pending: '<span class="badge bg-warning text-dark">Pending</span>',
        confirmed: '<span class="badge bg-success">Confirmed</span>',
        preparing: '<span class="badge bg-info">Preparing</span>',
        out_for_delivery: '<span class="badge bg-primary">Out for Delivery</span>',
        delivered: '<span class="badge bg-success">Delivered</span>',
        cancelled: '<span class="badge bg-danger">Cancelled</span>'
    };
    return badges[status] || '<span class="badge bg-secondary">Unknown</span>';
}

// Get Time Ago
function getTimeAgo(date) {
    const now = new Date();
    const diffInSeconds = Math.floor((now - date) / 1000);
    
    if (diffInSeconds < 60) return 'Just now';
    if (diffInSeconds < 3600) return `${Math.floor(diffInSeconds / 60)}m ago`;
    if (diffInSeconds < 86400) return `${Math.floor(diffInSeconds / 3600)}h ago`;
    return `${Math.floor(diffInSeconds / 86400)}d ago`;
}

// View Order Details
async function viewOrderDetails(orderId) {
    try {
        const response = await fetch(`/api/orders/${orderId}`);
        const order = await response.json();
        
        // Check if order has location data
        const hasLocation = order.location_lat && order.location_lng;
        const locationSection = hasLocation ? `
            <div class="col-12 mb-3">
                <h6>Customer Live Location</h6>
                <div class="d-flex gap-2 align-items-center">
                    <span class="badge bg-success">📍 Live Location Available</span>
                    <button class="btn btn-sm btn-outline-success" onclick="showCustomerLocation(${order.location_lat}, ${order.location_lng}, '${order.customer_name}')">
                        <i class="fas fa-satellite me-1"></i>View on Satellite Map
                    </button>
                </div>
                <small class="text-muted">Coordinates: ${order.location_lat.toFixed(6)}, ${order.location_lng.toFixed(6)}</small>
            </div>
        ` : '';

        const modalContent = document.getElementById('orderDetailsContent');
        modalContent.innerHTML = `
            ${locationSection}
            <div class="row">
                <div class="col-md-6">
                    <h6>Customer Information</h6>
                    <p><strong>Name:</strong> ${order.customer_name}</p>
                    <p><strong>Phone:</strong> ${order.customer_phone}</p>
                    <p><strong>Address:</strong> ${order.customer_address}</p>
                    <p><strong>Payment:</strong> ${order.payment_method}</p>
                    ${order.transaction_id ? `<p><strong>Transaction ID:</strong> ${order.transaction_id}</p>` : ''}
                    ${order.transaction_image_url ? `
                        <div class="mt-2">
                            <strong>Payment Screenshot:</strong><br>
                            <img src="${order.transaction_image_url}" alt="Payment Screenshot" style="max-width: 200px; max-height: 200px; border-radius: 8px; cursor: pointer;" onclick="showPaymentImage('${order.transaction_image_url}')">
                        </div>
                    ` : ''}
                </div>
                <div class="col-md-6">
                    <h6>Order Information</h6>
                    <p><strong>Order ID:</strong> #${order.id}</p>
                    <p><strong>Status:</strong> ${getStatusBadge(order.status)}</p>
                    <p><strong>Total:</strong> ETB ${order.total_amount.toFixed(2)}</p>
                    <p><strong>Date:</strong> ${new Date(order.created_at).toLocaleString()}</p>
                </div>
            </div>
            <hr>
            <h6>Order Items</h6>
            <div class="table-responsive">
                <table class="table table-sm">
                    <thead>
                        <tr>
                            <th>Item</th>
                            <th>Quantity</th>
                            <th>Price</th>
                            <th>Total</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${order.items.map(item => `
                            <tr>
                                <td>${item.name}</td>
                                <td>${item.quantity}</td>
                                <td>ETB ${item.price.toFixed(2)}</td>
                                <td>ETB ${(item.price * item.quantity).toFixed(2)}</td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
        `;
        
        const modal = new bootstrap.Modal(document.getElementById('orderDetailsModal'));
        modal.show();
        
    } catch (error) {
        console.error('Error loading order details:', error);
    }
}

// Update Date Time
function updateDateTime() {
    const now = new Date();
    const options = { 
        weekday: 'long', 
        year: 'numeric', 
        month: 'long', 
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    };
    const dateTimeElement = document.getElementById('currentDateTime');
    if (dateTimeElement) {
        dateTimeElement.textContent = now.toLocaleDateString('en-US', options);
    }
}

// Switch Tab Function
function switchToTab(tabName) {
    const tabLink = document.querySelector(`[href="#${tabName}"]`);
    if (tabLink) {
        const tab = new bootstrap.Tab(tabLink);
        tab.show();
    }
}

// Update Order Status Function
async function updateOrderStatus(orderId, newStatus) {
    try {
        const response = await fetch(`/api/orders/${orderId}/status`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ status: newStatus })
        });
        
        const result = await response.json();
        
        if (response.ok) {
            // Show success message
            alert(`Order #${orderId} status updated to ${newStatus}`);
            // Reload data
            loadDashboardData();
            loadOrdersTab();
        } else {
            alert(`Error: ${result.error || 'Failed to update order status'}`);
        }
    } catch (error) {
        console.error('Error updating order status:', error);
        alert('Failed to update order status. Please try again.');
    }
}

<<<<<<< HEAD
=======
// Assign Delivery Bot to Order
async function assignDeliveryBot(orderId) {
    try {
        const response = await fetch(`/api/orders/${orderId}/assign-bot`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        const result = await response.json();
        
        if (response.ok) {
            alert(`🤖 Delivery Bot assigned to Order #${orderId}`);
            loadDashboardData();
            loadOrdersTab();
        } else {
            alert(`Error: ${result.error || 'Failed to assign delivery bot'}`);
        }
    } catch (error) {
        console.error('Error assigning delivery bot:', error);
        alert('Failed to assign delivery bot. Please try again.');
    }
}

// Assign Human Driver to Order
async function assignHumanDriver(orderId) {
    try {
        const response = await fetch('/api/drivers');
        const drivers = await response.json();
        const availableDrivers = drivers.filter(d => d.is_available && d.is_approved && d.name !== "Delivery Bot");
        
        if (availableDrivers.length === 0) {
            alert('❌ No available human drivers found');
            return;
        }
        
        let driversList = 'Available Drivers:\n';
        availableDrivers.forEach((driver, index) => {
            driversList += `${index + 1}. ${driver.name} (${driver.vehicle_type})\n`;
        });
        
        const choice = prompt(driversList + '\nEnter driver number:');
        const driverIndex = parseInt(choice) - 1;
        
        if (driverIndex >= 0 && driverIndex < availableDrivers.length) {
            const selectedDriver = availableDrivers[driverIndex];
            
            const assignResponse = await fetch(`/api/drivers/${selectedDriver.id}/assign/${orderId}`, {
                method: 'POST'
            });
            
            const assignResult = await assignResponse.json();
            
            if (assignResponse.ok) {
                alert(`👤 ${selectedDriver.name} assigned to Order #${orderId}`);
                loadDashboardData();
                loadOrdersTab();
            } else {
                alert(`Error: ${assignResult.error || 'Failed to assign driver'}`);
            }
        }
    } catch (error) {
        console.error('Error assigning human driver:', error);
        alert('Failed to assign human driver. Please try again.');
    }
}

>>>>>>> 6dd25ab (Initial commit from Replit)
// Load Orders Tab
async function loadOrdersTab() {
    try {
        const response = await fetch('/api/orders');
        const data = await response.json();
        const orders = data.orders || [];
        
        const tbody = document.getElementById('ordersTable');
        if (!tbody) return;
        
        tbody.innerHTML = '';
        
        if (orders.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="8" class="text-center py-4 text-muted">
                        No orders found
                    </td>
                </tr>
            `;
            return;
        }
        
        orders.forEach(order => {
            const row = document.createElement('tr');
            const statusBadge = getStatusBadge(order.status);
            const itemsList = order.items.map(item => `${item.name} (x${item.quantity})`).join(', ');
            
            // Check if order has location data
            const hasLocation = order.location_lat && order.location_lng;
            const locationButton = hasLocation ? 
                `<button class="btn btn-sm btn-outline-success me-1" onclick="showCustomerLocation(${order.location_lat}, ${order.location_lng}, '${order.customer_name}')" title="View Customer Location">
                    <i class="fas fa-map-marker-alt"></i>
                </button>` : '';

            row.innerHTML = `
                <td>#${order.id}</td>
                <td>${order.customer_name}</td>
                <td>${order.customer_phone}</td>
                <td title="${itemsList}">${itemsList.length > 50 ? itemsList.substring(0, 50) + '...' : itemsList}</td>
                <td>ETB ${order.total_amount.toFixed(2)}</td>
                <td>${statusBadge}</td>
                <td>${new Date(order.created_at).toLocaleDateString()}</td>
                <td>
                    <div class="btn-group">
                        ${locationButton}
                        <button class="btn btn-sm btn-outline-primary" onclick="viewOrderDetails(${order.id})" title="View Details">
                            <i class="fas fa-eye"></i>
                        </button>
                        <button class="btn btn-sm btn-outline-secondary dropdown-toggle" data-bs-toggle="dropdown" title="Update Status">
                            <i class="fas fa-edit"></i>
                        </button>
                        <ul class="dropdown-menu">
                            <li><a class="dropdown-item" href="#" onclick="updateOrderStatus(${order.id}, 'pending')">
                                <i class="fas fa-clock text-warning me-2"></i>Pending
                            </a></li>
                            <li><a class="dropdown-item" href="#" onclick="updateOrderStatus(${order.id}, 'confirmed')">
                                <i class="fas fa-check text-success me-2"></i>Confirmed
                            </a></li>
                            <li><a class="dropdown-item" href="#" onclick="updateOrderStatus(${order.id}, 'preparing')">
                                <i class="fas fa-utensils text-info me-2"></i>Preparing
                            </a></li>
<<<<<<< HEAD
=======
                            <li><hr class="dropdown-divider"></li>
                            <li><a class="dropdown-item" href="#" onclick="assignDeliveryBot(${order.id})">
                                <i class="fas fa-robot text-primary me-2"></i>🤖 Assign Delivery Bot
                            </a></li>
                            <li><a class="dropdown-item" href="#" onclick="assignHumanDriver(${order.id})">
                                <i class="fas fa-user text-info me-2"></i>👤 Assign Human Driver
                            </a></li>
                            <li><hr class="dropdown-divider"></li>
>>>>>>> 6dd25ab (Initial commit from Replit)
                            <li><a class="dropdown-item" href="#" onclick="updateOrderStatus(${order.id}, 'out_for_delivery')">
                                <i class="fas fa-truck text-primary me-2"></i>Out for Delivery
                            </a></li>
                            <li><a class="dropdown-item" href="#" onclick="updateOrderStatus(${order.id}, 'delivered')">
                                <i class="fas fa-check-circle text-success me-2"></i>Delivered
                            </a></li>
                            <li><hr class="dropdown-divider"></li>
                            <li><a class="dropdown-item text-danger" href="#" onclick="updateOrderStatus(${order.id}, 'cancelled')">
                                <i class="fas fa-times text-danger me-2"></i>Cancel
                            </a></li>
                        </ul>
                    </div>
                </td>
            `;
            tbody.appendChild(row);
        });
        
    } catch (error) {
        console.error('Error loading orders:', error);
        const tbody = document.getElementById('ordersTable');
        if (tbody) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="8" class="text-center py-4 text-danger">
                        Error loading orders. Please refresh the page.
                    </td>
                </tr>
            `;
        }
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Initialize dashboard
    initializeDashboard();
    
    // Refresh button
    const refreshBtn = document.getElementById('refreshBtn');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', function() {
            loadDashboardData();
            loadOrdersTab();
        });
    }
    
    // Load orders when orders tab is shown
    const ordersTab = document.querySelector('[href="#orders"]');
    if (ordersTab) {
        ordersTab.addEventListener('shown.bs.tab', loadOrdersTab);
    }
    
    // Load orders immediately when page loads
    loadOrdersTab();
    
    // Auto-refresh every 5 minutes
    setInterval(function() {
        loadDashboardData();
        loadOrdersTab();
    }, 5 * 60 * 1000);
});