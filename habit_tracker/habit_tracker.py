#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

DATA_FILE = Path("habits.json")


def load_habits():
    if not DATA_FILE.exists():
        return []
    try:
        with DATA_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def save_habits(habits):
    with DATA_FILE.open("w", encoding="utf-8") as f:
        json.dump(habits, f, indent=2)


def add_habit(name):
    habits = load_habits()
    habits.append({"name": name, "done": False})
    save_habits(habits)
    print(f"Added habit: {name}")


def list_habits():
    habits = load_habits()
    if not habits:
        print("No habits found.")
        return
    for i, habit in enumerate(habits, start=1):
        status = "[x]" if habit.get("done") else "[ ]"
        print(f"{i}. {status} {habit.get('name', 'Unnamed habit')}")


def mark_done(index):
    habits = load_habits()
    if index < 1 or index > len(habits):
        print("Invalid habit number.")
        return
    habits[index - 1]["done"] = True
    save_habits(habits)
    print(f"Marked habit as done: {habits[index - 1].get('name', 'Unnamed habit')}")


def build_parser():
    parser = argparse.ArgumentParser(description="Simple CLI habit tracker")
    subparsers = parser.add_subparsers(dest="command")

    add_parser = subparsers.add_parser("add", help="Add a new habit")
    add_parser.add_argument("name", help="Habit name")

    subparsers.add_parser("list", help="List all habits")

    done_parser = subparsers.add_parser("done", help="Mark a habit as done")
    done_parser.add_argument("index", type=int, help="Habit number to mark done")

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "add":
        add_habit(args.name)
    elif args.command == "list":
        list_habits()
    elif args.command == "done":
        mark_done(args.index)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
