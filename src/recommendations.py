"""Python owns numerical evidence; personas receive qualitative next steps."""
import pandas as pd

from src.config import EVIDENCE_MODE, ANALYSIS_VERSION, SOURCE_CONTRACT_VERSION, EVENT_REFERENCE_VERSION
from src.mock_context import MOCK_RULES
from src.utils import DISCLAIMER, json_safe

PERSONAS = ['DRIVER', 'DISPATCHER', 'FLEET_MANAGER', 'MAINTENANCE']
FACTOR_NAMES = {'idle_context': '怠速／停留情境', 'rpm': '轉速型態', 'engine_load': '引擎負載型態'}
HEALTH_ACTION = '已觀測行程與行為的配對中，燃油殘差持續偏高；請核對保養、感測器與實際營運條件，安排車況檢查。'
# Fixed evidence contract also serves as the external API allow-list. No identifiers or coordinates.
EVIDENCE_UNITS = {
    'actual_fuel_l': 'L', 'expected_fuel_l': 'L', 'benchmark_gap_l': 'L', 'benchmark_gap_pct': '%',
    'idle_minutes': 'min', 'rpm_above_2500_ratio': 'ratio', 'engine_load_above_90_ratio': 'ratio',
    'peer_trip_count': 'trips', 'peer_vehicle_count': 'vehicles',
    'benchmark_quality': 'category', 'benchmark_level': 'category', 'vehicle_health_flag': 'boolean',
    'vehicle_residual_ratio': 'ratio', 'consecutive_anomaly_trips': 'trips', 'health_peer_count': 'trips',
    'health_peer_vehicle_count': 'vehicles', 'dtc_event_count': 'source events',
    'rapid_accel_event_count': 'source events', 'rapid_decel_event_count': 'source events',
    'speeding_event_count': 'source events', 'engine_overload_event_count': 'source events',
    **{f'{factor}_priority_pct': '%' for factor in FACTOR_NAMES},
}


def assign_owner(packet, problem_type='BENCHMARK_GAP'):
    """Route a question to a role; confidence describes evidence completeness only."""
    if problem_type == 'VEHICLE_HEALTH':
        return {'primary_owner': 'MAINTENANCE', 'supporting_roles': ['FLEET_MANAGER'],
                'handoff_reason': '車況殘差或來源 DTC 事件需核對保養與感測器紀錄。', 'owner_confidence': 'ROUTING_EVIDENCE_PRESENT'}
    if packet.get('benchmark_gap_l') is None or packet.get('benchmark_quality') in {None, 'LOW'} or packet.get('lever_status') == 'INSUFFICIENT_DATA':
        return {'primary_owner': 'FLEET_MANAGER', 'supporting_roles': [],
                'handoff_reason': '比較證據不足或偏弱，先補齊可比較行程與營運條件。', 'owner_confidence': 'ROUTING_EVIDENCE_LIMITED'}
    if packet.get('benchmark_gap_l', 0) <= 0:
        return {'primary_owner': 'FLEET_MANAGER', 'supporting_roles': [],
                'handoff_reason': '目前沒有正向燃油差距，持續觀測並核對營運條件。', 'owner_confidence': 'ROUTING_EVIDENCE_PRESENT'}
    levers = packet.get('improvement_levers', [])
    factor = levers[0]['factor'] if levers else None
    routing = {
        'idle_context': ('DISPATCHER', ['DRIVER'], '先核對停靠用途、PTO／設備需求與到站窗口。'),
        'rpm': ('DRIVER', ['FLEET_MANAGER'], '操作型態待核對；需兼顧安全、任務與車況。'),
        'engine_load': ('FLEET_MANAGER', ['DISPATCHER', 'MAINTENANCE'], '先核對實際載重、路段／坡度、作業需求與車況。'),
    }
    owner, roles, reason = routing.get(factor, ('FLEET_MANAGER', [], '目前沒有可排序的改善槓桿，先補證據。'))
    return {'primary_owner': owner, 'supporting_roles': roles, 'handoff_reason': reason,
            'owner_confidence': 'ROUTING_EVIDENCE_PRESENT' if factor else 'ROUTING_EVIDENCE_LIMITED'}


def decision_packet(trip, route_hotspot=None):
    t = dict(trip)
    def val(key): return json_safe(t.get(key))
    packet = {k: val(k) for k in ['trip_id', 'enabledCode', 'journeyCode', 'route_id', 'start_time', 'end_time',
        'data_quality_score', 'opportunity_status', 'lever_status', *EVIDENCE_UNITS]}
    packet.update(actual_fuel_l=val('trip_fuel_l'), route_hotspot=route_hotspot, evidence_mode=EVIDENCE_MODE)
    packet['vehicle_health_flag'] = bool(val('vehicle_health_flag') or False)
    packet['evidence'] = [dict(evidence_id='E_' + field, source_type='DERIVED', field=field,
                               value=packet[field], unit=unit) for field, unit in EVIDENCE_UNITS.items()]
    packet['improvement_levers'] = sorted([
        {'factor': factor, 'priority_pct': val(factor + '_priority_pct'), 'source_type': 'DERIVED',
         'evidence_id': 'E_' + factor + '_priority_pct'}
        for factor in FACTOR_NAMES if (val(factor + '_priority_pct') or 0) > 0], key=lambda item: -item['priority_pct'])
    packet['mock_context'] = {'source_type': 'MOCK', **{k: val(k) for k in MOCK_RULES}}
    packet['what_is_missing'] = ['競賽資料缺真實駕駛與任務識別；正式介接先核對 iTRAQ driverUid／tachographDriver', '真實載重', '交通與天氣', '停靠用途、PTO 與交付窗口', '維修履歷', 'Pilot 對照成效']
    packet['provenance'] = {'identifiers': 'RAW', 'primary_analysis': 'RAW / DERIVED only',
                             'operating_context': 'MOCK; excluded from primary evidence'}
    packet['disclaimer'] = DISCLAIMER
    packet.update(assign_owner(packet))
    packet.update(analysis_version=ANALYSIS_VERSION, source_contract_version=SOURCE_CONTRACT_VERSION,
                  event_reference_version=EVENT_REFERENCE_VERSION)
    return json_safe(packet)


def recommend(packet, persona):
    if persona not in PERSONAS:
        raise ValueError(f'Unknown persona: {persona}')
    known = packet.get('expected_fuel_l') is not None and packet.get('benchmark_gap_l') is not None
    levers = packet.get('improvement_levers', [])
    leading = levers[0]['factor'] if levers else None
    gap_positive = (packet.get('benchmark_gap_l') or 0) > 0
    summary = ('相較同儕仍有燃油差距；請先核對可比較性與實際營運條件。' if gap_positive else
               '本趟未觀測到正向同儕燃油差距；持續核對行為與營運條件。') if known else '目前資料不足以判斷；先補齊資料品質與可比較行程證據。'
    if packet.get('benchmark_quality') == 'LOW' and known:
        summary += '比較證據強度偏低，需審慎核對。'
    driver_actions = {
        'idle_context': '安全停妥且作業允許時，先確認現場作業與引擎運轉需求。',
        'rpm': '在安全與車況允許時核對轉速與換檔型態；不預設操作錯誤。',
        'engine_load': '請與車隊管理者核對實際載重、坡度與作業需求。',
        None: '記錄值得核對的操作與停留情境。'}
    actions = {
        'DRIVER': driver_actions[leading],
        'DISPATCHER': '核對停靠用途、作業需求、PTO／設備需求與到站窗口。',
        'FLEET_MANAGER': '依比較證據強度與燃油差距安排核對順序，指派跨角色負責人並追蹤可比較的後續 KPI。',
        'MAINTENANCE': HEALTH_ACTION if packet.get('vehicle_health_flag') else
            '請核對原始 DTC 事件、保養與感測器紀錄。' if (packet.get('dtc_event_count') or 0) > 0 else
            '目前缺少車況檢查觸發證據，請持續核對後續殘差與保養紀錄。',
    }
    if not known and persona != 'MAINTENANCE':
        actions[persona] = '先協助確認資料是否完整，再討論後續改善方向。'
    checks = {
        'DRIVER': ['停留是否由任務、PTO 或現場限制形成。'],
        'DISPATCHER': ['真實停靠用途與到站窗口。', '真實任務、載重與路況；Demo Context 仍為 MOCK。'],
        'FLEET_MANAGER': ['基準層級、支持趟數與比較證據強度。', 'Pilot 前後是否具備可比較條件。'],
        'MAINTENANCE': ['保養與感測器紀錄。', '實際任務與載重是否解釋持續殘差。'],
    }
    fields = ['actual_fuel_l', 'expected_fuel_l', 'benchmark_gap_l', 'benchmark_quality']
    if persona == 'MAINTENANCE':
        fields = ['vehicle_health_flag', 'vehicle_residual_ratio', 'consecutive_anomaly_trips', 'dtc_event_count']
    elif persona == 'DISPATCHER': fields += ['idle_minutes']
    if leading and persona != 'MAINTENANCE': fields += [leading + '_priority_pct']
    ids = [e['evidence_id'] for e in packet.get('evidence', []) if e['field'] in fields and e['value'] is not None]
    handoff = packet.get('primary_owner', 'FLEET_MANAGER')
    if persona == 'MAINTENANCE': handoff = 'MAINTENANCE'
    return {'headline': {'DRIVER': '下一趟的主要行動', 'DISPATCHER': '核對停留與任務安排',
                         'FLEET_MANAGER': '安排核對優先順序', 'MAINTENANCE': '車況證據核對'}[persona],
            'evidence_summary': summary, 'next_action': actions[persona], 'what_to_verify': checks[persona],
            'handoff_role': handoff, 'primary_owner': packet.get('primary_owner'),
            'supporting_roles': packet.get('supporting_roles', []), 'evidence_ids': ids, 'persona': persona,
            'mode': 'deterministic_template', 'disclaimer': DISCLAIMER, 'packet': packet}


def action_center(trips):
    """One accountable owner per trip problem; Maintenance never has a saving or gap allocation."""
    rows = []
    for _, t in trips.iterrows():
        packet = decision_packet(t)
        levers = packet['improvement_levers']
        if pd.notna(t.benchmark_gap_l) and t.benchmark_gap_l > 0:
            leading = levers[0]['factor'] if levers else None
            owner = packet['primary_owner']
            rows.append({'trip_id': t.trip_id, 'vehicle': t.enabledCode,
                'problem': FACTOR_NAMES[leading] + '優先核對' if leading else '燃油差距待核對', 'owner': owner,
                'primary_owner': owner, 'supporting_roles': packet['supporting_roles'],
                'handoff_reason': packet['handoff_reason'], 'owner_confidence': packet['owner_confidence'],
                'evidence': f'燃油差距 {t.benchmark_gap_l:.2f} L；{t.peer_trip_count} 趟／{t.peer_vehicle_count} 台其他車；證據 {t.benchmark_quality}',
                'benchmark_gap_l': t.benchmark_gap_l, 'benchmark_quality': t.benchmark_quality,
                'action': recommend(packet, owner)['next_action'], 'source': 'DERIVED；PRIMARY EVIDENCE MODE'})
        elif pd.isna(t.benchmark_gap_l):
            rows.append({'trip_id': t.trip_id, 'vehicle': t.enabledCode, 'problem': '比較證據不足',
                'owner': 'FLEET_MANAGER', 'primary_owner': 'FLEET_MANAGER', 'supporting_roles': [],
                'handoff_reason': packet['handoff_reason'], 'owner_confidence': 'ROUTING_EVIDENCE_LIMITED',
                'evidence': f'資料品質 {t.data_quality_score:.0f}；同儕 {t.peer_trip_count} 趟／{t.peer_vehicle_count} 台',
                'benchmark_gap_l': None, 'benchmark_quality': None,
                'action': '補齊品質與可比較行程證據，核對真實任務、載重及停留用途；暫不歸責駕駛。',
                'source': 'DERIVED；證據不足'})
        if t.vehicle_health_flag or t.dtc_event_count > 0:
            routing = assign_owner(packet, 'VEHICLE_HEALTH')
            rows.append({'trip_id': t.trip_id, 'vehicle': t.enabledCode, 'problem': '車況檢查訊號', 'owner': 'MAINTENANCE',
                **routing,
                'evidence': f'連續偏高殘差 {t.consecutive_anomaly_trips} 趟；DTC 來源事件 {t.dtc_event_count} 次',
                'benchmark_gap_l': None, 'benchmark_quality': None,
                'action': HEALTH_ACTION if t.vehicle_health_flag else '核對 DTC 與保養紀錄，安排必要檢查。',
                'source': 'DERIVED；未量化維修效益'})
    return pd.DataFrame(rows, columns=['trip_id', 'vehicle', 'problem', 'owner', 'primary_owner', 'supporting_roles',
                                       'handoff_reason', 'owner_confidence', 'evidence', 'benchmark_gap_l',
                                       'benchmark_quality', 'action', 'source'])
