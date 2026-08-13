/**
 * main.js — ANSER Dashboard
 * Handles: Theme toggle, Sidebar toggle (mobile), Modal events, Toast,
 *          Header search, Notification dropdown, Last-page persistence
 */

document.addEventListener("DOMContentLoaded", () => {
  // ========================================
  // 1. THEME TOGGLE (Light / Dark)
  // ========================================
  const themeToggleBtn = document.getElementById("themeToggle");
  const themeIcon = document.getElementById("themeIcon");
  const html = document.documentElement;

  // Load saved theme from localStorage
  const savedTheme = localStorage.getItem("anser-theme") || "light";
  html.setAttribute("data-theme", savedTheme);
  updateThemeIcon(savedTheme);

  themeToggleBtn.addEventListener("click", () => {
    const current = html.getAttribute("data-theme");
    const next = current === "light" ? "dark" : "light";
    html.setAttribute("data-theme", next);
    localStorage.setItem("anser-theme", next);
    updateThemeIcon(next);
  });

  function updateThemeIcon(theme) {
    if (theme === "dark") {
      themeIcon.className = "fa-regular fa-sun";
    } else {
      themeIcon.className = "fa-solid fa-moon";
    }
  }

  // ========================================
  // 2. SIDEBAR TOGGLE (Mobile)
  // ========================================
  const menuToggleBtn = document.getElementById("menuToggle");
  const mobileToggleBtn = document.getElementById("mobileSidebarToggle");
  const sidebar = document.getElementById("sidebar");

  // Use existing overlay from HTML, or create fallback
  let overlay = document.getElementById("sidebarOverlay");
  if (!overlay) {
    overlay = document.createElement("div");
    overlay.className = "sidebar-overlay";
    overlay.id = "sidebarOverlay";
    document.querySelector(".app").prepend(overlay);
  }

  function openSidebar() {
    sidebar.classList.add("active");
    overlay.classList.add("active");
    document.body.style.overflow = "hidden";
  }

  function closeSidebar() {
    sidebar.classList.remove("active");
    overlay.classList.remove("active");
    document.body.style.overflow = "";
  }

  // Desktop header toggle button
  if (menuToggleBtn) {
    menuToggleBtn.addEventListener("click", () => {
      if (sidebar.classList.contains("active")) {
        closeSidebar();
      } else {
        openSidebar();
      }
    });
  }

  // Mobile topbar hamburger button
  if (mobileToggleBtn) {
    mobileToggleBtn.addEventListener("click", () => {
      if (sidebar.classList.contains("active")) {
        closeSidebar();
      } else {
        openSidebar();
      }
    });
  }

  // Click overlay to close
  overlay.addEventListener("click", closeSidebar);

  // Auto-close sidebar when resizing to desktop
  window.addEventListener("resize", () => {
    if (window.innerWidth > 768) {
      closeSidebar();
    }
  });

  // ========================================
  // 2b. SIDEBAR COLLAPSE (Desktop)
  // ========================================
  const sidebarToggle = document.getElementById("sidebarToggle");
  const mainWrapper = document.querySelector(".main-wrapper");

  // Load saved collapsed state
  const isCollapsed = localStorage.getItem("sidebar-collapsed") === "true";
  if (isCollapsed) {
    sidebar.classList.add("collapsed");
    mainWrapper.classList.add("sidebar-collapsed");
    document.querySelector(".app").style.setProperty("--sidebar-current-width", "72px");
  }

  if (sidebarToggle) {
    sidebarToggle.addEventListener("click", () => {
      // Only toggle collapsed state on desktop (>=1024px)
      // On tablet/mobile (<1024px), use drawer behavior (open class)
      if (window.innerWidth >= 1024) {
        sidebar.classList.toggle("collapsed");
        mainWrapper.classList.toggle("sidebar-collapsed");
        const collapsed = sidebar.classList.contains("collapsed");
        localStorage.setItem("sidebar-collapsed", collapsed);
        // Update CSS variable for smooth transition
        document.querySelector(".app").style.setProperty(
          "--sidebar-current-width",
          collapsed ? "72px" : "240px"
        );
      } else {
        // Tablet/mobile: use drawer behavior
        if (sidebar.classList.contains("active")) {
          closeSidebar();
        } else {
          openSidebar();
        }
      }
    });
  }

  // Also handle collapsed state on main-wrapper
  if (mainWrapper && isCollapsed) {
    mainWrapper.classList.add("sidebar-collapsed");
  }

  // Auto-close sidebar on mobile when clicking items WITHOUT submenu
  // Items WITH submenu (has-sub) will only close after selecting from submenu
  document.querySelectorAll(".sidebar__item:not(.sidebar__item--has-sub)").forEach((el) => {
    el.addEventListener("click", () => {
      if (window.innerWidth <= 768) {
        closeSidebar();
      }
    });
  });

  // Auto-close sidebar on mobile when submenu item is clicked
  document.querySelectorAll(".sidebar__submenu-item").forEach((el) => {
    el.addEventListener("click", () => {
      if (window.innerWidth <= 768) {
        closeSidebar();
      }
    });
  });

  // ========================================
  // 2c. SIDEBAR COLLAPSED - Click icon to expand (desktop)
  // ========================================
  document.querySelectorAll(".sidebar__item").forEach((el) => {
    el.addEventListener("click", () => {
      // If sidebar is collapsed on desktop, expand it
      if (sidebar.classList.contains("collapsed") && window.innerWidth >= 1024) {
        sidebar.classList.remove("collapsed");
        if (mainWrapper) {
          mainWrapper.classList.remove("sidebar-collapsed");
        }
        localStorage.setItem("sidebar-collapsed", "false");
        document.querySelector(".app").style.setProperty("--sidebar-current-width", "240px");
      }
    });
  });

  // ========================================
  // 2d. SIDEBAR USER CARD (mobile)
  // ========================================
  const sidebarUserCard = document.getElementById("sidebarUserCard");
  const sidebarUserMenu = document.getElementById("sidebarUserMenu");

  if (sidebarUserCard && sidebarUserMenu) {
    sidebarUserCard.addEventListener("click", (e) => {
      e.preventDefault();
      e.stopPropagation();
      sidebarUserCard.classList.toggle("open");
      sidebarUserMenu.classList.toggle("open");
    });

    // Handle menu item clicks
    sidebarUserMenu.querySelectorAll(".sidebar-user-menu__item").forEach((el) => {
      el.addEventListener("click", () => {
        if (window.innerWidth <= 768) {
          closeSidebar();
        }
      });
    });
  }

  // ========================================
  // 3. MODAL EVENTS (shared across pages)
  // ========================================
  // Product Modal
  const productModal = document.getElementById("productModal");
  const modalClose = document.getElementById("modalClose");
  const modalOverlay = document.getElementById("modalOverlay");
  const btnCancelModal = document.getElementById("btnCancelModal");
  const productForm = document.getElementById("productForm");

  if (productModal && modalClose) {
    modalClose.addEventListener("click", () => productModal.classList.remove("open"));
  }
  if (productModal && modalOverlay) {
    modalOverlay.addEventListener("click", () => productModal.classList.remove("open"));
  }
  if (btnCancelModal) {
    btnCancelModal.addEventListener("click", () => productModal.classList.remove("open"));
  }
  if (productForm) {
    productForm.addEventListener("submit", (e) => {
      e.preventDefault();
      if (window.Router && typeof window.Router.saveProduct === "function") {
        // Router.saveProduct closes the modal itself once the API call
        // succeeds (and keeps it open on error, so the user can fix and retry).
        window.Router.saveProduct(e);
      } else {
        productModal.classList.remove("open");
        showToast("Đã lưu sản phẩm!");
      }
    });
  }

  // Production Order Modal
  const orderModal = document.getElementById("orderModal");
  const orderModalClose = document.getElementById("orderModalClose");
  const orderModalOverlay = document.getElementById("orderModalOverlay");
  const btnCancelOrderModal = document.getElementById("btnCancelOrderModal");
  const orderForm = document.getElementById("orderForm");

  if (orderModal && orderModalClose) {
    orderModalClose.addEventListener("click", () => orderModal.classList.remove("open"));
  }
  if (orderModal && orderModalOverlay) {
    orderModalOverlay.addEventListener("click", () => orderModal.classList.remove("open"));
  }
  if (btnCancelOrderModal) {
    btnCancelOrderModal.addEventListener("click", () => orderModal.classList.remove("open"));
  }
  if (orderForm) {
    orderForm.addEventListener("submit", (e) => {
      e.preventDefault();
      if (window.Router && typeof window.Router.saveOrderForm === "function") {
        window.Router.saveOrderForm(e);
      } else {
        orderModal.classList.remove("open");
        showToast("Đã lưu đơn hàng!");
      }
    });
  }

  // Material Batch Modal
  const batchModal = document.getElementById("batchModal");
  const batchModalClose = document.getElementById("batchModalClose");
  const batchModalOverlay = document.getElementById("batchModalOverlay");
  const btnCancelBatchModal = document.getElementById("btnCancelBatchModal");
  const batchForm = document.getElementById("batchForm");

  if (batchModal && batchModalClose) {
    batchModalClose.addEventListener("click", () => batchModal.classList.remove("open"));
  }
  if (batchModal && batchModalOverlay) {
    batchModalOverlay.addEventListener("click", () => batchModal.classList.remove("open"));
  }
  if (btnCancelBatchModal) {
    btnCancelBatchModal.addEventListener("click", () => batchModal.classList.remove("open"));
  }
  if (batchForm) {
    batchForm.addEventListener("submit", (e) => {
      e.preventDefault();
      if (window.Router && typeof window.Router.saveBatchForm === "function") {
        window.Router.saveBatchForm(e);
      } else {
        batchModal.classList.remove("open");
        showToast("Đã lưu lô nguyên liệu!");
      }
    });
  }

  // QC Result Modal
  const qcModal = document.getElementById("qcModal");
  const qcModalClose = document.getElementById("qcModalClose");
  const qcModalOverlay = document.getElementById("qcModalOverlay");
  const btnCancelQCModal = document.getElementById("btnCancelQCModal");
  const qcForm = document.getElementById("qcForm");

  if (qcModal && qcModalClose) {
    qcModalClose.addEventListener("click", () => qcModal.classList.remove("open"));
  }
  if (qcModal && qcModalOverlay) {
    qcModalOverlay.addEventListener("click", () => qcModal.classList.remove("open"));
  }
  if (btnCancelQCModal) {
    btnCancelQCModal.addEventListener("click", () => qcModal.classList.remove("open"));
  }
  if (qcForm) {
    qcForm.addEventListener("submit", (e) => {
      e.preventDefault();
      if (window.Router && typeof window.Router.saveQCForm === "function") {
        window.Router.saveQCForm(e);
      } else {
        qcModal.classList.remove("open");
        showToast("Đã lưu kết quả kiểm định!");
      }
    });
  }

  // Batch Process Event Modal
  const batchEventModal = document.getElementById("batchEventModal");
  const batchEventModalClose = document.getElementById("batchEventModalClose");
  const batchEventModalOverlay = document.getElementById("batchEventModalOverlay");
  const btnCancelBatchEventModal = document.getElementById("btnCancelBatchEventModal");
  const batchEventForm = document.getElementById("batchEventForm");

  if (batchEventModal && batchEventModalClose) {
    batchEventModalClose.addEventListener("click", () => batchEventModal.classList.remove("open"));
  }
  if (batchEventModal && batchEventModalOverlay) {
    batchEventModalOverlay.addEventListener("click", () => batchEventModal.classList.remove("open"));
  }
  if (btnCancelBatchEventModal) {
    btnCancelBatchEventModal.addEventListener("click", () => batchEventModal.classList.remove("open"));
  }
  if (batchEventForm) {
    batchEventForm.addEventListener("submit", (e) => {
      e.preventDefault();
      if (window.Router && typeof window.Router.saveBatchEventForm === "function") {
        window.Router.saveBatchEventForm(e);
      } else {
        batchEventModal.classList.remove("open");
        showToast("Đã ghi sự kiện!");
      }
    });
  }

  // Warehouse Transfer Modal
  const transferModal = document.getElementById("transferModal");
  const transferModalClose = document.getElementById("transferModalClose");
  const transferModalOverlay = document.getElementById("transferModalOverlay");
  const btnCancelTransferModal = document.getElementById("btnCancelTransferModal");
  const transferForm = document.getElementById("transferForm");

  if (transferModal && transferModalClose) {
    transferModalClose.addEventListener("click", () => transferModal.classList.remove("open"));
  }
  if (transferModal && transferModalOverlay) {
    transferModalOverlay.addEventListener("click", () => transferModal.classList.remove("open"));
  }
  if (btnCancelTransferModal) {
    btnCancelTransferModal.addEventListener("click", () => transferModal.classList.remove("open"));
  }
  if (transferForm) {
    transferForm.addEventListener("submit", (e) => {
      e.preventDefault();
      if (window.Router && typeof window.Router.saveTransferForm === "function") {
        window.Router.saveTransferForm(e);
      } else {
        transferModal.classList.remove("open");
        showToast("Đã chuyển kho!");
      }
    });
  }

  // Transfer modal: cascading selects (kho -> vị trí) + tồn kho theo vị trí info
  function populateLocationSelect(selectEl, warehouseId, placeholder) {
    selectEl.innerHTML = "";
    if (!warehouseId) {
      selectEl.innerHTML = `<option value="">${placeholder}</option>`;
      return;
    }
    const locs = window.Store ? Store.getLocationsForWarehouse(warehouseId) : [];
    selectEl.innerHTML = `<option value="">Chọn vị trí</option>` +
      locs.map((l) => `<option value="${l.id}">${l.code} — ${l.name}</option>`).join("");
  }

  function updateTransferStockInfo() {
    const infoEl = document.getElementById("transferStockInfo");
    if (!infoEl || !window.Store) return;
    const code = document.getElementById("transferProduct").value;
    if (!code) { infoEl.textContent = ""; return; }
    const rows = Store.warehouseStock.filter((s) => s.productCode === code);
    if (!rows.length) { infoEl.textContent = "Sản phẩm này chưa có tồn kho ở kho nào."; return; }
    infoEl.textContent = "Tồn hiện tại: " + rows.map((r) => {
      const wh = Store.getWarehouseById(r.warehouseId);
      const loc = Store.getLocationById(r.locationId);
      return `${wh?.code}/${loc?.code}: ${r.quantity}`;
    }).join(" · ");
  }

  const transferFromWarehouse = document.getElementById("transferFromWarehouse");
  const transferToWarehouse = document.getElementById("transferToWarehouse");
  const transferProductSel = document.getElementById("transferProduct");
  if (transferFromWarehouse) {
    transferFromWarehouse.addEventListener("change", () => {
      populateLocationSelect(document.getElementById("transferFromLocation"), transferFromWarehouse.value, "Chọn kho nguồn trước");
    });
  }
  if (transferToWarehouse) {
    transferToWarehouse.addEventListener("change", () => {
      populateLocationSelect(document.getElementById("transferToLocation"), transferToWarehouse.value, "Chọn kho đích trước");
    });
  }
  if (transferProductSel) {
    transferProductSel.addEventListener("change", updateTransferStockInfo);
  }

  // Stock Count (Kiểm kê) Modal
  const stockCountModal = document.getElementById("stockCountModal");
  const stockCountModalClose = document.getElementById("stockCountModalClose");
  const stockCountModalOverlay = document.getElementById("stockCountModalOverlay");
  const btnCancelStockCountModal = document.getElementById("btnCancelStockCountModal");
  const stockCountForm = document.getElementById("stockCountForm");

  if (stockCountModal && stockCountModalClose) {
    stockCountModalClose.addEventListener("click", () => stockCountModal.classList.remove("open"));
  }
  if (stockCountModal && stockCountModalOverlay) {
    stockCountModalOverlay.addEventListener("click", () => stockCountModal.classList.remove("open"));
  }
  if (btnCancelStockCountModal) {
    btnCancelStockCountModal.addEventListener("click", () => stockCountModal.classList.remove("open"));
  }
  if (stockCountForm) {
    stockCountForm.addEventListener("submit", (e) => {
      e.preventDefault();
      if (window.Router && typeof window.Router.saveStockCountForm === "function") {
        window.Router.saveStockCountForm(e);
      } else {
        stockCountModal.classList.remove("open");
        showToast("Đã lưu kết quả kiểm kê!");
      }
    });
  }

  function updateCountSystemQty() {
    const warehouseId = document.getElementById("countWarehouse").value;
    const locationId = document.getElementById("countLocation").value;
    const code = document.getElementById("countProduct").value;
    const sysEl = document.getElementById("countSystemQty");
    if (!warehouseId || !locationId || !code || !window.Store) {
      sysEl.textContent = "—";
      document.getElementById("countDiff").textContent = "—";
      return;
    }
    const row = Store.warehouseStock.find((s) =>
      s.warehouseId === Number(warehouseId) && s.locationId === Number(locationId) && s.productCode === code);
    const sysQty = row ? row.quantity : 0;
    sysEl.textContent = Helpers.formatNumber(sysQty);
    sysEl.dataset.systemQty = sysQty;
    updateCountDiff();
  }

  function updateCountDiff() {
    const sysEl = document.getElementById("countSystemQty");
    const actualEl = document.getElementById("countActualQty");
    const diffEl = document.getElementById("countDiff");
    const sysQty = Number(sysEl.dataset.systemQty || 0);
    const actual = parseFloat(actualEl.value);
    if (isNaN(actual)) { diffEl.textContent = "—"; diffEl.style.color = ""; return; }
    const diff = actual - sysQty;
    diffEl.textContent = (diff > 0 ? "+" : "") + Helpers.formatNumber(diff);
    diffEl.style.color = diff === 0 ? "var(--stat-green-icon)" : diff > 0 ? "var(--stat-blue-icon)" : "var(--stat-red-icon)";
  }

  const countWarehouse = document.getElementById("countWarehouse");
  const countLocation = document.getElementById("countLocation");
  const countProduct = document.getElementById("countProduct");
  const countActualQty = document.getElementById("countActualQty");
  if (countWarehouse) {
    countWarehouse.addEventListener("change", () => {
      populateLocationSelect(countLocation, countWarehouse.value, "Chọn kho trước");
      updateCountSystemQty();
    });
  }
  if (countLocation) countLocation.addEventListener("change", updateCountSystemQty);
  if (countProduct) countProduct.addEventListener("change", updateCountSystemQty);
  if (countActualQty) countActualQty.addEventListener("input", updateCountDiff);

  // Supplier Modal
  const supplierModal = document.getElementById("supplierModal");
  const supplierModalClose = document.getElementById("supplierModalClose");
  const supplierModalOverlay = document.getElementById("supplierModalOverlay");
  const btnCancelSupplierModal = document.getElementById("btnCancelSupplierModal");
  const supplierForm = document.getElementById("supplierForm");

  if (supplierModal && supplierModalClose) {
    supplierModalClose.addEventListener("click", () => supplierModal.classList.remove("open"));
  }
  if (supplierModal && supplierModalOverlay) {
    supplierModalOverlay.addEventListener("click", () => supplierModal.classList.remove("open"));
  }
  if (btnCancelSupplierModal) {
    btnCancelSupplierModal.addEventListener("click", () => supplierModal.classList.remove("open"));
  }
  if (supplierForm) {
    supplierForm.addEventListener("submit", (e) => {
      e.preventDefault();
      if (window.Router && typeof window.Router.saveSupplierForm === "function") {
        window.Router.saveSupplierForm(e);
      } else {
        supplierModal.classList.remove("open");
        showToast("Đã lưu nhà cung cấp!");
      }
    });
  }

  // Delete Modal — uses Router to actually delete
  const deleteModal = document.getElementById("deleteModal");
  const deleteClose = document.getElementById("deleteClose");
  const deleteOverlay = document.getElementById("deleteOverlay");
  const btnCancelDelete = document.getElementById("btnCancelDelete");
  const btnConfirmDelete = document.getElementById("btnConfirmDelete");

  if (deleteModal && deleteClose) {
    deleteClose.addEventListener("click", () => deleteModal.classList.remove("open"));
  }
  if (deleteModal && deleteOverlay) {
    deleteOverlay.addEventListener("click", () => deleteModal.classList.remove("open"));
  }
  if (btnCancelDelete) {
    btnCancelDelete.addEventListener("click", () => deleteModal.classList.remove("open"));
  }
  if (btnConfirmDelete) {
    btnConfirmDelete.addEventListener("click", () => {
      deleteModal.classList.remove("open");
      if (window.Router && typeof window.Router.confirmDelete === "function") {
        window.Router.confirmDelete();
      } else {
        showToast("Đã xoá sản phẩm!");
      }
    });
  }

  // ========================================
  // 4. CLOSE MODAL ON ESC KEY
  // ========================================
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      productModal?.classList.remove("open");
      orderModal?.classList.remove("open");
      batchModal?.classList.remove("open");
      qcModal?.classList.remove("open");
      batchEventModal?.classList.remove("open");
      transferModal?.classList.remove("open");
      stockCountModal?.classList.remove("open");
      supplierModal?.classList.remove("open");
      deleteModal?.classList.remove("open");
      const notiPanel = document.getElementById("notiPanel");
      if (notiPanel) notiPanel.classList.remove("open");
      const userPanel = document.getElementById("userPanel");
      if (userPanel) userPanel.classList.remove("open");
    }
  });

  // ========================================
  // 5. HEADER SEARCH (live route on Enter)
  // ========================================
  const headerSearch = document.getElementById("headerSearch");
  if (headerSearch) {
    headerSearch.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        const q = headerSearch.value.trim().toLowerCase();
        if (!q) return;
        // "Trợ lý AI" is a floating widget, not a page — open it instead of routing
        if (/(trợ lý|chat|ai\b)/.test(q)) {
          window.ChatWidget?.open();
          headerSearch.value = "";
          headerSearch.blur();
          return;
        }
        // Map common keywords to pages
        const route = mapQueryToRoute(q);
        if (route && window.Router) {
          window.Router.navigateTo(route);
          showToast(`Đã tìm: "${q}"`);
        } else {
          showToast(`Không tìm thấy: "${q}"`);
        }
        headerSearch.value = "";
        headerSearch.blur();
      }
    });
  }

  function mapQueryToRoute(q) {
    if (/(báo cáo|doanh thu|lợi nhuận|tồn kho)/.test(q)) return "reports";
    if (/(đơn hàng sản xuất|đơn sản xuất|production)/.test(q)) return "production-orders";
    if (/(nhà cung cấp|ncc)/.test(q)) return "suppliers";
    if (/(quản lý kho|chuyển kho|kiểm kê|vị trí kho)/.test(q)) return "warehouses";
    if (/(nhật ký quy trình|quy trình sản xuất)/.test(q)) return "batch-logs";
    if (/(kiểm định|qc)/.test(q)) return "qc";
    if (/(lô nguyên liệu|truy xuất)/.test(q)) return "material-batches";
    if (/(bom|định mức|nguyên vật liệu|nvl)/.test(q)) return "bom";
    if (/(sản phẩm|sp|hàng)/.test(q)) return "products";
    if (/(nhập)/.test(q)) return "import";
    if (/(xuất)/.test(q)) return "export";
    if (/(tự động|quy tắc|rule|automation)/.test(q)) return "automation-rules";
    if (/(log|lịch sử)/.test(q)) return "automation-logs";
    if (/(cài đặt|setting)/.test(q)) return "settings";
    if (/(trang chủ|home)/.test(q)) return "home";
    return null;
  }

  // ========================================
  // 6. NOTIFICATION DROPDOWN
  // ========================================
  const notiBtn = document.getElementById("notificationBtn");
  const notiPanel = document.getElementById("notiPanel");
  if (notiBtn && notiPanel) {
    notiBtn.addEventListener("click", (e) => {
      e.stopImmediatePropagation();
      notiPanel.classList.toggle("open");
    });
    document.addEventListener("click", (e) => {
      if (!notiPanel.contains(e.target) && e.target !== notiBtn && !notiBtn.contains(e.target)) {
        notiPanel.classList.remove("open");
      }
    });
    // Mark all as read
    notiPanel.querySelector("[data-action='mark-read']")?.addEventListener("click", () => {
      notiPanel.querySelectorAll(".noti-panel__item--unread").forEach((el) => {
        el.classList.remove("noti-panel__item--unread");
      });
      const badge = document.querySelector(".header__badge");
      if (badge) badge.style.display = "none";
      showToast("Đã đánh dấu tất cả đã đọc");
    });
  }

  // ========================================
  // 7. USER PANEL (avatar dropdown)
  // ========================================
  const userAvatar = document.getElementById("userAvatar");
  const userPanel = document.getElementById("userPanel");
  if (userAvatar && userPanel) {
    userAvatar.addEventListener("click", (e) => {
      e.stopImmediatePropagation();
      userPanel.classList.toggle("open");
    });
    document.addEventListener("click", (e) => {
      if (!userPanel.contains(e.target) && e.target !== userAvatar && !userAvatar.contains(e.target)) {
        userPanel.classList.remove("open");
      }
    });
    // Navigate to page when clicking a user panel item
    userPanel.querySelectorAll("[data-page]").forEach((el) => {
      el.addEventListener("click", (e) => {
        e.preventDefault();
        const page = el.dataset.page;
        userPanel.classList.remove("open");
        if (window.Router) window.Router.navigateTo(page);
        else window.location.hash = "#" + page;
      });
    });
  }
});

// ========================================
// Global toast function (single source of truth)
// ========================================
function showToast(message, type) {
  const toast = document.getElementById("toast");
  const toastMessage = document.getElementById("toastMessage");
  const icon = toast?.querySelector(".toast__icon");
  if (toast && toastMessage) {
    toastMessage.textContent = message;
    if (icon && type) {
      icon.className = "toast__icon";
      if (type === "error") icon.classList.add("fa-solid", "fa-circle-xmark");
      else if (type === "warning") icon.classList.add("fa-solid", "fa-triangle-exclamation");
      else if (type === "info") icon.classList.add("fa-solid", "fa-circle-info");
      else icon.classList.add("fa-solid", "fa-circle-check");
    }
    toast.classList.add("show");
    clearTimeout(window.__toastTimer);
    window.__toastTimer = setTimeout(() => toast.classList.remove("show"), 3000);
  }
}

// expose to window for inline handlers
window.showToast = showToast;
