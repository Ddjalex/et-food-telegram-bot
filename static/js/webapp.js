// Telegram WebApp JavaScript
let selectedItems = [];
let menuItems = [];
let userLocation = null;

// Initialize Telegram WebApp
if (window.Telegram && window.Telegram.WebApp) {
    const tg = window.Telegram.WebApp;
    tg.ready();
    
    // Set main button
    tg.MainButton.text = "Place Order";
    tg.MainButton.show();
    
    // Handle main button click
    tg.MainButton.onClick(() => {
        submitOrder();
    });
    
    // Auto-fill user data if available
    if (tg.initDataUnsafe && tg.initDataUnsafe.user) {
        const user = tg.initDataUnsafe.user;
        const customerNameElement = document.getElementById('customerName');
        if (customerNameElement) {
            if (user.first_name && user.last_name) {
                customerNameElement.value = `${user.first_name} ${user.last_name}`;
            } else if (user.first_name) {
                customerNameElement.value = user.first_name;
            }
        }
    }
}

// Load categories
async function loadCategories() {
    try {
        const response = await fetch('/api/categories');
        const categories = await response.json();
        displayCategories(categories);
    } catch (error) {
        console.error('Error loading categories:', error);
    }
}

// Display categories
function displayCategories(categories) {
    const container = document.getElementById('categoriesContainer');
    if (!container) return;
    
    container.innerHTML = '';
    
    categories.forEach(category => {
        const categoryCard = document.createElement('div');
        categoryCard.className = `category-card category-${category.name.toLowerCase().replace(/\s+/g, '-')}`;
        categoryCard.onclick = () => filterCategory(category.name);
        
        const categoryHTML = category.image_url ? 
            `<img src="${category.image_url}" alt="${category.name}" style="width: 32px; height: 32px; border-radius: 50%; object-fit: cover; margin-bottom: 8px;">` :
            `<span class="category-icon">${category.icon}</span>`;
        
        categoryCard.innerHTML = `
            ${categoryHTML}
            <div>${category.name}</div>
        `;
        
        container.appendChild(categoryCard);
    });
}

// Load menu items
async function loadMenuItems() {
    try {
        const response = await fetch('/api/menu');
        menuItems = await response.json();
        displayMenuItems();
    } catch (error) {
        console.error('Error loading menu:', error);
        const productGrid = document.getElementById('productGrid');
        if (productGrid) {
            productGrid.innerHTML = `
                <div class="col-12">
                    <div class="alert alert-danger">
                        <i class="fas fa-exclamation-triangle"></i>
                        Failed to load menu items. Please try again.
                    </div>
                </div>
            `;
        }
    }
}

// Display menu items
function displayMenuItems() {
    const container = document.getElementById('menuItems');
    if (!container) return;
    
    container.innerHTML = '';

    menuItems.forEach(item => {
        const col = document.createElement('div');
        col.className = 'col-md-6 mb-3';
        
        col.innerHTML = `
            <div class="card menu-item-card">
                <img src="${item.image_url}" class="card-img-top" alt="${item.name}" style="height: 200px; object-fit: cover;">
                <div class="card-body">
                    <h5 class="card-title">${item.name}</h5>
                    <p class="card-text">${item.description}</p>
                    <div class="d-flex justify-content-between align-items-center">
                        <span class="h5 mb-0 text-success">ETB ${item.price.toFixed(2)}</span>
                        <div class="btn-group" role="group">
                            <button class="btn btn-outline-secondary" onclick="updateQuantity(${item.id}, -1)">
                                <i class="fas fa-minus"></i>
                            </button>
                            <span class="btn btn-outline-secondary" id="qty-${item.id}">0</span>
                            <button class="btn btn-outline-secondary" onclick="updateQuantity(${item.id}, 1)">
                                <i class="fas fa-plus"></i>
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        container.appendChild(col);
    });
}

// Update item quantity
function updateQuantity(itemId, change) {
    const item = menuItems.find(i => i.id === itemId);
    if (!item) return;

    const existingItemIndex = selectedItems.findIndex(i => i.id === itemId);
    
    if (existingItemIndex >= 0) {
        selectedItems[existingItemIndex].quantity += change;
        if (selectedItems[existingItemIndex].quantity <= 0) {
            selectedItems.splice(existingItemIndex, 1);
        }
    } else if (change > 0) {
        selectedItems.push({
            id: itemId,
            name: item.name,
            price: item.price,
            quantity: change
        });
    }

    // Update display
    const qtyElement = document.getElementById(`qty-${itemId}`);
    if (qtyElement) {
        const currentItem = selectedItems.find(i => i.id === itemId);
        qtyElement.textContent = currentItem ? currentItem.quantity : 0;
    }

    updateOrderSummary();
    updateCartDisplay();
}

// Update order summary
function updateOrderSummary() {
    const summaryContainer = document.getElementById('orderSummary');
    const totalElement = document.getElementById('totalAmount');
    
    if (!summaryContainer || !totalElement) return;

    if (selectedItems.length === 0) {
        summaryContainer.innerHTML = '<p class="text-muted">No items selected</p>';
        totalElement.textContent = '0.00';
        return;
    }

    let total = 0;
    let summaryHTML = '';

    selectedItems.forEach(item => {
        const itemTotal = item.price * item.quantity;
        total += itemTotal;
        
        summaryHTML += `
            <div class="d-flex justify-content-between">
                <span>${item.name} x${item.quantity}</span>
                <span>ETB ${itemTotal.toFixed(2)}</span>
            </div>
        `;
    });

    summaryContainer.innerHTML = summaryHTML;
    totalElement.textContent = total.toFixed(2);
}

// Share location
function shareLocation() {
    if (window.Telegram && window.Telegram.WebApp) {
        // Try to get location from Telegram WebApp
        const tg = window.Telegram.WebApp;
        
        // Use Telegram's location request
        if (tg.sendData) {
            // Request location permission from Telegram
            if (navigator.geolocation) {
                navigator.geolocation.getCurrentPosition(
                    (position) => {
                        userLocation = {
                            latitude: position.coords.latitude,
                            longitude: position.coords.longitude
                        };
                        updateLocationDisplay(userLocation);
                        tg.showAlert('Location captured successfully!');
                    },
                    (error) => {
                        console.error('Error getting location:', error);
                        tg.showAlert('Failed to get location. Please enter your address manually.');
                    },
                    {
                        enableHighAccuracy: true,
                        timeout: 10000,
                        maximumAge: 60000
                    }
                );
            } else {
                tg.showAlert('Geolocation not supported. Please enter your address manually.');
            }
        }
    } else if (navigator.geolocation) {
        // Fallback to browser geolocation
        navigator.geolocation.getCurrentPosition(
            (position) => {
                userLocation = {
                    latitude: position.coords.latitude,
                    longitude: position.coords.longitude
                };
                updateLocationDisplay(userLocation);
                alert('Location captured successfully!');
            },
            (error) => {
                console.error('Error getting location:', error);
                alert('Failed to get location. Please enter your address manually.');
            },
            {
                enableHighAccuracy: true,
                timeout: 10000,
                maximumAge: 60000
            }
        );
    } else {
        alert('Location sharing not supported. Please enter your address manually.');
    }
}

// Update location display
function updateLocationDisplay(location) {
    const addressField = document.getElementById('customerAddress');
    const locationBtn = document.getElementById('shareLocationBtn');
    
    // Update address field with coordinates
    const currentAddress = addressField.value;
    const locationText = `📍 Location: ${location.latitude.toFixed(6)}, ${location.longitude.toFixed(6)}`;
    
    if (currentAddress && !currentAddress.includes('📍 Location:')) {
        addressField.value = `${currentAddress}\n${locationText}`;
    } else {
        addressField.value = locationText;
    }
    
    // Update button to show success
    locationBtn.innerHTML = '<i class="fas fa-check"></i> Location Captured';
    locationBtn.classList.remove('btn-outline-secondary');
    locationBtn.classList.add('btn-success');
    
    // You can integrate with a reverse geocoding service here
    // to convert coordinates to a readable address
}

// Submit order
async function submitOrder() {
    try {
        // Validate form
        const form = document.getElementById('orderForm');
        if (!form.checkValidity()) {
            form.reportValidity();
            return;
        }

        if (selectedItems.length === 0) {
            alert('Please select at least one item');
            return;
        }

        // Show loading
        const loadingModal = new bootstrap.Modal(document.getElementById('loadingModal'));
        loadingModal.show();

        // Get Telegram user ID
        let telegramUserId = 0;
        if (window.Telegram && window.Telegram.WebApp && window.Telegram.WebApp.initDataUnsafe) {
            telegramUserId = window.Telegram.WebApp.initDataUnsafe.user?.id || 0;
        }

        // Prepare order data
        const orderData = {
            telegram_user_id: telegramUserId,
            customer_name: document.getElementById('customerName').value,
            customer_phone: document.getElementById('customerPhone').value,
            customer_address: document.getElementById('customerAddress').value,
            items: selectedItems,
            payment_method: document.getElementById('paymentMethod').value,
            location_lat: userLocation?.latitude,
            location_lng: userLocation?.longitude
        };

        // Submit order
        const response = await fetch('/api/orders', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(orderData)
        });

        const result = await response.json();

        if (response.ok) {
            // Order successful
            loadingModal.hide();
            
            if (window.Telegram && window.Telegram.WebApp) {
                window.Telegram.WebApp.showAlert('Order placed successfully! You will receive a confirmation message shortly.');
                window.Telegram.WebApp.close();
            } else {
                alert('Order placed successfully!');
                // Reset form
                form.reset();
                selectedItems = [];
                updateOrderSummary();
                displayMenuItems();
            }
        } else {
            throw new Error(result.error || 'Failed to place order');
        }
    } catch (error) {
        console.error('Error submitting order:', error);
        
        // Hide loading modal
        const loadingModal = bootstrap.Modal.getInstance(document.getElementById('loadingModal'));
        if (loadingModal) {
            loadingModal.hide();
        }
        
        alert('Failed to place order: ' + error.message);
    }
}

// Update cart display
function updateCartDisplay() {
    const cartCount = document.getElementById('cartCount');
    const cartItems = document.getElementById('cartItems');
    const cartTotal = document.getElementById('cartTotal');
    const proceedBtn = document.getElementById('proceedToCheckout');
    
    // Update cart count (both mobile and desktop)
    const totalItems = selectedItems.reduce((sum, item) => sum + item.quantity, 0);
    cartCount.textContent = totalItems;
    cartCount.style.display = totalItems > 0 ? 'inline' : 'none';
    
    // Update desktop cart count if exists
    const cartCountDesktop = document.getElementById('cartCountDesktop');
    if (cartCountDesktop) {
        cartCountDesktop.textContent = totalItems;
        cartCountDesktop.style.display = totalItems > 0 ? 'inline' : 'none';
    }
    
    // Update cart item count in view cart button
    const cartItemCount = document.getElementById('cartItemCount');
    if (cartItemCount) {
        cartItemCount.textContent = totalItems;
    }
    
    // Update cart status text
    const cartStatusText = document.getElementById('cartStatusText');
    if (cartStatusText) {
        if (totalItems === 0) {
            cartStatusText.textContent = 'Your cart is empty';
        } else if (totalItems === 1) {
            cartStatusText.textContent = '1 item in cart';
        } else {
            cartStatusText.textContent = `${totalItems} items in cart`;
        }
    }
    
    // Show cart notice temporarily when items are added
    if (totalItems > 0) {
        const cartNotice = document.getElementById('cartNotice');
        if (cartNotice) {
            cartNotice.style.display = 'block';
            // Hide after 3 seconds
            setTimeout(() => {
                cartNotice.style.display = 'none';
            }, 3000);
        }
    }
    
    // Update cart items
    if (selectedItems.length === 0) {
        cartItems.innerHTML = '<p class="text-muted text-center">Your cart is empty</p>';
        cartTotal.textContent = '0.00';
        proceedBtn.disabled = true;
        return;
    }
    
    let total = 0;
    let cartHTML = '';
    
    selectedItems.forEach(item => {
        const itemTotal = item.price * item.quantity;
        total += itemTotal;
        
        cartHTML += `
            <div class="d-flex justify-content-between align-items-center mb-2 p-2 border rounded">
                <div>
                    <h6 class="mb-0">${item.name}</h6>
                    <small class="text-muted">ETB ${item.price.toFixed(2)} each</small>
                </div>
                <div class="d-flex align-items-center">
                    <button class="btn btn-sm btn-outline-secondary me-2" onclick="updateQuantity(${item.id}, -1)">
                        <i class="fas fa-minus"></i>
                    </button>
                    <span class="mx-2">${item.quantity}</span>
                    <button class="btn btn-sm btn-outline-secondary me-2" onclick="updateQuantity(${item.id}, 1)">
                        <i class="fas fa-plus"></i>
                    </button>
                    <span class="fw-bold">ETB ${itemTotal.toFixed(2)}</span>
                </div>
            </div>
        `;
    });
    
    cartItems.innerHTML = cartHTML;
    cartTotal.textContent = total.toFixed(2);
    proceedBtn.disabled = false;
}

// Proceed to checkout
function proceedToCheckout() {
    if (selectedItems.length === 0) {
        alert('Your cart is empty!');
        return;
    }
    
    // Close cart modal
    const cartModal = bootstrap.Modal.getInstance(document.getElementById('cartModal'));
    if (cartModal) {
        cartModal.hide();
    }
    
    // Fill checkout form with cart data
    updateCheckoutSummary();
    
    // Auto-fill user data if available
    if (window.Telegram && window.Telegram.WebApp && window.Telegram.WebApp.initDataUnsafe) {
        const user = window.Telegram.WebApp.initDataUnsafe.user;
        if (user && user.first_name) {
            document.getElementById('checkoutName').value = user.last_name ? 
                `${user.first_name} ${user.last_name}` : user.first_name;
        }
    }
    
    // Show checkout modal
    const checkoutModal = new bootstrap.Modal(document.getElementById('checkoutModal'));
    checkoutModal.show();
}

// Update checkout summary
function updateCheckoutSummary() {
    const checkoutSummary = document.getElementById('checkoutSummary');
    const checkoutTotal = document.getElementById('checkoutTotal');
    
    if (selectedItems.length === 0) {
        checkoutSummary.innerHTML = '<p class="text-muted">No items selected</p>';
        checkoutTotal.textContent = '0.00';
        return;
    }
    
    let total = 0;
    let summaryHTML = '';
    
    selectedItems.forEach(item => {
        const itemTotal = item.price * item.quantity;
        total += itemTotal;
        
        summaryHTML += `
            <div class="d-flex justify-content-between mb-1">
                <span>${item.name} x${item.quantity}</span>
                <span>ETB ${itemTotal.toFixed(2)}</span>
            </div>
        `;
    });
    
    checkoutSummary.innerHTML = summaryHTML;
    checkoutTotal.textContent = total.toFixed(2);
}

// Place order from checkout
async function placeOrder() {
    try {
        // Validate checkout form
        const form = document.getElementById('checkoutForm');
        if (!form.checkValidity()) {
            form.reportValidity();
            return;
        }
        
        if (selectedItems.length === 0) {
            alert('Your cart is empty!');
            return;
        }
        
        // Show loading
        const loadingModal = new bootstrap.Modal(document.getElementById('loadingModal'));
        loadingModal.show();
        
        // Get Telegram user ID
        let telegramUserId = 0;
        if (window.Telegram && window.Telegram.WebApp && window.Telegram.WebApp.initDataUnsafe) {
            telegramUserId = window.Telegram.WebApp.initDataUnsafe.user?.id || 0;
        }
        
        // Prepare order data
        const orderData = {
            telegram_user_id: telegramUserId,
            customer_name: document.getElementById('checkoutName').value,
            customer_phone: document.getElementById('checkoutPhone').value,
            customer_address: document.getElementById('checkoutAddress').value,
            items: selectedItems,
            payment_method: document.getElementById('checkoutPayment').value,
            location_lat: userLocation?.latitude,
            location_lng: userLocation?.longitude
        };
        
        // Submit order
        const response = await fetch('/api/orders', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(orderData)
        });
        
        const result = await response.json();
        
        if (response.ok) {
            // Order successful
            loadingModal.hide();
            
            // Hide checkout modal
            const checkoutModal = bootstrap.Modal.getInstance(document.getElementById('checkoutModal'));
            if (checkoutModal) {
                checkoutModal.hide();
            }
            
            if (window.Telegram && window.Telegram.WebApp) {
                // Use showAlert instead of showPopup for better compatibility
                window.Telegram.WebApp.showAlert('Order placed successfully! You will receive a confirmation message shortly.');
                window.Telegram.WebApp.close();
            } else {
                alert('Order placed successfully!');
                // Reset cart
                selectedItems = [];
                updateCartDisplay();
                updateOrderSummary();
                displayMenuItems();
            }
        } else {
            throw new Error(result.error || 'Failed to place order');
        }
    } catch (error) {
        console.error('Error placing order:', error);
        
        // Hide loading modal
        const loadingModal = bootstrap.Modal.getInstance(document.getElementById('loadingModal'));
        if (loadingModal) {
            loadingModal.hide();
        }
        
        if (window.Telegram && window.Telegram.WebApp) {
            window.Telegram.WebApp.showAlert('Failed to place order: ' + error.message);
        } else {
            alert('Failed to place order: ' + error.message);
        }
    }
}

// Event listeners
document.getElementById('shareLocationBtn').addEventListener('click', shareLocation);
document.getElementById('orderForm').addEventListener('submit', (e) => {
    e.preventDefault();
    submitOrder();
});

// Load order history
async function loadOrderHistory() {
    try {
        const historyContent = document.getElementById('orderHistoryContent');
        
        // Get Telegram user ID
        let telegramUserId = 0;
        if (window.Telegram && window.Telegram.WebApp && window.Telegram.WebApp.initDataUnsafe) {
            telegramUserId = window.Telegram.WebApp.initDataUnsafe.user?.id || 0;
        }
        
        if (telegramUserId === 0) {
            historyContent.innerHTML = `
                <div class="alert alert-info text-center">
                    <i class="fas fa-info-circle"></i>
                    <p class="mb-0">Order history is only available when using the Telegram bot.</p>
                </div>
            `;
            return;
        }
        
        // Fetch orders
        const response = await fetch(`/api/user-orders/${telegramUserId}`);
        
        if (!response.ok) {
            throw new Error('Failed to fetch orders');
        }
        
        const orders = await response.json();
        
        if (orders.length === 0) {
            historyContent.innerHTML = `
                <div class="alert alert-info text-center">
                    <i class="fas fa-shopping-bag"></i>
                    <p class="mb-0">No orders found. Place your first order to see it here!</p>
                </div>
            `;
            return;
        }
        
        // Display orders
        let historyHTML = '';
        orders.forEach(order => {
            const statusBadge = getStatusBadge(order.status);
            const orderDate = new Date(order.created_at).toLocaleDateString();
            
            historyHTML += `
                <div class="order-card">
                    <div class="order-header">
                        <div class="order-info">
                            <div class="order-number">Order Details</div>
                            <div class="order-date">${orderDate}</div>
                        </div>
                        <div class="order-status-price">
                            ${statusBadge}
                            <div class="order-total">ETB ${order.total_amount.toFixed(2)}</div>
                        </div>
                    </div>
                    
                    <div class="order-items">
                        ${order.items.map(item => `
                            <div class="item-row">
                                <span>${item.name} x${item.quantity}</span>
                                <span>ETB ${(item.price * item.quantity).toFixed(2)}</span>
                            </div>
                        `).join('')}
                    </div>
                    
                    <div class="order-actions">
                        ${order.status === 'pending' ? 
                            '<button class="order-action-btn btn-cancel" onclick="cancelOrder(' + order.id + ')">Cancel</button>' : ''}
                        ${order.status !== 'cancelled' && order.status !== 'delivered' ? 
                            '<button class="order-action-btn btn-track" onclick="trackOrder(' + order.id + ')">Track</button>' : ''}
                        <button class="order-action-btn btn-reorder" onclick="reorderItems(' + order.id + ')">Reorder</button>
                    </div>
                </div>
            `;
        });
        
        historyContent.innerHTML = historyHTML;
        
    } catch (error) {
        console.error('Error loading order history:', error);
        document.getElementById('orderHistoryContent').innerHTML = `
            <div class="alert alert-danger text-center">
                <i class="fas fa-exclamation-triangle"></i>
                <p class="mb-0">Failed to load order history. Please try again later.</p>
            </div>
        `;
    }
}

// Action functions for order history
function cancelOrder(orderId) {
    if (confirm('Are you sure you want to cancel this order?')) {
        // Implementation for canceling order
        console.log('Canceling order:', orderId);
        // You can add API call here
    }
}

function trackOrder(orderId) {
    console.log('Tracking order:', orderId);
    // Implementation for tracking order
    alert('Order tracking feature will be available soon!');
}

function reorderItems(orderId) {
    console.log('Reordering items from order:', orderId);
    // Implementation for reordering
    alert('Reorder feature will be available soon!');
}

// Get status badge HTML
function getStatusBadge(status) {
    const badges = {
        'pending': '<span class="badge bg-warning">Pending</span>',
        'confirmed': '<span class="badge bg-info">Confirmed</span>',
        'preparing': '<span class="badge bg-primary">Preparing</span>',
        'out_for_delivery': '<span class="badge bg-success">Out for Delivery</span>',
        'delivered': '<span class="badge bg-success">Delivered</span>',
        'cancelled': '<span class="badge bg-danger">Cancelled</span>'
    };
    return badges[status] || '<span class="badge bg-secondary">Unknown</span>';
}

// Navigation functions for bottom navigation bar
function scrollToCategory(category) {
    // Look for category heading or menu items with data-category attribute
    let targetElement = document.querySelector(`[data-category="${category}"]`);
    
    if (!targetElement) {
        // Fallback: look for heading containing category name
        const headings = document.querySelectorAll('h4, h5, h6');
        for (let heading of headings) {
            if (heading.textContent.toLowerCase().includes(category.toLowerCase())) {
                targetElement = heading;
                break;
            }
        }
    }
    
    if (targetElement) {
        targetElement.scrollIntoView({ behavior: 'smooth', block: 'start' });
    } else {
        // Final fallback: scroll to menu section
        const menuSection = document.getElementById('menuItems');
        if (menuSection) {
            menuSection.scrollIntoView({ behavior: 'smooth' });
        }
    }
}

function scrollToTop() {
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

// Show all items
function showAllItems() {
    displayMenuItems();
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    loadMenuItems();
    
    // Cart event listeners
    document.getElementById('proceedToCheckout').addEventListener('click', proceedToCheckout);
    document.getElementById('placeOrderBtn').addEventListener('click', placeOrder);
    
    // Order history event listener
    document.getElementById('historyModal').addEventListener('shown.bs.modal', loadOrderHistory);
    
    // View cart button event listener
    const viewCartBtn = document.getElementById('viewCartBtn');
    if (viewCartBtn) {
        viewCartBtn.addEventListener('click', function() {
            updateCartDisplay();
        });
    }
    
    // Initialize cart display
    updateCartDisplay();
    
    // Load categories for the user interface
    loadCategories();
});

// Filter products by category
function filterCategory(categoryName) {
    console.log('Filtering by category:', categoryName);
    
    // Create a mapping for category names
    const categoryMapping = {
        'burgers': 'Burgers',
        'snacks': ['Snacks', 'Fries & Pancakes'],
        'sauces': ['Sauces', 'Extras'],
        'drinks': 'Drinks',
        'shawarma': 'Shawarma',
        'sandwiches': ['Sandwiches & Wraps'],
        'pizza': 'Pizza',
        'pasta': 'Pasta',
        'rice': 'Rice Dishes',
        'egg': 'Egg Dishes & Toast',
        'traditional': 'Traditional Ethiopian Breakfast',
        'borrito': 'Borrito'
    };
    
    // Get the actual category names to filter by
    let categoriesToFilter = categoryMapping[categoryName.toLowerCase()];
    if (!categoriesToFilter) {
        categoriesToFilter = [categoryName];
    }
    if (!Array.isArray(categoriesToFilter)) {
        categoriesToFilter = [categoriesToFilter];
    }
    
    const filteredItems = menuItems.filter(item => 
        item.category && categoriesToFilter.some(cat => 
            item.category.toLowerCase().includes(cat.toLowerCase()) || 
            cat.toLowerCase().includes(item.category.toLowerCase())
        )
    );
    
    const container = document.getElementById('menuItems');
    if (!container) return;
    
    container.innerHTML = '';
    
    if (filteredItems.length === 0) {
        container.innerHTML = '<div class="col-12 text-center"><p>No items in this category</p></div>';
        return;
    }
    
    filteredItems.forEach(item => {
        if (item.available) {
            const col = document.createElement('div');
            col.className = 'col-md-6 mb-3';
            
            col.innerHTML = `
                <div class="card menu-item-card">
                    <img src="${item.image_url}" class="card-img-top" alt="${item.name}" style="height: 200px; object-fit: cover;">
                    <div class="card-body">
                        <h5 class="card-title">${item.name}</h5>
                        <p class="card-text">${item.description}</p>
                        <div class="d-flex justify-content-between align-items-center">
                            <span class="h5 mb-0 text-success">ETB ${item.price.toFixed(2)}</span>
                            <div class="btn-group" role="group">
                                <button class="btn btn-outline-secondary" onclick="updateQuantity(${item.id}, -1)">
                                    <i class="fas fa-minus"></i>
                                </button>
                                <span class="btn btn-outline-secondary" id="qty-${item.id}">0</span>
                                <button class="btn btn-outline-secondary" onclick="updateQuantity(${item.id}, 1)">
                                    <i class="fas fa-plus"></i>
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            `;
            
            container.appendChild(col);
        }
    });
}
