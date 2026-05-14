def levenshtein_distance(s1, s2):
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)
    if len(s2) == 0:
        return len(s1)

    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row

    return previous_row[-1]

def calculate_cer(preds, targets):
    total_distance = 0
    total_length = 0
    for p, t in zip(preds, targets):
        total_distance += levenshtein_distance(p, t)
        total_length += len(t)
    return total_distance / max(total_length, 1)

def calculate_wer(preds, targets):
    total_distance = 0
    total_length = 0
    for p, t in zip(preds, targets):
        p_words = p.split()
        t_words = t.split()
        total_distance += levenshtein_distance(p_words, t_words)
        total_length += len(t_words)
    return total_distance / max(total_length, 1)
