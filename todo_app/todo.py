import argparse
import json
from pathlib import Path

DATA_FILE = Path("todos.json")


def load_tasks():
    if not DATA_FILE.exists():
        return []
    try:
        with DATA_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
    except (json.JSONDecodeError, OSError):
        pass
    return []


def save_tasks(tasks):
    with DATA_FILE.open("w", encoding="utf-8") as f:
        json.dump(tasks, f, indent=2)


def add_task(description):
    tasks = load_tasks()
    tasks.append({"title": description, "done": False})
    save_tasks(tasks)
    print(f"Added: {description}")


def list_tasks():
    tasks = load_tasks()
    if not tasks:
        print("No tasks found.")
        return

    for index, task in enumerate(tasks, start=1):
        status = "x" if task.get("done") else " "
        print(f"{index}. [{status}] {task.get('title', '')}")


def mark_done(index):
    tasks = load_tasks()
    if index < 1 or index > len(tasks):
        print("Invalid task number.")
        return

    task = tasks[index - 1]
    task["done"] = True
    save_tasks(tasks)
    print(f"Completed: {task.get('title', '')}")


def build_parser():
    parser = argparse.ArgumentParser(description="Simple CLI todo list app")
    subparsers = parser.add_subparsers(dest="command", required=True)

    add_parser = subparsers.add_parser("add", help="Add a new task")
    add_parser.add_argument("description", help="Task description")

    subparsers.add_parser("list", help="List all tasks")

    done_parser = subparsers.add_parser("done", help="Mark a task as done")
    done_parser.add_argument("index", type=int, help="Task number to mark done")

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "add":
        add_task(args.description)
    elif args.command == "list":
        list_tasks()
    elif args.command == "done":
        mark_done(args.index)


if __name__ == "__main__":
    main()
