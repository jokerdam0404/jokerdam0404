---
name: factset-company-snapshot
description: Build a FactSet-backed company snapshot (profile, fundamentals, estimates, price, events)
---

Build a concise company snapshot using the FactSet MCP.

1. Resolve the company with `FactSet_EntityReference`.
2. Pull recent fundamentals via `FactSet_Fundamentals`.
3. Pull consensus estimates via `FactSet_EstimatesConsensus`.
4. Pull recent price/return context via `FactSet_GlobalPrices`.
5. Pull near-term events via `FactSet_CalendarEvents`.

Summarize in this order: what the company is, key financials, forward estimates, market performance, upcoming catalysts. Cite FactSet and include as-of dates. Ask which ticker or company if none was provided.
