#!/usr/bin/env python3
import sys

UNITS_TO_METERS = {
    "mm": 0.001,
    "cm": 0.01,
    "m": 1.0,
    "km": 1000.0,
    "in": 0.0254,
    "ft": 0.3048,
    "yd": 0.9144,
    "mi": 1609.344,
}


def format_number(value: float) -> str:
    if value.is_integer():
        return str(int(value))
    return f"{value:.10g}"


def main() -> int:
    if len(sys.argv) != 4:
        print("Usage: python unit_converter.py <value> <from_unit> <to_unit>", file=sys.stderr)
        print("Supported units: mm, cm, m, km, in, ft, yd, mi", file=sys.stderr)
        return 1

    value_text, from_unit, to_unit = sys.argv[1], sys.argv[2].lower(), sys.argv[3].lower()

    try:
        value = float(value_text)
    except ValueError:
        print(f"Error: invalid numeric value '{value_text}'", file=sys.stderr)
        return 1

    if from_unit not in UNITS_TO_METERS:
        print(f"Error: unsupported from_unit '{from_unit}'", file=sys.stderr)
        return 1

    if to_unit not in UNITS_TO_METERS:
        print(f"Error: unsupported to_unit '{to_unit}'", file=sys.stderr)
        return 1

    meters = value * UNITS_TO_METERS[from_unit]
    converted = meters / UNITS_TO_METERS[to_unit]
    print(format_number(converted))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
