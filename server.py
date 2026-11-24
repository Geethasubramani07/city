"""Smart City Traffic Dashboard - Python/Flask backend.
Simulates 12 junctions and streams live snapshots to the existing browser UI.
"""
from flask import Flask, Response, jsonify, request, send_from_directory
from datetime import datetime
from zoneinfo import ZoneInfo
from threading import Thread, Lock, Condition
from collections import deque
import os, time, math, random, json

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PUBLIC_DIR = os.path.join(BASE_DIR, 'public')
PORT = int(os.environ.get('PORT', 3000))
TICK_SECONDS = 2
HISTORY_LEN = 120
app = Flask(__name__, static_folder=None)

NAMES = ['Hebbal', 'Yeshwanthpur', 'KR Puram', 'Whitefield', 'Malleshwaram', 'MG Road',
         'Indiranagar', 'Marathahalli', 'Jayanagar', 'Koramangala', 'Silk Board', 'Electronic City']
WEIGHTS = [0.85, 0.7, 0.9, 0.8, 0.6, 1.0, 0.85, 0.95, 0.6, 0.9, 1.0, 0.75]
COLS = 4
nodes = []
for i, name in enumerate(NAMES):
    nodes.append({'id': f'J{i+1:02d}', 'name': name,
                  'x': 14 + (i % COLS) * 24 + (2 if i % 3 == 1 else -1),
                  'y': 12 + (i // COLS) * 23 + (2 if i % 2 else -2), 'weight': WEIGHTS[i]})
edges = []
for i, node in enumerate(nodes):
    col = i % COLS
    if col < COLS - 1: edges.append([node['id'], nodes[i+1]['id']])
    if i + COLS < len(nodes): edges.append([node['id'], nodes[i+COLS]['id']])
edges += [[nodes[1]['id'], nodes[6]['id']], [nodes[5]['id'], nodes[10]['id']]]

state = {n['id']: {'c': 30.0, 'signal': {'phase': random.choice(['NS', 'EW']), 'remaining': random.randint(10, 29)}} for n in nodes}
incidents, incident_seq, mode = [], 1, 'auto'
history = deque(maxlen=HISTORY_LEN)
lock = Lock()
condition = Condition(lock)
INCIDENT_TYPES = ['Accident', 'Road work', 'Vehicle breakdown', 'Waterlogging', 'Signal failure']


def ist_hour():
    now = datetime.now(ZoneInfo('Asia/Kolkata'))
    return now.hour + now.minute / 60


def rush_factor():
    if mode == 'rush': return 1.0
    if mode == 'night': return 0.12
    h = ist_hour()
    gaussian = lambda mu, sigma: math.exp(-((h-mu)**2) / (2*sigma*sigma))
    return 0.15 + 0.8 * max(gaussian(9, 1.4), gaussian(18.5, 1.8)) + 0.12 * gaussian(13, 1.5)


def simulate_tick():
    global incidents, incident_seq
    rf = rush_factor()
    for incident in incidents: incident['ticksLeft'] -= 1
    incidents = [i for i in incidents if i['ticksLeft'] > 0]
    if len(incidents) < 4 and random.random() < 0.035 + 0.03 * rf:
        node = random.choice(nodes)
        incidents.append({'id': incident_seq, 'nodeId': node['id'], 'node': node['name'],
                          'type': random.choice(INCIDENT_TYPES), 'severity': random.randint(1, 3),
                          'startedAt': int(time.time()*1000), 'ticksLeft': random.randint(20, 59)})
        incident_seq += 1
    for node in nodes:
        s = state[node['id']]
        boost = sum(i['severity'] * 12 for i in incidents if i['nodeId'] == node['id'])
        target = min(100, 100 * rf * node['weight'] * (0.88 + random.random()*0.24) + boost)
        s['c'] = max(2, min(100, s['c'] + (target-s['c'])*0.25))
        s['signal']['remaining'] -= TICK_SECONDS
        if s['signal']['remaining'] <= 0:
            s['signal']['phase'] = 'EW' if s['signal']['phase'] == 'NS' else 'NS'
            s['signal']['remaining'] = 20 + round((s['c']/100)*25)


def make_snapshot():
    listing = []
    for node in nodes:
        s = state[node['id']]
        c = round(s['c'])
        listing.append({'id': node['id'], 'congestion': c,
                        'speed': round(60*(1-0.85*(c/100))), 'vehicles': round(c*3.2+12),
                        'signal': {'phase': s['signal']['phase'], 'remaining': max(0, round(s['signal']['remaining']))}})
    worst = max(listing, key=lambda item: item['congestion'])
    return {'ts': int(time.time()*1000), 'mode': mode, 'nodes': listing,
            'kpis': {'avgSpeed': round(sum(x['speed'] for x in listing)/len(listing)),
                     'congestion': round(sum(x['congestion'] for x in listing)/len(listing)),
                     'vehicles': sum(x['vehicles'] for x in listing), 'activeIncidents': len(incidents),
                     'worst': {'id': worst['id'], 'name': next(n['name'] for n in nodes if n['id']==worst['id']), 'congestion': worst['congestion']}},
            'incidents': [{k:v for k,v in i.items() if k != 'ticksLeft'} for i in incidents]}


def simulation_loop():
    while True:
        time.sleep(TICK_SECONDS)
        with condition:
            simulate_tick()
            snap = make_snapshot()
            history.append({'t': snap['ts'], 'speed': snap['kpis']['avgSpeed'],
                            'congestion': snap['kpis']['congestion'], 'vehicles': snap['kpis']['vehicles']})
            condition.notify_all()

# Warm up chart history, as in the original Node.js project.
with lock:
    for i in range(60):
        simulate_tick()
        snap = make_snapshot()
        snap['ts'] = int(time.time()*1000) - (60-i)*TICK_SECONDS*1000
        history.append({'t': snap['ts'], 'speed': snap['kpis']['avgSpeed'],
                        'congestion': snap['kpis']['congestion'], 'vehicles': snap['kpis']['vehicles']})
Thread(target=simulation_loop, daemon=True).start()

@app.get('/')
def index(): return send_from_directory(PUBLIC_DIR, 'index.html')

@app.get('/<path:filename>')
def static_files(filename): return send_from_directory(PUBLIC_DIR, filename)

@app.get('/health')
def health(): return jsonify(status='ok')

@app.get('/api/network')
def network():
    return jsonify(nodes=[{k:v for k,v in n.items() if k != 'weight'} for n in nodes], edges=edges)

@app.get('/api/snapshot')
def snapshot():
    with lock: return jsonify(make_snapshot())

@app.get('/api/history')
def get_history():
    with lock: return jsonify(list(history))

@app.post('/api/mode')
def set_mode():
    global mode
    data = request.get_json(silent=True) or {}
    selected = data.get('mode')
    if selected not in ('auto', 'rush', 'night'):
        return jsonify(error='mode must be auto|rush|night'), 400
    with lock: mode = selected
    return jsonify(mode=mode)

@app.get('/api/stream')
def stream():
    def generate():
        last_sent = 0
        while True:
            with condition:
                condition.wait(timeout=25)
                snap = make_snapshot()
                current = snap['ts']
            if current != last_sent:
                yield f"data: {json.dumps(snap)}\n\n"
                last_sent = current
            else:
                yield ': ping\n\n'
    return Response(generate(), mimetype='text/event-stream', headers={
        'Cache-Control': 'no-cache, no-transform', 'X-Accel-Buffering': 'no'})

if __name__ == '__main__':
    print(f'Traffic dashboard running on http://localhost:{PORT}')
    app.run(host='0.0.0.0', port=PORT, threaded=True, use_reloader=False)
