"""
Input Validators
Validate request data and inputs
"""
import re
from werkzeug.datastructures import FileStorage


class ValidationError(Exception):
    """Custom validation error"""
    pass


def validate_image_file(file):
    """
    Validate uploaded image file
    
    Args:
        file: FileStorage object
        
    Raises:
        ValidationError: If validation fails
        
    Returns:
        True if valid
    """
    if not file:
        raise ValidationError("No file provided")
    
    if not isinstance(file, FileStorage):
        raise ValidationError("Invalid file object")
    
    if file.filename == '':
        raise ValidationError("Empty filename")
    
    # Check extension
    allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'pdf'}
    ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
    
    if ext not in allowed_extensions:
        raise ValidationError(
            f"Invalid file extension '{ext}'. Allowed: {', '.join(allowed_extensions)}"
        )
    
    # Check file size (max 16MB)
    file.seek(0, 2)  # Seek to end
    size = file.tell()
    file.seek(0)  # Reset
    
    max_size = 16 * 1024 * 1024  # 16MB
    if size > max_size:
        raise ValidationError(f"File too large ({size} bytes). Max: {max_size} bytes")
    
    if size == 0:
        raise ValidationError("Empty file")
    
    return True


def validate_invoice_data(data):
    """
    Validate manual invoice data input
    
    Args:
        data: String input from user
        
    Raises:
        ValidationError: If validation fails
        
    Returns:
        True if valid
    """
    if not data or not isinstance(data, str):
        raise ValidationError("Invoice data must be a non-empty string")
    
    data = data.strip()
    if not data:
        raise ValidationError("Invoice data is empty")
    
    # Check format: "Product - Quantity"
    lines = [line.strip() for line in data.split('\n') if line.strip()]
    
    if not lines:
        raise ValidationError("No valid lines found in invoice data")
    
    valid_lines = 0
    for line in lines:
        if '-' in line or ':' in line:
            parts = line.replace(':', '-').split('-', 1)
            if len(parts) == 2:
                try:
                    quantity = int(parts[1].strip())
                    if quantity > 0:
                        valid_lines += 1
                except ValueError:
                    continue
    
    if valid_lines == 0:
        raise ValidationError(
            'Invalid format. Use: "Product Name - Quantity" (one per line)'
        )
    
    return True


def validate_quantity(value):
    """
    Validate quantity value
    
    Args:
        value: Quantity to validate
        
    Raises:
        ValidationError: If invalid
        
    Returns:
        int: Validated quantity
    """
    try:
        qty = int(value)
        if qty < 0:
            raise ValidationError("Quantity cannot be negative")
        if qty > 1000000:
            raise ValidationError("Quantity too large (max: 1,000,000)")
        return qty
    except (ValueError, TypeError):
        raise ValidationError(f"Invalid quantity: {value}")


def validate_store_key(store_key):
    """
    Validate store key
    
    Args:
        store_key: Store identifier
        
    Raises:
        ValidationError: If invalid
        
    Returns:
        str: Validated store key
    """
    # QUANTUNG/Tung scenario removed - only 'son' supported
    allowed_stores = ['son']
    
    if not store_key:
        raise ValidationError("Store key is required")
    
    if store_key not in allowed_stores:
        raise ValidationError(
            f"Invalid store '{store_key}'."
        )
    
    return store_key


def sanitize_filename(filename):
    """
    Sanitize filename for safe storage
    
    Args:
        filename: Original filename
        
    Returns:
        str: Safe filename
    """
    # Remove non-alphanumeric characters (keep dots, underscores, hyphens)
    filename = re.sub(r'[^\w\s\-\.]', '', filename)
    # Replace spaces with underscores
    filename = filename.replace(' ', '_')
    # Limit length
    name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
    name = name[:100]  # Max 100 chars for name
    
    return f"{name}.{ext}" if ext else name
