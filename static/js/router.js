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
 *   - Router.editOrder(id) / Router.deleteOrder(id) / Router.viewOrder(id)
 *   - Router.transitionOrder(id, newStatus)
 *   - Router.addBatch() / Router.deleteBatch(id) / Router.viewBatch(id)
 *   - Router.resetBatchSeed()
 *   - Router.openQCForm(id) / Router.saveQCForm(e)
 *   - Router.openBatchEventForm(orderId) / Router.saveBatchEventForm(e)
 *   - Router.openTransferForm() / Router.saveTransferForm(e)
 *   - Router.openStockCountForm() / Router.saveStockCountForm(e)
 *   - Router.resetWarehouseSeed()
 *   - Router.editSupplier(id) / Router.deleteSupplier(id) / Router.viewSupplier(id)
 */

const Router = {
  currentPage: "home",
  pageCache: new Map(), // page HTML cache

  // ============ INIT ============
  async init() {
    // Products come from the real ANSER API. Automation (rules/logs) is
    // loaded per-page directly from the n8n API, not preloaded here.
    await Store.loadProducts();
    Store.loadProductionOrders();
    Store.loadBOMCatalog();
    Store.loadMaterialBatches();
    Store.loadWarehouseStock();
    Store.loadSuppliers();
    Store.loadInvoices();
    Store.loadChatMessages();

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
    modal.dataset.deleteType = "product";
    modal.classList.add("open");
  },

  async confirmDelete() {
    const modal = document.getElementById("deleteModal");
    const id = parseInt(modal?.dataset?.deleteId);
    const type = modal?.dataset?.deleteType || "product";
    if (!id) return;
    try {
      if (type === "order") {
        Store.deleteOrder(id);
        showToast("Đã xoá đơn hàng!");
      } else if (type === "batch") {
        Store.deleteBatch(id);
        showToast("Đã xoá lô nguyên liệu!");
      } else if (type === "supplier") {
        Store.deleteSupplier(id);
        showToast("Đã xoá nhà cung cấp!");
      } else {
        await Store.deleteProduct(id);
        showToast("Đã xoá sản phẩm!");
      }
      modal.classList.remove("open");
      const backTo = {
        "production-order-detail": "production-orders",
        "material-batch-detail": "material-batches",
        "supplier-detail": "suppliers",
      }[this.currentPage];
      this.loadPage(backTo || this.currentPage);
    } catch (err) {
      showToast(err.message || "Lỗi xoá", "error");
      modal.classList.remove("open");
    }
  },

  // ============ PRODUCTION ORDERS (mock, wired to Store.productionOrders) ============
  editOrder(id) {
    const modal = document.getElementById("orderModal");
    const title = document.getElementById("orderModalTitle");
    const form = document.getElementById("orderForm");
    if (!modal) return;

    const productSelect = form.elements.orderProduct;
    productSelect.innerHTML = `<option value="">Chọn sản phẩm</option>` +
      Store.products.map((p) =>
        `<option value="${Helpers.escapeHtml(p.code)}" data-name="${Helpers.escapeHtml(p.name)}" data-unit="${Helpers.escapeHtml(p.unit)}">${Helpers.escapeHtml(p.code)} — ${Helpers.escapeHtml(p.name)}</option>`
      ).join("");

    if (id) {
      const o = Store.getOrderById(id);
      if (o) {
        title.textContent = `Sửa đơn ${o.code}`;
        productSelect.value = o.productCode;
        form.elements.orderQuantity.value = o.quantity;
        form.elements.orderCustomer.value = o.customerName || "";
        form.elements.orderNotes.value = o.notes || "";
        modal.dataset.editId = id;
      }
    } else {
      title.textContent = "Tạo đơn sản xuất";
      form.reset();
      delete modal.dataset.editId;
    }
    modal.classList.add("open");
  },

  saveOrderForm(e) {
    e.preventDefault();
    const modal = document.getElementById("orderModal");
    const form = e.target;
    const productSelect = form.elements.orderProduct;
    const opt = productSelect.selectedOptions[0];
    const quantity = parseInt(form.elements.orderQuantity.value) || 0;
    if (!productSelect.value || quantity <= 0) {
      showToast("Chọn sản phẩm và nhập số lượng hợp lệ", "warning");
      return;
    }
    const data = {
      productCode: productSelect.value,
      productName: opt?.dataset.name || productSelect.value,
      unit: opt?.dataset.unit || "cái",
      quantity,
      customerName: form.elements.orderCustomer.value.trim(),
      notes: form.elements.orderNotes.value.trim(),
    };
    try {
      if (modal.dataset.editId) {
        Store.updateOrder(parseInt(modal.dataset.editId), data);
        showToast("Đã cập nhật đơn hàng!");
      } else {
        Store.createOrder(data);
        showToast("Đã tạo đơn sản xuất mới!");
      }
      modal.classList.remove("open");
      this.loadPage(this.currentPage === "production-order-detail" ? "production-orders" : this.currentPage);
    } catch (err) {
      showToast(err.message || "Lỗi lưu đơn hàng", "error");
    }
  },

  deleteOrder(id) {
    const o = Store.getOrderById(id);
    const modal = document.getElementById("deleteModal");
    if (!modal) return;
    document.getElementById("deleteMessage").textContent = o
      ? `Bạn có chắc muốn xoá đơn "${o.code}"?`
      : "Bạn có chắc muốn xoá đơn hàng này?";
    modal.dataset.deleteId = id;
    modal.dataset.deleteType = "order";
    modal.classList.add("open");
  },

  viewOrder(id) {
    Helpers.save("selectedOrderId", id);
    this.navigateTo("production-order-detail");
  },

  async transitionOrder(id, newStatus) {
    const order = Store.getOrderById(id);
    if (!order) return;
    const label = Store.ORDER_TRANSITION_LABELS[`${order.status}>${newStatus}`] || "chuyển trạng thái";
    const extra = newStatus === "completed"
      ? ` Thao tác này sẽ cộng ${order.quantity} ${order.unit} vào tồn kho sản phẩm "${order.productName}".`
      : "";
    if (!window.confirm(`Xác nhận "${label}" cho đơn ${order.code}?${extra}`)) return;
    try {
      await Store.transitionOrder(id, newStatus);
      showToast(`Đã ${label.toLowerCase()} đơn ${order.code}!`);
      this.loadPage(this.currentPage);
    } catch (err) {
      showToast(err.message || "Lỗi chuyển trạng thái", "error");
    }
  },

  // ============ MATERIAL BATCHES (mock, wired to Store.materialBatches) ============
  addBatch() {
    const modal = document.getElementById("batchModal");
    const form = document.getElementById("batchForm");
    if (!modal) return;

    const matSelect = form.elements.batchMaterial;
    matSelect.innerHTML = `<option value="">Chọn nguyên vật liệu</option>` +
      Store._MOCK_MATERIALS.map((m) =>
        `<option value="${Helpers.escapeHtml(m.code)}">${Helpers.escapeHtml(m.code)} — ${Helpers.escapeHtml(m.name)}</option>`
      ).join("");

    form.reset();
    modal.classList.add("open");
  },

  saveBatchForm(e) {
    e.preventDefault();
    const modal = document.getElementById("batchModal");
    const form = e.target;
    if (!form.elements.batchMaterial.value || !(parseFloat(form.elements.batchQuantity.value) > 0)) {
      showToast("Chọn nguyên vật liệu và nhập số lượng hợp lệ", "warning");
      return;
    }
    Store.createBatch({
      materialCode: form.elements.batchMaterial.value,
      supplierName: form.elements.batchSupplier.value.trim(),
      quantity: form.elements.batchQuantity.value,
      expiryDate: form.elements.batchExpiry.value,
      notes: form.elements.batchNotes.value.trim(),
    });
    showToast("Đã thêm lô nguyên liệu mới!");
    modal.classList.remove("open");
    this.loadPage(this.currentPage);
  },

  deleteBatch(id) {
    const b = Store.getBatchById(id);
    const modal = document.getElementById("deleteModal");
    if (!modal) return;
    document.getElementById("deleteMessage").textContent = b
      ? `Bạn có chắc muốn xoá lô "${b.code}"?`
      : "Bạn có chắc muốn xoá lô nguyên liệu này?";
    modal.dataset.deleteId = id;
    modal.dataset.deleteType = "batch";
    modal.classList.add("open");
  },

  viewBatch(id) {
    Helpers.save("selectedBatchId", id);
    this.navigateTo("material-batch-detail");
  },

  resetBatchSeed() {
    if (!window.confirm("Nạp lại dữ liệu mẫu lô nguyên liệu? Toàn bộ lô hiện tại (kể cả lô bạn tự thêm/tự kiểm định) sẽ bị thay bằng bộ dữ liệu mẫu mới nhất.")) return;
    Store.resetMaterialBatchesSeed();
    showToast("Đã nạp lại dữ liệu mẫu lô nguyên liệu!");
    this.loadPage(this.currentPage);
  },

  // Trang QC (qc.html) và material-batches.html — form nhập kết quả kiểm
  // định (đạt/không đạt + ghi chú) cho 1 lô đang chờ.
  openQCForm(id) {
    const batch = Store.getBatchById(id);
    const modal = document.getElementById("qcModal");
    const form = document.getElementById("qcForm");
    if (!batch || !modal) return;
    document.getElementById("qcModalBatchInfo").innerHTML =
      `<strong>${Helpers.escapeHtml(batch.code)}</strong> — ${Helpers.escapeHtml(batch.materialName)} `
      + `(${Helpers.formatNumber(batch.quantity)} ${Helpers.escapeHtml(batch.unit)}) · NCC: ${Helpers.escapeHtml(batch.supplierName || "—")}`;
    form.reset();
    modal.dataset.batchId = id;
    modal.classList.add("open");
  },

  saveQCForm(e) {
    e.preventDefault();
    const modal = document.getElementById("qcModal");
    const form = e.target;
    const id = parseInt(modal.dataset.batchId);
    const result = form.elements.qcResult.value;
    if (!id || !result) {
      showToast("Chọn kết quả kiểm định (Đạt / Không đạt)", "warning");
      return;
    }
    try {
      Store.setBatchQC(id, result, form.elements.qcNote.value.trim());
      modal.classList.remove("open");
      if (result === "failed") {
        showToast(`Lô đã KHÔNG ĐẠT — đã khoá, không được dùng cho sản xuất`, "warning");
      } else {
        showToast("Đã lưu kết quả kiểm định: Đạt");
      }
      this.loadPage(this.currentPage);
    } catch (err) {
      showToast(err.message || "Lỗi lưu kết quả kiểm định", "error");
    }
  },

  // ============ BATCH PROCESS LOG (mock, wired to Store.processLogs) ============
  openBatchEventForm(orderId) {
    const order = Store.getOrderById(orderId);
    const modal = document.getElementById("batchEventModal");
    const form = document.getElementById("batchEventForm");
    if (!order || !modal) return;
    if (order.status !== "in_progress") {
      showToast('Chỉ ghi được sự kiện cho đơn đang ở trạng thái "Đang sản xuất"', "warning");
      return;
    }
    document.getElementById("batchEventOrderInfo").innerHTML =
      `<strong>${Helpers.escapeHtml(order.code)}</strong> — ${Helpers.escapeHtml(order.productName)}`;
    form.reset();
    modal.dataset.orderId = orderId;
    modal.classList.add("open");
  },

  saveBatchEventForm(e) {
    e.preventDefault();
    const modal = document.getElementById("batchEventModal");
    const form = e.target;
    const orderId = parseInt(modal.dataset.orderId);
    const eventType = form.elements.eventType.value;
    if (!orderId || !eventType) {
      showToast("Chọn loại sự kiện", "warning");
      return;
    }
    try {
      Store.addProcessEvent(orderId, eventType, form.elements.batchEventNote.value.trim());
      showToast(`Đã ghi sự kiện: ${eventType}`);
      modal.classList.remove("open");
      this.loadPage(this.currentPage);
    } catch (err) {
      showToast(err.message || "Lỗi ghi sự kiện", "error");
    }
  },

  // ============ WAREHOUSES (mock, wired to Store.warehouseStock) ============
  _populateProductSelect(selectEl, placeholder) {
    selectEl.innerHTML = `<option value="">${placeholder}</option>` +
      Store.products.map((p) => `<option value="${Helpers.escapeHtml(p.code)}">${Helpers.escapeHtml(p.code)} — ${Helpers.escapeHtml(p.name)}</option>`).join("");
  },

  openTransferForm() {
    const modal = document.getElementById("transferModal");
    const form = document.getElementById("transferForm");
    if (!modal) return;
    this._populateProductSelect(form.elements.transferProduct, "Chọn sản phẩm");
    const whOptions = `<option value="">Chọn kho</option>` +
      Store.WAREHOUSES.map((w) => `<option value="${w.id}">${Helpers.escapeHtml(w.name)}</option>`).join("");
    form.elements.transferFromWarehouse.innerHTML = whOptions;
    form.elements.transferToWarehouse.innerHTML = whOptions;
    form.reset();
    form.elements.transferFromLocation.innerHTML = `<option value="">Chọn kho nguồn trước</option>`;
    form.elements.transferToLocation.innerHTML = `<option value="">Chọn kho đích trước</option>`;
    document.getElementById("transferStockInfo").textContent = "";
    modal.classList.add("open");
  },

  saveTransferForm(e) {
    e.preventDefault();
    const modal = document.getElementById("transferModal");
    const form = e.target;
    try {
      Store.transferStock({
        productCode: form.elements.transferProduct.value,
        fromWarehouseId: form.elements.transferFromWarehouse.value,
        fromLocationId: form.elements.transferFromLocation.value,
        toWarehouseId: form.elements.transferToWarehouse.value,
        toLocationId: form.elements.transferToLocation.value,
        quantity: form.elements.transferQuantity.value,
        note: form.elements.transferNote.value.trim(),
      });
      showToast("Đã chuyển kho thành công!");
      modal.classList.remove("open");
      this.loadPage(this.currentPage);
    } catch (err) {
      showToast(err.message || "Lỗi chuyển kho", "error");
    }
  },

  openStockCountForm() {
    const modal = document.getElementById("stockCountModal");
    const form = document.getElementById("stockCountForm");
    if (!modal) return;
    this._populateProductSelect(form.elements.countProduct, "Chọn sản phẩm");
    form.elements.countWarehouse.innerHTML = `<option value="">Chọn kho</option>` +
      Store.WAREHOUSES.map((w) => `<option value="${w.id}">${Helpers.escapeHtml(w.name)}</option>`).join("");
    form.reset();
    form.elements.countLocation.innerHTML = `<option value="">Chọn kho trước</option>`;
    document.getElementById("countSystemQty").textContent = "—";
    document.getElementById("countSystemQty").dataset.systemQty = "";
    document.getElementById("countDiff").textContent = "—";
    modal.classList.add("open");
  },

  saveStockCountForm(e) {
    e.preventDefault();
    const modal = document.getElementById("stockCountModal");
    const form = e.target;
    try {
      const entry = Store.recordStockCount({
        warehouseId: form.elements.countWarehouse.value,
        locationId: form.elements.countLocation.value,
        productCode: form.elements.countProduct.value,
        countedQty: form.elements.countActualQty.value,
        note: form.elements.countNote.value.trim(),
      });
      const msg = entry.diff === 0
        ? "Đã lưu kiểm kê — khớp hệ thống"
        : `Đã lưu kiểm kê — chênh lệch ${entry.diff > 0 ? "+" : ""}${entry.diff}`;
      showToast(msg, entry.diff === 0 ? "success" : "warning");
      modal.classList.remove("open");
      this.loadPage(this.currentPage);
    } catch (err) {
      showToast(err.message || "Lỗi lưu kiểm kê", "error");
    }
  },

  resetWarehouseSeed() {
    if (!window.confirm("Nạp lại dữ liệu mẫu kho? Toàn bộ tồn kho theo vị trí, lịch sử chuyển kho và kiểm kê hiện tại sẽ bị xoá và sinh lại từ tồn kho thật của sản phẩm.")) return;
    Store.resetWarehouseStockSeed();
    showToast("Đã nạp lại dữ liệu mẫu kho!");
    this.loadPage(this.currentPage);
  },

  // ============ SUPPLIERS (mock, wired to Store.suppliers) ============
  editSupplier(id) {
    const modal = document.getElementById("supplierModal");
    const title = document.getElementById("supplierModalTitle");
    const form = document.getElementById("supplierForm");
    if (!modal) return;
    if (id) {
      const s = Store.getSupplierById(id);
      if (s) {
        title.textContent = `Sửa nhà cung cấp: ${s.name}`;
        form.elements.supplierName.value = s.name;
        form.elements.supplierContact.value = s.contact || "";
        form.elements.supplierPhone.value = s.phone || "";
        form.elements.supplierEmail.value = s.email || "";
        form.elements.supplierAddress.value = s.address || "";
        form.elements.supplierNotes.value = s.notes || "";
        modal.dataset.editId = id;
      }
    } else {
      title.textContent = "Thêm nhà cung cấp";
      form.reset();
      delete modal.dataset.editId;
    }
    modal.classList.add("open");
  },

  saveSupplierForm(e) {
    e.preventDefault();
    const modal = document.getElementById("supplierModal");
    const form = e.target;
    const data = {
      name: form.elements.supplierName.value.trim(),
      contact: form.elements.supplierContact.value.trim(),
      phone: form.elements.supplierPhone.value.trim(),
      email: form.elements.supplierEmail.value.trim(),
      address: form.elements.supplierAddress.value.trim(),
      notes: form.elements.supplierNotes.value.trim(),
    };
    try {
      if (modal.dataset.editId) {
        Store.updateSupplier(parseInt(modal.dataset.editId), data);
        showToast("Đã cập nhật nhà cung cấp!");
      } else {
        Store.createSupplier(data);
        showToast("Đã thêm nhà cung cấp mới!");
      }
      modal.classList.remove("open");
      this.loadPage(this.currentPage === "supplier-detail" ? "suppliers" : this.currentPage);
    } catch (err) {
      showToast(err.message || "Lỗi lưu nhà cung cấp", "error");
    }
  },

  deleteSupplier(id) {
    const s = Store.getSupplierById(id);
    const modal = document.getElementById("deleteModal");
    if (!modal) return;
    document.getElementById("deleteMessage").textContent = s
      ? `Bạn có chắc muốn xoá nhà cung cấp "${s.name}"?`
      : "Bạn có chắc muốn xoá nhà cung cấp này?";
    modal.dataset.deleteId = id;
    modal.dataset.deleteType = "supplier";
    modal.classList.add("open");
  },

  viewSupplier(id) {
    Helpers.save("selectedSupplierId", id);
    this.navigateTo("supplier-detail");
  },

  _catToVal(c) {
    return ({ "Điện tử": "electronics", "Thời trang": "fashion", "Gia dụng": "home", "Thực phẩm": "food" })[c] || "electronics";
  },
  _valToCat(v) {
    return ({ electronics: "Điện tử", fashion: "Thời trang", home: "Gia dụng", food: "Thực phẩm" })[v] || "Điện tử";
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
