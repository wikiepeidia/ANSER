/**
 * store.js — Data store, wired to the real ANSER backend for products,
 * imports, exports, customers, dashboard stats, production orders and BOM.
 *
 * Automation (rules/logs) is not stored here — automation-rules.html and
 * automation-logs.html read directly from the real n8n API (/api/n8n/*).
 *
 * Material batches/warehouses/suppliers/invoices below this point are still
 * MOCK (localStorage) — real backends for those land in later phases.
 */

const Store = {
  // --- CSRF helper (Flask-WTF CSRFProtect requires this header on writes) ---
  _csrfToken() {
    return document.querySelector('meta[name="csrf-token"]')?.getAttribute("content") || "";
  },
  async _api(url, options = {}) {
    const opts = { headers: {}, ...options };
    opts.headers = { ...opts.headers };
    if (options.body) {
      opts.headers["Content-Type"] = "application/json";
    }
    if (options.method && options.method !== "GET") {
      opts.headers["X-CSRFToken"] = this._csrfToken();
    }
    const res = await fetch(url, opts);
    let data;
    try {
      data = await res.json();
    } catch (e) {
      throw new Error(`HTTP ${res.status}`);
    }
    if (!data.success) throw new Error(data.message || `Lỗi gọi ${url}`);
    return data;
  },

  // --- Products (real API: /api/products) ---
  products: [],

  _statusFor(stock) {
    if (stock === 0) return { status: "red", statusText: "Hết hàng" };
    if (stock <= 10) return { status: "orange", statusText: "Sắp hết" };
    return { status: "green", statusText: "Còn hàng" };
  },

  _mapProduct(p) {
    const stock = p.stock_quantity || 0;
    return {
      id: p.id,
      code: p.code,
      name: p.name,
      category: p.category || "",
      unit: p.unit || "cái",
      stock,
      // ANSER chỉ lưu 1 giá bán ở cấp sản phẩm — không có giá nhập riêng
      // theo sản phẩm (giá nhập nằm theo từng phiếu nhập, không cố định).
      sellPrice: p.price || 0,
      description: p.description || "",
      imageUrl: p.image_url || "",
      ...this._statusFor(stock),
    };
  },

  async loadProducts() {
    try {
      const data = await this._api("/api/products");
      this.products = (data.products || []).map((p) => this._mapProduct(p));
    } catch (e) {
      console.error("loadProducts failed:", e);
      this.products = [];
    }
    return this.products;
  },

  async addProduct(p) {
    await this._api("/api/products", {
      method: "POST",
      body: JSON.stringify({
        code: p.code,
        name: p.name,
        category: p.category,
        unit: p.unit || "cái",
        price: p.sellPrice,
        stock_quantity: p.stock,
        description: p.description || "",
      }),
    });
    await this.loadProducts();
  },

  async updateProduct(id, patch) {
    await this._api(`/api/products/${id}`, {
      method: "PUT",
      body: JSON.stringify({
        name: patch.name,
        category: patch.category,
        unit: patch.unit || "cái",
        price: patch.sellPrice,
        stock_quantity: patch.stock,
        description: patch.description || "",
      }),
    });
    await this.loadProducts();
  },

  async deleteProduct(id) {
    await this._api(`/api/products/${id}`, { method: "DELETE" });
    this.products = this.products.filter((p) => p.id !== id);
  },

  getProductById(id) {
    return this.products.find((p) => p.id === id);
  },

  // --- Imports (real API: /api/imports) ---
  async loadImports() {
    try {
      const data = await this._api("/api/imports");
      return data.imports || [];
    } catch (e) {
      console.error("loadImports failed:", e);
      return [];
    }
  },

  async createImport({ supplierName, notes, items }) {
    return this._api("/api/imports", {
      method: "POST",
      body: JSON.stringify({
        supplier_name: supplierName,
        notes,
        items: items.map((it) => ({
          product_code: it.code,
          product_name: it.name,
          quantity: it.qty,
          unit_price: it.price,
        })),
      }),
    });
  },

  // --- Exports (real API: /api/exports) ---
  async loadExports() {
    try {
      const data = await this._api("/api/exports");
      return data.exports || [];
    } catch (e) {
      console.error("loadExports failed:", e);
      return [];
    }
  },

  async createExport({ customerId, notes, items }) {
    return this._api("/api/exports", {
      method: "POST",
      body: JSON.stringify({
        customer_id: customerId,
        notes,
        items: items.map((it) => ({
          product_code: it.code,
          product_name: it.name,
          quantity: it.qty,
          unit_price: it.price,
        })),
      }),
    });
  },

  // --- Customers (real API: /api/customers, used by the export form) ---
  async loadCustomers() {
    try {
      const data = await this._api("/api/customers");
      return data.customers || [];
    } catch (e) {
      console.error("loadCustomers failed:", e);
      return [];
    }
  },

  // --- Dashboard / report stats (real API) ---
  async loadDashboardStats() {
    try {
      return await this._api("/api/dashboard/stats");
    } catch (e) {
      console.error("loadDashboardStats failed:", e);
      return null;
    }
  },

  // --- Production Orders (real API: /api/production-orders*, backed by
  // routes/production_routes.py). Function bodies below call Store._api();
  // signatures are unchanged so callers/HTML need no changes. ---
  ORDER_STATUSES: {
    draft:             { label: "Nháp",           badge: "gray",   icon: "fa-file-pen" },
    pending_approval:  { label: "Chờ duyệt",       badge: "orange", icon: "fa-hourglass-half" },
    approved:          { label: "Đã duyệt",        badge: "blue",   icon: "fa-check" },
    in_progress:       { label: "Đang sản xuất",   badge: "purple", icon: "fa-industry" },
    completed:         { label: "Hoàn thành",      badge: "green",  icon: "fa-circle-check" },
    cancelled:         { label: "Đã huỷ",          badge: "red",    icon: "fa-ban" },
  },

  ORDER_STATUS_FLOW: {
    draft: ["pending_approval", "cancelled"],
    pending_approval: ["approved", "draft", "cancelled"],
    approved: ["in_progress", "cancelled"],
    in_progress: ["completed", "cancelled"],
    completed: [],
    cancelled: [],
  },

  ORDER_TRANSITION_LABELS: {
    "draft>pending_approval": "Gửi duyệt",
    "pending_approval>approved": "Duyệt đơn",
    "pending_approval>draft": "Trả về nháp",
    "approved>in_progress": "Bắt đầu sản xuất",
    "in_progress>completed": "Hoàn thành",
    "draft>cancelled": "Huỷ đơn",
    "pending_approval>cancelled": "Huỷ đơn",
    "approved>cancelled": "Huỷ đơn",
    "in_progress>cancelled": "Huỷ đơn",
  },

  // Metadata cho từng loại sự kiện trong processLogs — dùng để tô màu chấm
  // tròn/icon trên dòng thời gian (batch-logs.html, production-order-detail.html).
  EVENT_META: {
    "Tạo đơn hàng":        { icon: "fa-file-circle-plus",       color: "gray" },
    "Gửi duyệt":           { icon: "fa-paper-plane",            color: "orange" },
    "Duyệt đơn":           { icon: "fa-check",                  color: "blue" },
    "Trả về nháp":         { icon: "fa-rotate-left",             color: "gray" },
    "Bắt đầu sản xuất":    { icon: "fa-play",                    color: "purple" },
    "Dừng sản xuất":       { icon: "fa-pause",                   color: "orange" },
    "Tiếp tục sản xuất":   { icon: "fa-play",                    color: "purple" },
    "Sự cố":               { icon: "fa-triangle-exclamation",    color: "red" },
    "Hoàn thành":          { icon: "fa-circle-check",            color: "green" },
    "Nhập kho thành phẩm": { icon: "fa-box-open",                color: "green" },
    "Huỷ đơn":             { icon: "fa-ban",                     color: "red" },
  },

  eventMeta(event) {
    return this.EVENT_META[event] || { icon: "fa-circle-info", color: "gray" };
  },

  // Sự kiện tự do trong quá trình sản xuất (dừng/tiếp tục/sự cố) — không
  // đổi trạng thái đơn, chỉ ghi log. Khác với transitionOrder() (đổi
  // trạng thái theo ORDER_STATUS_FLOW).
  addProcessEvent(orderId, event, note) {
    const order = this.getOrderById(orderId);
    if (!order) throw new Error("Không tìm thấy đơn hàng");
    const entry = { id: Date.now(), orderId: order.id, ts: new Date().toISOString(), event, note: note || "" };
    this.processLogs.push(entry);
    this._saveProductionOrders();
    return entry;
  },

  _MOCK_MATERIALS: [
    { code: "NVL-001", name: "Vải cotton", unit: "m", unitCost: 45000 },
    { code: "NVL-002", name: "Chỉ may", unit: "cuộn", unitCost: 8000 },
    { code: "NVL-003", name: "Khuy nhựa", unit: "cái", unitCost: 500 },
    { code: "NVL-004", name: "Nhãn mác", unit: "cái", unitCost: 1200 },
    { code: "NVL-005", name: "Bao bì đóng gói", unit: "cái", unitCost: 2500 },
    { code: "NVL-006", name: "Keo dán công nghiệp", unit: "kg", unitCost: 60000 },
    { code: "NVL-007", name: "Dây kéo", unit: "cái", unitCost: 3000 },
  ],

  _hashStr(s) {
    let h = 0;
    for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) | 0;
    return Math.abs(h);
  },

  // --- BOM master data (real API: /api/bom/*, backed by
  // routes/production_routes.py). Function bodies below call Store._api();
  // signatures are unchanged so bom.html/production-order-detail.html
  // need no changes. No client-side fabrication of default BOM lines —
  // an empty result means no BOM has been saved for that product yet. ---

  async saveBOMForProduct(productCode, lines) {
    if (!productCode) throw new Error("Chưa chọn sản phẩm");
    const clean = (lines || [])
      .filter((l) => l.code && l.name && Number(l.qtyPerUnit) > 0)
      .map((l) => ({
        code: l.code.trim(),
        name: l.name.trim(),
        unit: (l.unit || "cái").trim() || "cái",
        unitCost: Number(l.unitCost) || 0,
        qtyPerUnit: Number(l.qtyPerUnit),
      }));
    if (!clean.length) throw new Error("Cần ít nhất 1 dòng nguyên vật liệu hợp lệ (mã, tên, định mức > 0)");
    const res = await this._api(`/api/bom/${encodeURIComponent(productCode)}`, {
      method: "PUT",
      body: JSON.stringify({ lines: clean }),
    });
    return res.lines || clean;
  },

  // POST /api/bom/calculate — tính tổng NVL cần khi sản xuất X đơn vị.
  async calculateBOMForQuantity(productCode, quantity) {
    const res = await this._api("/api/bom/calculate", {
      method: "POST",
      body: JSON.stringify({ productCode, quantity }),
    });
    return { lines: res.lines, totalCost: res.totalCost, quantity: res.quantity };
  },

  // GET /api/bom/<productCode> — trả về [] nếu sản phẩm chưa có BOM.
  async getBOMForProduct(productCode) {
    const res = await this._api(`/api/bom/${encodeURIComponent(productCode)}`);
    return res.lines || [];
  },

  async getBOMForOrder(order) {
    if (!order) return [];
    return (await this.calculateBOMForQuantity(order.productCode, order.quantity)).lines;
  },

  async getOrderCost(order) {
    const bom = await this.getBOMForOrder(order);
    if (!bom.length) return null;
    return bom.reduce((sum, l) => sum + l.lineCost, 0);
  },

  // Giá thành thực tế (MOCK) — chưa có hệ thống chấm công/tiêu hao NVL thật
  // theo từng ca sản xuất, nên sinh lệch % ổn định (theo mã đơn) quanh định
  // mức (getOrderCost), thiên về hao hụt dương (thực tế thường cao hơn định
  // mức) để trang báo cáo có dữ liệu "hao hụt" minh hoạ. Chỉ có giá trị với
  // đơn đã bắt đầu sản xuất trở lên (in_progress/completed).
  async getActualCost(order) {
    if (!order || !["in_progress", "completed"].includes(order.status)) return null;
    const standard = await this.getOrderCost(order);
    if (standard === null) return null;
    const h = this._hashStr(order.code);
    const variancePct = -5 + (h % 30); // -5% .. +24%
    return Math.round(standard * (1 + variancePct / 100));
  },

  productionOrders: [],
  processLogs: [],

  async loadProductionOrders() {
    try {
      const [ordersData, eventsData] = await Promise.all([
        this._api("/api/production-orders"),
        this._api("/api/production-orders/events"),
      ]);
      this.productionOrders = ordersData.orders || [];
      this.processLogs = eventsData.events || [];
    } catch (e) {
      console.error("loadProductionOrders failed:", e);
      this.productionOrders = [];
      this.processLogs = [];
    }
    return this.productionOrders;
  },

  getOrderById(id) {
    return this.productionOrders.find((o) => o.id === Number(id));
  },

  getProcessLog(orderId) {
    return this.processLogs
      .filter((l) => l.orderId === Number(orderId))
      .sort((a, b) => new Date(a.ts) - new Date(b.ts));
  },

  // Vẫn được addProcessEvent() dùng (Phase 3 QC-03 sẽ cho "Ghi sự kiện" một
  // backend thật riêng — chưa đổi trong phase này).
  _saveProductionOrders() {
    Helpers.save("productionOrders", this.productionOrders);
    Helpers.save("productionOrderLogs", this.processLogs);
  },

  async createOrder(data) {
    const res = await this._api("/api/production-orders", {
      method: "POST",
      body: JSON.stringify({
        productCode: data.productCode,
        productName: data.productName,
        quantity: data.quantity,
        unit: data.unit || "cái",
        customerName: data.customerName || "",
        notes: data.notes || "",
      }),
    });
    await this.loadProductionOrders();
    return this.getOrderById(res.id);
  },

  async updateOrder(id, patch) {
    await this._api(`/api/production-orders/${id}`, {
      method: "PUT",
      body: JSON.stringify({
        productCode: patch.productCode,
        productName: patch.productName,
        quantity: patch.quantity,
        unit: patch.unit || "cái",
        customerName: patch.customerName || "",
        notes: patch.notes || "",
      }),
    });
    await this.loadProductionOrders();
    return this.getOrderById(id);
  },

  async transitionOrder(id, newStatus, note) {
    // Store._api() throws on {success:false} (e.g. the backend's 409
    // invalid-transition response) — router.js's existing catch already
    // relies on this. Stock increment on completion now happens
    // server-side, atomically, inside this same request.
    await this._api(`/api/production-orders/${id}/transition`, {
      method: "POST",
      body: JSON.stringify({ status: newStatus, note: note || "" }),
    });
    await this.loadProductionOrders();
    return this.getOrderById(id);
  },

  async deleteOrder(id) {
    await this._api(`/api/production-orders/${id}`, { method: "DELETE" });
    this.productionOrders = this.productionOrders.filter((o) => o.id !== Number(id));
  },

  // --- Material Batches + Traceability (MOCK — localStorage, đứng thay
  // /api/material-batches + /trace thật. San Xuat chưa có bảng lô NVL/kiểm
  // định thật (xem ghi chú trong routes/n8n_api.py) — manuf_material_batch_
  // intake.json và manuf_lab_test_gate.json chỉ ghi automation_events, chưa
  // có dữ liệu nghiệp vụ. traceBatch() suy ra "lô này dùng cho đơn nào" từ
  // chính BOM/đơn hàng mock đã có (khớp materialCode), không cần bảng liên
  // kết riêng — khi có API thật, đổi thân các hàm này sang gọi Store._api().) ---
  QC_STATUSES: {
    pending: { label: "Chờ kiểm định", badge: "orange", icon: "fa-flask-vial" },
    passed:  { label: "Đạt",           badge: "green",  icon: "fa-check" },
    failed:  { label: "Không đạt",     badge: "red",    icon: "fa-xmark" },
  },

  materialBatches: [],

  _seedMaterialBatches() {
    const pool = this._MOCK_MATERIALS;
    const sample = [
      { mat: pool[0], supplierName: "Dệt May Thành Công",  quantity: 800,  qcStatus: "passed",  daysAgo: 20, expiresInDays: 160 },
      { mat: pool[1], supplierName: "Chỉ May Phú Cường",   quantity: 300,  qcStatus: "passed",  daysAgo: 14, expiresInDays: 300 },
      { mat: pool[2], supplierName: "Nhựa Việt Thắng",     quantity: 5000, qcStatus: "failed",  daysAgo: 8,  expiresInDays: 200, qcNote: "Độ dày không đạt tiêu chuẩn, trả lại NCC" },
      { mat: pool[4], supplierName: "Bao Bì Sài Gòn",      quantity: 2000, qcStatus: "passed",  daysAgo: 3,  expiresInDays: 8 },
      // Các lô dưới đây đang "Chờ kiểm định" — để bạn thử luồng QC (vào
      // trang Kiểm định chất lượng, bấm "Nhập kết quả" cho từng lô).
      { mat: pool[5], supplierName: "Hoá Chất An Phát",    quantity: 150,  qcStatus: "pending", daysAgo: 2,  expiresInDays: 25 },
      { mat: pool[3], supplierName: "In Ấn Hồng Hà",       quantity: 10000, qcStatus: "pending", daysAgo: 1,  expiresInDays: 250 },
      { mat: pool[6], supplierName: "Khoá Kéo Nam Tiến",   quantity: 4000, qcStatus: "pending", daysAgo: 0,  expiresInDays: 180 },
      { mat: pool[0], supplierName: "Dệt May Thành Công",  quantity: 400,  qcStatus: "pending", daysAgo: 0,  expiresInDays: 170 },
      { mat: pool[1], supplierName: "Chỉ May Phú Cường",   quantity: 50,   qcStatus: "failed",  daysAgo: 5,  expiresInDays: 2, qcNote: "Lô ẩm mốc, gần hết hạn — không dùng được" },
    ];
    return sample.map((s, i) => {
      const receivedAt = new Date(Date.now() - s.daysAgo * 86400000).toISOString();
      const expiryDate = new Date(Date.now() + s.expiresInDays * 86400000).toISOString().slice(0, 10);
      return {
        id: i + 1,
        code: `LO-${2000 + i}`,
        materialCode: s.mat.code,
        materialName: s.mat.name,
        unit: s.mat.unit,
        supplierName: s.supplierName,
        quantity: s.quantity,
        receivedAt,
        expiryDate,
        qcStatus: s.qcStatus,
        qcNote: s.qcNote || "",
        notes: "",
      };
    });
  },

  loadMaterialBatches() {
    let batches = Helpers.load("materialBatches", null);
    if (!batches || !Array.isArray(batches) || !batches.length) {
      batches = this._seedMaterialBatches();
      Helpers.save("materialBatches", batches);
    }
    this.materialBatches = batches;
    return this.materialBatches;
  },

  _saveMaterialBatches() {
    Helpers.save("materialBatches", this.materialBatches);
  },

  getBatchById(id) {
    return this.materialBatches.find((b) => b.id === Number(id));
  },

  _nextBatchId() {
    return this.materialBatches.reduce((max, b) => Math.max(max, b.id), 0) + 1;
  },

  createBatch(data) {
    const id = this._nextBatchId();
    const mat = this._MOCK_MATERIALS.find((m) => m.code === data.materialCode);
    const batch = {
      id,
      code: `LO-${2000 + id}`,
      materialCode: data.materialCode,
      materialName: mat ? mat.name : data.materialCode,
      unit: mat ? mat.unit : data.unit || "cái",
      supplierName: data.supplierName || "",
      quantity: Number(data.quantity) || 0,
      receivedAt: new Date().toISOString(),
      expiryDate: data.expiryDate || "",
      qcStatus: "pending",
      qcNote: "",
      notes: data.notes || "",
    };
    this.materialBatches.unshift(batch);
    this._saveMaterialBatches();
    return batch;
  },

  setBatchQC(id, qcStatus, qcNote) {
    const batch = this.getBatchById(id);
    if (!batch) throw new Error("Không tìm thấy lô nguyên liệu");
    if (!this.QC_STATUSES[qcStatus]) throw new Error("Trạng thái QC không hợp lệ");
    batch.qcStatus = qcStatus;
    batch.qcNote = qcNote || "";
    this._saveMaterialBatches();
    return batch;
  },

  deleteBatch(id) {
    this.materialBatches = this.materialBatches.filter((b) => b.id !== Number(id));
    this._saveMaterialBatches();
  },

  // Nạp lại dữ liệu mẫu — xoá hết lô hiện tại (kể cả lô người dùng tự
  // thêm) và sinh lại bộ mẫu mới nhất từ _seedMaterialBatches(). Dùng khi
  // trình duyệt đã lưu sẵn 1 bộ mẫu cũ từ trước và cần thấy bộ mẫu mới.
  resetMaterialBatchesSeed() {
    this.materialBatches = this._seedMaterialBatches();
    this._saveMaterialBatches();
    return this.materialBatches;
  },

  expiryInfo(expiryDate) {
    if (!expiryDate) return { label: "—", badge: "gray" };
    const days = Math.ceil((new Date(expiryDate) - new Date()) / 86400000);
    if (days < 0) return { label: "Hết hạn", badge: "red", days };
    if (days <= 14) return { label: `Còn ${days} ngày`, badge: "orange", days };
    return { label: `Còn ${days} ngày`, badge: "green", days };
  },

  // Mock cho GET /api/material-batches/expiring?days=7 — lô sắp/đã hết hạn,
  // sắp xếp gấp nhất lên đầu (kể cả đã hết hạn, days < 0).
  getExpiringBatches(days = 7) {
    return this.materialBatches
      .filter((b) => b.expiryDate)
      .map((b) => ({ batch: b, info: this.expiryInfo(b.expiryDate) }))
      .filter((x) => x.info.days <= days)
      .sort((a, b) => a.info.days - b.info.days);
  },

  // Mock cho GET /trace?batchId=... — lô này đã dùng cho đơn sản xuất nào
  // (suy ra từ BOM của sản phẩm mỗi đơn có chứa đúng materialCode của lô),
  // và đơn nào trong số đó đã ra thành phẩm (status = completed).
  async traceBatch(id) {
    const batch = this.getBatchById(id);
    if (!batch) return null;
    const withLines = await Promise.all(
      this.productionOrders.map(async (o) => ({ o, lines: await this.getBOMForProduct(o.productCode) }))
    );
    const consumingOrders = withLines
      .filter(({ lines }) => lines.some((m) => m.code === batch.materialCode))
      .map(({ o }) => ({ order: o, isFinishedGoods: o.status === "completed" }))
      .sort((a, b) => new Date(b.order.createdAt) - new Date(a.order.createdAt));
    return { batch, consumingOrders };
  },

  // --- Warehouses (MOCK — localStorage. ANSER's real products table has one
  // flat stock_quantity, no warehouse/location dimension — WAREHOUSES/
  // warehouseLocations are fixed reference data here; warehouseStock is a
  // deterministic split of each product's REAL stock across locations, so
  // totals stay consistent with the real /api/products stock_quantity.) ---
  WAREHOUSES: [
    { id: 1, code: "KHO-HN", name: "Kho Hà Nội", address: "Khu CN Quang Minh, Mê Linh, Hà Nội" },
    { id: 2, code: "KHO-HCM", name: "Kho Hồ Chí Minh", address: "KCN Tân Bình, Q. Tân Phú, TP.HCM" },
    { id: 3, code: "KHO-DN", name: "Kho Đà Nẵng", address: "KCN Hoà Khánh, Q. Liên Chiểu, Đà Nẵng" },
  ],

  warehouseLocations: [
    { id: 101, warehouseId: 1, code: "A1", name: "Khu A1 - Kệ 1" },
    { id: 102, warehouseId: 1, code: "A2", name: "Khu A2 - Kệ 2" },
    { id: 103, warehouseId: 1, code: "B1", name: "Khu B1 - Kệ 1" },
    { id: 201, warehouseId: 2, code: "A1", name: "Khu A1 - Kệ 1" },
    { id: 202, warehouseId: 2, code: "A2", name: "Khu A2 - Kệ 2" },
    { id: 203, warehouseId: 2, code: "B1", name: "Khu B1 - Kệ 1" },
    { id: 301, warehouseId: 3, code: "A1", name: "Khu A1 - Kệ 1" },
    { id: 302, warehouseId: 3, code: "B1", name: "Khu B1 - Kệ 1" },
  ],

  getWarehouseById(id) {
    return this.WAREHOUSES.find((w) => w.id === Number(id));
  },

  getLocationById(id) {
    return this.warehouseLocations.find((l) => l.id === Number(id));
  },

  getLocationsForWarehouse(warehouseId) {
    return this.warehouseLocations.filter((l) => l.warehouseId === Number(warehouseId));
  },

  // Chia đều total thành n phần nguyên, tổng luôn đúng bằng total.
  _splitQuantity(total, n) {
    const base = Math.floor(total / n);
    let remainder = total - base * n;
    const parts = [];
    for (let i = 0; i < n; i++) {
      parts.push(base + (remainder > 0 ? 1 : 0));
      if (remainder > 0) remainder--;
    }
    return parts;
  },

  warehouseStock: [],

  _seedWarehouseStock() {
    const locs = this.warehouseLocations;
    const stock = [];
    let id = 1;
    this.products.forEach((p) => {
      if (!p.stock || p.stock <= 0) return;
      const h = this._hashStr(p.code);
      const n = 1 + (h % Math.min(3, locs.length));
      const chosen = [];
      const usedIds = new Set();
      for (let i = 0; i < locs.length && chosen.length < n; i++) {
        const loc = locs[(h + i * 5) % locs.length];
        if (!usedIds.has(loc.id)) { usedIds.add(loc.id); chosen.push(loc); }
      }
      const parts = this._splitQuantity(p.stock, chosen.length);
      chosen.forEach((loc, i) => {
        if (parts[i] <= 0) return;
        stock.push({
          id: id++, warehouseId: loc.warehouseId, locationId: loc.id,
          productCode: p.code, productName: p.name, unit: p.unit, quantity: parts[i],
        });
      });
    });
    return stock;
  },

  loadWarehouseStock() {
    let stock = Helpers.load("warehouseStock", null);
    if (!stock || !Array.isArray(stock) || !stock.length) {
      stock = this._seedWarehouseStock();
      Helpers.save("warehouseStock", stock);
    }
    this.warehouseStock = stock;
    this.stockCountHistory = Helpers.load("stockCountHistory", []) || [];
    this.stockTransferHistory = Helpers.load("stockTransferHistory", []) || [];
    return this.warehouseStock;
  },

  resetWarehouseStockSeed() {
    this.warehouseStock = this._seedWarehouseStock();
    this.stockCountHistory = [];
    this.stockTransferHistory = [];
    this._saveWarehouseStock();
    return this.warehouseStock;
  },

  _saveWarehouseStock() {
    Helpers.save("warehouseStock", this.warehouseStock);
    Helpers.save("stockCountHistory", this.stockCountHistory);
    Helpers.save("stockTransferHistory", this.stockTransferHistory);
  },

  getWarehouseSummary() {
    return this.WAREHOUSES.map((w) => {
      const rows = this.warehouseStock.filter((s) => s.warehouseId === w.id);
      return {
        warehouse: w,
        locationCount: this.getLocationsForWarehouse(w.id).length,
        skuCount: new Set(rows.map((r) => r.productCode)).size,
        totalQty: rows.reduce((sum, r) => sum + r.quantity, 0),
      };
    });
  },

  getStockForWarehouse(warehouseId) {
    return this.warehouseStock
      .filter((s) => s.warehouseId === Number(warehouseId))
      .map((s) => ({ ...s, location: this.getLocationById(s.locationId) }))
      .sort((a, b) => (a.location?.code || "").localeCompare(b.location?.code || "") || a.productName.localeCompare(b.productName));
  },

  _findStockRow(warehouseId, locationId, productCode) {
    return this.warehouseStock.find((s) =>
      s.warehouseId === Number(warehouseId) && s.locationId === Number(locationId) && s.productCode === productCode);
  },

  transferStock({ productCode, fromWarehouseId, fromLocationId, toWarehouseId, toLocationId, quantity, note }) {
    const qty = Number(quantity) || 0;
    if (qty <= 0) throw new Error("Số lượng chuyển phải lớn hơn 0");
    if (fromWarehouseId === toWarehouseId && fromLocationId === toLocationId) {
      throw new Error("Vị trí nguồn và đích phải khác nhau");
    }
    const source = this._findStockRow(fromWarehouseId, fromLocationId, productCode);
    if (!source || source.quantity < qty) {
      throw new Error(`Không đủ tồn kho tại vị trí nguồn (còn ${source ? source.quantity : 0})`);
    }
    source.quantity -= qty;
    this.warehouseStock = this.warehouseStock.filter((s) => s.quantity > 0 || s !== source);

    let dest = this._findStockRow(toWarehouseId, toLocationId, productCode);
    if (dest) {
      dest.quantity += qty;
    } else {
      const nextId = this.warehouseStock.reduce((max, s) => Math.max(max, s.id), 0) + 1;
      this.warehouseStock.push({
        id: nextId, warehouseId: Number(toWarehouseId), locationId: Number(toLocationId),
        productCode, productName: source.productName, unit: source.unit, quantity: qty,
      });
    }

    const entry = {
      id: Date.now(), productCode, productName: source.productName, quantity: qty,
      fromWarehouseId: Number(fromWarehouseId), fromLocationId: Number(fromLocationId),
      toWarehouseId: Number(toWarehouseId), toLocationId: Number(toLocationId),
      transferredAt: new Date().toISOString(), note: note || "",
    };
    this.stockTransferHistory.unshift(entry);
    this._saveWarehouseStock();
    return entry;
  },

  recordStockCount({ warehouseId, locationId, productCode, countedQty, note }) {
    const counted = Number(countedQty);
    if (isNaN(counted) || counted < 0) throw new Error("Số lượng đếm không hợp lệ");
    const row = this._findStockRow(warehouseId, locationId, productCode);
    const systemQty = row ? row.quantity : 0;
    const diff = counted - systemQty;

    if (row) {
      row.quantity = counted;
      if (row.quantity <= 0) this.warehouseStock = this.warehouseStock.filter((s) => s !== row);
    } else if (counted > 0) {
      const product = this.products.find((p) => p.code === productCode);
      const nextId = this.warehouseStock.reduce((max, s) => Math.max(max, s.id), 0) + 1;
      this.warehouseStock.push({
        id: nextId, warehouseId: Number(warehouseId), locationId: Number(locationId),
        productCode, productName: product ? product.name : productCode, unit: product ? product.unit : "cái", quantity: counted,
      });
    }

    const entry = {
      id: Date.now(), warehouseId: Number(warehouseId), locationId: Number(locationId),
      productCode, systemQty, countedQty: counted, diff,
      countedAt: new Date().toISOString(), note: note || "",
    };
    this.stockCountHistory.unshift(entry);
    this._saveWarehouseStock();
    return entry;
  },

  // --- Suppliers (real API: /api/suppliers*, backed by
  // routes/supplier_routes.py). Function bodies below call Store._api();
  // signatures are unchanged so callers/HTML need no changes. ---
  suppliers: [],

  async loadSuppliers() {
    try {
      const data = await this._api("/api/suppliers");
      this.suppliers = data.suppliers || [];
    } catch (e) {
      console.error("loadSuppliers failed:", e);
      this.suppliers = [];
    }
    return this.suppliers;
  },

  async createSupplier(data) {
    await this._api("/api/suppliers", {
      method: "POST",
      body: JSON.stringify({
        name: data.name,
        contact: data.contact || "",
        phone: data.phone || "",
        email: data.email || "",
        address: data.address || "",
        notes: data.notes || "",
      }),
    });
    await this.loadSuppliers();
  },

  async updateSupplier(id, patch) {
    await this._api(`/api/suppliers/${id}`, {
      method: "PUT",
      body: JSON.stringify({
        name: patch.name,
        contact: patch.contact || "",
        phone: patch.phone || "",
        email: patch.email || "",
        address: patch.address || "",
        notes: patch.notes || "",
      }),
    });
    await this.loadSuppliers();
  },

  async deleteSupplier(id) {
    await this._api(`/api/suppliers/${id}`, { method: "DELETE" });
    this.suppliers = this.suppliers.filter((s) => s.id !== Number(id));
  },

  getSupplierById(id) {
    return this.suppliers.find((s) => s.id === Number(id));
  },

  // GET /api/suppliers/<id>/batches — lịch sử lô NVL thật đã nhập từ 1 NCC,
  // qua FK material_batches.supplier_id (không còn khớp theo tên chuỗi tự do).
  async getSupplierBatches(supplierId) {
    const res = await this._api(`/api/suppliers/${supplierId}/batches`);
    return res.batches || [];
  },

  async getSupplierSummary() {
    return Promise.all(
      this.suppliers.map(async (s) => {
        const batches = await this.getSupplierBatches(s.id);
        return {
          supplier: s,
          batchCount: batches.length,
          lastReceivedAt: batches[0]?.receivedAt || null,
        };
      })
    );
  },

  // --- Invoices (MOCK — localStorage. Không có backend OCR/Excel-parser
  // thật (xem mock brain/upload endpoints trong routes/n8n_api.py) — thay
  // vì đọc file .xlsx thật, parseExcelMock() sinh dữ liệu dòng hàng giả lập
  // ổn định theo tên+kích thước file, kèm 1 vài dòng lỗi có chủ đích để demo
  // luồng validate trước khi nhập. fileUrl (blob: URL) chỉ sống trong phiên
  // trình duyệt hiện tại — không có backend để lưu file thật.) ---
  invoices: [],

  parseExcelMock(file) {
    const h = this._hashStr((file?.name || "invoice") + "_" + (file?.size || 0));
    const rowCount = 5 + (h % 4); // 5-8 dòng
    const rows = [];
    for (let i = 0; i < rowCount; i++) {
      const seed = h + i * 37;
      const useKnownProduct = this.products.length && seed % 3 !== 0;
      const product = useKnownProduct ? this.products[seed % this.products.length] : null;
      let quantity = 5 + (seed % 95);
      let unitPrice = 10000 + (seed % 40) * 5000;
      const productCode = product ? product.code : `SP-${100 + (seed % 900)}`;
      let productName = product ? product.name : "";
      let error = null;

      const errType = seed % 6;
      if (errType === 0) { quantity = 0; error = "Số lượng phải lớn hơn 0"; }
      else if (errType === 1) { unitPrice = 0; error = "Thiếu đơn giá"; }
      else if (errType === 2 && !product) { error = "Thiếu tên sản phẩm"; }
      else if (errType === 3 && !product) { error = `Mã sản phẩm "${productCode}" không tồn tại trong hệ thống`; }

      rows.push({ row: i + 2, productCode, productName, quantity, unitPrice, error });
    }
    return rows;
  },

  _seedInvoices() {
    return [
      {
        id: 1, code: "HD-9001", fileName: "hoa_don_NVL_thang6.xlsx", fileSize: 24500,
        uploadedAt: new Date(Date.now() - 6 * 86400000).toISOString(), status: "imported", fileUrl: null,
        lineItems: [
          { row: 2, productCode: "NVL-001", productName: "Vải cotton", quantity: 200, unitPrice: 45000, error: null },
          { row: 3, productCode: "NVL-002", productName: "Chỉ may", quantity: 80, unitPrice: 8000, error: null },
        ],
      },
      {
        id: 2, code: "HD-9002", fileName: "don_hang_bao_bi.xlsx", fileSize: 18200,
        uploadedAt: new Date(Date.now() - 2 * 86400000).toISOString(), status: "imported", fileUrl: null,
        lineItems: [
          { row: 2, productCode: "NVL-005", productName: "Bao bì đóng gói", quantity: 500, unitPrice: 2500, error: null },
        ],
      },
    ];
  },

  loadInvoices() {
    let invoices = Helpers.load("invoices", null);
    if (!invoices || !Array.isArray(invoices) || !invoices.length) {
      invoices = this._seedInvoices();
      Helpers.save("invoices", invoices);
    }
    this.invoices = invoices;
    return this.invoices;
  },

  _saveInvoices() {
    // fileUrl (blob: URL) không serialize bền qua reload — chỉ lưu phần còn lại.
    const persistable = this.invoices.map(({ fileUrl, ...rest }) => rest);
    Helpers.save("invoices", persistable);
  },

  _nextInvoiceId() {
    return this.invoices.reduce((max, i) => Math.max(max, i.id), 0) + 1;
  },

  createInvoice({ fileName, fileSize, lineItems, fileUrl }) {
    if (!lineItems || !lineItems.length) throw new Error("Không có dòng hàng hợp lệ để nhập");
    const id = this._nextInvoiceId();
    const invoice = {
      id, code: `HD-${9000 + id}`, fileName, fileSize,
      uploadedAt: new Date().toISOString(), status: "imported",
      lineItems, fileUrl: fileUrl || null,
    };
    this.invoices.unshift(invoice);
    this._saveInvoices();
    return invoice;
  },

  deleteInvoice(id) {
    this.invoices = this.invoices.filter((i) => i.id !== Number(id));
    this._saveInvoices();
  },

  // --- AI Chat messages (persisted in localStorage — the widget itself is
  // a local pattern-matched assistant, not a real LLM call) ---
  chatMessages: [],
  loadChatMessages() {
    const stored = Helpers.load("chatMessages", null);
    if (stored && Array.isArray(stored) && stored.length) {
      this.chatMessages = stored;
    } else {
      this.chatMessages = [
        {
          id: 1,
          role: "bot",
          text: "Xin chào! Tôi là trợ lý AI của ANSER Sản xuất. Bạn có thể hỏi tôi về tồn kho, hoặc quy trình n8n đang chạy.",
          ts: Date.now(),
        },
      ];
      this.saveChatMessages();
    }
    return this.chatMessages;
  },
  saveChatMessages() {
    Helpers.save("chatMessages", this.chatMessages);
  },
  addChatMessage(msg) {
    msg.id = Date.now() + Math.floor(Math.random() * 1000);
    msg.ts = msg.ts || Date.now();
    this.chatMessages.push(msg);
    this.saveChatMessages();
    return msg;
  },
  clearChatMessages() {
    this.chatMessages = [];
    this.saveChatMessages();
  },

};

// Expose to window for inline handlers
window.Store = Store;
