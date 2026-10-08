"""Demo Context only: eight explicit MOCK fields, never analysis inputs."""
import numpy as np
import pandas as pd

from src.utils import stable_int

MOCK_RULES = {
    'driver_id': '競賽資料缺駕駛身分的 Prototype placeholder；每車 2–3 名虛擬駕駛依日期輪值。正式產品先確認 iTRAQ driverUid／tachographDriver',
    'task_type': '里程至少 80 km 模擬跨城；其餘 75% 市區配送、25% 車庫間調度；用途：行程前任務情境',
    'payload_ratio': '依模擬任務採 Beta(5,2)、Beta(3,3)、Beta(2,4)，系列雜湊偏移 0–0.4；用途：行程探索 Future Enrichment',
    'traffic_level': '07–09、16–19 時高／中／低為 65%／25%／10%；其餘 15%／40%／45%；用途：行程前路況情境',
    'delivery_window': '行程開始整點起兩小時；用途：教練頁與調度核對窗口的 Demo Context',
    'stop_purpose': '怠速超過 20 分鐘模擬倉儲等待／配送／休息／未知為 55%／25%／10%／10%；其餘依任務；用途：熱點與待核對停靠用途',
    'mock_generation_rule': 'v2；種子 42 與每趟 SHA256 RNG；用途：資料與假設的重現性說明',
    'is_mock': '標記上述情境欄位；用途：MOCK badge，不表示原始車聯網量測為虛構',
}


def generate_mock_context(trips, seed=42):
    records = []
    for t in trips.itertuples(index=False):
        rng = np.random.default_rng(np.random.SeedSequence([seed, stable_int(t.trip_id)]))
        start = pd.Timestamp(t.start_time)
        hour, day = start.hour, start.toordinal()
        roster_count = 2 + stable_int(t.enabledCode) % 2
        driver = f'MOCK-D-{stable_int(t.enabledCode):016x}-{(day + (hour < 6 or hour >= 18)) % roster_count + 1}'
        task = 'intercity' if t.trip_distance_km >= 80 else str(rng.choice(['urban_delivery', 'depot_transfer'], p=[.75, .25]))
        a, b = {'intercity': (5, 2), 'urban_delivery': (3, 3), 'depot_transfer': (2, 4)}[task]
        a += (stable_int(t.vehicle_type) % 5) / 10
        stop = str(rng.choice(['warehouse_wait', 'delivery', 'rest', 'unknown'], p=[.55, .25, .1, .1])) if t.idle_minutes > 20 else {
            'urban_delivery': 'delivery', 'depot_transfer': 'pickup', 'intercity': 'rest'}[task]
        records.append({'trip_id': t.trip_id, 'driver_id': driver, 'task_type': task,
                        'payload_ratio': round(float(rng.beta(a, b)), 4),
                        'traffic_level': str(rng.choice(['high', 'medium', 'low'], p=[.65, .25, .1] if (7 <= hour <= 9 or 16 <= hour <= 19) else [.15, .4, .45])),
                        'delivery_window': start.floor('h').strftime('%H:%M') + '–' + (start.floor('h') + pd.Timedelta(hours=2)).strftime('%H:%M'),
                        'stop_purpose': stop, 'mock_generation_rule': f'v2; seed={seed}; stable per-trip SHA256 RNG', 'is_mock': True})
    return pd.DataFrame(records, columns=['trip_id', *MOCK_RULES])
