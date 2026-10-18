"""Fetch public model config/index/readme only; no tensor downloads or imports."""
from pathlib import Path
import json,requests
from kaggle.api.kaggle_api_extended import KaggleApi
H=Path(__file__).resolve().parent
api=KaggleApi();api.authenticate()
for name in ['dfranzen/albucino-qwen3.8-flash-next-w4a16-fp8ple/Transformers/default/1','dfranzen/intel-qwen3.8-flash-next-w4a16-autoround/Transformers/default/1']:
 try:
  r=api.model_instance_version_files(name,page_size=200)
  (H/(name.split('/')[1]+'-kaggle-files.json')).write_text(r.to_json(ignore_defaults=False))
 except Exception as e:print('kaggle_files',type(e).__name__)
for repo in ['albucino/Qwen3.8-Flash-Next-W4A16-FP8PLE','Intel/Qwen3.8-Flash-Next-W4A16-AutoRound']:
 d=H/repo.split('/')[0];d.mkdir(exist_ok=True)
 r=requests.get('https://huggingface.co/api/models/'+repo,params={'blobs':'true'},timeout=30);r.raise_for_status();j=r.json();(d/'model-api.json').write_text(json.dumps(j,indent=2));revision=j['sha']
 names=[x['rfilename'] for x in j['siblings'] if x['rfilename'] in {'config.json','model.safetensors.index.json','README.md','quantize_config.json','quantization_config.json'}]
 for name in names:
  r=requests.get(f'https://huggingface.co/{repo}/resolve/{revision}/{name}',timeout=40);r.raise_for_status()
  if len(r.content)>80000000:raise ValueError('unexpected metadata size')
  (d/name).write_bytes(r.content)
 print(repo,revision,names)
