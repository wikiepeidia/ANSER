import os
import argparse
import torch
from torch.utils.data import DataLoader
from tqdm import tqdm
import json

from _data import SROIEDataset, collate_fn, CHAR2IDX
from _model import MyBiLSTM
from _loss import get_loss_fn
from _util import calculate_metrics

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    default_train = os.path.join(script_dir, "..", "data", "processed", "train_dict.pth")
    default_val = os.path.join(script_dir, "..", "data", "processed", "test_dict.pth")
    
    parser = argparse.ArgumentParser(description="Task 3: Key Information Extraction Training")
    parser.add_argument("--train_dict", type=str, default=default_train, help="Path to training data dict")
    parser.add_argument("--val_dict", type=str, default=default_val, help="Path to validation data dict")
    parser.add_argument("--batch_size", type=int, default=8, help="Batch size")
    parser.add_argument("--epochs", type=int, default=20, help="Number of epochs to train")
    parser.add_argument("--lr", type=float, default=1e-3, help="Learning rate")
    parser.add_argument("--embedding_dim", type=int, default=128, help="Embedding dimension")
    parser.add_argument("--hidden_dim", type=int, default=256, help="LSTM hidden dimension")
    parser.add_argument("--num_layers", type=int, default=2, help="Number of LSTM layers")
    parser.add_argument("--save_dir", type=str, default="checkpoints", help="Directory to save checkpoints")
    
    args = parser.parse_args()
    
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")
    
    os.makedirs(args.save_dir, exist_ok=True)
    
    # Data loaders
    print("Loading datasets...")
    train_dataset = SROIEDataset(args.train_dict)
    val_dataset = SROIEDataset(args.val_dict)
    
    train_loader = DataLoader(train_dataset, batch_size=args.batch_size, shuffle=True, collate_fn=collate_fn)
    val_loader = DataLoader(val_dataset, batch_size=args.batch_size, shuffle=False, collate_fn=collate_fn)
    
    # Model
    vocab_size = len(CHAR2IDX)
    model = MyBiLSTM(
        vocab_size=vocab_size,
        embedding_dim=args.embedding_dim,
        hidden_dim=args.hidden_dim,
        num_classes=5,  # 0=other, 1=company, 2=date, 3=address, 4=total
        num_layers=args.num_layers
    ).to(device)
    
    criterion = get_loss_fn(ignore_index=-100)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr)
    
    best_f1 = 0.0
    
    for epoch in range(1, args.epochs + 1):
        print(f"\\nEpoch {epoch}/{args.epochs}")
        
        # Training
        model.train()
        train_loss = 0.0
        train_preds, train_targets = [], []
        
        for xs, ys in tqdm(train_loader, desc="Training"):
            xs, ys = xs.to(device), ys.to(device)
            
            optimizer.zero_grad()
            logits = model(xs)  # (B, L, C)
            
            # Reshape for loss: (B*L, C) and (B*L,)
            logits_flat = logits.view(-1, 5)
            ys_flat = ys.view(-1)
            
            loss = criterion(logits_flat, ys_flat)
            loss.backward()
            optimizer.step()
            
            train_loss += loss.item()
            
            preds = torch.argmax(logits, dim=-1)
            train_preds.append(preds.detach().cpu().numpy().flatten())
            train_targets.append(ys_flat.detach().cpu().numpy().flatten())
            
        train_loss /= len(train_loader)
        train_metrics = calculate_metrics(train_preds, train_targets)
        print(f"Train Loss: {train_loss:.4f} | Train Overall F1: {train_metrics['overall']['f1']:.4f}")
        
        # Validation
        model.eval()
        val_loss = 0.0
        val_preds, val_targets = [], []
        
        with torch.no_grad():
            for xs, ys in tqdm(val_loader, desc="Validation"):
                xs, ys = xs.to(device), ys.to(device)
                
                logits = model(xs)
                
                logits_flat = logits.view(-1, 5)
                ys_flat = ys.view(-1)
                
                loss = criterion(logits_flat, ys_flat)
                val_loss += loss.item()
                
                preds = torch.argmax(logits, dim=-1)
                val_preds.append(preds.detach().cpu().numpy().flatten())
                val_targets.append(ys_flat.detach().cpu().numpy().flatten())
                
        val_loss /= len(val_loader)
        val_metrics = calculate_metrics(val_preds, val_targets)
        
        print(f"Val Loss: {val_loss:.4f}")
        print("Val Metrics:")
        for k, v in val_metrics.items():
            if k == "overall":
                print(f"  {k}: P={v['precision']:.4f}, R={v['recall']:.4f}, F1={v['f1']:.4f}")
            else:
                print(f"  {k}: F1={v['f1']:.4f}")
                
        # Checkpoint
        save_path = os.path.join(args.save_dir, f"task3_epoch_{epoch}.pth")
        torch.save({
            "epoch": epoch,
            "model_state_dict": model.state_dict(),
            "optimizer_state_dict": optimizer.state_dict(),
            "metrics": val_metrics
        }, save_path)
        
        if val_metrics["overall"]["f1"] > best_f1:
            best_f1 = val_metrics["overall"]["f1"]
            best_path = os.path.join(args.save_dir, "task3_best.pth")
            torch.save({
                "epoch": epoch,
                "model_state_dict": model.state_dict(),
                "optimizer_state_dict": optimizer.state_dict(),
                "metrics": val_metrics
            }, best_path)
            print(f"Saved new best model to {best_path}")

if __name__ == "__main__":
    main()
