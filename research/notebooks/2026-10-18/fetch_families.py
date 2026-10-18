"""Read-only author notebook and model listings; weights are not downloaded."""
import json, concurrent.futures
from pathlib import Path
from kaggle.api.kaggle_api_extended import KaggleApi
HERE=Path(__file__).resolve().parent
api=KaggleApi(); api.authenticate()
owners=['dfranzen','jingshuifu','jeroencottaar','scottlegrand','lordhansolo','sirikilohit']
def fetch(owner):
    row={'owner':owner}
    try:
        r=api.kernels_list_with_response(competition='arc-prize-2026-arc-agi-3',user=owner,sort_by='dateRun',page_size=20)
        (HERE/f'author-{owner}.json').write_text(r.to_json(ignore_defaults=False))
        row['notebook_list']='saved'
    except Exception as e: row['notebook_error']=type(e).__name__
    try:
        models=api.model_list(owner=owner,sort_by='createTime',page_size=100)
        (HERE/f'models-{owner}.json').write_text(json.dumps([m.to_dict(ignore_defaults=False) for m in models],indent=2))
        row['models']=len(models)
    except Exception as e: row['model_error']=type(e).__name__
    return row
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool: rows=list(pool.map(fetch,owners))
(HERE/'families-index.json').write_text(json.dumps(rows,indent=2))
for r in rows:print(json.dumps(r))
