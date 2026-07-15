/**
 * router.js — Thin router: loads HTML page files into base.html's content slot
 *
 * Public API (called from inline onclick handlers in HTML pages):
 *   - Router.navigateTo(page)        — navigate to a page
 *   - Router.printSection(id, title) — print a section
 *   - Router.exportProductsCSV()     — export products list
 *   - Router.exportReportOverviewCSV()
 *   - Router.exportRevenueCSV(data)
 *   - Router.exportProfitCSV(data)
 *   - Router.editProduct(id)
 *   - Router.deleteProduct(id)
 *   - Router.editRule(id)
 */

const Router = {
  currentPage: "home",
  pageCache: new Map(), // page HTML cache

  // ============ INIT ============
  async init() {
    // Load stores — products come from the real ANSER API (async);
    // rules/logs are sample data kept in localStorage.
    await Store.loadProducts();
    Store.loadRules();
    Store.loadLogs();

    // Bind nav events
    this.bindNavEvents();

    // Restore last page or load from hash
    const hash = window.location.hash.replace("#", "") || Helpers.load("lastPage", "home");
    this.loadPage(hash);

    // Listen for hash changes (back/forward, anchor links)
    window.addEventListener("hashchange", () => {
      const page = window.location.hash.replace("#", "") || "home";
      if (page !== this.currentPage) this.loadPage(page);
    });

    // Start auto-log generator
    this.startLogGenerator();
  },

  // ============ NAVIGATION ============
  bindNavEvents() {
    document.querySelectorAll("[data-page]").forEach(el => {
      el.addEventListener("click", (e) => {
        e.preventDefault();
        const page = el.dataset.page;
        if (page === this.currentPage && !el.classList.contains("sidebar__item--has-sub")) return;
        if (el.classList.contains("sidebar__item--has-sub")) {
          // Toggle submenu
          const submenu = document.getElementById(el.dataset.sub);
          if (submenu) {
            const group = el.closest(".sidebar__group");
            if (group) group.classList.toggle("open");
          }
          return;
        }
        this.navigateTo(page);
      });
    });
  },

  navigateTo(page) {
    if (window.location.hash !== "#" + page) {
      window.location.hash = "#" + page;
    } else {
      this.loadPage(page);
    }
  },

  async loadPage(page) {
    // Check cache
    if (this.pageCache.has(page)) {
      this.injectPage(this.pageCache.get(page), page);
      return;
    }
    // Fetch HTML file
    try {
      const resp = await fetch(`/static/pages/${page}.html`);
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const html = await resp.text();
      this.pageCache.set(page, html);
      this.injectPage(html, page);
    } catch (err) {
      console.error(`Failed to load page: ${page}`, err);
      document.getElementById("pageContent").innerHTML = `
        <div class="content__header"><h1 class="content__title">Lỗi tải trang</h1></div>
        <p style="color:var(--stat-red-icon);padding:20px">Không thể tải trang <code>${page}.html</code>: ${err.message}</p>
      `;
    }
  },

  injectPage(html, page) {
    const container = document.getElementById("pageContent");
    if (!container) return;

    // Parse HTML, extract scripts and body
    const parser = new DOMParser();
    const doc = parser.parseFromString(html, "text/html");

    // Take body content (skip the html/head wrapper)
    const bodyContent = doc.body.innerHTML;

    // Inject into container
    container.innerHTML = bodyContent;

    // Animate chart-cards (start invisible, then fade in via .chart-animated)
    container.querySelectorAll(".chart-card").forEach((card, idx) => {
      // Trigger reflow then add class for transition to play
      void card.offsetWidth;
      setTimeout(() => card.classList.add("chart-animated"), 30 + idx * 100);
    });

    // Update active nav state
    this.setActiveNav(page);

    // Update current page
    this.currentPage = page;
    Helpers.save("lastPage", page);

    // Scroll to top
    container.scrollTop = 0;
    window.scrollTo(0, 0);

    // Execute inline scripts
    container.querySelectorAll("script").forEach(oldScript => {
      const newScript = document.createElement("script");
      Array.from(oldScript.attributes).forEach(attr => newScript.setAttribute(attr.name, attr.value));
      newScript.textContent = oldScript.textContent;
      oldScript.parentNode.replaceChild(newScript, oldScript);
    });
  },

  setActiveNav(page) {
    // Sidebar top-level items
    document.querySelectorAll(".sidebar__item[data-page]").forEach(el => {
      el.classList.toggle("active", el.dataset.page === page);
    });
    // Submenu items
    document.querySelectorAll(".sidebar__submenu-item[data-page]").forEach(el => {
      el.classList.toggle("active", el.dataset.page === page);
    });
    // Open parent submenu if needed
    document.querySelectorAll(".sidebar__submenu-item.active").forEach(el => {
      const group = el.closest(".sidebar__group");
      if (group) group.classList.add("open");
    });
  },

  // ============ AUTO LOG GENERATOR (sample data only) ============
  startLogGenerator() {
    const rules = Store.rules.map(r => r.title);
    setInterval(() => {
      if (Math.random() > 0.7 && rules.length) {
        const statuses = ["success", "success", "success", "failed", "skipped"];
        const status = statuses[Math.floor(Math.random() * statuses.length)];
        const rule = rules[Math.floor(Math.random() * rules.length)];
        const messages = {
          success: `Rule kích hoạt thành công, xử lý xong trong ${(Math.random() * 2).toFixed(1)}s`,
          failed: `Lỗi: timeout khi gọi API (status=${Math.floor(Math.random()*500+500)})`,
          skipped: `Rule đang tạm dừng, bỏ qua lịch chạy.`,
        };
        const now = new Date();
        const time = `${String(now.getHours()).padStart(2,"0")}:${String(now.getMinutes()).padStart(2,"0")} · hôm nay`;
        Store.addLog({ status, rule, msg: messages[status], meta: `${rule} · ${(Math.random()*2).toFixed(1)}s`, time });
      }
    }, 30000);
  },

  // ============ COMMON ACTIONS (called from HTML onclick) ============
  printSection(elementId, title) {
    Helpers.printElement(elementId, title);
  },

  exportProductsCSV() {
    const rows = Store.products.map(p => ({
      code: p.code, name: p.name, category: p.category, stock: p.stock,
      sellPrice: p.sellPrice, status: p.statusText,
    }));
    Helpers.exportCSV(`san-pham-${Helpers.formatDate(new Date()).replace(/\//g, "-")}.csv`,
      [
        { key: "code", label: "Mã SP" },
        { key: "name", label: "Tên sản phẩm" },
        { key: "category", label: "Danh mục" },
        { key: "stock", label: "Tồn kho" },
        { key: "sellPrice", label: "Giá bán (₫)" },
        { key: "status", label: "Trạng thái" },
      ],
      rows);
    showToast("Đã xuất danh sách sản phẩm!");
  },

  exportReportOverviewCSV() {
    Helpers.exportCSV(`bao-cao-tong-quan-${Helpers.formatDate(new Date()).replace(/\//g, "-")}.csv`,
      [
        { key: "metric", label: "Chỉ số" },
        { key: "value", label: "Giá trị" },
      ],
      [
        { metric: "Tổng nhập (tháng)", value: "1,279,000,000 ₫ (mẫu)" },
        { metric: "Tổng xuất (tháng)", value: "890,000,000 ₫ (mẫu)" },
        { metric: "Doanh thu ước tính", value: "2,100,000,000 ₫ (mẫu)" },
        { metric: "Tồn kho hiện tại", value: Store.products.reduce((s,p) => s+p.stock, 0) + " sp" },
      ]);
    showToast("Đã xuất báo cáo tổng quan!");
  },

  exportRevenueCSV(customers) {
    if (!customers) {
      // Try to grab from current page
      customers = window.topCustomersData || [];
    }
    Helpers.exportCSV(`doanh-thu-${Helpers.formatDate(new Date()).replace(/\//g, "-")}.csv`,
      [
        { key: "name", label: "Khách hàng" },
        { key: "region", label: "Khu vực" },
        { key: "orders", label: "Số đơn" },
        { key: "amount", label: "Doanh thu (₫)" },
      ],
      customers);
    showToast("Đã xuất báo cáo doanh thu!");
  },

  exportProfitCSV(factories) {
    if (!factories) {
      factories = window.profitFactoriesData || [];
    }
    Helpers.exportCSV(`loi-nhuan-${Helpers.formatDate(new Date()).replace(/\//g, "-")}.csv`,
      [
        { key: "name", label: "Nhà máy" },
        { key: "region", label: "Khu vực" },
        { key: "revenue", label: "Doanh thu" },
        { key: "cost", label: "Chi phí" },
        { key: "profit", label: "Lợi nhuận" },
        { key: "margin", label: "Biên LN (%)" },
      ],
      factories);
    showToast("Đã xuất báo cáo lợi nhuận!");
  },

  // ============ PRODUCT MODAL (wired to real /api/products) ============
  editProduct(id) {
    const modal = document.getElementById("productModal");
    const title = document.getElementById("modalTitle");
    const form = document.getElementById("productForm");
    if (!modal) return;
    if (id) {
      const p = Store.getProductById(id);
      if (p) {
        title.textContent = "Sửa sản phẩm";
        form.elements.productCode.value = p.code;
        form.elements.productCode.readOnly = true;
        form.elements.productName.value = p.name;
        form.elements.productCategory.value = this._catToVal(p.category);
        form.elements.productStock.value = p.stock;
        form.elements.productSellPrice.value = p.sellPrice;
        form.elements.productDesc.value = p.description || "";
        modal.dataset.editId = id;
      }
    } else {
      title.textContent = "Thêm sản phẩm";
      form.reset();
      form.elements.productCode.readOnly = false;
      delete modal.dataset.editId;
    }
    modal.classList.add("open");
  },

  async saveProduct(e) {
    e.preventDefault();
    const modal = document.getElementById("productModal");
    const form = e.target;
    const data = {
      code: form.elements.productCode.value.trim(),
      name: form.elements.productName.value.trim(),
      category: this._valToCat(form.elements.productCategory.value),
      stock: parseInt(form.elements.productStock.value) || 0,
      sellPrice: parseInt(form.elements.productSellPrice.value) || 0,
      description: form.elements.productDesc.value.trim(),
    };
    if (!data.code || !data.name) return;

    try {
      if (modal.dataset.editId) {
        await Store.updateProduct(parseInt(modal.dataset.editId), data);
        showToast("Đã cập nhật sản phẩm!");
      } else {
        await Store.addProduct(data);
        showToast("Đã thêm sản phẩm mới!");
      }
      modal.classList.remove("open");
      this.loadPage("products");
    } catch (err) {
      showToast(err.message || "Lỗi lưu sản phẩm", "error");
    }
  },

  deleteProduct(id) {
    const p = Store.getProductById(id);
    const modal = document.getElementById("deleteModal");
    if (!modal) return;
    document.getElementById("deleteMessage").textContent = p
      ? `Bạn có chắc muốn xoá "${p.name}"?`
      : "Bạn có chắc muốn xoá sản phẩm này?";
    modal.dataset.deleteId = id;
    modal.classList.add("open");
  },

  async confirmDelete() {
    const modal = document.getElementById("deleteModal");
    const id = parseInt(modal?.dataset?.deleteId);
    if (!id) return;
    try {
      await Store.deleteProduct(id);
      showToast("Đã xoá sản phẩm!");
      modal.classList.remove("open");
      this.loadPage(this.currentPage);
    } catch (err) {
      showToast(err.message || "Lỗi xoá sản phẩm", "error");
      modal.classList.remove("open");
    }
  },

  _catToVal(c) {
    return ({ "Điện tử": "electronics", "Thời trang": "fashion", "Gia dụng": "home", "Thực phẩm": "food" })[c] || "electronics";
  },
  _valToCat(v) {
    return ({ electronics: "Điện tử", fashion: "Thời trang", home: "Gia dụng", food: "Thực phẩm" })[v] || "Điện tử";
  },

  // ============ RULE MODAL (sample data only) ============
  editRule(id) {
    const modal = document.getElementById("ruleModal");
    const title = document.getElementById("ruleModalTitle");
    const form = document.getElementById("ruleForm");
    if (!modal) return;
    if (id) {
      const r = Store.rules.find(x => x.id === id);
      if (r) {
        title.textContent = "Sửa quy tắc";
        form.elements.ruleTitle.value = r.title;
        form.elements.ruleDesc.value = r.desc;
        form.elements.ruleIcon.value = r.icon;
        form.elements.ruleColor.value = r.color;
        form.elements.ruleTrigger.value = r.trigger;
        form.elements.ruleAction.value = r.action;
        form.elements.ruleFreq.value = r.freq;
        form.elements.ruleChannel.value = r.channel;
        form.elements.ruleThreshold.value = r.threshold || "";
        form.elements.ruleActive.checked = r.checked;
        modal.dataset.editId = id;
      }
    } else {
      title.textContent = "Tạo quy tắc mới";
      form.reset();
      form.elements.ruleActive.checked = true;
      delete modal.dataset.editId;
    }
    modal.classList.add("open");
  },

  saveRule(e) {
    e.preventDefault();
    const modal = document.getElementById("ruleModal");
    const form = e.target;
    const data = {
      icon: form.elements.ruleIcon.value,
      color: form.elements.ruleColor.value,
      title: form.elements.ruleTitle.value.trim(),
      desc: form.elements.ruleDesc.value.trim(),
      trigger: form.elements.ruleTrigger.value.trim(),
      action: form.elements.ruleAction.value.trim(),
      freq: form.elements.ruleFreq.value,
      channel: form.elements.ruleChannel.value,
      threshold: parseInt(form.elements.ruleThreshold.value) || 0,
      checked: form.elements.ruleActive.checked,
      status: form.elements.ruleActive.checked ? "Đang chạy" : "Tạm dừng",
      last: "vừa xong",
      total: 0,
      success: "—",
    };
    if (!data.title || !data.trigger || !data.action) return;
    if (modal.dataset.editId) {
      Store.updateRule(parseInt(modal.dataset.editId), data);
      showToast("Đã cập nhật quy tắc!");
    } else {
      Store.addRule(data);
      showToast("Đã tạo quy tắc mới!");
    }
    modal.classList.remove("open");
    this.loadPage("automation-rules");
  },
};

// Expose for inline handlers
window.Router = Router;

// ============ TOAST ============
function showToast(message, variant = "success") {
  const toast = document.getElementById("toast");
  const msg = document.getElementById("toastMessage");
  if (!toast || !msg) return;
  msg.textContent = message;
  toast.classList.remove("show");
  void toast.offsetWidth;
  toast.classList.add("show");
  if (variant === "warning") toast.classList.add("toast--warning");
  else if (variant === "error") toast.classList.add("toast--error");
  setTimeout(() => toast.classList.remove("show"), 2500);
}
window.showToast = showToast;

// ============ BOOTSTRAP ============
window.addEventListener("DOMContentLoaded", () => {
  Router.init();
});
