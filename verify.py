"""Verify harness-router plugin."""
import sys
from pathlib import Path

_HERE = str(Path(__file__).resolve().parent)
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import harness_router as hr

errors = []

# Test 1: status
st = hr.status()
assert st["available_count"] >= 0, "status failed"
assert len(st["top_models"]) == 10, f"expected 10 top models, got {len(st['top_models'])}"
print(f"  ✓ status: {st['available_count']}/5 harnesses, {len(st['top_models'])} top models")

# Test 2: top model filtering
assert hr.is_top_model("deepseek-v4-flash"), "deepseek should be top"
assert hr.is_top_model("deepseek-v4-flash:free"), "alias should resolve"
assert not hr.is_top_model("weak-model-xyz"), "unknown should not be top"
filtered = hr.filter_top_models(["deepseek-v4-flash", "weak-model", "glm-5.3-free"])
assert len(filtered) == 2, f"expected 2, got {len(filtered)}"
print(f"  ✓ model filtering: {filtered}")

# Test 3: routing
r = hr.route("single-file-edit")
assert r is not None, "single-file-edit should route"
print(f"  ✓ route single-file-edit -> {r}")

r = hr.route("nonexistent-capability")
assert r is None, "unknown capability should return None"
print(f"  ✓ route unknown -> None")

# Test 4: task routing
tr = hr.route_task("fix a bug in the frontend")
assert tr["harness"] is not None, "task routing should find a harness"
print(f"  ✓ route_task 'fix frontend' -> {tr['harness']} ({tr['reason']})")

# Test 5: harness availability
avail = hr.available_harnesses()
print(f"  ✓ available harnesses: {avail}")

# Test 7: run generates command
res = hr.run("kilo", "test prompt", model="deepseek-v4-flash")
assert res.ok, "run should succeed"
assert "kilo run" in res.output, f"expected kilo run command, got: {res.output}"
print(f"  ✓ run generates command: {res.output}")

# Test 8: run rejects non-top model
res = hr.run("kilo", "test", model="weak-model")
assert not res.ok, "non-top model should be rejected"
print(f"  ✓ run rejects non-top model: {res.error}")

print("\nALL CHECKS PASSED")
