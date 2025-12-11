from datetime import datetime
import pandas as pd
import os
from utils.logger import get_logger

logger = get_logger(__name__)


def load_timescale_data():
    """
    Load timescale data from CSV files
    Returns: (product_info_dict, imports_dict, sales_dict)
    """
    try:
        # Define helper function
        def clean_price(price_str):
            if pd.isna(price_str):
                return 0
            price_clean = str(price_str).replace('.', '').replace(',', '').strip()
            try:
                return float(price_clean)
            except ValueError:
                return 0

        # Load dataset_product.csv
        df_products = pd.read_csv('data/dataset_product.csv', sep=';', encoding='utf-8')
        logger.info(f"[DATA] Loaded dataset_product.csv: {len(df_products)} products from REAL CSV file")

        product_info = {}
        for _, row in df_products.iterrows():
            product_name = str(row.iloc[0]).strip()
            product_info[product_name] = {
                'initial_stock': int(row.iloc[1]) if pd.notna(row.iloc[1]) else 0,
                'import_price': clean_price(row.iloc[2]) if len(row) > 2 else 0,
                'retail_price': clean_price(row.iloc[3]) if len(row) > 3 else 0,
            }

        # Load import_in_a_timescale.csv
        df_imports = pd.read_csv('data/import_in_a_timescale.csv', sep=';', encoding='utf-8')
        logger.info(f"[DATA] Loaded import_in_a_timescale.csv: {len(df_imports)} import records from October 2025")

        imports_dict = {}
        for _, row in df_imports.iterrows():
            try:
                product_name = str(row.iloc[0]).strip()
                quantity = int(row.iloc[1]) if pd.notna(row.iloc[1]) else 0
                imports_dict[product_name] = imports_dict.get(product_name, 0) + quantity
            except (ValueError, IndexError):
                continue

        # Load sale_in_a_timescale.csv
        df_sales = pd.read_csv('data/sale_in_a_timescale.csv', sep=';', encoding='utf-8')
        logger.info(f"[DATA] Loaded sale_in_a_timescale.csv: {len(df_sales)} sales records from October 2025")

        sales_dict = {}
        for _, row in df_sales.iterrows():
            try:
                product_name = str(row.iloc[1]).strip()
                quantity = int(row.iloc[2]) if pd.notna(row.iloc[2]) else 0
                sales_dict[product_name] = sales_dict.get(product_name, 0) + quantity
            except (ValueError, IndexError):
                continue

        logger.info(f"Loaded timescale data: {len(product_info)} products, {len(imports_dict)} imports, {len(sales_dict)} sales")
        return product_info, imports_dict, sales_dict

    except Exception as e:
        logger.error(f"Error loading timescale data: {e}")
        return {}, {}, {}


def parse_manual_invoice_data(manual_invoice_data):
    
    if not manual_invoice_data or not manual_invoice_data.strip():
        return None

    logger.info("[INPUT] Parsing manual invoice data (x2, x3)")

    lines = manual_invoice_data.split('\n')
    parsed_products = []

    for line in lines:
        line = line.strip()
        if line and ('-' in line or ':' in line):
            # Split by - hoặc : và extract product và quantity
            parts = line.replace(':', '-').split('-', 1)
            if len(parts) == 2:
                product = parts[0].strip()
                try:
                    quantity = int(parts[1].strip())
                    parsed_products.append({
                        'product_id': None,
                        'product_name': product,
                        'quantity': quantity,
                        'unit_price': 10000,
                        'line_total': quantity * 10000
                    })
                    logger.debug(f" Parsed: {product} - {quantity}")
                except ValueError:
                    logger.warning(f" Skipped invalid line: {line}")
                    continue

    if not parsed_products:
        logger.warning("[INPUT] No valid products parsed")
        return None

    logger.info(f"[INPUT] Successfully parsed {len(parsed_products)} products")
    return parsed_products


def forecast_quantity(lstm_model, invoice_data_list):
    
    logger.info(f"[MODEL 2] Starting forecast for {len(invoice_data_list)} products")

    

    product_info, imports_dict, sales_dict = load_timescale_data()

    logger.info(f"[MODEL 2] Loaded REAL historical data:")
    logger.info(f"[MODEL 2] - {len(product_info)} products with info")
    logger.info(f"[MODEL 2] - {len(imports_dict)} products with import history")
    logger.info(f"[MODEL 2] - {len(sales_dict)} products with sales history")

    predicted_products = []
    total_predicted = 0

    for invoice_item in invoice_data_list:
        product_name = invoice_item.get('product_name', '')
        current_qty = invoice_item.get('quantity', 0)

        # Get historical data
        historical_import = imports_dict.get(product_name, 0)
        historical_sales = sales_dict.get(product_name, 0)
        initial_stock = product_info.get(product_name, {}).get('initial_stock', 0)

        logger.info(f"[MODEL 2] - Processing: {product_name}")
        logger.info(f"[MODEL 2] - Current qty in invoice: {current_qty}")
        logger.info(f"[MODEL 2] - Historical SALES (Oct 2025): {historical_sales} units")
        logger.info(f"[MODEL 2] - Historical IMPORT (Oct 2025): {historical_import} units")
        logger.info(f"[MODEL 2] - Initial stock from dataset: {initial_stock} units")

        # Predict based on sales velocity
        # If product has high sales, predict higher import
        if historical_sales > 0:
            # Sales velocity = sales / 30 days (October data)
            daily_sales = historical_sales / 30.0
            # Predict import = 2 weeks of sales (safety stock)
            predicted_import = int(daily_sales * 14)
            # Add some buffer based on current quantity
            predicted_import = max(predicted_import, current_qty)
            confidence = 0.75 + (min(historical_sales, 100) / 400.0)  # 0.75-1.0
            logger.info(f"[MODEL 2] - Using REAL sales data: {historical_sales} → daily_sales={daily_sales:.2f}")
            logger.info(f"[MODEL 2] - Formula: daily_sales * 14 days = {predicted_import} units")
        else:
            # No historical sales - use current quantity as baseline
            predicted_import = max(int(current_qty * 1.5), 5)  # At least 5 units
            confidence = 0.60
            logger.info(f"[MODEL 2] - No historical sales found, using fallback: current_qty * 1.5 = {predicted_import}")

        # Clamp predictions to reasonable range
        predicted_import = max(5, min(predicted_import, 500))

        predicted_products.append({
            'product_name': product_name,
            'current_quantity': current_qty,
            'predicted_quantity': predicted_import, 
            'confidence': round(confidence, 3),
            'historical_sales': historical_sales,
            'trend': 'increasing' if historical_sales > historical_import else 'stable'
        })

        total_predicted += predicted_import

        logger.info(f" {product_name}: current={current_qty}, predicted={predicted_import}, sales={historical_sales}")

    result = {
        'success': True,
        'predicted_products': predicted_products,  
        'predicted_quantity': total_predicted,  
        'trend': 'increasing' if total_predicted > 0 else 'stable',
        'confidence': sum(p['confidence'] for p in predicted_products) / len(predicted_products) if predicted_products else 0,
        'historical_mean': total_predicted,
        'model_type': 'LSTM Time-Series (Heuristic)',
        'timestamp': datetime.now().isoformat()
    }

    logger.info(f"[MODEL 2] Forecast complete: Total predicted import = {total_predicted} units")

    return result


def format_forecast_response(prediction, history_count=None):
    
    predicted_qty = int(prediction.get('predicted_quantity', 0))
    trend_text = prediction.get('trend', 'stable')
    confidence = float(prediction.get('confidence', 0.0))
    historical_mean = prediction.get('historical_mean', predicted_qty)
    predicted_products = prediction.get('predicted_products', [])

    logger.info("[OUTPUT] Formatting Y2 output for FINAL OUTPUT/UI")

    # Generate output1 - Main prediction result with product details
    if trend_text == 'increasing':
        trend_icon = ''
        trend_desc = 'Increasing'
    elif trend_text == 'decreasing':
        trend_icon = ''
        trend_desc = 'Decreasing'
    else:
        trend_icon = ''
        trend_desc = 'Stable'

    output1 = f"{trend_icon} Total Predicted Import: {predicted_qty} products (Trend: {trend_desc})"

    # Generate output2 - Simple product list
    output2_lines = []

    # Product-level predictions 
    if predicted_products:
        output2_lines.append("Predicted Products:")
        output2_lines.append("")
        for i, product in enumerate(predicted_products[:15], 1):  # Show top 15 products
            product_name = product['product_name']
            pred_qty = product['predicted_quantity']
            output2_lines.append(f"{i}. {product_name}: {pred_qty} products")

        if len(predicted_products) > 15:
            remaining = len(predicted_products) - 15
            output2_lines.append(f"... and {remaining} more products")

        output2_lines.append("")

        # Summary
        output2_lines.append(f"Total: {predicted_qty} products")
        output2_lines.append(f"Trend: {trend_desc}")
        output2_lines.append(f"Prediction Confidence: {confidence * 100:.1f}%")

    output2 = '\n'.join(output2_lines)

    return {
        'success': True,
        'message': 'Forecast completed successfully',
        'predicted_quantity': predicted_qty,
        'predicted_products': predicted_products,
        'trend': trend_text,
        'confidence': confidence,
        'output1': output1,
        'output2': output2,
        'recommendation': prediction.get('recommendation', 'maintain'),
        'recommendation_text': output2,
        'history_count': history_count or 0,
        'timestamp': datetime.now().isoformat()
    }
