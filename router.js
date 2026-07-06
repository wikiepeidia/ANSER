/**
 * router.js — SPA Router & Page Templates
 * Handles page navigation, renders content, and page-specific logic
 */

const Router = {
  currentPage: "home",
  products: [],
  currentPageInstance: null,

  // ============ INIT ============
  init() {
    this.bindNavEvents();
    this.bindSubmenuEvents();
    this.renderPage("home");
  },

  // ============ NAVIGATION ============
  bindNavEvents() {
    const navItems = document.querySelectorAll(".sidebar__item[data-page]");
    const submenuItems = document.querySelectorAll(".sidebar__submenu-item[data-page]");

    navItems.forEach((item) => {
      item.addEventListener("click", (e) => {
        e.preventDefault();
        const page = item.dataset.page;
        if (page) this.navigateTo(page);
      });
    });

    submenuItems.forEach((item) => {
      item.addEventListener("click", (e) => {
        e.preventDefault();
        const page = item.dataset.page;
        if (page) this.navigateTo(page);
      });
    });
  },

  bindSubmenuEvents() {
    const submenuGroups = document.querySelectorAll(".sidebar__group");

    submenuGroups.forEach((group) => {
      const trigger = group.querySelector(".sidebar__item--has-sub");

      trigger.addEventListener("click", (e) => {
        e.preventDefault();
        const isOpen = group.classList.contains("open");
        submenuGroups.forEach((g) => {
          g.classList.remove("open");
          const t = g.querySelector(".sidebar__item--has-sub");
          if (t) t.classList.remove("active");
        });
        if (!isOpen) {
          group.classList.add("open");
          trigger.classList.add("active");
        } else {
          trigger.classList.remove("active");
        }
      });

      trigger.addEventListener("mouseleave", () => {
        if (!group.classList.contains("open")) {
          trigger.classList.remove("active");
        }
      });

      trigger.addEventListener("mouseenter", () => {
        if (group.classList.contains("open")) {
          trigger.classList.add("active");
        }
      });
    });
  },

  navigateTo(page) {
    if (this.currentPage === page) return;
    this.currentPage = page;
    this.renderPage(page);
    this.updateActiveNav();
  },

  updateActiveNav() {
    // Remove all active classes
    document.querySelectorAll(".sidebar__item").forEach((el) => el.classList.remove("active"));
    document.querySelectorAll(".sidebar__submenu-item").forEach((el) => el.classList.remove("active"));

    // Close all submenus
    document.querySelectorAll(".sidebar__group").forEach((g) => g.classList.remove("open"));

    // Find and activate the correct nav item
    const page = this.currentPage;

    if (page === "home" || page === "reports" || page === "settings") {
      const item = document.querySelector(`.sidebar__item[data-page="${page}"]`);
      if (item) item.classList.add("active");
    } else if (["products", "import", "export"].includes(page)) {
      // Activate "Sản phẩm" parent
      const parentGroup = document.querySelector(".sidebar__group");
      const parentTrigger = parentGroup.querySelector(".sidebar__item--has-sub");
      parentGroup.classList.add("open");
      parentTrigger.classList.add("active");

      // Activate the submenu item
      const subItem = document.querySelector(`.sidebar__submenu-item[data-page="${page}"]`);
      if (subItem) subItem.classList.add("active");
    }
  },

  // ============ RENDER PAGE ============
  renderPage(page) {
    const container = document.getElementById("pageContent");
    if (!container) return;

    // Cleanup previous page
    if (this.currentPageInstance && this.currentPageInstance.destroy) {
      this.currentPageInstance.destroy();
    }

    // Add fade-out animation
    container.classList.add("page-exit");

    setTimeout(() => {
      const html = this.getPageHTML(page);
      container.innerHTML = html;
      container.classList.remove("page-exit");
      container.classList.add("page-enter");

      setTimeout(() => {
        container.classList.remove("page-enter");
      }, 300);

      // Initialize page-specific logic
      this.initPageLogic(page);
    }, 200);
  },

  // ============ PAGE HTML TEMPLATES ============
  getPageHTML(page) {
    const templates = {
      home: this.renderHomePage,
      products: this.renderProductsPage,
      import: this.renderImportPage,
      export: this.renderExportPage,
      reports: this.renderReportsPage,
      settings: this.renderSettingsPage,
    };

    const renderFn = templates[page];
    return renderFn ? renderFn.call(this) : "<p>Trang không tồn tại.</p>";
  },

  // ============ HOME PAGE ============
  renderHomePage() {
    return `
      <div class="content__header">
        <h1 class="content__title">Tổng quan kho hàng</h1>
        <p class="content__subtitle">Chào mừng bạn quay trở lại, Nguyễn Văn A 👋</p>
      </div>

      <!-- Hàng 1: Stat Cards -->
      <div class="stats-grid">
        <div class="stat-card">
          <div class="stat-card__icon stat-card__icon--blue">
            <i class="fa-solid fa-boxes-stacked"></i>
          </div>
          <div class="stat-card__info">
            <span class="stat-card__label">Tổng sản phẩm</span>
            <span class="stat-card__value">1,248</span>
            <span class="stat-card__change stat-card__change--up">
              <i class="fa-solid fa-arrow-up"></i> 5.2%
            </span>
          </div>
        </div>
        <div class="stat-card">
          <div class="stat-card__icon stat-card__icon--green">
            <i class="fa-solid fa-arrow-down-to-line"></i>
          </div>
          <div class="stat-card__info">
            <span class="stat-card__label">Đã nhập tháng này</span>
            <span class="stat-card__value">320</span>
            <span class="stat-card__change stat-card__change--up">
              <i class="fa-solid fa-arrow-up"></i> 12.5%
            </span>
          </div>
        </div>
        <div class="stat-card">
          <div class="stat-card__icon stat-card__icon--orange">
            <i class="fa-solid fa-arrow-up-from-line"></i>
          </div>
          <div class="stat-card__info">
            <span class="stat-card__label">Đã xuất tháng này</span>
            <span class="stat-card__value">185</span>
            <span class="stat-card__change stat-card__change--down">
              <i class="fa-solid fa-arrow-down"></i> 3.8%
            </span>
          </div>
        </div>
        <div class="stat-card">
          <div class="stat-card__icon stat-card__icon--red">
            <i class="fa-solid fa-triangle-exclamation"></i>
          </div>
          <div class="stat-card__info">
            <span class="stat-card__label">Hàng sắp hết</span>
            <span class="stat-card__value">12</span>
            <span class="stat-card__change stat-card__change--alert">
              <i class="fa-solid fa-circle-exclamation"></i> Cần nhập thêm
            </span>
          </div>
        </div>
      </div>

      <!-- Hàng 2: Charts + Quick Info (2 cột) -->
      <div class="z-row-2">
        <!-- Cột trái: Charts -->
        <div class="chart-section">
          <!-- Bar chart 7 ngày -->
          <div class="chart-card">
            <div class="chart-card__header">
              <h3>Nhập / Xuất 7 ngày gần nhất</h3>
              <div class="chart-card__actions">
                <button class="chart-btn active">Tuần</button>
                <button class="chart-btn">Tháng</button>
              </div>
            </div>
            <div class="chart-card__body">
              <div class="bar-chart" id="barChart">
                <div class="bar-chart__bars">
                  ${["T2", "T3", "T4", "T5", "T6", "T7", "CN"].map((day, i) => {
      const heights = ["45%", "65%", "55%", "80%", "90%", "70%", "50%"];
      const colors = ["--chart-import", "--chart-import", "--chart-import", "--chart-export", "--chart-import", "--chart-export", "--chart-import"];
      return `
                      <div class="bar-chart__item" style="--h: ${heights[i]}">
                        <span class="bar-chart__bar" style="background: var(${colors[i]})"></span>
                        <span class="bar-chart__label">${day}</span>
                      </div>`;
    }).join("")}
                </div>
                <div class="bar-chart__legend">
                  <span class="legend-item"><span class="legend-dot legend-dot--import"></span> Nhập</span>
                  <span class="legend-item"><span class="legend-dot legend-dot--export"></span> Xuất</span>
                </div>
              </div>
            </div>
          </div>

          <!-- Doanh thu theo tháng - 2 cột riêng -->
          <div class="chart-card">
            <div class="chart-card__header">
              <h3>Doanh thu theo tháng</h3>
              <div class="chart-card__actions">
                <button class="chart-btn active">6 tháng</button>
              </div>
            </div>
            <div class="chart-card__body">
              <div class="bar-chart bar-chart--dual">
                <div class="bar-chart__bars">
                  ${[
        { month: "T2", import: 65, export: 45 },
        { month: "T3", import: 80, export: 55 },
        { month: "T4", import: 70, export: 60 },
        { month: "T5", import: 90, export: 75 },
        { month: "T6", import: 85, export: 80 },
        { month: "T7", import: 95, export: 70 }
      ].map(item => `
                    <div class="bar-chart__group bar-chart__group--dual">
                      <div class="bar-chart__item" style="--h: ${item.import}%">
                        <span class="bar-chart__bar bar-chart__bar--import"></span>
                      </div>
                      <div class="bar-chart__item" style="--h: ${item.export}%">
                        <span class="bar-chart__bar bar-chart__bar--export"></span>
                      </div>
                      <span class="bar-chart__label">${item.month}</span>
                    </div>`).join("")}
                </div>
                <div class="bar-chart__legend">
                  <span class="legend-item"><span class="legend-dot legend-dot--import"></span> Nhập</span>
                  <span class="legend-item"><span class="legend-dot legend-dot--export"></span> Xuất</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Cột phải: Quick Info -->
        <div class="quick-info-col">
          <div class="quick-card">
            <div class="quick-card__header">
              <h3><i class="fa-solid fa-chart-pie"></i> Tồn kho theo danh mục</h3>
            </div>
            <div class="quick-card__body">
              ${[
        { name: "Điện tử", val: 78 },
        { name: "Thời trang", val: 55 },
        { name: "Gia dụng", val: 42 },
        { name: "Thực phẩm", val: 23 }
      ].map(item => `
                <div class="stock-item">
                  <span class="stock-item__name">${item.name}</span>
                  <div class="stock-item__bar-wrap">
                    <div class="stock-item__bar" style="--w: ${item.val}%"></div>
                  </div>
                  <span class="stock-item__val">${item.val}%</span>
                </div>`).join("")}
            </div>
          </div>
          <div class="quick-card">
            <div class="quick-card__header">
              <h3><i class="fa-solid fa-arrow-down"></i> Nhập kho gần đây</h3>
            </div>
            <div class="quick-card__body quick-card__body--list">
              ${[
        { name: "Laptop ASUS VivoBook", qty: "50 chiếc", date: "01/07/2026", status: "success" },
        { name: "Tai nghe AirPods 3", qty: "120 chiếc", date: "30/06/2026", status: "success" },
        { name: "Chuột Logitech MX", qty: "80 chiếc", date: "29/06/2026", status: "warning" }
      ].map(item => `
                <div class="import-item">
                  <div class="import-item__info">
                    <strong>${item.name}</strong>
                    <span>${item.qty} • ${item.date}</span>
                  </div>
                  <span class="import-item__badge import-item__badge--${item.status}">
                    ${item.status === "success" ? "Đã nhập" : "Chờ duyệt"}
                  </span>
                </div>`).join("")}
            </div>
          </div>
        </div>
      </div>

      <!-- Hàng 3: Table + Notifications -->
      <div class="bottom-row">
        <div class="table-card table-card--wide">
          <div class="table-card__header">
            <h3>Sản phẩm trong kho</h3>
            <button class="btn btn--primary" onclick="Router.navigateTo('products')">
              <i class="fa-solid fa-plus"></i> Thêm sản phẩm
            </button>
          </div>
          <div class="table-card__body">
            <table class="data-table">
              <thead>
                <tr>
                  <th>Mã SP</th>
                  <th>Tên sản phẩm</th>
                  <th>Danh mục</th>
                  <th>Tồn kho</th>
                  <th>Giá nhập</th>
                  <th>Trạng thái</th>
                </tr>
              </thead>
              <tbody>
                ${[
        { code: "#SP-001", name: "Laptop ASUS VivoBook 15", cat: "Điện tử", stock: 50, price: "15,500,000 ₫", status: "green", label: "Còn hàng" },
        { code: "#SP-002", name: "Tai nghe AirPods Pro 2", cat: "Điện tử", stock: 8, price: "4,200,000 ₫", status: "orange", label: "Sắp hết" },
        { code: "#SP-003", name: "Bàn phím cơ Keychron K2", cat: "Điện tử", stock: 0, price: "2,800,000 ₫", status: "red", label: "Hết hàng" },
        { code: "#SP-004", name: "Áo thun nam basic", cat: "Thời trang", stock: 245, price: "120,000 ₫", status: "green", label: "Còn hàng" },
        { code: "#SP-005", name: "Nồi cơm điện Sharp", cat: "Gia dụng", stock: 32, price: "890,000 ₫", status: "green", label: "Còn hàng" }
      ].map(row => `
                  <tr>
                    <td><strong>${row.code}</strong></td>
                    <td>${row.name}</td>
                    <td>${row.cat}</td>
                    <td>${row.stock}</td>
                    <td>${row.price}</td>
                    <td><span class="badge badge--${row.status}">${row.label}</span></td>
                  </tr>`).join("")}
              </tbody>
            </table>
          </div>
        </div>
        <div class="table-card">
          <div class="table-card__header">
            <h3><i class="fa-solid fa-bell"></i> Thông báo</h3>
          </div>
          <div class="noti-list">
            ${[
        { icon: "red", iconClass: "fa-solid fa-triangle-exclamation", title: "3 sản phẩm sắp hết hàng", desc: "Cần nhập thêm trong tuần này" },
        { icon: "green", iconClass: "fa-solid fa-arrow-down-to-line", title: "Đơn nhập kho mới", desc: "Laptop ASUS - 50 chiếc" },
        { icon: "orange", iconClass: "fa-solid fa-clock", title: "Hạn sử dụng sắp tới", desc: "5 sản phẩm thực phẩm" },
        { icon: "blue", iconClass: "fa-solid fa-file-export", title: "Xuất kho thành công", desc: "25 chiếc AirPods Pro 2" }
      ].map(item => `
              <div class="noti-item">
                <div class="noti-item__icon noti-item__icon--${item.icon}">
                  <i class="${item.iconClass}"></i>
                </div>
                <div class="noti-item__content">
                  <strong>${item.title}</strong>
                  <span>${item.desc}</span>
                </div>
              </div>`).join("")}
          </div>
        </div>
      </div>
    `;
  },

  // ============ PRODUCTS PAGE ============
  renderProductsPage() {
    return `
      <div class="content__header">
        <h1 class="content__title">Danh sách sản phẩm</h1>
        <p class="content__subtitle">Quản lý toàn bộ sản phẩm trong kho hàng</p>
      </div>

      <div class="toolbar">
        <div class="toolbar__filters">
          <select class="filter-select" id="filterCategory">
            <option value="">Tất cả danh mục</option>
            <option value="electronics">Điện tử</option>
            <option value="fashion">Thời trang</option>
            <option value="home">Gia dụng</option>
            <option value="food">Thực phẩm</option>
          </select>
          <select class="filter-select" id="filterStatus">
            <option value="">Tất cả trạng thái</option>
            <option value="in-stock">Còn hàng</option>
            <option value="low-stock">Sắp hết</option>
            <option value="out-of-stock">Hết hàng</option>
          </select>
        </div>
        <button class="btn btn--primary" id="btnAddProduct">
          <i class="fa-solid fa-plus"></i> Thêm sản phẩm
        </button>
      </div>

      <div class="table-card">
        <div class="table-card__body">
          <table class="data-table" id="productTable">
            <thead>
              <tr>
                <th><input type="checkbox" id="selectAll" /></th>
                <th>Mã SP</th>
                <th>Tên sản phẩm</th>
                <th>Danh mục</th>
                <th>Tồn kho</th>
                <th>Giá nhập</th>
                <th>Giá bán</th>
                <th>Trạng thái</th>
                <th>Hành động</th>
              </tr>
            </thead>
            <tbody id="productTableBody"></tbody>
          </table>
        </div>
        <div class="pagination">
          <span class="pagination__info" id="paginationInfo">Hiển thị 1-10</span>
          <div class="pagination__controls" id="paginationControls">
            <button class="pagination__btn" id="prevPage" disabled><i class="fa-solid fa-chevron-left"></i></button>
            <button class="pagination__btn active" data-page="1">1</button>
            <button class="pagination__btn" data-page="2">2</button>
            <button class="pagination__btn" data-page="3">3</button>
            <button class="pagination__btn" id="nextPage"><i class="fa-solid fa-chevron-right"></i></button>
          </div>
        </div>
      </div>
    `;
  },

  // ============ IMPORT PAGE ============
  renderImportPage() {
    return `
      <div class="content__header">
        <h1 class="content__title">Nhập sản phẩm</h1>
        <p class="content__subtitle">Tạo phiếu nhập kho hàng</p>
      </div>

      <div class="form-card">
        <div class="form-card__header">
          <h3><i class="fa-solid fa-file-invoice"></i> Thông tin phiếu nhập</h3>
        </div>
        <div class="form-card__body">
          <div class="form-row form-row--3">
            <div class="form-group">
              <label>Mã phiếu nhập</label>
              <input type="text" value="PN-20260702-001" readonly />
            </div>
            <div class="form-group">
              <label>Ngày nhập</label>
              <input type="date" value="2026-07-02" />
            </div>
            <div class="form-group">
              <label>Kho nhập</label>
              <select>
                <option>Kho chính</option>
                <option>Kho phụ</option>
                <option>Kho TP.HCM</option>
              </select>
            </div>
          </div>
          <div class="form-group">
            <label>Nhà cung cấp</label>
            <input type="text" placeholder="Nhập tên nhà cung cấp" />
          </div>
          <div class="form-group">
            <label>Ghi chú</label>
            <textarea rows="2" placeholder="Ghi chú phiếu nhập (nếu có)"></textarea>
          </div>
        </div>
      </div>

      <div class="form-card">
        <div class="form-card__header">
          <h3><i class="fa-solid fa-boxes-stacked"></i> Danh sách sản phẩm nhập</h3>
          <button class="btn btn--outline btn--sm" id="btnAddImportItem">
            <i class="fa-solid fa-plus"></i> Thêm sản phẩm
          </button>
        </div>
        <div class="table-card__body">
          <table class="data-table">
            <thead>
              <tr>
                <th>Mã SP</th>
                <th>Tên sản phẩm</th>
                <th>Đơn vị</th>
                <th>Số lượng</th>
                <th>Đơn giá (₫)</th>
                <th>Thành tiền (₫)</th>
                <th></th>
              </tr>
            </thead>
            <tbody id="importItemsBody">
              <tr class="import-item-row">
                <td><input type="text" class="table-input" value="SP-001" /></td>
                <td><input type="text" class="table-input" placeholder="Tên sản phẩm" /></td>
                <td><input type="text" class="table-input" value="Chiếc" /></td>
                <td><input type="number" class="table-input import-qty" value="50" /></td>
                <td><input type="number" class="table-input import-price" value="15500000" /></td>
                <td class="item-total import-total">775,000,000 ₫</td>
                <td><button class="action-btn action-btn--danger btn-remove-row"><i class="fa-solid fa-trash"></i></button></td>
              </tr>
              <tr class="import-item-row">
                <td><input type="text" class="table-input" value="SP-002" /></td>
                <td><input type="text" class="table-input" placeholder="Tên sản phẩm" /></td>
                <td><input type="text" class="table-input" value="Chiếc" /></td>
                <td><input type="number" class="table-input import-qty" value="120" /></td>
                <td><input type="number" class="table-input import-price" value="4200000" /></td>
                <td class="item-total import-total">504,000,000 ₫</td>
                <td><button class="action-btn action-btn--danger btn-remove-row"><i class="fa-solid fa-trash"></i></button></td>
              </tr>
            </tbody>
          </table>
        </div>
        <div class="form-summary">
          <div class="form-summary__row">
            <span>Tổng số sản phẩm:</span>
            <strong id="totalImportItems">2 loại</strong>
          </div>
          <div class="form-summary__row">
            <span>Tổng số lượng:</span>
            <strong id="totalImportQty">170 chiếc</strong>
          </div>
          <div class="form-summary__row form-summary__row--total">
            <span>Tổng tiền:</span>
            <strong id="totalImportAmount">1,279,000,000 ₫</strong>
          </div>
        </div>
        <div class="form-card__footer">
          <button class="btn btn--outline" onclick="showToast('Đã lưu nháp!')">
            <i class="fa-solid fa-floppy-disk"></i> Lưu nháp
          </button>
          <button class="btn btn--primary" onclick="showToast('Đã xác nhận nhập kho!')">
            <i class="fa-solid fa-check"></i> Xác nhận nhập kho
          </button>
        </div>
      </div>

      <div class="table-card">
        <div class="table-card__header">
          <h3>Lịch sử nhập kho gần đây</h3>
        </div>
        <div class="table-card__body">
          <table class="data-table">
            <thead>
              <tr>
                <th>Mã phiếu</th>
                <th>Ngày</th>
                <th>Nhà cung cấp</th>
                <th>Số sản phẩm</th>
                <th>Tổng tiền</th>
                <th>Trạng thái</th>
              </tr>
            </thead>
            <tbody>
              ${[
        { code: "#PN-001", date: "01/07/2026", supplier: "Công ty TNHH ABC", items: "3 loại", amount: "890,000,000 ₫" },
        { code: "#PN-002", date: "30/06/2026", supplier: "Nhà cung cấp XYZ", items: "2 loại", amount: "450,000,000 ₫" },
        { code: "#PN-003", date: "28/06/2026", supplier: "Cửa hàng TechStore", items: "5 loại", amount: "1,200,000,000 ₫" }
      ].map(row => `
                <tr>
                  <td><strong>${row.code}</strong></td>
                  <td>${row.date}</td>
                  <td>${row.supplier}</td>
                  <td>${row.items}</td>
                  <td>${row.amount}</td>
                  <td><span class="badge badge--green">Hoàn thành</span></td>
                </tr>`).join("")}
            </tbody>
          </table>
        </div>
      </div>
    `;
  },

  // ============ EXPORT PAGE ============
  renderExportPage() {
    return `
      <div class="content__header">
        <h1 class="content__title">Xuất sản phẩm</h1>
        <p class="content__subtitle">Tạo phiếu xuất kho hàng</p>
      </div>

      <div class="form-card">
        <div class="form-card__header">
          <h3><i class="fa-solid fa-file-invoice-dollar"></i> Thông tin phiếu xuất</h3>
        </div>
        <div class="form-card__body">
          <div class="form-row form-row--3">
            <div class="form-group">
              <label>Mã phiếu xuất</label>
              <input type="text" value="PX-20260702-001" readonly />
            </div>
            <div class="form-group">
              <label>Ngày xuất</label>
              <input type="date" value="2026-07-02" />
            </div>
            <div class="form-group">
              <label>Kho xuất</label>
              <select>
                <option>Kho chính</option>
                <option>Kho phụ</option>
                <option>Kho TP.HCM</option>
              </select>
            </div>
          </div>
          <div class="form-row form-row--2">
            <div class="form-group">
              <label>Khách hàng / Đơn vị nhận</label>
              <input type="text" placeholder="Nhập tên khách hàng" />
            </div>
            <div class="form-group">
              <label>Mục đích xuất</label>
              <select>
                <option>Bán hàng</option>
                <option>Trả hàng nhà cung cấp</option>
                <option>Chuyển kho</option>
                <option>Khác</option>
              </select>
            </div>
          </div>
          <div class="form-group">
            <label>Ghi chú</label>
            <textarea rows="2" placeholder="Ghi chú phiếu xuất (nếu có)"></textarea>
          </div>
        </div>
      </div>

      <div class="form-card">
        <div class="form-card__header">
          <h3><i class="fa-solid fa-truck-fast"></i> Danh sách sản phẩm xuất</h3>
          <button class="btn btn--outline btn--sm" id="btnAddExportItem">
            <i class="fa-solid fa-plus"></i> Thêm sản phẩm
          </button>
        </div>
        <div class="table-card__body">
          <table class="data-table">
            <thead>
              <tr>
                <th>Mã SP</th>
                <th>Tên sản phẩm</th>
                <th>Đơn vị</th>
                <th>Tồn kho</th>
                <th>SL xuất</th>
                <th>Đơn giá (₫)</th>
                <th>Thành tiền (₫)</th>
                <th></th>
              </tr>
            </thead>
            <tbody id="exportItemsBody">
              <tr class="export-item-row">
                <td><input type="text" class="table-input" value="SP-001" /></td>
                <td><input type="text" class="table-input" placeholder="Tên sản phẩm" /></td>
                <td><input type="text" class="table-input" value="Chiếc" /></td>
                <td class="stock-val">50</td>
                <td><input type="number" class="table-input export-qty" value="25" /></td>
                <td><input type="number" class="table-input export-price" value="18500000" /></td>
                <td class="item-total export-total">462,500,000 ₫</td>
                <td><button class="action-btn action-btn--danger btn-remove-row"><i class="fa-solid fa-trash"></i></button></td>
              </tr>
              <tr class="export-item-row">
                <td><input type="text" class="table-input" value="SP-004" /></td>
                <td><input type="text" class="table-input" placeholder="Tên sản phẩm" /></td>
                <td><input type="text" class="table-input" value="Chiếc" /></td>
                <td class="stock-val">245</td>
                <td><input type="number" class="table-input export-qty" value="80" /></td>
                <td><input type="number" class="table-input export-price" value="150000" /></td>
                <td class="item-total export-total">12,000,000 ₫</td>
                <td><button class="action-btn action-btn--danger btn-remove-row"><i class="fa-solid fa-trash"></i></button></td>
              </tr>
            </tbody>
          </table>
        </div>
        <div class="form-summary">
          <div class="form-summary__row">
            <span>Tổng số sản phẩm:</span>
            <strong id="totalExportItems">2 loại</strong>
          </div>
          <div class="form-summary__row">
            <span>Tổng số lượng xuất:</span>
            <strong id="totalExportQty">105 chiếc</strong>
          </div>
          <div class="form-summary__row form-summary__row--total">
            <span>Tổng tiền:</span>
            <strong id="totalExportAmount">474,500,000 ₫</strong>
          </div>
        </div>
        <div class="form-card__footer">
          <button class="btn btn--outline" onclick="showToast('Đã lưu nháp!')">
            <i class="fa-solid fa-floppy-disk"></i> Lưu nháp
          </button>
          <button class="btn btn--primary" onclick="showToast('Đã xác nhận xuất kho!')">
            <i class="fa-solid fa-check"></i> Xác nhận xuất kho
          </button>
        </div>
      </div>

      <div class="table-card">
        <div class="table-card__header">
          <h3>Lịch sử xuất kho gần đây</h3>
        </div>
        <div class="table-card__body">
          <table class="data-table">
            <thead>
              <tr>
                <th>Mã phiếu</th>
                <th>Ngày</th>
                <th>Khách hàng</th>
                <th>Số sản phẩm</th>
                <th>Tổng tiền</th>
                <th>Trạng thái</th>
              </tr>
            </thead>
            <tbody>
              ${[
        { code: "#PX-001", date: "01/07/2026", customer: "Cửa hàng Laptop Sài Gòn", items: "5 loại", amount: "320,000,000 ₫" },
        { code: "#PX-002", date: "30/06/2026", customer: "Công ty TechVN", items: "3 loại", amount: "180,000,000 ₫" },
        { code: "#PX-003", date: "28/06/2026", customer: "Khách lẻ", items: "2 loại", amount: "45,000,000 ₫" }
      ].map(row => `
                <tr>
                  <td><strong>${row.code}</strong></td>
                  <td>${row.date}</td>
                  <td>${row.customer}</td>
                  <td>${row.items}</td>
                  <td>${row.amount}</td>
                  <td><span class="badge badge--green">Hoàn thành</span></td>
                </tr>`).join("")}
            </tbody>
          </table>
        </div>
      </div>
    `;
  },

  // ============ REPORTS PAGE ============
  renderReportsPage() {
    return `
      <div class="content__header">
        <h1 class="content__title">Báo cáo</h1>
        <p class="content__subtitle">Thống kê và phân tích dữ liệu kho hàng</p>
      </div>

      <div class="report-toolbar">
        <div class="chart-card__actions">
          <button class="chart-btn active" data-range="day">Ngày</button>
          <button class="chart-btn" data-range="month">Tháng</button>
          <button class="chart-btn" data-range="year">Năm</button>
        </div>
        <div class="report-toolbar__right">
          <select class="filter-select">
            <option>Tháng 07/2026</option>
            <option>Tháng 06/2026</option>
            <option>Tháng 05/2026</option>
          </select>
          <button class="btn btn--outline" onclick="showToast('Đã xuất Excel!')">
            <i class="fa-solid fa-file-export"></i> Xuất Excel
          </button>
        </div>
      </div>

      <div class="stats-grid stats-grid--4">
        ${[
        { icon: "fa-solid fa-arrow-down-to-line", color: "blue", label: "Tổng nhập", value: "1,279M", unit: "₫", change: "15.3%", up: true },
        { icon: "fa-solid fa-arrow-up-from-line", color: "orange", label: "Tổng xuất", value: "890M", unit: "₫", change: "8.7%", up: true },
        { icon: "fa-solid fa-chart-line", color: "green", label: "Doanh thu ước tính", value: "2.1B", unit: "₫", change: "22.1%", up: true },
        { icon: "fa-solid fa-warehouse", color: "purple", label: "Tồn kho hiện tại", value: "1,248", unit: "", change: "5.2%", up: false }
      ].map(stat => `
          <div class="stat-card">
            <div class="stat-card__icon stat-card__icon--${stat.color}">
              <i class="${stat.icon}"></i>
            </div>
            <div class="stat-card__info">
              <span class="stat-card__label">${stat.label}</span>
              <span class="stat-card__value">${stat.value} <span class="stat-card__unit">${stat.unit}</span></span>
              <span class="stat-card__change ${stat.up ? 'stat-card__change--up' : 'stat-card__change--down'}">
                <i class="fa-solid fa-arrow-${stat.up ? 'up' : 'down'}"></i> ${stat.change}
              </span>
            </div>
          </div>`).join("")}
      </div>

      <!-- Row 2: 4 charts -->
      <div class="charts-row charts-row--4col">
        <!-- Chart 1: Nhập / Xuất theo thời gian -->
        <div class="chart-card">
          <div class="chart-card__header">
            <h3>Nhập / Xuất theo thời gian</h3>
          </div>
          <div class="chart-card__body">
            <div class="bar-chart bar-chart--grouped">
              <div class="bar-chart__bars">
                ${["T2", "T3", "T4", "T5", "T6", "T7"].map((day, i) => {
        const importH = ["70%", "85%", "65%", "90%", "95%", "80%"][i];
        const exportH = ["45%", "60%", "55%", "75%", "80%", "65%"][i];
        return `
                    <div class="bar-chart__group">
                      <div class="bar-chart__item" style="--h: ${importH}">
                        <span class="bar-chart__bar bar-chart__bar--import"></span>
                      </div>
                      <div class="bar-chart__item" style="--h: ${exportH}">
                        <span class="bar-chart__bar bar-chart__bar--export"></span>
                      </div>
                      <span class="bar-chart__label">${day}</span>
                    </div>`;
      }).join("")}
              </div>
              <div class="bar-chart__legend">
                <span class="legend-item"><span class="legend-dot legend-dot--import"></span> Nhập</span>
                <span class="legend-item"><span class="legend-dot legend-dot--export"></span> Xuất</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Chart 2: Doanh thu vs Lợi nhuận (Pie) -->
        <div class="chart-card">
          <div class="chart-card__header">
            <h3>Doanh thu vs Lợi nhuận</h3>
          </div>
          <div class="chart-card__body chart-card__body--center">
            <div class="pie-chart">
              <div class="pie-chart__ring" style="background: conic-gradient(var(--chart-revenue) 0deg 252deg, var(--chart-profit) 252deg 300deg, var(--chart-cost) 300deg 360deg)">
                <div class="pie-chart__center">
                  <span class="pie-chart__total">2.1B</span>
                  <span class="pie-chart__label">Doanh thu</span>
                </div>
              </div>
              <div class="donut-chart__legend">
                <div class="donut-chart__legend-item"><span class="dot" style="background: var(--chart-revenue)"></span> Doanh thu <strong>2.1B ₫</strong></div>
                <div class="donut-chart__legend-item"><span class="dot" style="background: var(--chart-profit)"></span> Lợi nhuận <strong>650M ₫</strong></div>
                <div class="donut-chart__legend-item"><span class="dot" style="background: var(--chart-cost)"></span> Chi phí <strong>1.45B ₫</strong></div>
              </div>
            </div>
          </div>
        </div>

        <!-- Chart 3: Top sản phẩm bán chạy -->
        <div class="chart-card">
          <div class="chart-card__header">
            <h3>Top sản phẩm bán chạy</h3>
          </div>
          <div class="chart-card__body">
            <div class="horizontal-bar-chart">
              ${[
        { name: "iPhone 15 Pro", val: 95 },
        { name: "MacBook Air M3", val: 78 },
        { name: "AirPods Pro 2", val: 62 },
        { name: "iPad Pro 12.9\"", val: 45 },
        { name: "Apple Watch U2", val: 30 }
      ].map(item => `
                <div class="h-bar-item">
                  <div class="h-bar-item__label">${item.name}</div>
                  <div class="h-bar-item__track">
                    <div class="h-bar-item__fill" style="--w: ${item.val}%"></div>
                  </div>
                  <div class="h-bar-item__value">${item.val}</div>
                </div>`).join("")}
            </div>
          </div>
        </div>

        <!-- Chart 4: Tồn kho theo danh mục (Donut) -->
        <div class="chart-card">
          <div class="chart-card__header">
            <h3>Tồn kho theo danh mục</h3>
          </div>
          <div class="chart-card__body chart-card__body--center">
            <div class="donut-chart">
              <div class="donut-chart__ring donut-chart__ring--large">
                <div class="donut-chart__ring" style="background: conic-gradient(var(--brand-primary) 0deg 130deg, var(--stat-green-icon) 130deg 220deg, var(--stat-orange-icon) 220deg 290deg, var(--stat-purple-icon) 290deg 360deg)">
                  <div class="donut-chart__center">
                    <span class="donut-chart__total">1,248</span>
                    <span class="donut-chart__label">Tổng SP</span>
                  </div>
                </div>
              </div>
              <div class="donut-chart__legend">
                <div class="donut-chart__legend-item"><span class="dot" style="background: var(--brand-primary)"></span> Điện tử <strong>420</strong></div>
                <div class="donut-chart__legend-item"><span class="dot" style="background: var(--stat-green-icon)"></span> Thời trang <strong>312</strong></div>
                <div class="donut-chart__legend-item"><span class="dot" style="background: var(--stat-orange-icon)"></span> Gia dụng <strong>280</strong></div>
                <div class="donut-chart__legend-item"><span class="dot" style="background: var(--stat-purple-icon)"></span> Thực phẩm <strong>236</strong></div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Row 3: 3 new charts -->
      <div class="charts-row charts-row--3col">
        <!-- Chart 5: So sánh doanh thu hôm nay vs hôm qua (Line) -->
        <div class="chart-card">
          <div class="chart-card__header">
            <h3>Doanh thu Hôm nay vs Hôm qua</h3>
            <span class="chart-card__badge chart-card__badge--success">+12.5%</span>
          </div>
          <div class="chart-card__body">
            <div class="line-chart line-chart--compare">
              <div class="line-chart__svg">
                <svg viewBox="0 0 400 150" preserveAspectRatio="none">
                  <line x1="0" y1="37.5" x2="400" y2="37.5" stroke="var(--chart-bar-bg)" stroke-width="1" stroke-dasharray="4" />
                  <line x1="0" y1="75" x2="400" y2="75" stroke="var(--chart-bar-bg)" stroke-width="1" stroke-dasharray="4" />
                  <!-- Hôm qua (xám) -->
                  <polyline points="0,100 57,85 114,95 171,70 228,60 285,75 342,80 400,85" fill="none" stroke="var(--text-muted)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" stroke-dasharray="6 4" />
                  <!-- Hôm nay (xanh chính) -->
                  <polyline points="0,110 57,90 114,85 171,55 228,35 285,50 342,30 400,25" fill="none" stroke="var(--brand-primary)" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" />
                  <polygon points="0,110 57,90 114,85 171,55 228,35 285,50 342,30 400,25 400,150 0,150" fill="url(#areaGradient)" opacity="0.15" />
                </svg>
              </div>
              <div class="line-chart__labels">
                <span>06h</span><span>09h</span><span>12h</span><span>15h</span><span>18h</span><span>21h</span><span>24h</span>
              </div>
            </div>
            <div class="chart-compare-legend">
              <span class="legend-item"><span class="legend-dot legend-dot--compare-yesterday"></span> Hôm qua</span>
              <span class="legend-item"><span class="legend-dot legend-dot--compare-today"></span> Hôm nay</span>
            </div>
          </div>
        </div>

        <!-- Chart 6: Nhà cung cấp (Bar chart) -->
        <div class="chart-card">
          <div class="chart-card__header">
            <h3>Nhà cung cấp hàng đầu</h3>
          </div>
          <div class="chart-card__body">
            <div class="bar-chart bar-chart--supplier">
              <div class="bar-chart__bars">
                ${[
        { name: "Apple VN", val: 95 },
        { name: "Samsung", val: 72 },
        { name: "Sony", val: 58 },
        { name: "LG", val: 45 },
        { name: "Sharp", val: 35 },
        { name: "Xiaomi", val: 28 }
      ].map(item => `
                  <div class="bar-chart__item bar-chart__item--h" style="--w: ${item.val}%">
                    <span class="bar-chart__bar bar-chart__bar--supplier"></span>
                    <span class="bar-chart__label-bar">${item.name}</span>
                  </div>`).join("")}
              </div>
            </div>
          </div>
        </div>

        <!-- Chart 7: Doanh thu theo thời gian (Line) -->
        <div class="chart-card">
          <div class="chart-card__header">
            <h3>Doanh thu theo thời gian</h3>
          </div>
          <div class="chart-card__body">
            <div class="line-chart">
              <div class="line-chart__svg">
                <svg viewBox="0 0 400 150" preserveAspectRatio="none">
                  <line x1="0" y1="37.5" x2="400" y2="37.5" stroke="var(--chart-bar-bg)" stroke-width="1" />
                  <line x1="0" y1="75" x2="400" y2="75" stroke="var(--chart-bar-bg)" stroke-width="1" />
                  <line x1="0" y1="112.5" x2="400" y2="112.5" stroke="var(--chart-bar-bg)" stroke-width="1" />
                  <polyline points="0,120 57,90 114,100 171,60 228,40 285,55 342,30 400,20" fill="none" stroke="var(--brand-primary)" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" />
                  <polygon points="0,120 57,90 114,100 171,60 228,40 285,55 342,30 400,20 400,150 0,150" fill="url(#areaGradient)" opacity="0.2" />
                </svg>
              </div>
              <div class="line-chart__labels">
                <span>T2</span><span>T3</span><span>T4</span><span>T5</span><span>T6</span><span>T7</span><span>CN</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="table-card">
        <div class="table-card__header">
          <h3>Chi tiết nhập / Xuất tháng này</h3>
          <button class="btn btn--outline" onclick="showToast('Đã xuất báo cáo!')">
            <i class="fa-solid fa-file-export"></i> Xuất báo cáo
          </button>
        </div>
        <div class="table-card__body">
          <table class="data-table">
            <thead>
              <tr>
                <th>Ngày</th>
                <th>Mã phiếu</th>
                <th>Loại</th>
                <th>Số sản phẩm</th>
                <th>Tổng tiền</th>
                <th>Trạng thái</th>
              </tr>
            </thead>
            <tbody>
              ${[
        { date: "02/07/2026", code: "#PN-007", type: "Nhập", items: "170 chiếc", amount: "1,279,000,000 ₫" },
        { date: "01/07/2026", code: "#PX-004", type: "Xuất", items: "105 chiếc", amount: "474,500,000 ₫" },
        { date: "01/07/2026", code: "#PN-006", type: "Nhập", items: "85 chiếc", amount: "450,000,000 ₫" },
        { date: "30/06/2026", code: "#PX-003", type: "Xuất", items: "60 chiếc", amount: "320,000,000 ₫" },
        { date: "29/06/2026", code: "#PN-005", type: "Nhập", items: "200 chiếc", amount: "890,000,000 ₫" }
      ].map(row => `
                <tr>
                  <td>${row.date}</td>
                  <td><strong>${row.code}</strong></td>
                  <td><span class="badge badge--${row.type === 'Nhập' ? 'blue' : 'orange'}">${row.type}</span></td>
                  <td>${row.items}</td>
                  <td>${row.amount}</td>
                  <td><span class="badge badge--green">Hoàn thành</span></td>
                </tr>`).join("")}
            </tbody>
          </table>
        </div>
      </div>
    `;
  },

  // ============ SETTINGS PAGE ============
  renderSettingsPage() {
    return `
      <div class="content__header">
        <h1 class="content__title">Cài đặt</h1>
        <p class="content__subtitle">Cấu hình hệ thống và tài khoản</p>
      </div>

      <div class="form-card">
        <div class="form-card__header">
          <h3><i class="fa-solid fa-gear"></i> Thông tin cửa hàng</h3>
        </div>
        <div class="form-card__body">
          <div class="form-row form-row--2">
            <div class="form-group">
              <label>Tên cửa hàng</label>
              <input type="text" value="ANSER Store" />
            </div>
            <div class="form-group">
              <label>Email liên hệ</label>
              <input type="email" value="contact@anser.vn" />
            </div>
          </div>
          <div class="form-row form-row--2">
            <div class="form-group">
              <label>Số điện thoại</label>
              <input type="tel" value="028 1234 5678" />
            </div>
            <div class="form-group">
              <label>Địa chỉ</label>
              <input type="text" value="123 Nguyễn Trãi, Q.1, TP.HCM" />
            </div>
          </div>
        </div>
        <div class="form-card__footer">
          <button class="btn btn--primary" onclick="showToast('Đã lưu cài đặt!')">
            <i class="fa-solid fa-check"></i> Lưu thay đổi
          </button>
        </div>
      </div>

      <div class="form-card">
        <div class="form-card__header">
          <h3><i class="fa-solid fa-user-gear"></i> Quản lý tài khoản</h3>
        </div>
        <div class="form-card__body">
          <div class="form-group">
            <label>Tên người dùng</label>
            <input type="text" value="Nguyễn Văn A" />
          </div>
          <div class="form-group">
            <label>Email</label>
            <input type="email" value="admin@anser.vn" />
          </div>
          <div class="form-group">
            <label>Mật khẩu mới</label>
            <input type="password" placeholder="Để trống nếu không đổi" />
          </div>
        </div>
        <div class="form-card__footer">
          <button class="btn btn--outline" onclick="showToast('Đã cập nhật tài khoản!')">
            <i class="fa-solid fa-floppy-disk"></i> Cập nhật
          </button>
        </div>
      </div>
    `;
  },

  // ============ PAGE-SPECIFIC LOGIC ============
  initPageLogic(page) {
    switch (page) {
      case "home":
        this.initHomePage();
        break;
      case "products":
        this.initProductsPage();
        break;
      case "import":
        this.initImportPage();
        break;
      case "export":
        this.initExportPage();
        break;
      case "reports":
        this.initReportsPage();
        break;
    }
  },

  initHomePage() {
    // Chart buttons
    document.querySelectorAll(".chart-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        const parent = btn.closest(".chart-card__actions");
        if (parent) {
          parent.querySelectorAll(".chart-btn").forEach((b) => b.classList.remove("active"));
          btn.classList.add("active");
        }
      });
    });

    // Animate chart cards on load
    setTimeout(() => {
      document.querySelectorAll(".chart-card").forEach((card) => {
        card.classList.add("chart-animated");
      });
    }, 100);
  },

  initProductsPage() {
    // Sample data
    const allProducts = [
      { id: 1, code: "SP-001", name: "Laptop ASUS VivoBook 15", category: "Điện tử", stock: 50, importPrice: "15,500,000 ₫", sellPrice: "18,900,000 ₫", status: "green", statusText: "Còn hàng" },
      { id: 2, code: "SP-002", name: "Tai nghe AirPods Pro 2", category: "Điện tử", stock: 8, importPrice: "4,200,000 ₫", sellPrice: "5,990,000 ₫", status: "orange", statusText: "Sắp hết" },
      { id: 3, code: "SP-003", name: "Bàn phím cơ Keychron K2", category: "Điện tử", stock: 0, importPrice: "2,800,000 ₫", sellPrice: "3,500,000 ₫", status: "red", statusText: "Hết hàng" },
      { id: 4, code: "SP-004", name: "Áo thun nam basic", category: "Thời trang", stock: 245, importPrice: "120,000 ₫", sellPrice: "250,000 ₫", status: "green", statusText: "Còn hàng" },
      { id: 5, code: "SP-005", name: "Nồi cơm điện Sharp", category: "Gia dụng", stock: 32, importPrice: "890,000 ₫", sellPrice: "1,350,000 ₫", status: "green", statusText: "Còn hàng" },
      { id: 6, code: "SP-006", name: "Quần jeans nam Slim", category: "Thời trang", stock: 5, importPrice: "350,000 ₫", sellPrice: "650,000 ₫", status: "orange", statusText: "Sắp hết" },
      { id: 7, code: "SP-007", name: "Chuột Logitech MX Master", category: "Điện tử", stock: 0, importPrice: "1,800,000 ₫", sellPrice: "2,500,000 ₫", status: "red", statusText: "Hết hàng" },
      { id: 8, code: "SP-008", name: "Máy lọc không khí Xiaomi", category: "Gia dụng", stock: 18, importPrice: "2,100,000 ₫", sellPrice: "3,200,000 ₫", status: "green", statusText: "Còn hàng" },
      { id: 9, code: "SP-009", name: "Bánh kẹo cao cấp", category: "Thực phẩm", stock: 3, importPrice: "85,000 ₫", sellPrice: "150,000 ₫", status: "orange", statusText: "Sắp hết" },
      { id: 10, code: "SP-010", name: "Sữa tươi Pasteur", category: "Thực phẩm", stock: 120, importPrice: "25,000 ₫", sellPrice: "45,000 ₫", status: "green", statusText: "Còn hàng" },
    ];

    this.products = allProducts;
    let currentPage = 1;
    const itemsPerPage = 5;
    let filteredProducts = [...allProducts];

    const renderTable = () => {
      const start = (currentPage - 1) * itemsPerPage;
      const end = start + itemsPerPage;
      const pageProducts = filteredProducts.slice(start, end);
      const tbody = document.getElementById("productTableBody");

      if (!tbody) return;

      tbody.innerHTML = pageProducts.map((p) => `
        <tr data-id="${p.id}">
          <td><input type="checkbox" class="row-checkbox" /></td>
          <td><strong>${p.code}</strong></td>
          <td>${p.name}</td>
          <td>${p.category}</td>
          <td>${p.stock}</td>
          <td>${p.importPrice}</td>
          <td>${p.sellPrice}</td>
          <td><span class="badge badge--${p.status}">${p.statusText}</span></td>
          <td>
            <div class="action-group">
              <button class="action-btn action-btn--edit" onclick="Router.editProduct(${p.id})">
                <i class="fa-solid fa-pen-to-square"></i>
              </button>
              <button class="action-btn action-btn--danger" onclick="Router.deleteProduct(${p.id})">
                <i class="fa-solid fa-trash"></i>
              </button>
            </div>
          </td>
        </tr>`).join("");

      // Update pagination
      const total = filteredProducts.length;
      const totalPages = Math.ceil(total / itemsPerPage);
      const info = document.getElementById("paginationInfo");
      if (info) {
        info.textContent = `Hiển thị ${start + 1}-${Math.min(end, total)} của ${total} sản phẩm`;
      }
      document.getElementById("prevPage").disabled = currentPage === 1;
      document.getElementById("nextPage").disabled = currentPage >= totalPages;
      document.querySelectorAll("#paginationControls .pagination__btn[data-page]").forEach((btn) => {
        btn.classList.toggle("active", parseInt(btn.dataset.page) === currentPage);
      });
    };

    // Filter events
    const applyFilters = () => {
      const cat = document.getElementById("filterCategory")?.value || "";
      const status = document.getElementById("filterStatus")?.value || "";
      filteredProducts = allProducts.filter((p) => {
        if (cat && p.category !== cat) return false;
        if (status === "in-stock" && p.stock === 0) return false;
        if (status === "low-stock" && (p.stock === 0 || p.stock > 10)) return false;
        if (status === "out-of-stock" && p.stock > 0) return false;
        return true;
      });
      currentPage = 1;
      renderTable();
    };

    document.getElementById("filterCategory")?.addEventListener("change", applyFilters);
    document.getElementById("filterStatus")?.addEventListener("change", applyFilters);

    // Add product button
    document.getElementById("btnAddProduct")?.addEventListener("click", () => this.editProduct());

    // Pagination
    document.getElementById("prevPage")?.addEventListener("click", () => {
      if (currentPage > 1) { currentPage--; renderTable(); }
    });
    document.getElementById("nextPage")?.addEventListener("click", () => {
      const totalPages = Math.ceil(filteredProducts.length / itemsPerPage);
      if (currentPage < totalPages) { currentPage++; renderTable(); }
    });
    document.querySelectorAll("#paginationControls .pagination__btn[data-page]").forEach((btn) => {
      btn.addEventListener("click", () => {
        currentPage = parseInt(btn.dataset.page);
        renderTable();
      });
    });

    renderTable();
  },

  editProduct(id) {
    document.getElementById("modalTitle").textContent = id ? "Sửa sản phẩm" : "Thêm sản phẩm";
    document.getElementById("productModal").classList.add("open");
  },

  deleteProduct(id) {
    document.getElementById("deleteMessage").textContent = "Bạn có chắc muốn xoá sản phẩm này?";
    document.getElementById("deleteModal").classList.add("open");
  },

  initImportPage() {
    const recalc = () => {
      const rows = document.querySelectorAll("#importItemsBody .import-item-row");
      let total = 0, qty = 0;
      rows.forEach((row) => {
        const rQty = parseInt(row.querySelector(".import-qty")?.value) || 0;
        const rPrice = parseInt(row.querySelector(".import-price")?.value) || 0;
        const itemTotal = rQty * rPrice;
        total += itemTotal;
        qty += rQty;
        const totalCell = row.querySelector(".import-total");
        if (totalCell) totalCell.textContent = new Intl.NumberFormat("vi-VN").format(itemTotal) + " ₫";
      });
      document.getElementById("totalImportItems").textContent = rows.length + " loại";
      document.getElementById("totalImportQty").textContent = qty + " chiếc";
      document.getElementById("totalImportAmount").textContent = new Intl.NumberFormat("vi-VN").format(total) + " ₫";
    };

    document.querySelectorAll(".import-item-row").forEach((row) => {
      row.querySelectorAll("input").forEach((inp) => inp.addEventListener("input", recalc));
    });

    document.querySelectorAll(".btn-remove-row").forEach((btn) => {
      btn.addEventListener("click", () => {
        const rows = document.querySelectorAll("#importItemsBody .import-item-row");
        if (rows.length > 1) btn.closest("tr").remove();
        else btn.closest("tr").querySelectorAll("input").forEach((i) => (i.value = ""));
        recalc();
      });
    });

    document.getElementById("btnAddImportItem")?.addEventListener("click", () => {
      const tbody = document.getElementById("importItemsBody");
      const row = document.createElement("tr");
      row.className = "import-item-row";
      row.innerHTML = `
        <td><input type="text" class="table-input" placeholder="Mã SP" /></td>
        <td><input type="text" class="table-input" placeholder="Tên sản phẩm" /></td>
        <td><input type="text" class="table-input" value="Chiếc" /></td>
        <td><input type="number" class="table-input import-qty" value="0" /></td>
        <td><input type="number" class="table-input import-price" value="0" /></td>
        <td class="item-total import-total">0 ₫</td>
        <td><button class="action-btn action-btn--danger btn-remove-row"><i class="fa-solid fa-trash"></i></button></td>`;
      tbody.appendChild(row);
      row.querySelectorAll("input").forEach((inp) => inp.addEventListener("input", recalc));
      row.querySelector(".btn-remove-row").addEventListener("click", () => {
        const rows = document.querySelectorAll("#importItemsBody .import-item-row");
        if (rows.length > 1) row.remove();
        else row.querySelectorAll("input").forEach((i) => (i.value = ""));
        recalc();
      });
    });

    recalc();
  },

  initExportPage() {
    const recalc = () => {
      const rows = document.querySelectorAll("#exportItemsBody .export-item-row");
      let total = 0, qty = 0;
      rows.forEach((row) => {
        const rQty = parseInt(row.querySelector(".export-qty")?.value) || 0;
        const rPrice = parseInt(row.querySelector(".export-price")?.value) || 0;
        const itemTotal = rQty * rPrice;
        total += itemTotal;
        qty += rQty;
        const totalCell = row.querySelector(".export-total");
        if (totalCell) totalCell.textContent = new Intl.NumberFormat("vi-VN").format(itemTotal) + " ₫";
      });
      document.getElementById("totalExportItems").textContent = rows.length + " loại";
      document.getElementById("totalExportQty").textContent = qty + " chiếc";
      document.getElementById("totalExportAmount").textContent = new Intl.NumberFormat("vi-VN").format(total) + " ₫";
    };

    document.querySelectorAll(".export-item-row").forEach((row) => {
      row.querySelectorAll("input").forEach((inp) => inp.addEventListener("input", recalc));
    });

    document.querySelectorAll(".btn-remove-row").forEach((btn) => {
      btn.addEventListener("click", () => {
        const rows = document.querySelectorAll("#exportItemsBody .export-item-row");
        if (rows.length > 1) btn.closest("tr").remove();
        else btn.closest("tr").querySelectorAll("input").forEach((i) => (i.value = ""));
        recalc();
      });
    });

    document.getElementById("btnAddExportItem")?.addEventListener("click", () => {
      const tbody = document.getElementById("exportItemsBody");
      const row = document.createElement("tr");
      row.className = "export-item-row";
      row.innerHTML = `
        <td><input type="text" class="table-input" placeholder="Mã SP" /></td>
        <td><input type="text" class="table-input" placeholder="Tên sản phẩm" /></td>
        <td><input type="text" class="table-input" value="Chiếc" /></td>
        <td class="stock-val">0</td>
        <td><input type="number" class="table-input export-qty" value="0" /></td>
        <td><input type="number" class="table-input export-price" value="0" /></td>
        <td class="item-total export-total">0 ₫</td>
        <td><button class="action-btn action-btn--danger btn-remove-row"><i class="fa-solid fa-trash"></i></button></td>`;
      tbody.appendChild(row);
      row.querySelectorAll("input").forEach((inp) => inp.addEventListener("input", recalc));
      row.querySelector(".btn-remove-row").addEventListener("click", () => {
        const rows = document.querySelectorAll("#exportItemsBody .export-item-row");
        if (rows.length > 1) row.remove();
        else row.querySelectorAll("input").forEach((i) => (i.value = ""));
        recalc();
      });
    });

    recalc();
  },

  initReportsPage() {
    document.querySelectorAll(".chart-btn[data-range]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const parent = btn.closest(".chart-card__actions");
        if (parent) {
          parent.querySelectorAll(".chart-btn").forEach((b) => b.classList.remove("active"));
          btn.classList.add("active");
        }
      });
    });

    // Animate chart cards on load
    setTimeout(() => {
      document.querySelectorAll(".chart-card").forEach((card) => {
        card.classList.add("chart-animated");
      });
    }, 100);
  },

  // ============ TOAST ============
  destroy() {
    // Cleanup when navigating away
  }
};

// Global function for toast
function showToast(message) {
  const toast = document.getElementById("toast");
  const toastMessage = document.getElementById("toastMessage");
  if (toast && toastMessage) {
    toastMessage.textContent = message;
    toast.classList.add("show");
    setTimeout(() => toast.classList.remove("show"), 3000);
  }
}

// Init router when DOM is ready
document.addEventListener("DOMContentLoaded", () => Router.init());
