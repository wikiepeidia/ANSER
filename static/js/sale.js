document.addEventListener('DOMContentLoaded', function () {
    // DOM Elements
    const searchInput = document.getElementById('productSearch');
    const searchResults = document.getElementById('searchResults');
    const productSuggestions = document.getElementById('productSuggestions');
    const cartItemsContainer = document.getElementById('cartItemsContainer');
    const cartTableBody = document.getElementById('cartTableBody');
    const cartTable = document.querySelector('.cart-table');
    const emptyCartMsg = document.querySelector('.empty-cart-msg');
    const grandTotalEl = document.getElementById('grandTotal');
    const customerGivenInput = document.getElementById('customerGiven');
    const refundAmountEl = document.getElementById('refundAmount');
    const btnCompleteSale = document.getElementById('btnCompleteSale');
    const btnClearCart = document.getElementById('btnClearCart');
    const cartItemCount = document.getElementById('cartItemCount');

    // State
    let cart = [];
    let products = []; // Will load from API
    
    // Format Currency
    const formatCurrency = (amount) => {
        return new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(amount);
    };

    // Parse Currency (remove symbols)
    const parseCurrency = (str) => {
        return Number(str.replace(/[^0-9.-]+/g,""));
    };

    // Initial Load of Products (Random suggestions)
    fetchProducts();

    async function fetchProducts(query = '') {
        try {
            const url = query ? `/api/products/search?q=${encodeURIComponent(query)}` : '/api/products/search?random=true';
            const response = await fetch(url);
            const data = await response.json();
            
            if (query) {
                renderSearchResults(data);
            } else {
                renderSuggestions(data);
            }
        } catch (error) {
            console.error('Error fetching products:', error);
        }
    }

    // Render Suggestions (Grid)
    function renderSuggestions(items) {
        productSuggestions.innerHTML = items.map(p => `
            <div class="col">
                <div class="card h-100 product-card shadow-sm" onclick="addToCart('${p.id}', '${p.name.replace(/'/g, "\\'")}', ${p.price})">
                    <div class="card-body d-flex flex-column">
                        <h6 class="card-title text-truncate" title="${p.name}">${p.name}</h6>
                        <div class="mt-auto d-flex justify-content-between align-items-center">
                            <span class="product-price">${formatCurrency(p.price)}</span>
                            <button class="btn btn-sm btn-outline-primary rounded-circle">
                                <i class="fas fa-plus"></i>
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `).join('');
    }

    // Render Search Results (Dropdown)
    function renderSearchResults(items) {
        if (items.length === 0) {
            searchResults.style.display = 'none';
            return;
        }
        
        searchResults.innerHTML = items.map(p => `
            <div class="search-result-item d-flex justify-content-between align-items-center" 
             onclick="addToCart('${p.id}', '${p.name.replace(/'/g, "\\'")}', ${p.price}); clearSearch();">
                <div>
                    <div class="fw-bold">${p.name}</div>
                    <small class="text-muted">${p.id}</small>
                </div>
                <div class="fw-bold text-primary">${formatCurrency(p.price)}</div>
            </div>
        `).join('');
        searchResults.style.display = 'block';
    }

    // Search Input Handler
    let debounceTimer;
    searchInput.addEventListener('input', (e) => {
        const query = e.target.value.trim();
        clearTimeout(debounceTimer);
        
        if (query.length > 1) {
            debounceTimer = setTimeout(() => fetchProducts(query), 300);
        } else {
            searchResults.style.display = 'none';
        }
    });

    // Show suggestions on focus
    searchInput.addEventListener('focus', () => {
        if (!searchInput.value) {
            fetchProducts(); // Refresh suggestions
        }
    });

    // Click outside to close search
    document.addEventListener('click', (e) => {
        if (!searchInput.contains(e.target) && !searchResults.contains(e.target)) {
            searchResults.style.display = 'none';
        }
    });

    // Make addToCart global so it can be called from HTML onclick
    window.addToCart = function(id, name, price) {
        const existingItem = cart.find(item => item.id === id);
        
        if (existingItem) {
            existingItem.qty += 1;
        } else {
            cart.push({ id, name, price, qty: 1 });
        }
        
        updateCartUI();
    };

    window.clearSearch = function() {
        searchInput.value = '';
        searchResults.style.display = 'none';
        searchInput.focus();
    };

    // Remove item
    window.removeFromCart = function(id) {
        cart = cart.filter(item => item.id !== id);
        updateCartUI();
    };

    // Update Quantity
    window.updateQty = function(id, newQty) {
        const item = cart.find(item => item.id === id);
        if (item) {
            item.qty = parseInt(newQty);
            if (item.qty <= 0) removeFromCart(id);
            else updateCartUI();
        }
    };

    // Update Price
    window.updatePrice = function(id, newPrice) {
        const item = cart.find(item => item.id === id);
        if (item) {
            item.price = parseFloat(newPrice);
            updateCartUI(); // To update total
        }
    };

    function updateCartUI() {
        // Toggle empty state
        if (cart.length === 0) {
            emptyCartMsg.style.display = 'block';
            cartTable.style.display = 'none';
            btnCompleteSale.disabled = true;
        } else {
            emptyCartMsg.style.display = 'none';
            cartTable.style.display = 'table';
            btnCompleteSale.disabled = false;
        }

        // Render rows
        cartTableBody.innerHTML = cart.map(item => `
            <tr class="cart-item-row">
                <td>
                    <div class="fw-medium text-truncate" style="max-width: 200px;" title="${item.name}">${item.name}</div>
                    <small class="text-muted" style="font-size: 0.75rem;">${item.id}</small>
                </td>
                <td>
                    <input type="number" class="qty-input" value="${item.qty}" min="1" 
                        onchange="updateQty('${item.id}', this.value)">
                </td>
                <td>
                    <input type="number" class="price-input" value="${item.price}" min="0" step="1000"
                        onchange="updatePrice('${item.id}', this.value)">
                </td>
                <td class="text-end">
                    <button class="btn-remove-item" onclick="removeFromCart('${item.id}')">
                        <i class="fas fa-times"></i>
                    </button>
                </td>
            </tr>
        `).join('');

        // Update counts and totals
        cartItemCount.innerText = cart.reduce((acc, item) => acc + item.qty, 0) + ' items';
        
        const total = cart.reduce((acc, item) => acc + (item.price * item.qty), 0);
        grandTotalEl.innerText = formatCurrency(total);
        grandTotalEl.dataset.value = total; // Store raw value

        calculateRefund();
    }

    // Payment Logic
    customerGivenInput.addEventListener('input', calculateRefund);

    function calculateRefund() {
        const total = parseFloat(grandTotalEl.dataset.value || 0);
        const given = parseFloat(customerGivenInput.value || 0);
        
        const refund = given - total;
        refundAmountEl.innerText = formatCurrency(refund);
        
        if (refund >= 0 && total > 0) {
            refundAmountEl.classList.remove('text-danger');
            refundAmountEl.classList.add('text-success');
            btnCompleteSale.disabled = false;
        } else if (total > 0) {
            refundAmountEl.classList.remove('text-success');
            refundAmountEl.classList.add('text-danger');
            // Optional: Block sale if not enough money? User requirement didn't specify strict blocking, but implied 'Completed' button.
            // Keeping it enabled but showing negative refund (debt) might be useful in some contexts, but usually POS requires full payment.
            // Let's assume strict payment for now unless given > total.
        }
    }

    // Clear Cart
    btnClearCart.addEventListener('click', () => {
        if(confirm('Are you sure you want to clear the cart?')) {
            cart = [];
            customerGivenInput.value = '';
            calculateRefund();
            updateCartUI();
        }
    });

    // History Logic
    let historySearchTimer;

    let currentHistoryData = [];

    window.refreshHistory = async function() {
        const query = document.getElementById('historySearchInput').value;
        const tbody = document.getElementById('historyTableBody');
        
        // Show loading state if it is a manual refresh or first load
        tbody.innerHTML = '<tr><td colspan="6" class="text-center py-4 text-body"><i class="fas fa-spinner fa-spin me-2"></i>Loading...</td></tr>';
        
        try {
            // Fetch 20 records by default
            const response = await fetch(`/api/sales/history?limit=20&q=${encodeURIComponent(query)}`);
            if (response.ok) {
                const history = await response.json();
                currentHistoryData = history; // Store for details view

                if (history.length === 0) {
                    tbody.innerHTML = '<tr><td colspan="6" class="text-center py-4 text-muted">No sales found.</td></tr>';
                } else {
                    tbody.innerHTML = history.map(sale => `
                        <tr>
                            <td><small class="id-cell">#${sale.id}</small></td>
                            <td>${sale.date}</td>
                            <td><span class="badge bg-secondary">${sale.payment_method}</span></td>
                            <td class="text-center">
                                <span class="badge badge-item-count">${sale.item_count}</span>
                            </td>
                            <td class="text-end fw-bold">${formatCurrency(sale.amount)}</td>
                            <td class="text-center">
                                <div class="btn-group btn-group-sm">
                                    <button class="btn btn-outline-primary" onclick="viewSaleDetails(${sale.id})" title="View Items">
                                        <i class="fas fa-eye"></i>
                                    </button>
                                    <button class="btn btn-outline-danger" onclick="deleteSale(${sale.id})" title="Delete Record">
                                        <i class="fas fa-trash"></i>
                                    </button>
                                </div>
                            </td>
                        </tr>
                    `).join('');
                }
            } else {
                console.error('Sales History Error:', response.status, response.statusText);
                tbody.innerHTML = `<tr><td colspan="6" class="text-center text-danger py-4">Failed to load history (${response.status}).</td></tr>`;
            }
        } catch (error) {
            console.error('Error fetching history:', error);
            tbody.innerHTML = `<tr><td colspan="6" class="text-center text-danger py-4">Error: ${error.message}</td></tr>`;
        }
    }

    window.deleteSale = async function(saleId) {
        if (!confirm('Are you sure you want to delete this sale record? It cannot be undone.')) return;
        
        try {
            const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');
            const response = await fetch(`/api/sales/history/${saleId}`, {
                method: 'DELETE',
                headers: {
                    'X-CSRFToken': csrfToken
                }
            });
            
            const result = await response.json();
            if (result.success) {
                // Refresh list
                refreshHistory();
            } else {
                alert('Failed to delete: ' + result.message);
            }
        } catch (error) {
            console.error('Error deleting sale:', error);
            alert('An unexpected error occurred.');
        }
    }

    window.viewSaleDetails = function(saleId) {
        const sale = currentHistoryData.find(s => s.id === saleId);
        if (!sale) return;

        document.getElementById('detailSaleId').textContent = sale.id;
        document.getElementById('detailSaleDate').textContent = sale.date;
        document.getElementById('detailSaleMethod').textContent = sale.payment_method;
        document.getElementById('detailSaleTotal').textContent = formatCurrency(sale.amount);

        const tbody = document.getElementById('detailItemsBody');
        if (sale.items && sale.items.length > 0) {
            tbody.innerHTML = sale.items.map(item => {
                const price = item.price || 0;
                const qty = item.qty || item.quantity || 0;
                const total = price * qty;
                return `
                    <tr>
                        <td>
                            <div class="fw-bold">${item.name || 'Unknown Item'}</div>
                            <small class="text-muted">${item.id || ''}</small>
                        </td>
                        <td class="text-center align-middle">${qty}</td>
                        <td class="text-end align-middle">${formatCurrency(price)}</td>
                        <td class="text-end align-middle">${formatCurrency(total)}</td>
                    </tr>
                `;
            }).join('');
        } else {
            tbody.innerHTML = '<tr><td colspan="4" class="text-center text-muted">No items data available</td></tr>';
        }

        const modal = new bootstrap.Modal(document.getElementById('saleDetailsModal'));
        modal.show();
    }


    window.showHistory = function() {
        const historyModal = new bootstrap.Modal(document.getElementById('historyModal'));
        historyModal.show();
        
        // Clear previous search when opening
        document.getElementById('historySearchInput').value = '';
        
        // Refresh data
        refreshHistory();
    };

    // Search input listener with debounce
    const historySearchInput = document.getElementById('historySearchInput');
    if (historySearchInput) {
        historySearchInput.addEventListener('input', () => {
            clearTimeout(historySearchTimer);
            historySearchTimer = setTimeout(refreshHistory, 500);
        });
    }

    // Complete Sale
    btnCompleteSale.addEventListener('click', async () => {
        const total = parseFloat(grandTotalEl.dataset.value || 0);
        let given = parseFloat(customerGivenInput.value || 0);
        
        // Get Payment Method
        const paymentMethod = document.querySelector('input[name="paymentMethod"]:checked').value;
        
        // Validation Logic
        if (total === 0) return;
        
        // If card/transfer, assume exact payment if given is 0
        if ((paymentMethod === 'Card' || paymentMethod === 'Transfer') && given === 0) {
            given = total;
            customerGivenInput.value = total; // Visual update
        }
        
        // Basic check for Cash
        if (paymentMethod === 'Cash' && given < total) {
             alert('Insufficient amount given for cash payment.');
             return;
        }

        const refund = given - total;
        
        const saleData = {
            items: cart,
            total_amount: total,
            amount_given: given,
            change_amount: refund,
            payment_method: paymentMethod
        };

        const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');

        try {
            btnCompleteSale.disabled = true;
            btnCompleteSale.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i> Processing...';

            const response = await fetch('/api/sales/create', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify(saleData)
            });

            const result = await response.json();
            
            if (result.success) {
                // Show Modal
                const receiptModal = new bootstrap.Modal(document.getElementById('receiptModal'));
                receiptModal.show();
                
                // Reset Cart on Modal Close
                document.getElementById('receiptModal').addEventListener('hidden.bs.modal', () => {
                    cart = [];
                    customerGivenInput.value = '';
                    // Reset to Cash
                    document.getElementById('payCash').checked = true;
                    updateCartUI();
                    btnCompleteSale.innerHTML = '<i class="fas fa-check-circle me-2"></i> COMPLETE SALE';
                });
            } else {
                alert('Error processing sale: ' + result.message);
                btnCompleteSale.disabled = false;
                btnCompleteSale.innerHTML = '<i class="fas fa-check-circle me-2"></i> COMPLETE SALE';
            }
        } catch (error) {
            console.error('Error:', error);
            alert('An unexpected error occurred.');
            btnCompleteSale.disabled = false;
            btnCompleteSale.innerHTML = '<i class="fas fa-check-circle me-2"></i> COMPLETE SALE';
        }
    });
});
