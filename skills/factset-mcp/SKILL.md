---
name: factset-mcp
description: >-
  Connect to and use the FactSet AI-Ready Data MCP server in Cursor. Use when
  setting up FactSet MCP, authenticating, choosing FactSet tools, or troubleshooting
  FactSet MCP connection or OAuth issues.
---

# FactSet MCP

## Endpoint

Hosted MCP (Streamable HTTP):

```text
https://mcp.factset.com/content/v1
```

Official docs: https://developer.factset.com/mcp/factset-ai-ready-data-mcp

## Cursor setup

1. Enable the FactSet plugin (or ensure `mcp.json` includes the `factset` server).
2. Open **Cursor Settings → Tools & MCP**.
3. Enable `factset` and complete OAuth when prompted.
4. If FactSet issued a confidential OAuth client, register Cursor redirect URIs with FactSet:
   - `https://www.cursor.com/agents/mcp/oauth/callback` (web / agents)
   - `http://localhost:8787/callback` (desktop)
5. Optional static OAuth in user `~/.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "factset": {
      "type": "http",
      "url": "https://mcp.factset.com/content/v1",
      "auth": {
        "CLIENT_ID": "${env:FACTSET_CLIENT_ID}",
        "CLIENT_SECRET": "${env:FACTSET_CLIENT_SECRET}"
      }
    }
  }
}
```

Request MCP access via FactSet Marketplace or your FactSet account representative if tools are unauthorized.

## Tool selection

| Need | Tool |
| --- | --- |
| Fundamentals / financials | `FactSet_Fundamentals` |
| Estimates / consensus | `FactSet_EstimatesConsensus` |
| Prices / returns | `FactSet_GlobalPrices` |
| Ownership / insider | `FactSet_Ownership` |
| People / board | `FactSet_People` |
| Entity lookup | `FactSet_EntityReference` |
| Events calendar | `FactSet_CalendarEvents` |
| M&A | `FactSet_MergersAcquisitions` |
| Private companies | `FactSet_PrivateCompany` |
| PE / VC | `FactSet_PrivateEquityVC` |
| Debt capital structure | `FactSet_DebtCapitalStructure` |
| Funds / ETFs | `FactSet_FundsETF`, `FactSet_FundsScreener` |
| Company screener | `FactSet_CompanyScreener` |
| Transcripts / news / filings | `FactSet_UnstructuredContent` |
| Metric codes | `FactSet_Metrics` |
| Supply chain | `FactSet_SupplyChain` |
| Geo revenue | `FactSet_GeoRev` |
| RBICS | `FactSet_RBICS` |
| Bond terms | `FactSet_TermsConditions` |
| Banks | `FactSet_Banks` |
| Macro | `FactSet_Macroeconomics` |
| Quant factors | `FactSet_QFL` |
| Power & utilities | `FactSet_PowerUtilities` |

## Troubleshooting

- **401 / auth**: Re-auth in Tools & MCP; confirm FactSet entitlements and OAuth client redirects.
- **Empty / limited tools**: Package availability depends on FactSet AI-Ready data tier and firm type.
- **Ambiguous issuer**: Call `FactSet_EntityReference` first to resolve identifiers.
- **Wrong metric codes**: Call `FactSet_Metrics` before fundamentals/estimates pulls.
