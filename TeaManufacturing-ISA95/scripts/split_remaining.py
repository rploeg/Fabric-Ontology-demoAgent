"""
Split full_data CSVs into parts, skipping the seed rows already deployed.

The seed files (first 75K/50K rows) are deployed by the automation tool.
This script creates part files from the REMAINING rows only.
"""
import csv
from pathlib import Path

BASE = Path("/Users/remco/repo/Fabric-Ontology-demoAgent/TeaManufacturing-ISA95/Data/Eventhouse")
FULL = BASE / "full_data"

splits = [
    ("MachineStateTelemetry.csv", 75000, 1_500_000),   # skip 75K seed, 1.5M per part
    ("ProductionCounterTelemetry.csv", 50000, 1_500_000),  # skip 50K seed, 1.5M per part
]

for filename, skip_rows, chunk_size in splits:
    src = FULL / filename
    if not src.exists():
        print(f"SKIP: {src} not found")
        continue

    with open(src, "r") as fin:
        reader = csv.reader(fin)
        header = next(reader)

        # Skip seed rows
        for i in range(skip_rows):
            next(reader)
        print(f"{filename}: skipped {skip_rows} seed rows")

        part = 0
        rows_in_part = 0
        rows_total = 0
        writer = None
        fout = None

        for row in reader:
            if rows_in_part % chunk_size == 0:
                if fout:
                    fout.close()
                    print(f"  {stem}_part{part}.csv: {rows_in_part} rows")
                part += 1
                stem = filename.replace(".csv", "")
                part_file = BASE / f"{stem}_part{part}.csv"
                fout = open(part_file, "w", newline="")
                writer = csv.writer(fout)
                writer.writerow(header)
                rows_in_part = 0

            writer.writerow(row)
            rows_in_part += 1
            rows_total += 1

        if fout:
            fout.close()
            print(f"  {stem}_part{part}.csv: {rows_in_part} rows")

    print(f"  Total remaining: {rows_total} rows in {part} parts\n")

# Show sizes
print("Part files:")
for f in sorted(BASE.glob("*_part*.csv")):
    size_mb = f.stat().st_size / (1024 * 1024)
    print(f"  {f.name}: {size_mb:.1f} MB")
