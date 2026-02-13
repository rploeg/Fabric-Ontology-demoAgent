"""Split ProductionCounterTelemetry.csv into chunks."""
import csv
from pathlib import Path

BASE = Path("/Users/remco/repo/Fabric-Ontology-demoAgent/TeaManufacturing-ISA95/Data/Eventhouse")
src = BASE / "ProductionCounterTelemetry.csv"
chunk_size = 1_500_000

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
            part_file = BASE / f"ProductionCounterTelemetry_part{part}.csv"
            fout = open(part_file, "w", newline="")
            writer = csv.writer(fout)
            writer.writerow(header)
        writer.writerow(row)
        rows_written += 1
    if fout:
        fout.close()

print(f"Done: {rows_written} rows -> {part} parts")
for f in sorted(BASE.glob("ProductionCounterTelemetry_part*.csv")):
    size_mb = f.stat().st_size / (1024 * 1024)
    rows = sum(1 for _ in open(f)) - 1
    print(f"  {f.name}: {rows} rows, {size_mb:.1f} MB")
