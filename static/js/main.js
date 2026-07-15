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
  const sidebar = document.getElementById("sidebar");

  // Create overlay for mobile
  const overlay = document.createElement("div");
  overlay.className = "sidebar__overlay";
  document.querySelector(".app").prepend(overlay);

  function openSidebar() {
    sidebar.classList.add("open");
    overlay.classList.add("active");
    document.body.style.overflow = "hidden";
  }

  function closeSidebar() {
    sidebar.classList.remove("open");
    overlay.classList.remove("active");
    document.body.style.overflow = "";
  }

  if (menuToggleBtn) {
    menuToggleBtn.addEventListener("click", () => {
      if (sidebar.classList.contains("open")) {
        closeSidebar();
      } else {
        openSidebar();
      }
    });
  }

  overlay.addEventListener("click", closeSidebar);

  // ========================================
  // 2b. SIDEBAR COLLAPSE (Desktop)
  // ========================================
  const sidebarToggle = document.getElementById("sidebarToggle");
  const mainWrapper = document.querySelector(".main-wrapper");

  // Load saved collapsed state
  const isCollapsed = localStorage.getItem("sidebar-collapsed") === "true";
  if (isCollapsed) {
    sidebar.classList.add("collapsed");
  }

  if (sidebarToggle) {
    sidebarToggle.addEventListener("click", () => {
      sidebar.classList.toggle("collapsed");
      mainWrapper.classList.toggle("sidebar-collapsed");
      const collapsed = sidebar.classList.contains("collapsed");
      localStorage.setItem("sidebar-collapsed", collapsed);
    });
  }

  // Also handle collapsed state on main-wrapper
  if (mainWrapper && isCollapsed) {
    mainWrapper.classList.add("sidebar-collapsed");
  }

  // Auto-close sidebar on mobile when any nav item is clicked
  // (router.js also handles clicks, this just closes the drawer)
  document.querySelectorAll(".sidebar__item, .sidebar__submenu-item").forEach((el) => {
    el.addEventListener("click", () => {
      if (window.innerWidth <= 768 && sidebar.classList.contains("open")) {
        closeSidebar();
      }

      // Expand sidebar when clicking submenu items in collapsed state
      if (sidebar.classList.contains("collapsed")) {
        // Check if this is a submenu parent item (has submenu)
        if (el.classList.contains("sidebar__item--has-sub")) {
          // Expand sidebar
          sidebar.classList.remove("collapsed");
          mainWrapper.classList.remove("sidebar-collapsed");
          // Open the submenu
          const subId = el.dataset.sub;
          if (subId) {
            const submenu = document.getElementById(subId);
            if (submenu) {
              const group = el.closest(".sidebar__group");
              if (group) group.classList.add("open");
            }
          }
        }
      }
    });
  });

  // When submenu item is clicked in collapsed state, collapse sidebar after selection
  document.querySelectorAll(".sidebar__submenu-item").forEach((el) => {
    el.addEventListener("click", () => {
      if (sidebar.classList.contains("collapsed")) {
        // Collapse after a short delay to let navigation happen
        setTimeout(() => {
          sidebar.classList.add("collapsed");
          mainWrapper.classList.add("sidebar-collapsed");
          localStorage.setItem("sidebar-collapsed", "true");
        }, 100);
      }
    });
  });

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
  // 4. RULE MODAL EVENTS
  // ========================================
  const ruleModal = document.getElementById("ruleModal");
  const ruleClose = document.getElementById("ruleClose");
  const ruleOverlay = document.getElementById("ruleOverlay");
  const btnCancelRuleModal = document.getElementById("btnCancelRuleModal");
  const ruleForm = document.getElementById("ruleForm");

  if (ruleModal && ruleClose) {
    ruleClose.addEventListener("click", () => ruleModal.classList.remove("open"));
  }
  if (ruleModal && ruleOverlay) {
    ruleOverlay.addEventListener("click", () => ruleModal.classList.remove("open"));
  }
  if (btnCancelRuleModal) {
    btnCancelRuleModal.addEventListener("click", () => ruleModal.classList.remove("open"));
  }
  if (ruleForm) {
    ruleForm.addEventListener("submit", (e) => {
      e.preventDefault();
      if (window.Router && typeof window.Router.saveRule === "function") {
        window.Router.saveRule();
      } else {
        showToast("Đã lưu quy tắc!");
        ruleModal.classList.remove("open");
      }
    });
  }

  // ========================================
  // 5. CLOSE MODAL ON ESC KEY
  // ========================================
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      productModal?.classList.remove("open");
      deleteModal?.classList.remove("open");
      document.getElementById("ruleModal")?.classList.remove("open");
      const notiPanel = document.getElementById("notiPanel");
      if (notiPanel) notiPanel.classList.remove("open");
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
