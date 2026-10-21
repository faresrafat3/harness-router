#!/usr/bin/env python3
"""Demo: harness router in action."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from harness_router import route, route_task, run, status, TOP_MODELS

print("=" * 60)
print("HARNESS ROUTER DEMO")
print("=" * 60)

# 1. Status
print("\n1. STATUS")
st = status()
print(f"   {st['available_count']}/5 harnesses available")
for name, info in st["harnesses"].items():
    mark = "✓" if info["available"] else "✗"
    print(f"   {mark} {name:<14} {info['version'] or 'not found'}")

# 2. Route by capability
print("\n2. ROUTE BY CAPABILITY")
for cap in ["single-file-edit", "multi-file-refactor", "model-sweep", "ui-frontend"]:
    h = route(cap)
    print(f"   {cap:<24} → {h}")

# 3. Route by task
print("\n3. ROUTE BY TASK")
tasks = [
    "fix the login bug",
    "refactor the auth module across 5 files",
    "sweep models to find the best output",
    "redesign the settings page UI",
    "run batch processing on the server",
]
for task in tasks:
    r = route_task(task)
    print(f"   \"{task}\"")
    print(f"     → {r['harness']} ({r['reason']})")

# 4. Generate commands
print("\n4. GENERATE COMMANDS")
for task in ["fix the login bug", "refactor auth module"]:
    r = route_task(task)
    res = run(r["harness"], task, model="deepseek-v4-flash")
    print(f"   {res.output}")

# 5. Model policy
print("\n5. TOP-10 MODELS (only these are allowed)")
for i, m in enumerate(TOP_MODELS, 1):
    print(f"   {i:>2}. {m}")

# 6. Rejected model
print("\n6. MODEL POLICY ENFORCEMENT")
res = run("kilo", "test", model="weak-model-xyz")
print(f"   run('kilo', 'test', model='weak-model-xyz')")
print(f"   → {res.error}")

print("\n" + "=" * 60)
print("ALL DEMOS PASSED")
print("=" * 60)
