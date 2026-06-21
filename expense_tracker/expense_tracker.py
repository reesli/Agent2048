import argparse
import json
from pathlib import Path
from datetime import datetime

DATA_FILE = Path("expenses.json")


def load_expenses():
    if not DATA_FILE.exists():
        return []
    try:
        with DATA_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def save_expenses(expenses):
    with DATA_FILE.open("w", encoding="utf-8") as f:
        json.dump(expenses, f, indent=2)


def add_expense(description, amount):
    expenses = load_expenses()
    expense = {
        "description": description,
        "amount": amount,
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }
    expenses.append(expense)
    save_expenses(expenses)
    print(f"Added expense: {description} (${amount:.2f})")


def list_expenses():
    expenses = load_expenses()
    if not expenses:
        print("No expenses found.")
        return

    for index, expense in enumerate(expenses, start=1):
        print(
            f"{index}. {expense['description']} - ${expense['amount']:.2f} "
            f"({expense['created_at']})"
        )


def total_expenses():
    expenses = load_expenses()
    total = sum(expense.get("amount", 0) for expense in expenses)
    print(f"Total expenses: ${total:.2f}")


def build_parser():
    parser = argparse.ArgumentParser(description="Simple CLI expense tracker")
    subparsers = parser.add_subparsers(dest="command", required=True)

    add_parser = subparsers.add_parser("add", help="Add a new expense")
    add_parser.add_argument("description", help="Expense description")
    add_parser.add_argument("amount", type=float, help="Expense amount")

    subparsers.add_parser("list", help="List all expenses")
    subparsers.add_parser("total", help="Show total amount of expenses")

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "add":
        add_expense(args.description, args.amount)
    elif args.command == "list":
        list_expenses()
    elif args.command == "total":
        total_expenses()


if __name__ == "__main__":
    main()
