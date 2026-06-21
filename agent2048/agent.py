"""Agent loop."""

import time
from pathlib import Path
from typing import Any

import openai
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from agent2048.actions import Action, ActionExecutor, parse_action
from agent2048.config import settings
from agent2048.exceptions import LLMError, MemoryError
from agent2048.llm import llm
from agent2048.logging_config import logger
from agent2048.memory import MemoryStore
from agent2048.prompts import AGENT_SYSTEM, build_context_prompt, build_observation_prompt
from agent2048.tokenizer import count_tokens
from agent2048.toml_config import ProjectConfig


class Agent:
    def __init__(
        self,
        memory: MemoryStore,
        workdir: Path,
        console: Console,
        project_cfg: ProjectConfig | None = None,
        approve_all: bool = False,
    ):
        self.memory = memory
        self.workdir = workdir
        self.console = console
        self.project_cfg = project_cfg or ProjectConfig()
        self.executor = ActionExecutor(memory, workdir, console, self.project_cfg, approve_all)
        self.last_log_tokens: int = 0
        self.last_memory_tokens: int = 0

    def _chat_with_retry(self, messages: list[dict[str, Any]], max_retries: int = 3) -> str:
        """Call LLM with retry on rate limit (429) and auth errors."""
        self._truncate_messages(messages)
        for attempt in range(max_retries):
            try:
                return llm.chat(messages)
            except openai.RateLimitError:
                wait = 2 ** attempt * 5
                self.console.print(f"[agent.warn]→ rate limited, waiting {wait}s...[/agent.warn]")
                time.sleep(wait)
            except (openai.APIConnectionError, openai.APITimeoutError, openai.InternalServerError) as e:
                wait = 2 ** attempt
                self.console.print(f"[agent.warn]→ API error ({type(e).__name__}), retry in {wait}s...[/agent.warn]")
                time.sleep(wait)
        self.console.print("[agent.danger]→ max retries reached[/agent.danger]")
        raise RuntimeError(f"LLM request failed after {max_retries} retries")

    def _truncate_messages(self, messages: list[dict[str, Any]]) -> None:
        """Truncate messages list to fit within max_context_tokens.

        Keeps system message + first user message, then keeps the most recent
        messages. Summarizes truncated history into a single user message."""
        max_tokens = settings.max_context_tokens
        total = sum(count_tokens(msg.get("content", "")) for msg in messages)
        if total <= max_tokens:
            return

        # Keep system (0) and first user (1), then last N messages.
        keep_head = 2
        while keep_head < len(messages) and total > max_tokens:
            removed = messages.pop(keep_head)
            total -= count_tokens(removed.get("content", ""))
            # Replace removed pair with a compact summary marker.
            if keep_head == 2:
                messages.insert(keep_head, {"role": "user", "content": "[Earlier steps truncated to fit context. See memory for details.]"})
                total += count_tokens(messages[keep_head]["content"])
                keep_head += 1

    def run(self, task: str) -> str:
        """Run the agent on a task until DONE or max steps."""
        relevant = self.memory.search(task, top_k=10)
        history: list[dict[str, Any]] = []

        messages = [
            {"role": "system", "content": AGENT_SYSTEM},
            {"role": "user", "content": build_context_prompt(task, relevant)},
        ]

        self.console.print(f"[agent.accent]→ task:[/agent.accent] {task}")
        if relevant:
            self.console.print(f"[agent.info]→ memory: {len(relevant)} items loaded[/agent.info]")
        else:
            self.console.print("[agent.muted]→ memory: empty[/agent.muted]")

        with Progress(
            SpinnerColumn(),
            TextColumn("[agent.accent]{task.description}[/agent.accent]"),
            console=self.console,
            transient=True,
        ) as progress:
            task_progress = progress.add_task("thinking...", total=settings.max_steps)
            for step in range(1, settings.max_steps + 1):
                progress.update(task_progress, description=f"step {step}", advance=1)
                prompt = build_observation_prompt(history, last_step=len(history))
                messages.append({"role": "user", "content": prompt})

                try:
                    raw = self._chat_with_retry(messages)
                except Exception as e:
                    self.console.print(f"[agent.danger]→ LLM error: {e}[/agent.danger]")
                    self._save_partial_memory(task, history)
                    self._compute_metrics(messages)
                    return f"Agent stopped at step {step}: {e}"

                try:
                    action = parse_action(raw)
                except Exception as e:
                    self.console.print(f"[agent.danger]→ parse error: {e}[/agent.danger]")
                    messages.append({"role": "assistant", "content": raw})
                    messages.append({"role": "user", "content": "That was not valid JSON. Return exactly one valid JSON action object."})
                    continue

                result = self.executor.execute(action, step)

                self.console.print(f"[agent.muted]→ step {step}[/agent.muted] {result['display']}")

                history.append({"step": step, "action": action.model_dump(), "result": result.get("result", "")})

                messages.append({"role": "assistant", "content": raw})
                messages.append({"role": "user", "content": f"Result: {result.get('result', '')}"})

                if action.type == "DONE":
                    progress.update(task_progress, completed=settings.max_steps)
                    self.console.print(f"[agent.success]→ done: {result.get('result', '')[:120]}[/agent.success]")
                    try:
                        self.memory.add(
                            f"Task result: {task}. {result.get('result', '')}",
                            level=1,
                            tag="task",
                            meta={"task": task},
                        )
                    except Exception as e:
                        logger.warning("Failed to save task result to memory: %s", e)
                    self._compute_metrics(messages)
                    return result.get("result", "")

        self.console.print("[agent.warn]→ max steps reached[/agent.warn]")
        self._save_partial_memory(task, history)
        self._compute_metrics(messages)
        return "Agent reached max steps without finishing."

    def _save_partial_memory(self, task: str, history: list[dict[str, Any]]) -> None:
        """Save partial progress to memory when the agent stops early."""
        try:
            steps_done = len(history)
            summary = f"Task (incomplete): {task}. Completed {steps_done} steps."
            if history:
                last = history[-1]
                summary += f" Last action: {last['action'].get('type', '?')}."
            self.memory.add(summary, level=1, tag="partial", meta={"task": task})
        except Exception as e:
            logger.warning("Failed to save partial memory: %s", e)

    def _compute_metrics(self, messages: list[dict[str, Any]]) -> None:
        """Compute log and memory token counts after a run.

        Uses get_token_counts() to avoid loading all embeddings.
        """
        self.last_log_tokens = sum(
            count_tokens(msg.get("content", "")) for msg in messages
        )
        _, self.last_memory_tokens = self.memory.get_token_counts()
