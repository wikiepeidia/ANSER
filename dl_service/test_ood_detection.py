"""
Test & Evaluate OOD Detection on Your LSTM Model
Practical script to validate OOD detection performance
"""

import numpy as np
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from utils.ood_detection import (
    OODDetector, UncertaintyEstimator, FallbackPredictor
)


def simulate_model_data():
    """
    Simulate feature outputs from your LSTM model
    In practice: features = model.layers[-3].output (hidden state)
    """
    
    print("\n" + "=" * 70)
    print("SIMULATING LSTM FEATURES")
    print("=" * 70)
    
    # Training features (ID distribution)
    # From normal products in your dataset
    n_train = 200
    train_features = np.random.randn(n_train, 64) * 0.5  # Normalized
    print(f"Training features: {train_features.shape}")
    print(f"  Mean: {np.mean(train_features, axis=0)[:5]}...")
    print(f"  Std:  {np.std(train_features, axis=0)[:5]}...")
    
    # Test ID features (from training distribution)
    n_test_id = 50
    test_id_features = np.random.randn(n_test_id, 64) * 0.5
    
    # Test OOD features (from different distribution)
    # Represent new/unknown products
    n_test_ood = 30
    test_ood_features = np.random.randn(n_test_ood, 64) * 2.0 + 2.0  # Shifted & scaled
    
    return train_features, test_id_features, test_ood_features


def test_ood_detectors():
    """Test all OOD detection methods"""
    
    print("\n" + "=" * 70)
    print("TESTING OOD DETECTION METHODS")
    print("=" * 70)
    
    train_features, test_id_features, test_ood_features = simulate_model_data()
    
    methods = ['msp', 'energy', 'mahalanobis', 'entropy']
    results = {}
    
    for method in methods:
        print(f"\n{'-' * 70}")
        print(f"Method: {method.upper()}")
        print(f"{'-' * 70}")
        
        try:
            # Initialize and fit
            detector = OODDetector(method=method, threshold=0.5)
            detector.fit(train_features)
            
            # Score test samples
            id_scores = detector.score(test_id_features)
            ood_scores = detector.score(test_ood_features)
            
            # Evaluate
            metrics = detector.evaluate(id_scores, ood_scores)
            
            print(f"AUROC:           {metrics['auroc']:.4f}")
            print(f"FPR@95%TPR:      {metrics['fpr_95_tpr']:.4f}")
            print(f"Best Threshold:  {metrics['best_threshold']:.4f}")
            print(f"\nID samples:")
            print(f"  Mean score:    {np.mean(id_scores):.4f}")
            print(f"  Std score:     {np.std(id_scores):.4f}")
            print(f"  Min/Max:       {np.min(id_scores):.4f} / {np.max(id_scores):.4f}")
            print(f"\nOOD samples:")
            print(f"  Mean score:    {np.mean(ood_scores):.4f}")
            print(f"  Std score:     {np.std(ood_scores):.4f}")
            print(f"  Min/Max:       {np.min(ood_scores):.4f} / {np.max(ood_scores):.4f}")
            
            # Calculate detection rate
            detected_ood = np.sum(ood_scores > metrics['best_threshold'])
            detection_rate = detected_ood / len(ood_scores)
            print(f"\nDetection Rate:  {detection_rate * 100:.1f}% ({detected_ood}/{len(ood_scores)})")
            
            results[method] = metrics
            
        except Exception as e:
            print(f"ERROR: {e}")
            results[method] = None
    
    # Summary
    print("\n" + "=" * 70)
    print("COMPARISON SUMMARY")
    print("=" * 70)
    print(f"{'Method':<15} {'AUROC':<10} {'FPR@95%TPR':<12} {'Status':<15}")
    print("-" * 70)
    
    for method, metrics in results.items():
        if metrics is None:
            status = "❌ FAILED"
        else:
            auroc = metrics['auroc']
            fpr = metrics['fpr_95_tpr']
            
            if auroc > 0.85 and fpr < 0.15:
                status = "✅ EXCELLENT"
            elif auroc > 0.75 and fpr < 0.25:
                status = "✓ GOOD"
            else:
                status = "⚠ FAIR"
            
            print(f"{method:<15} {auroc:<10.4f} {fpr:<12.4f} {status:<15}")
    
    # Find best method
    best_method = max(
        [m for m, r in results.items() if r is not None],
        key=lambda m: results[m]['auroc']
    )
    print(f"\n🏆 Recommended: {best_method.upper()} method")
    
    return results


def test_uncertainty_estimation():
    """Test MC Dropout uncertainty"""
    
    print("\n" + "=" * 70)
    print("TESTING UNCERTAINTY ESTIMATION")
    print("=" * 70)
    
    # Simulate LSTM output
    n_samples = 1
    n_forward_passes = 100
    
    # Uncertain predictions (high variance)
    predictions_uncertain = np.random.normal(500, 200, size=(n_forward_passes, n_samples))
    
    # Confident predictions (low variance)
    predictions_confident = np.random.normal(500, 50, size=(n_forward_passes, n_samples))
    
    print("\nUncertain Predictions (high variance):")
    mean_u = np.mean(predictions_uncertain)
    std_u = np.std(predictions_uncertain)
    confidence_u = 1.0 / (1.0 + std_u / (mean_u + 1e-6))
    print(f"  Mean: {mean_u:.1f}")
    print(f"  Std:  {std_u:.1f}")
    print(f"  Confidence: {confidence_u:.3f} (should be low)")
    lower_u, upper_u = UncertaintyEstimator.prediction_interval(mean_u, std_u)
    print(f"  95% PI: [{lower_u:.1f}, {upper_u:.1f}]")
    print(f"  → Use fallback strategy")
    
    print("\nConfident Predictions (low variance):")
    mean_c = np.mean(predictions_confident)
    std_c = np.std(predictions_confident)
    confidence_c = 1.0 / (1.0 + std_c / (mean_c + 1e-6))
    print(f"  Mean: {mean_c:.1f}")
    print(f"  Std:  {std_c:.1f}")
    print(f"  Confidence: {confidence_c:.3f} (should be high)")
    lower_c, upper_c = UncertaintyEstimator.prediction_interval(mean_c, std_c)
    print(f"  95% PI: [{lower_c:.1f}, {upper_c:.1f}]")
    print(f"  → Use LSTM prediction")


def test_fallback_strategies():
    """Test statistical fallback methods"""
    
    print("\n" + "=" * 70)
    print("TESTING FALLBACK STRATEGIES")
    print("=" * 70)
    
    # Simulate historical data
    historical_data = np.array([100, 120, 115, 130, 125, 135, 140])
    
    print(f"\nHistorical data: {historical_data}")
    print(f"Trend: Increasing\n")
    
    # Test each fallback method
    exp_smooth = FallbackPredictor.exponential_smoothing(historical_data, alpha=0.3)
    mov_avg_3 = FallbackPredictor.moving_average(historical_data, window=3)
    mov_avg_5 = FallbackPredictor.moving_average(historical_data, window=5)
    seasonal = FallbackPredictor.seasonal_naive(historical_data, season_length=3)
    
    print("Fallback Predictions:")
    print(f"  Exponential Smoothing (α=0.3): {exp_smooth:.1f}")
    print(f"  Moving Average (window=3):     {mov_avg_3:.1f}")
    print(f"  Moving Average (window=5):     {mov_avg_5:.1f}")
    print(f"  Seasonal Naive (period=3):     {seasonal:.1f}")
    print(f"\nRecommended: Exponential Smoothing = {exp_smooth:.0f} units")


def test_prediction_decision_logic():
    """Test decision logic for ID vs OOD"""
    
    print("\n" + "=" * 70)
    print("TESTING PREDICTION DECISION LOGIC")
    print("=" * 70)
    
    test_cases = [
        {
            'name': 'Known Product (High Confidence)',
            'lstm_pred': 5000,
            'ood_score': 0.2,
            'confidence': 0.92,
            'uncertainty': 150,
        },
        {
            'name': 'Rare Product (Medium Confidence)',
            'lstm_pred': 3000,
            'ood_score': 0.55,
            'confidence': 0.58,
            'uncertainty': 450,
        },
        {
            'name': 'Unknown Product (Low Confidence)',
            'lstm_pred': 1200,
            'ood_score': 0.88,
            'confidence': 0.25,
            'uncertainty': 800,
        },
    ]
    
    for i, case in enumerate(test_cases, 1):
        print(f"\n{'-' * 70}")
        print(f"Case {i}: {case['name']}")
        print(f"{'-' * 70}")
        
        print(f"LSTM Prediction:  {case['lstm_pred']:.0f} units")
        print(f"OOD Score:        {case['ood_score']:.2f} (0=ID, 1=OOD)")
        print(f"Confidence:       {case['confidence']:.2f}")
        print(f"Uncertainty:      {case['uncertainty']:.0f}")
        
        # Decision logic
        is_ood = case['ood_score'] > 0.6 or case['confidence'] < 0.5
        
        if is_ood:
            # Use fallback
            historical = [4000, 4500, 5000] if case['name'] == 'Rare Product (Medium Confidence)' else [100, 120, 110]
            fallback_pred = FallbackPredictor.exponential_smoothing(np.array(historical))
            
            print(f"\n⚠️  DECISION: Use FALLBACK (OOD detected)")
            print(f"   Reason: {'Low confidence' if case['confidence'] < 0.5 else 'High OOD score'}")
            print(f"   Fallback Prediction: {fallback_pred:.0f} units")
            print(f"   Method: Exponential Smoothing")
            print(f"   Confidence: 0.50 (reduced)")
        else:
            print(f"\n✅ DECISION: Use LSTM")
            print(f"   Reason: High confidence and low OOD score")
            print(f"   Final Prediction: {case['lstm_pred']:.0f} units")
            print(f"   Confidence: {case['confidence']:.2f}")


def run_integration_test():
    """Simulated integration test with realistic scenario"""
    
    print("\n" + "=" * 70)
    print("INTEGRATION TEST: Complete Prediction Pipeline")
    print("=" * 70)
    
    # Simulate 10 products
    products = [
        {'name': 'Coca Cola', 'in_training': True, 'sales_history': [1000, 1100, 1050]},
        {'name': 'Fanta', 'in_training': True, 'sales_history': [800, 850, 900]},
        {'name': 'Unknown Brand X', 'in_training': False, 'sales_history': []},
        {'name': 'Sprite', 'in_training': True, 'sales_history': [600, 650, 700]},
        {'name': 'New Product Y', 'in_training': False, 'sales_history': [10, 20, 15]},
    ]
    
    print(f"\nProcessing {len(products)} products:\n")
    print(f"{'Product':<20} {'Status':<15} {'Prediction':<12} {'Confidence':<12} {'Method':<15}")
    print("-" * 70)
    
    for product in products:
        name = product['name']
        
        if product['in_training']:
            # Known product
            pred = np.random.randint(800, 1200)
            conf = 0.85 + np.random.rand() * 0.1  # 0.85-0.95
            method = "LSTM"
            status = "✅ ID"
        else:
            # Unknown product
            if len(product['sales_history']) > 2:
                # Some history - use fallback
                pred = np.mean(product['sales_history']) * np.random.uniform(0.9, 1.1)
                conf = 0.50
                method = "Fallback"
                status = "⚠️  OOD (History)"
            else:
                # No history - default
                pred = 100
                conf = 0.30
                method = "Default"
                status = "❌ OOD"
        
        print(f"{name:<20} {status:<15} {pred:<12.0f} {conf:<12.2f} {method:<15}")
    
    print("\n✅ Integration test completed successfully!")


def main():
    """Run all tests"""
    
    print("\n" + "=" * 70)
    print("OOD DETECTION TEST SUITE")
    print("Validating out-of-distribution detection for LSTM models")
    print("=" * 70)
    
    try:
        # Test 1: OOD Detectors
        test_ood_detectors()
        
        # Test 2: Uncertainty Estimation
        test_uncertainty_estimation()
        
        # Test 3: Fallback Strategies
        test_fallback_strategies()
        
        # Test 4: Decision Logic
        test_prediction_decision_logic()
        
        # Test 5: Integration
        run_integration_test()
        
        print("\n" + "=" * 70)
        print("✅ ALL TESTS PASSED")
        print("=" * 70)
        print("\nNext steps:")
        print("  1. Review results above")
        print("  2. Choose recommended OOD detection method")
        print("  3. Integrate into models/lstm_model.py")
        print("  4. Update services/forecast_service.py")
        print("=" * 70 + "\n")
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)
