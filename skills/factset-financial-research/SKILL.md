---
name: factset-financial-research
description: >-
  Run FactSet-backed equity, credit, ownership, and event research workflows in
  Cursor. Use when analyzing companies, comparing peers, screening, reviewing
  ownership, or preparing financial due diligence with FactSet data.
---

# FactSet financial research

## Workflow

1. **Resolve the entity** with `FactSet_EntityReference` (ticker, name, or other ID).
2. **Pull the primary dataset** for the question (fundamentals, estimates, prices, ownership, etc.).
3. **Add context** only as needed: peers via screener, events, supply chain, geo revenue, or unstructured content.
4. **Report** with identifiers, as-of dates, currencies, and clear separation of FactSet facts vs analysis.

## Common playbooks

### Company snapshot

1. `FactSet_EntityReference` — profile and IDs
2. `FactSet_Fundamentals` — recent financials
3. `FactSet_EstimatesConsensus` — forward estimates
4. `FactSet_GlobalPrices` — price / return context
5. `FactSet_CalendarEvents` — near-term catalysts

### Ownership & control

1. Resolve entity
2. `FactSet_Ownership` — institutional / fund / insider
3. Optional: `FactSet_People` for board and management

### Credit / capital structure

1. Resolve entity
2. `FactSet_DebtCapitalStructure`
3. Optional: `FactSet_TermsConditions`, `FactSet_Fundamentals`

### Deal / M&A screen

1. `FactSet_MergersAcquisitions` for deal metrics
2. Supplement with fundamentals and ownership on target/acquirer

### Private markets

1. `FactSet_PrivateCompany` and/or `FactSet_PrivateEquityVC`
2. Cross-check entity reference before comparing to public comps

## Output standards

- Lead with the answer, then supporting FactSet figures.
- Keep tables tight: metric, value, period, source tool.
- Call out entitlement gaps instead of inventing substitutes.
- Prefer one clean narrative over dumping every tool response.
