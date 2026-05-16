# Node graph explanation methodology

Follow these six steps in order:

1. **Packages:** List every package with a one-line description of its role.
2. **Launches:** Identify top-level launch files and enumerate which nodes each starts.
3. **Per-node inventory:** For each node, list name, package, executable, subscribed topics, published topics, services, and action servers (from code and launch).
4. **Data-flow chain:** Describe a linear path from sensor inputs through processing to actuator outputs.
5. **Lifecycle:** Highlight lifecycle-managed nodes and their states if determinable from the codebase.
6. **Orphans:** Flag nodes whose published topics have no known subscribers as possible dead code or missing wiring.
