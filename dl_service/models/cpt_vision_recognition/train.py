import argparse
import os
import random

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader

import _dataset as dataset
import _utils as utils
from _model import CRNN
from _util import calculate_cer, calculate_wer


def parse_args():
    parser = argparse.ArgumentParser(description="Train CRNN for Task 2 (OCR)")
    parser.add_argument("--train_root", default="dataset/train", help="Path to train LMDB")
    parser.add_argument("--val_root", default="dataset/val", help="Path to validation LMDB")
    parser.add_argument("--workers", type=int, default=2, help="Number of data loading workers")
    parser.add_argument("--batch_size", type=int, default=64, help="Input batch size")
    parser.add_argument("--img_h", type=int, default=32, help="The height of the input image to network")
    parser.add_argument("--img_w", type=int, default=200, help="The width of the input image to network")
    parser.add_argument("--nh", type=int, default=256, help="Size of the lstm hidden state")
    parser.add_argument("--epochs", type=int, default=25, help="Number of epochs to train for")
    parser.add_argument("--lr", type=float, default=0.001, help="Learning rate")
    parser.add_argument("--checkpoint_dir", default="expr", help="Where to store models")
    parser.add_argument("--pretrained", default="", help="Path to pretrained model (to continue training)")
    parser.add_argument("--alphabet", type=str, default=r'0123456789,.:(%$!^&-/);<~|`>?+=_[]{}"\'@#*ABCDEFGHIJKLMNOPQRSTUVWXYZ\ ')
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    return parser.parse_args()


def weights_init(m):
    classname = m.__class__.__name__
    if classname.find("Conv") != -1:
        torch.nn.init.normal_(m.weight.data, 0.0, 0.02)
    elif classname.find("BatchNorm") != -1:
        torch.nn.init.normal_(m.weight.data, 1.0, 0.02)
        torch.nn.init.constant_(m.bias.data, 0)


def train_one_epoch(model, dataloader, criterion, optimizer, converter, device, epoch):
    model.train()
    total_loss = 0
    
    for i, (cpu_images, cpu_texts) in enumerate(dataloader):
        batch_size = cpu_images.size(0)
        images = cpu_images.to(device)

        # encode texts
        t, l = converter.encode(cpu_texts)
        texts = t.to(device)
        lengths = l.to(device)

        preds = model(images)  # [seq_len, batch_size, num_classes]
        preds_size = torch.IntTensor([preds.size(0)] * batch_size).to(device)

        loss = criterion(preds, texts, preds_size, lengths)
        
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

        total_loss += loss.item()

        if (i + 1) % 100 == 0:
            print(f"Epoch [{epoch}] Batch [{i+1}/{len(dataloader)}] Loss: {loss.item() / batch_size:.4f}")

    return total_loss / len(dataloader)


def validate(model, dataloader, converter, device):
    model.eval()
    all_preds = []
    all_targets = []
    
    with torch.no_grad():
        for cpu_images, cpu_texts in dataloader:
            batch_size = cpu_images.size(0)
            images = cpu_images.to(device)

            preds = model(images)
            _, preds_idx = preds.max(2)
            preds_idx = preds_idx.transpose(1, 0).contiguous().view(-1)
            preds_size = torch.IntTensor([preds.size(0)] * batch_size).to(device)

            sim_preds = converter.decode(preds_idx.data, preds_size.data, raw=False)
            
            # Handle case where decode returns a string (batch_size=1) instead of list
            if isinstance(sim_preds, str):
                sim_preds = [sim_preds]
                
            all_preds.extend([p.lower() for p in sim_preds])
            all_targets.extend([t.lower() for t in cpu_texts])
            
    cer = calculate_cer(all_preds, all_targets)
    wer = calculate_wer(all_preds, all_targets)
    return cer, wer


def main():
    args = parse_args()
    os.makedirs(args.checkpoint_dir, exist_ok=True)

    random.seed(args.seed)
    torch.manual_seed(args.seed)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")

    # Data
    train_dataset = dataset.lmdbDataset(root=args.train_root)
    val_dataset = dataset.lmdbDataset(root=args.val_root, transform=dataset.resizeNormalize((args.img_w, args.img_h)))

    train_loader = DataLoader(
        train_dataset, batch_size=args.batch_size,
        shuffle=True, num_workers=args.workers,
        collate_fn=dataset.alignCollate(imgH=args.img_h, imgW=args.img_w, keep_ratio=False)
    )
    val_loader = DataLoader(
        val_dataset, batch_size=args.batch_size,
        shuffle=False, num_workers=args.workers
    )

    nclass = len(args.alphabet) + 1
    nc = 1

    converter = utils.strLabelConverter(args.alphabet)
    criterion = nn.CTCLoss(zero_infinity=True).to(device)

    model = CRNN(args.img_h, nc, nclass, args.nh).to(device)
    model.apply(weights_init)

    optimizer = optim.Adam(model.parameters(), lr=args.lr)

    start_epoch = 0
    if args.pretrained:
        print(f"Loading pretrained model from {args.pretrained}")
        checkpoint = torch.load(args.pretrained, map_location=device)
        model.load_state_dict(checkpoint["model_state_dict"])
        optimizer.load_state_dict(checkpoint["optimizer_state_dict"])
        start_epoch = checkpoint["epoch"] + 1

    for epoch in range(start_epoch, args.epochs):
        train_loss = train_one_epoch(model, train_loader, criterion, optimizer, converter, device, epoch)
        print(f"Epoch {epoch} Training Loss: {train_loss:.4f}")

        cer, wer = validate(model, val_loader, converter, device)
        print(f"Epoch {epoch} Validation CER: {cer:.4f} | WER: {wer:.4f}")

        checkpoint_path = os.path.join(args.checkpoint_dir, f"crnn_epoch_{epoch}.pth")
        torch.save(
            {
                "epoch": epoch,
                "model_state_dict": model.state_dict(),
                "optimizer_state_dict": optimizer.state_dict(),
                "cer": cer,
                "wer": wer,
            },
            checkpoint_path,
        )
        print(f"Saved checkpoint to {checkpoint_path}")


if __name__ == "__main__":
    main()
