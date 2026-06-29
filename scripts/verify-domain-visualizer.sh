#!/usr/bin/env bash
set -euo pipefail

# Domain Visualizer Verification Script
#
# Verifies the Protean Observatory Domain Visualizer (Epic 2.1) end-to-end
# against a running ShopStream stack. Tests the IR API endpoint, D3 graph
# transformation, aggregate topology, event flow DAG, process manager view,
# detail panel data, and UI page rendering.
#
# Prerequisites:
#   make docker-up && make setup-db
#   make api                    # terminal 1 — port 8000
#   make observatory            # terminal 2 — port 9000
#
# No engine processes are required — the Domain Visualizer derives
# everything from the live IR, not from runtime events.
#
# Usage:
#   ./scripts/verify-domain-visualizer.sh              # Full run: seed + verify
#   ./scripts/verify-domain-visualizer.sh --skip-seed  # Skip seeding
#   ./scripts/verify-domain-visualizer.sh --seed-only  # Seed data only

API_URL="${API_URL:-http://localhost:8000}"
OBS_URL="${OBS_URL:-http://localhost:9000}"
SKIP_SEED=false
SEED_ONLY=false

for arg in "$@"; do
    case $arg in
        --skip-seed) SKIP_SEED=true ;;
        --seed-only) SEED_ONLY=true ;;
        -h|--help)
            echo "Usage: $0 [--skip-seed] [--seed-only]"
            echo "  --skip-seed  Skip data seeding, reuse existing data"
            echo "  --seed-only  Seed data only, skip verification"
            exit 0
            ;;
    esac
done

# --- Counters ---
PASS=0
FAIL=0
FAILURES=()

pass() {
    PASS=$((PASS + 1))
    echo "  [PASS] $1"
}

fail() {
    FAIL=$((FAIL + 1))
    FAILURES+=("$1")
    echo "  [FAIL] $1"
}

check() {
    if [ "$1" -eq 0 ]; then
        pass "$2"
    else
        fail "$2"
    fi
}

section() {
    echo ""
    echo "==========================================="
    echo "  $1"
    echo "==========================================="
}

# --- Temp files ---
TMPDIR=$(mktemp -d)
trap 'rm -rf "$TMPDIR"' EXIT

# ============================================================
#  Preflight
# ============================================================
section "Preflight"

echo "  Checking API server at $API_URL..."
if ! curl -sf "$API_URL/health" > /dev/null 2>&1; then
    echo "  ERROR: API server not reachable at $API_URL"
    echo "  Start it with: make api"
    exit 1
fi
pass "API server reachable"

echo "  Checking Observatory at $OBS_URL..."
if ! curl -sf "$OBS_URL/" > /dev/null 2>&1; then
    echo "  ERROR: Observatory not reachable at $OBS_URL"
    echo "  Start it with: make observatory"
    exit 1
fi
pass "Observatory reachable"

# ============================================================
#  Phase 1: Seed minimal test data
# ============================================================
# The Domain Visualizer is IR-derived (static topology), so it doesn't
# strictly need runtime data. However, seeding a customer and product
# confirms the domains are properly initialized and gives the detail
# panel real element examples.
if [ "$SKIP_SEED" = false ]; then
    section "Phase 1: Seeding minimal test data"

    echo "  Creating a customer (Identity domain)..."
    CUST=$(curl -sf -X POST "$API_URL/customers" \
        -H "Content-Type: application/json" \
        -d '{"external_id":"dv-cust-001","email":"dv-alice@example.com","first_name":"Alice","last_name":"Visualizer"}' 2>/dev/null || echo "")
    if [ -n "$CUST" ]; then
        CUST_ID=$(echo "$CUST" | python3 -c "import json,sys; print(json.load(sys.stdin).get('customer_id',''))" 2>/dev/null || echo "")
        echo "  Customer: ${CUST_ID:-already exists or created}"
    else
        echo "  Customer: skipped (may already exist)"
    fi

    echo "  Creating a product (Catalogue domain)..."
    PROD=$(curl -sf -X POST "$API_URL/products" \
        -H "Content-Type: application/json" \
        -d '{"sku":"DV-TEST-001","title":"Visualizer Test Product","description":"For domain visualizer testing"}' 2>/dev/null || echo "")
    if [ -n "$PROD" ]; then
        PROD_ID=$(echo "$PROD" | python3 -c "import json,sys; print(json.load(sys.stdin).get('product_id',''))" 2>/dev/null || echo "")
        echo "  Product: ${PROD_ID:-already exists or created}"
    else
        echo "  Product: skipped (may already exist)"
    fi

    echo "  Seeding complete."
fi

if [ "$SEED_ONLY" = true ]; then
    echo ""
    echo "Seed-only mode. Exiting."
    exit 0
fi

# ============================================================
#  Phase 2: IR API Endpoint (/api/domain/ir)
# ============================================================

section "2.1 IR API endpoint — availability"
HTTP=$(curl -s -o "$TMPDIR/ir.json" -w "%{http_code}" "$OBS_URL/api/domain/ir")
[ "$HTTP" = "200" ]; check $? "GET /api/domain/ir returns 200 (got $HTTP)"

# --- 2.2 Top-level structure ---
section "2.2 IR response — top-level structure"
python3 -c "
import json, sys

with open('$TMPDIR/ir.json') as f:
    d = json.load(f)

required = ['nodes', 'links', 'clusters', 'flows', 'projections', 'stats', 'flow_graph']
missing = [k for k in required if k not in d]
checks = []
checks.append((not missing, 'All top-level keys present' + (f' (missing: {\",\".join(missing)})' if missing else '')))
checks.append((isinstance(d.get('nodes'), list), 'nodes is a list'))
checks.append((isinstance(d.get('links'), list), 'links is a list'))
checks.append((isinstance(d.get('clusters'), dict), 'clusters is a dict'))
checks.append((isinstance(d.get('flows'), dict), 'flows is a dict'))
checks.append((isinstance(d.get('projections'), dict), 'projections is a dict'))
checks.append((isinstance(d.get('stats'), dict), 'stats is a dict'))
checks.append((isinstance(d.get('flow_graph'), dict), 'flow_graph is a dict'))

for ok, msg in checks:
    tag = 'PASS' if ok else 'FAIL'
    print(f'  [{tag}] {msg}')
with open('$TMPDIR/structure_results', 'w') as f:
    f.write(f'{sum(1 for ok,_ in checks if ok)}\n{sum(1 for ok,_ in checks if not ok)}')
"
read -r SP SF < "$TMPDIR/structure_results"
PASS=$((PASS + SP))
FAIL=$((FAIL + SF))

# --- 2.3 Aggregate nodes ---
section "2.3 Aggregate nodes"
python3 -c "
import json

with open('$TMPDIR/ir.json') as f:
    d = json.load(f)

nodes = d.get('nodes', [])
checks = []
checks.append((len(nodes) > 0, f'At least one aggregate node ({len(nodes)} found)'))

# All nodes must have required fields
if nodes:
    required = ['id', 'name', 'type', 'fqn', 'stream_category', 'is_event_sourced', 'counts']
    for n in nodes:
        missing = [f for f in required if f not in n]
        if missing:
            checks.append((False, f'Node {n.get(\"name\",\"?\")} missing fields: {\",\".join(missing)}'))
            break
    else:
        checks.append((True, 'All nodes have required fields (id, name, type, fqn, stream_category, is_event_sourced, counts)'))

    # All nodes should be type=aggregate
    all_agg = all(n['type'] == 'aggregate' for n in nodes)
    checks.append((all_agg, 'All topology nodes are type=aggregate'))

    # Each node should have counts dict with at least one key
    has_counts = all(isinstance(n.get('counts'), dict) and len(n['counts']) > 0 for n in nodes)
    checks.append((has_counts, 'All nodes have non-empty counts'))

    # Print aggregate names for manual inspection
    names = [n['name'] for n in nodes]
    print(f'  Aggregates: {\", \".join(sorted(names))}')

    # Check for event-sourced flag correctness
    es_nodes = [n['name'] for n in nodes if n.get('is_event_sourced')]
    if es_nodes:
        checks.append((True, f'Event-sourced aggregates identified: {\", \".join(es_nodes)}'))

for ok, msg in checks:
    tag = 'PASS' if ok else 'FAIL'
    print(f'  [{tag}] {msg}')
with open('$TMPDIR/nodes_results', 'w') as f:
    f.write(f'{sum(1 for ok,_ in checks if ok)}\n{sum(1 for ok,_ in checks if not ok)}')
"
read -r NP NF < "$TMPDIR/nodes_results"
PASS=$((PASS + NP))
FAIL=$((FAIL + NF))

# --- 2.4 Cross-aggregate links ---
section "2.4 Cross-aggregate links"
python3 -c "
import json

with open('$TMPDIR/ir.json') as f:
    d = json.load(f)

links = d.get('links', [])
nodes = d.get('nodes', [])
node_ids = {n['id'] for n in nodes}

checks = []
# Links may be empty if the first domain has no cross-aggregate edges
checks.append((isinstance(links, list), f'links is a list ({len(links)} edges)'))

if links:
    required = ['source', 'target', 'type', 'label']
    for link in links:
        missing = [f for f in required if f not in link]
        if missing:
            checks.append((False, f'Link missing fields: {\",\".join(missing)}'))
            break
    else:
        checks.append((True, 'All links have required fields (source, target, type, label)'))

    # Link types must be 'event' or 'process_manager'
    valid_types = {'event', 'process_manager'}
    types_found = {l['type'] for l in links}
    bad_types = types_found - valid_types
    checks.append((not bad_types, f'Link types valid ({types_found})' + (f' invalid: {bad_types}' if bad_types else '')))

    # All link sources/targets must reference existing nodes
    dangling = [l for l in links if l['source'] not in node_ids or l['target'] not in node_ids]
    checks.append((not dangling, f'All link endpoints reference existing nodes' + (f' ({len(dangling)} dangling)' if dangling else '')))

    # Print edge summary
    for l in links:
        src_name = l['source'].split('.')[-1] if '.' in l['source'] else l['source']
        tgt_name = l['target'].split('.')[-1] if '.' in l['target'] else l['target']
        print(f'    {src_name} --[{l[\"type\"]}:{l[\"label\"]}]--> {tgt_name}')
else:
    print('  (No cross-aggregate links — single-aggregate domain or no cross-cluster handlers)')

for ok, msg in checks:
    tag = 'PASS' if ok else 'FAIL'
    print(f'  [{tag}] {msg}')
with open('$TMPDIR/links_results', 'w') as f:
    f.write(f'{sum(1 for ok,_ in checks if ok)}\n{sum(1 for ok,_ in checks if not ok)}')
"
read -r LP LF < "$TMPDIR/links_results"
PASS=$((PASS + LP))
FAIL=$((FAIL + LF))

# --- 2.5 Stats ---
section "2.5 Domain stats"
python3 -c "
import json

with open('$TMPDIR/ir.json') as f:
    d = json.load(f)

stats = d.get('stats', {})
checks = []

# Required stat keys
required = ['aggregates', 'projections', 'commands', 'command_handlers', 'events',
            'event_handlers', 'entities', 'value_objects']
missing = [k for k in required if k not in stats]
checks.append((not missing, 'All required stat keys present' + (f' (missing: {\",\".join(missing)})' if missing else '')))

# Aggregates count should match nodes count
nodes = d.get('nodes', [])
checks.append((stats.get('aggregates', 0) == len(nodes), f'stats.aggregates ({stats.get(\"aggregates\",0)}) matches node count ({len(nodes)})'))

# All values should be non-negative integers
all_ints = all(isinstance(v, int) and v >= 0 for v in stats.values())
checks.append((all_ints, 'All stat values are non-negative integers'))

# At least one command and one event should exist
checks.append((stats.get('commands', 0) > 0, f'commands > 0 ({stats.get(\"commands\",0)})'))
checks.append((stats.get('events', 0) > 0, f'events > 0 ({stats.get(\"events\",0)})'))

# Print stats for manual inspection
for k, v in sorted(stats.items()):
    print(f'    {k}: {v}')

for ok, msg in checks:
    tag = 'PASS' if ok else 'FAIL'
    print(f'  [{tag}] {msg}')
with open('$TMPDIR/stats_results', 'w') as f:
    f.write(f'{sum(1 for ok,_ in checks if ok)}\n{sum(1 for ok,_ in checks if not ok)}')
"
read -r STP STF < "$TMPDIR/stats_results"
PASS=$((PASS + STP))
FAIL=$((FAIL + STF))

# --- 2.6 Clusters (drill-down data) ---
section "2.6 Cluster data for detail panel"
python3 -c "
import json

with open('$TMPDIR/ir.json') as f:
    d = json.load(f)

clusters = d.get('clusters', {})
checks = []

checks.append((len(clusters) > 0, f'At least one cluster ({len(clusters)} found)'))

if clusters:
    # Pick the first cluster to validate structure
    first_key = list(clusters.keys())[0]
    cluster = clusters[first_key]

    # Cluster must have aggregate definition
    checks.append(('aggregate' in cluster, f'Cluster {first_key} has aggregate key'))

    agg = cluster.get('aggregate', {})
    checks.append(('name' in agg, 'Aggregate has name'))
    checks.append(('options' in agg, 'Aggregate has options'))

    # Cluster should have at least commands or events
    has_cmds = len(cluster.get('commands', {})) > 0
    has_evts = len(cluster.get('events', {})) > 0
    checks.append((has_cmds or has_evts, f'Cluster has commands ({len(cluster.get(\"commands\", {}))}) or events ({len(cluster.get(\"events\", {}))})'))

    # Check fields exist on aggregate
    fields = agg.get('fields', {})
    if fields:
        first_field = list(fields.values())[0]
        checks.append(('kind' in first_field, 'Aggregate fields have kind'))
        # Standard fields have 'type', associations have 'target'
        has_type_info = 'type' in first_field or 'target' in first_field
        checks.append((has_type_info, 'Aggregate fields have type or target'))
    else:
        checks.append((True, 'Aggregate fields accessible (may be empty)'))

    # Check commands have expected structure
    cmds = cluster.get('commands', {})
    if cmds:
        first_cmd = list(cmds.values())[0]
        checks.append(('name' in first_cmd, 'Command has name'))
        checks.append(('fields' in first_cmd, 'Command has fields'))

    # Check events have expected structure
    evts = cluster.get('events', {})
    if evts:
        first_evt = list(evts.values())[0]
        checks.append(('name' in first_evt, 'Event has name'))
        checks.append(('__type__' in first_evt, 'Event has __type__'))

    # Print cluster summary
    for ckey, cval in clusters.items():
        agg_name = cval.get('aggregate', {}).get('name', '?')
        n_cmds = len(cval.get('commands', {}))
        n_evts = len(cval.get('events', {}))
        n_ents = len(cval.get('entities', {}))
        n_vos = len(cval.get('value_objects', {}))
        n_chs = len(cval.get('command_handlers', {}))
        n_ehs = len(cval.get('event_handlers', {}))
        print(f'    {agg_name}: {n_cmds} cmds, {n_evts} evts, {n_ents} ents, {n_vos} VOs, {n_chs} cmd_h, {n_ehs} evt_h')

for ok, msg in checks:
    tag = 'PASS' if ok else 'FAIL'
    print(f'  [{tag}] {msg}')
with open('$TMPDIR/cluster_results', 'w') as f:
    f.write(f'{sum(1 for ok,_ in checks if ok)}\n{sum(1 for ok,_ in checks if not ok)}')
"
read -r CP CF < "$TMPDIR/cluster_results"
PASS=$((PASS + CP))
FAIL=$((FAIL + CF))

# ============================================================
#  Phase 3: Flow Graph (Event Flows View)
# ============================================================

section "3.1 Flow graph structure"
python3 -c "
import json

with open('$TMPDIR/ir.json') as f:
    d = json.load(f)

fg = d.get('flow_graph', {})
nodes = fg.get('nodes', [])
edges = fg.get('edges', [])
checks = []

checks.append(('nodes' in fg, 'flow_graph has nodes key'))
checks.append(('edges' in fg, 'flow_graph has edges key'))
checks.append((len(nodes) > 0, f'flow_graph has nodes ({len(nodes)} found)'))
checks.append((len(edges) > 0, f'flow_graph has edges ({len(edges)} found)'))

# Validate node types
valid_types = {'command', 'command_handler', 'aggregate', 'event', 'event_handler', 'process_manager', 'projector'}
types_found = {n['type'] for n in nodes}
bad_types = types_found - valid_types
checks.append((not bad_types, f'All flow node types valid: {sorted(types_found)}' + (f' (invalid: {bad_types})' if bad_types else '')))

# All flow nodes must have required fields
if nodes:
    required = ['id', 'name', 'type']
    for n in nodes:
        missing = [f for f in required if f not in n]
        if missing:
            checks.append((False, f'Flow node {n.get(\"name\",\"?\")} missing: {\",\".join(missing)}'))
            break
    else:
        checks.append((True, 'All flow nodes have required fields (id, name, type)'))

    # Aggregate/command/event/handler nodes should have cluster field
    clustered = [n for n in nodes if n['type'] in ('command', 'command_handler', 'aggregate', 'event', 'event_handler')]
    has_cluster = all('cluster' in n for n in clustered)
    checks.append((has_cluster, 'Cluster-bound nodes have cluster field'))

# Event nodes should have published flag
event_nodes = [n for n in nodes if n['type'] == 'event']
if event_nodes:
    has_published = all('published' in n for n in event_nodes)
    checks.append((has_published, 'Event nodes have published flag'))
    published = [n['name'] for n in event_nodes if n.get('published')]
    if published:
        print(f'    Published events: {\", \".join(published)}')

# Projector nodes should have projection field
proj_nodes = [n for n in nodes if n['type'] == 'projector']
if proj_nodes:
    has_proj = all('projection' in n for n in proj_nodes)
    checks.append((has_proj, 'Projector nodes have projection field'))

# Print type breakdown
from collections import Counter
type_counts = Counter(n['type'] for n in nodes)
for t in sorted(type_counts):
    print(f'    {t}: {type_counts[t]}')

for ok, msg in checks:
    tag = 'PASS' if ok else 'FAIL'
    print(f'  [{tag}] {msg}')
with open('$TMPDIR/flow_struct_results', 'w') as f:
    f.write(f'{sum(1 for ok,_ in checks if ok)}\n{sum(1 for ok,_ in checks if not ok)}')
"
read -r FP FF < "$TMPDIR/flow_struct_results"
PASS=$((PASS + FP))
FAIL=$((FAIL + FF))

# --- 3.2 Flow graph edges ---
section "3.2 Flow graph edges"
python3 -c "
import json

with open('$TMPDIR/ir.json') as f:
    d = json.load(f)

fg = d.get('flow_graph', {})
nodes = fg.get('nodes', [])
edges = fg.get('edges', [])
node_ids = {n['id'] for n in nodes}

checks = []

# All edges must have source, target, type
required = ['source', 'target', 'type']
for e in edges:
    missing = [f for f in required if f not in e]
    if missing:
        checks.append((False, f'Edge missing fields: {\",\".join(missing)}'))
        break
else:
    checks.append((True, 'All edges have required fields (source, target, type)'))

# Valid edge types
valid_types = {'command', 'handler_to_agg', 'raises', 'event', 'projection'}
types_found = {e['type'] for e in edges}
bad_types = types_found - valid_types
checks.append((not bad_types, f'Edge types valid: {sorted(types_found)}' + (f' (invalid: {bad_types})' if bad_types else '')))

# All edge endpoints should reference existing nodes
dangling_src = [e for e in edges if e['source'] not in node_ids]
dangling_tgt = [e for e in edges if e['target'] not in node_ids]
checks.append((not dangling_src, f'All edge sources exist' + (f' ({len(dangling_src)} dangling)' if dangling_src else '')))
checks.append((not dangling_tgt, f'All edge targets exist' + (f' ({len(dangling_tgt)} dangling)' if dangling_tgt else '')))

# Cross-aggregate edges should have cross_aggregate flag
cross_agg_edges = [e for e in edges if e['type'] == 'event' and 'cross_aggregate' in e]
if cross_agg_edges:
    checks.append((True, f'Cross-aggregate event edges marked ({len(cross_agg_edges)} found)'))

# Process manager edges should have start/end flags
pm_edges = [e for e in edges if 'start' in e or 'end' in e]
if pm_edges:
    checks.append((True, f'Process manager edges with start/end flags ({len(pm_edges)} found)'))

# Verify the flow is a DAG: command → cmd_handler → aggregate → event → consumers
# Check that at least one full chain exists
from collections import Counter
edge_types = Counter(e['type'] for e in edges)
has_cmd_chain = 'command' in edge_types and 'handler_to_agg' in edge_types and 'raises' in edge_types
checks.append((has_cmd_chain, f'Complete command chain exists (command → handler_to_agg → raises)'))

print(f'    Edge type breakdown:')
for t in sorted(edge_types):
    print(f'      {t}: {edge_types[t]}')

for ok, msg in checks:
    tag = 'PASS' if ok else 'FAIL'
    print(f'  [{tag}] {msg}')
with open('$TMPDIR/flow_edge_results', 'w') as f:
    f.write(f'{sum(1 for ok,_ in checks if ok)}\n{sum(1 for ok,_ in checks if not ok)}')
"
read -r FEP FEF < "$TMPDIR/flow_edge_results"
PASS=$((PASS + FEP))
FAIL=$((FAIL + FEF))

# ============================================================
#  Phase 4: Flows & Projections
# ============================================================

section "4.1 Process managers and subscribers"
python3 -c "
import json

with open('$TMPDIR/ir.json') as f:
    d = json.load(f)

flows = d.get('flows', {})
checks = []

# flows should have process_managers and subscribers keys
checks.append(('process_managers' in flows or 'subscribers' in flows,
    f'flows has process_managers or subscribers'))

pms = flows.get('process_managers', {})
subs = flows.get('subscribers', {})
print(f'    Process managers: {len(pms)}')
print(f'    Subscribers: {len(subs)}')

# Validate PM structure if present
if pms:
    first_pm = list(pms.values())[0]
    checks.append(('name' in first_pm, 'Process manager has name'))
    checks.append(('handlers' in first_pm, 'Process manager has handlers'))
    for pm_key, pm in pms.items():
        pm_name = pm.get('name', pm_key)
        n_handlers = len(pm.get('handlers', {}))
        print(f'      PM: {pm_name} ({n_handlers} handlers)')

# Validate subscriber structure if present
if subs:
    first_sub = list(subs.values())[0]
    checks.append(('name' in first_sub, 'Subscriber has name'))
    for sub_key, sub in subs.items():
        sub_name = sub.get('name', sub_key)
        print(f'      Subscriber: {sub_name}')

for ok, msg in checks:
    tag = 'PASS' if ok else 'FAIL'
    print(f'  [{tag}] {msg}')
with open('$TMPDIR/flows_results', 'w') as f:
    f.write(f'{sum(1 for ok,_ in checks if ok)}\n{sum(1 for ok,_ in checks if not ok)}')
"
read -r FLP FLF < "$TMPDIR/flows_results"
PASS=$((PASS + FLP))
FAIL=$((FAIL + FLF))

# --- 4.2 Projections ---
section "4.2 Projections"
python3 -c "
import json

with open('$TMPDIR/ir.json') as f:
    d = json.load(f)

projections = d.get('projections', {})
checks = []

print(f'    Projections: {len(projections)}')

if projections:
    # Each projection should have projectors
    for proj_key, proj in projections.items():
        projectors = proj.get('projectors', {})
        proj_name = proj_key.split('.')[-1] if '.' in proj_key else proj_key
        print(f'      {proj_name}: {len(projectors)} projector(s)')
        checks.append((len(projectors) > 0, f'Projection {proj_name} has projectors'))

        # Projectors should have handlers
        for ptor_key, ptor in projectors.items():
            handlers = ptor.get('handlers', {})
            checks.append((len(handlers) > 0, f'Projector {ptor.get(\"name\", ptor_key)} has handlers'))

for ok, msg in checks:
    tag = 'PASS' if ok else 'FAIL'
    print(f'  [{tag}] {msg}')
with open('$TMPDIR/proj_results', 'w') as f:
    f.write(f'{sum(1 for ok,_ in checks if ok)}\n{sum(1 for ok,_ in checks if not ok)}')
"
read -r PRP PRF < "$TMPDIR/proj_results"
PASS=$((PASS + PRP))
FAIL=$((FAIL + PRF))

# ============================================================
#  Phase 5: Consistency Checks
# ============================================================

section "5.1 Cross-referential integrity"
python3 -c "
import json

with open('$TMPDIR/ir.json') as f:
    d = json.load(f)

nodes = d.get('nodes', [])
clusters = d.get('clusters', {})
stats = d.get('stats', {})
fg = d.get('flow_graph', {})

checks = []

# nodes count == clusters count == stats.aggregates
checks.append((len(nodes) == len(clusters),
    f'nodes count ({len(nodes)}) == clusters count ({len(clusters)})'))
checks.append((len(nodes) == stats.get('aggregates', -1),
    f'nodes count ({len(nodes)}) == stats.aggregates ({stats.get(\"aggregates\")})'))

# Every node ID should be a cluster key
node_ids = {n['id'] for n in nodes}
cluster_keys = set(clusters.keys())
checks.append((node_ids == cluster_keys,
    f'Node IDs match cluster keys' + (f' (diff: {node_ids.symmetric_difference(cluster_keys)})' if node_ids != cluster_keys else '')))

# Sum of per-cluster command counts should equal stats.commands
total_cmds = sum(len(c.get('commands', {})) for c in clusters.values())
checks.append((total_cmds == stats.get('commands', -1),
    f'Sum of cluster commands ({total_cmds}) == stats.commands ({stats.get(\"commands\")})'))

# Sum of per-cluster event counts should equal stats.events
total_evts = sum(len(c.get('events', {})) for c in clusters.values())
checks.append((total_evts == stats.get('events', -1),
    f'Sum of cluster events ({total_evts}) == stats.events ({stats.get(\"events\")})'))

# Flow graph aggregate nodes should match topology nodes
fg_agg_ids = {n['id'] for n in fg.get('nodes', []) if n['type'] == 'aggregate'}
checks.append((fg_agg_ids == node_ids,
    f'Flow graph aggregates match topology nodes' + (f' (diff: {fg_agg_ids.symmetric_difference(node_ids)})' if fg_agg_ids != node_ids else '')))

for ok, msg in checks:
    tag = 'PASS' if ok else 'FAIL'
    print(f'  [{tag}] {msg}')
with open('$TMPDIR/integrity_results', 'w') as f:
    f.write(f'{sum(1 for ok,_ in checks if ok)}\n{sum(1 for ok,_ in checks if not ok)}')
"
read -r IP IF < "$TMPDIR/integrity_results"
PASS=$((PASS + IP))
FAIL=$((FAIL + IF))

# ============================================================
#  Phase 6: UI Page Smoke Checks
# ============================================================

section "6.1 Domain page loads"
HTTP=$(curl -s -o "$TMPDIR/domain_page.html" -w "%{http_code}" "$OBS_URL/domain")
[ "$HTTP" = "200" ]; check $? "GET /domain returns 200 (got $HTTP)"

# Check the page contains expected elements
python3 -c "
import sys

with open('$TMPDIR/domain_page.html') as f:
    html = f.read()

checks = []
# Page title / heading
checks.append(('Domain' in html, 'Page contains \"Domain\" text'))

# Tab structure
checks.append(('data-tab=\"topology\"' in html or 'topology' in html.lower(), 'Topology tab present'))
checks.append(('data-tab=\"event-flows\"' in html or 'event-flows' in html.lower(), 'Event Flows tab present'))
checks.append(('data-tab=\"process-managers\"' in html or 'process-managers' in html.lower(), 'Process Managers tab present'))

# D3 container elements
checks.append(('dv-topology-container' in html, 'Topology container element present'))
checks.append(('dv-flows-container' in html, 'Flows container element present'))
checks.append(('dv-pm-container' in html, 'Process Managers container element present'))

# Detail panel
checks.append(('dv-detail-panel' in html, 'Detail panel element present'))

# Stats section
checks.append(('dv-stat-aggregates' in html, 'Aggregates stat element present'))
checks.append(('dv-stat-commands' in html, 'Commands stat element present'))

for ok, msg in checks:
    tag = 'PASS' if ok else 'FAIL'
    print(f'  [{tag}] {msg}')
with open('$TMPDIR/page_results', 'w') as f:
    f.write(f'{sum(1 for ok,_ in checks if ok)}\n{sum(1 for ok,_ in checks if not ok)}')
"
read -r PP PF < "$TMPDIR/page_results"
PASS=$((PASS + PP))
FAIL=$((FAIL + PF))

# --- 6.2 Static JS assets ---
section "6.2 JavaScript modules load"
for JS_FILE in domain-topology.js domain-flows.js domain-detail.js domain.js; do
    HTTP=$(curl -s -o /dev/null -w "%{http_code}" "$OBS_URL/static/js/$JS_FILE")
    [ "$HTTP" = "200" ]; check $? "$JS_FILE loads (HTTP $HTTP)"
done

# --- 6.3 D3 library ---
section "6.3 D3 library available"
# D3 is vendored under /static/vendor/
HTTP=$(curl -s -o /dev/null -w "%{http_code}" "$OBS_URL/static/vendor/d3.v7.min.js")
[ "$HTTP" = "200" ]; check $? "D3 v7 library loads (HTTP $HTTP)"

# --- 6.4 Sidebar navigation ---
section "6.4 Sidebar navigation"
# Fetch the main page and check the sidebar has a Domain link
curl -sf "$OBS_URL/" > "$TMPDIR/main_page.html"
python3 -c "
with open('$TMPDIR/main_page.html') as f:
    html = f.read()
# The sidebar should have a link to /domain
ok = '/domain' in html
tag = 'PASS' if ok else 'FAIL'
print(f'  [{tag}] Sidebar has /domain navigation link')
with open('$TMPDIR/sidebar_ok', 'w') as f:
    f.write('1' if ok else '0')
"
SIDEBAR_OK=$(cat "$TMPDIR/sidebar_ok")
if [ "$SIDEBAR_OK" = "1" ]; then PASS=$((PASS + 1)); else FAIL=$((FAIL + 1)); FAILURES+=("sidebar /domain link"); fi

# ============================================================
#  Phase 7: Edge Cases
# ============================================================

section "7.1 IR API caching"
# Two consecutive calls should return identical content (cached at startup)
curl -sf "$OBS_URL/api/domain/ir" > "$TMPDIR/ir_call2.json"
SAME=$(python3 -c "
import json
with open('$TMPDIR/ir.json') as f: d1 = json.load(f)
with open('$TMPDIR/ir_call2.json') as f: d2 = json.load(f)
print(1 if d1 == d2 else 0)
")
[ "$SAME" = "1" ]; check $? "IR response is deterministic (cached)"

# ============================================================
#  Summary
# ============================================================
section "RESULTS"
TOTAL=$((PASS + FAIL))
echo ""
echo "  Passed: $PASS / $TOTAL"
echo "  Failed: $FAIL / $TOTAL"

if [ "$FAIL" -gt 0 ]; then
    echo ""
    echo "  Failures:"
    for f in "${FAILURES[@]}"; do
        echo "    - $f"
    done
fi

echo ""
echo "==========================================="
echo "  Manual Verification URLs"
echo "==========================================="
echo ""
echo "  --- Domain Visualizer (Epic 2.1) ---"
echo ""
echo "  Domain overview page:     $OBS_URL/domain"
echo ""
echo "  Topology Tab:"
echo "    - Force-directed graph with aggregate nodes"
echo "    - Click any aggregate node → detail panel slides in from right"
echo "    - Cross-aggregate edges shown as solid (event) or dashed (process_manager) lines"
echo "    - Zoom/pan with mouse wheel and drag"
echo "    - Mini-map in corner for orientation"
echo ""
echo "  Event Flows Tab:"
echo "    - Left-to-right DAG: command → handler → aggregate → event → consumers"
echo "    - Filter checkboxes to show/hide node types"
echo "    - Published events highlighted differently"
echo "    - Cross-aggregate handler edges visible"
echo "    - Projector nodes show which projection they feed"
echo ""
echo "  Process Managers Tab:"
echo "    - State machine visualization for each PM"
echo "    - Event triggers and state transitions shown"
echo "    - Saga start/end markers on edges"
echo ""
echo "  Detail Panel (click any aggregate in Topology):"
echo "    - Aggregate fields with types"
echo "    - Entity and Value Object listings"
echo "    - Command definitions with fields"
echo "    - Event definitions with published flag"
echo "    - Handler listings"
echo "    - Invariant definitions"
echo ""
echo "  Stats Summary:"
echo "    - Top cards show aggregate, command, event, entity, VO counts"
echo "    - Cross-check with \`protean ir --domain <domain>\` output"
echo ""
echo "  IR API (raw data):"
echo "    curl -s $OBS_URL/api/domain/ir | python3 -m json.tool | less"
echo ""
echo "  Quick checks to try manually:"
echo "    1. Switch between all three tabs — each should render its own D3 graph"
echo "    2. Click an aggregate in Topology → verify detail panel content matches domain code"
echo "    3. In Event Flows, toggle filter checkboxes → nodes should hide/show"
echo "    4. Resize browser window → graphs should adapt"
echo "    5. Toggle dark/light theme → graphs should remain readable"
echo "    6. Press '?' to see keyboard shortcuts"
echo ""

if [ "$FAIL" -gt 0 ]; then
    exit 1
fi
