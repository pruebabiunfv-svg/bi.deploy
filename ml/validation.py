def walk_forward_splits(n_rows, min_train=120, folds=3):
    """Genera índices de entrenamiento creciente y validación futura sin mezclar el orden temporal."""
    if n_rows <= min_train + folds:
        return []
    remaining = n_rows - min_train
    step = max(1, remaining // folds)
    splits = []
    train_end = min_train
    while train_end < n_rows - 1 and len(splits) < folds:
        test_end = min(n_rows, train_end + step)
        splits.append((range(0, train_end), range(train_end, test_end)))
        train_end = test_end
    return splits


def classification_metrics(y_true, probabilities, threshold=0.5):
    if not y_true:
        return {"accuracy": 0.0, "samples": 0}
    preds = [1 if p >= threshold else 0 for p in probabilities]
    correct = sum(int(a == b) for a, b in zip(y_true, preds))
    return {"accuracy": correct / len(y_true), "samples": len(y_true)}
