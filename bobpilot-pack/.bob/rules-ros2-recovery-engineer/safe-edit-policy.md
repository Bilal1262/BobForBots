# Safe edit policy

- Do **not** edit packages whose names contain `hardware`, `driver`, `controller`, `actuator`, or `safety` without explicit engineer confirmation (wording match is case-insensitive).
- Do **not** change a parameter default without stating the current value and every node that reads that parameter.
- Do **not** remove a publisher or subscriber without checking all dependent nodes.
- Do **not** alter a lifecycle state machine without presenting the full transition diagram first.
- Always create a **Bob checkpoint** before the first file edit in any session.
- The **`safety_manager`** package is **read-only**: propose changes only; never apply them in this mode.
