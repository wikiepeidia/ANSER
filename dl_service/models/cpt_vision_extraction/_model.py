import torch
import torch.nn as nn

class MyBiLSTM(nn.Module):
    def __init__(self, vocab_size, embedding_dim=128, hidden_dim=256, num_classes=5, num_layers=2):
        super().__init__()
        self.embedding = nn.Embedding(vocab_size, embedding_dim)
        self.lstm = nn.LSTM(
            embedding_dim, 
            hidden_dim, 
            num_layers=num_layers, 
            bidirectional=True, 
            batch_first=True
        )
        self.fc = nn.Linear(hidden_dim * 2, num_classes)

    def forward(self, x):
        # x shape: (batch_size, seq_len)
        embedded = self.embedding(x)
        output, _ = self.lstm(embedded)
        # output shape: (batch_size, seq_len, hidden_dim * 2)
        logits = self.fc(output)
        # logits shape: (batch_size, seq_len, num_classes)
        return logits
