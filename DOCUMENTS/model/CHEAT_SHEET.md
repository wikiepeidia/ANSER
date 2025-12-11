# OOD Detection Visual Guide & Cheat Sheet

## 🎯 Decision Tree: When to Use What

```
┌─────────────────────────────────────────────────────────┐
│          Product Recognition Request                     │
└────────────────────┬────────────────────────────────────┘
                     │
                     ↓
        ┌────────────────────────────┐
        │ Has historical data?       │
        └────────┬──────────┬────────┘
                 │          │
            YES  │          │  NO
                 ↓          ↓
        ┌──────────────┐  ┌─────────────────┐
        │ Run LSTM     │  │ Use Default     │
        │ Model        │  │ Fallback (100)  │
        └────┬─────────┘  └────────┬────────┘
             │                     │
             ↓                     ↓
    ┌──────────────────────────────────────┐
    │ Confidence > 0.7 &                   │
    │ OOD Score < 0.6?                     │
    └────────┬────────────────────┬────────┘
             │                    │
          YES│                    │NO
             ↓                    ↓
    ┌──────────────────┐  ┌──────────────────┐
    │ ✅ Use LSTM      │  │ ⚠️  Use Fallback │
    │ Prediction       │  │ Strategy         │
    │ High Confidence  │  │ Medium Conf (0.5)│
    └──────────────────┘  └──────────────────┘
```

---

## 🔍 OOD Detection Methods At a Glance

### 1. MC Dropout (Uncertainty Estimation)
```
Concept: Forward pass with dropout enabled multiple times
Formula: uncertainty = std(predictions across passes)

Code:
    predictions = []
    for _ in range(100):
        pred = model(X, training=True)  # dropout ON
        predictions.append(pred)
    std = np.std(predictions)
    
Result:
    std < 50   → Confident (use LSTM)
    std > 200  → Uncertain (use fallback)
    
Pros: ✅ Simple, built-in to existing model
Cons: ❌ Requires 50+ forward passes
```

### 2. Mahalanobis Distance
```
Concept: Distance from feature to training distribution
Formula: d = √[(x-μ)ᵀ Σ⁻¹(x-μ)]

Code:
    detector = OODDetector(method='mahalanobis')
    detector.fit(training_features)
    distance = detector.score(test_features)
    
Result:
    distance < 2   → ID (known product)
    distance > 5   → OOD (new product)
    
Pros: ✅ Single forward pass, good accuracy
Cons: ❌ Need to fit on training data
```

### 3. Energy-Based
```
Concept: Model as energy function
Formula: E(x) = -log(Σ e^logit_i)

Code:
    energy = -log(exp(logits).sum())
    ood_score = sigmoid(energy)
    
Result:
    energy < -5   → ID
    energy > 0    → OOD
    
Pros: ✅ Fast, uses existing logits
Cons: ❌ Requires discrete outputs
```

### 4. Maximum Softmax Probability (MSP)
```
Concept: Max probability in softmax distribution
Formula: max(softmax(logits))

Code:
    probs = softmax(logits)
    max_prob = max(probs)
    ood_score = 1 - max_prob
    
Result:
    max_prob > 0.8 → ID
    max_prob < 0.5 → OOD
    
Pros: ✅ Simplest, no training needed
Cons: ❌ Low accuracy on hard cases
```

---

## 📊 Comparison Matrix

```
┌──────────────┬──────────┬────────┬──────────┬──────────────┐
│ Method       │ Setup    │ Speed  │ Accuracy │ Recommended  │
├──────────────┼──────────┼────────┼──────────┼──────────────┤
│ MC Dropout   │ Easy (1) │ Slow   │ Very Good│ ✅ START     │
│ Mahalanobis  │ Medium   │ Fast   │ Excellent│ ✅ NEXT      │
│ Energy       │ Easy     │ Fast   │ Good     │ ⭐ Good      │
│ MSP          │ Trivial  │ Instant│ Fair     │ ⭐ Baseline  │
│ Ensemble     │ Hard     │ Slow   │ Best     │ 🚀 Advanced │
└──────────────┴──────────┴────────┴──────────┴──────────────┘
```

---

## 🧠 Understanding Uncertainty

### Low Uncertainty (High Confidence)
```
Predictions: [500, 498, 502, 501, 499]
Mean: 500
Std:  1.4
Confidence: 0.99 ✅

→ Use LSTM prediction
→ Very likely correct
```

### High Uncertainty (Low Confidence)
```
Predictions: [200, 800, 100, 900, 150]
Mean: 430
Std:  350
Confidence: 0.55 ⚠️

→ Use fallback strategy
→ Model not sure
```

### Extreme Uncertainty (Very Low Confidence)
```
Predictions: [10, 2000, 5, 1800, 20]
Mean: 767
Std:  900
Confidence: 0.09 ❌

→ Use default fallback
→ Model completely confused
```

---

## 🔄 Complete Decision Logic

```python
def predict_smart(product_name, lstm_model, ood_detector):
    """Intelligent prediction with OOD handling"""
    
    # 1. Get LSTM prediction
    lstm_pred = lstm_model.predict(X)
    
    # 2. Get uncertainty estimate
    mean, std = estimate_uncertainty(lstm_model, X)
    confidence = 1.0 / (1.0 + std / mean)
    
    # 3. Get OOD detection score
    features = lstm_model.extract_features(X)
    ood_score = ood_detector.score(features)
    
    # 4. Make decision
    if ood_score > 0.6 or confidence < 0.5:
        # OOD or uncertain
        if has_historical_data(product_name):
            pred = fallback_exponential_smoothing(history)
            conf = 0.5
            method = "fallback"
        else:
            pred = default_quantity
            conf = 0.3
            method = "default"
    else:
        # ID and confident
        pred = lstm_pred
        conf = confidence
        method = "lstm"
    
    return {
        'prediction': pred,
        'confidence': conf,
        'ood_score': ood_score,
        'method': method
    }
```

---

## 🎨 Visual: How OOD Detection Works

### Training Data Distribution
```
LSTM Hidden States (64-dimensional space projected to 2D)

        ┌─────────────────────────────┐
        │     Training Data (ID)      │
        │    Coca Cola, Fanta, etc    │
        │                             │
        │        ○ ○  ○  ○            │
        │      ○   ○   ○   ○          │
        │    ○   ●   ○   ●   ○        │  ← Cluster of known products
        │      ○   ○   ○   ○          │
        │        ○  ○   ○             │
        │                             │
        └─────────────────────────────┘
```

### Test Data: Known Product
```
        ┌─────────────────────────────┐
        │     Test Data (ID)          │
        │    New Fanta (similar)      │
        │                             │
        │        ○ ○  ○  ○            │
        │      ○   ○ ▲ ○   ○          │
        │    ○   ●   ○   ●   ○        │  ← Still in cluster
        │      ○   ○   ○   ○          │  ✅ OOD Score: 0.2
        │        ○  ○   ○             │
        │                             │
        └─────────────────────────────┘
```

### Test Data: Unknown Product
```
        ┌─────────────────────────────┐
        │     Test Data (OOD)         │
        │    Totally New Product      │
        │                             │
        │        ○ ○  ○  ○            │
        │      ○   ○   ○   ○   ▲      │
        │    ○   ●   ○   ●   ○        │  ← Far from cluster
        │      ○   ○   ○   ○          │  ❌ OOD Score: 0.9
        │        ○  ○   ○             │
        │                             │
        └─────────────────────────────┘
```

---

## 📈 Performance Benchmarks

### AUROC (Area Under ROC Curve) - Higher is Better
```
Perfect Detection:     AUROC = 1.00 ████████████████████ 100%
Excellent:            AUROC = 0.90 ████████████████░░░░  90%
Good:                 AUROC = 0.80 ████████████░░░░░░░░  80%
Fair:                 AUROC = 0.70 ██████████░░░░░░░░░░  70%
Random:               AUROC = 0.50 ██████░░░░░░░░░░░░░░  50%

Your Target:          AUROC = 0.85 █████████████░░░░░░░  85%
```

### FPR@95%TPR - Lower is Better
```
Perfect:    FPR = 0.0%  No false OOD alarms
Excellent:  FPR < 10%   Mostly correct
Good:       FPR < 20%   Acceptable
Fair:       FPR < 30%   Needs improvement
Random:     FPR = 50%   Useless
```

---

## 🛠️ Implementation Checklist

### Before You Start
- [ ] Read GET_STARTED.md (5 min)
- [ ] Review OOD_README.md (10 min)
- [ ] Look at INTEGRATION_GUIDE.md (5 min)

### Tier 1 Implementation (MC Dropout)
- [ ] Add `predict_with_uncertainty()` to lstm_model.py
- [ ] Import numpy in lstm_model.py
- [ ] Test with sample data
- [ ] Update forecast_service.py to use uncertainty
- [ ] Check that confidence scores make sense

### Tier 2 Implementation (Mahalanobis)
- [ ] Copy utils/ood_detection.py
- [ ] Add feature extraction to lstm_model.py
- [ ] Fit OOD detector during training
- [ ] Add `predict_with_ood_detection()` method
- [ ] Update forecast_service.py to check OOD score
- [ ] Test with known vs unknown products

### Validation
- [ ] Run test_ood_detection.py
- [ ] Check AUROC > 0.85
- [ ] Verify fallback strategies work
- [ ] Test integration with real data
- [ ] Monitor in production for drift

---

## 🎓 Key Equations

### Confidence from Uncertainty
```
confidence = 1 / (1 + std/mean)

Example:
  mean = 500, std = 50
  confidence = 1 / (1 + 50/500) = 1 / 1.1 = 0.91 ✅

  mean = 500, std = 500
  confidence = 1 / (1 + 500/500) = 1 / 2 = 0.50 ⚠️

  mean = 500, std = 2000
  confidence = 1 / (1 + 2000/500) = 1 / 5 = 0.20 ❌
```

### Mahalanobis Distance
```
d = √[(x - μ)ᵀ Σ⁻¹(x - μ)]

Where:
  x = test sample feature vector
  μ = mean of training features
  Σ⁻¹ = inverse covariance matrix

Interpretation:
  d < 2   → Standard deviation away (ID)
  d > 5   → Far from distribution (OOD)
```

### AUROC Formula
```
AUROC = P(score_ood > score_id)

Means:
  - Probability that OOD sample scored higher than ID sample
  - Range: [0, 1]
  - 0.5 = random, 1.0 = perfect
```

---

## 💾 Code Templates

### Template 1: Add MC Dropout
```python
# Add to models/lstm_model.py

def predict_with_uncertainty(self, X, num_samples=50):
    predictions = []
    for _ in range(num_samples):
        pred = self.model(X, training=True)
        predictions.append(pred.numpy())
    
    predictions = np.array(predictions).squeeze()
    mean = np.mean(predictions)
    std = np.std(predictions)
    confidence = 1.0 / (1.0 + std / (mean + 1e-6))
    
    return mean, std, confidence
```

### Template 2: Add OOD Detection
```python
# Add to models/lstm_model.py

def predict_with_ood_detection(self, X):
    from utils.ood_detection import OODDetector
    
    prediction = self.model.predict(X)[0, 0]
    
    if self.ood_detector is None:
        return prediction, 0.0, False
    
    features = self.feature_extractor.predict(X)
    ood_scores = self.ood_detector.score(features)
    is_ood = ood_scores[0] > self.ood_detector.threshold
    
    return prediction, ood_scores[0], is_ood
```

### Template 3: Integrate in Forecast Service
```python
# Update services/forecast_service.py

def predict_import_quantity_smart(product_name, product_info):
    lstm_model = get_lstm_model()
    
    # Prepare input
    X = prepare_features(product_name, product_info)
    X = np.array(X).reshape(1, -1)
    
    # Get predictions
    mean_pred, std_pred, conf = lstm_model.predict_with_uncertainty(X)
    pred_lstm, ood_score, is_ood = lstm_model.predict_with_ood_detection(X)
    
    # Decide
    if is_ood or conf < 0.5:
        from utils.ood_detection import FallbackPredictor
        pred = FallbackPredictor.exponential_smoothing(
            get_historical_imports(product_name)
        )
        method = "fallback"
        confidence = 0.5
    else:
        pred = mean_pred
        method = "lstm"
        confidence = conf
    
    return {
        'quantity': int(pred),
        'confidence': confidence,
        'ood_score': ood_score,
        'method': method
    }
```

---

## 🚨 Troubleshooting

### Problem: All predictions have low confidence
```
Symptom: confidence always < 0.3
Cause: Too much dropout or high variance in LSTM
Solution: Reduce dropout from 0.3 to 0.2
```

### Problem: OOD detection doesn't discriminate
```
Symptom: OOD score = 0.5 for both ID and OOD
Cause: Features too similar or detector not fitted
Solution: Check training_stats is not None, use Mahalanobis
```

### Problem: Fallback predictions too high/low
```
Symptom: Fallback always predicts 1000
Cause: Historical data not loaded correctly
Solution: Print history before fallback call
```

### Problem: Predictions inconsistent
```
Symptom: Same product gets different predictions
Cause: Model not seeded or dropout too high
Solution: Set np.random.seed(42) before inference
```

---

## 📚 File Structure Reference

```
YOUR_PROJECT/
│
├─ GET_STARTED.md              ← You are here
├─ OOD_README.md               ← Overview & quick ref
├─ OOD_STRATEGIES.md           ← All theory & methods
├─ INTEGRATION_GUIDE.md        ← Implementation steps
│
├─ utils/
│  └─ ood_detection.py         ← Production code
│
├─ models/
│  └─ lstm_model.py            ← Modify this
│
├─ services/
│  └─ forecast_service.py      ← Modify this
│
└─ test_ood_detection.py       ← Run this to test
```

---

## ✅ Success Criteria

After implementation, you should see:

```
✅ Confidence scores between 0 and 1
✅ Known products: confidence > 0.8
✅ Unknown products: confidence < 0.6
✅ AUROC > 0.85 on test set
✅ Fallback strategies return reasonable values
✅ Integration tests pass
✅ No errors in forecast service
✅ API returns confidence field
✅ Unknown products don't crash system
✅ Predictions improve for new products
```

---

## 🎯 Next Step

**👉 Start with INTEGRATION_GUIDE.md - Quick Start (30 min)**

You're ready to build! 🚀
