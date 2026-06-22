"""Lightweight load testing harness to generate CSV and test COPY loader."""

import argparse
import csv
import os
import random
import string
from pathlib import Path

import pandas as pd


def gen_csv(path: Path, rows: int = 100000, cols: int = 6):
    path.parent.mkdir(parents=True, exist_ok=True)
    cols_names = [f"col{i}" for i in range(cols)]
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(cols_names)
        for _ in range(rows):
            row = [random.randint(0, 1000) for _ in range(cols - 1)] + [
                random.choice(["A", "B", "C"])
            ]
            writer.writerow(row)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--rows", type=int, default=100000)
    parser.add_argument("--out", type=str, default="data/raw/load_test.csv")
    args = parser.parse_args()
    gen_csv(Path(args.out), rows=args.rows)
    print(f"Generated {args.out} with {args.rows} rows")


if __name__ == "__main__":
    main()
