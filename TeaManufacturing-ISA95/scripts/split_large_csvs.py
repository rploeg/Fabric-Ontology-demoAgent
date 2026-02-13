"""Split large Eventhouse CSVs into chunks for .ingest ingestion (<200MB each)."""
import csv
import os
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent / "Data" / "Eventhouse"

splits = [
    ("MachineStateTelemetry.csv", 2_000_000),
    ("ProductionCounterTelemetry.csv", 1_500_000),
]

for filename, chunk_size in splits:
    src = BASE / filename
    if not src.exists():
        print(f"SKIP: {src} not found")
        continue

    with open(src, "r") as fin:
        reader = csv.reader(fin)
        header = next(reader)

        part = 0
        rows_written = 0
        writer = None
        fout = None

        for row in reader:
            if rows_written % chunk_size == 0:
                if fout:
                    fout.close()
                part += 1
                stem = src.stem
                part_file = BASE / f"{stem}_part{part}.csv"
                fout = open(part_file, "w", newline="")
                writer = csv.writer(fout)
                writer.writerow(header)
            writer.writerow(row)
            rows_written += 1

        if fout:
            fout.close()

    print(f"{filename}: {rows_written} rows -> {part} parts of ~{chunk_size} rows")

# Show sizes
print("\nPart files:")
for f in sorted(BASE.glob("*_part*.csv")):
    size_mb = f.stat().st_size / (1024 * 1024)
    print(f"  {f.name}: {size_mb:.1f} MB")
