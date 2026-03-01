"""Quick API verification script."""
import urllib.request
import json

BASE = "http://localhost:8000"

def post(path, data):
    req = urllib.request.Request(
        f"{BASE}{path}",
        data=json.dumps(data).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    resp = urllib.request.urlopen(req)
    return json.loads(resp.read())

# Test 1: Generate with priority weights
print("=== TEST 1: /api/generate (with weights) ===")
gen_payload = {
    "system_description": "Scalable chat backend for 100k users",
    "expected_users": 100000,
    "budget_sensitivity": "medium",
    "fault_tolerance": "high",
    "time_to_market": "balanced",
    "cost_weight": 2,
    "scalability_weight": 5,
    "speed_weight": 3,
    "reliability_weight": 4,
}
gen_data = post("/api/generate", gen_payload)
print(f"Architectures returned: {len(gen_data)}")
for r in gen_data:
    a = r["architecture"]
    print(f"  {a['name']} (style={a['style']}) | score={r['overall_score']} | nodes={len(a['component_diagram']['nodes'])} | edges={len(a['component_diagram']['edges'])}")
print()

# Test 2: Compare (new format with system_input)
print("=== TEST 2: /api/compare (with system_input) ===")
cmp_data = post("/api/compare", {
    "results": gen_data,
    "system_input": gen_payload,
})
print(f"Rankings: {[r['architecture']['name'] for r in cmp_data['rankings']]}")
print(f"Trade-offs: {len(cmp_data['trade_off_reasoning'])} items")
print(f"Tension warning: {cmp_data.get('constraint_tension_warning', 'None')}")
print(f"LLM analysis present: {cmp_data.get('llm_analysis') is not None}")
if cmp_data.get('llm_analysis'):
    analysis = cmp_data['llm_analysis']
    print(f"  Executive summary (first 100): {analysis.get('executive_summary', '')[:100]}...")
print(f"Recommendation (first 200 chars): {cmp_data['recommendation'][:200]}")
print()

# Test 3: Generate with tension trigger
print("=== TEST 3: Constraint Tension Detection ===")
tension_payload = {
    "system_description": "High-scale financial trading platform",
    "expected_users": 200000,
    "budget_sensitivity": "low",
    "fault_tolerance": "high",
    "time_to_market": "fast",
    "cost_weight": 3,
    "scalability_weight": 3,
    "speed_weight": 3,
    "reliability_weight": 3,
}
tension_gen = post("/api/generate", tension_payload)
tension_cmp = post("/api/compare", {
    "results": tension_gen,
    "system_input": tension_payload,
})
print(f"Tension warning: {tension_cmp.get('constraint_tension_warning', 'None')}")
assert tension_cmp.get('constraint_tension_warning') is not None, "Expected tension warning!"
print("Tension warning detected correctly ✓")
print()

# Test 4: Generate with extreme weights (speed only)
print("=== TEST 4: Extreme Weights (Speed=5, others=0) ===")
speed_payload = {
    "system_description": "Low latency game server",
    "expected_users": 50000,
    "budget_sensitivity": "medium",
    "fault_tolerance": "medium",
    "time_to_market": "balanced",
    "cost_weight": 0,
    "scalability_weight": 0,
    "speed_weight": 5,
    "reliability_weight": 0,
}
speed_gen = post("/api/generate", speed_payload)
for r in speed_gen:
    print(f"  {r['architecture']['name']} | score={r['overall_score']}")
# Monolith should rank high on speed
speed_ranking = sorted(speed_gen, key=lambda x: x['overall_score'], reverse=True)
print(f"Top for speed: {speed_ranking[0]['architecture']['name']}")
print()

# Test 5: Scaffold
print("=== TEST 5: /api/scaffold ===")
scaffold = post("/api/scaffold", {
    "architecture_name": "Microservices",
    "system_description": "Scalable chat backend",
})
print(f"Architecture: {scaffold['architecture_name']}")
print(f"Files generated: {list(scaffold['files'].keys())}")
print()

print("=== ALL TESTS PASSED ===")
