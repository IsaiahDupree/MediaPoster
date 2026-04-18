# MediaPoster — Agent Domain Audit

Each domain maps to a Claude Code agent with its own scoped MCP server and PRD.
Send each PRD + MCP config to a fresh Claude Code session to run work autonomously.

## Domain Map

| # | Domain | PRD | MCP Config |
|---|--------|-----|------------|
| 01 | Content Intelligence | [PRD](prds/01-content-intelligence.md) | [MCP](mcp-configs/01-content-intelligence.json) |
| 02 | Publishing Engine | [PRD](prds/02-publishing-engine.md) | [MCP](mcp-configs/02-publishing-engine.json) |
| 03 | Competitor Research | [PRD](prds/03-competitor-research.md) | [MCP](mcp-configs/03-competitor-research.json) |
| 04 | Social Analytics | [PRD](prds/04-social-analytics.md) | [MCP](mcp-configs/04-social-analytics.json) |
| 05 | Video Generation | [PRD](prds/05-video-generation.md) | [MCP](mcp-configs/05-video-generation.json) |
| 06 | Agent Orchestration | [PRD](prds/06-agent-orchestration.md) | [MCP](mcp-configs/06-agent-orchestration.json) |
| 07 | Safari Automation | [PRD](prds/07-safari-automation.md) | [MCP](mcp-configs/07-safari-automation.json) |
| 08 | CRM & Outreach | [PRD](prds/08-crm-outreach.md) | [MCP](mcp-configs/08-crm-outreach.json) |
| 09 | Trend Intelligence | [PRD](prds/09-trend-intelligence.md) | [MCP](mcp-configs/09-trend-intelligence.json) |
| 10 | ICP & Strategy | [PRD](prds/10-icp-strategy.md) | [MCP](mcp-configs/10-icp-strategy.json) |

## How to Use

1. Open Claude Code
2. Copy the MCP config JSON into `~/.claude/mcp_servers.json` (or Claude Desktop config)
3. Paste the PRD as your first message
4. The agent has scoped filesystem + shell access for its domain only

## Backend Root
`/Users/isaiahdupree/Documents/Software/MediaPoster/Backend`
