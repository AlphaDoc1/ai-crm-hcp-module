"""
integration_test.py - Stage 6: Full End-to-End Integration Test
Writes results to integration_results.txt so output is never lost.
Run: .\\venv\\Scripts\\python integration_test.py
"""
import os, sys, json, httpx

# Write to file AND stdout (avoids buffering/encoding issues on Windows)
OUT = open("integration_results.txt", "w", encoding="utf-8")

def emit(msg=""):
    print(msg, flush=True)
    OUT.write(msg + "\n")
    OUT.flush()

BASE = "http://localhost:8000"
PASS = 0
FAIL = 0
new_id = None

def ok(msg):
    global PASS; PASS += 1
    emit(f"  [PASS] {msg}")

def fail(msg):
    global FAIL; FAIL += 1
    emit(f"  [FAIL] {msg}")

def section(title):
    emit(f"\n{'='*60}")
    emit(f"  {title}")
    emit(f"{'='*60}")


section("INTEGRATION TEST - AI-CRM HCP Module (Stage 6)")
emit(f"Backend: {BASE}")

# ── 1: Health ─────────────────────────────────────────────────────────────────
section("1. Health Check")
try:
    r = httpx.get(f"{BASE}/health", timeout=10)
    d = r.json()
    if r.status_code == 200 and d.get("status") == "ok" and d.get("database") == "connected":
        ok(f"GET /health -> status=ok, database=connected")
    else:
        fail(f"GET /health: {d}")
except Exception as e:
    fail(f"GET /health error: {e}")

# ── 2: HCP search REST ────────────────────────────────────────────────────────
section("2. HCP Search REST")
try:
    r = httpx.get(f"{BASE}/api/hcps/search?q=Dr.", timeout=10)
    hcps = r.json()
    if r.status_code == 200 and len(hcps) >= 5:
        ok(f"GET /api/hcps/search -> {len(hcps)} HCPs found")
        for h in hcps[:3]:
            emit(f"     - {h['name']} | {h.get('specialty')} | {h.get('hospital')}")
    else:
        fail(f"Expected >=5 HCPs, got {len(hcps)}: status={r.status_code}")
except Exception as e:
    fail(f"HCP search error: {e}")

# ── 3: POST interaction ───────────────────────────────────────────────────────
section("3. POST /api/interactions (Form Submit)")
try:
    payload = {
        "hcp_id": 1,
        "interaction_type": "Meeting",
        "date": "2026-07-08",
        "time": "14:30",
        "attendees": "Stage-6 Tester",
        "topics_discussed": "Reviewed OncoBoost BOOST-301 Phase III data. 34% PFS improvement. Dr. Sharma asked about protocol detail.",
        "materials_shared": [{"name": "OncoBoost Phase III Summary", "type": "Clinical Brochure"}],
        "samples_distributed": [{"drug": "OncoBoost 150mg", "quantity": 5}],
        "sentiment": "positive",
        "outcomes": "Dr. agreed to enroll 2 NSCLC patients",
        "follow_up_actions": "Send full trial PDF by Friday"
    }
    r = httpx.post(f"{BASE}/api/interactions", json=payload, timeout=15)
    created = r.json()
    new_id = created.get("id")
    if r.status_code == 201 and new_id:
        ok(f"POST /api/interactions -> id={new_id}, hcp={created.get('hcp_name')}, sentiment={created.get('sentiment')}")
    else:
        fail(f"POST: status={r.status_code} | {json.dumps(created)[:200]}")
except Exception as e:
    fail(f"POST error: {e}")

# ── 4: GET interactions list ──────────────────────────────────────────────────
section("4. GET /api/interactions (list)")
try:
    r = httpx.get(f"{BASE}/api/interactions?limit=5", timeout=10)
    d = r.json()
    total = d.get("total", 0)
    items = d.get("interactions", [])
    if r.status_code == 200 and total >= 1:
        ok(f"GET /api/interactions -> total={total}, returned {len(items)} items")
    else:
        fail(f"GET interactions: status={r.status_code}, total={total}")
except Exception as e:
    fail(f"GET interactions error: {e}")

# ── 5: PUT interaction (edit) ─────────────────────────────────────────────────
section("5. PUT /api/interactions/{id} (Edit)")
if new_id:
    try:
        r = httpx.put(
            f"{BASE}/api/interactions/{new_id}",
            json={"outcomes": "UPDATED: Dr. agreed to enroll 3 patients", "sentiment": "positive"},
            timeout=10
        )
        updated = r.json()
        if r.status_code == 200 and "UPDATED" in (updated.get("outcomes") or ""):
            ok(f"PUT /api/interactions/{new_id} -> outcomes updated successfully")
        else:
            fail(f"PUT: status={r.status_code}")
    except Exception as e:
        fail(f"PUT error: {e}")
else:
    fail("Skipped PUT - no new_id from step 3")

# ── 6: GET follow-ups ─────────────────────────────────────────────────────────
section("6. GET /api/interactions/1/follow-ups")
try:
    r = httpx.get(f"{BASE}/api/interactions/1/follow-ups", timeout=10)
    fups = r.json()
    if r.status_code == 200 and len(fups) >= 1:
        ok(f"GET follow-ups for interaction 1 -> {len(fups)} follow-ups")
        for f in fups[:2]:
            emit(f"     [{f['status']}] {f['suggested_action'][:65]}")
    else:
        fail(f"Follow-ups: status={r.status_code}, count={len(fups)}")
except Exception as e:
    fail(f"GET follow-ups error: {e}")

# ── 7: AI Chat - log_interaction ──────────────────────────────────────────────
section("7. POST /api/chat -- Tool: log_interaction")
emit("  (Calling Groq API via full LangGraph graph - may take 15-30s)")
try:
    msg = (
        "Met Dr. Priya Mehta today at Fortis Hospital, Gurugram. "
        "Discussed CardioShield extended-release dosing for elderly atrial fibrillation patients. "
        "She showed strong interest, especially in the CGHS reimbursement data. "
        "Shared the CardioShield clinical brochure and AF patient diary. "
        "Distributed 8 samples of CardioShield 5mg. Sentiment was positive. "
        "Outcomes: she agreed to initiate in 3 new AF patients next week."
    )
    r = httpx.post(f"{BASE}/api/chat",
                   json={"message": msg, "conversation_history": []},
                   timeout=120)
    d = r.json()
    tool = d.get("tool_used")
    if r.status_code == 200 and tool == "log_interaction":
        idata = d.get("interaction_data") or {}
        ok(f"log_interaction -> HCP={idata.get('hcp_name')}, id={idata.get('id')}, sentiment={idata.get('sentiment')}")
        emit(f"     Reply: {str(d.get('reply', ''))[:120]}")
    else:
        fail(f"log_interaction: tool={tool}, reply={str(d.get('reply', ''))[:150]}")
except Exception as e:
    fail(f"Chat log_interaction error: {e}")

# ── 8: AI Chat - search_hcp ───────────────────────────────────────────────────
section("8. POST /api/chat -- Tool: search_hcp")
emit("  (Calling Groq API via full LangGraph graph)")
try:
    r = httpx.post(f"{BASE}/api/chat",
                   json={"message": "Search for Dr. Sharma", "conversation_history": []},
                   timeout=120)
    d = r.json()
    tool = d.get("tool_used")
    if r.status_code == 200 and tool == "search_hcp":
        ok(f"search_hcp -> tool invoked correctly")
        emit(f"     Reply: {str(d.get('reply', ''))[:120]}")
    else:
        fail(f"search_hcp: tool={tool}, reply={str(d.get('reply', ''))[:150]}")
except Exception as e:
    fail(f"Chat search_hcp error: {e}")

# ── 9: AI Chat - suggest_followups ────────────────────────────────────────────
section("9. POST /api/chat -- Tool: suggest_followups")
emit("  (Calling Groq API via full LangGraph graph)")
try:
    r = httpx.post(f"{BASE}/api/chat",
                   json={"message": "Suggest follow-ups for interaction 1", "conversation_history": []},
                   timeout=120)
    d = r.json()
    tool = d.get("tool_used")
    suggestions = d.get("suggestions") or []
    if r.status_code == 200 and tool == "suggest_followups":
        ok(f"suggest_followups -> {len(suggestions)} suggestions")
        for s in suggestions:
            emit(f"     - {s[:80]}")
    else:
        fail(f"suggest_followups: tool={tool}, reply={str(d.get('reply', ''))[:150]}")
except Exception as e:
    fail(f"Chat suggest_followups error: {e}")

# ── 10: AI Chat - summarize_interaction ──────────────────────────────────────
section("10. POST /api/chat -- Tool: summarize_interaction")
emit("  (Calling Groq API via full LangGraph graph)")
try:
    msg2 = (
        "Summarize this visit note: Met Dr. Rajesh Iyer at NIMHANS Bengaluru on Thursday. "
        "Reviewed NeuroCalm XR pediatric indication update issued by DCGI. "
        "He acknowledged the revised SmPC but showed neutral interest. "
        "Shared updated patient information leaflet. No samples distributed."
    )
    r = httpx.post(f"{BASE}/api/chat",
                   json={"message": msg2, "conversation_history": []},
                   timeout=120)
    d = r.json()
    tool = d.get("tool_used")
    summary = d.get("interaction_data") or {}
    if r.status_code == 200 and tool == "summarize_interaction":
        ok(f"summarize_interaction -> HCP={summary.get('hcp_name')}, confidence={summary.get('confidence')}")
        emit(f"     Topics: {str(summary.get('topics_summary', ''))[:100]}")
    else:
        fail(f"summarize_interaction: tool={tool}, reply={str(d.get('reply', ''))[:150]}")
except Exception as e:
    fail(f"Chat summarize error: {e}")

# ── 11: AI Chat - edit_interaction ───────────────────────────────────────────
section("11. POST /api/chat -- Tool: edit_interaction")
if new_id:
    emit("  (Calling Groq API via full LangGraph graph)")
    try:
        edit_msg = (
            f"Update interaction {new_id}: change sentiment to neutral "
            f"and update outcomes to: Dr. requested 4 weeks of additional trial data before prescribing"
        )
        r = httpx.post(f"{BASE}/api/chat",
                       json={"message": edit_msg, "conversation_history": []},
                       timeout=120)
        d = r.json()
        tool = d.get("tool_used")
        if r.status_code == 200 and tool == "edit_interaction":
            ok(f"edit_interaction -> tool invoked for interaction {new_id}")
            emit(f"     Reply: {str(d.get('reply', ''))[:120]}")
        else:
            fail(f"edit_interaction: tool={tool}, reply={str(d.get('reply', ''))[:150]}")
    except Exception as e:
        fail(f"Chat edit_interaction error: {e}")
else:
    fail("Skipped edit_interaction - no new_id")

# ── Summary ───────────────────────────────────────────────────────────────────
total = PASS + FAIL
section(f"STAGE 6 RESULTS: {PASS}/{total} passed, {FAIL} failed")
if FAIL == 0:
    emit("  ALL TESTS PASSED! Stage 6 complete.")
else:
    emit(f"  {FAIL} test(s) need attention.")

emit("\nResults saved to: integration_results.txt")
OUT.close()
sys.exit(0 if FAIL == 0 else 1)
