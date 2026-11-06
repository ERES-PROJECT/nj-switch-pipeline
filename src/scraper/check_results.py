import pandas as pd
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
df = pd.read_csv(PROJECT_ROOT / "data/demo_results.csv", dtype=str)
print(f'Total rows: {len(df)}')
print()
for s, g in df.groupby('supplier', sort=False):
    print(f'{s}: {len(g)} rows')
    for _, r in g.iterrows():
        plan = r.get('plan_name','')
        rate = r.get('rate','')
        term = r.get('term_months','')
        src = r.get('data_source','')
        curl = r.get('contract_url','')
        print(f'  plan={plan!r}  rate={rate}  term={term}  src={src}  contract_url={curl}')
