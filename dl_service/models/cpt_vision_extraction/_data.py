import torch
from torch.utils.data import Dataset
import numpy as np
from string import ascii_uppercase, digits, punctuation

# Exactly the same VOCAB as in prepare_data.py
VOCAB = ascii_uppercase + digits + punctuation + " \t\n"
CHAR2IDX = {c: i + 1 for i, c in enumerate(VOCAB)}
CHAR2IDX["<PAD>"] = 0
CHAR2IDX["<UNK>"] = len(CHAR2IDX)

class SROIEDataset(Dataset):
    def __init__(self, dict_path):
        super().__init__()
        self.data_dict = torch.load(dict_path, weights_only=False)
        self.keys = list(self.data_dict.keys())

    def __len__(self):
        return len(self.keys)

    def __getitem__(self, idx):
        key = self.keys[idx]
        text, labels = self.data_dict[key]
        
        # Convert text to character indices
        x = [CHAR2IDX.get(c, CHAR2IDX["<UNK>"]) for c in text]
        
        return torch.tensor(x, dtype=torch.long), torch.tensor(labels, dtype=torch.long)

def collate_fn(batch):
    xs, ys = zip(*batch)
    
    # Pad sequences to max length in the batch
    x_padded = torch.nn.utils.rnn.pad_sequence(xs, batch_first=True, padding_value=CHAR2IDX["<PAD>"])
    # Use -100 as the standard PyTorch ignore_index.
    y_padded = torch.nn.utils.rnn.pad_sequence(ys, batch_first=True, padding_value=-100)
    
    return x_padded, y_padded
