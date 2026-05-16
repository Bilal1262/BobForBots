# Mandatory package README template

Every generated package README must follow this structure exactly:

```markdown
# <Package Name>
## Overview
One paragraph: what does this package do, what robot capability does
it implement, what would break if removed.

## Node graph
mermaid graph LR showing this package's nodes and topic connections.

## Nodes
For each node: executable name, one-sentence description, topic table
with columns Topic/Type/Direction, parameter table with columns
Parameter/Type/Default/Description.

## Common failures
Table with columns: Symptom | Likely cause | How to diagnose | Fix

## Launch
How to launch this package and what parameters to tune for a new robot.
```
