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
}

// Load Dashboard Data
async function loadDashboardData() {
    try {
        // Load orders data
        const ordersResponse = await fetch('/api/orders');
        const ordersData = await ordersResponse.json();
        
        // Load drivers data
        const driversResponse = await fetch('/api/drivers');
        const driversData = driversResponse.ok ? await driversResponse.json() : [];
        
        // Load menu data
        const menuResponse = await fetch('/api/menu');
        const menuData = await menuResponse.json();
        
        // Load customers data (count unique telegram user IDs from orders)
        const customersCount = [...new Set(ordersData.orders?.map(order => order.telegram_user_id) || [])].length;
        
        // Process data
        processDashboardData(ordersData.orders || [], driversData || [], menuData || [], customersCount);
        updateDashboardStats();
        updateCharts();
        updateRecentOrders();
        
    } catch (error) {
        console.error('Error loading dashboard data:', error);
    }
}

// Process Dashboard Data
function processDashboardData(orders, drivers, menuItems, customersCount) {
    dashboardData.totalOrders = orders.length;
    dashboardData.totalRevenue = orders.reduce((sum, order) => sum + order.total_amount, 0);
    dashboardData.pendingOrders = orders.filter(order => order.status === 'pending').length;
    dashboardData.activeDrivers = drivers.filter(driver => driver.is_active).length;
    dashboardData.completedOrders = orders.filter(order => order.status === 'delivered').length;
    dashboardData.totalCustomers = customersCount;
    dashboardData.totalMenuItems = menuItems.length;
    dashboardData.recentOrders = orders.slice(0, 5); // Last 5 orders
    
    // Driver statistics
    dashboardData.totalDrivers = drivers.length;
    dashboardData.onlineDrivers = drivers.filter(driver => driver.is_active).length;
    dashboardData.offlineDrivers = drivers.filter(driver => !driver.is_active).length;
    dashboardData.availableDrivers = drivers.filter(driver => driver.is_available).length;
    dashboardData.busyDrivers = drivers.filter(driver => !driver.is_available).length;
    dashboardData.pendingDrivers = drivers.filter(driver => driver.approval_status === 'pending').length;
}

// Update Dashboard Stats
function updateDashboardStats() {
    document.getElementById('totalOrders').textContent = dashboardData.totalOrders;
    document.getElementById('totalRevenue').textContent = `ETB ${dashboardData.totalRevenue.toFixed(2)}`;
    document.getElementById('pendingOrders').textContent = dashboardData.pendingOrders;
    document.getElementById('activeDrivers').textContent = dashboardData.activeDrivers;
    
    // Update new dashboard stats
    if (document.getElementById('totalCustomers')) {
        document.getElementById('totalCustomers').textContent = dashboardData.totalCustomers || 0;
    }
    if (document.getElementById('totalMenuItems')) {
        document.getElementById('totalMenuItems').textContent = dashboardData.totalMenuItems || 0;
    }
    if (document.getElementById('completedOrders')) {
        document.getElementById('completedOrders').textContent = dashboardData.completedOrders || 0;
    }
    
    // Update driver statistics
    if (document.getElementById('totalDrivers')) {
        document.getElementById('totalDrivers').textContent = dashboardData.totalDrivers || 0;
    }
    if (document.getElementById('onlineDrivers')) {
        document.getElementById('onlineDrivers').textContent = dashboardData.onlineDrivers || 0;
    }
    if (document.getElementById('offlineDrivers')) {
        document.getElementById('offlineDrivers').textContent = dashboardData.offlineDrivers || 0;
    }
    if (document.getElementById('availableDrivers')) {
        document.getElementById('availableDrivers').textContent = dashboardData.availableDrivers || 0;
    }
    if (document.getElementById('busyDrivers')) {
        document.getElementById('busyDrivers').textContent = dashboardData.busyDrivers || 0;
    }
    if (document.getElementById('pendingDrivers')) {
        document.getElementById('pendingDrivers').textContent = dashboardData.pendingDrivers || 0;
    }
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
                        ${(() => {
                            let items = [];
                            try {
                                items = typeof order.items === 'string' ? JSON.parse(order.items) : order.items;
                            } catch (e) {
                                console.error('Error parsing items for order', order.id, e);
                                items = [];
                            }
                            return items.map(item => `
                                <tr>
                                    <td>${item.name}</td>
                                    <td>${item.quantity}</td>
                                    <td>ETB ${item.price.toFixed(2)}</td>
                                    <td>ETB ${(item.price * item.quantity).toFixed(2)}</td>
                                </tr>
                            `).join('');
                        })()}
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

// Load Orders Tab
// Live Tracking Functions
function showLiveTrackingMap() {
    // Create modal for live tracking map
    const modalHtml = `
        <div class="modal fade" id="liveTrackingModal" tabindex="-1">
            <div class="modal-dialog modal-xl">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">Live Driver Tracking</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <div id="liveTrackingMap" style="height: 500px; border-radius: 8px;"></div>
                        <div class="mt-3">
                            <div class="row" id="driversList">
                                <!-- Driver info cards will be loaded here -->
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    // Add modal to body if not exists
    if (!document.getElementById('liveTrackingModal')) {
        document.body.insertAdjacentHTML('beforeend', modalHtml);
    }
    
    // Show modal and initialize map
    const modal = new bootstrap.Modal(document.getElementById('liveTrackingModal'));
    modal.show();
    
    // Initialize map after modal is shown
    setTimeout(() => {
        initializeLiveTrackingMap();
    }, 500);
}

function initializeLiveTrackingMap() {
    // Initialize Leaflet map
    const map = L.map('liveTrackingMap').setView([9.145, 40.489658], 12);
    
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors'
    }).addTo(map);
    
    // Load and display driver locations
    fetch('/api/drivers')
        .then(response => response.json())
        .then(drivers => {
            const driversList = document.getElementById('driversList');
            driversList.innerHTML = '';
            
            drivers.forEach(driver => {
                if (driver.current_location && driver.current_location.lat) {
                    // Add marker to map
                    const marker = L.marker([driver.current_location.lat, driver.current_location.lng])
                        .addTo(map)
                        .bindPopup(`
                            <strong>${driver.name}</strong><br>
                            Vehicle: ${driver.vehicle_type}<br>
                            Status: ${driver.is_available ? 'Available' : 'Busy'}<br>
                            Last Update: ${new Date(driver.current_location.last_update).toLocaleTimeString()}
                        `);
                    
                    // Add driver info card
                    const driverCard = document.createElement('div');
                    driverCard.className = 'col-md-4 mb-3';
                    driverCard.innerHTML = `
                        <div class="card h-100">
                            <div class="card-body">
                                <h6 class="card-title">${driver.name}</h6>
                                <p class="card-text">
                                    <small class="text-muted">
                                        Vehicle: ${driver.vehicle_type}<br>
                                        Status: ${driver.is_available ? 'Available' : 'Busy'}<br>
                                        Last Update: ${new Date(driver.current_location.last_update).toLocaleTimeString()}
                                    </small>
                                </p>
                                <button class="btn btn-sm btn-primary" onclick="focusOnDriver(${driver.current_location.lat}, ${driver.current_location.lng})">
                                    <i class="fas fa-crosshairs"></i> Focus
                                </button>
                                <button class="btn btn-sm btn-secondary" onclick="requestDriverLocation(${driver.id})">
                                    <i class="fas fa-sync"></i> Update
                                </button>
                            </div>
                        </div>
                    `;
                    driversList.appendChild(driverCard);
                }
            });
            
            if (drivers.filter(d => d.current_location).length === 0) {
                driversList.innerHTML = '<div class="col-12"><div class="alert alert-info">No drivers are currently sharing their location.</div></div>';
            }
        })
        .catch(error => console.error('Error loading driver locations:', error));
}

function assignDeliveryBot() {
    // Find pending orders to assign to delivery bot
    fetch('/api/orders')
        .then(response => response.json())
        .then(data => {
            const pendingOrders = data.orders.filter(order => order.status === 'pending' || order.status === 'confirmed');
            
            if (pendingOrders.length === 0) {
                alert('No pending orders to assign to delivery bot.');
                return;
            }
            
            // Show order selection modal
            showDeliveryBotAssignmentModal(pendingOrders);
        })
        .catch(error => console.error('Error loading orders:', error));
}

function showDeliveryBotAssignmentModal(orders) {
    const modalHtml = `
        <div class="modal fade" id="deliveryBotModal" tabindex="-1">
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">Assign Delivery Bot</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <p>Select orders to assign to the automated delivery bot:</p>
                        <div id="ordersList">
                            ${orders.map(order => `
                                <div class="form-check mb-2">
                                    <input class="form-check-input" type="checkbox" value="${order.id}" id="order${order.id}">
                                    <label class="form-check-label" for="order${order.id}">
                                        Order #${order.id} - ${order.customer_name} - ETB ${order.total_amount.toFixed(2)}
                                    </label>
                                </div>
                            `).join('')}
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                        <button type="button" class="btn btn-primary" onclick="assignSelectedOrdersToBot()">Assign to Bot</button>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    document.body.insertAdjacentHTML('beforeend', modalHtml);
    const modal = new bootstrap.Modal(document.getElementById('deliveryBotModal'));
    modal.show();
}

function assignSelectedOrdersToBot() {
    const selectedOrders = Array.from(document.querySelectorAll('#ordersList input:checked')).map(cb => cb.value);
    
    if (selectedOrders.length === 0) {
        alert('Please select at least one order.');
        return;
    }
    
    // Create or get delivery bot driver
    fetch('/api/drivers', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            name: 'Delivery Bot',
            phone_number: '+251000000000',
            vehicle_type: 'autonomous',
            telegram_user_id: null
        })
    })
    .then(response => response.json())
    .then(data => {
        const botDriverId = data.driver_id || 1; // Fallback to existing bot driver
        
        // Assign each selected order to the bot
        selectedOrders.forEach(orderId => {
            fetch(`/api/drivers/${botDriverId}/assign/${orderId}`, { method: 'POST' })
                .then(() => console.log(`Order ${orderId} assigned to delivery bot`))
                .catch(error => console.error(`Error assigning order ${orderId}:`, error));
        });
        
        // Close modal and refresh dashboard
        bootstrap.Modal.getInstance(document.getElementById('deliveryBotModal')).hide();
        setTimeout(() => {
            loadDashboardData();
            loadOrdersTab();
        }, 1000);
        
        alert(`${selectedOrders.length} order(s) assigned to delivery bot!`);
    })
    .catch(error => console.error('Error creating delivery bot:', error));
}

function trackAllDeliveries() {
    // Show tracking modal for all active deliveries
    fetch('/api/orders')
        .then(response => response.json())
        .then(data => {
            const activeDeliveries = data.orders.filter(order => order.status === 'out_for_delivery');
            
            if (activeDeliveries.length === 0) {
                alert('No active deliveries to track.');
                return;
            }
            
            showAllDeliveriesModal(activeDeliveries);
        })
        .catch(error => console.error('Error loading deliveries:', error));
}

function showAllDeliveriesModal(deliveries) {
    const modalHtml = `
        <div class="modal fade" id="allDeliveriesModal" tabindex="-1">
            <div class="modal-dialog modal-lg">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">Active Deliveries Tracking</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <div class="row">
                            ${deliveries.map(order => `
                                <div class="col-md-6 mb-3">
                                    <div class="card">
                                        <div class="card-body">
                                            <h6 class="card-title">Order #${order.id}</h6>
                                            <p class="card-text">
                                                Customer: ${order.customer_name}<br>
                                                Driver: ${order.driver_name || 'Delivery Bot'}<br>
                                                Total: ETB ${order.total_amount.toFixed(2)}
                                            </p>
                                            <button class="btn btn-sm btn-primary" onclick="viewOrderDetails(${order.id})">
                                                <i class="fas fa-eye"></i> View Details
                                            </button>
                                            <button class="btn btn-sm btn-success" onclick="updateOrderStatus(${order.id}, 'delivered')">
                                                <i class="fas fa-check"></i> Mark Delivered
                                            </button>
                                        </div>
                                    </div>
                                </div>
                            `).join('')}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    document.body.insertAdjacentHTML('beforeend', modalHtml);
    const modal = new bootstrap.Modal(document.getElementById('allDeliveriesModal'));
    modal.show();
}

function requestDriverLocation(driverId) {
    fetch(`/api/drivers/${driverId}/request-location`, { method: 'POST' })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert('Location request sent to driver!');
            } else {
                alert('Failed to send location request.');
            }
        })
        .catch(error => console.error('Error requesting location:', error));
}

function focusOnDriver(lat, lng) {
    // Get the map instance and focus on driver location
    const mapContainer = document.getElementById('liveTrackingMap');
    if (mapContainer && mapContainer._leaflet_map) {
        const map = mapContainer._leaflet_map;
        map.setView([lat, lng], 15);
    }
}

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
            
            // Parse items from JSON string if needed
            let items = [];
            try {
                items = typeof order.items === 'string' ? JSON.parse(order.items) : order.items;
            } catch (e) {
                console.error('Error parsing items for order', order.id, e);
                items = [];
            }
            
            const itemsList = items.map(item => `${item.name} (x${item.quantity})`).join(', ');
            
            // Check if order has location data
            const hasLocation = order.location_lat && order.location_lng;
            const locationButton = hasLocation ? 
                `<button class="btn btn-sm btn-outline-success me-1" onclick="showCustomerLocation(${order.location_lat}, ${order.location_lng}, '${order.customer_name}')" title="View Customer Location">
                    <i class="fas fa-map-marker-alt"></i>
                </button>` : '';
            
            // Driver tracking button for out_for_delivery orders
            const driverTrackingButton = order.status === 'out_for_delivery' && order.driver_id ? 
                `<button class="btn btn-sm btn-primary me-1" onclick="showDriverTracking(${order.id})" title="Track Driver">
                    <i class="fas fa-truck"></i> Track Driver
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
                        ${driverTrackingButton}
                        <button class="btn btn-sm btn-outline-primary" onclick="viewOrderDetails(${order.id})" title="View Details">
                            <i class="fas fa-eye"></i>
                        </button>
                        <button class="btn btn-sm btn-outline-warning" onclick="manuallyAssignDriver(${order.id})" title="Manually Assign Driver">
                            <i class="fas fa-user-plus"></i>
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

// Manual Driver Assignment Functions
async function manuallyAssignDriver(orderId) {
    try {
        // Get available drivers for this order
        const driversResponse = await fetch(`/api/orders/${orderId}/available-drivers`);
        const driversData = await driversResponse.json();
        
        if (!driversData.success || driversData.drivers.length === 0) {
            alert('No available drivers found for this order.');
            return;
        }
        
        // Show driver selection modal
        showDriverSelectionModal(orderId, driversData.drivers);
        
    } catch (error) {
        console.error('Error loading available drivers:', error);
        alert('Failed to load available drivers. Please try again.');
    }
}

function showDriverSelectionModal(orderId, drivers) {
    const modalHtml = `
        <div class="modal fade" id="driverSelectionModal" tabindex="-1">
            <div class="modal-dialog modal-lg">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">
                            <i class="fas fa-user-plus text-warning me-2"></i>
                            Manually Assign Driver - Order #${orderId}
                        </h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <p class="text-muted mb-4">Select a driver to assign to this order:</p>
                        <div class="row">
                            ${drivers.map(driver => `
                                <div class="col-md-6 mb-3">
                                    <div class="card driver-card h-100" style="cursor: pointer;" onclick="selectDriver(${driver.id}, '${driver.name}')">
                                        <div class="card-body">
                                            <div class="d-flex justify-content-between align-items-start">
                                                <div>
                                                    <h6 class="card-title mb-1">${driver.name}</h6>
                                                    <p class="card-text text-muted small mb-1">
                                                        <i class="fas fa-phone me-1"></i>${driver.phone_number}
                                                    </p>
                                                    <p class="card-text text-muted small mb-1">
                                                        <i class="fas fa-motorcycle me-1"></i>${driver.vehicle_type}
                                                    </p>
                                                    ${driver.distance ? `
                                                        <p class="card-text text-muted small mb-1">
                                                            <i class="fas fa-map-marker-alt me-1"></i>${driver.distance.toFixed(1)} km away
                                                        </p>
                                                    ` : ''}
                                                </div>
                                                <div class="text-end">
                                                    <span class="badge ${driver.is_available ? 'bg-success' : 'bg-warning'}">
                                                        ${driver.is_available ? 'Available' : 'Busy'}
                                                    </span>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            `).join('')}
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                        <button type="button" class="btn btn-primary" onclick="findNearbyDrivers(${orderId})">
                            <i class="fas fa-search me-2"></i>Find Nearby Drivers
                        </button>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    // Remove existing modal if any
    const existingModal = document.getElementById('driverSelectionModal');
    if (existingModal) {
        existingModal.remove();
    }
    
    // Add modal to page
    document.body.insertAdjacentHTML('beforeend', modalHtml);
    
    // Add click effects for driver cards
    document.querySelectorAll('.driver-card').forEach(card => {
        card.addEventListener('mouseover', function() {
            this.style.transform = 'scale(1.02)';
            this.style.transition = 'transform 0.2s';
        });
        card.addEventListener('mouseout', function() {
            this.style.transform = 'scale(1)';
        });
    });
    
    // Show modal
    const modal = new bootstrap.Modal(document.getElementById('driverSelectionModal'));
    modal.show();
    
    // Clean up when modal is hidden
    document.getElementById('driverSelectionModal').addEventListener('hidden.bs.modal', function () {
        this.remove();
    });
}

async function selectDriver(driverId, driverName) {
    const orderId = getCurrentOrderId();
    
    if (!orderId) {
        alert('Error: Order ID not found');
        return;
    }
    
    const confirmation = confirm(`Assign driver "${driverName}" to order #${orderId}?`);
    if (!confirmation) return;
    
    try {
        const response = await fetch(`/api/orders/${orderId}/manual-assign-driver`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ 
                driver_id: driverId,
                admin_telegram_id: null // Optional: could be set if admin has telegram ID
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            alert(`Driver "${driverName}" successfully assigned to order #${orderId}`);
            
            // Close modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('driverSelectionModal'));
            if (modal) modal.hide();
            
            // Refresh data
            loadDashboardData();
            loadOrdersTab();
        } else {
            alert(`Failed to assign driver: ${result.message || 'Unknown error'}`);
        }
        
    } catch (error) {
        console.error('Error assigning driver:', error);
        alert('Failed to assign driver. Please try again.');
    }
}

async function findNearbyDrivers(orderId) {
    try {
        const response = await fetch(`/api/orders/${orderId}/find-nearby-drivers`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        });
        
        const result = await response.json();
        
        if (result.success) {
            alert(`Nearby drivers notified for order #${orderId}`);
            
            // Close modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('driverSelectionModal'));
            if (modal) modal.hide();
            
            // Refresh data
            loadDashboardData();
            loadOrdersTab();
        } else {
            alert(`Failed to notify drivers: ${result.message || 'No nearby drivers found'}`);
        }
        
    } catch (error) {
        console.error('Error finding nearby drivers:', error);
        alert('Failed to find nearby drivers. Please try again.');
    }
}

function getCurrentOrderId() {
    const modal = document.getElementById('driverSelectionModal');
    if (!modal) return null;
    
    const title = modal.querySelector('.modal-title');
    if (!title) return null;
    
    const match = title.textContent.match(/Order #(\d+)/);
    return match ? parseInt(match[1]) : null;
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
    
    // Load drivers when drivers tab is shown
    const driversTab = document.querySelector('[href="#drivers"]');
    if (driversTab) {
        driversTab.addEventListener('shown.bs.tab', loadDriversTab);
    }
    
    // Load orders immediately when page loads
    loadOrdersTab();
    
    // Auto-refresh every 5 minutes
    setInterval(function() {
        loadDashboardData();
        loadOrdersTab();
    }, 5 * 60 * 1000);
});


// New Dashboard Functions
function loadCustomerData() {
    alert(`Total customers: ${dashboardData.totalCustomers}\n\nCustomer data loaded successfully!`);
}

function showMenuTab() {
    // Switch to menu tab
    const menuTab = document.querySelector("a[href=\"#menu\"]");
    if (menuTab) {
        menuTab.click();
    }
}

function showCompletedOrders() {
    // Switch to orders tab
    const ordersTab = document.querySelector("a[href=\"#orders\"]");
    if (ordersTab) {
        ordersTab.click();
        // Filter completed orders after a short delay
        setTimeout(() => {
            loadOrders("delivered");
        }, 100);
    }
}

// Load Drivers Tab
async function loadDriversTab() {
    try {
        const response = await fetch('/api/drivers');
        const drivers = await response.json();
        populateDriversTable(drivers);
    } catch (error) {
        console.error('Error loading drivers:', error);
    }
}

// Populate Drivers Table
function populateDriversTable(drivers) {
    const tbody = document.getElementById('driversTable');
    tbody.innerHTML = '';
    
    drivers.forEach(driver => {
        const row = document.createElement('tr');
        const statusClass = driver.is_active ? 'success' : 'danger';
        const statusText = driver.is_active ? 'Active' : 'Inactive';
        const availabilityClass = driver.is_available ? 'primary' : 'warning';
        const availabilityText = driver.is_available ? 'Available' : 'Busy';
        
        row.innerHTML = `
            <td>${driver.id}</td>
            <td>${driver.name}</td>
            <td>${driver.phone_number}</td>
            <td>${driver.vehicle_type}</td>
            <td>
                <span class="badge bg-${statusClass}">${statusText}</span>
                <span class="badge bg-${availabilityClass}">${availabilityText}</span>
            </td>
            <td>
                ${driver.current_lat && driver.current_lng ? 
                    `<a href="https://www.google.com/maps?q=${driver.current_lat},${driver.current_lng}" target="_blank" class="btn btn-sm btn-info">
                        <i class="fas fa-map-marker-alt"></i> View Location
                    </a>` : 
                    '<span class="text-muted">No location</span>'
                }
            </td>
            <td>
                <div class="btn-group" role="group">
                    <button class="btn btn-sm btn-${driver.is_active ? 'danger' : 'success'}" 
                            onclick="toggleDriverStatus(${driver.id}, ${!driver.is_active})">
                        <i class="fas fa-${driver.is_active ? 'pause' : 'play'}"></i>
                        ${driver.is_active ? 'Deactivate' : 'Activate'}
                    </button>
                    <button class="btn btn-sm btn-warning" onclick="requestDriverLocation(${driver.id})">
                        <i class="fas fa-location-arrow"></i> Request Location
                    </button>
                    <button class="btn btn-sm btn-danger" onclick="removeDriver(${driver.id})">
                        <i class="fas fa-trash"></i> Remove
                    </button>
                </div>
            </td>
        `;
        tbody.appendChild(row);
    });
}

// Show Add Driver Modal
function showAddDriverModal() {
    const modalHTML = `
        <div class="modal fade" id="addDriverModal" tabindex="-1">
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">Add Driver Employee</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <form id="addDriverForm">
                            <div class="mb-3">
                                <label for="driverName" class="form-label">Driver Name</label>
                                <input type="text" class="form-control" id="driverName" required>
                            </div>
                            <div class="mb-3">
                                <label for="driverPhone" class="form-label">Phone Number</label>
                                <input type="tel" class="form-control" id="driverPhone" required>
                            </div>
                            <div class="mb-3">
                                <label for="driverTelegramId" class="form-label">Telegram ID</label>
                                <input type="text" class="form-control" id="driverTelegramId">
                            </div>
                            <div class="mb-3">
                                <label for="driverVehicle" class="form-label">Vehicle Type</label>
                                <select class="form-control" id="driverVehicle" required>
                                    <option value="motorcycle">Motorcycle</option>
                                    <option value="car">Car</option>
                                    <option value="bicycle">Bicycle</option>
                                    <option value="scooter">Scooter</option>
                                </select>
                            </div>
                            <div class="mb-3">
                                <div class="form-check">
                                    <input class="form-check-input" type="checkbox" id="autoApprove" checked>
                                    <label class="form-check-label" for="autoApprove">
                                        Auto-approve driver (skip manual approval)
                                    </label>
                                </div>
                            </div>
                        </form>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                        <button type="button" class="btn btn-primary" onclick="addDriver()">Add Driver</button>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    const existingModal = document.getElementById('addDriverModal');
    if (existingModal) {
        existingModal.remove();
    }
    
    document.body.insertAdjacentHTML('beforeend', modalHTML);
    const modal = new bootstrap.Modal(document.getElementById('addDriverModal'));
    modal.show();
}

// Add Driver
async function addDriver() {
    const name = document.getElementById('driverName').value;
    const phone = document.getElementById('driverPhone').value;
    const telegramId = document.getElementById('driverTelegramId').value;
    const vehicle = document.getElementById('driverVehicle').value;
    const autoApprove = document.getElementById('autoApprove').checked;
    
    if (!name || !phone || !vehicle) {
        alert('Please fill in all required fields');
        return;
    }
    
    try {
        const response = await fetch('/api/drivers', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                name: name,
                phone_number: phone,
                telegram_user_id: telegramId,
                vehicle_type: vehicle,
                auto_approve: autoApprove
            })
        });
        
        const result = await response.json();
        
        if (response.ok) {
            alert('Driver added successfully!');
            const modal = bootstrap.Modal.getInstance(document.getElementById('addDriverModal'));
            modal.hide();
            loadDriversTab();
            loadDashboardData();
        } else {
            alert('Error: ' + result.error);
        }
    } catch (error) {
        console.error('Error adding driver:', error);
        alert('Error adding driver. Please try again.');
    }
}

// Toggle Driver Status
async function toggleDriverStatus(driverId, newStatus) {
    try {
        const response = await fetch(`/api/drivers/${driverId}/toggle`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ is_active: newStatus })
        });
        
        if (response.ok) {
            loadDriversTab();
            loadDashboardData();
        } else {
            alert('Error toggling driver status');
        }
    } catch (error) {
        console.error('Error:', error);
        alert('Error toggling driver status');
    }
}

// Request Driver Location
async function requestDriverLocation(driverId) {
    try {
        const response = await fetch(`/api/drivers/${driverId}/request-location`, {
            method: 'POST'
        });
        
        if (response.ok) {
            alert('Location request sent to driver');
        } else {
            alert('Error requesting location');
        }
    } catch (error) {
        console.error('Error:', error);
        alert('Error requesting location');
    }
}

// Remove Driver
async function removeDriver(driverId) {
    if (!confirm('Are you sure you want to remove this driver?')) {
        return;
    }
    
    try {
        const response = await fetch(`/api/drivers/${driverId}`, {
            method: 'DELETE'
        });
        
        if (response.ok) {
            alert('Driver removed successfully');
            loadDriversTab();
            loadDashboardData();
        } else {
            const error = await response.json();
            alert('Error: ' + error.error);
        }
    } catch (error) {
        console.error('Error:', error);
        alert('Error removing driver');
    }
}

// Refresh Driver Data
function refreshDriverData() {
    loadDriversTab();
    loadDashboardData();
}

// Driver Tracking Functions
async function showDriverTracking(orderId) {
    try {
        // Get order details with driver information
        const orderResponse = await fetch(`/api/orders/${orderId}`);
        const orderData = await orderResponse.json();
        
        if (!orderData.success || !orderData.order.driver_id) {
            alert('Driver information not found for this order.');
            return;
        }
        
        const order = orderData.order;
        
        // Get driver details
        const driverResponse = await fetch(`/api/drivers/${order.driver_id}`);
        const driverData = await driverResponse.json();
        
        if (!driverData.success) {
            alert('Failed to load driver information.');
            return;
        }
        
        const driver = driverData.driver;
        
        // Create driver tracking modal
        const modalHtml = `
            <div class="modal fade" id="driverTrackingModal" tabindex="-1" aria-labelledby="driverTrackingModalLabel" aria-hidden="true">
                <div class="modal-dialog modal-xl">
                    <div class="modal-content">
                        <div class="modal-header bg-primary text-white">
                            <h5 class="modal-title" id="driverTrackingModalLabel">
                                <i class="fas fa-truck"></i> Driver Tracking - Order #${order.id}
                            </h5>
                            <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal" aria-label="Close"></button>
                        </div>
                        <div class="modal-body">
                            <div class="row">
                                <!-- Driver Information Panel -->
                                <div class="col-md-4">
                                    <div class="card h-100">
                                        <div class="card-header bg-light">
                                            <h6 class="mb-0"><i class="fas fa-user"></i> Driver Information</h6>
                                        </div>
                                        <div class="card-body">
                                            <div class="driver-avatar text-center mb-3">
                                                <div class="avatar-circle bg-primary text-white d-inline-flex align-items-center justify-content-center" style="width: 60px; height: 60px; border-radius: 50%; font-size: 24px; font-weight: bold;">
                                                    ${driver.name.charAt(0).toUpperCase()}
                                                </div>
                                                <h6 class="mt-2 mb-0">${driver.name}</h6>
                                                <small class="text-muted">${driver.vehicle_type || 'Vehicle'}</small>
                                            </div>
                                            
                                            <div class="driver-details">
                                                <div class="mb-2">
                                                    <strong><i class="fas fa-phone text-success"></i> Phone:</strong><br>
                                                    <a href="tel:${driver.phone_number}" class="btn btn-sm btn-success w-100 mt-1">
                                                        <i class="fas fa-phone"></i> Call ${driver.phone_number}
                                                    </a>
                                                </div>
                                                
                                                <div class="mb-2">
                                                    <strong><i class="fas fa-circle text-${driver.is_available ? 'success' : 'warning'}"></i> Status:</strong><br>
                                                    <span class="badge bg-${driver.is_available ? 'success' : 'warning'}">
                                                        ${driver.is_available ? 'Available' : 'Busy'}
                                                    </span>
                                                </div>
                                                
                                                <div class="mb-2">
                                                    <strong><i class="fas fa-clock"></i> Last Update:</strong><br>
                                                    <small class="text-muted">${driver.last_location_update ? new Date(driver.last_location_update).toLocaleString() : 'Never'}</small>
                                                </div>
                                                
                                                ${driver.current_lat && driver.current_lng ? `
                                                <div class="mb-2">
                                                    <strong><i class="fas fa-map-marker-alt text-primary"></i> Location:</strong><br>
                                                    <button class="btn btn-sm btn-primary w-100 mt-1" onclick="openDriverLocation(${driver.current_lat}, ${driver.current_lng}, '${driver.name}')">
                                                        <i class="fas fa-external-link-alt"></i> View on Maps
                                                    </button>
                                                </div>
                                                ` : '<div class="alert alert-warning"><small>No GPS location available</small></div>'}
                                            </div>
                                        </div>
                                    </div>
                                </div>
                                
                                <!-- Order & Customer Information Panel -->
                                <div class="col-md-4">
                                    <div class="card h-100">
                                        <div class="card-header bg-light">
                                            <h6 class="mb-0"><i class="fas fa-shopping-bag"></i> Order & Customer Info</h6>
                                        </div>
                                        <div class="card-body">
                                            <div class="order-info">
                                                <div class="mb-3">
                                                    <strong><i class="fas fa-user text-info"></i> Customer:</strong><br>
                                                    ${order.customer_name}<br>
                                                    <a href="tel:${order.customer_phone}" class="btn btn-sm btn-info w-100 mt-1">
                                                        <i class="fas fa-phone"></i> Call Customer
                                                    </a>
                                                </div>
                                                
                                                <div class="mb-3">
                                                    <strong><i class="fas fa-map-marker-alt text-danger"></i> Delivery Address:</strong><br>
                                                    <small>${order.customer_address || 'Address not provided'}</small>
                                                    ${order.location_lat && order.location_lng ? `
                                                    <button class="btn btn-sm btn-danger w-100 mt-1" onclick="openCustomerLocation(${order.location_lat}, ${order.location_lng}, '${order.customer_name}')">
                                                        <i class="fas fa-navigation"></i> Navigate to Customer
                                                    </button>
                                                    ` : ''}
                                                </div>
                                                
                                                <div class="mb-3">
                                                    <strong><i class="fas fa-money-bill text-success"></i> Payment:</strong><br>
                                                    <span class="badge bg-success">${order.payment_method}</span><br>
                                                    <strong>ETB ${order.total_amount.toFixed(2)}</strong>
                                                </div>
                                                
                                                <div class="mb-2">
                                                    <strong><i class="fas fa-clock"></i> Order Time:</strong><br>
                                                    <small>${new Date(order.created_at).toLocaleString()}</small>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                                
                                <!-- Live Tracking & Controls Panel -->
                                <div class="col-md-4">
                                    <div class="card h-100">
                                        <div class="card-header bg-light">
                                            <h6 class="mb-0"><i class="fas fa-satellite-dish"></i> Live Tracking & Controls</h6>
                                        </div>
                                        <div class="card-body">
                                            <div class="tracking-controls">
                                                <div class="mb-3">
                                                    <button class="btn btn-warning w-100 mb-2" onclick="requestDriverLocation(${driver.id})">
                                                        <i class="fas fa-location-arrow"></i> Request Location Update
                                                    </button>
                                                    
                                                    <button class="btn btn-info w-100 mb-2" onclick="openLiveTrackingMap(${order.id})">
                                                        <i class="fas fa-map"></i> Open Live Tracking Map
                                                    </button>
                                                    
                                                    <button class="btn btn-primary w-100 mb-2" onclick="sendMessageToDriver(${driver.telegram_user_id})">
                                                        <i class="fas fa-comment"></i> Send Message to Driver
                                                    </button>
                                                </div>
                                                
                                                <div class="tracking-status">
                                                    <div class="alert alert-info">
                                                        <h6><i class="fas fa-route"></i> Delivery Status</h6>
                                                        <div class="status-timeline">
                                                            <div class="status-step completed">
                                                                <i class="fas fa-check-circle"></i> Order Accepted
                                                            </div>
                                                            <div class="status-step ${order.status === 'out_for_delivery' ? 'active' : ''}">
                                                                <i class="fas fa-truck"></i> Out for Delivery
                                                            </div>
                                                            <div class="status-step ${order.status === 'delivered' ? 'completed' : ''}">
                                                                <i class="fas fa-flag-checkered"></i> Delivered
                                                            </div>
                                                        </div>
                                                    </div>
                                                </div>
                                                
                                                <div class="quick-actions">
                                                    <h6><i class="fas fa-bolt"></i> Quick Actions</h6>
                                                    <button class="btn btn-sm btn-outline-warning w-100 mb-1" onclick="markOrderAsDelivered(${order.id})">
                                                        <i class="fas fa-check"></i> Mark as Delivered
                                                    </button>
                                                    <button class="btn btn-sm btn-outline-danger w-100" onclick="reportDeliveryIssue(${order.id})">
                                                        <i class="fas fa-exclamation-triangle"></i> Report Issue
                                                    </button>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                            <button type="button" class="btn btn-primary" onclick="refreshDriverTracking(${order.id})">
                                <i class="fas fa-sync"></i> Refresh Data
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        // Remove existing modal if present
        const existingModal = document.getElementById('driverTrackingModal');
        if (existingModal) {
            existingModal.remove();
        }
        
        // Add modal to body
        document.body.insertAdjacentHTML('beforeend', modalHtml);
        
        // Add custom CSS for status timeline
        const style = document.createElement('style');
        style.textContent = `
            .status-timeline {
                list-style: none;
                padding: 0;
                margin: 0;
            }
            .status-step {
                display: flex;
                align-items: center;
                padding: 8px 0;
                font-size: 14px;
                color: #6c757d;
            }
            .status-step i {
                margin-right: 8px;
                width: 16px;
            }
            .status-step.completed {
                color: #28a745;
                font-weight: 500;
            }
            .status-step.active {
                color: #007bff;
                font-weight: 600;
                background-color: #f8f9fa;
                border-radius: 4px;
                padding: 10px;
            }
            .avatar-circle {
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
        `;
        document.head.appendChild(style);
        
        // Show modal
        const modal = new bootstrap.Modal(document.getElementById('driverTrackingModal'));
        modal.show();
        
    } catch (error) {
        console.error('Error showing driver tracking:', error);
        alert('Failed to load driver tracking information.');
    }
}

// Helper functions for driver tracking
function openDriverLocation(lat, lng, driverName) {
    const url = `https://www.google.com/maps?q=${lat},${lng}&z=15&t=m`;
    window.open(url, '_blank');
}

function openCustomerLocation(lat, lng, customerName) {
    const url = `https://www.google.com/maps/dir/9.047658,38.741143/${lat},${lng}`;
    window.open(url, '_blank');
}

function openLiveTrackingMap(orderId) {
    const url = `/live-tracking?order_id=${orderId}`;
    window.open(url, '_blank', 'width=1200,height=800');
}

async function sendMessageToDriver(telegramUserId) {
    const message = prompt('Enter message to send to driver:');
    if (!message) return;
    
    try {
        const response = await fetch('/api/send-driver-message', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                telegram_user_id: telegramUserId,
                message: message
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            alert('Message sent to driver successfully.');
        } else {
            alert('Failed to send message to driver.');
        }
    } catch (error) {
        console.error('Error sending message to driver:', error);
        alert('Failed to send message to driver.');
    }
}

async function markOrderAsDelivered(orderId) {
    if (!confirm('Are you sure you want to mark this order as delivered?')) return;
    
    try {
        const response = await fetch(`/api/orders/${orderId}/status`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                status: 'delivered'
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            alert('Order marked as delivered successfully.');
            // Close modal and refresh orders
            const modal = bootstrap.Modal.getInstance(document.getElementById('driverTrackingModal'));
            modal.hide();
            loadOrdersTab();
        } else {
            alert('Failed to mark order as delivered.');
        }
    } catch (error) {
        console.error('Error marking order as delivered:', error);
        alert('Failed to mark order as delivered.');
    }
}

function reportDeliveryIssue(orderId) {
    const issue = prompt('Describe the delivery issue:');
    if (!issue) return;
    
    // You can implement issue reporting logic here
    alert('Delivery issue reported. Admin will be notified.');
}

function refreshDriverTracking(orderId) {
    // Close current modal
    const modal = bootstrap.Modal.getInstance(document.getElementById('driverTrackingModal'));
    modal.hide();
    
    // Reopen with fresh data
    setTimeout(() => showDriverTracking(orderId), 500);
}

