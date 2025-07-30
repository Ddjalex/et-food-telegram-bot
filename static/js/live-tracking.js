/**
 * Live Driver Tracking System
 * Real-time GPS tracking for admin dashboard
 */

let driversMap = null;
let driverMarkers = {};
let autoRefreshInterval = null;
let mapInitialized = false;

// Initialize live tracking when drivers tab is loaded
function initializeLiveTracking() {
    if (!mapInitialized) {
        initializeDriversMap();
        mapInitialized = true;
    }
    
    loadDrivers();
    startDriversAutoRefresh();
}

// Initialize the map
function initializeDriversMap() {
    try {
        // Default center: Addis Ababa
        const defaultLat = 9.0579;
        const defaultLng = 38.7914;
        
        driversMap = L.map('driversMap').setView([defaultLat, defaultLng], 12);
        
        // Add tile layer
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '© OpenStreetMap contributors'
        }).addTo(driversMap);
        
        // Add restaurant marker
        const restaurantIcon = L.divIcon({
            className: 'restaurant-marker',
            html: '<i class="fas fa-utensils" style="color: #ff6b6b; font-size: 20px;"></i>',
            iconSize: [30, 30],
            iconAnchor: [15, 15]
        });
        
        L.marker([defaultLat, defaultLng], { icon: restaurantIcon })
            .addTo(driversMap)
            .bindPopup('<b>ET-FOOD Restaurant</b><br>Main Location')
            .openPopup();
            
    } catch (error) {
        console.error('Error initializing map:', error);
    }
}

// Load and display drivers on map
function loadDrivers() {
    fetch('/api/drivers')
        .then(response => response.json())
        .then(drivers => {
            updateDriversTable(drivers);
            updateDriversMap(drivers);
            updateDriversStats(drivers);
        })
        .catch(error => {
            console.error('Error loading drivers:', error);
            showError('Failed to load drivers data');
        });
}

// Update drivers table
function updateDriversTable(drivers) {
    const tbody = document.getElementById('driversTableBody');
    if (!tbody) return;
    
    tbody.innerHTML = '';
    
    drivers.forEach(driver => {
        const row = document.createElement('tr');
        
        // Determine location status
        let locationStatus = 'No Location';
        let locationColor = 'text-danger';
        let lastUpdate = 'Never';
        
        if (driver.current_lat && driver.current_lng) {
            if (driver.last_location_update) {
                const updateTime = new Date(driver.last_location_update);
                const now = new Date();
                const diffMinutes = (now - updateTime) / (1000 * 60);
                
                if (diffMinutes < 10) {
                    locationStatus = 'Live Location';
                    locationColor = 'text-success';
                } else if (diffMinutes < 60) {
                    locationStatus = 'Recent Location';
                    locationColor = 'text-warning';
                } else {
                    locationStatus = 'Outdated Location';
                    locationColor = 'text-danger';
                }
                
                lastUpdate = formatTimeAgo(updateTime);
            }
        }
        
        row.innerHTML = `
            <td>
                <strong>${driver.name}</strong>
                <br><small class="text-muted">${driver.vehicle_type}</small>
            </td>
            <td>${driver.phone_number}</td>
            <td>${driver.vehicle_type}</td>
            <td>
                <span class="badge ${driver.is_active ? 'bg-success' : 'bg-secondary'}">
                    ${driver.is_active ? 'Active' : 'Inactive'}
                </span>
                <br>
                <span class="badge ${driver.is_available ? 'bg-primary' : 'bg-warning'}">
                    ${driver.is_available ? 'Available' : 'Busy'}
                </span>
            </td>
            <td>
                <span class="${locationColor}">
                    <i class="fas fa-circle"></i> ${locationStatus}
                </span>
                ${driver.current_lat && driver.current_lng ? 
                    `<br><small class="text-muted">${driver.current_lat.toFixed(6)}, ${driver.current_lng.toFixed(6)}</small>` : 
                    ''
                }
            </td>
            <td>
                <small>${lastUpdate}</small>
            </td>
            <td>
                <div class="btn-group-vertical" role="group">
                    <button class="btn btn-sm btn-outline-primary" onclick="requestDriverLocation(${driver.id})" title="Request Location">
                        <i class="fas fa-location-arrow"></i>
                    </button>
                    <button class="btn btn-sm btn-outline-info" onclick="requestDriverLiveLocation(${driver.id})" title="Request Live Location">
                        <i class="fas fa-broadcast-tower"></i>
                    </button>
                    ${driver.current_lat && driver.current_lng ? 
                        `<button class="btn btn-sm btn-outline-success" onclick="viewDriverOnMap(${driver.id})" title="View on Map">
                            <i class="fas fa-map-marker-alt"></i>
                        </button>` : 
                        ''
                    }
                    <button class="btn btn-sm btn-outline-secondary" onclick="toggleDriverAvailability(${driver.id})" title="Toggle Availability">
                        <i class="fas fa-power-off"></i>
                    </button>
                </div>
            </td>
        `;
        
        tbody.appendChild(row);
    });
}

// Update drivers on map
function updateDriversMap(drivers) {
    if (!driversMap) return;
    
    // Clear existing driver markers
    Object.values(driverMarkers).forEach(marker => {
        driversMap.removeLayer(marker);
    });
    driverMarkers = {};
    
    // Add new driver markers
    drivers.forEach(driver => {
        if (driver.current_lat && driver.current_lng) {
            const color = getDriverMarkerColor(driver);
            const icon = createDriverIcon(driver, color);
            
            const marker = L.marker([driver.current_lat, driver.current_lng], { icon })
                .addTo(driversMap)
                .bindPopup(createDriverPopup(driver));
                
            driverMarkers[driver.id] = marker;
        }
    });
    
    // Update map last update time
    document.getElementById('mapLastUpdate').textContent = new Date().toLocaleTimeString();
}

// Create driver icon
function createDriverIcon(driver, color) {
    let iconClass = 'fas fa-motorcycle';
    if (driver.vehicle_type === 'bicycle') iconClass = 'fas fa-bicycle';
    if (driver.vehicle_type === 'car') iconClass = 'fas fa-car';
    
    return L.divIcon({
        className: 'driver-marker',
        html: `<i class="${iconClass}" style="color: ${color}; font-size: 16px;"></i>`,
        iconSize: [25, 25],
        iconAnchor: [12, 12]
    });
}

// Get driver marker color based on status
function getDriverMarkerColor(driver) {
    if (!driver.is_active) return '#6c757d'; // Gray for inactive
    if (!driver.is_available) return '#ffc107'; // Yellow for busy
    
    // Check location freshness
    if (driver.last_location_update) {
        const updateTime = new Date(driver.last_location_update);
        const now = new Date();
        const diffMinutes = (now - updateTime) / (1000 * 60);
        
        if (diffMinutes < 10) return '#28a745'; // Green for live location
        if (diffMinutes < 60) return '#fd7e14'; // Orange for recent
        return '#dc3545'; // Red for outdated
    }
    
    return '#dc3545'; // Red for no location data
}

// Create driver popup content
function createDriverPopup(driver) {
    const status = driver.is_available ? 'Available' : 'Busy';
    const lastUpdate = driver.last_location_update ? 
        formatTimeAgo(new Date(driver.last_location_update)) : 'Never';
    
    return `
        <div class="driver-popup">
            <h6><i class="fas fa-user"></i> ${driver.name}</h6>
            <p>
                <strong>Phone:</strong> ${driver.phone_number}<br>
                <strong>Vehicle:</strong> ${driver.vehicle_type}<br>
                <strong>Status:</strong> ${status}<br>
                <strong>Last Update:</strong> ${lastUpdate}
            </p>
            <div class="btn-group" role="group">
                <button class="btn btn-sm btn-primary" onclick="requestDriverLocation(${driver.id})">
                    <i class="fas fa-location-arrow"></i> Request Location
                </button>
                <button class="btn btn-sm btn-success" onclick="requestDriverLiveLocation(${driver.id})">
                    <i class="fas fa-broadcast-tower"></i> Live Location
                </button>
            </div>
        </div>
    `;
}

// Update driver statistics
function updateDriversStats(drivers) {
    const totalDrivers = drivers.length;
    const onlineDrivers = drivers.filter(d => d.is_active).length;
    const availableDrivers = drivers.filter(d => d.is_active && d.is_available).length;
    const busyDrivers = drivers.filter(d => d.is_active && !d.is_available).length;
    const trackingDrivers = drivers.filter(d => {
        if (!d.last_location_update) return false;
        const diffMinutes = (new Date() - new Date(d.last_location_update)) / (1000 * 60);
        return diffMinutes < 10;
    }).length;
    
    // Update dashboard cards
    document.getElementById('totalDriversCount').textContent = totalDrivers;
    document.getElementById('onlineDriversCount').textContent = onlineDrivers;
    document.getElementById('availableDriversCount').textContent = availableDrivers;
    document.getElementById('busyDriversCount').textContent = busyDrivers;
    document.getElementById('trackingDriversCount').textContent = trackingDrivers;
}

// Request location from driver
function requestDriverLocation(driverId) {
    fetch(`/api/drivers/${driverId}/location-request`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showSuccess(data.message);
        } else {
            showError(data.message);
        }
    })
    .catch(error => {
        console.error('Error requesting location:', error);
        showError('Failed to request location');
    });
}

// Request live location from driver
function requestDriverLiveLocation(driverId) {
    fetch(`/api/drivers/${driverId}/live-location-request`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showSuccess(data.message);
        } else {
            showError(data.message);
        }
    })
    .catch(error => {
        console.error('Error requesting live location:', error);
        showError('Failed to request live location');
    });
}

// Request all drivers location
function requestAllDriversLocation() {
    fetch('/api/drivers')
        .then(response => response.json())
        .then(drivers => {
            const activeDrivers = drivers.filter(d => d.is_active && d.telegram_user_id);
            
            if (activeDrivers.length === 0) {
                showError('No active drivers with Telegram accounts found');
                return;
            }
            
            let requestCount = 0;
            activeDrivers.forEach(driver => {
                fetch(`/api/drivers/${driver.id}/location-request`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' }
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) requestCount++;
                    
                    // Show result after all requests complete
                    if (requestCount === activeDrivers.length) {
                        showSuccess(`Location requests sent to ${requestCount} drivers`);
                    }
                })
                .catch(error => console.error('Error:', error));
            });
        })
        .catch(error => {
            console.error('Error fetching drivers:', error);
            showError('Failed to fetch drivers');
        });
}

// View driver on map
function viewDriverOnMap(driverId) {
    const marker = driverMarkers[driverId];
    if (marker) {
        driversMap.setView(marker.getLatLng(), 15);
        marker.openPopup();
    }
}

// Toggle driver availability
function toggleDriverAvailability(driverId) {
    // This would need an API endpoint to toggle availability
    console.log('Toggle availability for driver:', driverId);
}

// Auto-refresh drivers
function startDriversAutoRefresh() {
    if (autoRefreshInterval) {
        clearInterval(autoRefreshInterval);
    }
    
    autoRefreshInterval = setInterval(() => {
        loadDrivers();
    }, 30000); // Refresh every 30 seconds
}

// Stop auto-refresh
function stopDriversAutoRefresh() {
    if (autoRefreshInterval) {
        clearInterval(autoRefreshInterval);
        autoRefreshInterval = null;
    }
}

// Refresh driver map manually
function refreshDriverMap() {
    loadDrivers();
    showSuccess('Map refreshed');
}

// Toggle map view (satellite/normal)
function toggleMapView() {
    // This would toggle between different tile layers
    console.log('Toggle map view');
}

// Utility functions
function formatTimeAgo(date) {
    const now = new Date();
    const diffMs = now - date;
    const diffMinutes = Math.floor(diffMs / (1000 * 60));
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
    
    if (diffMinutes < 1) return 'Just now';
    if (diffMinutes < 60) return `${diffMinutes}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    return date.toLocaleDateString();
}

function showSuccess(message) {
    // You could implement a toast notification system here
    console.log('Success:', message);
    alert(message);
}

function showError(message) {
    // You could implement a toast notification system here
    console.error('Error:', message);
    alert('Error: ' + message);
}

// Export functions for global access
window.initializeLiveTracking = initializeLiveTracking;
window.refreshDriverMap = refreshDriverMap;
window.toggleMapView = toggleMapView;
window.requestAllDriversLocation = requestAllDriversLocation;
window.requestDriverLocation = requestDriverLocation;
window.requestDriverLiveLocation = requestDriverLiveLocation;
window.viewDriverOnMap = viewDriverOnMap;
window.toggleDriverAvailability = toggleDriverAvailability;