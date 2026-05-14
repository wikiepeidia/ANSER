import argparse
import os

import torch
from torch import optim
from torch.optim import lr_scheduler
from torch.utils.data import DataLoader, random_split, Subset
from torchvision import transforms
from tqdm import tqdm

from _data import Task1Dataset
from _model import CtpnModel


def parse_args():
    parser = argparse.ArgumentParser(description="Train Task 1 (CTPN Bounding-Box Detection)")
    
    # Data arguments
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(script_dir, "..", "data")
    
    parser.add_argument("--img_dir", type=str, default=os.path.join(data_dir, "img"), help="Directory containing receipt images")
    parser.add_argument("--box_dir", type=str, default=os.path.join(data_dir, "box"), help="Directory containing bounding box CSVs")
    
    # Hyperparameters
    parser.add_argument("--batch_size", type=int, default=1, help="Training batch size")
    parser.add_argument("--epochs", type=int, default=10, help="Number of training epochs")
    parser.add_argument("--lr", type=float, default=0.1, help="Learning rate")
    parser.add_argument("--gamma", type=float, default=0.1, help="Learning rate decay step")
    parser.add_argument("--num_workers", type=int, default=0, help="Number of dataloader workers")
    parser.add_argument("--val_split", type=float, default=0.1, help="Fraction of dataset to use for validation")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducible split")
    parser.add_argument(
        "--decision_threshold",
        type=float,
        default=0.5,
        help="Validation threshold for text probability when computing precision/recall/F1",
    )
    
    # Model arguments
    parser.add_argument("--n_anchor", type=int, default=5, help="Number of CTPN anchors")
    parser.add_argument("--img_height", type=int, default=448, help="Image resolution height")
    parser.add_argument("--img_width", type=int, default=224, help="Image resolution width")
    
    # Output arguments
    parser.add_argument("--checkpoint_dir", type=str, default=os.path.join(script_dir, "checkpoints"), help="Directory to save weights")
    parser.add_argument(
        "--cls_pos_weight",
        type=float,
        default=20.0,
        help="Positive-class weight for text anchors in classification loss",
    )
    parser.add_argument(
        "--resume_checkpoint",
        type=str,
        default="",
        help="Optional checkpoint path to resume/fine-tune from",
    )
    parser.add_argument(
        "--reset_optimizer",
        action="store_true",
        help="Do not load optimizer state when resuming (recommended for fine-tuning with new LR)",
    )
    
    return parser.parse_args()


def calculate_metrics(outputs, targets):
    """Anchor-level proxy metrics for text/non-text classification."""
    out_1, _, _ = outputs
    tgt_1, _, _ = targets

    preds = torch.argmax(out_1, dim=-1).reshape(-1)
    labels = tgt_1.reshape(-1)

    tp = ((preds == 1) & (labels == 1)).sum().item()
    fp = ((preds == 1) & (labels == 0)).sum().item()
    fn = ((preds == 0) & (labels == 1)).sum().item()

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1_iou_05 = (
        2 * precision * recall / (precision + recall)
        if (precision + recall) > 0
        else 0.0
    )
    return precision, recall, f1_iou_05


def main():
    args = parse_args()
    
    os.makedirs(args.checkpoint_dir, exist_ok=True)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")

    resolution = [args.img_height, args.img_width]
    
    print("Loading dataset...")
    # Build two datasets with identical samples but different transforms:
    # train -> augmentation, val -> deterministic tensor conversion.
    train_base = Task1Dataset(args.img_dir, args.box_dir, args.n_anchor, resolution)
    val_base = Task1Dataset(
        args.img_dir,
        args.box_dir,
        args.n_anchor,
        resolution,
        transform=transforms.ToTensor(),
    )

    # Train / Val Split (shared indices between both datasets)
    val_size = int(len(train_base) * args.val_split)
    train_size = len(train_base) - val_size
    split_generator = torch.Generator().manual_seed(args.seed)
    train_subset, val_subset = random_split(
        train_base,
        [train_size, val_size],
        generator=split_generator,
    )
    train_dataset = Subset(train_base, train_subset.indices)
    val_dataset = Subset(val_base, val_subset.indices)
    
    train_loader = DataLoader(train_dataset, batch_size=args.batch_size, shuffle=True, num_workers=args.num_workers)
    val_loader = DataLoader(val_dataset, batch_size=1, shuffle=False, num_workers=args.num_workers)

    print(f"Dataset split: {train_size} training samples, {val_size} validation samples")

    # Initialize model
    model = CtpnModel(args.n_anchor).to(device)

    # Loss Functions according to CTPN
    class_weights = torch.tensor([1.0, args.cls_pos_weight], device=device)
    criterion_1 = torch.nn.CrossEntropyLoss(weight=class_weights)
    criterion_2 = torch.nn.SmoothL1Loss(reduction="sum")
    criterion_3 = torch.nn.SmoothL1Loss(reduction="sum")

    # Optimizer & Scheduler
    optimizer = optim.Adagrad(model.parameters(), lr=args.lr)
    scheduler = lr_scheduler.ExponentialLR(optimizer, gamma=args.gamma)

    best_f1 = -1.0
    start_epoch = 1

    if args.resume_checkpoint:
        print(f"Resuming from checkpoint: {args.resume_checkpoint}")
        ckpt = torch.load(args.resume_checkpoint, map_location=device, weights_only=False)
        model.load_state_dict(ckpt["model_state_dict"])

        if (not args.reset_optimizer) and ("optimizer_state_dict" in ckpt):
            optimizer.load_state_dict(ckpt["optimizer_state_dict"])

        # Always enforce requested LR after potential optimizer-state load.
        for param_group in optimizer.param_groups:
            param_group["lr"] = args.lr

        start_epoch = int(ckpt.get("epoch", 0)) + 1
        best_f1 = float(ckpt.get("f1", -1.0))
        print(f"Resume epoch: {start_epoch} | Previous best F1: {best_f1:.4f}")

    print(f"Optimizer LR: {optimizer.param_groups[0]['lr']}")

    print("Starting training loop...")
    for epoch in range(start_epoch, args.epochs + 1):
        # --- Training Phase ---
        model.train()
        train_loss = 0.0
        
        train_pbar = tqdm(train_loader, desc=f"Epoch {epoch}/{args.epochs} [Train]")
        for batch in train_pbar:
            img, tgt_1, tgt_2, idx_2, tgt_3, idx_3 = [x.to(device) for x in batch]

            optimizer.zero_grad()
            out_1, out_2, out_3 = model(img)

            loss_1 = criterion_1(out_1.view(-1, 2), tgt_1.view(-1))
            
            # Use clamping/safety divisions depending on idx sums (smoothers)
            num_idx_2 = max(idx_2.sum().item(), 1.0)
            loss_2 = criterion_2(out_2[idx_2], tgt_2[idx_2]) / (num_idx_2 / 2.0)
            
            num_idx_3 = max(idx_3.sum().item(), 1.0)
            loss_3 = 2 * criterion_3(out_3[idx_3], tgt_3[idx_3]) / num_idx_3

            loss = loss_1 + loss_2 + loss_3
            loss.backward()
            optimizer.step()

            train_loss += loss.item() * img.size(0)
            train_pbar.set_postfix({"loss": f"{loss.item():.4f}"})

        train_loss /= train_size
        
        # --- Validation Phase ---
        model.eval()
        val_loss = 0.0
        
        val_tp = 0
        val_fp = 0
        val_fn = 0

        val_pbar = tqdm(val_loader, desc=f"Epoch {epoch}/{args.epochs} [Val]")
        with torch.no_grad():
            for batch in val_pbar:
                img, tgt_1, tgt_2, idx_2, tgt_3, idx_3 = [x.to(device) for x in batch]
                
                out_1, out_2, out_3 = model(img)

                loss_1 = criterion_1(out_1.view(-1, 2), tgt_1.view(-1))
                
                num_idx_2 = max(idx_2.sum().item(), 1.0)
                loss_2 = criterion_2(out_2[idx_2], tgt_2[idx_2]) / (num_idx_2 / 2.0)
                
                num_idx_3 = max(idx_3.sum().item(), 1.0)
                loss_3 = 2 * criterion_3(out_3[idx_3], tgt_3[idx_3]) / num_idx_3

                loss = loss_1 + loss_2 + loss_3
                val_loss += loss.item() * img.size(0)

                text_prob = torch.softmax(out_1, dim=-1)[..., 1]
                preds = text_prob >= args.decision_threshold
                val_tp += ((preds == 1) & (tgt_1 == 1)).sum().item()
                val_fp += ((preds == 1) & (tgt_1 == 0)).sum().item()
                val_fn += ((preds == 0) & (tgt_1 == 1)).sum().item()
                
                val_pbar.set_postfix({"loss": f"{loss.item():.4f}"})

        val_loss /= val_size
        avg_precision = val_tp / (val_tp + val_fp) if (val_tp + val_fp) > 0 else 0.0
        avg_recall = val_tp / (val_tp + val_fn) if (val_tp + val_fn) > 0 else 0.0
        avg_f1 = (
            2 * avg_precision * avg_recall / (avg_precision + avg_recall)
            if (avg_precision + avg_recall) > 0
            else 0.0
        )

        print(f"\nEpoch {epoch} Summary:")
        print(f"Train Loss: {train_loss:.4f} | Val Loss: {val_loss:.4f}")
        print(
            f"Val Metrics (thr={args.decision_threshold:.2f}) -> "
            f"Precision: {avg_precision:.4f} | Recall: {avg_recall:.4f} | F1: {avg_f1:.4f}"
        )

        # Checkpointing
        ckpt_path = os.path.join(args.checkpoint_dir, f"task1_epoch_{epoch}.pth")
        
        state_dict = {
            "epoch": epoch,
            "model_state_dict": model.state_dict(),
            "optimizer_state_dict": optimizer.state_dict(),
            "loss": val_loss,
            "f1": avg_f1
        }
        
        torch.save(state_dict, ckpt_path)
        print(f"Saved checkpoint to {ckpt_path}")
        
        if avg_f1 >= best_f1:
            best_f1 = avg_f1
            best_ckpt_path = os.path.join(args.checkpoint_dir, "task1_best.pth")
            torch.save(state_dict, best_ckpt_path)
            print(f"--> Saved BEST model to {best_ckpt_path}")

        scheduler.step()

    print("Training complete!")

if __name__ == "__main__":
    main()
