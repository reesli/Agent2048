import argparse
import json
from pathlib import Path

NOTES_FILE = Path("notes.json")


def load_notes():
    if not NOTES_FILE.exists():
        return []
    try:
        with NOTES_FILE.open("r", encoding="utf-8") as file:
            data = json.load(file)
            return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def save_notes(notes):
    with NOTES_FILE.open("w", encoding="utf-8") as file:
        json.dump(notes, file, indent=2)


def add_note(content):
    notes = load_notes()
    next_id = max((note.get("id", 0) for note in notes), default=0) + 1
    notes.append({"id": next_id, "content": content})
    save_notes(notes)
    print(f"Added note {next_id}.")


def list_notes():
    notes = load_notes()
    if not notes:
        print("No notes found.")
        return

    for note in notes:
        print(f"{note['id']}: {note['content']}")


def delete_note(note_id):
    notes = load_notes()
    filtered_notes = [note for note in notes if note.get("id") != note_id]

    if len(filtered_notes) == len(notes):
        print(f"Note {note_id} not found.")
        return

    save_notes(filtered_notes)
    print(f"Deleted note {note_id}.")


def main():
    parser = argparse.ArgumentParser(description="Simple CLI notes app")
    subparsers = parser.add_subparsers(dest="command")

    add_parser = subparsers.add_parser("add", help="Add a new note")
    add_parser.add_argument("content", help="Note content")

    subparsers.add_parser("list", help="List all notes")

    delete_parser = subparsers.add_parser("delete", help="Delete a note by ID")
    delete_parser.add_argument("id", type=int, help="ID of the note to delete")

    args = parser.parse_args()

    if args.command == "add":
        add_note(args.content)
    elif args.command == "list":
        list_notes()
    elif args.command == "delete":
        delete_note(args.id)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
