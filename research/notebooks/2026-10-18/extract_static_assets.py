"""Extract patch additions and string literals; never executes author code."""
from pathlib import Path
import ast,json,zlib,base64,hashlib
H=Path(__file__).resolve().parent
for d in H.iterdir():
 p=d/'source.ipynb'
 if not p.is_file():continue
 for i,c in enumerate(json.loads(p.read_text())['cells']):
  s=''.join(c.get('source',''))
  a=d/'extracted-assets';a.mkdir(exist_ok=True)
  if s.startswith('%%writefile ') and 'diff --git' in s:
   patch=s.split('\n',1)[1];(a/f'cell{i:03}.patch').write_text(patch)
   for chunk in patch.split('diff --git ')[1:]:
    if '--- /dev/null\n' not in chunk:continue
    name=chunk.split('\n',1)[0].split(' b/',1)[1]
    pp=Path(name)
    if pp.is_absolute() or '..' in pp.parts:continue
    lines=chunk.splitlines(True)
    content=''.join(x[1:] for x in lines if x.startswith('+') and not x.startswith('+++'))
    dest=a/'patch-files'/pp;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(content)
  try:t=ast.parse(s)
  except SyntaxError:continue
  for node in ast.walk(t):
   if isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute) and node.func.attr=='write_text' and node.args:
    try: value=ast.literal_eval(node.args[0])
    except (ValueError,TypeError):continue
    if isinstance(value,str) and len(value)>1000:
     (a/f'cell{i:03}-write_text-line{node.lineno}.py').write_text(value)
# Latest Action7 v22 payload: decode its final static JSON asset package, no historical launcher execution.
d=H/'prvsiyan__arc-agi-3-stock-taaf-action7-shadow'
s=(d/'cells/116.txt').read_text();t=ast.parse(s)
vals={n.targets[0].id:n.value for n in t.body if isinstance(n,ast.Assign) and len(n.targets)==1 and isinstance(n.targets[0],ast.Name)}
raw=base64.b64decode(ast.literal_eval(vals['_compressed'].args[0]),validate=True)
payload=zlib.decompress(raw);assets=json.loads(payload)
index=[]
for name,source in assets.items():
 p=Path(name)
 if p.is_absolute() or '..' in p.parts:raise ValueError(name)
 dest=d/'extracted-assets/v22-new-files'/p;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(source)
 index.append({'name':name,'sha256':hashlib.sha256(source.encode()).hexdigest()})
(d/'extracted-assets/v22-new-files/index.json').write_text(json.dumps(index,indent=2))
print('Action7 final layer files',len(index))
