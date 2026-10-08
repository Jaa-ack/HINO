"""Prototype screening parameters, not HINO calibration or causal coefficients."""
HINO_SERIES = {'300': 'HINO 300 系列', '500': 'HINO 500 系列', '700': 'HINO 700 系列'}
TYPE_DEFINITION = 'Type 為 HINO 車型系列代碼；300／500／700 分別代表 HINO 300／500／700 系列。現有資料不足以確認細部車型、噸位與引擎規格，因此僅用於系列分組比較。'
EVIDENCE_MODE = 'PRIMARY_EVIDENCE_MODE'
MIN_PEER_TRIPS = 5
MIN_PEER_VEHICLES = 2
# Bounded excess = max(actual - peer, 0) / (max(actual - peer, 0) + max(abs(peer), floor)).
# Floors handle zero peer medians; they are heuristic scales, never liter coefficients.
ANALYSIS_VERSION = 'ecopilot_v3'
SOURCE_CONTRACT_VERSION = 'competition+faq+event0929_v1'
EVENT_REFERENCE_VERSION = '0929'
LEVER_FEATURES = {'idle_context': ('idle_ratio', .05), 'rpm': ('rpm_above_2500_ratio', .05),
                  'engine_load': ('engine_load_above_90_ratio', .05)}
HEALTH_RESIDUAL_THRESHOLD = .15
HEALTH_STREAK_TRIPS = 3
HEALTH_MAX_DISTANCE = 8.
HEALTH_MAX_PEERS = 20
ML_NUMERIC_FEATURES = ['trip_distance_km', 'duration_minutes', 'idle_ratio', 'rpm_above_2500_ratio',
                       'engine_load_above_90_ratio', 'avg_speed']
ML_CATEGORICAL_FEATURES = ['vehicle_type', 'route_id', 'time_of_day']
