# Out-of-Distribution (OOD) Product Recognition - Summary

## Problem Statement
Your retail import forecasting system is trained on a fixed dataset of ~14,367 products. When new products appear (not in training data), the model may produce inaccurate predictions or fail to recognize them as unknown.

## Solution Overview

I've provided **three levels of solutions**, from simple to advanced:

---

## 📋 Documents Created

### 1. **OOD_STRATEGIES.md** - Comprehensive Theory & Methods
   - 8 major detection techniques with code examples
   - Architecture modifications (open-set, MoE, residual networks)
   - Ensemble and training strategies
   - Evaluation metrics
   - **Best for**: Understanding all options, choosing best approach

### 2. **INTEGRATION_GUIDE.md** - Step-by-Step Implementation
   - 🚀 Quick Start (30 min): Enable MC Dropout
   - 🔧 Step 2 (60 min): Add Mahalanobis OOD detection
   - 📊 Step 3 (30 min): Evaluation script
   - Implementation order and dependencies
   - Debugging tips
   - **Best for**: Getting it working in your system

### 3. **utils/ood_detection.py** - Ready-to-Use Code
   - `OODDetector`: 4 methods (MSP, Energy, Mahalanobis, Entropy)
   - `UncertaintyEstimator`: MC Dropout + Ensemble
   - `OpenSetClassifier`: Build open-set LSTM
   - `FallbackPredictor`: Statistical backups
   - `AugmentationStrategy`: Robustness training
   - **Best for**: Copy-paste into your codebase

---

## 🎯 Recommended Approach for Your System

### Tier 1: Uncertainty Estimation (Week 1)
**Effort**: Low | **Time**: 30 min | **Impact**: High

Enable Monte Carlo Dropout to get uncertainty estimates:
```python
mean, std, confidence = lstm_model.predict_with_uncertainty(X)

# Use fallback if confidence < 0.6
if confidence < 0.6:
    prediction = fallback_exponential_smoothing(...)
```

**File changes**: `models/lstm_model.py` only

---

### Tier 2: OOD Detection (Week 2)
**Effort**: Medium | **Time**: 60 min | **Impact**: High

Detect products outside training distribution:
```python
prediction, ood_score, is_ood = lstm_model.predict_with_ood_detection(X)

# Use fallback if OOD
if is_ood:
    prediction = fallback_strategy(...)
```

**Files changed**: `models/lstm_model.py`, `services/forecast_service.py`

---

### Tier 3: Advanced Methods (Week 3+)
**Effort**: High | **Time**: Days | **Impact**: Highest

- Ensemble forecasters (multiple LSTM models)
- Open-set LSTM with "unknown product" class
- Data augmentation with synthetic OOD

**Files changed**: Multiple, larger refactoring

---

## 🚀 Quick Start (Copy-Paste)

### 1. Add to `models/lstm_model.py`

```python
def predict_with_uncertainty(self, X, num_samples=50):
    """Return (mean, std, confidence)"""
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

### 2. Use in `services/forecast_service.py`

```python
mean_pred, std_pred, confidence = lstm_model.predict_with_uncertainty(X)

if confidence < 0.6:
    # OOD - use fallback
    from utils.ood_detection import FallbackPredictor
    prediction = FallbackPredictor.exponential_smoothing(historical_data)
    method = "fallback"
else:
    prediction = mean_pred
    method = "lstm"

return {
    'quantity': prediction,
    'confidence': confidence,
    'uncertainty': std_pred,
    'method': method
}
```

---

## 🧠 Key Concepts Explained

### OOD Detection Methods (in order of simplicity)

| Method | Complexity | Speed | Accuracy | Code |
|--------|-----------|-------|----------|------|
| **MSP** | ⭐ | ⚡⚡⚡ | ⭐⭐ | 5 lines |
| **MC Dropout** | ⭐⭐ | ⚡⚡ | ⭐⭐⭐ | 10 lines |
| **Energy** | ⭐⭐ | ⚡⚡ | ⭐⭐⭐ | 8 lines |
| **Mahalanobis** | ⭐⭐⭐ | ⚡ | ⭐⭐⭐⭐ | 15 lines |
| **Ensemble** | ⭐⭐⭐ | ⚡ | ⭐⭐⭐⭐⭐ | 20 lines |

**Recommended**: Start with **MC Dropout** (best balance)

---

## 📊 Expected Performance

### With Tier 1 (Uncertainty)
- Detection capability: 65-75% AUROC
- Computational overhead: ~5-10x (50 forward passes)
- Code complexity: Low
- Time to implement: 30 min

### With Tier 2 (OOD Detection)
- Detection capability: 75-85% AUROC
- Computational overhead: ~2x (feature extraction)
- Code complexity: Medium
- Time to implement: 60 min

### With Tier 3 (Advanced)
- Detection capability: 85-95% AUROC
- Computational overhead: 3-5x (ensemble)
- Code complexity: High
- Time to implement: Days

---

## 💡 Practical Examples

### Example 1: Known Product (Coca Cola)
```
Input: Coca Cola, Oct-Nov sales history available
OOD Score: 0.2 (likely ID)
Confidence: 0.85
→ Use LSTM prediction: 5000 units
```

### Example 2: Rare Product (Limited history)
```
Input: Brand X Soda, only 2 sales records
OOD Score: 0.6 (uncertain)
Confidence: 0.55
→ Use fallback: exponential smoothing = 3000 units
```

### Example 3: Completely New Product
```
Input: New Product Y, zero history
OOD Score: 0.95 (likely OOD)
Confidence: 0.2
→ Use fallback: moving average = 100 units (default)
```

---

## 🔄 Fallback Strategies (when OOD detected)

Your system can use multiple fallback strategies:

1. **Exponential Smoothing** - Best for trending data
2. **Moving Average** - Simple and robust
3. **Seasonal Naive** - For products with patterns
4. **Similar Product Average** - Find similar products, use their forecast
5. **Statistical Median** - Last resort: use median of historical imports

---

## 📈 Monitoring & Metrics

Track these to see if OOD handling is working:

```python
metrics = {
    # OOD Detection Quality
    'ood_auroc': 0.85,  # Target: > 0.80
    'fpr_at_95_tpr': 0.15,  # Target: < 0.20
    
    # Forecast Accuracy
    'mae_with_ood': 1200,  # Mean absolute error
    'mae_without_ood': 1500,  # Improvement: 20%
    
    # System Health
    'pct_products_ood': 0.15,  # % flagged as OOD
    'avg_confidence': 0.72,  # Average confidence score
    'avg_uncertainty': 450,  # Average std deviation
}
```

---

## ✅ Validation Checklist

Before deploying:

- [ ] MC Dropout predictions have reasonable confidence scores
- [ ] OOD detector initialized with training data statistics
- [ ] Fallback strategies return sensible values
- [ ] API returns `confidence` and `method` fields
- [ ] Unknown products don't crash (graceful degradation)
- [ ] Evaluation shows improvement over baseline
- [ ] Performance acceptable (< 100ms per prediction)

---

## 🚨 Common Issues & Solutions

| Issue | Cause | Solution |
|-------|-------|----------|
| All predictions have low confidence | Too much dropout | Reduce dropout rate to 0.2 |
| OOD detector not discriminating | Features too similar | Use Mahalanobis distance |
| Slow predictions | MC Dropout too many samples | Reduce to 30-50 samples |
| Fallback always triggered | Threshold too high | Lower OOD threshold to 0.5 |
| Inconsistent predictions | No seeding | Set `np.random.seed(42)` |

---

## 📚 File Organization

```
Your Project/
├── OOD_STRATEGIES.md          ← Read for theory
├── INTEGRATION_GUIDE.md       ← Follow step-by-step
├── utils/
│   └── ood_detection.py       ← Copy classes into your code
├── models/
│   └── lstm_model.py          ← Add uncertainty methods
├── services/
│   └── forecast_service.py    ← Integrate OOD handling
└── evaluate_ood.py            ← Test & validate
```

---

## 🎓 Learning Resources

**Provided in this package:**
- 3 complete markdown guides
- 1 production-ready Python module
- Multiple code examples
- Integration patterns for your existing code

**External references** (see OOD_STRATEGIES.md):
- Hendrycks & Gimpel (2016) - Baseline MSP
- Liu et al. (2020) - Energy-based OOD
- Lee et al. (2018) - Mahalanobis distance
- Gal & Ghahramani (2016) - MC Dropout for uncertainty

---

## 🎯 Next Steps

1. **Today**: Read `INTEGRATION_GUIDE.md` - Quick Start section (15 min)
2. **Tomorrow**: Implement Tier 1 - MC Dropout (30 min)
3. **This week**: Implement Tier 2 - OOD Detection (60 min)
4. **Optional**: Tier 3 - Advanced methods (as needed)

---

## 📞 Quick Reference: When to Use What

### Scenario 1: Product with incomplete history
```python
confidence = 0.55  # Medium
→ Use fallback with reduced weight, LSTM with reduced weight
```

### Scenario 2: Product completely new
```python
ood_score = 0.9  # High OOD
→ Use statistical fallback (exponential smoothing, moving average)
```

### Scenario 3: Rare edge case
```python
confidence = 0.1  # Very low
→ Flag for manual review, return default prediction
```

### Scenario 4: Product well-represented in training
```python
ood_score = 0.1, confidence = 0.95  # Clear ID
→ Use LSTM prediction with full confidence
```

---

## 💬 Summary

You now have **three complete solutions** to detect and handle out-of-distribution products:

1. **Theory**: Understand all approaches (OOD_STRATEGIES.md)
2. **Implementation**: Step-by-step integration (INTEGRATION_GUIDE.md)  
3. **Code**: Production-ready utilities (ood_detection.py)

Start with **Tier 1 (MC Dropout)** this week, then progress to Tier 2 & 3 as needed.

**Good luck with your retail forecasting system!** 🚀
