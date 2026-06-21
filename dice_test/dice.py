#!/usr/bin/env python3
import argparse
import random
import re
import sys


def roll_expression(expr: str):
    match = re.fullmatch(r"(\d*)d(\d+)", expr.strip().lower())
    if not match:
        raise ValueError("Invalid dice notation. Use format NdM, e.g. 2d6 or d20.")

    count_str, sides_str = match.groups()
    count = int(count_str) if count_str else 1
    sides = int(sides_str)

    if count < 1 or sides < 1:
        raise ValueError("Dice count and sides must both be positive integers.")

    rolls = [random.randint(1, sides) for _ in range(count)]
    return rolls, sum(rolls)


def main():
    parser = argparse.ArgumentParser(description="Simple CLI dice roller")
    parser.add_argument("dice", nargs="?", default="1d6", help="Dice notation, e.g. 2d6 or d20")
    args = parser.parse_args()

    try:
        rolls, total = roll_expression(args.dice)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    print(f"Rolling {args.dice}...")
    print("Rolls:", ", ".join(map(str, rolls)))
    print("Total:", total)


if __name__ == "__main__":
    main()
