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

### 2026-08-30 · Cycle 1 · 1 change · merged
- **intent-comprehension** — The agent incorrectly refused to provide the time, despite having shell access, so the prompt should clarify its capabilities.
