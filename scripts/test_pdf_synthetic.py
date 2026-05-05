"""Smoke-test PDF generation with synthetic data — no real CSV needed."""
import pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

import numpy as np
import pandas as pd
from analysis.decay_engine import normalise_dataframe, run_analysis, QCParams
from utils.pdf_export import generate_pdf

rng = np.random.default_rng(42)

def _house(name, ach=0.4, c0=1800.0, n_days=5):
    rows = []
    for d in range(n_days):
        base = pd.Timestamp("2026-02-10", tz="UTC") + pd.Timedelta(days=d)
        # ambient pre-period
        for m in range(60):
            rows.append((name, base + pd.Timedelta(minutes=m), 420 + rng.normal(0, 5)))
        # rise
        for i, m in enumerate(range(60, 90)):
            rows.append((name, base + pd.Timedelta(minutes=m), 420 + (c0 - 420) * i / 30))
        # decay
        t = np.arange(240) / 60
        co2 = (c0 - 420) * np.exp(-ach * t) + 420 + rng.normal(0, 8, 240)
        for i, m in enumerate(range(90, 330)):
            rows.append((name, base + pd.Timedelta(minutes=m), float(np.clip(co2[i], 420, None))))
    return rows

rows = []
for house, ach in [("RIAQ_ICE_001", 0.30), ("RIAQ_ICE_002", 0.45),
                   ("RIAQ_ICE_003", 0.22), ("RIAQ_ICE_004", 0.60)]:
    rows.extend(_house(house, ach=ach))

raw = pd.DataFrame(rows, columns=["HouseNo.", "dtm", "co2, ppm"])
raw["dtm"] = raw["dtm"].dt.strftime("%d-%b-%Y %H:%M:%S+00:00")
raw["co2, ppm"] = raw["co2, ppm"].round().astype(int)

df = normalise_dataframe(raw)
params = QCParams()
results, rejected = run_analysis(df, params)
print(f"Results: {len(results)}  Rejected: {len(rejected)}")

if len(results) == 0:
    print("No results — cannot generate PDF")
    sys.exit(1)

print("Generating PDF (English)...")
pdf_en = generate_pdf(results, rejected, df, params, "en")
out = pathlib.Path(__file__).parent.parent / "test_output_en.pdf"
out.write_bytes(pdf_en)
print(f"  EN: {len(pdf_en)//1024} KB -> {out}")

print("Generating PDF (Icelandic)...")
pdf_is = generate_pdf(results, rejected, df, params, "is")
out_is = pathlib.Path(__file__).parent.parent / "test_output_is.pdf"
out_is.write_bytes(pdf_is)
print(f"  IS: {len(pdf_is)//1024} KB -> {out_is}")

print("Done.")
