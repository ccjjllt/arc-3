"""Read-only public Kaggle source/metadata/output inventory; never executes notebook code."""
from pathlib import Path
import concurrent.futures, json, sys
from kaggle.api.kaggle_api_extended import KaggleApi
from kagglesdk.kernels.types.kernels_api_service import ApiGetKernelRequest, ApiListKernelFilesRequest
HERE=Path(__file__).resolve().parent
REFS=[
'dfranzen/arc-agi-3-milestone-2-solution',
'jingshuifu/arc3-m2-solution','jingshuifu/arc3-m2-solution-v2','jingshuifu/arc3-m2-solution-v3',
'heliosli/try-merging-it-you-might-get-lucky-and-win-gold',
'sujanmajhisuzan/arc-agi-3-m2-top-submission',
'habanwer/arcaid3-lexicon-view-dfranzen-m2',
'zhangyues0000/arc-agi-3-m2-franzen-fork',
'yukailiu/arc-agi-3-champion-solution',
'greenalgeria/arc-agi-3-milestone-final',
'amatlas/dfranzen-fork-d-prime',
'vladimiryakunin/df-wm',
'jeroencottaar/tufa-labs-duck-harness-june-30-milestone-winner',
'scottlegrand/taaf-flashnext-sheetu12b-0922',
'lordhansolo/built-on-tufa-labs-duck-harness-milestone-2',
'sirikilohit/arc-agi-3-duck-18-1gc-submit',
'prvsiyan/arc-agi-3-stock-taaf-action7-shadow',
]
REFS=sys.argv[1:] or REFS
api=KaggleApi(); api.authenticate()
def fetch(ref):
    d=HERE/ref.replace('/','__'); d.mkdir(exist_ok=True)
    owner,slug=ref.split('/')
    request=ApiGetKernelRequest(); request.user_name=owner; request.kernel_slug=slug
    try:
        with api.build_kaggle_client() as client:
            r=client.kernels.kernels_api_client.get_kernel(request)
        (d/'api-response.json').write_text(r.to_json(ignore_defaults=False))
        (d/'metadata.json').write_text(r.metadata.to_json(ignore_defaults=False))
        suffix='.ipynb' if r.blob.kernel_type.lower()=='notebook' else '.py'
        (d/('source'+suffix)).write_text(r.blob.source)
        version=r.metadata.current_version_number
        result={'ref':ref,'version':version}
        try:
            request=ApiListKernelFilesRequest(); request.user_name=owner; request.kernel_slug=slug; request.version_label=str(version); request.page_size=200
            with api.build_kaggle_client() as client:
                files=client.kernels.kernels_api_client.list_kernel_files(request)
            (d/'output-files.json').write_text(files.to_json(ignore_defaults=False))
            result['output_count']=len(files.files)
            result['output_bytes']=sum(f.size for f in files.files)
            result['output_next_page_token_present']=bool(files.next_page_token)
        except Exception as e:
            result['output_error_type']=type(e).__name__
            (d/'output-files-error.json').write_text(json.dumps({'error_type':type(e).__name__,'message':str(e)[:600]}))
        return result
    except Exception as e:
        return {'ref':ref,'error_type':type(e).__name__,'message':str(e)[:600]}
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
    rows=list(pool.map(fetch, REFS))
index_path=HERE/'fetch-index.json'
old=json.loads(index_path.read_text()) if index_path.exists() else []
merged={r['ref']:r for r in old}
merged.update({r['ref']:r for r in rows})
index_path.write_text(json.dumps(list(merged.values()),indent=2))
for row in rows: print(json.dumps(row))
