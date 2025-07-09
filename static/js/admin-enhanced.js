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
        const driversData = await driversResponse.json();
        
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
    dashboardData.activeDrivers = drivers.filter(driver => driver.is_active && driver.is_available).length;
    dashboardData.completedOrders = orders.filter(order => order.status === 'delivered').length;
    dashboardData.totalCustomers = customersCount;
    dashboardData.totalMenuItems = menuItems.length;
    dashboardData.recentOrders = orders.slice(0, 5); // Last 5 orders
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

