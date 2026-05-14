"""
Train LSTM model for time-series import forecasting.
Uses daily sales/import patterns to predict future import needs.
"""

import os
import sys
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import MinMaxScaler
import pickle

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import LSTM_MODEL_PATH, LSTM_SCALER_PATH
from models.lstm_model import ImportForecastLSTM

# Constants
SEQUENCE_LENGTH = 7  # Use 7 days of history to predict next import
# Resolve data paths relative to the project root (parent of this file)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Prefer top-level `data/` but fall back to `dl_service/data/` if present
CANDIDATE_DATA_DIRS = [
    os.path.join(PROJECT_ROOT, 'data'),
    os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
]
DATA_DIR = next((p for p in CANDIDATE_DATA_DIRS if os.path.exists(p)), CANDIDATE_DATA_DIRS[0])
if not os.path.exists(DATA_DIR):
    # This should rarely happen and will be caught later, but log for clarity
    print(f"[WARN] No data directory found among candidates: {CANDIDATE_DATA_DIRS}")
else:
    print(f"[INFO] Using data directory: {DATA_DIR}")
IMPORT_CSV_PATH = os.path.join(DATA_DIR, 'import_in_a_timescale.csv')
SALE_CSV_PATH = os.path.join(DATA_DIR, 'sale_in_a_timescale.csv')
PRODUCT_CSV_PATH = os.path.join(DATA_DIR, 'dataset_product.csv')

def load_timeseries_data():
    
    print("[INFO] Loading time-series data...")
    print(f"[INFO] Looking for data files in: {os.path.abspath(DATA_DIR)}")

    # Ensure data files exist
    for path in [IMPORT_CSV_PATH, SALE_CSV_PATH, PRODUCT_CSV_PATH]:
        if not os.path.exists(path):
            raise FileNotFoundError(f"Required data file not found: {os.path.abspath(path)}")
    
    # Load imports with dates
    df_imports = pd.read_csv(IMPORT_CSV_PATH, sep=';', encoding='utf-8')
    df_imports.columns = ['date', 'product', 'import_qty', 'unit_price']
    df_imports['date'] = pd.to_datetime(df_imports['date'], format='%d/%m/%Y')
    df_imports['product'] = df_imports['product'].str.strip()
    
    # Load sales with dates
    df_sales = pd.read_csv(SALE_CSV_PATH, sep=';', encoding='utf-8')
    df_sales.columns = ['date', 'product', 'sale_qty']
    df_sales['date'] = pd.to_datetime(df_sales['date'], format='%d/%m/%Y')
    df_sales['product'] = df_sales['product'].str.strip()
    
    # Load static product info (initial stock, prices)
    df_products = pd.read_csv(PRODUCT_CSV_PATH, sep=';', encoding='utf-8')
    df_products.columns = ['product', 'initial_stock', 'cost_price', 'retail_price', 'import_price']
    df_products['product'] = df_products['product'].str.strip()
    
    # Parse prices (remove thousand separators)
    for col in ['initial_stock', 'import_price', 'retail_price']:
        df_products[col] = df_products[col].astype(str).str.replace('.', '').str.replace(',', '.').astype(float)
    
    # Get date range
    min_date = min(df_imports['date'].min(), df_sales['date'].min())
    max_date = max(df_imports['date'].max(), df_sales['date'].max())
    
    print(f"[INFO] Date range: {min_date.date()} to {max_date.date()}")
    
    # VECTORIZED: Aggregate imports by product and date
    df_imports_agg = df_imports.groupby(['product', 'date'])['import_qty'].sum().reset_index()
    
    # VECTORIZED: Aggregate sales by product and date
    df_sales_agg = df_sales.groupby(['product', 'date'])['sale_qty'].sum().reset_index()
    
    # VECTORIZED: Merge imports and sales on product+date (outer join to keep all dates)
    df_merged = pd.merge(df_imports_agg, df_sales_agg, on=['product', 'date'], how='outer')
    df_merged['import_qty'] = df_merged['import_qty'].fillna(0)
    df_merged['sale_qty'] = df_merged['sale_qty'].fillna(0)
    
    # CRITICAL: Create complete date range for EACH product (fill missing days with zeros)
    print("[INFO] Creating complete date range for all products...")
    all_dates = pd.date_range(start=min_date, end=max_date, freq='D')
    all_products = df_merged['product'].unique()
    
    # Create cartesian product: all products × all dates
    complete_index = pd.MultiIndex.from_product([all_products, all_dates], names=['product', 'date'])
    df_complete = pd.DataFrame(index=complete_index).reset_index()
    
    # Merge with actual data
    df_merged = pd.merge(df_complete, df_merged, on=['product', 'date'], how='left')
    df_merged['import_qty'] = df_merged['import_qty'].fillna(0)
    df_merged['sale_qty'] = df_merged['sale_qty'].fillna(0)
    
    # Add temporal features (VECTORIZED!)
    df_merged['day_of_week'] = df_merged['date'].dt.dayofweek
    df_merged['day_of_month'] = df_merged['date'].dt.day
    df_merged['is_weekend'] = (df_merged['day_of_week'] >= 5).astype(int)
    
    # Merge with product info
    df_merged = pd.merge(df_merged, df_products[['product', 'initial_stock', 'import_price', 'retail_price']], 
                         on='product', how='left')
    df_merged[['initial_stock', 'import_price', 'retail_price']] = df_merged[['initial_stock', 'import_price', 'retail_price']].fillna(0)
    
    # Sort by product and date
    df_merged = df_merged.sort_values(['product', 'date']).reset_index(drop=True)
    
    print(f"[INFO] Built time-series for {df_merged['product'].nunique()} products")
    print(f"[INFO] Total data points: {len(df_merged)}")
    
    # Convert to dictionary format (still needed for sequence creation)
    product_dict = {}
    for product in df_merged['product'].unique():
        product_data = df_merged[df_merged['product'] == product]
        
        daily_data = product_data[['date', 'import_qty', 'sale_qty', 'day_of_week', 'day_of_month', 'is_weekend']].to_dict('records')
        
        product_dict[product] = {
            'daily_data': daily_data,
            'initial_stock': product_data['initial_stock'].iloc[0],
            'import_price': product_data['import_price'].iloc[0],
            'retail_price': product_data['retail_price'].iloc[0]
        }
    
    return product_dict

def create_sequences(product_dict, sequence_length=7):
    """
    Create training sequences using sliding window.
    

    """
    print(f"[INFO] Creating sequences with {sequence_length}-day history...")
    
    X_list = []
    y_list = []
    
    for product_name, data in product_dict.items():
        daily_data = data['daily_data']
        
        # Need at least sequence_length + 1 days to create a sequence
        if len(daily_data) < sequence_length + 1:
            continue
        
        # Sliding window: use days [0:7] to predict day 7 import,
        #                 then [1:8] to predict day 8 import, etc.
        for i in range(len(daily_data) - sequence_length):
            # Get sequence of past days
            sequence = daily_data[i:i + sequence_length]
            
            # Get target (import on the LAST day of sequence)
            target_day = daily_data[i + sequence_length]
            target_import = target_day['import_qty']
            
            # Features for each day in sequence:
            # [sale_qty, day_of_week, is_weekend, cumulative_sales, days_since_last_import]
            sequence_features = []
            cumulative_sales = 0
            last_import_day = -999  # Days since last import
            
            for day_idx, day in enumerate(sequence):
                cumulative_sales += day['sale_qty']
                
                # Update last import day
                if day['import_qty'] > 0:
                    last_import_day = day_idx
                
                days_since_import = day_idx - last_import_day if last_import_day >= 0 else 999
                
                day_features = [
                    day['sale_qty'],
                    day['day_of_week'] / 6.0,  # Normalize to [0, 1]
                    day['is_weekend'],
                    cumulative_sales,
                    min(days_since_import, 30) / 30.0  # Normalize, cap at 30 days
                ]
                sequence_features.append(day_features)
            
            # Add static features (same for all days in sequence)
            # We'll append these to each time step
            static_features = [
                data['initial_stock'],
                data['retail_price']
            ]
            
            # Append static features to each day
            for day_features in sequence_features:
                day_features.extend(static_features)
            
            X_list.append(sequence_features)
            y_list.append(target_import)
    
    X = np.array(X_list)
    y = np.array(y_list)
    
    print(f"[INFO] Created {len(X)} sequences")
    print(f"[INFO] Input shape: {X.shape} (samples, time_steps, features)")
    print(f"[INFO] Output shape: {y.shape}")
    
    # Print statistics
    print(f"\n[STATS] Target distribution:")
    print(f"  - Zero imports: {(y == 0).sum()} ({(y == 0).sum() / len(y) * 100:.1f}%)")
    print(f"  - Non-zero imports: {(y > 0).sum()} ({(y > 0).sum() / len(y) * 100:.1f}%)")
    print(f"  - Mean: {y.mean():.2f}, Median: {np.median(y):.2f}, Max: {y.max():.0f}")
    
    return X, y

def normalize_features(X_train, X_val, X_test, y_train, y_val, y_test):
    """
    Normalize features using MinMaxScaler.
    
    Args:
        X_train, X_val, X_test: Input sequences
        y_train, y_val, y_test: Target values
    
    Returns:
        Normalized X and y, plus fitted scalers
    """
    print("[INFO] Normalizing features...")
    
    # Flatten sequences to fit scaler
    n_samples_train, n_timesteps, n_features = X_train.shape
    X_train_flat = X_train.reshape(-1, n_features)
    X_val_flat = X_val.reshape(-1, n_features)
    X_test_flat = X_test.reshape(-1, n_features)
    
    # Fit scaler on training data
    feature_scaler = MinMaxScaler()
    feature_scaler.fit(X_train_flat)
    
    # Transform all sets
    X_train_norm = feature_scaler.transform(X_train_flat).reshape(X_train.shape)
    X_val_norm = feature_scaler.transform(X_val_flat).reshape(X_val.shape)
    X_test_norm = feature_scaler.transform(X_test_flat).reshape(X_test.shape)
    
    # Scale targets
    target_scaler = MinMaxScaler()
    y_train_norm = target_scaler.fit_transform(y_train.reshape(-1, 1)).flatten()
    y_val_norm = target_scaler.transform(y_val.reshape(-1, 1)).flatten()
    y_test_norm = target_scaler.transform(y_test.reshape(-1, 1)).flatten()
    
    print(f"[INFO] Feature scaler range: [{feature_scaler.data_min_[:3]}...] to [{feature_scaler.data_max_[:3]}...]")
    print(f"[INFO] Target scaler range: {target_scaler.data_min_[0]:.2f} to {target_scaler.data_max_[0]:.2f}")
    
    return X_train_norm, X_val_norm, X_test_norm, y_train_norm, y_val_norm, y_test_norm, feature_scaler, target_scaler

def main():
    """Main training pipeline."""
    print("=" * 60)
    print("LSTM TIME-SERIES TRAINING")
    print("=" * 60)
    
    # 1. Load time-series data
    product_dict = load_timeseries_data()
    
    # 2. Create sequences
    X, y = create_sequences(product_dict, sequence_length=SEQUENCE_LENGTH)
    
    # 3. Split data (70% train, 10% val, 20% test)
    X_temp, X_test, y_temp, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    X_train, X_val, y_train, y_val = train_test_split(X_temp, y_temp, test_size=0.125, random_state=42)  # 0.125 * 0.8 = 0.1
    
    print(f"\n[SPLIT] Train: {len(X_train)}, Val: {len(X_val)}, Test: {len(X_test)}")
    
    # 4. Normalize
    X_train, X_val, X_test, y_train, y_val, y_test, feature_scaler, target_scaler = \
        normalize_features(X_train, X_val, X_test, y_train, y_val, y_test)
    
    # 5. Build and train model
    print("\n[INFO] Building LSTM model...")
    n_features = X_train.shape[2]
    
    model = ImportForecastLSTM(
        lookback=SEQUENCE_LENGTH,
        features=n_features
    )
    
    print("\n[INFO] Training model with extended epochs for better convergence...")
    history = model.train(
        train_data=(X_train, y_train),
        val_data=(X_val, y_val),
        epochs=100,  # Increased from 50 to 100 for better training
        batch_size=32
    )
    
    # 6. Evaluate
    print("\n[INFO] Evaluating on test set...")
    test_loss, test_mae = model.model.evaluate(X_test, y_test, verbose=0)
    print(f"[RESULT] Test loss: {test_loss:.4f}, MAE: {test_mae:.4f}")
    
    # 7. Save model and scalers
    print("\n[INFO] Saving model and scalers...")
    model.save_model(str(LSTM_MODEL_PATH))
    
    with open(LSTM_SCALER_PATH, 'wb') as f:
        pickle.dump({
            'feature_scaler': feature_scaler,
            'target_scaler': target_scaler,
            'sequence_length': SEQUENCE_LENGTH
        }, f)
    
    print(f"[SAVED] Model: {LSTM_MODEL_PATH}")
    print(f"[SAVED] Scaler: {LSTM_SCALER_PATH}")
    
    print("\n" + "=" * 60)
    print("TRAINING COMPLETE")
    print("=" * 60)

if __name__ == '__main__':
    main()
