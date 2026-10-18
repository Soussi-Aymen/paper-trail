---
name: learn-from-failures
description: >-
  Reads docs/LESSONS.md before a plan step and appends a general lesson after
  a step that failed. Use at the start and end of a step in docs/plan.md.
---

# Learn from failures

Read `docs/LESSONS.md` before a step.

After a step, append one entry only if something failed: a command error, a failing check, or an abandoned approach. If nothing failed, write nothing.

```markdown
### <short title>
- Step: <id>
- Symptom: <what was observed>
- Root cause: <why>
- Rule: <a rule that applies beyond this case>
```

Merge duplicate entries. Keep the file under about 100 lines.
