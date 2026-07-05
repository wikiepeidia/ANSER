/**
 * store.js — Data store (products, rules, logs) with localStorage persistence
 */

const Store = {
  // --- Products (persisted) ---
  products: [],
  loadProducts() {
    const stored = Helpers.load("products", null);
    if (stored && Array.isArray(stored) && stored.length) {
      this.products = stored;
    } else {
      this.products = [
        { id: 1, code: "SP-001", name: "Laptop ASUS VivoBook 15", category: "Điện tử", stock: 50, importPrice: 15500000, sellPrice: 18900000, status: "green", statusText: "Còn hàng" },
        { id: 2, code: "SP-002", name: "Tai nghe AirPods Pro 2", category: "Điện tử", stock: 8, importPrice: 4200000, sellPrice: 5990000, status: "orange", statusText: "Sắp hết" },
        { id: 3, code: "SP-003", name: "Bàn phím cơ Keychron K2", category: "Điện tử", stock: 0, importPrice: 2800000, sellPrice: 3500000, status: "red", statusText: "Hết hàng" },
        { id: 4, code: "SP-004", name: "Áo thun nam basic", category: "Thời trang", stock: 245, importPrice: 120000, sellPrice: 250000, status: "green", statusText: "Còn hàng" },
        { id: 5, code: "SP-005", name: "Nồi cơm điện Sharp", category: "Gia dụng", stock: 32, importPrice: 890000, sellPrice: 1350000, status: "green", statusText: "Còn hàng" },
        { id: 6, code: "SP-006", name: "Quần jeans nam Slim", category: "Thời trang", stock: 5, importPrice: 350000, sellPrice: 650000, status: "orange", statusText: "Sắp hết" },
        { id: 7, code: "SP-007", name: "Chuột Logitech MX Master", category: "Điện tử", stock: 0, importPrice: 1800000, sellPrice: 2500000, status: "red", statusText: "Hết hàng" },
        { id: 8, code: "SP-008", name: "Máy lọc không khí Xiaomi", category: "Gia dụng", stock: 18, importPrice: 2100000, sellPrice: 3200000, status: "green", statusText: "Còn hàng" },
        { id: 9, code: "SP-009", name: "Bánh kẹo cao cấp", category: "Thực phẩm", stock: 3, importPrice: 85000, sellPrice: 150000, status: "orange", statusText: "Sắp hết" },
        { id: 10, code: "SP-010", name: "Sữa tươi Pasteur", category: "Thực phẩm", stock: 120, importPrice: 25000, sellPrice: 45000, status: "green", statusText: "Còn hàng" },
        { id: 11, code: "SP-011", name: "Webcam Logitech C920", category: "Điện tử", stock: 24, importPrice: 1900000, sellPrice: 2700000, status: "green", statusText: "Còn hàng" },
        { id: 12, code: "SP-012", name: "Balo laptop 15.6 inch", category: "Thời trang", stock: 67, importPrice: 280000, sellPrice: 490000, status: "green", statusText: "Còn hàng" },
        { id: 13, code: "SP-013", name: "Bếp điện từ Sunhouse", category: "Gia dụng", stock: 4, importPrice: 1200000, sellPrice: 1890000, status: "orange", statusText: "Sắp hết" },
        { id: 14, code: "SP-014", name: "Mật ong rừng 500ml", category: "Thực phẩm", stock: 88, importPrice: 180000, sellPrice: 280000, status: "green", statusText: "Còn hàng" },
        { id: 15, code: "SP-015", name: "Ổ cứng SSD 1TB", category: "Điện tử", stock: 12, importPrice: 2200000, sellPrice: 2990000, status: "green", statusText: "Còn hàng" },
      ];
      Helpers.save("products", this.products);
    }
    return this.products;
  },
  saveProducts() {
    Helpers.save("products", this.products);
  },
  addProduct(p) {
    p.id = Math.max(0, ...this.products.map((x) => x.id)) + 1;
    this.products.push(p);
    this.saveProducts();
    return p;
  },
  updateProduct(id, patch) {
    const i = this.products.findIndex((p) => p.id === id);
    if (i === -1) return null;
    this.products[i] = { ...this.products[i], ...patch };
    this.saveProducts();
    return this.products[i];
  },
  deleteProduct(id) {
    this.products = this.products.filter((p) => p.id !== id);
    this.saveProducts();
  },
  getProductById(id) {
    return this.products.find((p) => p.id === id);
  },

  // --- Rules (persisted) ---
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

  // --- Logs (persisted, auto-grow) ---
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