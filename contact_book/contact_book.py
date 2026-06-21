import argparse
import json
from pathlib import Path

DATA_FILE = Path("contacts.json")


def load_contacts():
    if not DATA_FILE.exists():
        return []
    try:
        with DATA_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def save_contacts(contacts):
    with DATA_FILE.open("w", encoding="utf-8") as f:
        json.dump(contacts, f, indent=2)


def add_contact(name, phone, email):
    contacts = load_contacts()
    contacts.append({"name": name, "phone": phone, "email": email})
    save_contacts(contacts)
    print(f"Added contact: {name}")


def list_contacts():
    contacts = load_contacts()
    if not contacts:
        print("No contacts found.")
        return

    for index, contact in enumerate(contacts, start=1):
        print(f"{index}. {contact['name']} | Phone: {contact['phone']} | Email: {contact['email']}")


def search_contacts(query):
    contacts = load_contacts()
    query_lower = query.lower()
    matches = [
        contact for contact in contacts
        if query_lower in contact["name"].lower()
        or query_lower in contact["phone"].lower()
        or query_lower in contact["email"].lower()
    ]

    if not matches:
        print("No matching contacts found.")
        return

    for index, contact in enumerate(matches, start=1):
        print(f"{index}. {contact['name']} | Phone: {contact['phone']} | Email: {contact['email']}")


def main():
    parser = argparse.ArgumentParser(description="Simple CLI contact book")
    subparsers = parser.add_subparsers(dest="command")

    add_parser = subparsers.add_parser("add", help="Add a new contact")
    add_parser.add_argument("name", help="Contact name")
    add_parser.add_argument("phone", help="Contact phone number")
    add_parser.add_argument("email", help="Contact email address")

    subparsers.add_parser("list", help="List all contacts")

    search_parser = subparsers.add_parser("search", help="Search contacts")
    search_parser.add_argument("query", help="Search by name, phone, or email")

    args = parser.parse_args()

    if args.command == "add":
        add_contact(args.name, args.phone, args.email)
    elif args.command == "list":
        list_contacts()
    elif args.command == "search":
        search_contacts(args.query)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
