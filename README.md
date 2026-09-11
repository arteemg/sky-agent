# Sky agent 

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Stars](https://img.shields.io/github/stars/arteemg/autoswarm?style=social)](https://github.com/arteemg/autoswarm)
[![Forks](https://img.shields.io/github/forks/arteemg/autoswarm?style=social)](https://github.com/arteemg/autoswarm)
[![Python](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/)
[![Docker](https://img.shields.io/badge/Docker-required-2496ED?logo=docker&logoColor=white)](https://docker.com)

<p align="center">
  <br>
  <a href="https://discord.gg/9ggSRAFGKQ">
    <img src="https://img.shields.io/badge/Discord-Join%20Community-5865F2?logo=discord&logoColor=white" alt="Discord" />
  </a>
  <br>
  <img src="assets/logo_271.gif" alt="One-click-agent logo" width="400">
</p>

Deploy your own AI agent to the cloud in one click.


## Deploy

1. Fork this repo.
2. On [Railway](https://railway.com?referralCode=JRZMm1): **New Project → Deploy from GitHub repo** → pick your fork.
3. Add `LLM_API_KEY` - this can be an API key from any provider, including Anthropic, OpenAI, OpenRouter, etc.
4. Add `TELEGRAM_BOT_TOKEN` (see below)
5. Deploy.

Railway auto-redeploys every time you push to your fork, so editing your agent = editing files on GitHub.

## Get a Telegram bot token

1. Open Telegram and message [@BotFather](https://t.me/BotFather).
2. Send `/newbot`, pick a name and a username.
3. Copy the token it gives you — that's your `TELEGRAM_BOT_TOKEN`.

Telegram enables itself when `TELEGRAM_BOT_TOKEN` exists. In chat: `/reset` wipes the bot's memory of that conversation.

## Make it yours

| Want to change...                  | Edit...                                                                         |
| ---------------------------------- | ------------------------------------------------------------------------------- |
| API endpoints                      | `channels/http_api.py`                                                          |
| Personality, model, context length | `agent.yaml`                                                                    |
| The agent's abilities (tools)      | `agent/tools.py`                                                                |
| Channels (add Discord, Slack, ...) | drop a new file in `channels/`                                                  |

## Give your agent files

In the GitHub web UI open `knowledge/`, **Add file → Upload files**, commit. After the auto-redeploy, ask your agent "what files do you have?"

Plain-text formats work (md, txt, csv, code). PDFs and images are detected but not supported for now.

## How it works

```
Telegram / HTTP ──▶ respond(chat_id, text, config) ──▶ Claude API
                          │                              │
                     SQLite memory ◀──── tool use loop ──┘
```

Conversation memory is SQLite on disk, mount a volume (`DB_PATH`) to keep it across redeploys; on Railway, add a volume mounted at `/data` and set `DB_PATH=/data/agent.db`.

## Self-optimizing benchmark

This repo also ships a benchmark harness where a meta-agent rewrites its own multi-agent pipeline (prompts, tools, topology) to hill-climb on Harbor tasks. See `benchmark/` to run an experiment.


## License

MIT — do whatever you want with it. Have fun.
