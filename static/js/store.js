/**
 * store.js — Data store, wired to the real ANSER backend for products,
 * imports, exports, customers and dashboard stats.
 *
 * Rules & Logs (automation) stay on localStorage sample data — ANSER's
 * backend only supports two fixed automation types (low_stock, scheduled),
 * not the free-form rule model this UI shows, so we don't fake it as real.
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

  // ======================================================================
  // Rules (SAMPLE DATA — persisted to localStorage only). ANSER's backend
  // (/api/automations, table se_automations) only supports two fixed
  // rule types (low_stock, scheduled restock) with no run-history log,
  // so it can't back this free-form trigger/action/channel UI honestly.
  // ======================================================================
  rules: [],
  loadRules() {
    const stored = Helpers.load("rules", null);
    if (stored && Array.isArray(stored) && stored.length) {
      this.rules = stored;
    } else {
      this.rules = [
        { id: 1, icon: "fa-solid fa-triangle-exclamation", color: "orange", title: "Cảnh báo NVL sắp hết", status: "Đang chạy", freq: "Mỗi 30 phút", desc: "Khi tồn kho NVL < 30% ngưỡng tối thiểu, gửi cảnh báo tới quản lý kho.", trigger: "Tồn kho < 30% min", action: "Gửi email + Zalo OA", last: "12 phút trước", total: 1247, success: "99.4%", checked: true, channel: "email+zalo", threshold: 30 },
        { id: 2, icon: "fa-solid fa-bug", color: "red", title: "Lỗi nghiêm trọng → QC leader", status: "Đang chạy", freq: "Realtime", desc: 'Khi QC ghi nhận lỗi mức "Nghiêm trọng", tự động tạo ticket và ping QC leader.', trigger: "Mức lỗi = Nghiêm trọng", action: "Tạo ticket + Ping Zalo", last: "2 giờ trước", total: 23, success: "100%", checked: true, channel: "zalo", threshold: 1 },
        { id: 3, icon: "fa-solid fa-box-open", color: "blue", title: "Tự xuất kho khi đơn xác nhận", status: "Đang chạy", freq: "Realtime", desc: 'Khi đơn hàng chuyển sang "Đã xác nhận", tự tạo phiếu xuất kho và trừ tồn thành phẩm.', trigger: "Trạng thái đơn = Đã xác nhận", action: "Tạo phiếu xuất", last: "5 phút trước", total: 328, success: "98.8%", checked: true, channel: "internal", threshold: 0 },
        { id: 4, icon: "fa-solid fa-arrow-trend-up", color: "green", title: "Báo cáo doanh thu cuối ngày", status: "Tạm dừng", freq: "Hằng ngày 20:00", desc: "Tự tổng hợp doanh thu, đơn hàng, lợi nhuận trong ngày gửi email cho Ban giám đốc.", trigger: "20:00 hằng ngày", action: "Tạo PDF + gửi email", last: "3 ngày trước", total: 87, success: null, checked: false, channel: "email", threshold: 0 },
        { id: 5, icon: "fa-solid fa-truck", color: "purple", title: "Đặt hàng tự động khi hết NVL", status: "Đang chạy", freq: "Hằng ngày 08:00", desc: "Khi NVL về 0, tự động tạo đơn đặt hàng nhà cung cấp theo định mức tồn kho an toàn.", trigger: "Tồn kho = 0", action: "Tạo đơn mua + Email NCC", last: "1 ngày trước", total: 42, success: "97.6%", checked: true, channel: "email", threshold: 0 },
        { id: 6, icon: "fa-solid fa-clock", color: "orange", title: "Cảnh báo hạn sử dụng thực phẩm", status: "Đang chạy", freq: "Hằng ngày 07:00", desc: "Thực phẩm còn < 7 ngày HSD sẽ tự động cảnh báo để xả hàng hoặc giảm giá.", trigger: "HSD < 7 ngày", action: "Gửi email quản lý", last: "6 giờ trước", total: 156, success: "98.7%", checked: true, channel: "email", threshold: 7 },
      ];
      Helpers.save("rules", this.rules);
    }
    return this.rules;
  },
  saveRules() {
    Helpers.save("rules", this.rules);
  },
  addRule(r) {
    r.id = Math.max(0, ...this.rules.map((x) => x.id || 0)) + 1;
    if (!r.total) r.total = 0;
    if (r.checked === undefined) r.checked = true;
    this.rules.push(r);
    this.saveRules();
    return r;
  },
  updateRule(id, patch) {
    const i = this.rules.findIndex((r) => r.id === id);
    if (i === -1) return null;
    this.rules[i] = { ...this.rules[i], ...patch };
    this.saveRules();
    return this.rules[i];
  },
  deleteRule(id) {
    this.rules = this.rules.filter((r) => r.id !== id);
    this.saveRules();
  },

  // --- Logs (SAMPLE DATA, same reason as rules above) ---
  logs: [],
  loadLogs() {
    const stored = Helpers.load("logs", null);
    if (stored && Array.isArray(stored) && stored.length) {
      this.logs = stored;
    } else {
      this.logs = this._generateSeedLogs();
      Helpers.save("logs", this.logs);
    }
    return this.logs;
  },
  saveLogs() {
    Helpers.save("logs", this.logs);
  },
  _generateSeedLogs() {
    const ruleTitles = [
      "Cảnh báo NVL sắp hết",
      "Tự xuất kho khi đơn xác nhận",
      "Lỗi nghiêm trọng → QC leader",
      "Báo cáo doanh thu cuối ngày",
      "Đặt hàng tự động khi hết NVL",
      "Cảnh báo hạn sử dụng thực phẩm",
    ];
    const messages = {
      success: [
        (r) => `Đã tạo phiếu xuất PX-2024-${Math.floor(Math.random() * 9000 + 1000)} cho đơn DH-2024-${Math.floor(Math.random() * 9000 + 1000)} (Vỏ hộp kim loại 100x60 × ${Math.floor(Math.random() * 50 + 10)} cái)`,
        (r) => `Đã gửi cảnh báo Zalo OA tới 3 quản lý kho: NVL003 Bulong M8x40 còn 320/1000 con`,
        (r) => `Đã gửi email báo cáo doanh thu ngày ${Helpers.formatDate(new Date())} tới 5 giám đốc`,
        (r) => `Đã tạo đơn mua hàng PO-2024-${Math.floor(Math.random() * 9000 + 1000)} gửi NCC Hòa Phát (Tôn cuộn 0.5mm × 2000kg)`,
        (r) => `Đã gửi email cảnh báo 3 thực phẩm sắp hết HSD (Sữa tươi, Mật ong, Bánh kẹo)`,
        (r) => `Rule kích hoạt thành công, đã xử lý trong ${(Math.random() * 2).toFixed(1)}s`,
      ],
      failed: [
        (r) => "Gửi email thất bại: SMTP timeout sau 30s (smtp.gmail.com:587)",
        (r) => "Zalo OA API trả về 401: Token hết hạn — cần refresh credential.",
        (r) => "Webhook trả về 500: Internal Server Error từ endpoint /api/orders",
        (r) => "Database timeout: query kiểm tra tồn kho > 10s",
        (r) => "Lỗi xác thực: NCC email không hợp lệ (po-2024-1234@invalid)",
      ],
      skipped: [
        (r) => 'Rule đang ở trạng thái "Tạm dừng" — bỏ qua lịch chạy.',
        (r) => "Điều kiện trigger không thoả mãn (tồn kho > ngưỡng) — bỏ qua.",
        (r) => "Đã chạy gần đây (cooldown 5 phút) — bỏ qua lần này.",
        (r) => "Trùng lịch với rule #2 — bỏ qua để tránh gửi trùng.",
      ],
    };
    const statuses = ["success", "success", "success", "success", "failed", "failed", "success", "skipped", "success", "success", "failed", "success"];
    const logs = [];
    const now = Date.now();
    for (let i = 0; i < 30; i++) {
      const status = statuses[i % statuses.length];
      const ruleTitle = ruleTitles[i % ruleTitles.length];
      const ts = new Date(now - i * 1800000 - Math.random() * 1800000);
      const msgFns = messages[status];
      const msg = msgFns[i % msgFns.length](ruleTitle);
      const time = `${String(ts.getHours()).padStart(2, "0")}:${String(ts.getMinutes()).padStart(2, "0")} · ${i === 0 ? "hôm nay" : i < 8 ? "hôm nay" : "hôm qua"}`;
      const meta = status === "failed"
        ? `${ruleTitle} · ${(Math.random() * 2).toFixed(1)}s`
        : `${ruleTitle} · ${(Math.random() * 1.5 + 0.3).toFixed(1)}s`;
      logs.push({ id: Date.now() - i, status, rule: ruleTitle, time, msg, meta, ts: ts.getTime() });
    }
    return logs;
  },
  addLog(log) {
    log.id = Date.now() + Math.floor(Math.random() * 1000);
    log.ts = log.ts || Date.now();
    this.logs.unshift(log);
    if (this.logs.length > 200) this.logs = this.logs.slice(0, 200);
    this.saveLogs();
    return log;
  },
};

// Expose to window for inline handlers
window.Store = Store;
