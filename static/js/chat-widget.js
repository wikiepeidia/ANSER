/**
 * chat-widget.js — Floating AI chat assistant (bottom-right, all pages)
 *
 * Loaded once in base.html (persistent shell), unlike page scripts which are
 * re-injected on every navigation. Answers are pattern-matched against real
 * data (Store.products, /api/n8n/workflows, /api/n8n/executions) — this is
 * a local mock, not a real LLM call.
 */

const ChatWidget = {
  els: {},

  init() {
    this.els = {
      widget: document.getElementById("aiChatWidget"),
      toggle: document.getElementById("aiChatToggle"),
      toggleIcon: document.getElementById("aiChatToggleIcon"),
      window: document.getElementById("aiChatWindow"),
      close: document.getElementById("aiChatClose"),
      messages: document.getElementById("aiChatMessages"),
      input: document.getElementById("aiChatInput"),
      send: document.getElementById("aiChatSend"),
      suggestions: document.getElementById("aiChatSuggestions"),
    };
    if (!this.els.widget) return;

    this.els.toggle.addEventListener("click", () => this.toggleOpen());
    this.els.close.addEventListener("click", () => this.close());
    this.els.send.addEventListener("click", () => this.send(this.els.input.value));
    this.els.input.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        this.send(this.els.input.value);
      }
    });
    this.els.input.addEventListener("input", () => {
      this.els.input.style.height = "auto";
      this.els.input.style.height = Math.min(this.els.input.scrollHeight, 90) + "px";
    });
    this.els.suggestions.querySelectorAll(".ai-chat-suggestion").forEach((btn) => {
      btn.addEventListener("click", () => this.send(btn.dataset.q));
    });
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape") this.close();
    });

    this.render();
  },

  open() {
    this.els.window.hidden = false;
    this.els.toggleIcon.className = "fa-solid fa-xmark";
    this.render();
    setTimeout(() => this.els.input.focus(), 50);
  },

  close() {
    this.els.window.hidden = true;
    this.els.toggleIcon.className = "fa-solid fa-robot";
  },

  toggleOpen() {
    if (this.els.window.hidden) this.open();
    else this.close();
  },

  scrollToBottom() {
    this.els.messages.scrollTop = this.els.messages.scrollHeight;
  },

  render() {
    if (!this.els.messages) return;
    this.els.messages.innerHTML = Store.chatMessages.map((m) => `
      <div class="ai-msg ai-msg--${m.role}">
        <div class="ai-msg__avatar"><i class="fa-solid ${m.role === "bot" ? "fa-robot" : "fa-user"}"></i></div>
        <div class="ai-msg__bubble">${Helpers.escapeHtml(m.text)}</div>
      </div>
    `).join("");
    this.scrollToBottom();
  },

  showTyping() {
    const div = document.createElement("div");
    div.className = "ai-msg ai-msg--bot";
    div.id = "aiChatTyping";
    div.innerHTML = `
      <div class="ai-msg__avatar"><i class="fa-solid fa-robot"></i></div>
      <div class="ai-msg__bubble"><span class="ai-chat-typing"><span></span><span></span><span></span></span></div>
    `;
    this.els.messages.appendChild(div);
    this.scrollToBottom();
  },

  hideTyping() {
    document.getElementById("aiChatTyping")?.remove();
  },

  // ---- Mock "AI" answer engine: pattern-matches the question and looks up
  // the answer from real data (Store.products, n8n API). Not a real LLM call.
  async answer(question) {
    const q = question.toLowerCase();
    const money = (n) => Helpers.formatVND(n);

    if (/(xin chào|hello|hi\b|chào)/.test(q)) {
      return "Xin chào! Bạn muốn hỏi về tồn kho hay quy trình n8n đang chạy?";
    }

    if (/hết hàng(?!.*sắp)/.test(q) || /(còn 0|out.?of.?stock)/.test(q)) {
      const out = Store.products.filter((p) => p.stock === 0);
      if (!out.length) return "Hiện không có sản phẩm nào hết hàng. 👍";
      return `Có ${out.length} sản phẩm đã hết hàng:\n` + out.map((p) => `• ${p.name} (${p.code})`).join("\n");
    }

    if (/sắp hết|tồn kho thấp|low.?stock/.test(q)) {
      const low = Store.products.filter((p) => p.stock > 0 && p.stock <= 10);
      if (!low.length) return "Không có sản phẩm nào sắp hết hàng ở thời điểm này.";
      return `Có ${low.length} sản phẩm sắp hết hàng (tồn kho ≤ 10):\n` + low.map((p) => `• ${p.name}: còn ${p.stock}`).join("\n");
    }

    if (/giá trị tồn kho|tổng giá trị kho/.test(q)) {
      // ANSER chỉ lưu 1 giá bán ở cấp sản phẩm, không có giá nhập riêng.
      const total = Store.products.reduce((s, p) => s + p.stock * p.sellPrice, 0);
      return `Tổng giá trị tồn kho hiện tại (theo giá bán): ${money(total)}, gồm ${Store.products.reduce((s, p) => s + p.stock, 0)} sản phẩm trên ${Store.products.length} mã hàng.`;
    }

    if (/tổng tồn kho|tổng số lượng/.test(q)) {
      const total = Store.products.reduce((s, p) => s + p.stock, 0);
      return `Tổng tồn kho hiện tại là ${Helpers.formatNumber(total)} sản phẩm trên ${Store.products.length} mã hàng.`;
    }

    const categoryMatch = Store.products
      .map((p) => p.category)
      .filter((c, i, arr) => c && arr.indexOf(c) === i)
      .find((c) => q.includes(c.toLowerCase()));
    if (categoryMatch && /tồn kho|còn bao nhiêu/.test(q)) {
      const items = Store.products.filter((p) => p.category === categoryMatch);
      const total = items.reduce((s, p) => s + p.stock, 0);
      return `Ngành hàng "${categoryMatch}" có ${items.length} mã sản phẩm, tổng tồn kho ${Helpers.formatNumber(total)} cái.`;
    }

    // Quy tắc (= quy trình n8n thật) đang chạy — thay cho Store.rules cũ.
    if (/(quy tắc|quy trình|rule|automation|n8n).*(đang chạy|hoạt động)|bao nhiêu quy tắc/.test(q)) {
      try {
        const r = await fetch("/api/n8n/workflows");
        const d = await r.json();
        if (!d.success) return "Không kết nối được n8n để kiểm tra quy tắc đang chạy.";
        const active = d.workflows.filter((w) => w.active);
        const paused = d.workflows.length - active.length;
        if (!active.length) return "Hiện không có quy tắc nào đang chạy.";
        return `Có ${active.length} quy tắc đang chạy, ${paused} quy tắc tạm dừng:\n` + active.map((w) => `• ${w.name}`).join("\n");
      } catch {
        return "Không kết nối được n8n để kiểm tra quy tắc đang chạy.";
      }
    }

    // Lỗi / lịch sử chạy — thay cho Store.logs cũ, đọc lịch sử chạy n8n thật.
    if (/(lỗi|thất bại|failed).*(tự động|rule|log|quy trình)|có lỗi.*không/.test(q)) {
      try {
        const r = await fetch("/api/n8n/executions?limit=20");
        const d = await r.json();
        if (!d.success) return "Không kết nối được n8n để kiểm tra lịch sử chạy.";
        const failed = d.executions.filter((e) => e.status === "error" || e.status === "crashed").slice(0, 5);
        if (!failed.length) return "Không có lỗi nào trong lịch sử chạy gần đây. 👍";
        return `Có ${failed.length} lượt lỗi gần đây:\n` + failed.map((e) => `• [${e.workflowName}] lúc ${e.startedAt ? new Date(e.startedAt).toLocaleString("vi-VN") : "?"}`).join("\n");
      } catch {
        return "Không kết nối được n8n để kiểm tra lịch sử chạy.";
      }
    }

    if (/lịch sử chạy|log gần đây/.test(q)) {
      try {
        const r = await fetch("/api/n8n/executions?limit=5");
        const d = await r.json();
        if (!d.success || !d.executions.length) return "Chưa có lượt chạy nào được ghi nhận.";
        return "5 lượt chạy gần nhất:\n" + d.executions.map((e) =>
          `• [${e.workflowName}] — ${e.status === "success" ? "Thành công" : e.status === "error" ? "Thất bại" : e.status}`
        ).join("\n");
      } catch {
        return "Không kết nối được n8n để lấy lịch sử chạy.";
      }
    }

    if (/doanh thu|lợi nhuận/.test(q)) {
      return "Số liệu doanh thu/lợi nhuận chi tiết đang ở trang Báo cáo.";
    }

    return "Tôi chưa có đủ dữ liệu để trả lời chính xác câu này. Bạn có thể hỏi về: sản phẩm sắp hết/hết hàng, giá trị tồn kho, quy tắc đang chạy, hoặc lịch sử chạy gần đây.";
  },

  async send(text) {
    text = (text || "").trim();
    if (!text) return;
    Store.addChatMessage({ role: "user", text });
    this.render();
    this.els.input.value = "";
    this.els.input.style.height = "auto";
    this.showTyping();
    const [reply] = await Promise.all([
      this.answer(text),
      new Promise((resolve) => setTimeout(resolve, 400 + Math.random() * 400)),
    ]);
    this.hideTyping();
    Store.addChatMessage({ role: "bot", text: reply });
    this.render();
  },
};

window.ChatWidget = ChatWidget;

window.addEventListener("DOMContentLoaded", () => {
  ChatWidget.init();
});
