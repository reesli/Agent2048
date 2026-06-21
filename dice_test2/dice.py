#!/usr/bin/env python3
import argparse
import random
import sys


def roll_dice(count: int, sides: int) -> list[int]:
    return [random.randint(1, sides) for _ in range(count)]


def main() -> int:
    parser = argparse.ArgumentParser(description="Simple CLI dice roller")
    parser.add_argument("-n", "--number", type=int, default=1, help="number of dice to roll (default: 1)")
    parser.add_argument("-s", "--sides", type=int, default=6, help="number of sides per die (default: 6)")
    args = parser.parse_args()

    if args.number < 1:
        print("Error: number of dice must be at least 1", file=sys.stderr)
        return 1
    if args.sides < 2:
        print("Error: number of sides must be at least 2", file=sys.stderr)
        return 1

    rolls = roll_dice(args.number, args.sides)
    print("Rolls:", ", ".join(map(str, rolls)))
    print("Total:", sum(rolls))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
