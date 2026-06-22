# Demo Runbook — POS → NeonDB → Discord (5 phút)

## Checklist trước demo (30 phút trước)

- [ ] Docker Desktop đang chạy ("Engine running")
- [ ] `docker compose up -d` — tất cả 3 container UP
- [ ] n8n mở tại http://localhost:5678 — workflow "POS Demo" ở trạng thái **Active**
- [ ] Discord webhook URL đã paste vào node "Notify Discord"
- [ ] Chạy thử 1 lần: `python scripts/pos_simulator.py invoice` → thấy thông báo Discord
- [ ] NeonDB có dữ liệu: `python scripts/pos_simulator.py invoice` → kiểm tra DB
- [ ] Mở sẵn tab: n8n Executions | Discord | terminal

---

## Kịch bản demo 5 phút

### Phút 0:00 — Giới thiệu (30 giây)
> "Hệ thống này giải quyết bài toán: khi máy POS bán hàng xong,
> làm sao team quản lý biết ngay mà không cần nhìn màn hình quầy?"

Chỉ vào sơ đồ luồng:
```
Máy POS → Webhook n8n → Validate → NeonDB → Discord
```

### Phút 0:30 — Chạy demo hóa đơn đầu tiên (1 phút)

Mở terminal, chạy:
```powershell
python scripts/pos_simulator.py invoice
```

**Chỉ cho Lâm thấy:**
1. Terminal in ra HTTP 201 + invoice_no
2. Discord nhận thông báo ngay lập tức (< 2 giây)
3. n8n Executions tab → thấy execution xanh

### Phút 1:30 — Chạy full demo 5 sự kiện (1.5 phút)

```powershell
python scripts/pos_simulator.py
```

Giải thích từng event khi nó chạy:
- **sale_completed** → hóa đơn bình thường → Discord thông báo màu xanh
- **cash_low** → cảnh báo tiền mặt sắp hết → Discord thông báo màu cam
- **BAD PAYLOAD** → thiếu device_id → hệ thống trả 400, không crash

### Phút 3:00 — Kiểm tra dữ liệu trong NeonDB (1 phút)

Mở tab NeonDB Console (hoặc chạy):
```sql
SELECT id, device_id, event_type, payload->>'amount' as amount, created_at
FROM iot_events
ORDER BY id DESC
LIMIT 5;
```

> "Tất cả dữ liệu đã được lưu với timestamp chính xác, payload đầy đủ
> dưới dạng JSONB — có thể query linh hoạt sau này."

### Phút 4:00 — Hiển thị n8n workflow (45 giây)

Mở http://localhost:5678 → vào workflow "POS Demo":
- Chỉ vào từng node và giải thích vai trò
- Nhấn vào "Executions" → thấy lịch sử chạy và input/output từng bước
- Nhấn vào 1 execution → zoom vào node "Validate + Enrich" để thấy data transform

### Phút 4:45 — Kết luận (15 giây)
> "Toàn bộ luồng này không cần viết server riêng —
> chỉ cần n8n + 1 Python microservice. Dễ mở rộng thêm:
> email, SMS, Zalo OA, hay bất kỳ kênh nào khác."

---

## Câu hỏi Lâm có thể hỏi — chuẩn bị trả lời

**Q: Nếu n8n chết thì sao?**
A: n8n có `restart: always` trong docker-compose — tự restart. Execution log lưu lại để retry thủ công.

**Q: Nhiều máy POS cùng gửi 1 lúc thì có bị nghẽn không?**
A: n8n xử lý concurrent webhook tốt. NeonDB pooler hỗ trợ nhiều connection đồng thời. Có thể stress test bằng `python scripts/pos_simulator.py loop 50`.

**Q: Discord thay bằng Zalo/Telegram được không?**
A: Được — chỉ cần đổi URL và payload format trong node "Notify Discord". Telegram và Zalo OA đều có webhook API tương tự.

**Q: Dữ liệu payload có thể thay đổi cấu trúc không?**
A: Được — dùng JSONB nên payload không có schema cứng. Mỗi loại event có thể có cấu trúc khác nhau.

---

## Video backup

Quay màn hình toàn bộ kịch bản trên bằng OBS hoặc Windows Game Bar (Win + G).
Lưu vào `.planning/demo-backup.mp4`.

Các cảnh cần có trong video:
1. `docker compose ps` → thấy 3 container UP
2. Chạy `pos_simulator.py invoice` → Discord nhận notification
3. Chạy full demo → 5 events
4. NeonDB console → SELECT rows
5. n8n Executions → xem execution detail
