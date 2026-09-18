def walk_forward_splits(n_rows, min_train=120, folds=4):
    """Ventanas crecientes: entrena con pasado y valida únicamente con futuro."""
    if n_rows <= min_train + folds:
        return []

    remaining = n_rows - min_train
    step = max(1, remaining // folds)
    splits = []
    train_end = min_train

    while train_end < n_rows and len(splits) < folds:
        test_end = min(n_rows, train_end + step)
        if test_end <= train_end:
            break
        splits.append((range(0, train_end), range(train_end, test_end)))
        train_end = test_end

    return splits


def _roc_auc(y_true, probabilities):
    """AUC binario por suma de rangos, incluyendo empates."""
    pairs = sorted(
        [(float(p), int(y)) for y, p in zip(y_true, probabilities)],
        key=lambda x: x[0],
    )
    positives = sum(y for _, y in pairs)
    negatives = len(pairs) - positives
    if positives == 0 or negatives == 0:
        return 0.5

    positive_rank_sum = 0.0
    i = 0
    rank = 1
    while i < len(pairs):
        j = i + 1
        while j < len(pairs) and pairs[j][0] == pairs[i][0]:
            j += 1
        count = j - i
        average_rank = (rank + (rank + count - 1)) / 2.0
        positive_count = sum(pairs[k][1] for k in range(i, j))
        positive_rank_sum += positive_count * average_rank
        rank += count
        i = j

    return (
        positive_rank_sum - positives * (positives + 1) / 2.0
    ) / (positives * negatives)


def classification_metrics(y_true, probabilities, threshold=0.5):
    y_true = [int(v) for v in y_true]
    probabilities = [float(v) for v in probabilities]
    if not y_true:
        return {
            "accuracy": 0.0,
            "precision": 0.0,
            "recall": 0.0,
            "f1": 0.0,
            "roc_auc": 0.5,
            "samples": 0,
        }

    predictions = [1 if p >= threshold else 0 for p in probabilities]
    tp = tn = fp = fn = 0

    for real, pred in zip(y_true, predictions):
        if real == 1 and pred == 1:
            tp += 1
        elif real == 0 and pred == 0:
            tn += 1
        elif real == 0 and pred == 1:
            fp += 1
        elif real == 1 and pred == 0:
            fn += 1

    total = len(y_true)
    accuracy = (tp + tn) / total if total else 0.0
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0

    return {
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "roc_auc": _roc_auc(y_true, probabilities),
        "samples": total,
    }
