import torch.nn as nn

def get_loss_fn(ignore_index=-100):
    return nn.CrossEntropyLoss(ignore_index=ignore_index)
