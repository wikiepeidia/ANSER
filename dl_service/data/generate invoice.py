# -*- coding: utf-8 -*-
"""
Generate Balanced Dataset with Proper Splits
Train: 70% (840 images)
Valid: 20% (240 images)
Test:  10% (120 images)
Total: 1200 images from dataset_product.csv

Date range: October 1, 2025 → November 1, 2025
"""
import os
import sys
import json
import random
from pathlib import Path
from datetime import datetime, timedelta
from PIL import Image, ImageDraw, ImageFont

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def load_products_from_csv(csv_path='data/dataset_product.csv'):
    """Load product data from CSV"""
    import pandas as pd
    
    df = pd.read_csv(csv_path, sep=';')
    
    # Clean price columns
    def clean_price(val):
        if pd.isna(val):
            return 0
        if isinstance(val, str):
            return float(val.replace('.', '').replace(',', ''))
        return float(val)
    
    products = []
    for _, row in df.iterrows():
        products.append({
            'name': str(row.iloc[0]).strip(),  # Product name
            'stock': int(row.iloc[1]) if pd.notna(row.iloc[1]) else 0,  # Stock quantity
            'import_price': clean_price(row.iloc[2]) if len(row) > 2 else 0,  # Import price
            'retail_price': clean_price(row.iloc[3]) if len(row) > 3 else 0,  # Retail price
        })
    
    # Filter out products with invalid prices
    products = [p for p in products if p['retail_price'] > 0 and p['import_price'] > 0]
    
    print(f"   Loaded {len(products)} valid products from {csv_path}")
    return products


def generate_invoice_image(products, invoice_data, date, img_width=800, img_height=1000):
    """Generate a simple invoice image with proper alignment"""
    
    # Create image with white background
    img = Image.new('RGB', (img_width, img_height), color='white')
    draw = ImageDraw.Draw(img)
    
    # Try to load a font, fallback to default if not available
    try:
        title_font = ImageFont.truetype("arial.ttf", 24)
        header_font = ImageFont.truetype("arial.ttf", 16)
        text_font = ImageFont.truetype("arial.ttf", 14)
    except:
        title_font = ImageFont.load_default()
        header_font = ImageFont.load_default()
        text_font = ImageFont.load_default()
    
    # Define column positions for perfect alignment
    margin_left = 20
    margin_right = img_width - 20
    col_san_pham = margin_left
    col_sl = 340
    col_don_gia = 420
    col_thanh_tien = 580
    
    # Draw header
    y = 20
    draw.text((img_width//2 - 120, y), "HOA DON BAN HANG", fill='black', font=title_font)
    y += 40
    
    draw.text((margin_left, y), f"Ngay: {date.strftime('%d/%m/%Y')}", fill='black', font=header_font)
    y += 30
    
    # Draw separator line (full width)
    draw.line([(margin_left, y), (margin_right, y)], fill='black', width=1)
    y += 25
    
    # Draw table header with proper alignment
    draw.text((col_san_pham, y), "San Pham", fill='black', font=header_font)
    draw.text((col_sl, y), "SL", fill='black', font=header_font)
    draw.text((col_don_gia, y), "Don Gia", fill='black', font=header_font)
    draw.text((col_thanh_tien, y), "Thanh Tien", fill='black', font=header_font)
    y += 25
    
    # Draw separator line (full width)
    draw.line([(margin_left, y), (margin_right, y)], fill='black', width=1)
    y += 20
    
    # Draw products with proper column alignment
    for idx, item in enumerate(invoice_data['products'], 1):
        # Product name (truncate if too long to fit in column)
        name = item['name'][:35]
        draw.text((col_san_pham, y), name, fill='black', font=text_font)
        
        # Center-align quantity
        sl_text = str(item['quantity'])
        draw.text((col_sl, y), sl_text, fill='black', font=text_font)
        
        # Right-align prices for better readability
        don_gia_text = f"{item['unit_price']:,.0f}"
        draw.text((col_don_gia, y), don_gia_text, fill='black', font=text_font)
        
        thanh_tien_text = f"{item['line_total']:,.0f}"
        draw.text((col_thanh_tien, y), thanh_tien_text, fill='black', font=text_font)
        
        y += 22
        
        if y > img_height - 100:  # Stop if we run out of space
            break
    
    # Draw footer separator line (full width)
    y += 10
    draw.line([(margin_left, y), (margin_right, y)], fill='black', width=1)
    y += 25
    
    # Draw total with proper alignment (right side)
    total_text = f"Tong Cong: {invoice_data['total_amount']:,.0f} VND"
    draw.text((col_thanh_tien - 100, y), total_text, fill='black', font=header_font)
    
    return img


def generate_balanced_dataset(total_images=400):
    """
    Generate balanced dataset from dataset_product.csv only
    Date range: October 1, 2025 → November 1, 2025
    
    Args:
        total_images: Total number of images to generate (default 400)
    """
    
    print("="*70)
    print("  INVOICE DATASET GENERATION")
    print("  Source: dataset_product.csv")
    print("  Date Range: October 1, 2025 → November 1, 2025")
    print("="*70)
    
    # Calculate splits
    splits = {
        'train': int(total_images * 0.70),  # 280 images
        'valid': int(total_images * 0.20),  # 80 images  
        'test': int(total_images * 0.10)    # 40 images
    }
    
    print(f"\nTotal images: {total_images}")
    print(f"  Train: {splits['train']} ({splits['train']/total_images*100:.0f}%)")
    print(f"  Valid: {splits['valid']} ({splits['valid']/total_images*100:.0f}%)")
    print(f"  Test:  {splits['test']} ({splits['test']/total_images*100:.0f}%)")
    print()
    
    # Create output directories
    base_dir = Path('data/generated_invoices')
    for split in ['train', 'valid', 'test']:
        (base_dir / split).mkdir(parents=True, exist_ok=True)
    
    # Load products
    print("\n" + "="*70)
    print("LOADING PRODUCTS FROM dataset_product.csv")
    print("="*70)
    products = load_products_from_csv('data/dataset_product.csv')
    
    if len(products) == 0:
        raise ValueError("No valid products loaded from dataset_product.csv")
    
    # Date range: October 1, 2025 → November 1, 2025
    start_date = datetime(2025, 10, 1)
    end_date = datetime(2025, 11, 1)
    date_range_days = (end_date - start_date).days
    
    print(f"\nDate range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
    print(f"Total days: {date_range_days}")
    
    # ==========================================
    # Generate invoice images
    # ==========================================
    print("\n" + "="*70)
    print("GENERATING INVOICE IMAGES")
    print("="*70)
    
    all_metadata = {
        'train': [],
        'valid': [],
        'test': []
    }
    
    image_counter = 0
    
    for split in ['train', 'valid', 'test']:
        num_images = splits[split]
        print(f"\nGenerating {num_images} {split} images...")
        
        for i in range(num_images):
            # Random number of products per invoice (2-15 items)
            num_products_in_invoice = random.randint(2, 15)
            
            # Random date within range
            random_days = random.randint(0, date_range_days - 1)
            invoice_date = start_date + timedelta(days=random_days)
            
            # Select random products
            selected_products = random.sample(products, min(num_products_in_invoice, len(products)))
            
            # Generate invoice data
            invoice_items = []
            total_amount = 0
            
            for product in selected_products:
                quantity = random.randint(1, 20)  # Random quantity
                unit_price = product['retail_price']
                line_total = quantity * unit_price
                
                invoice_items.append({
                    'name': product['name'],
                    'quantity': quantity,
                    'unit_price': unit_price,
                    'line_total': line_total
                })
                total_amount += line_total
            
            invoice_data = {
                'date': invoice_date.strftime('%Y-%m-%d'),
                'products': invoice_items,
                'num_products': num_products_in_invoice,
                'total_amount': total_amount,
                'store_name': 'Retail Store'
            }
            
            # Generate image
            img = generate_invoice_image(products, invoice_data, invoice_date)
            
            # Save to proper split folder
            img_filename = f"invoice_{split}_{image_counter:04d}.png"
            img_path = base_dir / split / img_filename
            img.save(img_path)
            
            # Update metadata
            invoice_data['image_path'] = str(img_path)
            all_metadata[split].append(invoice_data)
            
            image_counter += 1
            
            if (i + 1) % 50 == 0:
                print(f"  Generated {i + 1}/{num_images} images...")
        
        print(f"   {split} complete: {num_images} images")
    
    # ==========================================
    # Save metadata
    # ==========================================
    print("\n" + "="*70)
    print("SAVING METADATA")
    print("="*70)
    
    for split in ['train', 'valid', 'test']:
        # Shuffle
        random.shuffle(all_metadata[split])
        
        # Save
        metadata_path = base_dir / f"{split}_metadata.json"
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(all_metadata[split], f, ensure_ascii=False, indent=2)
        
        print(f"  {split}: {len(all_metadata[split])} images -> {metadata_path}")
    
    # ==========================================
    # Print final summary
    # ==========================================
    print("\n" + "="*70)
    print("DATASET GENERATION COMPLETE!")
    print("="*70)
    
    total_train = len(all_metadata['train'])
    total_valid = len(all_metadata['valid'])
    total_test = len(all_metadata['test'])
    total_all = total_train + total_valid + total_test
    
    print(f"\nFinal Statistics:")
    print(f"  Train: {total_train} images ({total_train/total_all*100:.1f}%)")
    print(f"  Valid: {total_valid} images ({total_valid/total_all*100:.1f}%)")
    print(f"  Test:  {total_test} images ({total_test/total_all*100:.1f}%)")
    print(f"\nTotal: {total_all} images")
    print(f"Source: dataset_product.csv ({len(products)} products)")
    print(f"Date range: October 1, 2025 → November 1, 2025")
    print(f"\nAll images saved to: {base_dir}")
    print(f"  - train/ : Training images")
    print(f"  - valid/ : Validation images")
    print(f"  - test/  : Test images")
    print()


if __name__ == '__main__':
    # Generate 1200 images from dataset_product.csv
    generate_balanced_dataset(total_images=1200)
