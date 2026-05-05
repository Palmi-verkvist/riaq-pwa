import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import pandas as pd
from analysis.decay_engine import normalise_dataframe, run_analysis, QCParams
from utils.pdf_export import generate_pdf

import pathlib
_ROOT = pathlib.Path(__file__).parent.parent
raw = pd.read_csv(_ROOT / 'Stofa_CO2.csv', low_memory=False)
raw = raw.loc[:, ~raw.columns.str.startswith('Unnamed')]
raw = raw.dropna(subset=['HouseNo.', 'dtm', 'co2, ppm'])
df = normalise_dataframe(raw)
params = QCParams()
results, rejected = run_analysis(df, params)
print(f'Results: {len(results)}, Rejected: {len(rejected)}')
print('Generating PDF...')
pdf_bytes = generate_pdf(results, rejected, df, params, 'en')
print(f'PDF generated: {len(pdf_bytes)//1024} KB')
with open(_ROOT / 'test_output.pdf', 'wb') as f:
    f.write(pdf_bytes)
print('Saved to test_output.pdf')
