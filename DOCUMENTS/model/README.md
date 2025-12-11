# Predicting Future Imports Using Deep Learning on Retail Store Products

**Course:** Deep Learning- ICT3.017 - University of Science and Technology of Hanoi  
**Date:** November 4, 2025

---

## 1. Project Overview

Our project implements an intelligent retail import forecasting system using Deep Learning in order to:

- Detect and digitize paper invoices using a YOLO layout detector plus multi-backend OCR pipeline
- Predict future imports, based on historical data, using LSTM models

> **Update (Nov 2025):** Model 1 now runs the fine-tuned YOLOv8 layout detector followed by PaddleOCR/EasyOCR/Tesseract fallbacks. The legacy CNN stage has been fully removed from the codebase.

---

## 2. Input and Output Description

### 2.1 Model 1: Layout-Aware Invoice OCR

#### **Inputs (x1):**

- **Type:** Paper invoice images
- **Format:** PNG/JPG images
- **Resolution:** 800×1000 pixels
- **Source:** User upload via web interface
- **Processing:** YOLO layout detector localizes headers/tables before OCR crops are sent to PaddleOCR

**Sample Input:**

```go
HOA DON BAN HANG
Ngay: 23/10/2025
-------------------------------------------------
San Pham              SL  Don Gia      Thanh Tien
-------------------------------------------------
Product A             12  29,000       348,000
Product B             5   149,000      745,000
...
-------------------------------------------------
                      Tong Cong: 7,472,000 VND
```

#### **Outputs (Y1):**

- **Type:** Electronic invoice data (JSON)
- **Format:** Structured JSON object
- **Contents:** Product names, quantities, unit_price, line_totals

**Sample Output:**

```json
{
  "invoice_id": "INV_20251023_001",
  "date": "23/10/2025",
  "products": [
    {
      "name": "Set 4 đôi khuyên tai",
      "quantity": 1,
      "unit_price": 29000,
      "line_total": 29000
    },
    {
      "name": "Túi bút chữ nhật Kitty nơ 3 màu signatur",
      "quantity": 1,
      "unit_price": 69000,
      "line_total": 69000
    }
  ],
  "num_products": 9,
  "total_amount": 7472000,
  "confidence": 0.89,
  "processing_time": "1.2s"
}
```

---

### 2.2 Model 2: LSTM Quantity Forecasting

#### **Inputs:**

- To build time-series sequences for LSTM, we combine multiple data sources:

| Input | Name | Source | Format | Description |
|-------|------|--------|--------|-------------|
| **x2** | Electronic Invoice | Model 1 Output (Y1) | JSON | Detected products after Model 1 |
| **x3** | Product Stock data | `dataset_product.csv` | CSV → DataFrame | A list of products with prices & stock, prices |
| **x4** | Product Import History | `import_in_a_timescale.csv` | CSV → DataFrame | Historical import records  |
| **x5** | Product Sales History | `sale_in_a_timescale.csv` | CSV → DataFrame | Historical sales records) |

**Input Features (7 features per day):**

1. `sales_quantity`: Daily sales volume
2. `day_of_week`: Encoded day (0-6)
3. `is_weekend`: Binary flag (0/1)
4. `cumulative_sales`: Running total of sales
5. `days_since_import`: Days since last import
6. `initial_stock`: Starting inventory level
7. `retail_price`: Product selling price

**Time-Series:**

- **Sequence Length:** 7 days lookback
- **Shape:** (batch_size, 7, 7) - 7 timesteps, 7 features each

#### **Outputs (Y2):**

- **Type:** Predicted import quantities with confidence scores
- **Format:** JSON object with forecasting details

**Sample Output:**

```json
{
  "prediction_date": "2025-11-04",
  "forecast_period": "14 days",
  "predicted_products": [
    {
      "product_name": "Set 4 đôi khuyên tai",
      "current_quantity": 1,
      "predicted_import_quantity": 24,
      "confidence": 0.85,
      "trend": "Increasing",
      "historical_sales_avg": 107.1,
      "reasoning": "Based on 30-day sales velocity"
    },
  ],
  "total_predicted_import": 142,
  "overall_confidence": 0.83,
  "heuristic_formula": "(historical_sales / 30) × 14"
}
```

---

## 3. Obtained Outcomes

### 3.1 Model 1 (Layout Detector + OCR) Results

- Successfully digitizes paper invoices to structured JSON data for Model 2 input
- Handles Vietnamese product names with UTF-8 encoding
- YOLO layout detector boosts OCR accuracy by cropping table regions only

---

### 3.2 Model 2 (LSTM Forecasting) Results

- Accurate time-series forecasting with LSTM
- Real-time predictions based on sales trends
- Confidence scoring.
- Trend analysis: Increasing/Stable/Decreasing

---

## 4. Project Flow

Our system follows a simple 2-step pipeline:

### Step 1: Invoice Detection (Model 1 - Layout Detector + OCR)

1. User uploads paper invoice image via web interface
2. YOLOv8 layout detector finds table/header/total regions
3. Cropped table regions are fed through PaddleOCR with EasyOCR/Tesseract fallbacks
4. Parsed text is converted into structured product line items (Y1)

### Step 2: Quantity Forecasting (Model 2 - LSTM)

1. System takes electronic invoice from Step 1
2. Loads historical data from CSV files (imports, sales, product catalog)
3. Creates 7-day time-series sequences with 7 features
4. LSTM model predicts future import quantities
5. Output: Predicted quantities with confidence scores (Y2)

### Workflow Diagram

![Project Workflow Flowchart](https://raw.githubusercontent.com/wikiepeidia/predict-future-import-for-Retail-store-products/refs/heads/main/images/FLOW.jpg)

---

## 5. Source Code Tutorial

### 5.1 Installation & Setup

#### **Prerequisites:**

- Python 3.8 or higher
- `pip` package manager
- 2GB RAM reserved for training

#### **Step 1: Clone Repository**

```bash
git clone https://github.com/wikiepeidia/predict-future-import-for-Retail-store-products.git
cd predict-future-import-for-Retail-store-products
```

#### **Step 2: Install Dependencies**

```bash
pip install DEPENDENCY_NAME==VERSION
```

**Key Dependencies:**

- `tensorflow==2.15.0` - Deep learning framework
- `flask==3.0.0` - Web framework
- `pandas==2.3.3` - Data manipulation
- `numpy==1.26.0` - Numerical operations
- `pillow==10.0.0` - Image processing
- `scikit-learn==1.3.0` - Machine Learning utilities

#### **Step 3: Dataset**

- You can download the pre-generated invoices from <https://www.kaggle.com/datasets/thminhphm/invoice-datasets>
- Unzip the folder in `data/generated_invoices/`

---

### 5.2 Running the Project

#### **Step 1: Generate Synthetic Dataset**

```bash
python data/generate_invoice.py
```

**Output:**

```go
Generated files:
  - data/generated_invoices/train/ (280 images)
  - data/generated_invoices/valid/ (80 images)
  - data/generated_invoices/test/ (40 images)
  - train_metadata.json
  - valid_metadata.json
  - test_metadata.json
```

---

#### **Step 2: Train Layout Detector (YOLOv8)**

```bash
python train_cnn_models.py
```

Despite the filename, this script now prepares YOLO-style datasets, fine-tunes the layout detector, copies the resulting `best.pt` into `saved_models/layout_detector/weights/`, and immediately verifies that `services.layout_service` can load it.

**Output:**

- Fine-tuned weights stored under `saved_models/layout_detector/weights/best.pt`
- Optional base checkpoints (`yolov8n.pt`, `yolo11n.pt`) kept inside `saved_models/`

---

#### **Step 3: Train LSTM Model (Quantity Forecasting)**

```bash
python train_lstm_model.py
```

**Output:**

- Trained model will be saved to `saved_models/lstm_text_recognizer.weights.h5`
- Scalers will be saved to `saved_models/lstm_text_recognizer.weights_scaler.pkl`

---

#### **Step 4: Start Backend service for Web**

```bash
python app.py
```

- Server will be hosted at: <http://localhost:5000>

#### **Accuracy Dashboard (New)**

- Every `/api/model1/detect` response now includes a `metrics` payload with per-invoice layout confidence, OCR precision, rolling averages, and the most recent YOLO training mAP values.
- The UI displays these numbers in the “Accuracy Metrics” panel so stakeholders can track improvements after each training run.

---

### 5.3 Key Code Components

#### **Frontend Interface**

- The front end interface is built with HTML, CSS, and JavaScript to provide a simple two-step workflow for users.

**HTML Structure: `ui/templates/index.html`**

```html
<div class="container">
    <!-- Model 1: Layout Detector + OCR -->
    <div class="model-card">
        <div class="model-header">
        <h2>Model 1: Layout + OCR</h2>
            <p>Paper Invoice → Electronic Invoice (OCR)</p>
        </div>
        <button class="predict-btn" onclick="predictModel1()" id="predictBtn1">
                Convert to Electronic Invoice (OCR)
            </button>
    </div>

    <!-- Model 2: Quantity Forecasting -->
    <div class="model-card">
        <div class="model-header">
            <h2>Model 2: LSTM</h2>
            <p>Import Quantity Prediction</p>
        </div>
        <!-- Predict button -->
            <button class="predict-btn" onclick="predictModel2()" id="predictBtn2">
                Predict Next Import Quantities
            </button>
    </div>
</div>
```

**CSS Styling: `ui/static/styles.css`**

```css
/* Modern gradient background */
body {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
    min-height: 100vh;
    color: #333;
    padding: 20px;
    line-height: 1.6;
}
/* Animations*/
@keyframes spin{}
@keyframes fadeIn{}
/*Hover effects*/
.product-table tbody tr:hover {
    background: #f8f9fa;
}
```

#### **Backend API Structure**

**Main Application (`app.py`):**

- Registers 3 API blueprints: `/api/model1`, `/api/model2`, `/api/history`
- Serves web interface at <http://localhost:5000>

**Model 1 Endpoint (`api/model1_routes.py`):**

```python
@model1_bp.route('/detect', methods=['POST'])
def detect_invoice():
  # Receives uploaded image
  # Runs YOLO layout detector + OCR fusion
  # Returns electronic invoice (Y1) as JSON
```

**Model 2 Endpoint (`api/model2_routes.py`):**

```python
@model2_bp.route('/predict', methods=['POST'])
def predict_quantities():
    # Receives Y1 from Model 1
    # Loads historical CSV data
    # Runs LSTM inference
    # Returns predictions (Y2) as JSON
```

---

#### **Core Model Methods**

**Layout Service (`services/layout_service.py`):**

```python
def detect_layout_regions(image):
  # Run YOLOv8 on invoice
  # Take best bbox per class (header/table/totals)
  # Clamp + return regions for downstream crops
```

**LSTM Model (`models/lstm_model.py`):**

```python
class ImportForecastLSTM:
    def predict(self, sequences):
        # Normalize 7-day sequences
        # LSTM inference (3-layer: 128→64→32)
        # Denormalize predictions
        return predicted_quantities
```

**Forecast Service (`services/forecast_service.py`):**

```python
def generate_forecast(current_invoice, history, model):
    # For each product in invoice:
    #   1. Get historical data
    #   2. Create 7-day sequence
    #   3. LSTM prediction
    #   4. Apply heuristic: (sales_30d / 30) × 14
    #   5. Calculate confidence
    return {predictions, confidence, trends}
```

---

#### **Model Architectures**

**Layout Detector (YOLOv8):**

- **Base:** Ultralytics YOLOv8n pretrained on COCO
- **Fine-Tuning:** Synthetic invoice dataset with header/table/totals classes

**LSTM (Quantity Forecasting):**

- **Input:** (7 days, 7 features)
- **Layers:** LSTM(128) → LSTM(64) → LSTM(32) → Dense(16) → Dense(1)

---

### 5.4 Usage

**Start the webserver:**

```bash
python app.py 
```

- Access at: <http://localhost:5000>
**Test via web interface:**

1. Upload invoice image- up to 3 images.
2. View detected products (Y1)
3. View import predictions (Y2)

---

## 6. Evaluation Results

- Layout detector quality is inspected visually after each training run (the `train_cnn_models.py` script saves crops and logs top detections). Quantitative mAP tracking will be added in the accuracy-reporting task.
- LSTM convergence remains stable with validation metrics closely matching training values.

| Model | Final Training Loss | Final Validation Loss | Final Training MAE | Final Validation MAE | Total Epochs |
|:------|:-------------------:|:---------------------:|:------------------:|:--------------------:|:-------------:|
| **LSTM** | 0.0044 | 0.0021 | 0.0403 | 0.0226 | 16 |

---

## 7. Conclusion

This project successfully demonstrates:

- **Automated Invoice Digitization** using YOLO layout detection plus multi-backend OCR  
- **Intelligent Forecasting** using LSTM-based time-series prediction  
- **Real-time Processing** with Flask web interface  

The system provides retail businesses with an end-to-end solution for:

- Converting paper invoices to structured data
- Predicting future import needs based on sales patterns
- Optimizing inventory management with confidence-scored recommendations

Future Improvements:

- Real-world invoice image processing (OCR integration)
- Multi-store support with location-based forecasting
- Real-time dashboard with live data streaming
- Mobile application for on-site invoice capture

---

## 8. References

**Dataset:**

<https://www.kaggle.com/datasets/thminhphm/invoice-datasets>

**Code Repository:**  
<https://github.com/wikiepeidia/predict-future-import-for-Retail-store-products>

**Team Members:**

| No. | Name | Student ID | Major | Email |
|:--:|:---------------------------|:------------:|:------:|:------------------------------------|
| 1 | **Hà Thái Sơn** | 23BI14386 | ICT | <sonht.23bi14386@usth.edu.vn> |
| 2 | **Nguyễn Duy Ngọc** | 23BI14342 | ICT | <ngocnd.23bi14342@usth.edu.vn> |
| 3 | **Trần Quốc Thái** | 23BI14396 | ICT | <thaitq.23bi14396@usth.edu.vn> |
| 4 | **Phạm Thế Minh** | 23BI14279 | ICT | <minhpt.23bi14279@usth.edu.vn> |
| 5 | **Nguyễn Mạnh Khánh An** | 23BI14003 | ICT | <annmk.23bi14003@usth.edu.vn> |
| 6 | **Phạm Ngọc Tùng** | 23BI14444 | ICT | <tungpn.23bi14444@usth.edu.vn> |

---
