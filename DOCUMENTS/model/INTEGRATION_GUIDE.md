# Quick Integration Guide: OOD Detection for Your System

## 🚀 Quick Start (30 minutes)

### Step 1: Enable MC Dropout (Uncertainty Estimation)

**File: `models/lstm_model.py`**

Replace your LSTM model definition with this:

```python
def build_model_with_mc_dropout(self):
    """Build LSTM with MC Dropout for uncertainty estimation"""
    model = models.Sequential([
        layers.Input(shape=(self.lookback, self.features)),
        
        # LSTM Layer 1 with MC Dropout
        layers.LSTM(128, return_sequences=True, activation='tanh'),
        layers.Dropout(0.3),  # THIS STAYS ON AT TEST TIME
        layers.BatchNormalization(),
        
        # LSTM Layer 2
        layers.LSTM(64, return_sequences=True, activation='tanh'),
        layers.Dropout(0.3),  # THIS STAYS ON AT TEST TIME
        layers.BatchNormalization(),
        
        # LSTM Layer 3
        layers.LSTM(32, return_sequences=False, activation='tanh'),
        layers.Dropout(0.3),  # THIS STAYS ON AT TEST TIME
        
        # Dense layers
        layers.Dense(64, activation='relu'),
        layers.Dropout(0.2),  # THIS STAYS ON AT TEST TIME
        layers.Dense(32, activation='relu'),
        
        # Output
        layers.Dense(1, activation='relu')
    ])
    
    model.compile(
        optimizer=keras.optimizers.Adam(learning_rate=0.01, clipnorm=1.0),
        loss=keras.losses.Huber(delta=1.0),
        metrics=['mae']
    )
    
    return model
```

### Step 2: Add Uncertainty Estimation Method

**File: `models/lstm_model.py`** - Add to `ImportForecastLSTM` class:

```python
def predict_with_uncertainty(self, X, num_samples=50):
    """
    Predict with uncertainty using MC Dropout
    
    Returns:
        mean: Mean prediction
        std: Standard deviation (uncertainty measure)
        confidence: 1 - normalized_std (0=uncertain, 1=confident)
    """
    predictions = []
    
    # Multiple forward passes with dropout enabled
    for _ in range(num_samples):
        pred = self.model(X, training=True)
        predictions.append(pred.numpy())
    
    predictions = np.array(predictions).squeeze()
    mean = np.mean(predictions)
    std = np.std(predictions)
    
    # Normalize std relative to prediction magnitude
    confidence = 1.0 / (1.0 + std / (mean + 1e-6))  # sigmoid(mean/std)
    
    return mean, std, confidence
```

### Step 3: Update Forecast Service

**File: `services/forecast_service.py`** - Modify prediction function:

```python
def predict_import_quantity_enhanced(product_name, product_info, imports_dict, sales_dict):
    """
    Predict with OOD detection and uncertainty
    """
    from utils.ood_detection import FallbackPredictor
    
    lstm_model = get_lstm_model()
    
    # Prepare features (your existing code)
    features = prepare_features_for_lstm(...)
    X = np.array(features).reshape(1, lstm_model.lookback, lstm_model.features)
    
    # Get prediction with uncertainty
    mean_pred, std_pred, confidence = lstm_model.predict_with_uncertainty(X)
    
    # Threshold for OOD detection
    if confidence < 0.6:  # Low confidence = likely OOD
        # Use fallback strategy
        historical_imports = imports_dict.get(product_name, [])
        fallback_pred = FallbackPredictor.exponential_smoothing(historical_imports)
        
        return {
            'quantity': fallback_pred,
            'confidence': 0.5,  # Lower confidence for fallback
            'uncertainty': std_pred,
            'status': 'OOD_FALLBACK',
            'method': 'exponential_smoothing'
        }
    
    return {
        'quantity': mean_pred,
        'confidence': confidence,
        'uncertainty': std_pred,
        'status': 'ID_CONFIDENT',
        'method': 'lstm'
    }
```

---

## 🔧 Step 2: Add OOD Detection (60 minutes)

### Step 1: Extract Hidden Features

**File: `models/lstm_model.py`** - Add feature extraction:

```python
def build_feature_extractor(self):
    """Create model to extract hidden features before output layer"""
    if self.model is None:
        return None
    
    # Get features from penultimate layer (before output)
    self.feature_extractor = keras.Model(
        inputs=self.model.input,
        outputs=self.model.layers[-3].output  # Adjust index as needed
    )
    return self.feature_extractor

def extract_features(self, X):
    """Extract hidden representations"""
    if self.feature_extractor is None:
        self.build_feature_extractor()
    return self.feature_extractor.predict(X, verbose=0)
```

### Step 2: Initialize OOD Detector During Training

**File: `models/lstm_model.py`** - After training:

```python
def train_with_ood_detection_setup(self, X_train, y_train, epochs=50):
    """Train and prepare OOD detector"""
    from utils.ood_detection import OODDetector
    
    # Train model
    self.model.fit(
        X_train, y_train,
        epochs=epochs,
        validation_split=0.2,
        verbose=0
    )
    
    # Initialize OOD detector on training features
    train_features = self.extract_features(X_train)
    self.ood_detector = OODDetector(method='mahalanobis', threshold=0.6)
    self.ood_detector.fit(train_features)
    
    return self
```

### Step 3: Predict with OOD Detection

**File: `models/lstm_model.py`** - Add method:

```python
def predict_with_ood_detection(self, X):
    """
    Predict with OOD detection
    
    Returns:
        prediction: Forecast quantity
        ood_score: 0 (ID) to 1 (OOD)
        is_ood: Boolean flag
    """
    prediction = self.model.predict(X, verbose=0)[0, 0]
    
    if self.ood_detector is None:
        return prediction, 0.0, False
    
    # Extract features and compute OOD score
    features = self.extract_features(X)
    ood_scores = self.ood_detector.score(features)
    ood_score = ood_scores[0]
    
    is_ood = ood_score > self.ood_detector.threshold
    
    return prediction, ood_score, is_ood
```

### Step 4: Enhanced Forecast Service

**File: `services/forecast_service.py`** - Add enhanced function:

```python
def predict_with_full_ood_handling(product_name, product_info, imports_dict, sales_dict):
    """
    Full OOD handling pipeline
    """
    from utils.ood_detection import FallbackPredictor, UncertaintyEstimator
    
    lstm_model = get_lstm_model()
    
    # Prepare input
    X = prepare_features(product_name, product_info)
    X = np.array(X).reshape(1, lstm_model.lookback, lstm_model.features)
    
    # Get predictions
    pred_lstm, ood_score, is_ood = lstm_model.predict_with_ood_detection(X)
    mean_pred, std_pred, confidence = lstm_model.predict_with_uncertainty(X)
    
    # Determine action based on OOD detection
    if is_ood or confidence < 0.5:
        # Use fallback
        hist = imports_dict.get(product_name, [100, 110, 120])
        fallback_pred = FallbackPredictor.exponential_smoothing(hist)
        
        result = {
            'quantity': int(fallback_pred),
            'confidence': 0.4,
            'uncertainty': std_pred,
            'ood_score': ood_score,
            'status': 'OOD',
            'reason': 'Product not in training distribution',
            'method': 'fallback_exponential_smoothing'
        }
    else:
        # Use LSTM
        result = {
            'quantity': int(pred_lstm),
            'confidence': float(confidence),
            'uncertainty': std_pred,
            'ood_score': ood_score,
            'status': 'ID',
            'reason': 'Confident prediction from LSTM',
            'method': 'lstm_with_mc_dropout'
        }
    
    return result
```

---

## 📊 Step 3: Evaluation & Testing (30 minutes)

### Create Test Script

**File: `evaluate_ood.py`** - New file:

```python
"""
Evaluate OOD detection performance
"""
import numpy as np
from utils.ood_detection import OODDetector

def evaluate_ood_detection():
    """
    Simulate OOD detection on ID vs OOD samples
    """
    # Generate synthetic in-distribution data
    id_features = np.random.randn(100, 64) + 0  # Center at 0
    
    # Generate synthetic out-of-distribution data
    ood_features = np.random.randn(50, 64) + 5  # Center at 5 (shifted)
    
    # Train OOD detector
    detector = OODDetector(method='mahalanobis', threshold=0.5)
    detector.fit(id_features)
    
    # Score test samples
    id_scores = detector.score(id_features[:20])
    ood_scores = detector.score(ood_features)
    
    # Evaluate
    metrics = detector.evaluate(id_scores, ood_scores)
    
    print("=" * 60)
    print("OOD Detection Evaluation")
    print("=" * 60)
    print(f"AUROC: {metrics['auroc']:.3f} (higher is better)")
    print(f"FPR@95%TPR: {metrics['fpr_95_tpr']:.3f} (lower is better)")
    print(f"Best threshold: {metrics['best_threshold']:.3f}")
    print()
    print(f"ID samples: mean OOD score = {np.mean(id_scores):.3f}")
    print(f"OOD samples: mean OOD score = {np.mean(ood_scores):.3f}")
    
    return metrics

if __name__ == '__main__':
    evaluate_ood_detection()
```

**Run it:**
```bash
python evaluate_ood.py
```

---

## 🎯 Recommended Implementation Order

### Immediate (Week 1)
- ✅ Enable MC Dropout in `build_model()`
- ✅ Add `predict_with_uncertainty()` method
- ✅ Integrate fallback strategies

### Short-term (Week 2)
- ✅ Add OOD detector with Mahalanobis distance
- ✅ Create feature extractor
- ✅ Update forecast service

### Medium-term (Week 3+)
- ✅ Build ensemble forecaster (3-5 models)
- ✅ Implement open-set LSTM with "unknown" class
- ✅ Add data augmentation with synthetic OOD

---

## 📈 Key Metrics to Monitor

### OOD Detection Quality
```python
# In forecast_service.py after predictions
metrics = {
    'true_positive_rate': len([p for p in predictions if p['ood'] and is_actually_ood]) / total_ood,
    'false_positive_rate': len([p for p in predictions if p['ood'] and not is_actually_ood]) / total_id,
    'confidence_calibration': compute_calibration_error(predictions),
}
```

### Forecast Accuracy
```python
# Compare with/without OOD handling
mae_with_ood = mean_absolute_error(y_true, y_pred_with_ood)
mae_without_ood = mean_absolute_error(y_true, y_pred_without_ood)

print(f"MAE improvement: {(1 - mae_with_ood/mae_without_ood)*100:.1f}%")
```

---

## 🔗 File Dependencies

```
models/
  └─ lstm_model.py          (Add uncertainty & OOD methods)

services/
  └─ forecast_service.py     (Update prediction functions)

utils/
  ├─ ood_detection.py        (New file - ready to use)
  └─ logger.py              (Existing)

Root/
  ├─ OOD_STRATEGIES.md       (Theory & explanations)
  ├─ INTEGRATION_GUIDE.md    (This file)
  └─ evaluate_ood.py         (New testing script)
```

---

## 🧪 Testing with Your Real Data

```python
# Test with actual products
from services.forecast_service import predict_with_full_ood_handling
from services.forecast_service import load_timescale_data

product_info, imports_dict, sales_dict = load_timescale_data()

# Test on known product
result = predict_with_full_ood_handling(
    'Coca Cola', 
    product_info['Coca Cola'],
    imports_dict,
    sales_dict
)
print(f"Known product: {result}")

# Simulate OOD product by passing empty history
result = predict_with_full_ood_handling(
    'Totally New Product',
    {'initial_stock': 0, 'retail_price': 50000},
    {},  # No import history
    {}   # No sales history
)
print(f"Unknown product: {result}")
```

---

## ✅ Validation Checklist

- [ ] MC Dropout enabled in LSTM
- [ ] `predict_with_uncertainty()` returns (mean, std, confidence)
- [ ] OOD detector fitted on training features
- [ ] Fallback predictor returns reasonable values for OOD
- [ ] Forecast service returns `status` field ('ID' or 'OOD')
- [ ] Evaluation script shows AUROC > 0.85
- [ ] Integration tests pass with real data
- [ ] API returns confidence scores
- [ ] Unknown products trigger fallback gracefully

---

## 📞 Debugging Tips

### Issue: Predictions too uncertain for all samples
- **Solution**: Reduce MC Dropout rate from 0.3 to 0.2
- **Check**: Are training and test data distributions similar?

### Issue: OOD detector not working
- **Solution**: Check that `training_stats` is not None
- **Debug**: `print(ood_detector.training_stats.keys())`

### Issue: Fallback predictions too conservative
- **Solution**: Try different strategies (moving_average, seasonal_naive)
- **Benchmark**: Compare MAE of each fallback method

### Issue: Ensemble too slow
- **Solution**: Reduce to 2-3 models instead of 5
- **Alternative**: Use MC Dropout (single model, faster)

---

## 📚 References in Code

See `OOD_STRATEGIES.md` for:
- Theoretical background
- Advanced methods (contrastive learning, domain adaptation)
- Research papers and citations

See `utils/ood_detection.py` for:
- Ready-to-use implementations
- Class interfaces and parameters
- Example usage patterns
