/**
 * main.js — ANSER Dashboard
 * Handles: Theme toggle, Sidebar toggle (mobile), Modal events, Toast
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
      productModal.classList.remove("open");
      showToast("Đã lưu sản phẩm!");
    });
  }

  // Delete Modal
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
      showToast("Đã xoá sản phẩm!");
    });
  }

  // ========================================
  // 4. CLOSE MODAL ON ESC KEY
  // ========================================
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      productModal?.classList.remove("open");
      deleteModal?.classList.remove("open");
    }
  });
});

// Global toast function
function showToast(message) {
  const toast = document.getElementById("toast");
  const toastMessage = document.getElementById("toastMessage");
  if (toast && toastMessage) {
    toastMessage.textContent = message;
    toast.classList.add("show");
    setTimeout(() => toast.classList.remove("show"), 3000);
  }
}
