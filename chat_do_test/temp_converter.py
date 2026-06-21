#!/usr/bin/env python3
import argparse
import sys


def c_to_f(celsius: float) -> float:
    return (celsius * 9 / 5) + 32


def f_to_c(fahrenheit: float) -> float:
    return (fahrenheit - 32) * 5 / 9


def main() -> int:
    parser = argparse.ArgumentParser(description="Simple temperature converter")
    parser.add_argument("value", type=float, help="Temperature value to convert")
    parser.add_argument("--from-unit", choices=["C", "F", "c", "f"], required=True, help="Source unit: C or F")
    parser.add_argument("--to-unit", choices=["C", "F", "c", "f"], required=True, help="Target unit: C or F")
    args = parser.parse_args()

    from_unit = args.from_unit.upper()
    to_unit = args.to_unit.upper()

    if from_unit == to_unit:
        result = args.value
    elif from_unit == "C" and to_unit == "F":
        result = c_to_f(args.value)
    elif from_unit == "F" and to_unit == "C":
        result = f_to_c(args.value)
    else:
        print("Unsupported conversion", file=sys.stderr)
        return 1

    print(f"{args.value:.2f}°{from_unit} = {result:.2f}°{to_unit}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
