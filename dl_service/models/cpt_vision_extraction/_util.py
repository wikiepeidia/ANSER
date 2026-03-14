import numpy as np

def calculate_metrics(preds, targets, ignore_index=-100, num_classes=5):
    """
    Calculate precision, recall, and F1 for each class and overall.
    preds: list of 1D numpy arrays or a flat array
    targets: list of 1D numpy arrays or a flat array
    """
    if isinstance(preds, list):
        preds = np.concatenate(preds)
        targets = np.concatenate(targets)
        
    mask = targets != ignore_index
    preds = preds[mask]
    targets = targets[mask]
    
    metrics = {}
    total_tp = 0
    total_fp = 0
    total_fn = 0
    
    # Classes: 0=other, 1=company, 2=date, 3=address, 4=total
    class_names = {1: "company", 2: "date", 3: "address", 4: "total"}
    
    for c in range(1, num_classes):  # Skip 'other' class
        tp = np.sum((preds == c) & (targets == c))
        fp = np.sum((preds == c) & (targets != c))
        fn = np.sum((preds != c) & (targets == c))
        
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
        
        metrics[class_names[c]] = {
            "precision": precision,
            "recall": recall,
            "f1": f1
        }
        
        total_tp += tp
        total_fp += fp
        total_fn += fn
        
    overall_p = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0.0
    overall_r = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 0.0
    overall_f1 = 2 * overall_p * overall_r / (overall_p + overall_r) if (overall_p + overall_r) > 0 else 0.0
    
    metrics["overall"] = {
        "precision": overall_p,
        "recall": overall_r,
        "f1": overall_f1
    }
    
    return metrics
