# Agent Etna — Contract & Guardrails

This file is maintained automatically by **Agent Etna** for **sky agent**.
It is this agent's behavioral **contract**: what it's for, who it serves, what's
in and out of scope, plus a log of every change Etna has applied — so the whole
footprint is visible and auditable in your own repo.

_Maintained by Agent Etna. Don't edit by hand — it is rewritten on every shipped change._

## Agent
- **Repo:** `arteemg/sky-agent` (branch `main`)

## Behavioral contract
- **Purpose:** sky agent is a general conversational assistant reachable through HTTP API and Telegram, backed by an LLM and running on Railway.
- **Calibration level:** Foundational — basics first

## Guardrails
- Stay focused on this purpose: sky agent is a general conversational assistant reachable through HTTP API and Telegram, backed by an LLM and running on Railway.

## Change history

### 2026-08-31 · Cycle 2 · 1 change · merged
- **context-retention** — Scopes the fix to the exact phrasing failure (blanket 'no memory' denial) as narrow domain knowledge without touching the system prompt that previously regressed the cost-unbounded-loop guardrail.
