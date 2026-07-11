# Deviations — sai khác giữa triển khai và tài liệu PDF

Ghi lại các quyết định thực dụng khác với mô tả trong PDF automation. PDF 3 (INFRASTRUCTURE)
là master; các mục dưới đây là đề xuất cập nhật PDF hoặc lý do giữ khác.

| # | Điểm | PDF viết | Triển khai thực tế | Lý do |
|---|---|---|---|---|
| D1 | Idempotency store | PDF 1 (NT 5): Redis TTL 24h | **Postgres**: cột `iot_events.idempotency_key UNIQUE` + `ON CONFLICT DO NOTHING` | Không thêm container Redis cho pilot; unique constraint đủ mạnh & bền hơn (không mất khi restart). Khớp Manuf ràng buộc 6 (unique constraint). |
| D2 | `event_type` giá trị | Registry: `sale` | Workflow/POS gửi `sale`; `rag_service` map alias `sale_completed`/`payment_received`/`invoice` → `sale` khi ghi | Tương thích ngược dữ liệu/thiết bị cũ trong khi vẫn chuẩn hóa registry. |
| D3 | Brain (VLM/LLM) | Gọi Brain thật (Colab/ngrok) | **mock-brain** container trả response cố định (`/upload`, `/mcp/validate-invoice`, `/chat`) | Dev/test luồng automation không cần GPU. Nối Brain thật qua `BRAIN_BASE_URL` khi sẵn sàng. |
| D4 | QT5/QT1 upload hóa đơn | Webhook multipart (file ảnh) | Webhook JSON `{scenario}` gọi mock-brain OCR | Đơn giản hóa để test tự động deterministic. Khi nối Brain thật sẽ chuyển sang multipart → Brain `/upload`. |
| D5 | Discord | Discord webhook thật | **discord-mock** (:9099) trong dev; workflow đọc `$env.DISCORD_WEBHOOK_URL` | Test không spam Discord thật; prod chỉ đổi `.env`. |
| D6 | Error workflow | Settings → Error Workflow gán `__error_handler` | ✅ ĐÃ auto-wire: `tests/smoke/setup.py` PATCH `settings.errorWorkflow` cho mọi workflow sau import | Hoàn tất. |
| D7 | n8n DB backend | Staging: `postgresdb` | Dev: **SQLite mặc định** (nhanh, ít cấu hình) | Chuyển postgresdb khi lên staging/scale (queue mode) — Sprint sau. |
| D8 | Retry/backoff HTTP node | Bật "Retry On Fail" 3 lần | ✅ ĐÃ bật cho node gọi `rag_service` (3 lần, 1s). Discord/notify KHÔNG retry (đúng rule rate-limit) | Hoàn tất. |
| D9 | PII masking | Mask SĐT/email khi log/thông báo | ✅ ĐÃ mask trong `retail_new_customer_welcome` (SĐT `XXXXXXX678`, email `n***@d`) và `retail_debt_reminder` | Hoàn tất. |
| D10 | Kênh thông báo | Discord | ✅ **Notifier đa kênh** `shared_notify` (webhook `/webhook/notify`) route theo `channel` → `$env` URL (discord/telegram/zalo/facebook). Dev mock, prod đổi `.env` | QT6-10 dùng notifier; QT1-5 vẫn post Discord trực tiếp (migrate dần). |
| D11 | QT7 đăng FB | Auto-post FB Graph API | Caption AI sinh → **status pending_approval + notify duyệt**, KHÔNG auto-post (chống hallucination); `FB_POST_URL` để cho bước duyệt | Đúng NT "AI đề xuất, người quyết". |
| D12 | QT10 ResearcherAgent | DuckDuckGo crawl giá đối thủ | **Stub** trong Code node (giả lập đối thủ -20%); thay bằng `$env.RESEARCHER_URL` thật ở prod | Nhánh ngoài chưa test tự động (đúng lựa chọn "build logic + stub"). |

## V2 — Pilot thật: CÔNG TY TNHH TRÀ NGỌC DUY (trà/cao atiso Đà Lạt)

**2026-07-11:** đọc `ANSER_AUTOMATION_V2_DEEPDIVE.pdf` + `ANSER_AUTOMATION_V2_MANUFACTURING.pdf`
+ khảo sát ngocduygroup.com → pilot là công ty thật của user. Đã **chuyển đổi toàn bộ domain
sản xuất từ "nước đóng chai" (scaffolding V1) sang trà/cao atiso** theo quyết định user:

| # | Điểm | Quyết định |
|---|---|---|
| V2-1 | Chiến lược V1→V2 | GIỮ khung orchestration + hạ tầng chung; SỬA semantic domain; THÊM E2/F1/F2. KHÔNG giữ 2 schema song song (bản nước đóng chai còn trong git history) |
| V2-2 | Thứ tự | Sản xuất đợt 1 (E2→F1→F2) trước — vì retail FEFO/HSD tiêu thụ lô do F1 sinh; **B1 (HĐĐT) + C1 (SePay) làm NGAY SAU** (bắt buộc pháp lý NĐ 70/2025 khi go-live); cả 2 khối P0 trước mọi P1 |
| V2-3 | Dữ liệu | PUBLIC (tên SP, giá bán, quy cách) = thật từ ngocduygroup.com **ngày 2026-07-11** (thời giá — sẽ đổi); NỘI BỘ (giá thu mua, định mức tươi→khô, BOM, chi phí) = ASSUMED có gắn cờ trong seed |
| V2-4 | BOM ĐẢO yield | Nước đóng chai tính xuôi (qty×định mức); atiso tính NGƯỢC qua hao hụt sấy: **cần mua tươi = thiếu khô ÷ yield_tươi→khô** (`bom_materials.yield_fresh_to_dry`) |
| V2-5 | Vá báo động giả yield | Sấy tươi→khô mất 70-95% khối lượng là **BÌNH THƯỜNG** — QT6 không còn cảnh báo theo `yield_loss>10%`; so **yield thực vs định mức** (`manuf_products.standard_yield`), chỉ warn khi lệch >15% tương đối (ASSUMED) — test #39/#40 |
| V2-6 | Cửa sổ 24h (E2/F1) | Đồng hồ từ `material_batches.harvest_date`: còn <6h → khẩn; quá 24h → cảnh báo mất cynarin + cân nhắc chuyển hướng SP. Code thuần, không LLM |
| V2-7 | Độ ẩm → HSD (F1) | ASSUMED: ≤7% → HSD 12 tháng; ≤8% → 6 tháng; >8% → sấy tiếp (không chốt mẻ). Nhập tay/tablet, IoT optional |
| V2-8 | Gate kiểm nghiệm (F2) | GATE CỨNG: mẻ hoàn thành = `pending_lab`, chỉ `passed` mới được bán. Ngưỡng ASSUMED: cynarin ≥2%, mốc <100 CFU/g, BVTV + kim loại nặng đạt. Fail → chặn + truy xuất về nông hộ/vùng trồng |
| V2-9 | E2 thay QT4 | Bên C = **nông hộ/HTX** (cân tại chỗ, KHÔNG HĐĐT chuẩn) — `manuf_material_import_ocr` → `manuf_material_batch_intake`: OCR phiếu cân HOẶC nhập app; vẫn giữ nguyên tắc tiền (lệch cân×giá → 422) |
| V2-10 | F1 thay QT5 | `manuf_plc_production_ingest` → `manuf_batch_process_log`: 1 webhook `/batch-process` với event start/stage/complete (nhật ký héo/xao/vò/sấy + CCP nhiệt độ) |
| V2-11 | Traceability | Chưa tách bảng `traceability` riêng (G1 đợt 2) — dùng `production_batches.material_lot_code` → `material_batches` (nông hộ, vùng, harvest_date, GACP cert) đủ cho F2 điều tra |
| V2-12 | Retail chưa gate QC | Marketplace/POS chưa kiểm tra `qc_status` khi bán (A1 FEFO + khóa lô = đợt bán lẻ V2 tiếp theo) |

**Khảo sát Ngọc Duy — user đã trả lời (2026-07-11):**
- Q1 nguồn NVL: **lai** — vườn 4.000m² tự trồng + vùng hợp tác chuyên canh/nông hộ (tỷ lệ cụ thể chưa rõ)
- Q5 SP theo mùa: trà atiso túi lọc = flagship bán volume; cao atiso = quà tặng giá trị cao; cao điểm = mùa du lịch (hè, Tết)

**Khảo sát còn mở (cần Ngọc Duy trả lời để thay ASSUMED):**
- Q2 kiểm nghiệm (cynarin/mốc/BVTV) nội bộ hay gửi lab ngoài? (đang giả định lab ngoài)
- Q3 đo độ ẩm khâu sấy bằng thiết bị điện tử hay kinh nghiệm? (đang giả định nhập tay + IoT optional)
- Q4 định mức tươi→khô thật từng SP (đang ASSUMED: trà 25%, bông 20%, cao 5%)
- Q6 cảm biến nhiệt/ẩm ở xưởng & kho? (quyết phạm vi IoT cho F1/H1)
- Giá thu mua nông hộ thật (đang ASSUMED 12-18k/kg tươi); ngưỡng lệch định mức chấp nhận (đang 15%)

**B1 + C1 ĐÃ LÀM (2026-07-11, chưa commit):**

| # | Điểm | Quyết định / triển khai |
|---|---|---|
| B1-1 | NCC HĐĐT | User chưa chọn → **shape trung lập** (`mock_services/einvoice_mock`, issue/adjust/lookup + mã CQT); khi chốt MISA/VNPT/Viettel viết 1 adapter + đổi `EINVOICE_API_URL` |
| B1-2 | VAT | **8% đến 31/12/2026 (NQ 204/2025) → 10%** — bảng suất theo ngày hiệu lực trong rag (`VAT_SCHEDULE`), ASSUMED chờ kế toán; giá bán lẻ coi là ĐÃ gồm VAT → tách ngược (test #43/#50 kiểm tay) |
| B1-3 | Không hủy HĐ | NĐ 70/2025: không có route delete; `/einvoice-adjust` phát hành HĐ điều chỉnh trỏ HĐ gốc, gốc → 'adjusted' vẫn lưu vết (test #48) |
| B1-4 | NCC lỗi | Hàng đợi `einvoice_pending` — không để đơn thiếu hóa đơn (test #47); retry tự động = backlog |
| B1-5 | Backup ≥10 năm | Schedule 23h → export JSON + SHA-256 → **2 đích** (dev: discord-mock /drive-backup + /s3-backup; prod: đổi `BACKUP_URL_1/2` sang Google Drive + storage khác) (test #49) |
| C1-1 | VietQR | QR động `img.vietqr.io`, nội dung CK `NGOCDUY DH{id}`; TK thật MB (user cấp) trong `.env`; QR đính thẳng embed Discord |
| C1-2 | SePay | User CÓ tài khoản → **nối thật qua cloudflared quick tunnel** (URL đổi mỗi lần chạy — prod cần domain/tunnel cố định); verify header `Authorization: Apikey` (key thật trong `.env`, sai key → 401, test #45); idempotent theo tx id (test #44) |
| C1-3 | Đối soát | Khớp mã đơn + đúng tiền → paid + tự phát hành HĐĐT; MỌI ca lệch (lệch tiền/không đọc được mã/đơn đã trả) → `payment_pending` + gợi ý đơn theo tiền+thời gian, KHÔNG tự khớp (test #46) |
| C1-4 | Trigger HĐĐT | Hiện chỉ luồng SePay paid → issue. POS tại quầy + marketplace chưa wire (chờ A1 gộp đơn đa kênh về `channel_orders`) |

**C1 bổ sung — SePay POLL thay webhook (2026-07-11):** user không tìm thấy trang Webhooks trong
dashboard SePay nhưng key cấp là **API Access Token hợp lệ** (userapi trả 200) → `retail_sepay_poll`
poll `my.sepay.vn/userapi/transactions/list` mỗi phút (Bearer), lọc tiền vào 10 phút gần nhất, bơm
vào `/webhook/sepay-webhook` (tự-post kèm Apikey — tái dùng nguyên pipeline đối soát/HĐĐT).
Idempotent theo tx id nên poll lặp vô hại. User chốt: **poll là cơ chế chính thức**, webhook bật
thêm sau khi tìm thấy trang (2 đường chạy song song vô hại). Prod: chuyển cursor last-id thay cửa sổ
10 phút.

**A1 ĐÃ LÀM (2026-07-11, chưa commit) — đồng bộ tồn & đơn đa kênh (FEFO theo lô):**

| # | Điểm | Quyết định / triển khai |
|---|---|---|
| A1-1 | Tồn theo LÔ | `product_lots` (sku, lot_code, HSD, qty) + `lot_allocations` (lưu vết lô→đơn); `products.stock_quantity` = SUM(lô) cho SKU quản theo lô |
| A1-2 | Nguồn lô | **Cả hai** (user chốt): mẻ F2 ĐẠT → TỰ nhập kho (lot_code = batch_code, HSD kế thừa từ độ ẩm F1, source='production' — nối liền chuỗi SX→bán lẻ, test #52) + nhập tay hàng thương mại (`/webhook/lot-intake`, test #51) |
| A1-3 | FEFO + quà tặng | Bán thường: lô HSD GẦN xuất trước (test #53); `is_gift=true` → đảo chiều lấy lô HSD XA + cảnh báo nếu lô gán cận hạn <90 ngày ASSUMED (test #55) |
| A1-4 | Chống oversell | Transaction + `SELECT ... FOR UPDATE` khóa lô; thiếu tồn → rollback toàn bộ + 409, KHÔNG trừ gì (test #56) |
| A1-5 | Chuẩn hóa kênh | 1 webhook `/channel-order` + Code node normalize theo `channel`: shopee (order_sn/item_list), tiktok (order_id/line_items), web (Woo id/line_items); idempotent theo external_order_id (test #54) |
| A1-6 | Đồng bộ ngược | Bán 1 kênh → push tồn mới lên CẢ 3 kênh ($env WOO/SHOPEE/TIKTOK_STOCK_URL — dev mock, test #58) |
| A1-7 | HĐĐT đơn sàn | User chốt: **chờ delivered** mới xuất (giảm điều chỉnh do COD hoàn/hủy — test #57); đơn web thanh toán QR xuất ngay như C1 |
| A1-8 | WooCommerce | KHÔNG có quyền admin ngocduygroup.com; site mẫu của user (gundam58.wordpress.com) là **wp.com Free — không cài được plugin WooCommerce** (cần gói trả phí) → dựng `mock_services/woo_mock` (:8300) nói ĐÚNG shape API Woo thật (`/wp-json/wc/v3/orders`, auth consumer key → sai = 401). `retail_woo_poll` 5 phút poll như site thật (test #59); khi có site Woo thật chỉ đổi WOO_BASE_URL/KEY/SECRET trong .env |
| A1-10 | Poller vs test | 2 poller (SePay/Woo) chạy schedule tự động → gen_evidence TẮT chúng đầu run (deterministic FEFO), BẬT lại cuối run; TRUNCATE channel_orders xóa cả đơn demo live → đơn live luôn tạo lại SAU khi chạy matrix |
| A1-9 | QT8 legacy | `retail_marketplace_sync` (bản cũ trừ thẳng stock_quantity) giữ chạy song song; migrate hẳn sang channel-order khi nối sàn thật |

**V2 chưa làm:** A2 dự báo mùa du lịch, C2 giao đi tỉnh, C3 marketing gate; Sản xuất đợt 2-3 (E1 dự
báo thu mua năm — PHẢI xong trước mùa vụ tháng 3, G1 QR truy xuất, G2 giá thành đủ (điện sấy/bao
bì), H1 HSD+độ ẩm kho, H2 in tem); retry tự động einvoice_pending; SePay cursor last-id; Woo push
tồn thật (mới có mock đích).

## Sản xuất V1 (nước đóng chai — ĐÃ THAY THẾ bằng V2 atiso ở trên, giữ lại làm sử liệu quyết định)

Pilot giả định cũ: xưởng chế biến đồ uống đóng chai. Các quyết định M1-M12 bên dưới vẫn đúng
về NGUYÊN TẮC (đơn vị kép, deterministic-first, idempotency, LLM fallback...) — chỉ domain đổi:

| # | Điểm | Quyết định | Lý do / nguồn |
|---|---|---|---|
| M1 | Đơn vị đo | NVL vào theo **kg**, TP ra theo **đơn vị đóng gói** (chai) + `unit_weight_kg` để quy đổi | User chọn "cả hai" — schema `production_batches` có `input_material_kg` + `output_units` + `unit_weight_kg` |
| M2 | Định nghĩa thất thoát | **Cả yield + NG**: `yield_loss = (NVL_kg − TP_quy_kg)/NVL_kg`; `ng = lỗi/(TP+lỗi)` | User chọn "cả hai". Tính bằng SQL (deterministic), LLM chỉ diễn giải |
| M3 | Báo cáo ĐR | **Cả theo đơn A + theo kỳ**; kỳ gồm Ngân sách khu vực / Chi phí B / Lợi nhuận | User chọn "cả hai" + đúng khung ảnh ghi chú A/B |
| M4 | Nguồn dữ liệu sản lượng | QT5 nhận **cả PLC lẫn nhập tay** (cùng webhook `/webhook/plc-event`, field `source`) | Hạ tầng "chưa rõ" → không phụ thuộc nhà máy có PLC hay không |
| M5 | Ground-truth tài chính | %thất thoát/%lãi tính bằng SQL trong rag; Brain (mock) **chỉ diễn giải nguyên nhân** | Nguyên tắc deterministic-first (Manuf ràng buộc 1) |
| M6 | Idempotency PLC | `production_batches.batch_code UNIQUE` + `ON CONFLICT` | Gateway PLC có thể retry (Manuf ràng buộc 6) |
| M7 | Xuất Google Docs (QT7) | **Stub** `$env.DOCS_URL` (dev → mock); prod = Body `/api/google/docs-create` | Body đã có OAuth Google |

**Câu hỏi khảo sát pilot còn mở (cần đối tác B trả lời để thay seed giả định bằng số thật):**
hãng PLC + có đọc được bộ đếm sản lượng/khối lượng không; đơn giá NVL & nhân công thực; `unit_weight_kg` thực của sản phẩm; ngưỡng cảnh báo hao hụt/NG mà B chấp nhận; ca sản xuất (1/2/3 ca) để đặt lịch QT6/QT7; có cảm biến đếm phế phẩm riêng hay ước lượng.

**QT1/2/4 đã build (đợt 2 sản xuất) — quyết định theo trả lời khảo sát:**

| # | Điểm | Quyết định |
|---|---|---|
| M8 | BOM | **Cả hai**: định mức/1 đơn vị TP (`bom_materials.qty_per_unit`) làm chuẩn + quy ra **số mẻ gợi ý** (`manuf_products.batch_output_units`, ceil) |
| M9 | SL cần SX (QT1) | **LLM suy luận** (đúng PDF QT1) — mock-brain giả lập buffer 2% NG; lệnh SX luôn `status='draft'` chờ người duyệt |
| M10 | Tồn NVL (QT2) | **Có theo dõi** `material_stock`: cần mua = cần dùng − tồn; QT4 cộng tồn khi nhập từ C |
| M11 | Thiếu BOM (QT2 3b) | **LLM fallback + cờ** `estimation_method='llm_fallback'` + cảnh báo "BẮT BUỘC duyệt tay" |
| M12 | Trạng thái chuỗi | QT4 nhập NVL có `order_code` → `material_requirements.status='materials_received'` (sẵn sàng SX — nối QT5) |

**Chưa làm (sản xuất đợt sau):** QT3 RFQ tới C (cần Gmail qua Body), QT8 bàn giao SP cho A (cần Google Docs template + trạng thái delivered/closed).

## Đã đóng đúng theo PDF (không phải deviation)
- SEC-3 token `x-anser-token` mọi webhook → 400 (test #1,#2). 
- SEC-5 parameterized query, chống SQLi (test #5).
- `?date=` rỗng fallback CURRENT_DATE (test #9).
- `N8N_BLOCK_ENV_ACCESS_IN_NODE=false` cho $env (test #10 ngầm — mọi $env hoạt động).
- Low-stock theo ngưỡng RIÊNG từng SP (`low_stock_threshold`) — đóng gap G1 báo cáo (test #11).
- Deterministic-first: mock-brain `/mcp/validate-invoice` tính lại tổng bằng code (test #12/#13).

## Bug có sẵn đã phát hiện & vá khi build Sprint 1
- `rag_service /customer-insert`: `COALESCE(MAX(id),0)+1` thiếu alias → KeyError `'coalesce'` (từ trước Sprint 0). Đã vá `AS next_id`. → luồng "Chào khách hàng mới" trong báo cáo `.docx` trước đây chưa từng chạy được.
