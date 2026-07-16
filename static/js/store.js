/**
 * store.js — Data store, wired to the real ANSER backend for products,
 * imports, exports, customers and dashboard stats.
 *
 * Automation (rules/logs) is not stored here — automation-rules.html and
 * automation-logs.html read directly from the real n8n API (/api/n8n/*).
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
