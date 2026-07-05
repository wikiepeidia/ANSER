```markdown
# Search Tools

Exa AI search engine.

## Exa AI Search

A high-quality AI search engine, strong at technical and code search.

```bash
mcporter call 'exa.web_search_exa(query: "query", numResults: 5)'
mcporter call 'exa.get_code_context_exa(query: "code question", tokensNum: 3000)'
```

### Usage Scenarios

| Scenario | Parameters |
|-----|------|
| Web search | `web_search_exa(query: "...", numResults: 5)` |
| Code search | `get_code_context_exa(query: "...", tokensNum: 3000)` |

### Features

- Strong with English-language content and technical documentation
- Supports code-context search
- High-quality results

## Comparison With Other Search Tools

| Tool | Source | Best For |
|-----|------|---------|
| Exa | agent-reach | English / technical / code search |
| Zhipu Search | my-mcp-tools | Chinese-language search |
| GitHub Search | agent-reach (dev.md) | Repository / code search |
