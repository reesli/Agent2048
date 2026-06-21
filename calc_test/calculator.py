#!/usr/bin/env python3
import argparse
import sys


def add(a, b):
    return a + b


def sub(a, b):
    return a - b


def mul(a, b):
    return a * b


def div(a, b):
    if b == 0:
        raise ValueError("division by zero")
    return a / b


def build_parser():
    parser = argparse.ArgumentParser(description="Simple CLI calculator")
    subparsers = parser.add_subparsers(dest="command", required=True)

    for name in ("add", "sub", "mul", "div"):
        cmd = subparsers.add_parser(name)
        cmd.add_argument("a", type=float)
        cmd.add_argument("b", type=float)

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    operations = {
        "add": add,
        "sub": sub,
        "mul": mul,
        "div": div,
    }

    try:
        result = operations[args.command](args.a, args.b)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    if result.is_integer():
        print(int(result))
    else:
        print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
