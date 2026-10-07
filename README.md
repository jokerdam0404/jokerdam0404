# FactSet Cursor Plugin

Connect Cursor to [FactSet AI-Ready Data MCP](https://developer.factset.com/mcp/factset-ai-ready-data-mcp) for institutional financial data: fundamentals, estimates, prices, ownership, people, events, M&A, funds, screening, and more.

## What's included

| Component | Purpose |
| --- | --- |
| **MCP** (`mcp.json`) | Hosted FactSet server at `https://mcp.factset.com/content/v1` |
| **Skills** | Setup / auth guidance and financial research workflows |
| **Rules** | Prefer FactSet MCP for market data; keep data hygiene |
| **Commands** | `/factset-company-snapshot`, `/factset-ownership` |

## Install in Cursor

### Local plugin (this repo)

1. Copy or symlink this directory to `~/.cursor/plugins/local/factset`
2. Restart Cursor or reload the window
3. Open **Settings → Tools & MCP**, enable `factset`, and complete OAuth

### Manual MCP only

Add to `~/.cursor/mcp.json` (or project `.cursor/mcp.json`):

```json
{
  "mcpServers": {
    "factset": {
      "type": "http",
      "url": "https://mcp.factset.com/content/v1"
    }
  }
}
```

### Confidential OAuth client (optional)

If FactSet provisioned a confidential client, set env vars and extend the MCP entry:

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

Register these redirect URIs with FactSet:

- `https://www.cursor.com/agents/mcp/oauth/callback`
- `http://localhost:8787/callback`

FactSet access and content entitlements are required. Request MCP via the [FactSet Marketplace](https://www.factset.com/marketplace/catalog/product/model-context-protocol) or your account representative. Docs: [developer.factset.com/mcp](https://developer.factset.com/mcp).

## Usage

Ask Cursor natural-language finance questions, for example:

- "Pull FactSet fundamentals and consensus estimates for AAPL"
- "Who are the largest institutional holders of MSFT?"
- "Summarize upcoming calendar events for NVDA"

Or run `/factset-company-snapshot` / `/factset-ownership`.

## License

MIT. FactSet data remains subject to your FactSet subscription and terms.
