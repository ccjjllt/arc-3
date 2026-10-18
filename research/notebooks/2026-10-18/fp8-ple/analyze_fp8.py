"""Recompute config, index and public LFS metadata comparison. Never loads tensors."""
from pathlib import Path
import json,hashlib
H=Path(__file__).resolve().parent
def diff(a,b,path=''):
 if isinstance(a,dict) and isinstance(b,dict):
  return sum((diff(a.get(k,'<MISSING>'),b.get(k,'<MISSING>'),path+'.'+k) for k in sorted(a.keys()|b.keys())),[])
 return [] if a==b else [{'path':path,'fp8':a,'bf16':b}]
config={s:json.loads((H/s/'config.json').read_text()) for s in ['albucino','Intel']}
indexes={s:json.loads((H/s/'model.safetensors.index.json').read_text()) for s in config}
out={'config_differences':diff(config['albucino'],config['Intel'])}
for s in config:
 j=json.loads((H/s/'model-api.json').read_text());wm=indexes[s]['weight_map']
 out[s]={'revision':j['sha'],'tensor_count':len(wm),'payload_size':indexes[s].get('metadata',{}),'ple_tensors':{k:v for k,v in wm.items() if '.ple_embedding.ngram_embedding.' in k},'lfs':{x['rfilename']:x.get('lfs',{}) for x in j['siblings'] if x['rfilename'].endswith('.safetensors')}}
out['identical_shard_hashes']=[{'fp8_file':an,'bf16_file':bn,'sha256':av['sha256'],'size':av.get('size')} for an,av in out['albucino']['lfs'].items() for bn,bv in out['Intel']['lfs'].items() if av.get('sha256') and av.get('sha256')==bv.get('sha256')]
a,b=[indexes[s]['weight_map'] for s in ['albucino','Intel']]
out['tensor_keys_added']=sorted(a.keys()-b.keys());out['tensor_keys_removed']=sorted(b.keys()-a.keys())
out['index_warning']='Intel index metadata.total_size differs from current safetensors file totals; do not use it as physical download size.'
out['metadata_only']=True;out['local_tensor_hashes_recomputed']=False;out['kaggle_mirror_tensor_hashes_verified']=False
out['source_files_sha256']={str(p.relative_to(H)):hashlib.sha256(p.read_bytes()).hexdigest() for p in H.rglob('*') if p.is_file() and p.name not in ['comparison.json','analyze_fp8.py']}
(H/'comparison.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps({'config_diff_count':len(out['config_differences']),'same_lfs_shards':len(out['identical_shard_hashes']),'same_lfs_bytes':sum(x['size'] for x in out['identical_shard_hashes']),'added_keys':len(out['tensor_keys_added']),'removed_keys':len(out['tensor_keys_removed'])}))
