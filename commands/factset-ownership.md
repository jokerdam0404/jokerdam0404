---
name: factset-ownership
description: Analyze FactSet institutional ownership, fund holdings, and insider activity for a company
---

Analyze ownership for a company using the FactSet MCP.

1. Resolve the entity with `FactSet_EntityReference`.
2. Query `FactSet_Ownership` for institutional holders, fund holdings, and insider activity as available.
3. Optionally add `FactSet_People` for board/management context.

Present top holders, recent position changes, and any notable insider activity. Cite FactSet and note data vintage. Ask which ticker or company if none was provided.
