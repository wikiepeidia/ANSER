-- ANSER automation — schema test cho stack dev/staging (PDF 3 mục 7 + V2 trà/cao atiso).
-- Postgres 16. Chạy tự động qua /docker-entrypoint-initdb.d khi tạo container mới.
-- Deterministic-first: tiền/số lượng do code/DB tính, LLM không phải nguồn số liệu cuối.
--
-- PILOT: CÔNG TY TNHH TRÀ NGỌC DUY (Đà Lạt) — sản xuất & bán lẻ trà/cao atiso dược liệu.
-- Dữ liệu PUBLIC (tên SP, giá bán, quy cách): lấy từ ngocduygroup.com ngày 2026-07-11 (thời giá).
-- Dữ liệu NỘI BỘ (giá thu mua, định mức tươi→khô, BOM, chi phí): -- ASSUMED, chờ Ngọc Duy xác nhận.

-- ─────────────────────────────────────────────────────────────────────────────
-- IoT / sự kiện ingest (POS, cảm biến xưởng/kho) — hợp đồng JSON PDF 3 mục 3
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS iot_events (
    id               SERIAL PRIMARY KEY,
    device_id        VARCHAR(255) NOT NULL,
    event_type       VARCHAR(100) NOT NULL,
    payload          JSONB NOT NULL DEFAULT '{}'::jsonb,
    -- timestamp thực tế của sự kiện (khác created_at của DB)
    timestamp_source TIMESTAMPTZ,
    -- UUID client sinh, dùng để dedup khi client/gateway retry (PDF3 mục 3 + Manuf ràng buộc 6)
    idempotency_key  VARCHAR(64) UNIQUE,
    created_at       TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_iot_events_device_id  ON iot_events (device_id);
CREATE INDEX IF NOT EXISTS ix_iot_events_event_type ON iot_events (event_type);

-- ─────────────────────────────────────────────────────────────────────────────
-- Bán lẻ: products (có ngưỡng theo từng SP — đóng gap G1 báo cáo), sales, customers
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS products (
    id                  SERIAL PRIMARY KEY,
    name                VARCHAR(255) NOT NULL,
    code                VARCHAR(64) UNIQUE,
    stock_quantity      INTEGER DEFAULT 0,
    -- ngưỡng cảnh báo RIÊNG từng SP (báo cáo .docx hứa per-store/per-product)
    low_stock_threshold INTEGER DEFAULT 10,
    price               NUMERIC(14,2) DEFAULT 0,
    category            VARCHAR(100)
);

CREATE TABLE IF NOT EXISTS sales (
    id           SERIAL PRIMARY KEY,
    user_id      INTEGER,
    total_amount NUMERIC(14,2) DEFAULT 0,
    items        TEXT,               -- JSON array: [{"name","qty","price"}]
    created_at   TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS customers (
    id                SERIAL PRIMARY KEY,
    code              VARCHAR(32),
    name              VARCHAR(255) NOT NULL,
    email             VARCHAR(255),
    phone             VARCHAR(50),
    address           TEXT,
    debt_amount       NUMERIC(14,2) DEFAULT 0,     -- QT9 công nợ
    last_payment_date DATE,                         -- QT9 lần trả gần nhất
    marketing_opt_in  BOOLEAN DEFAULT true,         -- QT9 opt-in luật marketing
    created_at        TIMESTAMPTZ DEFAULT now()
);

-- ─────────────────────────────────────────────────────────────────────────────
-- Bán lẻ QT5: OCR hóa đơn nhập hàng thương mại → phiếu nhập kho (deterministic-first)
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS import_transactions (
    id           SERIAL PRIMARY KEY,
    supplier     VARCHAR(255),
    total_amount NUMERIC(14,2) DEFAULT 0,
    source_file  VARCHAR(255),
    created_at   TIMESTAMPTZ DEFAULT now()
);
CREATE TABLE IF NOT EXISTS import_details (
    id           SERIAL PRIMARY KEY,
    import_id    INTEGER REFERENCES import_transactions(id) ON DELETE CASCADE,
    sku          VARCHAR(64),
    name         VARCHAR(255),
    qty          INTEGER,
    unit_price   NUMERIC(14,2)
);
-- Chứng từ lệch tổng → chờ người xác nhận thủ công (không tự ghi kho)
CREATE TABLE IF NOT EXISTS pending_review (
    id               SERIAL PRIMARY KEY,
    kind             VARCHAR(50),        -- 'invoice_import' | 'material_intake' ...
    reason           TEXT,
    ocr_total        NUMERIC(14,2),
    calculated_total NUMERIC(14,2),
    raw_payload      JSONB,
    created_at       TIMESTAMPTZ DEFAULT now()
);

-- ─────────────────────────────────────────────────────────────────────────────
-- Shared: audit trail + error log (PDF 3 mục 4.3, Manuf ràng buộc 7)
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS audit_log (
    id         SERIAL PRIMARY KEY,
    entity     VARCHAR(100),
    entity_id  VARCHAR(64),
    action     VARCHAR(100),
    user_id    VARCHAR(64),
    details    JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT now()
);
CREATE TABLE IF NOT EXISTS workflow_errors (
    id            SERIAL PRIMARY KEY,
    workflow_name VARCHAR(255),
    node_name     VARCHAR(255),
    error_message TEXT,
    execution_id  VARCHAR(64),
    created_at    TIMESTAMPTZ DEFAULT now()
);

-- ─────────────────────────────────────────────────────────────────────────────
-- Bán lẻ P1/P2 (QT6-10)
-- ─────────────────────────────────────────────────────────────────────────────
-- QT6: đề xuất nhập hàng (draft PO — người duyệt trước khi thành PO thật)
CREATE TABLE IF NOT EXISTS purchase_orders_draft (
    id               SERIAL PRIMARY KEY,
    sku              VARCHAR(64),
    product_name     VARCHAR(255),
    predicted_demand INTEGER,
    current_stock    INTEGER,
    reorder_qty      INTEGER,
    method           VARCHAR(32) DEFAULT 'moving_avg',
    status           VARCHAR(32) DEFAULT 'draft',   -- draft | approved | rejected
    created_at       TIMESTAMPTZ DEFAULT now()
);
-- QT7: khuyến mãi + bài đăng social (SP dược liệu: caption AI BẮT BUỘC người duyệt — pháp lý quảng cáo)
CREATE TABLE IF NOT EXISTS promotions (
    id           SERIAL PRIMARY KEY,
    product_code VARCHAR(64),
    product_name VARCHAR(255),
    discount_pct INTEGER,
    active       BOOLEAN DEFAULT true
);
CREATE TABLE IF NOT EXISTS social_posts (
    id               SERIAL PRIMARY KEY,
    promo_id         INTEGER,
    caption          TEXT,
    channel          VARCHAR(32),
    external_post_id VARCHAR(128),
    status           VARCHAR(32) DEFAULT 'posted',
    created_at       TIMESTAMPTZ DEFAULT now()
);
-- QT8: đơn marketplace (idempotent theo external_order_id)
CREATE TABLE IF NOT EXISTS marketplace_orders (
    id                SERIAL PRIMARY KEY,
    marketplace       VARCHAR(32),
    external_order_id VARCHAR(128) UNIQUE,
    mapped_sale_id    INTEGER,
    raw               JSONB,
    created_at        TIMESTAMPTZ DEFAULT now()
);
-- QT9: log nhắc nợ
CREATE TABLE IF NOT EXISTS debt_reminders (
    id          SERIAL PRIMARY KEY,
    customer_id INTEGER,
    channel     VARCHAR(32),
    message     TEXT,
    created_at  TIMESTAMPTZ DEFAULT now()
);
-- QT10: giá đối thủ (đặc sản Đà Lạt nhiều hàng nhái/phá giá)
CREATE TABLE IF NOT EXISTS competitor_prices (
    id               SERIAL PRIMARY KEY,
    sku              VARCHAR(64),
    product_name     VARCHAR(255),
    our_price        NUMERIC(14,2),
    competitor_price NUMERIC(14,2),
    source           VARCHAR(128),
    created_at       TIMESTAMPTZ DEFAULT now()
);

-- ─────────────────────────────────────────────────────────────────────────────
-- Bán lẻ V2 — C1 (SePay + VietQR) & B1 (HĐĐT NĐ 70/2025)
-- ─────────────────────────────────────────────────────────────────────────────
-- C1: đơn bán cần thanh toán QR (order_no nhúng vào nội dung CK 'NGOCDUY DH{n}').
-- Cũng là nền cho A1 đồng bộ đa kênh (channel: store|web|shopee|tiktok) đợt sau.
CREATE TABLE IF NOT EXISTS channel_orders (
    id             SERIAL PRIMARY KEY,
    order_no       VARCHAR(32) UNIQUE,          -- 'DH{id}'
    channel        VARCHAR(32) DEFAULT 'store',
    customer_name  VARCHAR(255),
    items          JSONB,                        -- [{sku,name,qty,price}] giá ĐÃ gồm VAT (giá bán lẻ)
    total_amount   NUMERIC(14,2) DEFAULT 0,
    payment_status VARCHAR(16) DEFAULT 'unpaid', -- unpaid | paid | review
    qr_url         TEXT,                         -- VietQR động (img.vietqr.io)
    sepay_tx_id    VARCHAR(64) UNIQUE,           -- id giao dịch SePay (idempotent khi retry)
    paid_at        TIMESTAMPTZ,
    created_at     TIMESTAMPTZ DEFAULT now()
);
-- C1: CK lệch tiền/sai nội dung → giữ chờ đối soát thủ công (KHÔNG tự khớp)
CREATE TABLE IF NOT EXISTS payment_pending (
    id              SERIAL PRIMARY KEY,
    sepay_tx_id     VARCHAR(64) UNIQUE,
    gateway         VARCHAR(64),
    content         TEXT,
    amount          NUMERIC(14,2),
    reason          TEXT,
    suggested_order VARCHAR(32),                 -- gợi ý đơn khớp theo tiền + thời gian
    status          VARCHAR(16) DEFAULT 'review',
    created_at      TIMESTAMPTZ DEFAULT now()
);
-- B1: hóa đơn điện tử — NĐ 70/2025: KHÔNG hủy (chỉ điều chỉnh/thay thế), lưu ≥10 năm.
-- VAT: 8% đến 31/12/2026 (NQ 204/2025) rồi về 10% — bảng suất theo ngày trong rag. ASSUMED chờ kế toán.
CREATE TABLE IF NOT EXISTS einvoices (
    id                  SERIAL PRIMARY KEY,
    invoice_no          VARCHAR(64) UNIQUE,      -- số HĐ do NCC cấp
    order_no            VARCHAR(32),
    buyer_name          VARCHAR(255),
    buyer_tax_code      VARCHAR(32),
    items               JSONB,
    subtotal            NUMERIC(14,2),           -- chưa VAT (tách ngược từ giá bán lẻ gồm VAT)
    vat_rate            NUMERIC(5,2),
    vat_amount          NUMERIC(14,2),
    total               NUMERIC(14,2),
    tax_authority_code  VARCHAR(64),             -- mã cơ quan thuế
    status              VARCHAR(16) DEFAULT 'issued',  -- issued | adjusted | replaced
    adjusts_invoice_no  VARCHAR(64),             -- HĐ điều chỉnh trỏ về HĐ gốc (lưu vết)
    provider            VARCHAR(32) DEFAULT 'mock',
    payload             JSONB,                   -- bản lưu đầy đủ phục vụ lưu trữ 10 năm
    checksum            VARCHAR(64),             -- SHA-256 (đối chiếu khi backup)
    issued_at           TIMESTAMPTZ DEFAULT now()
);
-- B1: API NCC lỗi → hàng đợi chờ phát hành lại (không để đơn không có hóa đơn)
CREATE TABLE IF NOT EXISTS einvoice_pending (
    id          SERIAL PRIMARY KEY,
    order_no    VARCHAR(32),
    request     JSONB,
    error       TEXT,
    retry_count INTEGER DEFAULT 0,
    status      VARCHAR(16) DEFAULT 'queued',
    created_at  TIMESTAMPTZ DEFAULT now()
);

-- A1: tồn kho theo LÔ + HSD (FEFO — lô cận hạn xuất trước; quà tặng gán lô HSD xa).
-- Nguồn lô: mẻ sản xuất qua kiểm nghiệm F2 đạt TỰ nhập kho (kế thừa HSD + traceability),
-- hoặc nhập tay (hàng thương mại: trà TN, linh chi). products.stock_quantity = SUM(lô).
CREATE TABLE IF NOT EXISTS product_lots (
    id          SERIAL PRIMARY KEY,
    sku         VARCHAR(64),
    lot_code    VARCHAR(64) UNIQUE,
    expiry_date DATE,
    qty_on_hand INTEGER DEFAULT 0,
    source      VARCHAR(16) DEFAULT 'manual',   -- 'production' | 'manual'
    batch_code  VARCHAR(64),                     -- truy xuất về mẻ SX (nếu từ sản xuất)
    created_at  TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_lots_sku ON product_lots (sku, expiry_date);
-- A1: lưu vết lô nào xuất cho đơn nào (truy xuất + khiếu nại)
CREATE TABLE IF NOT EXISTS lot_allocations (
    id         SERIAL PRIMARY KEY,
    order_no   VARCHAR(32),
    sku        VARCHAR(64),
    lot_code   VARCHAR(64),
    qty        INTEGER,
    created_at TIMESTAMPTZ DEFAULT now()
);
-- A1: channel_orders mở rộng cho đa kênh (idempotent theo mã đơn của KÊNH)
ALTER TABLE channel_orders ADD COLUMN IF NOT EXISTS external_order_id VARCHAR(128) UNIQUE;
ALTER TABLE channel_orders ADD COLUMN IF NOT EXISTS is_gift BOOLEAN DEFAULT false;
ALTER TABLE channel_orders ADD COLUMN IF NOT EXISTS fulfillment_status VARCHAR(16) DEFAULT 'new'; -- new|delivered|cancelled

-- ─────────────────────────────────────────────────────────────────────────────
-- SẢN XUẤT TRÀ/CAO ATISO (V2) — chuỗi: đơn A (QT1) → BOM đảo yield (QT2) →
-- thu mua/nhập lô nông hộ (E2) → mẻ chế biến + cửa sổ 24h + độ ẩm (F1) →
-- gate kiểm nghiệm dược liệu (F2) → báo cáo lệch định mức + lãi (QT6) → ĐR (QT7)
-- ─────────────────────────────────────────────────────────────────────────────
-- Đơn hàng từ khách A (đại lý/khách sỉ đặc sản) → lệnh sản xuất của B (Ngọc Duy)
CREATE TABLE IF NOT EXISTS production_orders (
    id            SERIAL PRIMARY KEY,
    order_code    VARCHAR(64) UNIQUE,
    customer_code VARCHAR(64),                 -- bên A
    product_code  VARCHAR(64),
    product_name  VARCHAR(255),
    qty_ordered    INTEGER,                      -- số đơn vị đóng gói khách A đặt (hộp/túi)
    qty_to_produce INTEGER,                      -- SL cần SX (LLM suy luận + buffer, người duyệt)
    unit_price     NUMERIC(14,2),                -- giá bán / đơn vị (doanh thu)
    region        VARCHAR(100),                  -- khu vực bán (cho "Ngân sách khu vực")
    status        VARCHAR(32) DEFAULT 'in_progress',
    created_at    TIMESTAMPTZ DEFAULT now()
);

-- E2: LÔ NGUYÊN LIỆU từ nông hộ/HTX (mùa vụ tháng 3-4; cân tại chỗ, không HĐĐT chuẩn).
-- harvest_date khởi động đồng hồ cửa sổ chế biến 24h (giữ cynarin) cho lô TƯƠI.
CREATE TABLE IF NOT EXISTS material_batches (
    id            SERIAL PRIMARY KEY,
    lot_code      VARCHAR(64) UNIQUE,          -- dedup khi phiếu cân gửi lại
    farmer        VARCHAR(255),                -- nông hộ/HTX (vd HTX Thuận Phát)
    region_grown  VARCHAR(128),                -- vùng trồng (truy xuất GACP)
    part          VARCHAR(16),                 -- bông | lá | thân | rễ
    form          VARCHAR(8) DEFAULT 'tuoi',   -- tuoi (cửa sổ 24h) | kho (lưu được ≤1 năm)
    material_code VARCHAR(64),                 -- khớp material_stock (BONG-TUOI, LA-TUOI...)
    qty_kg        NUMERIC(14,3) DEFAULT 0,
    unit_cost_vnd NUMERIC(14,2) DEFAULT 0,     -- ASSUMED: giá thu mua chờ Ngọc Duy xác nhận
    harvest_date  TIMESTAMPTZ,                 -- giờ thu hái (đồng hồ 24h)
    gacp_cert     VARCHAR(128),                -- chứng nhận GACP vùng trồng (nếu có)
    order_id      INTEGER REFERENCES production_orders(id),  -- mua theo đơn (nếu có)
    status        VARCHAR(32) DEFAULT 'received',
    created_at    TIMESTAMPTZ DEFAULT now()
);

-- Mỗi MẺ chế biến (héo→xao→vò→sấy / chiết xuất cao). Idempotent theo batch_code.
-- Traceability: material_lot_code → material_batches (nông hộ, vùng, ngày thu hái).
CREATE TABLE IF NOT EXISTS production_batches (
    id                 SERIAL PRIMARY KEY,
    batch_code         VARCHAR(64) UNIQUE,       -- dedup khi gateway/tablet retry
    order_id           INTEGER REFERENCES production_orders(id),
    material_lot_code  VARCHAR(64),              -- lô nguyên liệu (truy xuất về nông hộ)
    input_material_kg  NUMERIC(14,3) DEFAULT 0,  -- NVL tươi vào (kg)
    output_units       INTEGER DEFAULT 0,        -- TP đóng gói ra (hộp/túi)
    unit_weight_kg     NUMERIC(10,4) DEFAULT 0,  -- kg KHÔ/đơn vị (quy đổi TP→kg khô)
    ng_units           INTEGER DEFAULT 0,        -- phế phẩm đóng gói (KHÁC hao hụt sấy tự nhiên)
    moisture_pct       NUMERIC(5,2),             -- độ ẩm cuối mẻ (quyết định HSD)
    expiry_date        DATE,                     -- HSD tính từ độ ẩm (khô lưu ≤ 1 năm)
    qc_status          VARCHAR(16) DEFAULT 'in_progress', -- in_progress|pending_lab|passed|failed
    material_cost_vnd  NUMERIC(14,2) DEFAULT 0,  -- ASSUMED (G2 đợt 3 tính đủ điện sấy/bao bì)
    labor_cost_vnd     NUMERIC(14,2) DEFAULT 0,
    shift              VARCHAR(16),
    source             VARCHAR(16) DEFAULT 'manual', -- 'iot' | 'manual' (app/tablet tại xưởng)
    created_at         TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_pb_order ON production_batches (order_id);

-- F1: nhật ký từng công đoạn của mẻ (héo/cắt/lên men/xao/vò/sấy — CCP nhiệt độ/độ ẩm)
CREATE TABLE IF NOT EXISTS batch_process_log (
    id           SERIAL PRIMARY KEY,
    batch_code   VARCHAR(64),
    stage        VARCHAR(32),                 -- start|heo|cat|len_men|xao|vo|say|say_lai
    temp_c       NUMERIC(6,2),
    duration_min INTEGER,
    moisture_pct NUMERIC(5,2),
    operator     VARCHAR(128),
    note         TEXT,
    created_at   TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_bpl_batch ON batch_process_log (batch_code);

-- F2: kết quả kiểm nghiệm dược liệu theo lô — GATE CỨNG: chưa đạt = không được bán
CREATE TABLE IF NOT EXISTS lab_test_results (
    id             SERIAL PRIMARY KEY,
    batch_code     VARCHAR(64),
    cynarin_pct    NUMERIC(6,3),              -- hàm lượng dược tính
    mold_cfu_g     INTEGER,                   -- nấm mốc (ngưỡng <100/g)
    pesticide_ok   BOOLEAN,                   -- dư lượng BVTV đạt
    heavy_metal_ok BOOLEAN,                   -- kim loại nặng đạt
    result         VARCHAR(16),               -- passed | failed (code tính, không phải LLM)
    reasons        JSONB DEFAULT '[]'::jsonb, -- lý do fail (nếu có)
    tested_by      VARCHAR(128),              -- lab nội bộ / lab ngoài (ASSUMED: gửi lab ngoài)
    created_at     TIMESTAMPTZ DEFAULT now()
);

-- Catalog SP sản xuất: mẻ chuẩn + định mức yield tươi→khô + kg khô/đơn vị
CREATE TABLE IF NOT EXISTS manuf_products (
    product_code       VARCHAR(64) PRIMARY KEY,
    product_name       VARCHAR(255),
    batch_output_units INTEGER DEFAULT 0,          -- TP/mẻ chuẩn (0 = chưa biết) — ASSUMED
    unit_net_kg        NUMERIC(10,4) DEFAULT 0,    -- kg KHÔ (hoặc cao) / đơn vị đóng gói
    -- ĐỊNH MỨC tươi→khô của NGÀNH (hao hụt sấy là BÌNH THƯỜNG, không phải thất thoát).
    -- Chỉ cảnh báo khi yield THỰC lệch quá định mức. ASSUMED — cần số thật từ Ngọc Duy.
    standard_yield     NUMERIC(6,4) DEFAULT 0      -- vd 0.25 = 4kg tươi → 1kg khô
);

-- BOM: định mức cho 1 ĐƠN VỊ thành phẩm. qty_per_unit tính theo KHÔ (kg khô/cao) hoặc cái.
-- yield_fresh_to_dry <1 nghĩa là NVL mua vào ở dạng TƯƠI: cần mua tươi = thiếu khô / yield (BOM ĐẢO).
CREATE TABLE IF NOT EXISTS bom_materials (
    id                 SERIAL PRIMARY KEY,
    product_code       VARCHAR(64),
    material_code      VARCHAR(64),
    material_name      VARCHAR(255),
    qty_per_unit       NUMERIC(12,4),              -- vd 0.1 kg khô lá atiso / hộp trà
    unit               VARCHAR(16),                -- 'kg khô' | 'cái'
    yield_fresh_to_dry NUMERIC(6,4) DEFAULT 1      -- ASSUMED; 1 = không quy đổi (bao bì)
);
CREATE INDEX IF NOT EXISTS ix_bom_product ON bom_materials (product_code);

-- Tồn kho NVL: dạng KHÔ lưu được (LA, BONG) + bao bì + dạng TƯƠI transient (cửa sổ 24h)
CREATE TABLE IF NOT EXISTS material_stock (
    material_code VARCHAR(64) PRIMARY KEY,
    material_name VARCHAR(255),
    qty_on_hand   NUMERIC(14,3) DEFAULT 0,
    unit          VARCHAR(16),
    avg_unit_cost NUMERIC(14,2) DEFAULT 0          -- ASSUMED với NVL dược liệu
);

-- DS nguyên liệu cần mua cho đơn (QT2) — người duyệt trước khi gửi RFQ tới nông hộ/HTX
CREATE TABLE IF NOT EXISTS material_requirements (
    id                SERIAL PRIMARY KEY,
    order_id          INTEGER REFERENCES production_orders(id),
    materials         JSONB,                       -- [{material_code,need,on_hand,to_buy,unit,buy_unit}]
    estimation_method VARCHAR(32) DEFAULT 'bom',   -- 'bom' | 'llm_fallback'
    batches_suggested INTEGER,
    status            VARCHAR(32) DEFAULT 'draft', -- draft | rfq_sent | materials_received
    created_at        TIMESTAMPTZ DEFAULT now()
);

-- Báo cáo tính sẵn (deterministic) theo mẻ/đơn/kỳ.
-- yield_actual vs định mức: hao hụt sấy tự nhiên KHÔNG báo động; chỉ báo khi lệch định mức.
CREATE TABLE IF NOT EXISTS production_reports (
    id                  SERIAL PRIMARY KEY,
    scope               VARCHAR(16),               -- 'order' | 'shift' | 'period'
    ref                 VARCHAR(64),               -- order_code / shift / period label
    yield_actual_pct    NUMERIC(6,2),              -- kg khô ra / kg tươi vào
    yield_deviation_pct NUMERIC(6,2),              -- lệch so với định mức ngành
    ng_pct              NUMERIC(6,2),
    cost_vnd            NUMERIC(14,2),
    revenue_vnd         NUMERIC(14,2),
    profit_pct          NUMERIC(6,2),
    ai_explanation      TEXT,
    created_at          TIMESTAMPTZ DEFAULT now()
);

-- ─────────────────────────────────────────────────────────────────────────────
-- Seed dữ liệu test (để test-matrix chạy có kết quả xác định)
-- Giá bán = PUBLIC từ ngocduygroup.com ngày 2026-07-11. Tồn/ngưỡng = ASSUMED.
-- ─────────────────────────────────────────────────────────────────────────────
INSERT INTO products (name, code, stock_quantity, low_stock_threshold, price, category) VALUES
 ('Trà atiso túi lọc (50 túi)', 'TRA-TL50', 40,  20, 87000,  'Trà atiso'),
 ('Cao atisô lá khô 1kg',       'CAO-1KG',  5,   10, 843000, 'Cao atiso'),
 -- BONG-400: tồn 12 > ngưỡng chung 10 nhưng < ngưỡng RIÊNG 15 → chứng minh per-product threshold (G1)
 ('Bông atiso sấy khô 400gr',   'BONG-400', 12,  15, 584000, 'Bông atiso'),
 ('Linh chi lát 400gr',         'LINH-400', 30,  10, 344000, 'Dược liệu'),
 ('Trà Thái Nguyên 80gr',       'TRA-TN80', 100, 30, 21000,  'Trà thương mại')
ON CONFLICT (code) DO NOTHING;

INSERT INTO sales (user_id, total_amount, items) VALUES
 (1, 1017000, '[{"name":"Trà atiso túi lọc (50 túi)","qty":2,"price":87000},{"name":"Cao atisô lá khô 1kg","qty":1,"price":843000}]'),
 (2, 261000,  '[{"name":"Trà atiso túi lọc (50 túi)","qty":3,"price":87000}]');

-- Lịch sử bán 28 ngày (cho QT6 forecast moving-average; trà túi lọc là SP bán volume)
INSERT INTO sales (user_id, total_amount, items, created_at)
SELECT 1, 87000 * (2 + (g % 4)),
       ('[{"sku":"TRA-TL50","name":"Trà atiso túi lọc (50 túi)","qty":' || (2 + (g % 4)) || ',"price":87000}]')::text,
       now() - (g || ' days')::interval
FROM generate_series(1, 28) AS g;

-- A1: seed LÔ khớp đúng tồn products (FEFO cần lô + HSD; tổng lô = stock_quantity).
-- TRA-TL50 có 2 lô HSD khác nhau để test FEFO (bán thường → lô 2026-10 trước; quà → lô 2027-04)
INSERT INTO product_lots (sku, lot_code, expiry_date, qty_on_hand, source) VALUES
 ('TRA-TL50', 'LOT-RT-A', '2026-10-01', 15,  'manual'),
 ('TRA-TL50', 'LOT-RT-B', '2027-04-01', 25,  'manual'),
 ('CAO-1KG',  'LOT-RT-C', '2027-02-01', 5,   'manual'),
 ('BONG-400', 'LOT-RT-D', '2026-09-01', 12,  'manual'),
 ('LINH-400', 'LOT-RT-E', '2027-06-01', 30,  'manual'),
 ('TRA-TN80', 'LOT-RT-F', '2026-12-01', 100, 'manual')
ON CONFLICT (lot_code) DO NOTHING;

-- QT7 khuyến mãi đang chạy (nội dung dược liệu → caption AI bắt buộc người duyệt)
INSERT INTO promotions (product_code, product_name, discount_pct, active) VALUES
 ('TRA-TL50', 'Trà atiso túi lọc (50 túi)', 10, true),
 ('LINH-400', 'Linh chi lát 400gr', 15, true);

-- QT9 khách sỉ có công nợ quá hạn (>30 ngày) + opt-in
INSERT INTO customers (code, name, email, phone, debt_amount, last_payment_date, marketing_opt_in) VALUES
 ('KH9001', 'Nguyễn Văn Nợ', 'no@kh.vn', '0912345678', 1500000, CURRENT_DATE - 45, true),
 ('KH9002', 'Trần Thị Hạn',  'han@kh.vn','0987654321',  800000, CURRENT_DATE - 60, false); -- opt-out: KHÔNG gửi

-- ── SẢN XUẤT: catalog + BOM đảo yield + tồn NVL + đơn + lô + mẻ ──────────────
-- ASSUMED toàn bộ định mức/mẻ chuẩn/chi phí — chờ khảo sát Ngọc Duy (docs/DEVIATIONS.md)
INSERT INTO manuf_products (product_code, product_name, batch_output_units, unit_net_kg, standard_yield) VALUES
 ('TRA-TL50', 'Trà atiso túi lọc (50 túi)', 200, 0.1, 0.25),   -- 4kg lá tươi → 1kg trà khô (ASSUMED)
 ('BONG-400', 'Bông atiso sấy khô 400gr',   250, 0.4, 0.20),   -- 5kg bông tươi → 1kg khô (ASSUMED)
 ('CAO-1KG',  'Cao atisô lá khô 1kg',        50, 1.0, 0.05),   -- 20kg lá tươi → 1kg cao (ASSUMED)
 ('TRA-GUNG', 'Trà xanh ướp gừng (hộp)',      0, 0.1, 0)       -- CHƯA có BOM → test LLM fallback
ON CONFLICT (product_code) DO NOTHING;

-- BOM ĐẢO: qty_per_unit theo KHÔ; NVL tươi quy ngược qua yield_fresh_to_dry (ASSUMED)
INSERT INTO bom_materials (product_code, material_code, material_name, qty_per_unit, unit, yield_fresh_to_dry) VALUES
 ('TRA-TL50', 'LA',      'Lá/thân atiso',      0.1, 'kg khô', 0.25),
 ('TRA-TL50', 'TUI-LOC', 'Túi lọc',            50,  'cái',    1),
 ('TRA-TL50', 'HOP-TL',  'Hộp trà túi lọc',    1,   'cái',    1),
 ('TRA-TL50', 'TEM-QR',  'Tem QR truy xuất',   1,   'cái',    1),
 ('BONG-400', 'BONG',    'Bông atiso',         0.4, 'kg khô', 0.20),
 ('BONG-400', 'HOP-400', 'Hộp bông 400gr',     1,   'cái',    1),
 ('BONG-400', 'TEM-QR',  'Tem QR truy xuất',   1,   'cái',    1),
 ('CAO-1KG',  'LA',      'Lá/thân atiso',      1.0, 'kg cao', 0.05),
 ('CAO-1KG',  'HU-1KG',  'Hũ cao 1kg',         1,   'cái',    1),
 ('CAO-1KG',  'TEM-QR',  'Tem QR truy xuất',   1,   'cái',    1);

-- Tồn NVL: khô lưu được + bao bì + tươi transient. Giá thu mua/bao bì = ASSUMED.
INSERT INTO material_stock (material_code, material_name, qty_on_hand, unit, avg_unit_cost) VALUES
 ('LA',        'Lá/thân atiso khô',    20,   'kg khô', 120000),
 ('BONG',      'Bông atiso khô',       30,   'kg khô', 250000),
 ('LA-TUOI',   'Lá/thân atiso tươi',   0,    'kg',     12000),   -- giá thu mua nông hộ ASSUMED
 ('BONG-TUOI', 'Bông atiso tươi',      0,    'kg',     18000),   -- giá thu mua nông hộ ASSUMED
 ('TUI-LOC',   'Túi lọc',              5000, 'cái',    200),
 ('HOP-TL',    'Hộp trà túi lọc',      300,  'cái',    3000),
 ('HOP-400',   'Hộp bông 400gr',       500,  'cái',    4000),
 ('HU-1KG',    'Hũ cao 1kg',           200,  'cái',    15000),
 ('TEM-QR',    'Tem QR truy xuất',     2000, 'cái',    500)
ON CONFLICT (material_code) DO NOTHING;

-- 2 đơn từ khách A (2 khu vực bán — cho báo cáo ĐR/ngân sách khu vực QT7)
INSERT INTO production_orders (order_code, customer_code, product_code, product_name, qty_ordered, unit_price, region, status) VALUES
 ('DH-A-101', 'DL-DAILY-01',  'TRA-TL50', 'Trà atiso túi lọc (50 túi)', 900, 87000,  'Đà Lạt',  'in_progress'),
 ('DH-A-102', 'HCM-DAILY-02', 'BONG-400', 'Bông atiso sấy khô 400gr',   240, 584000, 'TP.HCM', 'in_progress');

-- Lô nguyên liệu mùa vụ tháng 4/2026 (đã chế biến xong — cho traceability mẻ seed)
INSERT INTO material_batches (lot_code, farmer, region_grown, part, form, material_code, qty_kg, unit_cost_vnd, harvest_date, gacp_cert, status) VALUES
 ('LOT-2026T4-001', 'HTX Thuận Phát',    'Đà Lạt - Xuân Thọ', 'lá',   'tuoi', 'LA-TUOI',   450, 12000, '2026-04-05 06:30+07', 'GACP-LD-2025-17', 'processed'),
 ('LOT-2026T4-002', 'Nông hộ Trần Văn B','Đà Lạt - Thái Phiên','bông', 'tuoi', 'BONG-TUOI', 500, 18000, '2026-04-08 07:00+07', NULL,              'processed');

-- 3 mẻ seed (QT6/QT7 có dữ liệu; số để KIỂM TAY):
-- MEB-001: 200kg lá tươi → 500 hộp trà ×0.1 = 50kg khô → yield 25% = ĐÚNG định mức → không cảnh báo
-- MEB-002: 250kg lá tươi → 400 hộp = 40kg khô → yield 16% vs 25% → lệch 36% → CẢNH BÁO thật
-- MEB-003: 500kg bông tươi → 240 hộp ×0.4 = 96kg khô → yield 19.2% vs 20% → lệch 4% → KHÔNG báo giả
INSERT INTO production_batches (batch_code, order_id, material_lot_code, input_material_kg, output_units, unit_weight_kg, ng_units, moisture_pct, expiry_date, qc_status, material_cost_vnd, labor_cost_vnd, shift, source) VALUES
 ('MEB-001', (SELECT id FROM production_orders WHERE order_code='DH-A-101'), 'LOT-2026T4-001', 200.0, 500, 0.1, 5,  6.5, '2027-04-10', 'passed', 2400000, 800000,  'Mẻ sáng',  'manual'),
 ('MEB-002', (SELECT id FROM production_orders WHERE order_code='DH-A-101'), 'LOT-2026T4-001', 250.0, 400, 0.1, 10, 6.8, '2027-04-12', 'passed', 3000000, 900000,  'Mẻ chiều', 'manual'),
 ('MEB-003', (SELECT id FROM production_orders WHERE order_code='DH-A-102'), 'LOT-2026T4-002', 500.0, 240, 0.4, 6,  7.2, '2026-10-15', 'passed', 9000000, 1200000, 'Mẻ sáng',  'iot');
