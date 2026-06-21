# Agent2048 — Pitch Deck

## Slide 1: Problem

**AI agents forget.**

Every time you ask an agent to work on your project:
- It reads 100+ files (80,000 tokens)
- Works for 30+ steps
- Forgets everything next session

```
Session 1: read 100 files → 80k tokens
Session 2: read 100 files again → 80k tokens
Session 3: read 100 files again → 80k tokens
```

**Cost: expensive, slow, repetitive.**

---

## Slide 2: Solution — 2048-style Memory

Inspired by the game 2048: **small tiles merge into bigger ones.**

```
Fact (L1) + Fact (L1)      → Pattern (L2)
Pattern (L2) + Pattern (L2) → Concept (L3)
Concept (L3) + Concept (L3) → Principle (L4)
```

| Level | What | Example |
|-------|------|---------|
| L1 | Concrete fact | "Project uses FastAPI" |
| L2 | Pattern | "All endpoints use FastAPI" |
| L3 | Concept | "REST API architecture" |
| **L4** | **Principle** | **"Production-ready, stop reviewing"** |

**Soft merge**: old facts are kept, marked as `merged_into`. `dive` reveals the full lineage tree.

---

## Slide 3: Metrics

### Compression
```
Raw facts:     48 items, 17,747 tokens
Active memory: 18 items,  2,631 tokens  (6.7x)
L4 principle:   1 item,    190 tokens  (93x)
```

### Token economy
```
Without memory:  7 audits × 80k = 56,000 tokens
With memory:     L4 + task =    390 tokens
Savings:         99%
```

### Real benchmark
```
Agent loads L4 (190 tokens) → knows entire project
→ answers in 1 step, not 30
```

---

## Slide 4: Features

- **28+ LLM providers** (OpenAI, Anthropic, Fireworks, Nvidia, Groq, etc.)
- **Interactive TUI** with command completion
- **Agent loop** with READ/WRITE/RUN/MEMORY actions
- **Permission system** (auto/ask/deny + allow/deny patterns)
- **SQLite + sqlite-vec ANN** for fast similarity search
- **Local embeddings** (fastembed, no API needed)
- **Per-project memory** (`.agent2048/memory.db`)
- **137 tests, 80% coverage, 9.5/10 security score**

---

## Slide 5: Demo

```bash
# 30-second demo
./demo.sh

# Or interactive
agent2048 tui
agent2048> ask audit the system --auto
# → agent works 20 steps, saves to memory

agent2048> ask what are your recommendations?
# → agent loads L4, answers in 1 step (not 30)

agent2048> stats
# → Memory pyramid: L1 → L2 → L3 → L4

agent2048> dive <L4_id>
# → Full lineage tree
```

**Agent2048: 56,000 tokens → 390 tokens. The agent always knows your project.**
