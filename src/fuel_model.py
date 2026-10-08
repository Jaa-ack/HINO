"""Cross-vehicle matched residuals and optional grouped-validation ML."""
import numpy as np
import pandas as pd

from src.config import (MIN_PEER_TRIPS, MIN_PEER_VEHICLES, HEALTH_RESIDUAL_THRESHOLD,
    HEALTH_STREAK_TRIPS, HEALTH_MAX_DISTANCE, HEALTH_MAX_PEERS, ML_NUMERIC_FEATURES, ML_CATEGORICAL_FEATURES)


def analyze_vehicle_health(trips, min_peers=MIN_PEER_TRIPS):
    out = trips.copy()
    out["health_expected_fuel_l"] = np.nan
    out["health_peer_count"] = 0
    out["health_peer_vehicle_count"] = 0
    out["health_match_distance"] = np.nan
    pool = out.loc[out.benchmark_eligible].copy()
    grouped = {k: g for k, g in pool.groupby(["vehicle_type", "distance_bin"])}
    for idx, t in pool.iterrows():
        peers = grouped[(t.vehicle_type, t.distance_bin)]
        peers = peers.loc[peers.enabledCode.ne(t.enabledCode)].copy()
        if len(peers) < max(min_peers, MIN_PEER_TRIPS):
            continue
        distance = np.abs(np.log(peers.trip_distance_km / t.trip_distance_km)) / np.log(1.5)
        distance += .25 * np.abs(np.log(peers.duration_minutes.clip(lower=1) / max(t.duration_minutes, 1)))
        # All controls must be observed for a supported comparison.
        for feature, scale in [("idle_ratio", .15), ("rpm_above_2500_ratio", .1), ("engine_load_above_90_ratio", .2), ("avg_speed", 20)]:
            distance += (peers[feature] - t[feature]).abs() / scale
        distance += peers.route_id.ne(t.route_id).astype(float)
        peers["match_distance"] = distance
        peers = peers.loc[distance.le(HEALTH_MAX_DISTANCE)].nsmallest(HEALTH_MAX_PEERS, "match_distance")
        if len(peers) < max(min_peers, MIN_PEER_TRIPS) or peers.enabledCode.nunique() < MIN_PEER_VEHICLES:
            continue
        # Weighted median resists a few high-fuel peer outliers.
        intensity = peers.trip_fuel_l / peers.trip_distance_km
        ordered = np.argsort(intensity.to_numpy())
        weights = 1 / (1 + peers.match_distance.to_numpy()[ordered])
        median = intensity.to_numpy()[ordered][np.searchsorted(np.cumsum(weights), weights.sum() / 2)]
        out.loc[idx, "health_expected_fuel_l"] = median * t.trip_distance_km
        out.loc[idx, "health_peer_count"] = len(peers)
        out.loc[idx, "health_peer_vehicle_count"] = peers.enabledCode.nunique()
        out.loc[idx, "health_match_distance"] = peers.match_distance.mean()
    out["vehicle_residual_ratio"] = out.trip_fuel_l / out.health_expected_fuel_l - 1
    out["vehicle_health_flag"] = False
    out["consecutive_anomaly_trips"] = 0
    # Unknown / ineligible trips break the streak; no hidden cherry-picking of consecutive trips.
    for _, vehicle in out.sort_values(["start_time", "trip_id"]).groupby("enabledCode"):
        streak = 0
        for idx, t in vehicle.iterrows():
            streak = streak + 1 if pd.notna(t.vehicle_residual_ratio) and t.vehicle_residual_ratio > HEALTH_RESIDUAL_THRESHOLD else 0
            out.loc[idx, "consecutive_anomaly_trips"] = streak
            out.loc[idx, "vehicle_health_flag"] = streak >= HEALTH_STREAK_TRIPS
    return out


def evaluate_optional_ml(trips):
    """Validation / Scenario Support. Fit preprocessing AND baselines inside each split."""
    from sklearn.compose import ColumnTransformer
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.impute import SimpleImputer
    from sklearn.metrics import mean_absolute_error, r2_score
    from sklearn.model_selection import GroupKFold
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import OneHotEncoder

    numeric, categorical = ML_NUMERIC_FEATURES, ML_CATEGORICAL_FEATURES
    columns = ['trip_id', 'ml_oof_prediction_l', 'baseline_a_prediction_l', 'baseline_b_prediction_l', 'fold']
    df = trips.loc[trips.benchmark_eligible].reset_index(drop=True)
    if len(df) < 50 or df.enabledCode.nunique() < 3:
        return pd.DataFrame(columns=columns), {'status': 'insufficient_data', 'reason': 'Need at least 50 trips and three vehicles.'}

    def evaluate_split(train, test):
        transformer = ColumnTransformer([
            ('num', SimpleImputer(strategy='median', keep_empty_features=True), numeric),
            ('cat', Pipeline([('impute', SimpleImputer(strategy='most_frequent', keep_empty_features=True)),
                             ('encode', OneHotEncoder(handle_unknown='ignore', min_frequency=5, sparse_output=False))]), categorical)])
        estimator = Pipeline([('features', transformer), ('model', RandomForestRegressor(
            n_estimators=100, max_depth=9, min_samples_leaf=5, random_state=42, n_jobs=2))])
        estimator.fit(train[numeric + categorical], train.trip_fuel_l)
        predicted = estimator.predict(test[numeric + categorical])
        intensity = train.trip_fuel_l / train.trip_distance_km
        global_median = float(intensity.median())
        a = test.trip_distance_km.to_numpy() * global_median
        groups = train.assign(_intensity=intensity).groupby(['vehicle_type', 'distance_bin'])._intensity.median()
        b = np.array([groups.get((t.vehicle_type, t.distance_bin), global_median) * t.trip_distance_km for t in test.itertuples()])
        return predicted, a, b

    def metrics(actual, prediction, baseline_a, baseline_b):
        mae = float(mean_absolute_error(actual, prediction))
        a, b = float(mean_absolute_error(actual, baseline_a)), float(mean_absolute_error(actual, baseline_b))
        return {'mae_l': mae, 'r2': float(r2_score(actual, prediction)), 'baseline_a_mae_l': a, 'baseline_b_mae_l': b,
                'relative_improvement_vs_a': (a - mae) / a if a > 0 else None,
                'relative_improvement_vs_b': (b - mae) / b if b > 0 else None}

    predictions = np.full((len(df), 3), np.nan)
    folds = np.full(len(df), -1)
    n_splits = min(5, df.enabledCode.nunique())
    for fold, (train, test) in enumerate(GroupKFold(n_splits=n_splits).split(df, groups=df.enabledCode)):
        predictions[test] = np.column_stack(evaluate_split(df.iloc[train], df.iloc[test]))
        folds[test] = fold
    report = {'status': 'evaluated', 'purpose': 'Validation / Scenario Support', 'model': 'RandomForestRegressor',
              'random_seed': 42, 'validation': f'{n_splits}-fold GroupKFold by enabledCode; held-out vehicles',
              'n_trips': len(df), 'numeric_features': numeric, 'categorical_features': categorical,
              'baseline_a': 'Training-fold median L/km multiplied by test distance',
              'baseline_b': 'Training-fold vehicle_type + distance_bin median L/km; unseen groups fall back to A',
              **metrics(df.trip_fuel_l, *predictions.T)}
    times = pd.to_datetime(df.start_time)
    cutoff = times.sort_values().iloc[int(len(df) * .8)]
    ends = pd.to_datetime(df.end_time)
    train, test = df.loc[ends.lt(cutoff)], df.loc[times.ge(cutoff)]
    if len(train) >= 30 and len(test) >= 10 and (times.max() - times.min()).days >= 60:
        report['time_holdout'] = {'status': 'evaluated', 'train_trips': len(train), 'test_trips': len(test),
            'train_end': train.end_time.max().isoformat(), 'test_start': test.start_time.min().isoformat(),
            'overlap_trips_excluded': len(df) - len(train) - len(test),
            **metrics(test.trip_fuel_l, *evaluate_split(train, test))}
    else:
        report['time_holdout'] = {'status': 'insufficient_data', 'reason': 'Need 60-day span, 30 training and 10 test trips with nonoverlapping times.'}
    report['limitations'] = ('Retrospective validation only; same vehicles may appear in temporal holdout. '
        'Observed behavior is available only after the trip. Unmeasured payload, task, traffic and maintenance remain. '
        'No causal or realized-saving claim. Model outputs never drive primary KPIs or health flags.')
    return pd.DataFrame(dict(zip(columns, [df.trip_id, *predictions.T, folds]))), report
