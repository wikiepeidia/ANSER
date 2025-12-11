# Out-of-Distribution (OOD) Product Recognition Strategies

## Overview
Your system currently:
- **YOLO Layout Detector**: Detects invoice regions (header, table, totals)
- **OCR Service**: Extracts text from invoices (PaddleOCR)
- **LSTM Forecaster**: Predicts import quantities based on historical data (14,367 products)

The challenge: New products not in training data may not be recognized or predicted accurately.

---

## 1. Detection & Monitoring Methods

### 1.1 Confidence Score Analysis
**Implementation**: Monitor prediction confidence thresholds
```python
def detect_ood_by_confidence(model_output, confidence_threshold=0.5):
    """Flag products with low model confidence"""
    if model_output.confidence < confidence_threshold:
        return "OOD_DETECTED"
    return "ID"
```

**For Your System**:
- YOLO: Currently outputs confidence scores for detections
- LSTM: Add confidence intervals (Bayesian uncertainty)

### 1.2 Maximum Softmax Probability (MSP)
**How it works**: Models with softmax layers output probability distributions. OOD samples often have lower max probability.

```python
def msp_score(model_logits):
    """Maximum softmax probability"""
    probs = softmax(model_logits)
    return np.max(probs)

def detect_ood_msp(probs, msp_threshold=0.7):
    if np.max(probs) < msp_threshold:
        return "OOD"
    return "ID"
```

**For Your LSTM**:
- Extract penultimate layer features (before Dense output)
- Compute confidence from magnitude of activation

### 1.3 Distance-Based Methods
**Mahalanobis Distance**: Measure feature distance to training distribution
```python
def compute_mahalanobis_distance(features, train_features_mean, cov_matrix):
    """Distance to training feature distribution"""
    diff = features - train_features_mean
    md = np.sqrt(diff @ np.linalg.inv(cov_matrix) @ diff.T)
    return md
```

**For Your System**:
- Extract LSTM hidden state before output layer
- Store statistics of training hidden states
- Compare new products' hidden states

### 1.4 Energy-Based OOD Detection
Treats the model as energy function where ID samples have low energy
```python
def energy_based_ood(logits):
    """Lower energy = more likely ID"""
    energy = -np.log(np.exp(logits).sum())
    return energy
```

---

## 2. Architecture Modifications

### 2.1 Add Auxiliary Classifier (Open-Set Recognition)
Modify LSTM to include "Unknown Product" class:
```python
def build_open_set_lstm(lookback, features):
    model = Sequential([
        # ... existing LSTM layers ...
        layers.LSTM(32, return_sequences=False),
        layers.Dense(64, activation='relu'),
        layers.Dense(32, activation='relu'),
        
        # Original regression head (for known products)
        layers.Dense(1, name='quantity_output', activation='relu'),
        
        # New: Binary classifier for ID vs OOD
        layers.Dense(1, name='ood_classifier', activation='sigmoid')
    ])
    
    model.compile(
        optimizer='adam',
        loss={
            'quantity_output': 'mse',
            'ood_classifier': 'binary_crossentropy'
        },
        metrics=['mae']
    )
    return model
```

### 2.2 Mixture of Experts (MoE)
Route unknown products to a separate model:
```python
def mixture_of_experts_forward(input_data):
    # Router network
    is_known = router_network(input_data)
    
    if is_known > 0.5:
        # Known product - use LSTM forecaster
        prediction = lstm_model(input_data)
    else:
        # Unknown product - use fallback strategy
        prediction = fallback_model(input_data)
    
    return prediction, is_known
```

### 2.3 Residual Network (Add Skip Connection)
```python
def build_residual_lstm(lookback, features):
    inputs = layers.Input(shape=(lookback, features))
    
    # Main path
    x = layers.LSTM(128, return_sequences=True)(inputs)
    x = layers.LSTM(64, return_sequences=False)(x)
    x = layers.Dense(64, activation='relu')(x)
    
    # Skip connection (add auxiliary path)
    skip = layers.Dense(64, activation='relu')(inputs[:, -1, :])
    x = layers.Add()([x, skip])
    
    output = layers.Dense(1, activation='relu')(x)
    
    model = keras.Model(inputs, output)
    return model
```

---

## 3. Ensemble Methods

### 3.1 Deep Ensemble
Train multiple LSTM models with different initializations:
```python
def build_ensemble_forecast(num_models=3, lookback=30, features=5):
    ensemble = []
    for i in range(num_models):
        model = build_lstm_model(lookback, features)
        # Different random seed per model
        np.random.seed(i)
        model.fit(X_train, y_train)
        ensemble.append(model)
    
    return ensemble

def predict_with_ensemble(ensemble, X):
    predictions = []
    for model in ensemble:
        pred = model.predict(X)
        predictions.append(pred)
    
    # Return mean and variance as uncertainty
    mean = np.mean(predictions, axis=0)
    std = np.std(predictions, axis=0)
    return mean, std  # std = uncertainty measure
```

### 3.2 Monte Carlo Dropout
Enable dropout at inference time for uncertainty estimation:
```python
def build_mc_dropout_lstm(lookback, features):
    model = Sequential([
        layers.LSTM(128, return_sequences=True),
        layers.Dropout(0.5),  # Enable dropout at test time too
        layers.LSTM(64, return_sequences=False),
        layers.Dropout(0.5),
        layers.Dense(32, activation='relu'),
        layers.Dropout(0.5),
        layers.Dense(1, activation='relu')
    ])
    return model

def predict_with_uncertainty(model, X, num_samples=100):
    """Forward pass with dropout enabled (Monte Carlo)"""
    predictions = []
    for _ in range(num_samples):
        # Set training=True to enable dropout
        pred = model(X, training=True)
        predictions.append(pred.numpy())
    
    mean = np.mean(predictions, axis=0)
    std = np.std(predictions, axis=0)
    return mean, std  # std = aleatoric uncertainty
```

---

## 4. Training Strategies

### 4.1 Data Augmentation (Synthetic OOD)
Create "fake new products" during training:
```python
def augment_with_synthetic_ood(X_train, y_train, contamination_rate=0.1):
    """Add synthetic OOD samples (out-of-range values)"""
    n_synthetic = int(len(X_train) * contamination_rate)
    
    # Generate OOD samples: mix random products with extreme values
    indices = np.random.choice(len(X_train), n_synthetic)
    X_ood = X_train[indices].copy()
    
    # Add noise to push outside training distribution
    X_ood = X_ood * np.random.uniform(0.1, 5.0)  # Extreme multipliers
    y_ood = y_train[indices] * np.random.uniform(0.05, 10.0)
    
    # Combine with original data
    X_augmented = np.vstack([X_train, X_ood])
    y_augmented = np.hstack([y_train, y_ood])
    
    return X_augmented, y_augmented
```

### 4.2 Contrastive Learning
Learn to distinguish known vs unknown patterns:
```python
def triplet_loss_lstm(anchor, positive, negative, margin=1.0):
    """
    anchor: feature from known product
    positive: another sample from same product
    negative: feature from different product
    """
    d_pos = np.linalg.norm(anchor - positive)
    d_neg = np.linalg.norm(anchor - negative)
    
    loss = max(d_pos - d_neg + margin, 0)
    return loss
```

### 4.3 Domain Adaptation
Pre-train on large public datasets, fine-tune on your data:
```python
# Stage 1: Pre-train on public time-series dataset (e.g., UCR datasets)
pretrained_model = load_pretrained_lstm()

# Stage 2: Fine-tune on your invoice data (transfer learning)
model = keras.models.clone_model(pretrained_model)
model.compile(optimizer='adam', loss='mse')
model.fit(X_train, y_train, epochs=10, validation_split=0.2)
```

---

## 5. Fallback Strategies for OOD Products

### 5.1 Rule-Based Default Prediction
```python
def predict_ood_product(product_info):
    """Fallback for unknown products"""
    if product_ood_detected:
        # Strategy 1: Predict based on similar known products
        similar_products = find_similar_by_name(product_name)
        avg_prediction = np.mean([lstm_forecast(p) for p in similar_products])
        return avg_prediction, confidence=0.5
```

### 5.2 Statistical Baseline
```python
def statistical_fallback(historical_sales, historical_imports):
    """Use statistics when model fails"""
    # Predict using exponential smoothing
    from statsmodels.tsa.holtwinters import ExponentialSmoothing
    
    if len(historical_sales) < 3:
        return np.median(historical_imports)  # Last resort: median
    
    es = ExponentialSmoothing(historical_sales, trend='add')
    fit = es.fit()
    forecast = fit.fittedvalues[-1]
    return forecast
```

### 5.3 Human-in-the-Loop
```python
def handle_ood_with_feedback(product_name, ood_confidence):
    """Request user input for uncertain products"""
    if ood_confidence > UNCERTAINTY_THRESHOLD:
        # Flag for manual review
        return {
            'product': product_name,
            'needs_review': True,
            'confidence': ood_confidence,
            'suggested_action': 'MANUAL_INPUT_REQUIRED'
        }
```

---

## 6. Evaluation Methods for OOD Detection

### 6.1 AUROC (Area Under ROC Curve)
```python
from sklearn.metrics import roc_auc_score

def evaluate_ood_detection(id_scores, ood_scores):
    """Higher AUROC = better OOD detection"""
    y_true = np.concatenate([np.ones(len(id_scores)), 
                             np.zeros(len(ood_scores))])
    y_scores = np.concatenate([id_scores, ood_scores])
    auroc = roc_auc_score(y_true, y_scores)
    return auroc
```

### 6.2 False Positive Rate (FPR) at 95% True Positive Rate (TPR)
```python
def fpr_at_95_tpr(id_scores, ood_scores):
    """How many OOD falsely classified as ID?"""
    from sklearn.metrics import roc_curve
    
    y_true = np.concatenate([np.ones(len(id_scores)), 
                             np.zeros(len(ood_scores))])
    y_scores = np.concatenate([id_scores, ood_scores])
    
    fpr, tpr, _ = roc_curve(y_true, y_scores)
    idx = np.argmin(np.abs(tpr - 0.95))
    return fpr[idx]
```

### 6.3 Prediction Accuracy on OOD
```python
def evaluate_ood_forecast_quality(model, ood_test_data):
    """How accurate are OOD predictions?"""
    predictions = model.predict(ood_test_data)
    mae = np.mean(np.abs(predictions - ood_test_data.y))
    return mae  # Lower is better
```

---

## 7. Quick Start Implementation Plan

### Phase 1: Detection (No Architecture Change)
1. Add confidence thresholding to LSTM output
2. Store hidden state statistics from training
3. Compute distance-based OOD scores at inference

### Phase 2: Moderate Changes
1. Add MC Dropout for uncertainty estimation
2. Implement ensemble of 3 LSTM models
3. Create statistical fallback

### Phase 3: Advanced
1. Build open-set LSTM with "unknown" class
2. Implement mixture of experts routing
3. Add contrastive learning

---

## 8. Integration with Your Current System

### For `models/lstm_model.py`:
```python
class ImportForecastLSTM:
    def __init__(self, lookback=30, features=5, enable_ood=True):
        self.lookback = lookback
        self.features = features
        self.enable_ood = enable_ood
        self.training_feature_stats = None  # Store for OOD detection
        
    def predict_with_ood_detection(self, X):
        """Return (prediction, ood_confidence)"""
        prediction = self.model.predict(X)
        
        if self.enable_ood:
            # Get hidden state
            feature_extractor = keras.Model(
                inputs=self.model.input,
                outputs=self.model.layers[-3].output  # Before output layer
            )
            features = feature_extractor.predict(X)
            
            # Compute OOD score
            ood_score = self._compute_ood_score(features)
            return prediction, ood_score
        
        return prediction, None
    
    def _compute_ood_score(self, features):
        """Score from 0 (ID) to 1 (OOD)"""
        from scipy.spatial.distance import mahalanobis
        
        md = mahalanobis(
            features[0],
            self.training_feature_stats['mean'],
            self.training_feature_stats['cov_inv']
        )
        ood_score = 1.0 / (1.0 + np.exp(-md))  # Sigmoid
        return ood_score
```

### For `services/forecast_service.py`:
```python
def predict_import_quantity_with_ood_handling(product_name, product_info):
    """Enhanced prediction with OOD detection"""
    
    # Get LSTM prediction
    lstm_model = get_lstm_model()
    features = prepare_features(product_name, product_info)
    
    prediction, ood_score = lstm_model.predict_with_ood_detection(features)
    
    if ood_score > 0.7:  # High OOD confidence
        # Use fallback
        prediction = statistical_fallback(product_name)
        confidence = 0.5
        status = "OOD_FALLBACK"
    else:
        confidence = 1.0 - ood_score
        status = "ID_CONFIDENT"
    
    return {
        'prediction': prediction,
        'confidence': confidence,
        'ood_score': ood_score,
        'status': status
    }
```

---

## Summary: Recommended Approach

**For your retail import forecasting system**, I recommend:

1. **Immediate** (Low effort): Add MC Dropout uncertainty estimation
2. **Short-term** (Medium effort): Implement ensemble forecasting
3. **Medium-term** (Higher effort): Add open-set LSTM with "unknown product" detection
4. **Long-term** (Optional): Domain adaptation from public time-series data

This balances **detection capability**, **computational cost**, and **implementation complexity**.

---

## References
- **MSP-based**: Hendrycks & Gimpel (2016) - Baseline for Detecting Misclassified and Out-of-Distribution Examples
- **Energy-based**: Liu et al. (2020) - Energy-based Out-of-distribution Detection
- **Mahalanobis**: Lee et al. (2018) - A Simple Unified Framework for Detecting Out-of-Distribution Samples
- **MC Dropout**: Gal & Ghahramani (2016) - Bayesian Deep Learning via Dropout
