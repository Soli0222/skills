---
type: Attested Computation
title: Example Computation
description: What this computation returns and whose definition it follows.
status: draft
runtime: bigquery
parameters:
  - { name: year, type: integer, required: true }
executor:
  resource: references/skills/run-on-bq.md
  receipt: [job_id, executed_sql, result]
attester:
  resource: references/attesters/example.py
# Replace with the actor that wrote this and when (§5.2, §7).
# Use human:<id> only when a person actually authored it.
generated: { by: REPLACE-WITH-ACTOR, at: REPLACE-WITH-ISO-8601-DATETIME }
# Add stale_after only when the definition has a known lifetime (§5.5).
sources:
  - id: policy
    resource: https://example.com/policy
    title: The policy this computation implements
---

# Computation

```sql
SELECT SUM(amount) AS total
FROM example.table
WHERE fiscal_year = @year
```

The computation binds only the declared `parameters`, per the policy.[^policy]

[^policy]: The policy this computation implements
