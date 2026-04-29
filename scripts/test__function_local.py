import requests
import json
 
BASE_URL = "http://localhost:7071/api"
 
print("Testing local Azure Function...\n")
 
# ── Health check ──────────────────────────────────────────────────────────────
r = requests.get(f"{BASE_URL}/health", timeout=10)
print(f"[health] Status: {r.status_code}")
health = r.json()
print(f"  model_loaded : {health.get('model_loaded')}")
print(f"  data_loaded  : {health.get('data_loaded')}")
print()
 
# ── Forecast endpoint ─────────────────────────────────────────────────────────
r2 = requests.get(f"{BASE_URL}/forecast?horizon=3", timeout=30)
print(f"[forecast] Status: {r2.status_code}")
data = r2.json()
 
# Check all required keys
required_keys = [
    "status", "dominant_signal", "intensity",
    "glut_score", "shortage_score", "action_text",
    "reason", "confidence_days", "price_change_pct",
    "ci_width_pct", "forecast_dates", "forecast_values",
    "ci_lower", "ci_upper", "current_price",
]
missing = [k for k in required_keys if k not in data]
if missing:
    print(f"  ⚠ MISSING KEYS: {missing}")
else:
    print("  ✓ All required keys present")
 
# Value sanity checks
assert data["status"] == "ok",                       "status must be ok"
assert data["dominant_signal"] in ["GLUT","SHORTAGE","NEUTRAL"], "invalid signal"
assert data["intensity"] in ["HIGH","MEDIUM","LOW"],  "invalid intensity"
assert 0 <= data["glut_score"] <= 100,                "glut_score out of range"
assert 0 <= data["shortage_score"] <= 100,            "shortage_score out of range"
assert len(data["forecast_values"]) == 3,             "expected 3 forecast values"
assert data["current_price"] > 5000,                  "current_price seems wrong"
 
print("  ✓ All value assertions passed")
print()
print("Response summary:")
print(f"  Signal        : {data['dominant_signal']} — {data['intensity']}")
print(f"  Glut / Short  : {data['glut_score']} / {data['shortage_score']}")
print(f"  Current price : Rp {data['current_price']:,}")
print(f"  Price change  : {data['price_change_pct']:+.1f}%")
print(f"  CI width      : ±{data['ci_width_pct']:.0f}%")
print()
print(f"  Reason        : {data['reason']}")
print()
print("Action text:")
for line in data["action_text"].split("→"):
    if line.strip():
        print(f"  → {line.strip()}")
 
print("\n✓ Local function test passed — safe to deploy to Azure")