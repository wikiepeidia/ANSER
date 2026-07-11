# ANSER Automation — Test Matrix (PDF 3 mục 5 + V2 trà/cao atiso)

Mọi workflow ingest phải pass checklist này trước khi merge. Chạy tự động:
`python tests/smoke/gen_evidence.py` → sinh `tests/evidence/report.html` + transcript.

Pilot: **Trà Ngọc Duy (Đà Lạt)**. Giá bán = PUBLIC từ ngocduygroup.com (2026-07-11);
định mức tươi→khô, giá thu mua, ngưỡng kiểm nghiệm = **ASSUMED** (docs/DEVIATIONS.md).

## Bán lẻ + shared (#1-22)

| # | Kịch bản | Kỳ vọng | Workflow áp dụng |
|---|---|---|---|
| 1 | POST không token | 400 Unauthorized | mọi webhook |
| 2 | POST token sai | 400 Unauthorized | mọi webhook |
| 3 | POST token đúng, payload đúng | 200/201 + row DB | pos_ingest, new_customer, invoice_ocr |
| 4 | POST token đúng, thiếu trường required | 400 nêu rõ trường thiếu | pos_ingest |
| 5 | SQL injection trong query param (`'; DROP TABLE …`) | Vô hiệu, bảng nguyên vẹn | rag /daily-sales |
| 6 | Client retry cùng `idempotency_key` | Chỉ 1 row DB (deduped) | pos_ingest |
| 7 | Discord mock offline | Workflow không crash; response chính vẫn OK | (kiểm thủ công) |
| 8 | Schedule chạy đúng giờ VN | timestamp Asia/Ho_Chi_Minh | low_stock, daily_sales |
| 9 | Query `?date=` rỗng | Fallback CURRENT_DATE (không 500) | rag /daily-sales |
| 10 | `$env` trong Code node | Đọc được (N8N_BLOCK_ENV_ACCESS_IN_NODE=false) | mọi workflow dùng $env |
| 11 | Low-stock theo ngưỡng RIÊNG từng SP | Bông atiso 400gr (12<15 riêng, dù >10 chung) | low_stock (gap G1) |
| 12 | OCR hóa đơn nhập hàng thương mại khớp tổng | 200 + phiếu nhập import_transactions | invoice_ocr |
| 13 | OCR hóa đơn lệch tổng (scenario=mismatch) | 422 + pending_review, KHÔNG ghi kho | invoice_ocr |
| 14 | Khách hàng mới | 201 + row customers | new_customer_welcome |
| 15 | Notifier đa kênh — gửi Zalo | 200 + mock nhận path /zalo | shared_notify |
| 16 | QT7 đăng bài KM (dược liệu → BẮT BUỘC duyệt) | 200 pending_approval + log social_posts | auto_promo_post |
| 17 | QT8 đơn marketplace mới (Shopee trà túi lọc) | 201 + tạo sale + marketplace_orders++ | marketplace_sync |
| 18 | QT8 đơn marketplace trùng | duplicate, không tạo thêm (idempotent) | marketplace_sync |
| 19 | QT6 gợi ý nhập (moving-avg) | Sinh purchase_orders_draft | forecast_suggest_reorder |
| 20 | QT9 nhắc nợ (opt-in + PII) | Gửi khách opt-in, KHÔNG gửi opt-out | debt_reminder |
| 21 | QT10 giá đối thủ | Ghi competitor_prices + cảnh báo | competitor_price_sync |
| 22 | PII masking SĐT | SĐT bị che (XXXXXXX…) trong thông báo | new_customer_welcome |

## Sản xuất trà/cao atiso — V2 (#23-41)

| # | Kịch bản | Kỳ vọng | Workflow áp dụng |
|---|---|---|---|
| 23 | E2 nhập lô nông hộ (OCR phiếu cân, thu hái 5h trước) | 201 + lô mới + tồn bông tươi +300kg + window ok (~19h) | material_batch_intake |
| 24 | E2 lô trùng lot_code (phiếu cân gửi lại) | duplicate (idempotent) | material_batch_intake |
| 25 | E2 lô tươi QUÁ cửa sổ 24h (30h) | 201 + `window_status=overdue` (cảnh báo mất cynarin) | material_batch_intake |
| 26 | E2 phiếu cân lệch tổng | 422 pending, tồn KHÔNG đổi (tiền trả nông hộ = cân × giá) | material_batch_intake |
| 27 | QT1 OCR đơn A → lệnh SX | 201 draft + LLM buffer (500 hộp → 510) | ocr_customer_order |
| 28 | QT1 đơn trùng order_code | duplicate (idempotent) | ocr_customer_order |
| 29 | QT2 BOM ĐẢO yield | LA mua = (51−20)/0.25 = **124kg TƯƠI**; tem đủ→0; 3 mẻ | generate_material_list |
| 30 | QT2 thiếu BOM (TRA-GUNG) | llm_fallback + cờ duyệt tay | generate_material_list |
| 31 | E2 nhập app trực tiếp + mua theo đơn | tồn lá tươi +124kg + materials_received | material_batch_intake |
| 32 | F1 bắt đầu mẻ (lô 3h tuổi) | 201 started + đồng hồ 24h (~21h còn lại) | batch_process_log |
| 33 | F1 mẻ trùng batch_code | duplicate (idempotent) | batch_process_log |
| 34 | F1 nhật ký công đoạn (xao 110°C) | logged + batch_process_log++ | batch_process_log |
| 35 | F1 độ ẩm 9.2% CHƯA đạt (>8%) | moisture_fail + KHÔNG chốt HSD → sấy tiếp | batch_process_log |
| 36 | F1 sấy lại đạt 6.5% | completed + HSD 12 tháng + qc=pending_lab (chưa mở bán) | batch_process_log |
| 37 | F2 kiểm nghiệm ĐẠT (cynarin 2.8%, mốc 40) | passed + sellable + qc=passed | lab_test_gate |
| 38 | F2 KHÔNG ĐẠT (nấm mốc 150>100 CFU/g) | failed + CHẶN XUẤT + điều tra về nông hộ/vùng trồng | lab_test_gate |
| 39 | QT6 hao hụt sấy 80.8% NHƯNG đúng định mức | yield 19.2%/định mức 20% → lệch 4% → **warn=false** (vá báo động giả) | waste_profit_report |
| 40 | QT6 lệch định mức THẬT | yield 20%/định mức 25% → lệch 20%>15% → **warn=true**; NG 1.64%; lãi 90.93% | waste_profit_report |
| 41 | QT7 báo cáo ĐR | kỳ + đơn + ≥2 khu vực (Đà Lạt/TP.HCM) | dr_report_periodic |

## Bán lẻ V2 — B1 HĐĐT + C1 SePay/VietQR (#42-50)

| # | Kịch bản | Kỳ vọng | Workflow áp dụng |
|---|---|---|---|
| 42 | C1 tạo đơn → VietQR động | 201 + tổng 174.000 (code tính) + QR nhúng `NGOCDUY DH{id}` | order_payment_qr |
| 43 | C1→B1 SePay khớp (đúng key + đúng tiền) | paid + HĐĐT tự phát hành: VAT 8% = 161.111,11 + 12.888,89 + mã CQT | sepay_payment |
| 44 | C1 SePay retry trùng tx id | duplicate — không double-paid/double-invoice | sepay_payment |
| 45 | C1 SePay sai API key | 401 Unauthorized | sepay_payment |
| 46 | C1 CK lệch tiền (500k vs 843k) | review + payment_pending + đơn VẪN unpaid | sepay_payment |
| 47 | B1 NCC HĐĐT lỗi (503) | queued vào einvoice_pending, KHÔNG mất đơn, KHÔNG HĐ rác | rag /einvoice-issue |
| 48 | B1 điều chỉnh HĐ (NĐ 70/2025: KHÔNG hủy) | HĐ mới trỏ gốc; gốc 'adjusted' nhưng VẪN tồn tại | einvoice_adjust |
| 49 | B1 backup 2 đích + checksum | targets_ok=2 + mock nhận đúng SHA-256 | einvoice_backup (schedule) |
| 50 | B1 VAT theo ngày hiệu lực (2027) | 10% (hết NQ 204): 79.090,91 + 7.909,09 | rag /einvoice-issue |

## Bán lẻ V2 — A1 đồng bộ tồn & đơn đa kênh, FEFO theo lô (#51-58)

| # | Kịch bản | Kỳ vọng | Workflow áp dụng |
|---|---|---|---|
| 51 | A1 nhập lô tay (hàng thương mại) | 201 + lô mới + stock = SUM(lô) | lot_intake |
| 52 | Chuỗi F2 ĐẠT → TỰ nhập kho bán | lô = mẻ SX (qty, source=production, HSD kế thừa độ ẩm F1) | lab_test_gate → product_lots |
| 53 | Đơn Shopee chuẩn hóa + FEFO | trừ lô HSD GẦN nhất trước (LOT-RT-A 2026-10) | channel_order_sync |
| 54 | Đơn kênh trùng external_order_id | duplicate (webhook sàn retry) | channel_order_sync |
| 55 | Đơn QUÀ TẶNG | gán lô HSD XA nhất (đảo FEFO) + cảnh báo nếu cận hạn | channel_order_sync |
| 56 | Oversell (đặt 99, tồn lô 5) | 409 blocked + rollback, tồn KHÔNG đổi (khóa lô FOR UPDATE) | channel_order_sync |
| 57 | Đơn sàn delivered → HĐĐT | trước giao 0 HĐ; sau giao 1 HĐ (giảm điều chỉnh COD) | channel_delivered |
| 58 | Đồng bộ tồn ngược 3 kênh | web + Shopee + TikTok đều nhận stock_update | channel_order_sync |
| 59 | Kênh web: poll WooCommerce (woo-mock, shape API thật + auth 401) | đơn Woo mới → poll → channel_orders + FEFO | woo_poll → channel_order_sync |

Kết quả gần nhất: **56/56 PASS** — xem `tests/evidence/report.html` + `report.png` + `n8n_executions.png`
(timestamp, raw HTTP, DB rows, Discord/Zalo payloads, n8n UI). Demo Discord thật: `tests/evidence/demo_transcript.txt`.
SePay nhận tiền qua POLL API mỗi phút (`retail_sepay_poll`); kênh web qua woo-mock (site Woo thật = đổi 3 dòng .env).
Lưu ý vận hành: matrix TẮT 2 poller khi chạy (bật lại cuối run) + TRUNCATE channel_orders → tạo lại đơn demo live sau test.
