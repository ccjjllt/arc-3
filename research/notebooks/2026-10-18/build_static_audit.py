"""Static JSON/cell/diff audit only: no remote source imports or execution."""
from pathlib import Path
import json, hashlib, difflib, ast, base64, zlib, gzip
HERE=Path(__file__).resolve().parent
OLD=HERE.parent/'2026-10-17'
def sha(b): return hashlib.sha256(b).hexdigest()
def cells(p):
    j=json.loads(p.read_text()); return [''.join(c.get('source','')) for c in j['cells']]
rows=[]
for d in sorted(HERE.iterdir()):
    p=d/'source.ipynb'
    if not p.is_file(): continue
    m=json.loads((d/'metadata.json').read_text()); n=json.loads(p.read_text()); c=cells(p)
    (d/'cells').mkdir(exist_ok=True)
    for i,(source,cell) in enumerate(zip(c,n['cells'])):
        (d/'cells'/f'{i:03}.txt').write_text(source)
    (d/'readable.py').write_text('\n\n'.join(f'# CELL {i} ({n["cells"][i]["cell_type"]})\n'+s for i,s in enumerate(c)))
    row={'ref':m['ref'],'version':m['currentVersionNumber'],'source_sha256':sha(p.read_bytes()),'cell_source_sha256':sha('\n'.join(c).encode()),'cells':len(c),'outputs_count':sum(len(x.get('outputs',[])) for x in n['cells']),'model_sources':m.get('modelDataSources',[]),'score_bound_to_source':None}
    candidates=[OLD/d.name/'source.ipynb', HERE.parent/(d.name+'.ipynb')]
    if d.name=='jingshuifu__arc3-m2-solution': candidates.insert(0,HERE.parent/'2026-10-13/jingshuifu-m2/mcp-source.ipynb')
    old=next((x for x in candidates if x.is_file()),None)
    if old:
        oc=cells(old); row.update({'compared_to':str(old.relative_to(HERE.parent)),'same_cell_sources':oc==c,'changed_cells_zero_based':[i for i in range(max(len(oc),len(c))) if (oc[i] if i<len(oc) else None)!=(c[i] if i<len(c) else None)]})
        (d/'source.diff').write_text(''.join(difflib.unified_diff('\n\n'.join(oc).splitlines(True),'\n\n'.join(c).splitlines(True),fromfile=str(old.relative_to(HERE.parent)),tofile=str(p.relative_to(HERE.parent)))))
    else:
        oc=cells(HERE/'dfranzen__arc-agi-3-milestone-2-solution/source.ipynb')
        row['compared_to_baseline']='2026-10-18/dfranzen__arc-agi-3-milestone-2-solution/source.ipynb'
        (d/'baseline.diff').write_text(''.join(difflib.unified_diff('\n\n'.join(oc).splitlines(True),'\n\n'.join(c).splitlines(True),fromfile='Franzen v3',tofile=m['ref'])))
    assets=d/'extracted-assets'; assets.mkdir(exist_ok=True)
    for i,s in enumerate(c):
        try: tree=ast.parse(s)
        except SyntaxError: continue
        for node in ast.walk(tree):
            if not isinstance(node,(ast.Assign,ast.AnnAssign)): continue
            val=node.value
            try: value=ast.literal_eval(val)
            except (ValueError,TypeError): continue
            targets=node.targets if isinstance(node,ast.Assign) else [node.target]
            name=next((t.id for t in targets if isinstance(t,ast.Name)),None)
            if not name or not isinstance(value,(str,bytes)): continue
            if isinstance(value,bytes): value=value.decode(errors='replace')
            data=None; kind=None
            if len(value)>200:
                if value.startswith('diff --git'): data=value;kind='patch'
                elif len(value)>1000 and '\n' not in value:
                    for dec in (lambda x:zlib.decompress(base64.b64decode(x)),lambda x:gzip.decompress(base64.b64decode(x)),lambda x:zlib.decompress(base64.b85decode(x))):
                        try: data=dec(value).decode();kind='decoded';break
                        except Exception: pass
                elif any(x in name.lower() for x in ('source','patch','code')) and '\n' in value: data=value;kind='literal'
            if data: (assets/f'cell{i:03}-{name}.{kind}.txt').write_text(data)
    rows.append(row)
(HERE/'audit.json').write_text(json.dumps({'method':'Kaggle public API get_kernel, static literal extraction and source diffs. No notebook execution. Numerical score not returned.','notebooks':rows},ensure_ascii=False,indent=2)+'\n')
for r in rows: print(r['ref'],r['version'],r.get('same_cell_sources','NEW'),r.get('changed_cells_zero_based'),r['outputs_count'],r['source_sha256'][:12])
