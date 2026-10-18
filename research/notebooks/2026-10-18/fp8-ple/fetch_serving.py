"""Read public pinned serving sources only."""
from pathlib import Path
import requests,json
H=Path(__file__).resolve().parent/'pennyroyal';H.mkdir(exist_ok=True)
repo='jpezzulli/sglang-rtxpro6000';rev='d00d88efc8d6281b12be4f4073126aec95038c55'
r=requests.get(f'https://api.github.com/repos/{repo}/git/trees/{rev}',params={'recursive':'1'},timeout=40);r.raise_for_status();tree=r.json();(H/'tree.json').write_text(json.dumps(tree,indent=2))
paths=[x['path'] for x in tree['tree'] if x['type']=='blob' and any(t in x['path'].lower() for t in ['ple.py','ple_embedding','qwen3_8','qwen3p8','qwen38','qwen3_5','qwen3p5']) and x['path'].endswith('.py')]
for p in paths:
 r=requests.get(f'https://raw.githubusercontent.com/{repo}/{rev}/{p}',timeout=40);r.raise_for_status();d=H/p;d.parent.mkdir(exist_ok=True,parents=True);d.write_bytes(r.content)
print(paths)
