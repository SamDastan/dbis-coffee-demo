def single_exponential_smoothing(values, alpha):
    if not values:
        return []

    smoothed = [values[0]]

    for value in values[1:]:
        next_smoothed = alpha * value + (1 - alpha) * smoothed[-1]
        smoothed.append(next_smoothed)

    return smoothed


def forecast_future(values, alpha, horizon):
    smoothed = single_exponential_smoothing(values, alpha)

    if not smoothed:
        return []

    last_level = smoothed[-1]
    return [last_level for _ in range(horizon)]


def rolling_evaluation_forecast(train_values, test_values, alpha):
    smoothed = single_exponential_smoothing(train_values, alpha)

    if not smoothed:
        return []

    current_level = smoothed[-1]
    forecasts = []

    for actual_value in test_values:
        forecasts.append(current_level)
        current_level = alpha * actual_value + (1 - alpha) * current_level

    return forecasts
