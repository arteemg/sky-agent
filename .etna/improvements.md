

## Improvements (approved via Agent Etna simulations)
- Scopes the fix to the exact phrasing failure (blanket 'no memory' denial) as narrow domain knowledge without touching the system prompt that previously regressed the cost-unbounded-loop guardrail.
  > {"topic":"in-session vs cross-session memory phrasing","trigger":"user asks whether you remember them, remember previous conversations, or refers to something 'earlier'","correct-behavior":"Before saying you have no memory, check the current conversation's prior turns — if the referenced content is there, use it. Only state you lack memory of PREVIOUS SESSIONS (across /reset or new chats); never say 'I don't have any memory' as a blanket statement, since in-session turns are always available to you.","note":"All other guardrails still apply unchanged: /reset still means a genuine fresh start, and unsafe/looping requests must still be refused or gated exactly as before."}
  This change is not sufficient on its own.
  This agent has nowhere to remember anything between messages.
  The PR wires this up in the agent's code. It will not work until you have actually created the store and given the agent its connection details — that part is yours, and nothing we ship can do it for you.
  We looked at pyproject.toml, the repository file list (1 file), the environment variables this agent declares and found nothing that persists between conversations. If this agent does have a store we missed, say so and we'll work from that instead.
  Options that fit this agent:
  - SQLite file — lowest — a file next to the agent, no account, no cost (better-sqlite3). Lost whenever the filesystem is replaced, which on most hosts is every deploy.
  - A hosted Postgres (Supabase, Neon, Render, RDS) — moderate — an account, a connection string, one table (pg). Survives deploys and scales past one instance. The usual right answer.
  - A hosted Redis (Upstash, Redis Cloud) — low — an account and a URL (ioredis). Ideal for recent conversation state; set an expiry, and don't use it as the only copy of anything you need next month.
