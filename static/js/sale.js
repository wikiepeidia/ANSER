/**
 * Sale page (POS) — ban-le
 * Phase 1 rewrite: image-aware product cards, quick amount chips,
 * stock badge, quick add button, redesigned cart item layout.
 *
 * Product data shape (from /api/products/search):
 *   { id, name, price, image_url?, stock? }
 * image_url is optional — falls back to placeholder when missing/null.
 */
(function () {
    'use strict';

    // ── Placeholder image (used when product has no image_url) ─────────
    const PLACEHOLDER_IMG = '/static/img/placeholder-product.svg';

    // ── DOM refs ────────────────────────────────────────────────────────
    const $ = (id) => document.getElementById(id);
    let searchInput, searchResults, productSuggestions,
        cartItemsContainer, cartItemsList, emptyCartMsg,
        cartTable, cartTableBody,
        grandTotalEl, customerGivenInput, refundAmountEl,
        btnCompleteSale, btnClearCart, cartItemCount,
        quickAmountFullBtn, quickAmountChips,
        paymentMinibarTrigger, paymentDetails;

    // ── State ───────────────────────────────────────────────────────────
    let cart = [];

    // ── Currency helpers ────────────────────────────────────────────────
    const formatCurrency = (amount) => {
        if (amount == null || isNaN(amount)) return '0 ₫';
        return new Intl.NumberFormat('vi-VN', {
            style: 'currency',
            currency: 'VND',
            maximumFractionDigits: 0,
        }).format(amount);
    };
    const formatCurrencyShort = (amount) => {
        if (amount == null || isNaN(amount)) return '0';
        return new Intl.NumberFormat('vi-VN', {
            maximumFractionDigits: 0,
        }).format(amount);
    };
    const formatQty = (amount) => {
        if (amount == null || isNaN(amount)) return '0 ₫';
        return new Intl.NumberFormat('vi-VN', {
            style: 'currency',
            currency: 'VND',
            maximumFractionDigits: 0,
        }).format(amount);
    };

    // ── Render product card (P0) ────────────────────────────────────────
    function renderProductCard(p) {
        const imgUrl = p.image_url || PLACEHOLDER_IMG;
        const stock = typeof p.stock === 'number' ? p.stock : null;
        let stockBadge = '';
        if (stock !== null && stock >= 0) {
            if (stock === 0) {
                stockBadge = '<span class="sale-card__stock sale-card__stock--out">Hết hàng</span>';
            } else if (stock < 5) {
                stockBadge = `<span class="sale-card__stock sale-card__stock--low">Còn ${stock}</span>`;
            } else {
                stockBadge = `<span class="sale-card__stock">Còn ${stock}</span>`;
            }
        }

        // Escape name for safe HTML attribute
        const safeName = (p.name || '').replace(/"/g, '&quot;').replace(/'/g, '&#39;');
        const sku = p.id || '';
        // Limit SKU to readable format (e.g. PRD00001 → PRD...001 or just show as-is)
        const skuDisplay = sku.length > 12 ? sku.slice(0, 6) + '…' + sku.slice(-3) : sku;

        return `
            <article class="sale-card" data-product-id="${p.id}">
                <div class="sale-card__image">
                    <img src="${imgUrl}" alt="${safeName}" loading="lazy" onerror="this.onerror=null;this.src='${PLACEHOLDER_IMG}';this.classList.add('sale-card__image-fallback');">
                    ${stockBadge}
                    <button type="button" class="sale-card__add" data-add-to-cart aria-label="Thêm vào giỏ">
                        <i class="fa-solid fa-plus"></i>
                    </button>
                </div>
                <div class="sale-card__body">
                    <h6 class="sale-card__name" title="${safeName}">${p.name || 'Sản phẩm'}</h6>
                    <p class="sale-card__sku">${skuDisplay}</p>
                    <div class="sale-card__price">${formatCurrency(p.price)}</div>
                </div>
            </article>
        `;
    }

    // ── Render cart item (Phase 1 redesign) ─────────────────────────────
    function renderCartItem(item) {
        const imgUrl = item.image_url || PLACEHOLDER_IMG;
        const safeName = (item.name || '').replace(/"/g, '&quot;').replace(/'/g, '&#39;');
        return `
            <div class="sale-cart-item" data-id="${item.id}">
                <div class="sale-cart-item__image">
                    <img src="${imgUrl}" alt="${safeName}" onerror="this.onerror=null;this.style.display='none';this.nextElementSibling.style.display='flex';">
                    <div class="sale-cart-item__image-placeholder" style="display:none;">
                        <i class="fa-solid fa-box"></i>
                    </div>
                </div>
                <div class="sale-cart-item__info">
                    <p class="sale-cart-item__name" title="${safeName}">${item.name}</p>
                    <span class="sale-cart-item__price">${formatCurrency(item.price)}</span>
                    <div class="sale-cart-item__qty">
                        <button type="button" onclick="window.updateQty('${item.id}', ${item.qty - 1})" ${item.qty <= 1 ? 'disabled' : ''} aria-label="Giảm">
                            <i class="fa-solid fa-minus"></i>
                        </button>
                        <input type="number" value="${item.qty}" min="1" onchange="window.updateQty('${item.id}', this.value)">
                        <button type="button" onclick="window.updateQty('${item.id}', ${item.qty + 1})" aria-label="Tăng">
                            <i class="fa-solid fa-plus"></i>
                        </button>
                    </div>
                </div>
                <button type="button" class="sale-cart-item__remove" onclick="window.removeFromCart('${item.id}')" aria-label="Xóa">
                    <i class="fa-solid fa-xmark"></i>
                </button>
            </div>
        `;
    }

    // ── Update cart UI (P0/P1) ──────────────────────────────────────────
    function updateCartUI() {
        const totalQty = cart.reduce((acc, item) => acc + item.qty, 0);
        const total = cart.reduce((acc, item) => acc + item.price * item.qty, 0);

        // Empty state toggle
        if (cart.length === 0) {
            if (emptyCartMsg) emptyCartMsg.style.display = 'flex';
            if (cartItemsList) cartItemsList.style.display = 'none';
            if (btnCompleteSale) btnCompleteSale.disabled = true;
        } else {
            if (emptyCartMsg) emptyCartMsg.style.display = 'none';
            if (cartItemsList) {
                cartItemsList.style.display = 'flex';
                cartItemsList.innerHTML = cart.map(renderCartItem).join('');
            }
            if (btnCompleteSale) btnCompleteSale.disabled = false;
        }

        // Cart count badge (mini-bar uses sale-cart__minibar-count--active)
        if (cartItemCount) {
            cartItemCount.textContent = totalQty;
            if (totalQty > 0) {
                cartItemCount.classList.add('sale-cart__count--active', 'sale-cart__minibar-count--active');
            } else {
                cartItemCount.classList.remove('sale-cart__count--active', 'sale-cart__minibar-count--active');
            }
        }

        // Grand total
        if (grandTotalEl) {
            grandTotalEl.textContent = formatCurrency(total);
            grandTotalEl.dataset.value = total;
        }

        // Update "Đủ" chip label
        updateQuickAmountFull(total);

        // Recalc refund
        calculateRefund();
    }

    // ── Quick amount logic (P0) ─────────────────────────────────────────
    function setQuickAmount(amount) {
        if (!customerGivenInput) return;
        customerGivenInput.value = amount;
        customerGivenInput.dispatchEvent(new Event('input', { bubbles: true }));
        // Visual feedback
        customerGivenInput.focus();
    }

    function updateQuickAmountFull(total) {
        if (!quickAmountFullBtn) return;
        if (total > 0) {
            quickAmountFullBtn.disabled = false;
            // Show formatted amount in label, e.g. "Đủ 245K"
            const shortAmount = total >= 1000000
                ? (total / 1000000).toFixed(1).replace('.0', '') + 'M'
                : total >= 1000
                    ? Math.round(total / 1000) + 'K'
                    : formatCurrencyShort(total);
            quickAmountFullBtn.textContent = `Đủ ${shortAmount}`;
        } else {
            quickAmountFullBtn.disabled = true;
            quickAmountFullBtn.textContent = 'Đủ';
        }
    }

    // ── Cart actions (global for inline onclick) ───────────────────────
    window.addToCart = function (id, name, price, stock, imageUrl, sourceEl) {
        // Trigger fly animation (Phase 3)
        if (sourceEl) animateAddToCart(sourceEl);

        const existingItem = cart.find((item) => item.id === id);
        if (existingItem) {
            // Check stock limit if known
            if (typeof stock === 'number' && stock >= 0 && existingItem.qty + 1 > stock) {
                showToast(`Chỉ còn ${stock} sản phẩm trong kho`, 'warning');
                return;
            }
            existingItem.qty += 1;
        } else {
            if (typeof stock === 'number' && stock === 0) {
                showToast('Sản phẩm đã hết hàng', 'error');
                return;
            }
            cart.push({
                id,
                name,
                price: Number(price) || 0,
                qty: 1,
                stock: typeof stock === 'number' ? stock : null,
                image_url: imageUrl || null,
            });
        }
        // Pop cart count badge (Phase 3)
        popCartCount();
        updateCartUI();
    };

    window.removeFromCart = function (id) {
        cart = cart.filter((item) => item.id !== id);
        updateCartUI();
    };

    window.updateQty = function (id, newQty) {
        const item = cart.find((i) => i.id === id);
        if (!item) return;
        const qty = Math.max(0, parseInt(newQty, 10) || 0);
        if (qty === 0) {
            removeFromCart(id);
            return;
        }
        // Stock check
        if (typeof item.stock === 'number' && item.stock >= 0 && qty > item.stock) {
            showToast(`Chỉ còn ${item.stock} sản phẩm trong kho`, 'warning');
            item.qty = item.stock;
        } else {
            item.qty = qty;
        }
        // Bounce animation on qty input (Phase 3)
        bounceQtyInput(id);
        updateCartUI();
    };

    window.clearSearch = function () {
        if (!searchInput) return;
        searchInput.value = '';
        if (searchResults) searchResults.style.display = 'none';
        searchInput.focus();
    };

    // ── Animations (Phase 3) ───────────────────────────────────────────
    function animateAddToCart(sourceEl) {
        // Respect reduced motion
        if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
        if (!sourceEl) return;

        const sourceImg = sourceEl.querySelector('img') || sourceEl;
        const targetEl = document.querySelector('.sale-cart__minibar') ||
                          document.querySelector('.sale-cart__count') ||
                          document.querySelector('.sale-cart');
        if (!sourceImg || !targetEl) return;

        const sourceRect = sourceImg.getBoundingClientRect();
        const targetRect = targetEl.getBoundingClientRect();

        const clone = document.createElement('img');
        clone.src = sourceImg.src;
        clone.alt = '';
        clone.className = 'sale-fly-clone';
        clone.style.left = sourceRect.left + 'px';
        clone.style.top = sourceRect.top + 'px';
        clone.style.width = sourceRect.width + 'px';
        clone.style.height = sourceRect.height + 'px';
        document.body.appendChild(clone);

        // Force reflow so transition applies
        void clone.offsetWidth;

        // Calculate trajectory
        const deltaX = (targetRect.left + targetRect.width / 2) -
                        (sourceRect.left + sourceRect.width / 2);
        const deltaY = (targetRect.top + targetRect.height / 2) -
                        (sourceRect.top + sourceRect.height / 2);

        clone.style.transform = `translate(${deltaX}px, ${deltaY}px) scale(0.15)`;
        clone.style.opacity = '0.2';

        setTimeout(() => {
            if (clone.parentNode) clone.remove();
        }, 650);
    }

    function bounceQtyInput(productId) {
        if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
        // Find the rendered qty input for this product
        const itemEl = document.querySelector(`.sale-cart-item[data-id="${CSS.escape(productId)}"] input`);
        if (!itemEl) return;
        itemEl.classList.remove('bounce');
        // Force reflow
        void itemEl.offsetWidth;
        itemEl.classList.add('bounce');
    }

    function popCartCount() {
        if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
        if (!cartItemCount) return;
        cartItemCount.classList.remove('pop');
        void cartItemCount.offsetWidth;
        cartItemCount.classList.add('pop');
    }

    // Legacy (still used by editPrice if any) — keep harmless stub
    window.updatePrice = function (id, newPrice) {
        const item = cart.find((i) => i.id === id);
        if (item) {
            item.price = parseFloat(newPrice) || 0;
            updateCartUI();
        }
    };

    // ── Toast helper (reuses banleUI.showAlert if present) ────────────
    function showToast(message, type) {
        if (window.banleUI && window.banleUI.showAlert) {
            window.banleUI.showAlert(type || 'info', message);
        } else if (window.showToast) {
            window.showToast(message, type || 'info');
        } else {
            console.log(`[${type || 'info'}] ${message}`);
        }
    }

    // ── Calculate refund ────────────────────────────────────────────────
    function calculateRefund() {
        if (!grandTotalEl || !refundAmountEl) return;
        const total = parseFloat(grandTotalEl.dataset.value || 0);
        const given = parseFloat(customerGivenInput.value || 0);
        const refund = given - total;

        refundAmountEl.textContent = formatCurrency(refund);
        refundAmountEl.classList.remove('sale-cart__refund-value--positive');
        if (refund > 0 && total > 0) {
            refundAmountEl.classList.add('sale-cart__refund-value--positive');
        }

        // Update "Đủ" chip state based on given vs total
        if (quickAmountChips) {
            const chips = quickAmountChips.querySelectorAll('.sale-quick-amount__chip[data-amount]');
            chips.forEach((chip) => {
                const amt = chip.dataset.amount;
                if (amt === 'full') return; // handled separately
                const numAmt = parseInt(amt, 10);
                if (numAmt < total && total > 0) {
                    chip.disabled = false; // usable for partial
                }
            });
        }
    }

    // ── Render suggestions (P0) ─────────────────────────────────────────
    function renderSuggestions(items) {
        if (!productSuggestions) return;
        if (!items || items.length === 0) {
            productSuggestions.innerHTML = `
                <div class="sale-cart__empty" style="grid-column: 1/-1;">
                    <i class="fa-solid fa-box-open sale-cart__empty-icon"></i>
                    <p class="sale-cart__empty-title">Chưa có sản phẩm gợi ý</p>
                    <p class="sale-cart__empty-desc">Thử tìm kiếm sản phẩm khác</p>
                </div>
            `;
            return;
        }
        productSuggestions.innerHTML = items.map(renderProductCard).join('');

        // Event delegation: click on card or quick-add button
        productSuggestions.onclick = (e) => {
            const btn = e.target.closest('[data-add-to-cart]');
            const card = e.target.closest('.sale-card');
            if (!card) return;
            // Find the product data from the rendered card's data attribute
            const id = card.dataset.productId;
            // Look up the product from last fetched data (cached in closure scope)
            const item = (window._lastProducts || []).find((p) => String(p.id) === String(id));
            if (!item) return;
            const sourceEl = btn || card;
            window.addToCart(item.id, item.name, item.price,
                typeof item.stock === 'number' ? item.stock : null,
                item.image_url || null, sourceEl);
        };
    }

    // Cache last fetched products into window._lastProducts (used by event
    // delegation in renderSuggestions). Declared as a function so it's
    // hoisted and callable from init() (which runs after this position).
    // Don't reassign via `fetchProducts = ...` — that would fail in
    // strict mode IIFE because the bare name doesn't exist as a let/var.
    async function fetchProducts(query = '') {
        try {
            const url = query
                ? `/api/products/search?q=${encodeURIComponent(query)}`
                : '/api/products/search?random=true';
            const response = await fetch(url);
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            const data = await response.json();
            window._lastProducts = data;
            if (query) {
                renderSearchResults(data);
            } else {
                renderSuggestions(data);
            }
        } catch (error) {
            console.error('Error fetching products:', error);
        }
    }

    // ── Render search results (dropdown) ────────────────────────────────
    function renderSearchResults(items) {
        if (!searchResults) return;
        if (!items || items.length === 0) {
            searchResults.style.display = 'none';
            return;
        }
        searchResults.innerHTML = items
            .map((p) => {
                const safeName = (p.name || '').replace(/"/g, '&quot;').replace(/'/g, '&#39;');
                const imgUrl = p.image_url || PLACEHOLDER_IMG;
                const stock = typeof p.stock === 'number' ? p.stock : null;
                let stockBadge = '';
                if (stock !== null && stock >= 0) {
                    stockBadge = stock === 0
                        ? '<span style="color: var(--status-error); font-size: 0.75rem;">Hết</span>'
                        : `<span style="color: var(--text-muted); font-size: 0.75rem;">Còn ${stock}</span>`;
                }
                return `
                    <div class="search-result-item" data-search-result-id="${p.id}">
                        <img src="${imgUrl}" alt="" class="search-result-item__img" onerror="this.onerror=null;this.src='${PLACEHOLDER_IMG}'">
                        <div class="search-result-item__info">
                            <div class="search-result-item__name">${p.name || 'Sản phẩm'}</div>
                            <div class="search-result-item__meta">${p.id || ''} ${stockBadge}</div>
                        </div>
                        <div class="search-result-item__price">${formatCurrency(p.price)}</div>
                    </div>
                `;
            })
            .join('');
        searchResults.style.display = 'block';

        // Event delegation for search results
        searchResults.onclick = (e) => {
            const item = e.target.closest('[data-search-result-id]');
            if (!item) return;
            const id = item.dataset.searchResultId;
            const product = (window._lastProducts || []).find((p) => String(p.id) === String(id));
            if (!product) return;
            window.addToCart(product.id, product.name, product.price,
                typeof product.stock === 'number' ? product.stock : null,
                product.image_url || null, item);
            window.clearSearch();
        };
    }

    // ── History logic (Phase 1: simplified) ─────────────────────────────
    let historySearchTimer;
    let currentHistoryData = [];

    window.refreshHistory = async function () {
        const queryInput = document.getElementById('historySearchInput');
        const query = queryInput ? queryInput.value : '';
        const tbody = document.getElementById('historyTableBody');
        if (!tbody) return;
        tbody.innerHTML = '<tr><td colspan="6" class="text-center py-4"><i class="fas fa-spinner fa-spin me-2"></i>Đang tải...</td></tr>';

        try {
            const response = await fetch(`/api/sales/history?limit=20&q=${encodeURIComponent(query)}`);
            if (response.ok) {
                const history = await response.json();
                currentHistoryData = history;
                if (!history || history.length === 0) {
                    tbody.innerHTML = '<tr><td colspan="6" class="text-center py-4 text-muted">Không tìm thấy giao dịch nào.</td></tr>';
                } else {
                    tbody.innerHTML = history
                        .map(
                            (sale) => `
                        <tr>
                            <td><small class="id-cell">#${sale.id}</small></td>
                            <td>${sale.date || ''}</td>
                            <td><span class="badge bg-secondary">${sale.payment_method || ''}</span></td>
                            <td class="text-center"><span class="badge badge-item-count">${sale.item_count || 0}</span></td>
                            <td class="text-end fw-bold">${formatCurrency(sale.amount)}</td>
                            <td class="text-center">
                                <div class="btn-group btn-group-sm">
                                    <button class="btn btn-outline-primary" onclick="window.viewSaleDetails(${sale.id})" title="Xem chi tiết"><i class="fas fa-eye"></i></button>
                                    <button class="btn btn-outline-danger" onclick="window.deleteSale(${sale.id})" title="Xóa"><i class="fas fa-trash"></i></button>
                                </div>
                            </td>
                        </tr>
                    `
                        )
                        .join('');
                }
            } else {
                tbody.innerHTML = `<tr><td colspan="6" class="text-center text-danger py-4">Không tải được lịch sử (${response.status}).</td></tr>`;
            }
        } catch (error) {
            tbody.innerHTML = `<tr><td colspan="6" class="text-center text-danger py-4">Lỗi: ${error.message}</td></tr>`;
        }
    };

    window.deleteSale = async function (saleId) {
        if (!confirm('Bạn có chắc chắn muốn xóa giao dịch này?')) return;
        try {
            const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');
            const response = await fetch(`/api/sales/history/${saleId}`, {
                method: 'DELETE',
                headers: { 'X-CSRFToken': csrfToken },
            });
            const result = await response.json();
            if (result.success) {
                refreshHistory();
            } else {
                alert('Không xóa được: ' + (result.message || ''));
            }
        } catch (error) {
            console.error('Error deleting sale:', error);
            alert('Lỗi: ' + error.message);
        }
    };

    window.viewSaleDetails = function (saleId) {
        const sale = currentHistoryData.find((s) => s.id === saleId);
        if (!sale) return;
        document.getElementById('detailSaleId').textContent = sale.id;
        document.getElementById('detailSaleDate').textContent = sale.date;
        document.getElementById('detailSaleMethod').textContent = sale.payment_method;
        document.getElementById('detailSaleTotal').textContent = formatCurrency(sale.amount);
        const tbody = document.getElementById('detailItemsBody');
        if (sale.items && sale.items.length > 0) {
            tbody.innerHTML = sale.items
                .map((item) => {
                    const price = item.price || 0;
                    const qty = item.qty || item.quantity || 0;
                    const total = price * qty;
                    return `
                    <tr>
                        <td><div class="fw-bold">${item.name || 'N/A'}</div><small class="text-muted">${item.id || ''}</small></td>
                        <td class="text-center align-middle">${qty}</td>
                        <td class="text-end align-middle">${formatCurrency(price)}</td>
                        <td class="text-end align-middle">${formatCurrency(total)}</td>
                    </tr>`;
                })
                .join('');
        } else {
            tbody.innerHTML = '<tr><td colspan="4" class="text-center text-muted">Không có dữ liệu</td></tr>';
        }
        openModal('saleDetailsModal');
    };

    window.showHistory = function () {
        openModal('historyModal');
        const searchInput = document.getElementById('historySearchInput');
        if (searchInput) searchInput.value = '';
        refreshHistory();
    };

    // ── Payment details expand/collapse (Approach B) ────────────────────
    function isPaymentDetailsOpen() {
        return paymentDetails && paymentDetails.classList.contains('is-open');
    }

    function openPaymentDetails() {
        if (!paymentDetails || !paymentMinibarTrigger) return;
        paymentDetails.classList.add('is-open');
        paymentMinibarTrigger.setAttribute('aria-expanded', 'true');
    }

    function closePaymentDetails() {
        if (!paymentDetails || !paymentMinibarTrigger) return;
        paymentDetails.classList.remove('is-open');
        paymentMinibarTrigger.setAttribute('aria-expanded', 'false');
    }

    function togglePaymentDetails() {
        if (isPaymentDetailsOpen()) {
            closePaymentDetails();
        } else {
            openPaymentDetails();
        }
    }

    // ── Empty state suggestion chips (Phase 2) ──────────────────────────
    function bindEmptyStateSuggestions() {
        const emptyEl = $('emptyCartMsg');
        if (!emptyEl) return;
        emptyEl.addEventListener('click', (e) => {
            const chip = e.target.closest('.sale-cart__empty-suggestion[data-suggestion]');
            if (!chip) return;
            const query = chip.dataset.suggestion;
            if (!searchInput) return;
            searchInput.value = query;
            searchInput.focus();
            // Trigger input event so debounce/search kicks in
            searchInput.dispatchEvent(new Event('input', { bubbles: true }));
        });
    }

    // ── Live time + today's stats (Phase 2) ─────────────────────────────
    function updateLiveTime() {
        const el = $('saleStatsTime');
        if (!el) return;
        const now = new Date();
        const hh = String(now.getHours()).padStart(2, '0');
        const mm = String(now.getMinutes()).padStart(2, '0');
        el.textContent = `${hh}:${mm}`;
    }

    async function fetchTodayStats() {
        const countEl = $('saleStatsCount');
        const amountEl = $('saleStatsAmount');
        if (!countEl || !amountEl) return;
        try {
            const response = await fetch('/api/dashboard/stats?days=1', { credentials: 'same-origin' });
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            const data = await response.json();
            // Best-effort field mapping (depends on backend shape)
            const count = data.today_orders ?? data.sales_count ?? data.count ?? 0;
            const amount = data.today_revenue ?? data.revenue ?? data.total_amount ?? 0;
            countEl.textContent = count;
            amountEl.textContent = formatCurrency(Number(amount) || 0);
        } catch (err) {
            // Silent fail — keep defaults ("0 đơn / 0 ₫")
            console.warn('fetchTodayStats failed:', err);
        }
    }

    // ── Init ────────────────────────────────────────────────────────────
    function init() {
        // Resolve DOM refs
        searchInput = $('productSearch');
        searchResults = $('searchResults');
        productSuggestions = $('productSuggestions');
        cartItemsContainer = $('cartItemsContainer');
        cartItemsList = $('cartItemsList');
        emptyCartMsg = $('emptyCartMsg');
        cartTable = $('cartTable');
        cartTableBody = $('cartTableBody');
        grandTotalEl = $('grandTotal');
        customerGivenInput = $('customerGiven');
        refundAmountEl = $('refundAmount');
        btnCompleteSale = $('btnCompleteSale');
        btnClearCart = $('btnClearCart');
        cartItemCount = $('cartItemCount');
        quickAmountFullBtn = $('quickAmountFull');
        quickAmountChips = $('quickAmountChips');
        paymentMinibarTrigger = $('paymentMinibarTrigger');
        paymentDetails = $('paymentDetails');

        // Initial fetch
        fetchProducts();
        bindEmptyStateSuggestions();
        updateLiveTime();
        fetchTodayStats();

        // Live clock every 30s
        setInterval(updateLiveTime, 30000);

        // Search debounce
        let debounceTimer;
        if (searchInput) {
            searchInput.addEventListener('input', (e) => {
                const query = e.target.value.trim();
                clearTimeout(debounceTimer);
                if (query.length > 1) {
                    debounceTimer = setTimeout(() => fetchProducts(query), 300);
                } else {
                    searchResults.style.display = 'none';
                }
            });
            searchInput.addEventListener('focus', () => {
                if (!searchInput.value) fetchProducts();
            });
        }

        // Click outside to close search
        document.addEventListener('click', (e) => {
            if (searchInput && searchResults &&
                !searchInput.contains(e.target) && !searchResults.contains(e.target)) {
                searchResults.style.display = 'none';
            }
        });

        // Payment: customer given
        if (customerGivenInput) {
            customerGivenInput.addEventListener('input', calculateRefund);
            customerGivenInput.addEventListener('focus', () => {
                // Auto-open details when user focuses the input
                if (!isPaymentDetailsOpen()) openPaymentDetails();
            });
        }

        // Quick amount chips (event delegation)
        if (quickAmountChips) {
            quickAmountChips.addEventListener('click', (e) => {
                const chip = e.target.closest('.sale-quick-amount__chip');
                if (!chip || chip.disabled) return;
                const amt = chip.dataset.amount;
                if (amt === 'full') {
                    const total = parseFloat(grandTotalEl.dataset.value || 0);
                    setQuickAmount(total);
                } else {
                    setQuickAmount(parseInt(amt, 10));
                }
            });
        }

        // Clear cart
        if (btnClearCart) {
            btnClearCart.addEventListener('click', () => {
                if (confirm('Bạn có chắc chắn muốn xóa giỏ hàng?')) {
                    cart = [];
                    if (customerGivenInput) customerGivenInput.value = '';
                    updateCartUI();
                }
            });
        }

        // Complete sale
        if (btnCompleteSale) {
            btnCompleteSale.addEventListener('click', completeSale);
        }

        // Payment mini-bar trigger (toggle details)
        if (paymentMinibarTrigger) {
            paymentMinibarTrigger.addEventListener('click', (e) => {
                // Don't toggle if user clicked a focusable element inside (shouldn't be, but safe)
                togglePaymentDetails();
            });
        }

        // Click outside to close payment details
        document.addEventListener('click', (e) => {
            if (!isPaymentDetailsOpen()) return;
            const cartEl = document.querySelector('.sale-container__cart');
            if (cartEl && !cartEl.contains(e.target)) {
                closePaymentDetails();
            }
        });

        // ESC to close payment details
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && isPaymentDetailsOpen()) {
                closePaymentDetails();
            }
        });

        // History search debounce
        const historySearchInput = $('historySearchInput');
        if (historySearchInput) {
            historySearchInput.addEventListener('input', () => {
                clearTimeout(historySearchTimer);
                historySearchTimer = setTimeout(refreshHistory, 500);
            });
        }

        // Initial cart UI
        updateCartUI();
    }

    // ── Complete sale (extracted for clarity) ──────────────────────────
    async function completeSale() {
        const total = parseFloat(grandTotalEl.dataset.value || 0);
        let given = parseFloat(customerGivenInput.value || 0);
        const paymentMethod = document.querySelector('input[name="paymentMethod"]:checked').value;

        if (total === 0) return;

        // Card/Transfer auto-fill exact amount if given is 0
        if ((paymentMethod === 'Card' || paymentMethod === 'Transfer') && given === 0) {
            given = total;
            customerGivenInput.value = total;
        }

        if (paymentMethod === 'Cash' && given < total) {
            showToast('Số tiền khách đưa không đủ', 'warning');
            return;
        }

        const refund = given - total;
        const saleData = {
            items: cart,
            total_amount: total,
            amount_given: given,
            change_amount: refund,
            payment_method: paymentMethod,
        };
        const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');

        try {
            btnCompleteSale.disabled = true;
            const originalLabel = btnCompleteSale.innerHTML;
            btnCompleteSale.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i> Đang xử lý...';

            const response = await fetch('/api/sales/create', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
                body: JSON.stringify(saleData),
            });
            const result = await response.json();

            if (result.success) {
                openModal('receiptModal');
                closePaymentDetails();
                setTimeout(() => {
                    cart = [];
                    customerGivenInput.value = '';
                    const cashRadio = document.getElementById('payCash');
                    if (cashRadio) cashRadio.checked = true;
                    updateCartUI();
                    btnCompleteSale.innerHTML = originalLabel;
                }, 3000);
            } else {
                showToast('Lỗi: ' + (result.message || 'Không xử lý được giao dịch'), 'error');
                btnCompleteSale.disabled = false;
                btnCompleteSale.innerHTML = originalLabel;
            }
        } catch (error) {
            console.error('Error:', error);
            showToast('Lỗi: ' + error.message, 'error');
            btnCompleteSale.disabled = false;
            btnCompleteSale.innerHTML = '<i class="fas fa-check-circle me-2"></i> HOÀN TẤT BÁN HÀNG';
        }
    }

    // ── Boot ────────────────────────────────────────────────────────────
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
