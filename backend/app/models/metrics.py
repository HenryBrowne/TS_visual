import numpy as np


def compute_metrics(actual: np.ndarray, predicted: np.ndarray) -> dict[str, float]:
    actual = np.asarray(actual, dtype=float)
    predicted = np.asarray(predicted, dtype=float)
    errors = actual - predicted

    mae = float(np.mean(np.abs(errors)))
    rmse = float(np.sqrt(np.mean(errors**2)))

    # sMAPE instead of MAPE: stays well-defined when actuals include zeros,
    # which matters for the intermittent series this app profiles.
    denom = np.abs(actual) + np.abs(predicted)
    ratio = np.zeros_like(denom)
    nonzero = denom != 0
    ratio[nonzero] = 2 * np.abs(errors[nonzero]) / denom[nonzero]
    smape = float(np.mean(ratio) * 100)

    return {"mae": mae, "rmse": rmse, "smape": smape}
