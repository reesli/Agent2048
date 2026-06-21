# Agent2048

A CLI framework for AI agents with hierarchical memory inspired by the **2048** game.

> **56,000 tokens → 390 tokens (99% savings).** The agent always knows your project, without re-reading files.

## Beyond Token Savings — Real Programming, Not Vibe Coding

Most AI coding tools work in a "do this / continue / write something" mode — you give a vague prompt, the agent guesses what you want, writes code, and forgets everything. This is **vibe coding**: fun for prototypes, dangerous for real projects.

Agent2048 takes a different approach: **conscious task execution with persistent memory.**

- **Set real tasks, not vibes.** Instead of "write a function that does X", you say "audit the security of this module and fix what you find". The agent works step-by-step: reads files, analyzes, writes code, runs tests, saves findings to memory.

- **The agent remembers.** Next time you ask about the project, it doesn't start from scratch. It loads the L4 principle ("production-ready, 9.5/10, stop reviewing") and gives you an answer in 1 step instead of 30.

- **Knowledge compounds.** Facts merge into patterns, patterns into concepts, concepts into principles. The more you use it, the smarter it gets about your specific project.

This is not a chatbot that writes code. It's an **agent with project awareness** that does real software engineering work.

## The Problem

Every time you ask an AI agent to work on your project:
- It reads 100+ files (80,000 tokens)
- Works for 30+ steps
- **Forgets everything** next session

```
Session 1: read 100 files → 80k tokens
Session 2: read 100 files again → 80k tokens
Session 3: read 100 files again → 80k tokens
```

**Cost: expensive, slow, repetitive.**

## The Solution — 2048-style Memory

Inspired by the game 2048: **small tiles merge into bigger ones.**

```
Fact (L1) + Fact (L1)    → Pattern (L2)
Pattern (L2) + Pattern (L2) → Concept (L3)
Concept (L3) + Concept (L3) → Principle (L4)
```

| Level | What | Example |
|-------|------|---------|
| L1 | Concrete fact | "Project uses FastAPI" |
| L2 | Pattern | "All endpoints use FastAPI" |
| L3 | Concept | "REST API architecture" |
| **L4** | **Principle** | **"Production-ready, stop reviewing"** |

**Soft merge**: old facts are kept, marked as `merged_into`. Use `dive` to reveal the full lineage tree.

When starting a new task, the agent loads the relevant **L4 principle** (190 tokens) instead of re-reading all files (80,000 tokens).

## Demo

[![Agent2048 Demo](https://asciinema.org/a/b3lZeQtR0hfJJ1Me.svg)](https://asciinema.org/a/b3lZeQtR0hfJJ1Me)

```text
$ agent2048 tui
Agent2048 Control Panel
Tab to complete, ↑↓ for history, /help for commands

agent2048> auto on
Auto-approve: ON

agent2048 [auto]> ask audit the system
→ task: audit the system
→ memory: 10 items loaded
→ step 1 ⚙️ List project files
→ step 2 📄 Read agent2048/actions.py
→ step 3 🤔 Security is solid, path traversal fixed...
→ step 4 ✅ System is production-ready, 9.5/10
→ done

agent2048 [auto]> ask what are your recommendations?
→ task: what are your recommendations?
→ memory: 10 items loaded
→ step 1 ✅ Based on L4 memory: stop reviewing, focus on features.

agent2048 [auto]> stats
    Memory Pyramid (2048)
┏━━━━━━━┳━━━━━━━━━━━┳━━━━━━━┓
┃ Level ┃ Name      ┃ Count ┃
┡━━━━━━━╇━━━━━━━━━━━╇━━━━━━━┩
│   1   │ Fact      │    16 │
│   2   │ Pattern   │     3 │
│   3   │ Concept   │     2 │
│   4   │ Principle │     1 │
│   —   │ Total     │    22 │
└───────┴───────────┴───────┘

agent2048 [auto]> dive <L4_id>
L4 [task]: System is production-ready, 9.5/10...
  L3 [task]: Performance-audit-driven optimization...
    L2 [task]: Security audit converged...
      L1 [task]: First audit: 7/10, 2 critical issues...
      L1 [task]: Second audit: 8.5/10, all fixed...
```

**Key moment**: The second `ask` answered in **1 step** (not 30) because the agent loaded the L4 principle from memory.

## Metrics

| Metric | Value |
|--------|-------|
| Tests | 137 (80% coverage) |
| LLM providers | 28+ |
| Context compression | **93x** (L4 principle) |
| Token savings | **99%** (56k → 390) |
| Security score | 9.5/10 |

## Pitch

See [PITCH_DECK.md](PITCH_DECK.md) for the 5-slide presentation.

## Installation

### One command (recommended)

```bash
curl -fsSL https://raw.githubusercontent.com/reesli/Agent2048/main/install.sh | bash
```

This clones the repo, creates a venv, installs the package, and creates a global `agent2048` command. After installation, edit `~/.config/agent2048/.env` to add your API key.

### Manual

```bash
# Global venv (once)
python3 -m venv ~/.venvs/agent2048
source ~/.venvs/agent2048/bin/activate
pip install -e /path/to/agent2048

# Or locally
cp .env.example .env
# edit .env, add your OPENAI_API_KEY
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Configuration

### Quick setup with a provider

Agent2048 supports 28+ providers. The fastest way to configure:

```bash
# 1. List available providers
agent2048 providers

# 2. Activate a provider (prompts for API key)
agent2048 use openai
# or with key and model:
agent2048 use fireworks --key fw_yourkey --model accounts/fireworks/models/glm-5p2

# 3. List available models from the provider
agent2048 models

# 4. Set active model
agent2048 model gpt-4o-mini
```

### Manual config via `.env`

You can edit the config file directly:

```bash
# Global config (works in any directory)
vi ~/.config/agent2048/.env

# Or per-project config (in project root)
vi .env
```

```bash
# .env example
OPENAI_API_KEY=your-api-key-here
OPENAI_BASE_URL=https://api.openai.com/v1
MODEL=gpt-4o-mini
EMBEDDING_PROVIDER=fastembed
EMBEDDING_MODEL=BAAI/bge-small-en-v1.5
DB_PATH=
```

### Provider examples

```bash
# OpenAI
OPENAI_API_KEY=sk-...
OPENAI_BASE_URL=https://api.openai.com/v1
MODEL=gpt-4o-mini

# Fireworks AI (GLM 5.2, Kimi K2.7, etc.)
OPENAI_API_KEY=fw_...
OPENAI_BASE_URL=https://api.fireworks.ai/inference/v1
MODEL=accounts/fireworks/models/glm-5p2

# Nvidia NIM
OPENAI_API_KEY=nvapi-...
OPENAI_BASE_URL=https://integrate.api.nvidia.com/v1
MODEL=minimaxai/minimax-m3

# OpenRouter
OPENAI_API_KEY=sk-or-...
OPENAI_BASE_URL=https://openrouter.ai/api/v1
MODEL=openai/gpt-4o-mini

# Ollama (local, no API key needed)
OPENAI_API_KEY=ollama
OPENAI_BASE_URL=http://localhost:11434/v1
MODEL=llama3.3
```

### Per-project memory

Each project gets its own memory database in `.agent2048/memory.db` (relative to your working directory). This means:
- Agent working in `/project-a` has its own memory
- Agent working in `/project-b` has its own memory
- No cross-contamination between projects

Leave `DB_PATH=` empty to use the default per-project path, or set it explicitly:
```bash
DB_PATH=.agent2048/memory.db
```

Supports any OpenAI-compatible provider. Check the list:

```bash
agent2048 providers
```

## Providers

Agent2048 auto-loads providers from `~/.config/opencode/opencode.jsonc`, `~/.config/kilo/kilo.jsonc`, and `~/.codex/config.toml` (without copying secrets). Additionally, 28+ built-in presets:

- OpenAI, Anthropic, Google Gemini, OpenRouter, Groq
- Fireworks, Together, Perplexity, Mistral, DeepSeek, xAI, Cohere
- Alibaba, Hugging Face, Minimax, Moonshot/Kimi, Cloudflare
- GitHub Models, GitHub Copilot, Azure, VertexAI, Amazon Bedrock
- Nvidia, Ollama, LM Studio, vLLM, Aerolink, Kilo Gateway, Freemodel

API keys stay in your `.env` — we never copy them into project code.

## Memory Demo (no API key needed)

```bash
python examples/memory_demo.py
python examples/compression_demo.py
```

The demo shows how similar facts automatically merge into patterns and concepts.

## Context Compression

We measure two metrics:

- **Raw log tokens** — total tokens of all messages the agent sent to the LLM.
- **Memory tokens** — total tokens of the final hierarchical memory after merges.

### Synthetic benchmark (500 facts)

| Metric | Value |
|--------|-------|
| Raw facts | 500 |
| Raw tokens | 4669 |
| Memory items | 22 |
| Memory tokens | 131 |
| **Compression ratio** | **35.64x** |

### Real benchmark (4 CLI tasks)

| Metric | Value |
|--------|-------|
| Tasks | 4 |
| Total log tokens | 40730 |
| Memory items | 8 |
| Memory tokens | 306 |
| **Compression ratio** | **133.10x** |

## Soft Merge and Dive

Old facts are not deleted — they are marked as `merged_into` and remain in the database. To see what an abstraction is made of:

```bash
agent2048 memory <query>          # find the ID of a top-level item
agent2048 dive <item_id>          # dive into the details
```

## Management and Approvals (Codex CLI + Claude CLI style)

Create a config:

```bash
agent2048 init
```

This creates `~/.config/agent2048/config.toml` with trust level, permissions, and per-project overrides.

### Run modes

```bash
# Auto-approve — agent works without asking
agent2048 ask "..." --auto

# Ask before every action (like Claude Code)
agent2048 ask "..." --ask

# Default: reads trust_level from config.toml
```

### Example config.toml

```toml
model = "gpt-4o-mini"
provider = "openai"
reasoning_effort = "medium"

# auto, ask, deny
trust_level = "ask"

[permissions]
allow = ["*.py", "*.md"]
deny = ["*.secret", "rm"]

[projects."/home/user/myproject"]
trust_level = "ask"
allow = ["*.py", "*.md"]
```

## Multiple Agents — One Memory

Memory is a regular SQLite database (`DB_PATH`). If multiple agents point to the same `DB_PATH`, they read and populate the same memory. This works with different LLM providers: embeddings are local (`fastembed`), while the LLMs can be anything.

## Interactive Chat

```bash
agent2048 chat
```

Mode with streaming responses, history, and memory. Commands available inside:

- `/save <fact>` — save a fact to memory
- `/search <query>` — search memory
- `/do <task>` — run the full action loop inside chat
- `/exit` — exit

## Streaming

Responses in `chat` mode are streamed (like opencode/kilo). For `ask`, a regular one-shot completion is used.

## Progress

The `ask` command shows a `step N / max` progress indicator during execution.

## Control Panel (TUI)

```bash
agent2048 tui
```

Interactive panel with command completion, history, and shortcuts. No need to type `agent2048` before every command:

```text
agent2048> ask Create a simple Python CLI dice roller
agent2048> chat
agent2048> stats
agent2048> providers
agent2048> exit
```

## Project Settings

```bash
agent2048 project --trust-level auto    # for current folder
agent2048 project --allow "*.py" --allow "*.md"   # allow file patterns
agent2048 project --deny "*.secret" --deny "rm"   # deny patterns
agent2048 project --show               # show settings
```

## Shell Completion

```bash
agent2048 --install-completion zsh
# or bash
agent2048 --install-completion bash
```

## Running the Agent

```bash
agent2048 ask "Write a Python CLI habit tracker"
```

Commands:

- `agent2048 ask <task>` — run the agent
- `agent2048 ask <task> --auto` — auto-approve
- `agent2048 ask <task> --ask` — ask before every action
- `agent2048 chat` — interactive chat with memory and streaming
- `agent2048 tui` — control panel with completion
- `agent2048 stats [--include-merged]` — memory pyramid
- `agent2048 memory <query>` — semantic search
- `agent2048 dive <item_id>` — dive into an abstraction
- `agent2048 project` — project settings
- `agent2048 clear --yes` — wipe memory
- `agent2048 providers` — list providers
- `agent2048 use <provider> [key] [--model <id>]` — activate provider
- `agent2048 set-key <api_key>` — save API key to .env
- `agent2048 models [--provider <name>]` — list available models
- `agent2048 model <id_or_number>` — set active model

### Supported Providers

Built-in presets: OpenAI, Anthropic, Google Gemini, OpenRouter, Groq, Fireworks, Together, Perplexity, Mistral, DeepSeek, xAI, Cohere, Alibaba, Hugging Face, Minimax, Moonshot/Kimi, Cloudflare, GitHub Models, GitHub Copilot, Azure, VertexAI, Amazon Bedrock, Nvidia, Ollama, LM Studio, vLLM, Aerolink, Kilo Gateway, Freemodel, and more.

## Theme

The interface uses a color scheme inspired by your `waybar` config (Dracula-like: dark background, pink and purple accents). Settings in `agent2048/theme.py`.

## Architecture

- `agent2048/cli.py` — entry point
- `agent2048/memory.py` — SQLite storage, soft merge, ANN index
- `agent2048/llm.py` — LLM wrapper and embedding plugins
- `agent2048/agent.py` — agent loop with retry
- `agent2048/actions.py` — agent actions
- `agent2048/prompts.py` — system prompts
- `agent2048/providers.py` — provider registry
- `agent2048/theme.py` — color theme
- `agent2048/toml_config.py` — TOML config and permissions
- `agent2048/tui.py` — interactive control panel
- `agent2048/logging_config.py` — structured logging
- `agent2048/exceptions.py` — typed exceptions

## Tests

```bash
pytest tests/ -v
```

## Status

Production-ready. 137 tests, 80% coverage, 9.5/10 security score.
