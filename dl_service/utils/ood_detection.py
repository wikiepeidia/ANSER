"""
Out-of-Distribution Detection Implementation
Ready-to-use utility functions for OOD detection and handling
"""

import numpy as np
import tensorflow as tf
from tensorflow import keras
from scipy.spatial.distance import mahalanobis
from sklearn.metrics import roc_auc_score, roc_curve
import warnings
warnings.filterwarnings('ignore')


class OODDetector:
    """Unified OOD detection utility"""
    
    def __init__(self, method='energy', threshold=0.5):
        """
        Args:
            method: 'msp', 'energy', 'mahalanobis', 'entropy'
            threshold: Decision boundary for OOD detection
        """
        self.method = method
        self.threshold = threshold
        self.training_stats = None
        
    def fit(self, features):
        """Store statistics from training features"""
        self.training_stats = {
            'mean': np.mean(features, axis=0),
            'cov': np.cov(features.T),
            'cov_inv': np.linalg.inv(np.cov(features.T) + np.eye(features.shape[1]) * 1e-4),
            'min': np.min(features, axis=0),
            'max': np.max(features, axis=0),
        }
        return self
    
    def score(self, logits_or_features):
        """
        Compute OOD score (0=ID, 1=OOD)
        
        Args:
            logits_or_features: Model output or feature vectors
            
        Returns:
            scores: OOD scores [0, 1]
        """
        if self.method == 'msp':
            return self._msp_score(logits_or_features)
        elif self.method == 'energy':
            return self._energy_score(logits_or_features)
        elif self.method == 'mahalanobis':
            return self._mahalanobis_score(logits_or_features)
        elif self.method == 'entropy':
            return self._entropy_score(logits_or_features)
        else:
            raise ValueError(f"Unknown method: {self.method}")
    
    def _msp_score(self, logits):
        """Maximum softmax probability - high for ID, low for OOD"""
        probs = tf.nn.softmax(logits, axis=-1)
        max_prob = np.max(probs, axis=-1)
        # Convert to OOD score: low prob -> high OOD score
        return 1.0 - max_prob
    
    def _energy_score(self, logits):
        """Energy-based score"""
        energy = -np.log(np.sum(np.exp(logits), axis=-1))
        # Normalize to [0, 1]
        energy_min, energy_max = np.min(energy), np.max(energy)
        return (energy - energy_min) / (energy_max - energy_min + 1e-8)
    
    def _mahalanobis_score(self, features):
        """Mahalanobis distance to training distribution"""
        scores = []
        for feat in features:
            try:
                dist = mahalanobis(
                    feat,
                    self.training_stats['mean'],
                    self.training_stats['cov_inv']
                )
                scores.append(dist)
            except:
                scores.append(np.inf)
        
        scores = np.array(scores)
        scores[np.isinf(scores)] = np.max(scores[~np.isinf(scores)])
        
        # Normalize to [0, 1]
        s_min, s_max = np.min(scores), np.max(scores)
        return (scores - s_min) / (s_max - s_min + 1e-8)
    
    def _entropy_score(self, logits):
        """Entropy of softmax distribution"""
        probs = tf.nn.softmax(logits, axis=-1)
        entropy = -np.sum(probs * np.log(probs + 1e-8), axis=-1)
        
        # High entropy -> likely OOD
        max_entropy = np.log(probs.shape[-1])
        return entropy / max_entropy
    
    def predict(self, scores):
        """Binary prediction (0=ID, 1=OOD)"""
        return (scores > self.threshold).astype(int)
    
    def evaluate(self, id_scores, ood_scores):
        """Evaluate OOD detection performance"""
        y_true = np.concatenate([np.ones(len(id_scores)), np.zeros(len(ood_scores))])
        y_scores = np.concatenate([id_scores, ood_scores])
        
        auroc = roc_auc_score(y_true, 1 - y_scores)  # Invert scores for ROC
        fpr, tpr, thresholds = roc_curve(y_true, y_scores)
        
        idx_95_tpr = np.argmin(np.abs(tpr - 0.95))
        fpr_95 = fpr[idx_95_tpr]
        
        return {
            'auroc': auroc,
            'fpr_95_tpr': fpr_95,
            'best_threshold': thresholds[np.argmax(tpr - fpr)]
        }


class UncertaintyEstimator:
    """Estimate prediction uncertainty for LSTM models"""
    
    @staticmethod
    def monte_carlo_dropout(model, X, num_samples=100, dropout_rate=0.5):
        """
        Forward passes with dropout enabled (MC Dropout)
        
        Args:
            model: Keras model with Dropout layers
            X: Input data
            num_samples: Number of stochastic forward passes
            dropout_rate: Dropout rate to use (optional override)
            
        Returns:
            mean: Mean prediction
            std: Standard deviation (uncertainty)
            samples: All samples for inspection
        """
        # Make dropout layers visible during inference
        predictions = []
        for _ in range(num_samples):
            # Use training=True to enable dropout
            pred = model(X, training=True)
            predictions.append(pred.numpy() if hasattr(pred, 'numpy') else pred)
        
        predictions = np.array(predictions)
        mean = np.mean(predictions, axis=0)
        std = np.std(predictions, axis=0)
        
        return mean, std, predictions
    
    @staticmethod
    def ensemble_uncertainty(models, X):
        """
        Ensemble predictions for uncertainty
        
        Args:
            models: List of trained models
            X: Input data
            
        Returns:
            mean: Mean prediction across ensemble
            std: Standard deviation (uncertainty)
        """
        predictions = []
        for model in models:
            pred = model.predict(X, verbose=0)
            predictions.append(pred)
        
        predictions = np.array(predictions).squeeze()
        mean = np.mean(predictions, axis=0)
        std = np.std(predictions, axis=0)
        
        return mean, std
    
    @staticmethod
    def prediction_interval(mean, std, confidence=0.95):
        """
        Compute prediction interval
        
        Args:
            mean: Mean prediction
            std: Standard deviation
            confidence: Confidence level (0.95 = 95%)
            
        Returns:
            (lower, upper): Prediction interval bounds
        """
        z_score = 1.96 if confidence == 0.95 else 2.576  # 99%
        lower = mean - z_score * std
        upper = mean + z_score * std
        return lower, upper


class OpenSetClassifier:
    """Build open-set recognition LSTM for unknown product detection"""
    
    @staticmethod
    def build_open_set_lstm(lookback=30, features=5, num_known_products=100):
        """
        LSTM with auxiliary output for open-set recognition
        
        Args:
            lookback: Sequence length
            features: Number of input features
            num_known_products: Number of known product classes
            
        Returns:
            model: Keras model with two outputs
        """
        inputs = keras.Input(shape=(lookback, features))
        
        # Shared LSTM layers
        x = keras.layers.LSTM(128, return_sequences=True)(inputs)
        x = keras.layers.Dropout(0.3)(x)
        x = keras.layers.LSTM(64, return_sequences=False)(x)
        x = keras.layers.Dropout(0.3)(x)
        
        # Shared dense layer
        shared = keras.layers.Dense(64, activation='relu')(x)
        shared = keras.layers.Dropout(0.2)(shared)
        
        # Head 1: Quantity prediction (regression)
        quantity_head = keras.layers.Dense(32, activation='relu')(shared)
        quantity_out = keras.layers.Dense(1, activation='relu', name='quantity')(quantity_head)
        
        # Head 2: Known vs Unknown classifier (binary classification)
        known_head = keras.layers.Dense(32, activation='relu')(shared)
        known_out = keras.layers.Dense(1, activation='sigmoid', name='is_known')(known_head)
        
        model = keras.Model(inputs=inputs, outputs=[quantity_out, known_out])
        
        model.compile(
            optimizer=keras.optimizers.Adam(learning_rate=0.001),
            loss={
                'quantity': 'mse',
                'is_known': 'binary_crossentropy'
            },
            loss_weights={
                'quantity': 1.0,
                'is_known': 0.5
            },
            metrics={
                'quantity': 'mae',
                'is_known': 'accuracy'
            }
        )
        
        return model
    
    @staticmethod
    def prepare_training_data(X_train, y_train_quantity, product_ids=None):
        """
        Prepare labels for open-set training
        
        Args:
            X_train: Training features
            y_train_quantity: Target quantities
            product_ids: Product identifiers (if None, all treated as known)
            
        Returns:
            X, (y_quantity, y_known): Data for model training
        """
        if product_ids is None:
            y_known = np.ones(len(X_train))  # All known
        else:
            # Assume unknown products have ID >= max(known_ids) + 1000
            y_known = (product_ids < max(product_ids) - 1000).astype(float)
        
        return X_train, (y_train_quantity, y_known)


class FallbackPredictor:
    """Statistical fallback strategies for OOD products"""
    
    @staticmethod
    def exponential_smoothing(data, alpha=0.3):
        """Simple exponential smoothing prediction"""
        if len(data) == 0:
            return 100  # Default
        if len(data) == 1:
            return data[0]
        
        result = [data[0]]
        for i in range(1, len(data)):
            result.append(alpha * data[i] + (1 - alpha) * result[i-1])
        return result[-1]
    
    @staticmethod
    def moving_average(data, window=3):
        """Moving average prediction"""
        if len(data) < window:
            return np.mean(data) if len(data) > 0 else 100
        return np.mean(data[-window:])
    
    @staticmethod
    def seasonal_naive(data, season_length=7):
        """Seasonal naive forecast"""
        if len(data) < season_length:
            return np.mean(data) if len(data) > 0 else 100
        return data[-season_length]
    
    @staticmethod
    def similar_product_average(product_name, known_products_forecast):
        """Predict using similar products"""
        # Find products with similar names
        similar = []
        for prod_name, forecast in known_products_forecast.items():
            if FallbackPredictor._string_similarity(product_name, prod_name) > 0.6:
                similar.append(forecast)
        
        return np.mean(similar) if similar else 100
    
    @staticmethod
    def _string_similarity(s1, s2):
        """Simple string similarity (Jaccard)"""
        from difflib import SequenceMatcher
        return SequenceMatcher(None, s1.lower(), s2.lower()).ratio()


class AugmentationStrategy:
    """Data augmentation for OOD robustness"""
    
    @staticmethod
    def add_synthetic_ood(X, y, contamination_rate=0.1):
        """
        Add synthetic OOD samples to training data
        
        Args:
            X: Training features (n_samples, lookback, features)
            y: Training targets
            contamination_rate: Fraction of synthetic OOD to add
            
        Returns:
            X_aug, y_aug: Augmented data
        """
        n_synthetic = max(1, int(len(X) * contamination_rate))
        indices = np.random.choice(len(X), n_synthetic, replace=False)
        
        X_ood = X[indices].copy()
        y_ood = y[indices].copy()
        
        # Corrupt data to create OOD samples
        noise_level = np.random.uniform(3.0, 10.0)
        X_ood = X_ood * noise_level
        y_ood = y_ood * np.random.uniform(0.1, 20.0)
        
        X_aug = np.vstack([X, X_ood])
        y_aug = np.hstack([y, y_ood])
        
        return X_aug, y_aug
    
    @staticmethod
    def mixup_augmentation(X, y, alpha=0.2):
        """
        Mixup: Create training examples by linear interpolation
        
        Args:
            X: Training features
            y: Training targets
            alpha: Beta distribution parameter
            
        Returns:
            X_mixed, y_mixed: Augmented data
        """
        batch_size = len(X)
        index = np.random.permutation(batch_size)
        
        lam = np.random.beta(alpha, alpha)
        X_mixed = lam * X + (1 - lam) * X[index]
        y_mixed = lam * y + (1 - lam) * y[index]
        
        return X_mixed, y_mixed
    
    @staticmethod
    def gaussian_noise_augmentation(X, y, noise_std=0.1):
        """Add Gaussian noise to features"""
        X_noisy = X + np.random.normal(0, noise_std, X.shape)
        return X_noisy, y


# ============================================
# Integration Example for Your System
# ============================================

def example_usage():
    """
    Example: How to integrate OOD detection into your LSTM forecaster
    """
    
    # 1. Detect OOD using hidden state features
    print("=" * 60)
    print("OOD Detection Example")
    print("=" * 60)
    
    # Sample LSTM outputs (normally from your model)
    hidden_features_id = np.random.randn(100, 64)  # Training data features
    hidden_features_test_id = np.random.randn(20, 64)  # Test ID data
    hidden_features_test_ood = np.random.randn(20, 64) * 5 + 10  # OOD data
    
    # Fit OOD detector on training data
    ood_detector = OODDetector(method='mahalanobis', threshold=0.5)
    ood_detector.fit(hidden_features_id)
    
    # Score test samples
    scores_id = ood_detector.score(hidden_features_test_id)
    scores_ood = ood_detector.score(hidden_features_test_ood)
    
    # Evaluate detection
    metrics = ood_detector.evaluate(scores_id, scores_ood)
    print(f"AUROC: {metrics['auroc']:.3f}")
    print(f"FPR@95%TPR: {metrics['fpr_95_tpr']:.3f}")
    
    # 2. Uncertainty estimation
    print("\n" + "=" * 60)
    print("Uncertainty Estimation Example")
    print("=" * 60)
    
    predictions = np.random.randn(1, 1) * 100 + 500  # Mean ~500
    std_dev = np.abs(np.random.randn(1, 1)) * 50 + 10  # Std ~10-60
    
    lower, upper = UncertaintyEstimator.prediction_interval(predictions, std_dev, confidence=0.95)
    print(f"Prediction: {predictions[0, 0]:.0f}")
    print(f"95% PI: [{lower[0, 0]:.0f}, {upper[0, 0]:.0f}]")
    
    # 3. Fallback strategies
    print("\n" + "=" * 60)
    print("Fallback Prediction Example")
    print("=" * 60)
    
    historical_data = np.array([100, 120, 110, 130, 125, 140, 135])
    
    exp_smooth = FallbackPredictor.exponential_smoothing(historical_data)
    mov_avg = FallbackPredictor.moving_average(historical_data)
    seasonal = FallbackPredictor.seasonal_naive(historical_data)
    
    print(f"Exponential Smoothing: {exp_smooth:.0f}")
    print(f"Moving Average (3): {mov_avg:.0f}")
    print(f"Seasonal Naive: {seasonal:.0f}")


if __name__ == '__main__':
    example_usage()
