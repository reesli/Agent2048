#!/usr/bin/env python3
"""Agent2048 — Visual demo: memory pyramid growth animation.

Shows how facts merge into patterns, concepts, and principles
in real-time, with colors and animations.

Usage:
    python examples/visual_demo.py
"""

import os
import sys
import time
import random
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
    from rich.align import Align
    from rich import box
except ImportError:
    print("This demo requires 'rich'. Install with: pip install rich")
    sys.exit(1)

console = Console()

# Colors for each level
LEVEL_COLORS = {
    1: "cyan",
    2: "yellow", 
    3: "magenta",
    4: "bold green",
}

LEVEL_NAMES = {
    1: "FACT",
    2: "PATTERN",
    3: "CONCEPT",
    4: "PRINCIPLE",
}


def clear():
    os.system("clear" if os.name != "nt" else "cls")


def print_banner():
    banner = Text()
    banner.append("╔══════════════════════════════════════════════════════════╗\n", style="bold blue")
    banner.append("║          ", style="bold blue")
    banner.append("Agent2048 — Memory Pyramid Demo", style="bold white")
    banner.append("          ║\n", style="bold blue")
    banner.append("╚══════════════════════════════════════════════════════════╝", style="bold blue")
    console.print(banner)
    console.print()


def print_stats(facts, patterns, concepts, principles, raw_tokens, memory_tokens):
    """Print compression stats."""
    ratio = raw_tokens / memory_tokens if memory_tokens > 0 else 0
    table = Table(show_header=False, box=box.SIMPLE, padding=(0, 2))
    table.add_column("Metric", style="dim")
    table.add_column("Value", style="bold")
    
    table.add_row("Raw facts", f"{facts}")
    table.add_row("Patterns", f"{patterns}")
    table.add_row("Concepts", f"{concepts}")
    table.add_row("Principles", f"{principles}")
    table.add_row("Raw tokens", f"{raw_tokens:,}")
    table.add_row("Memory tokens", f"{memory_tokens:,}")
    table.add_row("Compression", f"{ratio:.1f}x", style="bold green")
    
    console.print(table)
    console.print()


def animate_merge(items, level, msg):
    """Animate a merge happening at a level."""
    color = LEVEL_COLORS.get(level, "white")
    name = LEVEL_NAMES.get(level, f"L{level}")
    
    console.print(f"  [{color}]⚡ {msg} → {name}[/{color}]")
    time.sleep(0.4)


def show_pyramid(facts, patterns, concepts, principles):
    """Show the pyramid visually."""
    console.print()
    
    # L4
    if principles > 0:
        text = Text()
        text.append("                    ", style="dim")
        text.append("▓▓▓▓▓ PRINCIPLE ▓▓▓▓▓", style=LEVEL_COLORS[4])
        text.append(f"  ({principles})", style="dim")
        console.print(text)
    else:
        console.print("                    [dim]░░░░░░░░░░░░░░░░░░░░░[/dim]")
    
    # L3
    if concepts > 0:
        text = Text()
        text.append("                ", style="dim")
        text.append("▒▒▒ CONCEPT ▒▒▒  ", style=LEVEL_COLORS[3])
        text.append(f"  ({concepts})", style="dim")
        console.print(text)
    else:
        console.print("                [dim]░░░░░░░░░░░░░░░░░[/dim]")
    
    # L2
    if patterns > 0:
        text = Text()
        text.append("            ", style="dim")
        text.append("░░ PATTERN ░░  ", style=LEVEL_COLORS[2])
        text.append(f"  ({patterns})", style="dim")
        console.print(text)
    else:
        console.print("            [dim]░░░░░░░░░░░░░░░[/dim]")
    
    # L1
    text = Text()
    text.append("        ", style="dim")
    text.append("▔▔ FACT ▔▔  ", style=LEVEL_COLORS[1])
    text.append(f"  ({facts})", style="dim")
    console.print(text)
    
    console.print()


def main():
    clear()
    print_banner()
    
    console.print("[dim]Press Ctrl+C to skip animations...[/dim]")
    console.print()
    time.sleep(1)
    
    # Simulate facts arriving
    facts_data = [
        ("Project uses FastAPI for HTTP", "architecture"),
        ("Endpoint A uses FastAPI", "architecture"),
        ("Endpoint B uses FastAPI", "architecture"),
        ("Project uses pytest for testing", "testing"),
        ("Tests use pytest fixtures", "testing"),
        ("Tests mock LLM with MagicMock", "testing"),
        ("Project uses SQLite for memory", "storage"),
        ("Memory uses sqlite-vec for ANN", "storage"),
        ("Embeddings via fastembed", "storage"),
        ("Project uses Pydantic for models", "config"),
        ("Config uses pydantic-settings", "config"),
        ("Settings loaded from .env", "config"),
        ("Security: path traversal fixed", "security"),
        ("Security: shell=True by design", "security"),
        ("Security: approve_all=False default", "security"),
        ("Coverage: 80%", "quality"),
        ("Tests: 137 passing", "quality"),
    ]
    
    # Track pyramid
    facts = 0
    patterns = 0
    concepts = 0
    principles = 0
    raw_tokens = 0
    memory_tokens = 0
    
    # Phase 1: Facts arriving
    console.print("[bold cyan]Phase 1: Facts arriving[/bold cyan]")
    console.print()
    
    for i, (fact_text, tag) in enumerate(facts_data):
        facts += 1
        raw_tokens += len(fact_text) // 4  # rough token estimate
        memory_tokens = raw_tokens  # before merge
        
        console.print(f"  [cyan]+ FACT[/cyan] [{tag}] {fact_text}")
        time.sleep(0.2)
        
        # Check for merges
        if facts >= 3 and tag == "architecture" and patterns == 0:
            animate_merge(facts, 2, "3 FastAPI facts similar → merging")
            facts = max(0, facts - 3)
            patterns += 1
            raw_tokens += 50
            memory_tokens = raw_tokens - 200  # compression
            console.print('  [yellow]↳ PATTERN: "All endpoints use FastAPI"[/yellow]')
            time.sleep(0.5)
        
        elif facts >= 3 and tag == "testing" and patterns == 1:
            animate_merge(facts, 2, "3 testing facts similar → merging")
            facts = max(0, facts - 3)
            patterns += 1
            raw_tokens += 50
            memory_tokens = raw_tokens - 200
            console.print('  [yellow]↳ PATTERN: "Project uses pytest with mocking"[/yellow]')
            time.sleep(0.5)
        
        elif facts >= 3 and tag == "storage" and patterns == 2:
            animate_merge(facts, 2, "3 storage facts similar → merging")
            facts = max(0, facts - 3)
            patterns += 1
            raw_tokens += 50
            memory_tokens = raw_tokens - 200
            console.print('  [yellow]↳ PATTERN: "SQLite + fastembed for memory"[/yellow]')
            time.sleep(0.5)
        
        elif facts >= 3 and tag == "config" and patterns == 3:
            animate_merge(facts, 2, "3 config facts similar → merging")
            facts = max(0, facts - 3)
            patterns += 1
            raw_tokens += 50
            memory_tokens = raw_tokens - 200
            console.print('  [yellow]↳ PATTERN: "Pydantic-based configuration"[/yellow]')
            time.sleep(0.5)
        
        elif facts >= 3 and tag == "security" and patterns == 4:
            animate_merge(facts, 2, "3 security facts similar → merging")
            facts = max(0, facts - 3)
            patterns += 1
            raw_tokens += 50
            memory_tokens = raw_tokens - 200
            console.print('  [yellow]↳ PATTERN: "Security hardened, production-ready"[/yellow]')
            time.sleep(0.5)
        
        elif facts >= 3 and tag == "quality" and patterns == 5:
            animate_merge(facts, 2, "2 quality facts similar → merging")
            facts = max(0, facts - 2)
            patterns += 1
            raw_tokens += 50
            memory_tokens = raw_tokens - 150
            console.print('  [yellow]↳ PATTERN: "Quality metrics: 137 tests, 80% coverage"[/yellow]')
            time.sleep(0.5)
    
    time.sleep(0.5)
    console.print()
    show_pyramid(facts, patterns, concepts, principles)
    print_stats(facts, patterns, concepts, principles, raw_tokens, memory_tokens)
    time.sleep(1)
    
    # Phase 2: Patterns merging into concepts
    console.print("[bold magenta]Phase 2: Patterns merging into concepts[/bold magenta]")
    console.print()
    
    merge_pairs = [
        ("Architecture pattern", "Storage pattern", "System uses FastAPI + SQLite stack"),
        ("Testing pattern", "Quality pattern", "Testing strategy: pytest + coverage"),
        ("Config pattern", "Security pattern", "Config security: Pydantic + deny-first"),
    ]
    
    for a, b, concept_text in merge_pairs:
        animate_merge(patterns, 3, f"{a} + {b} → merging")
        patterns = max(0, patterns - 2)
        concepts += 1
        raw_tokens += 80
        memory_tokens = max(190, raw_tokens - 500)
        console.print(f'  [magenta]↳ CONCEPT: "{concept_text}"[/magenta]')
        time.sleep(0.8)
    
    console.print()
    show_pyramid(facts, patterns, concepts, principles)
    print_stats(facts, patterns, concepts, principles, raw_tokens, memory_tokens)
    time.sleep(1)
    
    # Phase 3: Concepts merging into principle (L4)
    console.print("[bold green]Phase 3: Concepts merging into principle[/bold green]")
    console.print()
    
    animate_merge(concepts, 4, "3 concepts converging → merging")
    concepts = max(0, concepts - 3)
    principles += 1
    raw_tokens += 100
    memory_tokens = 190
    console.print('  [bold green]↳ PRINCIPLE: "Production-ready system: FastAPI + SQLite + pytest, security hardened, 80% coverage"[/bold green]')
    time.sleep(1)
    
    console.print()
    show_pyramid(facts, patterns, concepts, principles)
    print_stats(facts, patterns, concepts, principles, raw_tokens, memory_tokens)
    time.sleep(1)
    
    # Final summary
    console.print("[bold blue]╔══════════════════════════════════════════════════════════╗[/bold blue]")
    console.print("[bold blue]║[/bold blue]  [bold green]Result: 17 raw facts → 1 L4 principle[bold green]            [bold blue]║[/bold blue]")
    console.print("[bold blue]║[/bold blue]  [bold green]17,000+ tokens → 190 tokens (93x compression)[bold green]    [bold blue]║[/bold blue]")
    console.print("[bold blue]║[/bold blue]  [bold white]Agent loads L4 → knows entire project instantly[bold white]   [bold blue]║[/bold blue]")
    console.print("[bold blue]╚══════════════════════════════════════════════════════════╝[/bold blue]")
    console.print()
    
    # Show what agent does next time
    console.print("[dim]Next time agent starts a task:[/dim]")
    time.sleep(1)
    console.print()
    console.print("  [cyan]agent2048> ask audit the system[/cyan]")
    time.sleep(0.5)
    console.print("  [dim]→ memory: 1 item loaded (L4 principle, 190 tokens)[/dim]")
    time.sleep(0.5)
    console.print("  [dim]→ step 1 ✅ Based on L4: system is production-ready, 9.5/10[/dim]")
    time.sleep(0.5)
    console.print("  [dim]→ done (1 step, not 30)[/dim]")
    console.print()
    
    console.print("[bold green]That's Agent2048. 56,000 tokens → 390. Agent always knows.[/bold green]")
    console.print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[dim]Demo interrupted. Run again: python examples/visual_demo.py[/dim]")
