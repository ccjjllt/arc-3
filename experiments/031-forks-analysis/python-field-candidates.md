# 031 Python字段访问候选

以下为静态语法命中。必须阅读真实工具输出、函数调用位置及后续行为；不能据此自动宣称自然采用。

## ft09-0d8bbf25 A · call_a3f1e660346143fa879d9604

请求日志：runs/031-segmentation-forks/segmentation_forks_A/ft09-0d8bbf25_A_requests.jsonl:5；工具结果存在：True；返回码0且无error：True。

```python

rows=[]
for h in history:
    res = h.result or {}
    rows.append((res.get('action_num'), res.get('level'), res.get('score'), (h.action or '')))
for r in rows[-24:]: print(r)
print('last call score', (last_action_call_result or {}).get('score'))
# bar state now
for n in current_frame.segmentation['nodes']:
    if n['boundary'][0][0]>=62:
        b=n['boundary']; cs=[p[1] for p in b]
        print('bar', n['color'], n['pixels'], min(cs), max(cs))

```

静态访问：`[{"field": "boundary", "kind": "subscript_load", "code_line": 11, "expression": "n['boundary']", "enclosing_scopes": ["If", "For"]}, {"field": "boundary", "kind": "subscript_load", "code_line": 10, "expression": "n['boundary']", "enclosing_scopes": ["If", "For"]}]`

```json
{
  "first_snapshot_line": 5,
  "content_sha256": "0dc6da84929479fa150b1df019df316863927739b20e873ce8737e7409609497",
  "content_chars": 986,
  "payload": {
    "tool": "python",
    "returncode": 0,
    "stdout": "(5, 2, 1, 'MOUSE(row=16, col=22)')\n(6, 2, 1, 'MOUSE(row=24, col=22)')\n(7, 2, 1, 'MOUSE(row=24, col=38)')\n(8, 2, 1, 'MOUSE(row=32, col=22)')\n(9, 2, 1, 'MOUSE(row=32, col=38)')\n(10, 2, 1, 'MOUSE(row=48, col=22)')\n(11, 3, 2, 'MOUSE(row=48, col=30)')\n(12, 3, 2, 'MOUSE(row=6, col=22)')\n(13, 3, 2, 'MOUSE(row=6, col=30)')\n(14, 3, 2, 'MOUSE(row=6, col=38)')\n(15, 3, 2, 'MOUSE(row=14, col=22)')\n(16, 3, 2, 'MOUSE(row=22, col=14)')\n(17, 3, 2, 'MOUSE(row=22, col=30)')\n(18, 3, 2, 'MOUSE(row=30, col=14)')\n(19, 3, 2, 'MOUSE(row=30, col=46)')\n(20, 3, 2, 'MOUSE(row=38, col=30)')\n(21, 3, 2, 'MOUSE(row=38, col=46)')\n(22, 3, 2, 'MOUSE(row=46, col=22)')\n(23, 3, 2, 'MOUSE(row=46, col=38)')\n(24, 3, 2, 'MOUSE(row=54, col=22)')\n(25, 3, 2, 'MOUSE(row=54, col=30)')\n(26, 3, 2, 'MOUSE(row=54, col=38)')\n(27, 3, 2, 'MOUSE(row=6, col=22)')\n(28, 3, 2, 'MOUSE(row=30, col=22)')\nlast call score 2\nbar O 53 0 52\nbar Y 11 53 63\n"
  },
  "text_if_unparsed": null
}
```

## ft09-0d8bbf25 A · call_0f0c2430b8b0438e8047aba8

请求日志：runs/031-segmentation-forks/segmentation_forks_A/ft09-0d8bbf25_A_requests.jsonl:11；工具结果存在：True；返回码0且无error：True。

```python

# current board state
seg = current_frame.segmentation
grid_rows=[4,12,20,28,36,44,52]; grid_cols=[12,20,28,36,44]
cur={}
for n in seg['nodes']:
    b=n['boundary']; rs=[p[0] for p in b]; cs=[p[1] for p in b]
    r0,r1,c0,c1=min(rs),max(rs),min(cs),max(cs)
    if n['pixels']==36 and r1-r0==5 and c1-c0==5:
        cur[(grid_rows.index(r0),grid_cols.index(c0))]=(n['color'],r0,c0)
A = {}
legA = {0:'.OOO.',1:'.ORR.',2:'ORORR',3:'OOROO',4:'RRORO',5:'.ORO.',6:'.OOO.'}
for r in range(7):
    for c in range(5):
        if legA[r][c]!='.': A[(r,c)]=legA[r][c]
B = {k:('R' if v=='O' else 'O') for k,v in A.items()}
clicks=[]
for k,(col,r0,c0) in sorted(cur.items()):
    if k in B and col!=B[k]:
        clicks.append((r0+2,c0+2))
print('cells', len(cur), 'clicks for B', len(clicks))
print(clicks)

```

静态访问：`[{"field": "boundary", "kind": "subscript_load", "code_line": 7, "expression": "n['boundary']", "enclosing_scopes": ["For"]}]`

```json
{
  "first_snapshot_line": 11,
  "content_sha256": "d9858482615e597e6795473f01b7bb3ac17c9c9cfcfdffad7a587724c5404af2",
  "content_chars": 303,
  "payload": {
    "tool": "python",
    "returncode": 0,
    "stdout": "cells 23 clicks for B 22\n[(6, 30), (6, 38), (14, 22), (14, 38), (22, 14), (22, 22), (22, 30), (22, 38), (22, 46), (30, 14), (30, 30), (30, 46), (38, 14), (38, 22), (38, 30), (38, 38), (38, 46), (46, 22), (46, 38), (54, 22), (54, 30), (54, 38)]\n"
  },
  "text_if_unparsed": null
}
```

## tu93-0768757b A · call_a6ee9ac994484b69b5b5e922

请求日志：runs/031-segmentation-forks/segmentation_forks_A/tu93-0768757b_A_requests.jsonl:9；工具结果存在：True；返回码0且无error：False。

```python
import collections
def rooms(fr):
    rm,H,V,_=rgrid(fr); R=len(rm);C=len(rm[0])
    ADJ=collections.defaultdict(set)
    for i in range(R):
        for j in range(C):
            if rm[i][j]=='B': continue
            if (i,j) in H and j+1<C and rm[i][j+1]!='B': ADJ[(i,j)].add((i,j+1)); ADJ[(i,j+1)].add((i,j))
            if (i,j) in V and i+1<R and rm[i+1][j]!='B': ADJ[(i,j)].add((i+1,j)); ADJ[(i+1,j)].add((i,j))
    return {k:set(v) for k,v in ADJ.items()}
def one(fr,col):
    for n in fr.segmentation['nodes']:
        if n['color']==col:
            b=n['boundary']; return (min(p[0] for p in b), min(p[1] for p in b)) if len(n['pixels'])<4 else None
    return None
def cellof(fr,col):
    for n in fr.segmentation['nodes']:
        if n['color']==col and n['pixels']<=2:
            b=n['boundary'][0]; return (b[0],b[1])
    return None
rows=[]
for tr in transitions:
    if tr.level not in (8,9): continue
    bf=tr.before_frame; af=tr.after_frame
    if bf is None or af is None: continue
    p0=cellof(bf,'b'); p1=cellof(af,'b'); c0=cellof(bf,'r'); c1=cellof(af,'r')
    if p0 is None or p1 is None: continue
    rows.append((tr.level,tr.action,p0,p1,c0,c1))
print(len(rows))
for r_ in rows[-40:]: print(r_)

```

静态访问：`[{"field": "boundary", "kind": "subscript_load", "code_line": 14, "expression": "n['boundary']", "enclosing_scopes": ["If", "For", "FunctionDef"]}, {"field": "boundary", "kind": "subscript_load", "code_line": 19, "expression": "n['boundary']", "enclosing_scopes": ["If", "For", "FunctionDef"]}]`

```json
{
  "first_snapshot_line": 9,
  "content_sha256": "664d0c817d19e7bb801b4a979e04ca1ae25fc18bde453fbd4ff13a7c71fb34b1",
  "content_chars": 433,
  "payload": {
    "tool": "python",
    "function_retention": "Retained your function rooms(fr) for later Python calls in this game.\nRetained your function one(fr, col) for later Python calls in this game.\nRetained your function cellof(fr, col) for later Python calls in this game.",
    "error": "Traceback (most recent call last):\n  File \"<python_tool>\", line 23, in <module>\nAttributeError: 'TransitionView' object has no attribute 'level'"
  },
  "text_if_unparsed": null
}
```

## tu93-0768757b A · call_62b67fed98874a3abe300a89

请求日志：runs/031-segmentation-forks/segmentation_forks_A/tu93-0768757b_A_requests.jsonl:13；工具结果存在：True；返回码0且无error：True。

```python
sg=current_frame.segmentation
for n in sg['nodes']:
    if n['color'] in 'brNR':
        print(n['color'], n['pixels'], n['boundary'][:6])

```

静态访问：`[{"field": "boundary", "kind": "subscript_load", "code_line": 4, "expression": "n['boundary']", "enclosing_scopes": ["If", "For"]}]`

```json
{
  "first_snapshot_line": 13,
  "content_sha256": "6641833dfdd5635917fa512272e158e98b9f8700d2d0d2b49a184b6b8cc32f9e",
  "content_chars": 327,
  "payload": {
    "tool": "python",
    "returncode": 0,
    "stdout": "r 8 [[10, 33], [10, 35], [11, 34], [12, 35], [12, 33]]\nb 8 [[10, 45], [10, 47], [11, 46], [12, 47], [12, 45]]\nR 8 [[40, 27], [40, 29], [41, 28], [42, 29], [42, 27]]\nN 9 [[40, 33], [40, 35], [42, 35], [42, 33]]\nR 8 [[46, 27], [47, 28], [46, 29], [48, 29], [48, 27]]\n"
  },
  "text_if_unparsed": null
}
```

## ft09-0d8bbf25 B · call_def70a557dd242cf8e0e94c0

请求日志：runs/031-segmentation-forks/segmentation_forks_B/ft09-0d8bbf25_B_requests.jsonl:7；工具结果存在：True；返回码0且无error：True。

```python

seg = current_frame.segmentation
ns = seg['nodes']
grid_rows=[4,12,20,28,36,44,52]; grid_cols=[12,20,28,36,44]
cur={}
pieces={}
for n in ns:
    b=n['boundary']; rs=[p[0] for p in b]; cs=[p[1] for p in b]
    r0,r1,c0,c1=min(rs),max(rs),min(cs),max(cs)
    if n['pixels']==36 and r1-r0==5 and c1-c0==5:
        cur[(grid_rows.index(r0),grid_cols.index(c0))]=n['color']
    elif r1-r0<=5 and c1-c0<=5 and (r1-r0)>=1:
        for r in range(r0,r1+1):
            for c in range(c0,c1+1): pieces[(r,c)]=n['color']
pats=[(12,28),(28,20),(28,36),(44,28)]
other={'O':'R','R':'O'}
def target_for(mode):
    t={}
    for (pr,pc) in pats:
        center=pieces[(pr+2,pc+2)]
        R=grid_rows.index(pr); C=grid_cols.index(pc)
        for i in range(3):
            for j in range(3):
                if i==1 and j==1: continue
                sub=pieces[(pr+2*i,pc+2*j)]
                if mode=='A': col = center if sub=='W' else other[center]
                else: col = other[center] if sub=='W' else center
                t[(R-1+i,C-1+j)]=col
    return t
for mode in ('A','B'):
    t=target_for(mode)
    mism=[(k,cur.get(k),t[k]) for k in sorted(t) if cur.get(k)!=t[k]]
    print(mode,'mismatches:',mism)
print('cur:')
for r in range(7): print('  ',''.join(cur.get((r,c),'.') for c in range(5)))

```

静态访问：`[{"field": "boundary", "kind": "subscript_load", "code_line": 8, "expression": "n['boundary']", "enclosing_scopes": ["For"]}]`

```json
{
  "first_snapshot_line": 7,
  "content_sha256": "7859c4aef1e7c0a6a063a05e90949e041539c6030f1cd35b327348fa71bf4af8",
  "content_chars": 830,
  "payload": {
    "tool": "python",
    "function_retention": "Your function target_for was not retained: unavailable dependencies: grid_cols, grid_rows, other, pats, pieces. Pass snippet-specific data as arguments or redefine it if needed.",
    "returncode": 0,
    "stdout": "A mismatches: [((0, 1), 'R', 'O')]\nB mismatches: [((0, 2), 'O', 'R'), ((0, 3), 'O', 'R'), ((1, 1), 'O', 'R'), ((1, 3), 'R', 'O'), ((2, 0), 'O', 'R'), ((2, 1), 'R', 'O'), ((2, 2), 'O', 'R'), ((2, 3), 'R', 'O'), ((2, 4), 'R', 'O'), ((3, 0), 'O', 'R'), ((3, 2), 'R', 'O'), ((3, 4), 'O', 'R'), ((4, 0), 'R', 'O'), ((4, 1), 'R', 'O'), ((4, 2), 'O', 'R'), ((4, 3), 'R', 'O'), ((4, 4), 'O', 'R'), ((5, 1), 'O', 'R'), ((5, 3), 'O', 'R'), ((6, 1), 'O', 'R'), ((6, 2), 'O', 'R'), ((6, 3), 'O', 'R')]\ncur:\n   .ROO.\n   .O.R.\n   ORORR\n   O.R.O\n   RRORO\n   .O.O.\n   .OOO.\n"
  },
  "text_if_unparsed": null
}
```
