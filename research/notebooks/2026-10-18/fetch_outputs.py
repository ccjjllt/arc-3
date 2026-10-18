"""Read-only public output logs and inventories, exact version request, no artifacts executed."""
from pathlib import Path
import json, concurrent.futures
from kaggle.api.kaggle_api_extended import KaggleApi
from kagglesdk.kernels.types.kernels_api_service import ApiListKernelSessionOutputRequest
HERE=Path(__file__).resolve().parent
api=KaggleApi(); api.authenticate()
def fetch(d):
    m=json.loads((d/'metadata.json').read_text()); owner,slug=m['ref'].split('/')
    request=ApiListKernelSessionOutputRequest(); request.user_name=owner; request.kernel_slug=slug; request.version_label=str(m['currentVersionNumber']); request.page_size=200
    row={'ref':m['ref'],'requested_version':m['currentVersionNumber']}
    try:
        with api.build_kaggle_client() as client:
            res=client.kernels.kernels_api_client.list_kernel_session_output(request)
        data=res.to_dict(ignore_defaults=False)
        # Signed download URLs are not evidence and are not persisted.
        for f in data.get('files',[]): f.pop('url',None)
        log=data.pop('log',None)
        if log: (d/'public-run.log').write_text(log)
        (d/'output-session.json').write_text(json.dumps(data,indent=2))
        row.update({'files':len(data.get('files',[])),'log_chars':len(log or ''),'next_page_token_present':bool(res.next_page_token)})
    except Exception as e:
        row.update({'error_type':type(e).__name__,'message':str(e)[:500]})
    return row
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool: rows=list(pool.map(fetch,[d for d in HERE.iterdir() if (d/'metadata.json').exists()]))
(HERE/'output-index.json').write_text(json.dumps(rows,indent=2))
for row in rows: print(json.dumps(row))
