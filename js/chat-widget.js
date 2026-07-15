/**
 * chat-widget.js — Floating AI chat assistant (bottom-right, all pages)
 *
 * Loaded once in base.html (persistent shell), unlike page scripts which are
 * re-injected on every navigation. Answers are pattern-matched against Store
 * data (products/rules/logs) — this is a local mock, not a real LLM call.
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

  timeLabel(ts) {
    const d = new Date(ts);
    return `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
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
  // the answer from Store (products/rules/logs). Not a real LLM call.
  answer(question) {
    const q = question.toLowerCase();
    const money = (n) => Helpers.formatVND(n);

    if (/(xin chào|hello|hi\b|chào)/.test(q)) {
      return "Xin chào! Bạn muốn hỏi về tồn kho, quy tắc tự động hoá hay lịch sử chạy?";
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
      const total = Store.products.reduce((s, p) => s + p.stock * p.importPrice, 0);
      return `Tổng giá trị tồn kho hiện tại (theo giá nhập): ${money(total)}, gồm ${Store.products.reduce((s, p) => s + p.stock, 0)} sản phẩm trên ${Store.products.length} mã hàng.`;
    }

    if (/tổng tồn kho|tổng số lượng/.test(q)) {
      const total = Store.products.reduce((s, p) => s + p.stock, 0);
      return `Tổng tồn kho hiện tại là ${Helpers.formatNumber(total)} sản phẩm trên ${Store.products.length} mã hàng.`;
    }

    const categoryMatch = ["Điện tử", "Thời trang", "Gia dụng", "Thực phẩm"].find((c) => q.includes(c.toLowerCase()));
    if (categoryMatch && /tồn kho|còn bao nhiêu/.test(q)) {
      const items = Store.products.filter((p) => p.category === categoryMatch);
      const total = items.reduce((s, p) => s + p.stock, 0);
      return `Ngành hàng "${categoryMatch}" có ${items.length} mã sản phẩm, tổng tồn kho ${Helpers.formatNumber(total)} cái.`;
    }

    if (/(quy tắc|rule|automation).*(đang chạy|hoạt động)|bao nhiêu quy tắc/.test(q)) {
      const active = Store.rules.filter((r) => r.checked);
      const paused = Store.rules.length - active.length;
      if (!active.length) return "Hiện không có quy tắc tự động hoá nào đang chạy.";
      return `Có ${active.length} quy tắc đang chạy, ${paused} quy tắc tạm dừng:\n` + active.map((r) => `• ${r.title} (${r.freq})`).join("\n");
    }

    if (/(lỗi|thất bại|failed).*(tự động|rule|log)|có lỗi.*không/.test(q)) {
      const failed = Store.logs.filter((l) => l.status === "failed").slice(0, 5);
      if (!failed.length) return "Không có lỗi nào trong lịch sử chạy tự động gần đây. 👍";
      return `Có ${Store.logs.filter((l) => l.status === "failed").length} lượt lỗi gần đây, mới nhất:\n` + failed.map((l) => `• [${l.time}] ${l.rule}: ${l.msg}`).join("\n");
    }

    if (/lịch sử chạy|log gần đây/.test(q)) {
      const recent = Store.logs.slice(0, 5);
      if (!recent.length) return "Chưa có lượt chạy tự động hoá nào được ghi nhận.";
      return "5 lượt chạy gần nhất:\n" + recent.map((l) => `• [${l.time}] ${l.rule} — ${l.status === "success" ? "Thành công" : l.status === "failed" ? "Thất bại" : "Bỏ qua"}`).join("\n");
    }

    if (/doanh thu|lợi nhuận/.test(q)) {
      return "Số liệu doanh thu/lợi nhuận chi tiết đang ở trang Báo cáo. Đây là bản demo nên các con số ở đó là dữ liệu minh hoạ, chưa nối với đơn hàng thật.";
    }

    return "Tôi chưa có đủ dữ liệu để trả lời chính xác câu này. Bạn có thể hỏi về: sản phẩm sắp hết/hết hàng, giá trị tồn kho, quy tắc tự động hoá đang chạy, hoặc lịch sử chạy gần đây.";
  },

  send(text) {
    text = (text || "").trim();
    if (!text) return;
    Store.addChatMessage({ role: "user", text });
    this.render();
    this.els.input.value = "";
    this.els.input.style.height = "auto";
    this.showTyping();
    setTimeout(() => {
      this.hideTyping();
      const reply = this.answer(text);
      Store.addChatMessage({ role: "bot", text: reply });
      this.render();
    }, 500 + Math.random() * 500);
  },
};

window.ChatWidget = ChatWidget;

window.addEventListener("DOMContentLoaded", () => {
  ChatWidget.init();
});
