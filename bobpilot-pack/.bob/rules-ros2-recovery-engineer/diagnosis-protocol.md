# Five-step fault diagnosis protocol

**Step 1 — Timeline reconstruction:** **Call `parse_diagnostics` first** on the mission bag (earliest WARN/ERROR is the lead). Then use `read_bag` on specific topics in a **narrow** time window around that event. Sort everything by timestamp and narrate what failed and when.

**Step 2 — Fault isolation:** The **first** chronological anomaly is the primary suspect; the root cause is rarely the loudest later symptom. Use `inspect_graph` to map the offending topic or parameter to an owning node.

**Step 3 — Code trace:** Open that node’s source, locate the function where the fault originates, cite file and line.

**Step 4 — Fix proposal:** Describe the minimal change: what it changes, why it fixes the root cause, what it does **not** change, and which tests will prove it.

**Step 5 — Approval gate:** Present the plan and **wait** for engineer approval before edits. After approval, create a Bob checkpoint, apply the fix, add a test, and update the relevant runbook.
