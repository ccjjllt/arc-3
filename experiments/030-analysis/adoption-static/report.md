# 030 持久 Python 结果分析

自动提取的跨调用读取仅供人工复核；定义存在、函数保留和工具不报错均不等于实际解题收益。


## 实际 Python 调用与读取候选

| 文件 | 去重调用 | 异常 | 超时 | 状态丢失通知 | 成功读取候选调用 |
|---|---:|---:|---:|---:|---:|
| cn04-2fe56bfb_p0_requests.jsonl | 158 | 20 | 1 | 2 | 61 |
| r11l-495a7899_p0_requests.jsonl | 88 | 2 | 0 | 0 | 32 |
| tu93-0768757b_p0_requests.jsonl | 136 | 11 | 0 | 0 | 75 |

状态丢失通知可能同时出现在超时调用和随后重启调用，不是独立丢失次数。调用token来自完整response日志；benchmark与日志记账分别保留，不能相加冒充新增成本。

## 待人工确认的代码和输出

### cn04-2fe56bfb_p0_requests.jsonl 变量 plans

读取方式：direct_before_definition；类型：list；定义输出行161，读取输出行165；关卡3。

定义代码：
```python

CUR4={'A':((4,11),0),'Z':((5,7),0),'B':((11,10),1)}
plans=[]
for kA,kZ,kB in itertools.product(range(4),repeat=3):
    TA0=set(PO2[('A',kA)][1]); TZ0=set(PO2[('Z',kZ)][1]); TB0=set(PO2[('B',kB)][1])
    dzs={(ta[0]-tz[0], ta[1]-tz[1]) for ta in TA0 for tz in TZ0}
    for dz in dzs:
        TZ={(p[0]+dz[0],p[1]+dz[1]) for p in TZ0}
        dbs={(ta[0]-tb[0], ta[1]-tb[1]) for ta in TA0 for tb in TB0} | {(tz[0]-tb[0], tz[1]-tb[1]) for tz in TZ for tb in TB0}
        for db in dbs:
            TB={(p[0]+db[0],p[1]+db[1]) for p in TB0}
            joints=(TA0&TZ)|(TA0&TB)|(TZ&TB)
            if len(joints)!=3: continue
            bA=set(PO2[('A',kA)][0]); bZ={(p[0]+dz[0],p[1]+dz[1]) for p in PO2[('Z',kZ)][0]}
            bB={(p[0]+db[0],p[1]+db[1]) for p in PO2[('B',kB)][0]}
            ov=(bA&bZ)|(bA&bB)|(bZ&bB)
            if ov-joints: continue
            allc=bA|bZ|bB
            mr=min(p[0] for p in allc); Mr=max(p[0] for p in allc); mc=min(p[1] for p in allc); Mc=max(p[1] for p in allc)
            if Mr-mr>19 or Mc-mc>19: continue
            bb=None
            for x in range(1-mr,21-Mr):
                for y in range(1-mc,21-Mc):
                    rotc=((kA-CUR4['A'][1])%4)+((kZ-CUR4['Z'][1])%4)+((kB-CUR4['B'][1])%4)
                    c=rotc+abs(x-CUR4['A'][0][0])+abs(y-CUR4['A'][0][1])+abs(x+dz[0]-CUR4['Z'][0][0])+abs(y+dz[1]-CUR4['Z'][0][1])+abs(x+db[0]-CUR4['B'][0][0])+abs(y+db[1]-CUR4['B'][0][1])
                    if bb is None or c<bb[0]: bb=(c,(x,y))
            if bb: plans.append((bb[0],(kA,kZ,kB),dz,db,bb[1],sorted(joints)))
plans.sort()
print(len(plans))
for p in plans[:5]:
    c,rots,dz,db,T,jn=p
    print('cost',c,'rots',rots,'T(A)',T,'-> Z',(T[0]+dz[0],T[1]+dz[1]),'B',(T[0]+db[0],T[1]+db[1]),'joints_abs',[(j[0]+T[0],j[1]+T[1]) for j in jn])

```

随后代码：
```python

c,rots,dz,db,T,jn=plans[0]
kA,kZ,kB=rots
def abso(o,k,base):
    bd,tp=PO2[(o,k)]
    return {(base[0]+r,base[1]+c2) for r,c2 in bd}, {(base[0]+r,base[1]+c2) for r,c2 in set(tp)}
bA,tA=abso('A',kA,T); bZ,tZ=abso('Z',kZ,(T[0]+dz[0],T[1]+dz[1])); bB,tB=abso('B',kB,(T[0]+db[0],T[1]+db[1]))
print('tipsA',sorted(tA),'tipsZ',sorted(tZ),'tipsB',sorted(tB))
ovs={'AZ':sorted(bA&bZ),'AB':sorted(bA&bB),'ZB':sorted(bZ&bB)}
print('overlaps',ovs)
cells=bA|bZ|bB
mr=min(p[0] for p in cells); Mr=max(p[0] for p in cells); mc=min(p[1] for p in cells); Mc=max(p[1] for p in cells)
jnset=set(jn)
for r_ in range(mr,Mr+1):
    row=''
    for c2 in range(mc,Mc+1):
        if (r_,c2) in jnset: row+='J'
        elif (r_,c2) in bA: row+='A'
        elif (r_,c2) in bZ: row+='Z'
        elif (r_,c2) in bB: row+='B'
        else: row+='.'
    print(r_, row)

```

实际随后输出：
```text
tipsA [(10, 16), (11, 11)] tipsZ [(5, 11), (11, 11)] tipsB [(5, 11), (10, 16)]
overlaps {'AZ': [], 'AB': [], 'ZB': []}
4 .....BBBBBB
5 ..ZZ.B....B
6 ..Z..BBBB.B
7 ZZZ.....B.B
8 Z.......B.B
9 ZZZ.....BBB
10 ..Z......A.
11 ..ZZAAAAAA.

```

人工确认：读取语句是否实际执行、值是否来自旧调用、是否仍适用当前盘面、是否用于搜索或动作、与新增关卡的关系。

### r11l-495a7899_p0_requests.jsonl 变量 plans

读取方式：direct_before_definition；类型：dict；定义输出行143，读取输出行145；关卡6。

定义代码：
```python
COARSE=[(r,c) for r in range(1,64,3) for c in range(0,64,3) if EO[r][c]]
print('coarse',len(COARSE))
def cells_beads(ends): 
    s=set()
    for p in ends: s|=set(diamond(*p))
    return s
def plan_chain(ends,hi,stops,needblobs,forbid_extra):
    """stops: list of hub targets (blob centers then ring). Returns (clicks, ends, hi) or None."""
    e=list(ends); h=hi; clicks=[]
    for i,t in enumerate(stops):
        remaining=set(blobsC[k] for k in needblobs[i:])
        fhub=(remaining-{t})|forbid_extra
        fend=forbid_extra|set(blobsC[k] for k in blobsC if blobsC[k] not in (t,))
        r_=reach(e,h,t,fhub,fend,coarse=COARSE)
        if r_ is None: return None
        clicks+=list(r_[1]); e=list(r_[2]); h=r_[3]
    return (clicks,e,h)
setA=[(11,11),(19,4),(19,22)]; setB=[(43,49),(57,50)]
plans={}
import itertools
assigns=[('R1',['B7','B2','B5'],'R3',['B6','B4','B8']), ('R3',['B6','B4','B8'],'R1',['B7','B2','B5'])]
for (ringA,blA,ringB,blB) in assigns:
    for oA in itertools.permutations(blA):
        for oB in itertools.permutations(blB):
            stopsA=[blobsC[x] for x in oA]+[rings[ringA]]
            stopsB=[blobsC[x] for x in oB]+[rings[ringB]]
            needA=list(oA); needB=list(oB)
            forb_for_A = cells_beads(setB)|{rings[ringB]}
            pA=plan_chain(setA,0,stopsA,needA,forb_for_A)
            if pA is None: continue
            # chain B: forbid chain A final beads+hub, ring A, remaining? all A blobs gone
            forb_for_B = cells_beads(pA[1])|set(hubcells(*mean_of(pA[1])))|{rings[ringA]}
            pB=plan_chain(setB,0,stopsB,needB,forb_for_B)
            if pB is None: continue
            total=1+len(pA[1])+1+len(pB[1])
            key=(ringA,oA,ringB,oB)
            if 'best' not in plans or total<plans['best'][0]:
                plans['best']=(total,key,pA,pB)
print('BEST',plans['best'][0],plans['best'][1])

```

随后代码：
```python
tot,pA,pB=plans['best'][0],plans['best'][2],plans['best'][3]
print('chainA clicks',pA[0])
print('chainA final ends',pA[1],'handle idx',pA[2],'hub',mean_of(pA[1]))
print('chainB clicks',pB[0])
print('chainB final ends',pB[1],'handle idx',pB[2],'hub',mean_of(pB[1]))
print('lens',len(pA[0]),len(pB[0]))

```

实际随后输出：
```text
chainA clicks [(55, 3), (19, 4), (61, 23), (25, 8), (4, 36), (55, 3), (28, 44), (7, 57), (19, 22), (25, 60)]
chainA final ends [(7, 57), (4, 36), (25, 60)] handle idx 2 hub (12, 51)
chainB clicks [(31, 14), (3, 40), (49, 3), (57, 50), (61, 47), (61, 19)]
chainB final ends [(49, 3), (61, 19)] handle idx 1 hub (55, 11)
lens 10 6

```

人工确认：读取语句是否实际执行、值是否来自旧调用、是否仍适用当前盘面、是否用于搜索或动作、与新增关卡的关系。

### tu93-0768757b_p0_requests.jsonl 变量 path

读取方式：direct_before_definition；类型：list；定义输出行133，读取输出行137；关卡5。

定义代码：
```python
path=['RIGHT','LEFT','LEFT','LEFT','LEFT','LEFT','DOWN','UP','DOWN','UP','DOWN','UP','DOWN','UP','DOWN','DOWN','DOWN','RIGHT','DOWN','DOWN','RIGHT','RIGHT','RIGHT','UP','UP','LEFT']
pos=(0,8); tt=3; bad=[]
for k,mv in enumerate(path,1):
    dd={'UP':(-2,0),'DOWN':(2,0),'LEFT':(0,-2),'RIGHT':(0,2)}[mv]
    np_=(pos[0]+dd[0],pos[1]+dd[1]); tt+=1
    if np_ in occ(tt): bad.append((k,mv,np_,'POSTMOVE-OCC'))
    if np_ in occ(tt-1): bad.append((k,mv,np_,'LANDED-ON'))
    if g5[(pos[0]+dd[0]//2)[0] if False else pos[0]+dd[0]//2][pos[1]+dd[1]//2]=='B': bad.append((k,mv,'mid-blocked'))
    pos=np_
print('final',pos,'t',tt,'problems',bad)

```

随后代码：
```python
plan=path[:8]
for k,mv in enumerate(plan,1):
    res,G,p,Os = step5(mv)
    pred=sorted(occ(3+k))
    print(3+k,mv,'p',p,'O',sorted(Os),'pred',pred,'MATCH' if sorted(Os)==pred else 'MISMATCH','over',res.get('game_over'),'won',res.get('level_completed'))
    if res.get('game_over') or res.get('level_completed'): break

```

实际随后输出：
```text
[action] RIGHT -> effect
4 RIGHT p (0, 10) O [(0, 6), (6, 4), (6, 8), (8, 6)] pred [(0, 6), (6, 4), (6, 8), (8, 6)] MATCH over False won False
[action] LEFT -> effect
5 LEFT p (0, 8) O [(2, 6), (6, 6), (6, 10), (8, 4)] pred [(2, 6), (6, 6), (6, 10), (8, 4)] MATCH over False won False
[action] LEFT -> effect
6 LEFT p (0, 6) O [(4, 6), (6, 4), (6, 12)] pred [(4, 6), (6, 4), (6, 12)] MATCH over False won False
[action] LEFT -> effect
7 LEFT p (0, 4) O [(2, 6), (4, 4), (6, 6), (6, 14)] pred [(2, 6), (4, 4), (6, 6), (6, 14)] MATCH over False won False
[action] LEFT -> effect
8 LEFT p (0, 2) O [(0, 6), (6, 4), (6, 12), (8, 6)] pred [(0, 6), (6, 4), (6, 12), (8, 6)] MATCH over False won False
[action] LEFT -> effect
9 LEFT p (0, 0) O [(2, 6), (6, 10), (8, 4), (10, 6)] pred [(2, 6), (6, 10), (8, 4), (10, 6)] MATCH over False won False
[action] DOWN -> effect
10 DOWN p (2, 0) O [(4, 6), (6, 4), (6, 8), (8, 6)] pred [(4, 6), (6, 4), (6, 8), (8, 6)] MATCH over False won False
[action] UP -> effect
11 UP p (0, 0) O [(4, 4), (6, 6)] pred [(4, 4), (6, 6)] MATCH over False won False

```

人工确认：读取语句是否实际执行、值是否来自旧调用、是否仍适用当前盘面、是否用于搜索或动作、与新增关卡的关系。

### tu93-0768757b_p0_requests.jsonl 变量 path

读取方式：direct_before_definition；类型：list；定义输出行133，读取输出行139；关卡5。

定义代码：
```python
path=['RIGHT','LEFT','LEFT','LEFT','LEFT','LEFT','DOWN','UP','DOWN','UP','DOWN','UP','DOWN','UP','DOWN','DOWN','DOWN','RIGHT','DOWN','DOWN','RIGHT','RIGHT','RIGHT','UP','UP','LEFT']
pos=(0,8); tt=3; bad=[]
for k,mv in enumerate(path,1):
    dd={'UP':(-2,0),'DOWN':(2,0),'LEFT':(0,-2),'RIGHT':(0,2)}[mv]
    np_=(pos[0]+dd[0],pos[1]+dd[1]); tt+=1
    if np_ in occ(tt): bad.append((k,mv,np_,'POSTMOVE-OCC'))
    if np_ in occ(tt-1): bad.append((k,mv,np_,'LANDED-ON'))
    if g5[(pos[0]+dd[0]//2)[0] if False else pos[0]+dd[0]//2][pos[1]+dd[1]//2]=='B': bad.append((k,mv,'mid-blocked'))
    pos=np_
print('final',pos,'t',tt,'problems',bad)

```

随后代码：
```python
plan=path[8:]
for k,mv in enumerate(plan,12):
    res,G,p,Os = step5(mv)
    pred=sorted(occ(k))
    bar=current_frame.ascii.split('\n')[63].count('M')
    print(k,mv,'p',p,'O',sorted(Os),'MATCH' if sorted(Os)==pred else 'MISMATCH pred '+str(pred),'bar',bar,'over',res.get('game_over'),'won',res.get('level_completed'))
    if res.get('game_over') or res.get('level_completed'): break

```

实际随后输出：
```text
[action] DOWN -> effect
12 DOWN p (2, 0) O [(4, 6), (6, 4), (8, 6)] MATCH bar 49 over False won False
[action] UP -> effect
13 UP p (0, 0) O [(2, 6), (6, 2), (8, 4), (10, 6)] MATCH bar 47 over False won False
[action] DOWN -> effect
14 DOWN p (2, 0) O [(0, 6), (6, 0), (6, 4), (8, 6)] MATCH bar 46 over False won False
[action] UP -> effect
15 UP p (0, 0) O [(2, 6), (4, 4), (6, 2), (6, 6)] MATCH bar 45 over False won False
[action] DOWN -> effect
16 DOWN p (2, 0) O [(4, 6), (6, 4)] MATCH bar 44 over False won False
[action] UP -> effect
17 UP p (0, 0) O [(2, 6), (6, 6), (8, 4)] MATCH bar 42 over False won False
[action] DOWN -> effect
18 DOWN p (2, 0) O [(0, 6), (6, 4), (6, 8), (8, 6)] MATCH bar 41 over False won False
[action] DOWN -> effect
19 DOWN p (4, 0) O [(2, 6), (4, 4), (6, 10), (10, 6)] MATCH bar 40 over False won False
[action] DOWN -> effect
20 DOWN p (6, 0) O [(4, 6), (6, 4), (6, 12), (8, 6)] MATCH bar 38 over False won False
[action] RIGHT -> effect
21 RIGHT p (6, 2) O [(6, 6), (6, 14), (8, 4)] MATCH bar 37 over False won False
[action] DOWN -> effect
22 DOWN p (8, 2) O [(4, 6), (6, 4), (6, 12), (8, 6)] MATCH bar 36 over False won False
[action] DOWN -> effect
23 DOWN p (10, 2) O [(2, 6), (4, 4), (6, 10), (10, 6)] MATCH bar 35 over False won False
[action] RIGHT -> effect
24 RIGHT p (10, 4) O [(0, 6), (6, 4), (6, 8), (8, 6)] MATCH bar 33 over False won False
[action] RIGHT -> effect
25 RIGHT p (10, 6) O [(2, 6), (6, 6), (8, 4)] MATCH bar 32 over False won False
[action] RIGHT -> effect
26 RIGHT p (10, 8) O [(4, 6), (6, 4)] MATCH bar 31 over False won False
[action] UP -> effect
27 UP p (8, 8) O [(2, 6), (4, 4), (6, 2), (6, 6)] MATCH bar 29 over False won False
[action] UP -> effect
28 UP p (6, 8) O [(0, 6), (6, 0), (6, 4), (8, 6)] MATCH bar 28 over False won False
[action] LEFT -> LEVEL COMPLETED
29 LEFT p (1, 13) O [(9, 13)] MISMATCH pred [(2, 6), (6, 2), (8, 4), (10, 6)] bar 64 over False won True

```

人工确认：读取语句是否实际执行、值是否来自旧调用、是否仍适用当前盘面、是否用于搜索或动作、与新增关卡的关系。

### cn04-2fe56bfb_p0_requests.jsonl 变量 sols

读取方式：direct_before_definition；类型：list；定义输出行37，读取输出行39；关卡2。

定义代码：
```python

def rot(cells, k):
    # k x 90 CW: (r,c) -> (c, -r)
    out=set()
    for (r,c) in cells:
        rr,cc=r,c
        for _ in range(k):
            rr,cc = cc, -rr
        out.add((rr,cc))
    return out
objs={}
for name in ['p','N','Y','W']:
    bs = info[name]['body']
    rb = set()
    for (r0,c0) in info[name]['reds']:
        for dr in range(3):
            for dc in range(3):
                rb.add((r0+dr,c0+dc))
    objs[name]={'body':bs,'red':rb}
    print(name,'body',len(bs),'red',len(rb))

def norm(s):
    mr=min(p[0] for p in s); mc=min(p[1] for p in s)
    return frozenset((r-mr,c-mc) for r,c in s)

sols=[]
for P in objs:
    for S in objs:
        if P==S: continue
        for k in range(4):
            rb = rot(objs[P]['red'],k); bb = rot(objs[P]['body'],k)
            if len(rb)!=len(objs[P]['red']): pass
            # try map rb onto subsets of S red of same size
            Sr = objs[S]['red']; Sb=objs[S]['body']
            rbl=sorted(rb)
            if not rbl: continue
            # candidate translations: align rbl[0] to each red cell of S
            cands=set()
            for (tr,tc) in Sr:
                dr, dc = tr-rbl[0][0], tc-rbl[0][1]
                cands.add((dr,dc))
            for (dr,dc) in cands:
                moved_red = {(r+dr,c+dc) for r,c in rb}
                if not moved_red <= Sr: continue
                moved_body = {(r+dr,c+dc) for r,c in bb}
                if moved_body & Sb: continue
                if moved_body & Sr: continue   # body shouldn't cover pins? allow check later
                sols.append((P,S,k,dr,dc,len(moved_red)))
for s in sols: print(s)
print('num sols', len(sols))

```

随后代码：
```python

def render_placement(P,S,k,dr,dc):
    bb = rot(objs[P]['body'],k); rb = rot(objs[P]['red'],k)
    mb = {(r+dr,c+dc) for r,c in bb}; mr={(r+dr,c+dc) for r,c in rb}
    Sb=objs[S]['body']; Sr=objs[S]['red']
    rows = sorted({p[0] for p in mb|mr|Sb|Sr}); cols=sorted({p[1] for p in mb|mr|Sb|Sr})
    r0,r1=min(rows),max(rows); c0,c1=min(cols),max(cols)
    out=[]
    for r_ in range(r0,r1+1):
        line=''
        for c_ in range(c0,c1+1):
            ch='.'
            if (r_,c_) in Sb: ch='S'
            if (r_,c_) in Sr: ch='r'
            if (r_,c_) in mb: ch='P'
            if (r_,c_) in mr: ch='#'
            line+=ch
        out.append(f'{r_:2d} '+line)
    print(f'--- {P} rot{k} -> {S} at ({dr},{dc})  bbox rows {r0}-{r1} cols {c0}-{c1}')
    print('\n'.join(out))
for s in sols:
    render_placement(*s[:5])

```

实际随后输出：
```text
--- p rot0 -> Y at (21,0)  bbox rows 29-55 cols 11-34
29 PPPPPPPPP...............
30 PPPPPPPPP...............
31 PPPPPPPPP...............
32 PPP...PPP...............
33 PPP...PPP...............
34 PPP...PPP...............
35 PPP...PPP...SSSSSSSSS...
36 PPP...PPP...SSSSSSSSS...
37 PPP...PPP...SSSSSSSSS...
38 PPP...###...SSS...SSSrrr
39 PPP...###...SSS...SSSrrr
40 PPP...###...SSS...SSSrrr
41 PPP...SSSSSSSSS...SSS...
42 PPP...SSSSSSSSS...SSS...
43 PPP...SSSSSSSSS...SSS...
44 PPP###SSS.........SSS...
45 PPP###SSS.........SSS...
46 PPP###SSS.........SSS...
47 ......SSSSSSSSS...SSS...
48 ......SSSSSSSSS...SSS...
49 ......SSSSSSSSS...SSS...
50 ............SSSSSSSSS...
51 ............SSSSSSSSS...
52 ............SSSSSSSSS...
53 ...............rrr......
54 ...............rrr......
55 ...............rrr......
--- W rot3 -> N at (78,3)  bbox rows 14-34 cols 38-58
14 ......rrrSSS.........
15 ......rrrSSS.........
16 ......rrrSSS.........
17 .........SSS.........
18 .........SSS.........
19 .........SSS.........
20 .........SSS###PPPPPP
21 .........SSS###PPPPPP
22 .........SSS###PPPPPP
23 .........SSS......PPP
24 .........SSS......PPP
25 .........SSS......PPP
26 .........SSS###PPPPPP
27 .........SSS###PPPPPP
28 .........SSS###PPPPPP
29 rrr......SSS.........
30 rrr......SSS.........
31 rrr......SSS.........
32 SSSSSSSSSSSS.........
33 SSSSSSSSSSSS.........
34 SSSSSSSSSSSS.........

```

人工确认：读取语句是否实际执行、值是否来自旧调用、是否仍适用当前盘面、是否用于搜索或动作、与新增关卡的关系。

### cn04-2fe56bfb_p0_requests.jsonl 变量 sols_found

读取方式：direct_before_definition；类型：list；定义输出行91，读取输出行93；关卡2。

定义代码：
```python

sols_found=[(0,0,(-1,-3),0,(-3,-5),3,(2,5)),(1,1,(-3,2),1,(-5,4),0,(5,2)),(2,2,(2,2),2,(4,6),1,(2,-3)),(3,3,(2,-1),3,(6,-3),2,(-3,2))]
curpos={'N':(5,12),'Y':(12,6),'W':(11,4),'b':(7,18)}
currot={'N':0,'Y':0,'W':0,'b':3}
for (kg,ky,ty,kw,tw,kb,tb) in sols_found:
    rel={'N':(0,0),'Y':ty,'W':tw,'b':tb}
    rot={'N':kg,'Y':ky,'W':kw,'b':kb}
    # optimal shift per axis
    import statistics
    rs=[curpos[o][0]-rel[o][0] for o in rel]; cs=[curpos[o][1]-rel[o][1] for o in rel]
    def med(vals):
        v=sorted(vals); return v[len(v)//2-1], v[len(v)//2]
    rlo,rhi = med(rs); clo,chi = med(cs)
    best=None
    for s in range(-6,28):
        for t in range(-6,28):
            # check on-board: all cells of all objects within blocks 1..20
            ok=True; tot=0
            for o in rel:
                S=SHAPE[o][rot[o]]
                tr=(s+rel[o][0], t+rel[o][1])
                cells_abs={(r+tr[0],c+tr[1]) for r,c in (S['body']|S['red'])}
                if min(p[0] for p in cells_abs)<1 or max(p[0] for p in cells_abs)>20: ok=False; break
                if min(p[1] for p in cells_abs)<1 or max(p[1] for p in cells_abs)>20: ok=False; break
                tot += abs(tr[0]-curpos[o][0])+abs(tr[1]-curpos[o][1])
            if not ok: continue
            rotcost = sum((rot[o]-currot[o])%4 for o in rel)
            c = tot+rotcost
            if best is None or c<best[0]: best=(c,s,t,tot,rotcost)
    print('sol',kg,ky,kw,kb,'->',best)

```

随后代码：
```python

kg,ky,ty,kw,tw,kb,tb = sols_found[0]
shift=(5,9)
rot={'N':kg,'Y':ky,'W':kw,'b':kb}; rel={'N':(0,0),'Y':ty,'W':tw,'b':tb}
placed={}
for o in rel:
    S=SHAPE[o][rot[o]]; tr=(shift[0]+rel[o][0], shift[1]+rel[o][1])
    placed[o]={'body':{(r+tr[0],c+tr[1]) for r,c in S['body']},'red':{(r+tr[0],c+tr[1]) for r,c in S['red']},'tr':tr}
allb=set().union(*[placed[o]['body'] for o in rel]); allr=set().union(*[placed[o]['red'] for o in rel])
r0=min(p[0] for p in allb|allr); r1=max(p[0] for p in allb|allr); c0=min(p[1] for p in allb|allr); c1=max(p[1] for p in allb|allr)
print('target assembly blocks rows',r0,r1,'cols',c0,c1)
for r_ in range(r0,r1+1):
    line=''
    for c_ in range(c0,c1+1):
        ch='.'
        for o in rel:
            if (r_,c_) in placed[o]['body']: ch={'N':'G','Y':'Y','W':'W','b':'U'}[o]
        m=[o for o in rel if (r_,c_) in placed[o]['red']]
        if len(m)>1: ch='#'
        elif len(m)==1: ch={'N':'g','Y':'y','W':'w','b':'u'}[m[0]]
        line+=ch
    print(f'{r_:2d} '+line)
# check pairing
for o in rel:
    un=[p for p in placed[o]['red'] if not any(p in placed[q]['red'] for q in rel if q!=o)]
    print(o,'unpaired red blocks:',sorted(un))
print('targets', {o:placed[o]['tr'] for o in rel})

```

实际随后输出：
```text
target assembly blocks rows 2 11 cols 4 15
 2 WWW.........
 3 W.W.........
 4 W.W.YYY.....
 5 W.#.Y.Y#G...
 6 W.YYY.Y.G...
 7 W#Y...Y.G#UU
 8 ..YYY.Y.G..U
 9 ....YYY.G#UU
10 .....#..G...
11 .....GGGG...
N unpaired red blocks: []
Y unpaired red blocks: []
W unpaired red blocks: []
b unpaired red blocks: []
targets {'N': (5, 9), 'Y': (4, 6), 'W': (2, 4), 'b': (7, 14)}

```

人工确认：读取语句是否实际执行、值是否来自旧调用、是否仍适用当前盘面、是否用于搜索或动作、与新增关卡的关系。

### cn04-2fe56bfb_p0_requests.jsonl 变量 A_body0

读取方式：direct_before_definition；类型：set；定义输出行137，读取输出行139；关卡3。

定义代码：
```python

# local shapes (rot 0), relative to body-bbox min, from level-3 INITIAL frame
Z_body0={(0,2),(0,3),(1,2),(2,0),(2,1),(2,2),(3,0),(4,0),(4,1),(4,2),(5,2),(6,2),(6,3)}
Z_tips0={(0,4),(6,4)}
A_body0={(0,5),(1,0),(1,1),(1,2),(1,3),(1,4),(1,5)}
A_tips0={(0,5),(1,0)}
B_all0={(10,11),(11,10),(11,11),(11,12),(12,10),(12,12),(13,10),(13,12),(14,10),(14,12),(14,13),(14,14),(14,15),(15,10),(15,15),(15,16),(16,10),(16,11),(16,12),(16,13),(16,14),(16,15)}
# normalize by body min (body = all minus tips hook(10,11),tail(15,16))
B_tips_abs={(10,11),(15,16)}
B_body_abs=B_all0-B_tips_abs
mb=(min(p[0] for p in B_body_abs), min(p[1] for p in B_body_abs))
B_body0={(r-mb[0],c-mb[1]) for r,c in B_body_abs}
B_tips0={(r-mb[0],c-mb[1]) for r,c in B_tips_abs}
print('B body min', mb, 'n body', len(B_body0), 'tips', sorted(B_tips0))
for nm,bd,tp in [('Z',Z_body0,Z_tips0),('A',A_body0,A_tips0),('B',B_body0,B_tips0)]:
    mr=min(p[0] for p in bd|tp); Mr=max(p[0] for p in bd|tp); mc=min(p[1] for p in bd|tp); Mc=max(p[1] for p in bd|tp)
    for r_ in range(mr,Mr+1):
        print(nm, ''.join('#' if (r_,c_) in tp else ('B' if (r_,c_) in bd else '.') for c_ in range(mc,Mc+1)))
    print()

```

随后代码：
```python

import itertools
SH={'A':(A_body0,A_tips0),'Z':(Z_body0,Z_tips0),'B':(B_body0,B_tips0)}
CUR={'A':((4,11),0),'Z':((5,7),0),'B':((12,10),0)}
def pose(o,k):
    bd,tp=SH[o]
    b=rotb(bd,k); t=rotb(tp,k)
    m=min(p[0] for p in b); n=min(p[1] for p in b)
    return ({(r-m,c-n) for r,c in b}, [(r-m,c-n) for r,c in t])
PO={}
for o in SH:
    for k in range(4): PO[(o,k)]=pose(o,k)
tips={'A':['a0','a1'],'Z':['z0','z1'],'B':['b0','b1']}
tips_local={'A':list(A_tips0),'Z':list(Z_tips0),'B':list(B_tips0)}
# enumerate matchings
alltips=[('A',0),('A',1),('Z',0),('Z',1),('B',0),('B',1)]
def matchings(items):
    if not items: yield []; return
    a=items[0]
    for i in range(1,len(items)):
        b=items[i]
        rest=items[1:i]+items[i+1:]
        for m in matchings(rest): yield [(a,b)]+m
valid_ms=[]
for m in matchings(alltips):
    if any(x[0]==y[0] for x,y in m): continue
    # object graph must be triangle
    edges=set(frozenset((x[0],y[0])) for x,y in m)
    if len(edges)==3: valid_ms.append(m)
print('valid matchings', len(valid_ms))
sols=[]
for kA,kZ,kB in itertools.product(range(4),repeat=3):
    P={'A':PO[('A',kA)],'Z':PO[('Z',kZ)],'B':PO[('B',kB)]}
    for m in valid_ms:
        # build equations t_P - t_Q = rot(tq) - rot(tp)
        # solve via BFS over objects
        eqs=[]
        for (x,i),(y,j) in m:
            tp=P[x][1][i]; tq=P[y][1][j]
            eqs.append((x,y,(tq[0]-tp[0], tq[1]-tp[1])))   # t_P + tp = t_Q + tq -> t_Q = t_P + (tp - tq)
        # t_A = base; compute t_Z, t_B
        rel={'A':(0,0)}
        ok=True
        pend=list(eqs)
        while pend:
            nxt=[]
            for (x,y,d) in pend:
                if x in rel and y in rel:
                    if (rel[y][0]-rel[x][0], rel[y][1]-rel[x][1]) != d: ok=False; break
                elif x in rel:
                    rel[y]=(rel[x][0]+d[0], rel[x][1]+d[1])
                elif y in rel:
                    rel[x]=(rel[y][0]-d[0], rel[y][1]-d[1])
                else: nxt.append((x,y,d))
            if not ok: break
            pend=nxt
            if not nxt and pend: ok=False; break
        if not ok: continue
        # overlaps & bbox in relative frame
        absb={o:{(p[0]+rel[o][0],p[1]+rel[o][1]) for p in P[o][0]} for o in P}
        abst={o:{(p[0]+rel[o][0],p[1]+rel[o][1]) for p in P[o][1]} for o in P}
        jointcells=set()
        for (x,i),(y,j) in m:
            tp=P[x][1][i]; tq=P[y][1][j]
            jointcells.add((tp[0]+rel[x][0], tp[1]+rel[x][1]))
        ov=set()
        for a,b in [('A','Z'),('A','B'),('Z','B')]:
            ov |= (absb[a] & absb[b])
        if ov != jointcells: continue
        allc=set().union(*absb.values())
        mr=min(p[0] for p in allc); Mr=max(p[0] for p in allc); mc=min(p[1] for p in allc); Mc=max(p[1] for p in allc)
        if Mr-mr>20 or Mc-mc>20: continue
        sols.append(((kA,kZ,kB), tuple(m), tuple(sorted(jointcells)), (mr,mc,Mr,Mc)))
print('candidate assemblies:', len(sols))
for s in sols[:12]: print(s[0], s[2], s[3])

```

实际随后输出：
```text
valid matchings 8
candidate assemblies: 0

```

人工确认：读取语句是否实际执行、值是否来自旧调用、是否仍适用当前盘面、是否用于搜索或动作、与新增关卡的关系。

### cn04-2fe56bfb_p0_requests.jsonl 变量 A_tips0

读取方式：direct_before_definition；类型：set；定义输出行137，读取输出行139；关卡3。

定义代码：
```python

# local shapes (rot 0), relative to body-bbox min, from level-3 INITIAL frame
Z_body0={(0,2),(0,3),(1,2),(2,0),(2,1),(2,2),(3,0),(4,0),(4,1),(4,2),(5,2),(6,2),(6,3)}
Z_tips0={(0,4),(6,4)}
A_body0={(0,5),(1,0),(1,1),(1,2),(1,3),(1,4),(1,5)}
A_tips0={(0,5),(1,0)}
B_all0={(10,11),(11,10),(11,11),(11,12),(12,10),(12,12),(13,10),(13,12),(14,10),(14,12),(14,13),(14,14),(14,15),(15,10),(15,15),(15,16),(16,10),(16,11),(16,12),(16,13),(16,14),(16,15)}
# normalize by body min (body = all minus tips hook(10,11),tail(15,16))
B_tips_abs={(10,11),(15,16)}
B_body_abs=B_all0-B_tips_abs
mb=(min(p[0] for p in B_body_abs), min(p[1] for p in B_body_abs))
B_body0={(r-mb[0],c-mb[1]) for r,c in B_body_abs}
B_tips0={(r-mb[0],c-mb[1]) for r,c in B_tips_abs}
print('B body min', mb, 'n body', len(B_body0), 'tips', sorted(B_tips0))
for nm,bd,tp in [('Z',Z_body0,Z_tips0),('A',A_body0,A_tips0),('B',B_body0,B_tips0)]:
    mr=min(p[0] for p in bd|tp); Mr=max(p[0] for p in bd|tp); mc=min(p[1] for p in bd|tp); Mc=max(p[1] for p in bd|tp)
    for r_ in range(mr,Mr+1):
        print(nm, ''.join('#' if (r_,c_) in tp else ('B' if (r_,c_) in bd else '.') for c_ in range(mc,Mc+1)))
    print()

```

随后代码：
```python

import itertools
SH={'A':(A_body0,A_tips0),'Z':(Z_body0,Z_tips0),'B':(B_body0,B_tips0)}
CUR={'A':((4,11),0),'Z':((5,7),0),'B':((12,10),0)}
def pose(o,k):
    bd,tp=SH[o]
    b=rotb(bd,k); t=rotb(tp,k)
    m=min(p[0] for p in b); n=min(p[1] for p in b)
    return ({(r-m,c-n) for r,c in b}, [(r-m,c-n) for r,c in t])
PO={}
for o in SH:
    for k in range(4): PO[(o,k)]=pose(o,k)
tips={'A':['a0','a1'],'Z':['z0','z1'],'B':['b0','b1']}
tips_local={'A':list(A_tips0),'Z':list(Z_tips0),'B':list(B_tips0)}
# enumerate matchings
alltips=[('A',0),('A',1),('Z',0),('Z',1),('B',0),('B',1)]
def matchings(items):
    if not items: yield []; return
    a=items[0]
    for i in range(1,len(items)):
        b=items[i]
        rest=items[1:i]+items[i+1:]
        for m in matchings(rest): yield [(a,b)]+m
valid_ms=[]
for m in matchings(alltips):
    if any(x[0]==y[0] for x,y in m): continue
    # object graph must be triangle
    edges=set(frozenset((x[0],y[0])) for x,y in m)
    if len(edges)==3: valid_ms.append(m)
print('valid matchings', len(valid_ms))
sols=[]
for kA,kZ,kB in itertools.product(range(4),repeat=3):
    P={'A':PO[('A',kA)],'Z':PO[('Z',kZ)],'B':PO[('B',kB)]}
    for m in valid_ms:
        # build equations t_P - t_Q = rot(tq) - rot(tp)
        # solve via BFS over objects
        eqs=[]
        for (x,i),(y,j) in m:
            tp=P[x][1][i]; tq=P[y][1][j]
            eqs.append((x,y,(tq[0]-tp[0], tq[1]-tp[1])))   # t_P + tp = t_Q + tq -> t_Q = t_P + (tp - tq)
        # t_A = base; compute t_Z, t_B
        rel={'A':(0,0)}
        ok=True
        pend=list(eqs)
        while pend:
            nxt=[]
            for (x,y,d) in pend:
                if x in rel and y in rel:
                    if (rel[y][0]-rel[x][0], rel[y][1]-rel[x][1]) != d: ok=False; break
                elif x in rel:
                    rel[y]=(rel[x][0]+d[0], rel[x][1]+d[1])
                elif y in rel:
                    rel[x]=(rel[y][0]-d[0], rel[y][1]-d[1])
                else: nxt.append((x,y,d))
            if not ok: break
            pend=nxt
            if not nxt and pend: ok=False; break
        if not ok: continue
        # overlaps & bbox in relative frame
        absb={o:{(p[0]+rel[o][0],p[1]+rel[o][1]) for p in P[o][0]} for o in P}
        abst={o:{(p[0]+rel[o][0],p[1]+rel[o][1]) for p in P[o][1]} for o in P}
        jointcells=set()
        for (x,i),(y,j) in m:
            tp=P[x][1][i]; tq=P[y][1][j]
            jointcells.add((tp[0]+rel[x][0], tp[1]+rel[x][1]))
        ov=set()
        for a,b in [('A','Z'),('A','B'),('Z','B')]:
            ov |= (absb[a] & absb[b])
        if ov != jointcells: continue
        allc=set().union(*absb.values())
        mr=min(p[0] for p in allc); Mr=max(p[0] for p in allc); mc=min(p[1] for p in allc); Mc=max(p[1] for p in allc)
        if Mr-mr>20 or Mc-mc>20: continue
        sols.append(((kA,kZ,kB), tuple(m), tuple(sorted(jointcells)), (mr,mc,Mr,Mc)))
print('candidate assemblies:', len(sols))
for s in sols[:12]: print(s[0], s[2], s[3])

```

实际随后输出：
```text
valid matchings 8
candidate assemblies: 0

```

人工确认：读取语句是否实际执行、值是否来自旧调用、是否仍适用当前盘面、是否用于搜索或动作、与新增关卡的关系。

### cn04-2fe56bfb_p0_requests.jsonl 变量 B_body0

读取方式：direct_before_definition；类型：set；定义输出行137，读取输出行139；关卡3。

定义代码：
```python

# local shapes (rot 0), relative to body-bbox min, from level-3 INITIAL frame
Z_body0={(0,2),(0,3),(1,2),(2,0),(2,1),(2,2),(3,0),(4,0),(4,1),(4,2),(5,2),(6,2),(6,3)}
Z_tips0={(0,4),(6,4)}
A_body0={(0,5),(1,0),(1,1),(1,2),(1,3),(1,4),(1,5)}
A_tips0={(0,5),(1,0)}
B_all0={(10,11),(11,10),(11,11),(11,12),(12,10),(12,12),(13,10),(13,12),(14,10),(14,12),(14,13),(14,14),(14,15),(15,10),(15,15),(15,16),(16,10),(16,11),(16,12),(16,13),(16,14),(16,15)}
# normalize by body min (body = all minus tips hook(10,11),tail(15,16))
B_tips_abs={(10,11),(15,16)}
B_body_abs=B_all0-B_tips_abs
mb=(min(p[0] for p in B_body_abs), min(p[1] for p in B_body_abs))
B_body0={(r-mb[0],c-mb[1]) for r,c in B_body_abs}
B_tips0={(r-mb[0],c-mb[1]) for r,c in B_tips_abs}
print('B body min', mb, 'n body', len(B_body0), 'tips', sorted(B_tips0))
for nm,bd,tp in [('Z',Z_body0,Z_tips0),('A',A_body0,A_tips0),('B',B_body0,B_tips0)]:
    mr=min(p[0] for p in bd|tp); Mr=max(p[0] for p in bd|tp); mc=min(p[1] for p in bd|tp); Mc=max(p[1] for p in bd|tp)
    for r_ in range(mr,Mr+1):
        print(nm, ''.join('#' if (r_,c_) in tp else ('B' if (r_,c_) in bd else '.') for c_ in range(mc,Mc+1)))
    print()

```

随后代码：
```python

import itertools
SH={'A':(A_body0,A_tips0),'Z':(Z_body0,Z_tips0),'B':(B_body0,B_tips0)}
CUR={'A':((4,11),0),'Z':((5,7),0),'B':((12,10),0)}
def pose(o,k):
    bd,tp=SH[o]
    b=rotb(bd,k); t=rotb(tp,k)
    m=min(p[0] for p in b); n=min(p[1] for p in b)
    return ({(r-m,c-n) for r,c in b}, [(r-m,c-n) for r,c in t])
PO={}
for o in SH:
    for k in range(4): PO[(o,k)]=pose(o,k)
tips={'A':['a0','a1'],'Z':['z0','z1'],'B':['b0','b1']}
tips_local={'A':list(A_tips0),'Z':list(Z_tips0),'B':list(B_tips0)}
# enumerate matchings
alltips=[('A',0),('A',1),('Z',0),('Z',1),('B',0),('B',1)]
def matchings(items):
    if not items: yield []; return
    a=items[0]
    for i in range(1,len(items)):
        b=items[i]
        rest=items[1:i]+items[i+1:]
        for m in matchings(rest): yield [(a,b)]+m
valid_ms=[]
for m in matchings(alltips):
    if any(x[0]==y[0] for x,y in m): continue
    # object graph must be triangle
    edges=set(frozenset((x[0],y[0])) for x,y in m)
    if len(edges)==3: valid_ms.append(m)
print('valid matchings', len(valid_ms))
sols=[]
for kA,kZ,kB in itertools.product(range(4),repeat=3):
    P={'A':PO[('A',kA)],'Z':PO[('Z',kZ)],'B':PO[('B',kB)]}
    for m in valid_ms:
        # build equations t_P - t_Q = rot(tq) - rot(tp)
        # solve via BFS over objects
        eqs=[]
        for (x,i),(y,j) in m:
            tp=P[x][1][i]; tq=P[y][1][j]
            eqs.append((x,y,(tq[0]-tp[0], tq[1]-tp[1])))   # t_P + tp = t_Q + tq -> t_Q = t_P + (tp - tq)
        # t_A = base; compute t_Z, t_B
        rel={'A':(0,0)}
        ok=True
        pend=list(eqs)
        while pend:
            nxt=[]
            for (x,y,d) in pend:
                if x in rel and y in rel:
                    if (rel[y][0]-rel[x][0], rel[y][1]-rel[x][1]) != d: ok=False; break
                elif x in rel:
                    rel[y]=(rel[x][0]+d[0], rel[x][1]+d[1])
                elif y in rel:
                    rel[x]=(rel[y][0]-d[0], rel[y][1]-d[1])
                else: nxt.append((x,y,d))
            if not ok: break
            pend=nxt
            if not nxt and pend: ok=False; break
        if not ok: continue
        # overlaps & bbox in relative frame
        absb={o:{(p[0]+rel[o][0],p[1]+rel[o][1]) for p in P[o][0]} for o in P}
        abst={o:{(p[0]+rel[o][0],p[1]+rel[o][1]) for p in P[o][1]} for o in P}
        jointcells=set()
        for (x,i),(y,j) in m:
            tp=P[x][1][i]; tq=P[y][1][j]
            jointcells.add((tp[0]+rel[x][0], tp[1]+rel[x][1]))
        ov=set()
        for a,b in [('A','Z'),('A','B'),('Z','B')]:
            ov |= (absb[a] & absb[b])
        if ov != jointcells: continue
        allc=set().union(*absb.values())
        mr=min(p[0] for p in allc); Mr=max(p[0] for p in allc); mc=min(p[1] for p in allc); Mc=max(p[1] for p in allc)
        if Mr-mr>20 or Mc-mc>20: continue
        sols.append(((kA,kZ,kB), tuple(m), tuple(sorted(jointcells)), (mr,mc,Mr,Mc)))
print('candidate assemblies:', len(sols))
for s in sols[:12]: print(s[0], s[2], s[3])

```

实际随后输出：
```text
valid matchings 8
candidate assemblies: 0

```

人工确认：读取语句是否实际执行、值是否来自旧调用、是否仍适用当前盘面、是否用于搜索或动作、与新增关卡的关系。

### cn04-2fe56bfb_p0_requests.jsonl 变量 B_tips0

读取方式：direct_before_definition；类型：set；定义输出行137，读取输出行139；关卡3。

定义代码：
```python

# local shapes (rot 0), relative to body-bbox min, from level-3 INITIAL frame
Z_body0={(0,2),(0,3),(1,2),(2,0),(2,1),(2,2),(3,0),(4,0),(4,1),(4,2),(5,2),(6,2),(6,3)}
Z_tips0={(0,4),(6,4)}
A_body0={(0,5),(1,0),(1,1),(1,2),(1,3),(1,4),(1,5)}
A_tips0={(0,5),(1,0)}
B_all0={(10,11),(11,10),(11,11),(11,12),(12,10),(12,12),(13,10),(13,12),(14,10),(14,12),(14,13),(14,14),(14,15),(15,10),(15,15),(15,16),(16,10),(16,11),(16,12),(16,13),(16,14),(16,15)}
# normalize by body min (body = all minus tips hook(10,11),tail(15,16))
B_tips_abs={(10,11),(15,16)}
B_body_abs=B_all0-B_tips_abs
mb=(min(p[0] for p in B_body_abs), min(p[1] for p in B_body_abs))
B_body0={(r-mb[0],c-mb[1]) for r,c in B_body_abs}
B_tips0={(r-mb[0],c-mb[1]) for r,c in B_tips_abs}
print('B body min', mb, 'n body', len(B_body0), 'tips', sorted(B_tips0))
for nm,bd,tp in [('Z',Z_body0,Z_tips0),('A',A_body0,A_tips0),('B',B_body0,B_tips0)]:
    mr=min(p[0] for p in bd|tp); Mr=max(p[0] for p in bd|tp); mc=min(p[1] for p in bd|tp); Mc=max(p[1] for p in bd|tp)
    for r_ in range(mr,Mr+1):
        print(nm, ''.join('#' if (r_,c_) in tp else ('B' if (r_,c_) in bd else '.') for c_ in range(mc,Mc+1)))
    print()

```

随后代码：
```python

import itertools
SH={'A':(A_body0,A_tips0),'Z':(Z_body0,Z_tips0),'B':(B_body0,B_tips0)}
CUR={'A':((4,11),0),'Z':((5,7),0),'B':((12,10),0)}
def pose(o,k):
    bd,tp=SH[o]
    b=rotb(bd,k); t=rotb(tp,k)
    m=min(p[0] for p in b); n=min(p[1] for p in b)
    return ({(r-m,c-n) for r,c in b}, [(r-m,c-n) for r,c in t])
PO={}
for o in SH:
    for k in range(4): PO[(o,k)]=pose(o,k)
tips={'A':['a0','a1'],'Z':['z0','z1'],'B':['b0','b1']}
tips_local={'A':list(A_tips0),'Z':list(Z_tips0),'B':list(B_tips0)}
# enumerate matchings
alltips=[('A',0),('A',1),('Z',0),('Z',1),('B',0),('B',1)]
def matchings(items):
    if not items: yield []; return
    a=items[0]
    for i in range(1,len(items)):
        b=items[i]
        rest=items[1:i]+items[i+1:]
        for m in matchings(rest): yield [(a,b)]+m
valid_ms=[]
for m in matchings(alltips):
    if any(x[0]==y[0] for x,y in m): continue
    # object graph must be triangle
    edges=set(frozenset((x[0],y[0])) for x,y in m)
    if len(edges)==3: valid_ms.append(m)
print('valid matchings', len(valid_ms))
sols=[]
for kA,kZ,kB in itertools.product(range(4),repeat=3):
    P={'A':PO[('A',kA)],'Z':PO[('Z',kZ)],'B':PO[('B',kB)]}
    for m in valid_ms:
        # build equations t_P - t_Q = rot(tq) - rot(tp)
        # solve via BFS over objects
        eqs=[]
        for (x,i),(y,j) in m:
            tp=P[x][1][i]; tq=P[y][1][j]
            eqs.append((x,y,(tq[0]-tp[0], tq[1]-tp[1])))   # t_P + tp = t_Q + tq -> t_Q = t_P + (tp - tq)
        # t_A = base; compute t_Z, t_B
        rel={'A':(0,0)}
        ok=True
        pend=list(eqs)
        while pend:
            nxt=[]
            for (x,y,d) in pend:
                if x in rel and y in rel:
                    if (rel[y][0]-rel[x][0], rel[y][1]-rel[x][1]) != d: ok=False; break
                elif x in rel:
                    rel[y]=(rel[x][0]+d[0], rel[x][1]+d[1])
                elif y in rel:
                    rel[x]=(rel[y][0]-d[0], rel[y][1]-d[1])
                else: nxt.append((x,y,d))
            if not ok: break
            pend=nxt
            if not nxt and pend: ok=False; break
        if not ok: continue
        # overlaps & bbox in relative frame
        absb={o:{(p[0]+rel[o][0],p[1]+rel[o][1]) for p in P[o][0]} for o in P}
        abst={o:{(p[0]+rel[o][0],p[1]+rel[o][1]) for p in P[o][1]} for o in P}
        jointcells=set()
        for (x,i),(y,j) in m:
            tp=P[x][1][i]; tq=P[y][1][j]
            jointcells.add((tp[0]+rel[x][0], tp[1]+rel[x][1]))
        ov=set()
        for a,b in [('A','Z'),('A','B'),('Z','B')]:
            ov |= (absb[a] & absb[b])
        if ov != jointcells: continue
        allc=set().union(*absb.values())
        mr=min(p[0] for p in allc); Mr=max(p[0] for p in allc); mc=min(p[1] for p in allc); Mc=max(p[1] for p in allc)
        if Mr-mr>20 or Mc-mc>20: continue
        sols.append(((kA,kZ,kB), tuple(m), tuple(sorted(jointcells)), (mr,mc,Mr,Mc)))
print('candidate assemblies:', len(sols))
for s in sols[:12]: print(s[0], s[2], s[3])

```

实际随后输出：
```text
valid matchings 8
candidate assemblies: 0

```

人工确认：读取语句是否实际执行、值是否来自旧调用、是否仍适用当前盘面、是否用于搜索或动作、与新增关卡的关系。

### cn04-2fe56bfb_p0_requests.jsonl 变量 Z_body0

读取方式：direct_before_definition；类型：set；定义输出行137，读取输出行139；关卡3。

定义代码：
```python

# local shapes (rot 0), relative to body-bbox min, from level-3 INITIAL frame
Z_body0={(0,2),(0,3),(1,2),(2,0),(2,1),(2,2),(3,0),(4,0),(4,1),(4,2),(5,2),(6,2),(6,3)}
Z_tips0={(0,4),(6,4)}
A_body0={(0,5),(1,0),(1,1),(1,2),(1,3),(1,4),(1,5)}
A_tips0={(0,5),(1,0)}
B_all0={(10,11),(11,10),(11,11),(11,12),(12,10),(12,12),(13,10),(13,12),(14,10),(14,12),(14,13),(14,14),(14,15),(15,10),(15,15),(15,16),(16,10),(16,11),(16,12),(16,13),(16,14),(16,15)}
# normalize by body min (body = all minus tips hook(10,11),tail(15,16))
B_tips_abs={(10,11),(15,16)}
B_body_abs=B_all0-B_tips_abs
mb=(min(p[0] for p in B_body_abs), min(p[1] for p in B_body_abs))
B_body0={(r-mb[0],c-mb[1]) for r,c in B_body_abs}
B_tips0={(r-mb[0],c-mb[1]) for r,c in B_tips_abs}
print('B body min', mb, 'n body', len(B_body0), 'tips', sorted(B_tips0))
for nm,bd,tp in [('Z',Z_body0,Z_tips0),('A',A_body0,A_tips0),('B',B_body0,B_tips0)]:
    mr=min(p[0] for p in bd|tp); Mr=max(p[0] for p in bd|tp); mc=min(p[1] for p in bd|tp); Mc=max(p[1] for p in bd|tp)
    for r_ in range(mr,Mr+1):
        print(nm, ''.join('#' if (r_,c_) in tp else ('B' if (r_,c_) in bd else '.') for c_ in range(mc,Mc+1)))
    print()

```

随后代码：
```python

import itertools
SH={'A':(A_body0,A_tips0),'Z':(Z_body0,Z_tips0),'B':(B_body0,B_tips0)}
CUR={'A':((4,11),0),'Z':((5,7),0),'B':((12,10),0)}
def pose(o,k):
    bd,tp=SH[o]
    b=rotb(bd,k); t=rotb(tp,k)
    m=min(p[0] for p in b); n=min(p[1] for p in b)
    return ({(r-m,c-n) for r,c in b}, [(r-m,c-n) for r,c in t])
PO={}
for o in SH:
    for k in range(4): PO[(o,k)]=pose(o,k)
tips={'A':['a0','a1'],'Z':['z0','z1'],'B':['b0','b1']}
tips_local={'A':list(A_tips0),'Z':list(Z_tips0),'B':list(B_tips0)}
# enumerate matchings
alltips=[('A',0),('A',1),('Z',0),('Z',1),('B',0),('B',1)]
def matchings(items):
    if not items: yield []; return
    a=items[0]
    for i in range(1,len(items)):
        b=items[i]
        rest=items[1:i]+items[i+1:]
        for m in matchings(rest): yield [(a,b)]+m
valid_ms=[]
for m in matchings(alltips):
    if any(x[0]==y[0] for x,y in m): continue
    # object graph must be triangle
    edges=set(frozenset((x[0],y[0])) for x,y in m)
    if len(edges)==3: valid_ms.append(m)
print('valid matchings', len(valid_ms))
sols=[]
for kA,kZ,kB in itertools.product(range(4),repeat=3):
    P={'A':PO[('A',kA)],'Z':PO[('Z',kZ)],'B':PO[('B',kB)]}
    for m in valid_ms:
        # build equations t_P - t_Q = rot(tq) - rot(tp)
        # solve via BFS over objects
        eqs=[]
        for (x,i),(y,j) in m:
            tp=P[x][1][i]; tq=P[y][1][j]
            eqs.append((x,y,(tq[0]-tp[0], tq[1]-tp[1])))   # t_P + tp = t_Q + tq -> t_Q = t_P + (tp - tq)
        # t_A = base; compute t_Z, t_B
        rel={'A':(0,0)}
        ok=True
        pend=list(eqs)
        while pend:
            nxt=[]
            for (x,y,d) in pend:
                if x in rel and y in rel:
                    if (rel[y][0]-rel[x][0], rel[y][1]-rel[x][1]) != d: ok=False; break
                elif x in rel:
                    rel[y]=(rel[x][0]+d[0], rel[x][1]+d[1])
                elif y in rel:
                    rel[x]=(rel[y][0]-d[0], rel[y][1]-d[1])
                else: nxt.append((x,y,d))
            if not ok: break
            pend=nxt
            if not nxt and pend: ok=False; break
        if not ok: continue
        # overlaps & bbox in relative frame
        absb={o:{(p[0]+rel[o][0],p[1]+rel[o][1]) for p in P[o][0]} for o in P}
        abst={o:{(p[0]+rel[o][0],p[1]+rel[o][1]) for p in P[o][1]} for o in P}
        jointcells=set()
        for (x,i),(y,j) in m:
            tp=P[x][1][i]; tq=P[y][1][j]
            jointcells.add((tp[0]+rel[x][0], tp[1]+rel[x][1]))
        ov=set()
        for a,b in [('A','Z'),('A','B'),('Z','B')]:
            ov |= (absb[a] & absb[b])
        if ov != jointcells: continue
        allc=set().union(*absb.values())
        mr=min(p[0] for p in allc); Mr=max(p[0] for p in allc); mc=min(p[1] for p in allc); Mc=max(p[1] for p in allc)
        if Mr-mr>20 or Mc-mc>20: continue
        sols.append(((kA,kZ,kB), tuple(m), tuple(sorted(jointcells)), (mr,mc,Mr,Mc)))
print('candidate assemblies:', len(sols))
for s in sols[:12]: print(s[0], s[2], s[3])

```

实际随后输出：
```text
valid matchings 8
candidate assemblies: 0

```

人工确认：读取语句是否实际执行、值是否来自旧调用、是否仍适用当前盘面、是否用于搜索或动作、与新增关卡的关系。

### cn04-2fe56bfb_p0_requests.jsonl 变量 Z_tips0

读取方式：direct_before_definition；类型：set；定义输出行137，读取输出行139；关卡3。

定义代码：
```python

# local shapes (rot 0), relative to body-bbox min, from level-3 INITIAL frame
Z_body0={(0,2),(0,3),(1,2),(2,0),(2,1),(2,2),(3,0),(4,0),(4,1),(4,2),(5,2),(6,2),(6,3)}
Z_tips0={(0,4),(6,4)}
A_body0={(0,5),(1,0),(1,1),(1,2),(1,3),(1,4),(1,5)}
A_tips0={(0,5),(1,0)}
B_all0={(10,11),(11,10),(11,11),(11,12),(12,10),(12,12),(13,10),(13,12),(14,10),(14,12),(14,13),(14,14),(14,15),(15,10),(15,15),(15,16),(16,10),(16,11),(16,12),(16,13),(16,14),(16,15)}
# normalize by body min (body = all minus tips hook(10,11),tail(15,16))
B_tips_abs={(10,11),(15,16)}
B_body_abs=B_all0-B_tips_abs
mb=(min(p[0] for p in B_body_abs), min(p[1] for p in B_body_abs))
B_body0={(r-mb[0],c-mb[1]) for r,c in B_body_abs}
B_tips0={(r-mb[0],c-mb[1]) for r,c in B_tips_abs}
print('B body min', mb, 'n body', len(B_body0), 'tips', sorted(B_tips0))
for nm,bd,tp in [('Z',Z_body0,Z_tips0),('A',A_body0,A_tips0),('B',B_body0,B_tips0)]:
    mr=min(p[0] for p in bd|tp); Mr=max(p[0] for p in bd|tp); mc=min(p[1] for p in bd|tp); Mc=max(p[1] for p in bd|tp)
    for r_ in range(mr,Mr+1):
        print(nm, ''.join('#' if (r_,c_) in tp else ('B' if (r_,c_) in bd else '.') for c_ in range(mc,Mc+1)))
    print()

```

随后代码：
```python

import itertools
SH={'A':(A_body0,A_tips0),'Z':(Z_body0,Z_tips0),'B':(B_body0,B_tips0)}
CUR={'A':((4,11),0),'Z':((5,7),0),'B':((12,10),0)}
def pose(o,k):
    bd,tp=SH[o]
    b=rotb(bd,k); t=rotb(tp,k)
    m=min(p[0] for p in b); n=min(p[1] for p in b)
    return ({(r-m,c-n) for r,c in b}, [(r-m,c-n) for r,c in t])
PO={}
for o in SH:
    for k in range(4): PO[(o,k)]=pose(o,k)
tips={'A':['a0','a1'],'Z':['z0','z1'],'B':['b0','b1']}
tips_local={'A':list(A_tips0),'Z':list(Z_tips0),'B':list(B_tips0)}
# enumerate matchings
alltips=[('A',0),('A',1),('Z',0),('Z',1),('B',0),('B',1)]
def matchings(items):
    if not items: yield []; return
    a=items[0]
    for i in range(1,len(items)):
        b=items[i]
        rest=items[1:i]+items[i+1:]
        for m in matchings(rest): yield [(a,b)]+m
valid_ms=[]
for m in matchings(alltips):
    if any(x[0]==y[0] for x,y in m): continue
    # object graph must be triangle
    edges=set(frozenset((x[0],y[0])) for x,y in m)
    if len(edges)==3: valid_ms.append(m)
print('valid matchings', len(valid_ms))
sols=[]
for kA,kZ,kB in itertools.product(range(4),repeat=3):
    P={'A':PO[('A',kA)],'Z':PO[('Z',kZ)],'B':PO[('B',kB)]}
    for m in valid_ms:
        # build equations t_P - t_Q = rot(tq) - rot(tp)
        # solve via BFS over objects
        eqs=[]
        for (x,i),(y,j) in m:
            tp=P[x][1][i]; tq=P[y][1][j]
            eqs.append((x,y,(tq[0]-tp[0], tq[1]-tp[1])))   # t_P + tp = t_Q + tq -> t_Q = t_P + (tp - tq)
        # t_A = base; compute t_Z, t_B
        rel={'A':(0,0)}
        ok=True
        pend=list(eqs)
        while pend:
            nxt=[]
            for (x,y,d) in pend:
                if x in rel and y in rel:
                    if (rel[y][0]-rel[x][0], rel[y][1]-rel[x][1]) != d: ok=False; break
                elif x in rel:
                    rel[y]=(rel[x][0]+d[0], rel[x][1]+d[1])
                elif y in rel:
                    rel[x]=(rel[y][0]-d[0], rel[y][1]-d[1])
                else: nxt.append((x,y,d))
            if not ok: break
            pend=nxt
            if not nxt and pend: ok=False; break
        if not ok: continue
        # overlaps & bbox in relative frame
        absb={o:{(p[0]+rel[o][0],p[1]+rel[o][1]) for p in P[o][0]} for o in P}
        abst={o:{(p[0]+rel[o][0],p[1]+rel[o][1]) for p in P[o][1]} for o in P}
        jointcells=set()
        for (x,i),(y,j) in m:
            tp=P[x][1][i]; tq=P[y][1][j]
            jointcells.add((tp[0]+rel[x][0], tp[1]+rel[x][1]))
        ov=set()
        for a,b in [('A','Z'),('A','B'),('Z','B')]:
            ov |= (absb[a] & absb[b])
        if ov != jointcells: continue
        allc=set().union(*absb.values())
        mr=min(p[0] for p in allc); Mr=max(p[0] for p in allc); mc=min(p[1] for p in allc); Mc=max(p[1] for p in allc)
        if Mr-mr>20 or Mc-mc>20: continue
        sols.append(((kA,kZ,kB), tuple(m), tuple(sorted(jointcells)), (mr,mc,Mr,Mc)))
print('candidate assemblies:', len(sols))
for s in sols[:12]: print(s[0], s[2], s[3])

```

实际随后输出：
```text
valid matchings 8
candidate assemblies: 0

```

人工确认：读取语句是否实际执行、值是否来自旧调用、是否仍适用当前盘面、是否用于搜索或动作、与新增关卡的关系。

### cn04-2fe56bfb_p0_requests.jsonl 变量 SH

读取方式：direct_before_definition；类型：dict；定义输出行139，读取输出行143；关卡3。

定义代码：
```python

import itertools
SH={'A':(A_body0,A_tips0),'Z':(Z_body0,Z_tips0),'B':(B_body0,B_tips0)}
CUR={'A':((4,11),0),'Z':((5,7),0),'B':((12,10),0)}
def pose(o,k):
    bd,tp=SH[o]
    b=rotb(bd,k); t=rotb(tp,k)
    m=min(p[0] for p in b); n=min(p[1] for p in b)
    return ({(r-m,c-n) for r,c in b}, [(r-m,c-n) for r,c in t])
PO={}
for o in SH:
    for k in range(4): PO[(o,k)]=pose(o,k)
tips={'A':['a0','a1'],'Z':['z0','z1'],'B':['b0','b1']}
tips_local={'A':list(A_tips0),'Z':list(Z_tips0),'B':list(B_tips0)}
# enumerate matchings
alltips=[('A',0),('A',1),('Z',0),('Z',1),('B',0),('B',1)]
def matchings(items):
    if not items: yield []; return
    a=items[0]
    for i in range(1,len(items)):
        b=items[i]
        rest=items[1:i]+items[i+1:]
        for m in matchings(rest): yield [(a,b)]+m
valid_ms=[]
for m in matchings(alltips):
    if any(x[0]==y[0] for x,y in m): continue
    # object graph must be triangle
    edges=set(frozenset((x[0],y[0])) for x,y in m)
    if len(edges)==3: valid_ms.append(m)
print('valid matchings', len(valid_ms))
sols=[]
for kA,kZ,kB in itertools.product(range(4),repeat=3):
    P={'A':PO[('A',kA)],'Z':PO[('Z',kZ)],'B':PO[('B',kB)]}
    for m in valid_ms:
        # build equations t_P - t_Q = rot(tq) - rot(tp)
        # solve via BFS over objects
        eqs=[]
        for (x,i),(y,j) in m:
            tp=P[x][1][i]; tq=P[y][1][j]
            eqs.append((x,y,(tq[0]-tp[0], tq[1]-tp[1])))   # t_P + tp = t_Q + tq -> t_Q = t_P + (tp - tq)
        # t_A = base; compute t_Z, t_B
        rel={'A':(0,0)}
        ok=True
        pend=list(eqs)
        while pend:
            nxt=[]
            for (x,y,d) in pend:
                if x in rel and y in rel:
                    if (rel[y][0]-rel[x][0], rel[y][1]-rel[x][1]) != d: ok=False; break
                elif x in rel:
                    rel[y]=(rel[x][0]+d[0], rel[x][1]+d[1])
                elif y in rel:
                    rel[x]=(rel[y][0]-d[0], rel[y][1]-d[1])
                else: nxt.append((x,y,d))
            if not ok: break
            pend=nxt
            if not nxt and pend: ok=False; break
        if not ok: continue
        # overlaps & bbox in relative frame
        absb={o:{(p[0]+rel[o][0],p[1]+rel[o][1]) for p in P[o][0]} for o in P}
        abst={o:{(p[0]+rel[o][0],p[1]+rel[o][1]) for p in P[o][1]} for o in P}
        jointcells=set()
        for (x,i),(y,j) in m:
            tp=P[x][1][i]; tq=P[y][1][j]
            jointcells.add((tp[0]+rel[x][0], tp[1]+rel[x][1]))
        ov=set()
        for a,b in [('A','Z'),('A','B'),('Z','B')]:
            ov |= (absb[a] & absb[b])
        if ov != jointcells: continue
        allc=set().union(*absb.values())
        mr=min(p[0] for p in allc); Mr=max(p[0] for p in allc); mc=min(p[1] for p in allc); Mc=max(p[1] for p in allc)
        if Mr-mr>20 or Mc-mc>20: continue
        sols.append(((kA,kZ,kB), tuple(m), tuple(sorted(jointcells)), (mr,mc,Mr,Mc)))
print('candidate assemblies:', len(sols))
for s in sols[:12]: print(s[0], s[2], s[3])

```

随后代码：
```python

def pose2(o,k):
    bd,tp=SH[o]
    full=bd|tp
    fr=rotset(full,k)   # rotation-invariant normalized set of the union
    # need mapping: use rotb on union with consistent normalization
    def rot(pts,k):
        return rotb(set(pts),k)
    fb=rot(full,k); fbd=rot(bd,k); ftp=rot(tp,k)
    m=min(p[0] for p in fb); n=min(p[1] for p in fb)
    norm=lambda S:{(r-m,c-n) for r,c in S}
    return (norm(fbd), sorted(norm(ftp)))
PO2={}
for o in SH:
    for k in range(4): PO2[(o,k)]=pose2(o,k)
for o in ['A','Z','B']:
    for k in range(4):
        bd,tp=PO2[(o,k)]
        print(o,k,'tips',tp)
    print()

```

实际随后输出：
```text
A 0 tips [(0, 5), (1, 0)]
A 1 tips [(0, 0), (5, 1)]
A 2 tips [(0, 5), (1, 0)]
A 3 tips [(0, 0), (5, 1)]

Z 0 tips [(0, 4), (6, 4)]
Z 1 tips [(4, 0), (4, 6)]
Z 2 tips [(0, 0), (6, 0)]
Z 3 tips [(0, 0), (0, 6)]

B 0 tips [(0, 1), (5, 6)]
B 1 tips [(1, 6), (6, 1)]
B 2 tips [(1, 0), (6, 5)]
B 3 tips [(0, 5), (5, 0)]


```

人工确认：读取语句是否实际执行、值是否来自旧调用、是否仍适用当前盘面、是否用于搜索或动作、与新增关卡的关系。

### cn04-2fe56bfb_p0_requests.jsonl 变量 cands

读取方式：direct_before_definition；类型：list；定义输出行147，读取输出行151；关卡3。

定义代码：
```python

def tipsets(o,k,base=(0,0)):
    bd,tp=PO2[(o,k)]
    return {(base[0]+r,base[1]+c) for r,c in tp}, {(base[0]+r,base[1]+c) for r,c in bd}
bestcnt=0; bestcfg=None
cands=[]
for kA,kZ,kB in itertools.product(range(4),repeat=3):
    TA,_=tipsets('A',kA)
    TZ0,_=tipsets('Z',kZ); TB0,_=tipsets('B',kB)
    # candidate dz: A tip == Z tip
    dzs={(ta[0]-tz[0], ta[1]-tz[1]) for ta in TA for tz in TZ0}
    for dz in dzs:
        TZ={(p[0]+dz[0],p[1]+dz[1]) for p in TZ0}
        # candidate db: B tip == A tip or B tip == Z tip
        dbs={(ta[0]-tb[0], ta[1]-tb[1]) for ta in TA for tb in TB0} | {(tz[0]-tb[0], tz[1]-tb[1]) for tz in TZ for tb in TB0}
        for db in dbs:
            TB={(p[0]+db[0],p[1]+db[1]) for p in TB0}
            cnt=len((TA&TZ)|(TA&TB)|(TZ&TB))
            if cnt>bestcnt: bestcnt=cnt; bestcfg=(kA,kZ,kB,dz,db)
            if cnt==3: cands.append((kA,kZ,kB,dz,db))
print('max tip-tip coincidences:', bestcnt, bestcfg, 'num 3-configs:', len(cands))

```

随后代码：
```python

def full(o,k,base):
    bd,tp=PO2[(o,k)]
    tp=set(tp)
    return {(base[0]+r,base[1]+c) for r,c in bd}, {(base[0]+r,base[1]+c) for r,c in tp}
out=[]
for (kA,kZ,kB,dz,db) in cands:
    bA,tA=full('A',kA,(0,0)); bZ,tZ=full('Z',kZ,dz); bB,tB=full('B',kB,db)
    joints=(tA&tZ)|(tA&tB)|(tZ&tB)
    ov=(bA&bZ)|(bA&bB)|(bZ&bB)
    allc=bA|bZ|bB
    mr=min(p[0] for p in allc); Mr=max(p[0] for p in allc); mc=min(p[1] for p in allc); Mc=max(p[1] for p in allc)
    out.append((len(ov-joints),(Mr-mr,Mc-mc),(kA,kZ,kB),dz,db,sorted(joints),sorted(ov-joints)[:8]))
out.sort()
for o in out[:6]: print(o)

```

实际随后输出：
```text
(0, (7, 10), (0, 0, 2), (-5, -4), (-6, 0), [(-5, 0), (0, 5), (1, 0)], [])
(0, (7, 10), (0, 2, 0), (0, 5), (1, -1), [(0, 5), (1, 0), (6, 5)], [])
(0, (7, 10), (2, 0, 2), (-5, -4), (-6, 0), [(-5, 0), (0, 5), (1, 0)], [])
(0, (7, 10), (2, 2, 0), (0, 5), (1, -1), [(0, 5), (1, 0), (6, 5)], [])
(0, (10, 7), (1, 1, 3), (-4, 0), (0, 1), [(0, 0), (0, 6), (5, 1)], [])
(0, (10, 7), (1, 3, 1), (5, -5), (-1, -6), [(0, 0), (5, -5), (5, 1)], [])

```

人工确认：读取语句是否实际执行、值是否来自旧调用、是否仍适用当前盘面、是否用于搜索或动作、与新增关卡的关系。

### cn04-2fe56bfb_p0_requests.jsonl 变量 cands

读取方式：direct_before_definition；类型：list；定义输出行147，读取输出行153；关卡3。

定义代码：
```python

def tipsets(o,k,base=(0,0)):
    bd,tp=PO2[(o,k)]
    return {(base[0]+r,base[1]+c) for r,c in tp}, {(base[0]+r,base[1]+c) for r,c in bd}
bestcnt=0; bestcfg=None
cands=[]
for kA,kZ,kB in itertools.product(range(4),repeat=3):
    TA,_=tipsets('A',kA)
    TZ0,_=tipsets('Z',kZ); TB0,_=tipsets('B',kB)
    # candidate dz: A tip == Z tip
    dzs={(ta[0]-tz[0], ta[1]-tz[1]) for ta in TA for tz in TZ0}
    for dz in dzs:
        TZ={(p[0]+dz[0],p[1]+dz[1]) for p in TZ0}
        # candidate db: B tip == A tip or B tip == Z tip
        dbs={(ta[0]-tb[0], ta[1]-tb[1]) for ta in TA for tb in TB0} | {(tz[0]-tb[0], tz[1]-tb[1]) for tz in TZ for tb in TB0}
        for db in dbs:
            TB={(p[0]+db[0],p[1]+db[1]) for p in TB0}
            cnt=len((TA&TZ)|(TA&TB)|(TZ&TB))
            if cnt>bestcnt: bestcnt=cnt; bestcfg=(kA,kZ,kB,dz,db)
            if cnt==3: cands.append((kA,kZ,kB,dz,db))
print('max tip-tip coincidences:', bestcnt, bestcfg, 'num 3-configs:', len(cands))

```

随后代码：
```python

CUR3={'A':(4,11),'Z':(5,7),'B':(11,10)}
res=[]
for (kA,kZ,kB,dz,db) in cands:
    bA,tA=full('A',kA,(0,0)); bZ,tZ=full('Z',kZ,dz); bB,tB=full('B',kB,db)
    ov=(bA&bZ)|(bA&bB)|(bZ&bB); joints=(tA&tZ)|(tA&tB)|(tZ&tB)
    if ov-joints: continue
    allc=bA|bZ|bB
    mr=min(p[0] for p in allc); Mr=max(p[0] for p in allc); mc=min(p[1] for p in allc); Mc=max(p[1] for p in allc)
    # choose T to minimize cost
    bestT=None
    for x in range(1-mr,21-Mr):
        for y in range(1-mc,21-Mc):
            T=(x,y)
            c=(kA+kZ+kB)+abs(x-CUR3['A'][0])+abs(y-CUR3['A'][1]) \
              +abs(x+dz[0]-CUR3['Z'][0])+abs(y+dz[1]-CUR3['Z'][1]) \
              +abs(x+db[0]-CUR3['B'][0])+abs(y+db[1]-CUR3['B'][1])
            if bestT is None or c<bestT[0]: bestT=(c,T)
    if bestT: res.append((bestT[0],(kA,kZ,kB),dz,db,bestT[1]))
res.sort()
for r_ in res[:8]: print('cost',r_[0],'rots',r_[1],'dz',r_[2],'db',r_[3],'T',r_[4])

```

实际随后输出：
```text
cost 16 rots (0, 0, 2) dz (-5, -4) db (-6, 0) T (10, 11)
cost 16 rots (1, 1, 3) dz (-4, 0) db (0, 1) T (9, 9)
cost 17 rots (0, 2, 0) dz (0, 5) db (1, -1) T (5, 11)
cost 18 rots (2, 0, 2) dz (-5, -4) db (-6, 0) T (10, 11)
cost 18 rots (3, 1, 3) dz (-4, 0) db (0, 1) T (9, 9)
cost 19 rots (2, 2, 0) dz (0, 5) db (1, -1) T (5, 11)
cost 22 rots (1, 3, 1) dz (5, -5) db (-1, -6) T (4, 12)
cost 24 rots (3, 3, 1) dz (5, -5) db (-1, -6) T (4, 12)

```

人工确认：读取语句是否实际执行、值是否来自旧调用、是否仍适用当前盘面、是否用于搜索或动作、与新增关卡的关系。

### cn04-2fe56bfb_p0_requests.jsonl 变量 best

读取方式：direct_before_definition；类型：list；定义输出行185，读取输出行187；关卡4。

定义代码：
```python

import itertools, statistics
best=[]
for ks in itertools.product(range(4),repeat=4):
    K=dict(zip(objs,ks)); rotc=sum(ks)
    P={o:P4[(o,K[o])] for o in objs}
    for mm in MS:
        rel={'S':(0,0)}; ok=True
        eqs=[]
        for (x,i),(y,j) in mm:
            tp=P[x][1][i]; tq=P[y][1][j]
            eqs.append((x,y,(tq[0]-tp[0], tq[1]-tp[1])))
        pend=list(eqs)
        while pend and ok:
            nxt=[]
            for (x,y,d) in pend:
                if x in rel and y in rel:
                    if (rel[y][0]-rel[x][0], rel[y][1]-rel[x][1])!=d: ok=False; break
                elif x in rel: rel[y]=(rel[x][0]+d[0], rel[x][1]+d[1])
                elif y in rel: rel[x]=(rel[y][0]-d[0], rel[y][1]-d[1])
                else: nxt.append((x,y,d))
            pend=nxt
            if pend and not nxt: ok=False
        if not ok: continue
        cellsB={o:{(p[0]+rel[o][0],p[1]+rel[o][1]) for p in P[o][0]} for o in objs}
        joint=set()
        for (x,i),(y,j) in mm:
            tp=P[x][1][i]; joint.add((tp[0]+rel[x][0],tp[1]+rel[x][1]))
        if len(joint)!=4: continue
        ov=set()
        for a,b2 in itertools.combinations(objs,2): ov |= (cellsB[a]&cellsB[b2])
        if ov-joint: continue
        allt=set().union(*cellsB.values())
        mr=min(p[0] for p in allt); Mr=max(p[0] for p in allt); mc=min(p[1] for p in allt); Mc=max(p[1] for p in allt)
        if Mr-mr>19 or Mc-mc>19: continue
        lo_x,hi_x=1-mr,20-Mr; lo_y,hi_y=1-mc,20-Mc
        if lo_x>hi_x or lo_y>hi_y: continue
        xs=sorted(CUR5[o][0][0]-rel[o][0] for o in objs); ys=sorted(CUR5[o][0][1]-rel[o][1] for o in objs)
        mx=(xs[1]+xs[2])//2; my=(ys[1]+ys[2])//2
        cx=set([min(max(mx,lo_x),hi_x),min(max(mx-1,lo_x),hi_x),lo_x,hi_x]); cy=set([min(max(my,lo_y),hi_y),min(max(my-1,lo_y),hi_y),lo_y,hi_y])
        bb=None
        for X in cx:
            for Y in cy:
                c=rotc+sum(abs(X+rel[o][0]-CUR5[o][0][0])+abs(Y+rel[o][1]-CUR5[o][0][1]) for o in objs)
                if bb is None or c<bb[0]: bb=(c,(X,Y))
        best.append((bb[0],ks,tuple(mm),bb[1],tuple(rel[o] for o in objs)))
best.sort(key=lambda z:z[0])
print('configs',len(best))
for z in best[:6]: print('cost',z[0],'rots',z[1],'T',z[3])

```

随后代码：
```python

z=best[0]; c,ks,mm,T,rel=z
K=dict(zip(objs,ks))
print('cost',c,'rots',ks,'T',T)
P={o:P4[(o,K[o])] for o in objs}
cellsB={o:{(p[0]+T[0]+rel[i][0],p[1]+T[1]+rel[i][1]) for p in P[o][0]} for i,o in enumerate(objs)}
for o in objs: print(o,'target base',(T[0]+rel[objs.index(o)][0],T[1]+rel[objs.index(o)][1]),'cur',CUR5[o][0],'rot',K[o])
jn=set()
for (x,i),(y,j) in mm:
    tp=P[x][1][i]; jn.add((tp[0]+T[0]+rel[objs.index(x)][0], tp[1]+T[1]+rel[objs.index(x)][1]))
print('joints',sorted(jn))
allt=set().union(*cellsB.values())
mr=min(p[0] for p in allt); Mr=max(p[0] for p in allt); mc=min(p[1] for p in allt); Mc=max(p[1] for p in allt)
for r_ in range(mr,Mr+1):
    row=''
    for c2 in range(mc,Mc+1):
        ch='J' if (r_,c2) in jn else next((o for o in objs if (r_,c2) in cellsB[o]),'.')
        row+= ch if ch=='J' else ch.lower()
    print(r_,row)

```

实际随后输出：
```text
cost 43 rots (3, 0, 0, 0) T (12, 14)
S target base (12, 14) cur (4, 3) rot 3
N target base (7, 9) cur (7, 12) rot 0
Y target base (7, 7) cur (16, 6) rot 0
O target base (12, 9) cur (14, 15) rot 0
joints [(7, 9), (7, 13), (12, 19), (17, 21)]
7 yJn.nJ.......
8 ..n.n........
9 ..n.n........
10 ..nnn........
11 .............
12 ..ooo.sssssJ.
13 ..o.o.s...s..
14 ..o.o.s.s.s..
15 ..o.o.s.ssss.
16 ..o.o.s......
17 ..ooo.sssssss

```

人工确认：读取语句是否实际执行、值是否来自旧调用、是否仍适用当前盘面、是否用于搜索或动作、与新增关卡的关系。

### cn04-2fe56bfb_p0_requests.jsonl 变量 best

读取方式：direct_before_definition；类型：list；定义输出行185，读取输出行193；关卡4。

定义代码：
```python

import itertools, statistics
best=[]
for ks in itertools.product(range(4),repeat=4):
    K=dict(zip(objs,ks)); rotc=sum(ks)
    P={o:P4[(o,K[o])] for o in objs}
    for mm in MS:
        rel={'S':(0,0)}; ok=True
        eqs=[]
        for (x,i),(y,j) in mm:
            tp=P[x][1][i]; tq=P[y][1][j]
            eqs.append((x,y,(tq[0]-tp[0], tq[1]-tp[1])))
        pend=list(eqs)
        while pend and ok:
            nxt=[]
            for (x,y,d) in pend:
                if x in rel and y in rel:
                    if (rel[y][0]-rel[x][0], rel[y][1]-rel[x][1])!=d: ok=False; break
                elif x in rel: rel[y]=(rel[x][0]+d[0], rel[x][1]+d[1])
                elif y in rel: rel[x]=(rel[y][0]-d[0], rel[y][1]-d[1])
                else: nxt.append((x,y,d))
            pend=nxt
            if pend and not nxt: ok=False
        if not ok: continue
        cellsB={o:{(p[0]+rel[o][0],p[1]+rel[o][1]) for p in P[o][0]} for o in objs}
        joint=set()
        for (x,i),(y,j) in mm:
            tp=P[x][1][i]; joint.add((tp[0]+rel[x][0],tp[1]+rel[x][1]))
        if len(joint)!=4: continue
        ov=set()
        for a,b2 in itertools.combinations(objs,2): ov |= (cellsB[a]&cellsB[b2])
        if ov-joint: continue
        allt=set().union(*cellsB.values())
        mr=min(p[0] for p in allt); Mr=max(p[0] for p in allt); mc=min(p[1] for p in allt); Mc=max(p[1] for p in allt)
        if Mr-mr>19 or Mc-mc>19: continue
        lo_x,hi_x=1-mr,20-Mr; lo_y,hi_y=1-mc,20-Mc
        if lo_x>hi_x or lo_y>hi_y: continue
        xs=sorted(CUR5[o][0][0]-rel[o][0] for o in objs); ys=sorted(CUR5[o][0][1]-rel[o][1] for o in objs)
        mx=(xs[1]+xs[2])//2; my=(ys[1]+ys[2])//2
        cx=set([min(max(mx,lo_x),hi_x),min(max(mx-1,lo_x),hi_x),lo_x,hi_x]); cy=set([min(max(my,lo_y),hi_y),min(max(my-1,lo_y),hi_y),lo_y,hi_y])
        bb=None
        for X in cx:
            for Y in cy:
                c=rotc+sum(abs(X+rel[o][0]-CUR5[o][0][0])+abs(Y+rel[o][1]-CUR5[o][0][1]) for o in objs)
                if bb is None or c<bb[0]: bb=(c,(X,Y))
        best.append((bb[0],ks,tuple(mm),bb[1],tuple(rel[o] for o in objs)))
best.sort(key=lambda z:z[0])
print('configs',len(best))
for z in best[:6]: print('cost',z[0],'rots',z[1],'T',z[3])

```

随后代码：
```python

z=best[0]; cost,ks,mm,T,relT=z
rel=dict(zip(objs,relT))
K=dict(zip(objs,ks))
print('cost',cost,'T',T,'rel',rel,'rots',K)
P={o:P4[(o,K[o])] for o in objs}
cellsB={}; cellsT={}
for o in objs:
    b0=T[0]+rel[o][0]; b1=T[1]+rel[o][1]
    cellsB[o]={(b0+r,b1+c) for r,c in P[o][0]}
    cellsT[o]={(b0+r,b1+c) for r,c in P[o][1]}
    print(o,'base',(b0,b1),'cur',CUR5[o][0],'rot',K[o],'tips',sorted(cellsT[o]))
pairs=[]
for (x,i),(y,j) in mm: pairs.append(((x,i),(y,j)))
print('matching',pairs)
allt=set().union(*cellsB.values())
mc=min(p[1] for p in allt); mr=min(p[0] for p in allt)
print('min row/col',mr,mc)
jn={(r,c) for o in objs for (r,c) in cellsT[o] if any((r,c) in cellsT[q] for q in objs if q!=o)}
print('tip-tip joints', sorted(jn))
for r_ in range(mr,max(p[0] for p in allt)+1):
    row=''
    for c2 in range(mc,max(p[1] for p in allt)+1):
        if (r_,c2) in jn: row+='J'
        else:
            hit=[o for o in objs if (r_,c2) in cellsB[o]]
            row+= hit[0].lower() if hit else '.'
    print(f'{r_:2d} '+row)

```

实际随后输出：
```text
cost 43 T (12, 14) rel {'S': (0, 0), 'N': (-5, -5), 'Y': (-5, -7), 'O': (0, -5)} rots {'S': 3, 'N': 0, 'Y': 0, 'O': 0}
S base (12, 14) cur (4, 3) rot 3 tips [(12, 19), (17, 21)]
N base (7, 9) cur (7, 12) rot 0 tips [(7, 9), (7, 13)]
Y base (7, 7) cur (16, 6) rot 0 tips [(7, 7), (7, 9)]
O base (12, 9) cur (14, 15) rot 0 tips [(12, 9), (17, 9)]
matching [(('S', 0), ('O', 0)), (('S', 1), ('Y', 0)), (('N', 0), ('O', 1)), (('N', 1), ('Y', 1))]
min row/col 7 8
tip-tip joints [(7, 9)]
 7 yJn.n........
 8 ..n.n........
 9 ..n.n........
10 ..nnn........
11 .............
12 ..ooo.sssss..
13 ..o.o.s...s..
14 ..o.o.s.s.s..
15 ..o.o.s.ssss.
16 ..o.o.s......
17 ..ooo.sssssss

```

人工确认：读取语句是否实际执行、值是否来自旧调用、是否仍适用当前盘面、是否用于搜索或动作、与新增关卡的关系。

### cn04-2fe56bfb_p0_requests.jsonl 变量 res

读取方式：direct_before_definition；类型：list；定义输出行195，读取输出行197；关卡4。

定义代码：
```python

def solve4(ks, mm):
    P={o:P4[(o,ks[i])] for i,o in enumerate(objs)}
    rel={'S':(0,0)}; ok=True
    eqs=[]
    for (x,i),(y,j) in mm:
        tp=P[x][1][i]; tq=P[y][1][j]
        eqs.append((x,y,(tp[0]-tq[0], tp[1]-tq[1])))   # t_Q = t_P + (tp - tq)
    pend=list(eqs)
    while pend and ok:
        nxt=[]
        for (x,y,d) in pend:
            if x in rel and y in rel:
                if (rel[y][0]-rel[x][0],rel[y][1]-rel[x][1])!=d: ok=False; break
            elif x in rel: rel[y]=(rel[x][0]+d[0],rel[x][1]+d[1])
            elif y in rel: rel[x]=(rel[y][0]-d[0],rel[y][1]-d[1])
            else: nxt.append((x,y,d))
        pend=nxt
        if pend and not nxt: ok=False
    return (ok, rel, P)
res=[]
for ks in itertools.product(range(4),repeat=4):
    ok_all=True
    for mm in MS:
        ok,rel,P=solve4(ks,mm)
        if not ok: continue
        cellsB={o:{(p[0]+rel[o][0],p[1]+rel[o][1]) for p in P[o][0]} for o in objs}
        cellsT={o:{(p[0]+rel[o][0],p[1]+rel[o][1]) for p in P[o][1]} for o in objs}
        # verify every tip coincides with exactly one other tip
        allt=[(p,o) for o in objs for p in cellsT[o]]
        bad=False
        for p,o in allt:
            partners=[q for q in objs if q!=o and p in cellsT[q]]
            if len(partners)!=1: bad=True; break
        if bad: continue
        ov=set()
        for a,b2 in itertools.combinations(objs,2): ov |= (cellsB[a]&cellsB[b2])
        jt=set(p for p,_ in allt)
        if ov-jt: continue
        cells=allt
        U=set().union(*cellsB.values())
        mr=min(p[0] for p in U); Mr=max(p[0] for p in U); mc=min(p[1] for p in U); Mc=max(p[1] for p in U)
        lo_x,hi_x=1-mr,20-Mr; lo_y,hi_y=1-mc,20-Mc
        if lo_x>hi_x or lo_y>hi_y: continue
        rotc=sum(ks)
        xs=sorted(CUR5[o][0][0]-rel[o][0] for o in objs); ys=sorted(CUR5[o][0][1]-rel[o][1] for o in objs)
        mx=(xs[1]+xs[2])//2; my=(ys[1]+ys[2])//2
        cx=set([min(max(mx,lo_x),hi_x),min(max(mx-1,lo_x),hi_x),lo_x,hi_x]); cy=set([min(max(my,lo_y),hi_y),min(max(my-1,lo_y),hi_y),lo_y,hi_y])
        bb=None
        for X in cx:
            for Y2 in cy:
                cc2=rotc+sum(abs(X+rel[o][0]-CUR5[o][0][0])+abs(Y2+rel[o][1]-CUR5[o][0][1]) for o in objs)
                if bb is None or cc2<bb[0]: bb=(cc2,(X,Y2))
        res.append((bb[0],ks,tuple(mm),bb[1],tuple(rel[o] for o in objs)))
res.sort(key=lambda z:z[0])
print('valid assemblies', len(res))
for z3 in res[:6]: print('cost',z3[0],'rots',z3[1],'T',z3[3])

```

随后代码：
```python

def show_plan(z3):
    cost,ks,mm,T,relT=z3
    rel=dict(zip(objs,relT)); K=dict(zip(objs,ks))
    P={o:P4[(o,K[o])] for o in objs}
    cellsB={}; cellsT={}
    print('=== cost',cost,'rots',K,'T',T)
    for o in objs:
        b0=T[0]+rel[o][0]; b1=T[1]+rel[o][1]
        cellsB[o]={(b0+r,b1+c) for r,c in P[o][0]}; cellsT[o]={(b0+r,b1+c) for r,c in P[o][1]}
        print(' ',o,'base',(b0,b1),'cur',CUR5[o][0],'rot',K[o],'tips',sorted(cellsT[o]),'moves',(b0-CUR5[o][0][0],b1-CUR5[o][0][1]))
    jn={p for o in objs for p in cellsT[o] if any(p in cellsT[q] for q in objs if q!=o)}
    print('  tip-tip joints',sorted(jn))
    U=set().union(*cellsB.values())
    mr=min(p[0] for p in U); Mc=max(p[1] for p in U); mc=min(p[1] for p in U); Mr=max(p[0] for p in U)
    for r_ in range(mr,Mr+1):
        row=''
        for c2 in range(mc,Mc+1):
            if (r_,c2) in jn: row+='J'
            else:
                hit=[o for o in objs if (r_,c2) in cellsB[o]]
                row+=hit[0].lower() if hit else '.'
        print(f'  {r_:2d} '+row)
    return cellsB,cellsT
show_plan(res[0])

```

实际随后输出：
```text
=== cost 26 rots {'S': 0, 'N': 3, 'Y': 1, 'O': 1} T (4, 6)
  S base (4, 6) cur (4, 3) rot 0 tips [(9, 11), (11, 6)] moves (0, 3)
  N base (9, 11) cur (7, 12) rot 3 tips [(9, 11), (13, 11)] moves (2, -1)
  Y base (11, 6) cur (16, 6) rot 1 tips [(11, 6), (13, 6)] moves (-5, 0)
  O base (13, 6) cur (14, 15) rot 1 tips [(13, 6), (13, 11)] moves (-1, -9)
  tip-tip joints [(9, 11), (11, 6), (13, 6), (13, 11)]
   4 ssssss...
   5 s....s...
   6 s.ss.s...
   7 s.s..s...
   8 s.ssss...
   9 s.s..J...
  10 s....nnnn
  11 J.......n
  12 y....nnnn
  13 J....J...
  14 oooooo...
  15 o....o...
  16 oooooo...
({'S': {(4, 9), (4, 6), (8, 9), (10, 6), (9, 8), (8, 6), (6, 11), (6, 8), (5, 6), (4, 8), (4, 11), (8, 11), (8, 8), (7, 6), (4, 7), (4, 10), (5, 11), (9, 6), (8, 10), (6, 6), (7, 11), (6, 9), (7, 8)}, 'N': {(10, 11), (10, 14), (12, 13), (10, 13), (12, 12), (12, 11), (11, 14), (10, 12), (12, 14)}, 'Y': {(12, 6)}, 'O': {(16, 7), (14, 8), (15, 11), (16, 10), (14, 7), (16, 9), (14, 10), (16, 6), (14, 6), (15, 6), (14, 9), (16, 8), (16, 11), (14, 11)}}, {'S': {(9, 11), (11, 6)}, 'N': {(9, 11), (13, 11)}, 'Y': {(13, 6), (11, 6)}, 'O': {(13, 11), (13, 6)}})

```

人工确认：读取语句是否实际执行、值是否来自旧调用、是否仍适用当前盘面、是否用于搜索或动作、与新增关卡的关系。

### cn04-2fe56bfb_p0_requests.jsonl 变量 objs

读取方式：direct_before_definition；类型：computed_value；定义输出行181，读取输出行199；关卡4。

定义代码：
```python

P4={}
for k in OB:
    base,bd,tp=OB[k]
    for kk in range(4): P4[(k,kk)]=pose4(bd,set(tp),kk)
for k in OB: print(k,'tips by rot', [P4[(k,kk)][1] for kk in range(4)])
objs=list(OB)
def all_matchings(items):
    if not items: yield []; return
    a=items[0]
    for i in range(1,len(items)):
        b=items[i]
        rest=items[1:i]+items[i+1:]
        for mm in all_matchings(rest): yield [(a,b)]+mm
tips8=[(o,i) for o in objs for i in (0,1)]
MS=[mm for mm in all_matchings(tips8) if all(x[0]!=y[0] for x,y in mm)]
print('matchings', len(MS))

```

随后代码：
```python

OFF={}
for o in objs:
    for k in range(4):
        bd,tp=P4[(o,k)]
        u=bd|set(tp)
        OFF[(o,k)]=(min(p[0] for p in bd)-min(p[0] for p in u), min(p[1] for p in bd)-min(p[1] for p in u))
print(OFF)
# phase 1: S -> base (4,6) rot0
r=action([{'action':'MOUSE','row':12,'col':9}])
bl=readblk(current_frame)
print('after click S:', {k2:len(v) for k2,v in bl.items()}, 'R', sorted(bl.get('R',set())))
body=bl.get('S',set())
print('S body n', len(body), 'base', (min(p[0] for p in body)-OFF[('S',0)][0], min(p[1] for p in body)-OFF[('S',0)][1]))

```

实际随后输出：
```text
{('S', 0): (0, 0), ('S', 1): (0, 1), ('S', 2): (1, 0), ('S', 3): (0, 0), ('N', 0): (0, 1), ('N', 1): (1, 0), ('N', 2): (0, 1), ('N', 3): (1, 0), ('Y', 0): (0, 1), ('Y', 1): (1, 0), ('Y', 2): (0, 1), ('Y', 3): (1, 0), ('O', 0): (0, 1), ('O', 1): (1, 0), ('O', 2): (0, 0), ('O', 3): (0, 0)}
[action] MOUSE(row=12, col=9) -> effect
after click S: {'W': 1, 'c': 41, 'S': 23, 'R': 2} R [(9, 8), (11, 3)]
S body n 23 base (4, 3)

```

人工确认：读取语句是否实际执行、值是否来自旧调用、是否仍适用当前盘面、是否用于搜索或动作、与新增关卡的关系。

### cn04-2fe56bfb_p0_requests.jsonl 变量 uniq

读取方式：direct_before_definition；类型：list；定义输出行235，读取输出行237；关卡5。

定义代码：
```python

others=['E','H','L']
sols=[]
for kv in range(4):
    vb,vtp=P5[('V',kv)]; vtp=set(vtp)
    for X in others:
        pass
    cand={}
    okall=True
    for X in others:
        cl=[]
        for kX in range(4):
            xb,xtp=P5[(X,kX)]; xtp=set(xtp)
            for xt in xtp:
                for vt in vtp:
                    t=(vt[0]-xt[0], vt[1]-xt[1])
                    xtA={(p[0]+t[0],p[1]+t[1]) for p in xtp}
                    if not xtA<=vtp: continue
                    xbA={(p[0]+t[0],p[1]+t[1]) for p in xb}
                    if xbA & vb: continue
                    if xbA & (vtp-xtA): continue
                    cl.append((kX,t,frozenset(xtA),xbA))
        cand[X]=cl
    if any(not cand[X] for X in others): continue
    for cE in cand['E']:
        for cH in cand['H']:
            if cE[3]&cH[3]: continue
            if (cE[2]&cH[2]): continue
            if cE[3]&cH[2] or cH[3]&cE[2]: continue
            for cL in cand['L']:
                cs=(cE,cH,cL)
                if cL[3]&(cE[3]|cH[3]): continue
                if cL[2]&(cE[2]|cH[2]): continue
                if cL[3]&(cE[2]|cH[2]) or (cL[2]&(cE[3]|cH[3])): continue
                used=cE[2]|cH[2]|cL[2]
                if used!=vtp: continue
                # assembly relative placements: V at (0,0), X at t
                rel={'V':(0,0),'E':cE[1],'H':cH[1],'L':cL[1]}
                rotc=kv+cE[0]+cH[0]+cL[0]
                U=set(vb)|set(vtp)
                for X,c in zip(others,cs): U |= c[3]|c[2]
                mr=min(p[0] for p in U); Mr=max(p[0] for p in U); mc=min(p[1] for p in U); Mc=max(p[1] for p in U)
                lo_x,hi_x=1-mr,20-Mr; lo_y,hi_y=1-mc,20-Mc
                if lo_x>hi_x or lo_y>hi_y: continue
                xs=sorted(CUR6[o][0]-rel[o][0] for o in ['V']+others); ys=sorted(CUR6[o][1]-rel[o][1] for o in ['V']+others)
                mx=(xs[1]+xs[2])//2; my=(ys[1]+ys[2])//2
                cx=set([min(max(mx,lo_x),hi_x),min(max(mx-1,lo_x),hi_x),lo_x,hi_x]); cy=set([min(max(my,lo_y),hi_y),min(max(my-1,lo_y),hi_y),lo_y,hi_y])
                bb=None
                for XX in cx:
                    for YY in cy:
                        cc2=rotc+sum(abs(XX+rel[o][0]-CUR6[o][0])+abs(YY+rel[o][1]-CUR6[o][1]) for o in ['V']+others)
                        if bb is None or cc2<bb[0]: bb=(cc2,(XX,YY))
                sols.append((bb[0],kv,(cE[0],cH[0],cL[0]),bb[1],rel))
sols.sort(key=lambda z:z[0])
print('solutions',len(sols))
seen=set(); uniq=[]
for s in sols:
    key=(s[1],s[2],s[3])
    if key in seen: continue
    seen.add(key); uniq.append(s)
for s in uniq[:8]: print('cost',s[0],'vineRot',s[1],'objRots E,H,L',s[2],'T',s[3],'rel',s[4])

```

随后代码：
```python

s=uniq[0]; cost,kv,rots,T,rel=s
print('cost',cost,'vineRot',kv,'E,H,L rots',rots,'T',T)
names=['V','E','H','L']; ks=[kv]+list(rots)
cellsB={}; cellsT={}
for i,o in enumerate(names):
    bd,tp=P5[(o,ks[i])]; t=(T[0]+rel[o][0],T[1]+rel[o][1])
    cellsB[o]={(t[0]+p[0],t[1]+p[1]) for p in bd}; cellsT[o]={(t[0]+p[0],t[1]+p[1]) for p in tp}
    print(o,'rot',ks[i],'base',t,'cur',CUR6[o],'moves',(t[0]-CUR6[o][0],t[1]-CUR6[o][1]))
jn={p for o in names for p in cellsT[o] if any(p in cellsT[q] for q in names if q!=o)}
print('joints',sorted(jn),'n=',len(jn))
U=set().union(*cellsB.values())
for r_ in range(min(p[0] for p in U),max(p[0] for p in U)+1):
    row=''
    for c2 in range(min(p[1] for p in U),max(p[1] for p in U)+1):
        if (r_,c2) in jn: row+='J'
        else:
            hit=[o for o in names if (r_,c2) in cellsB[o]]
            row+=hit[0].lower() if hit else '.'
    print(f'{r_:2d} '+row)

```

实际随后输出：
```text
cost 38 vineRot 0 E,H,L rots (0, 3, 3) T (8, 8)
V rot 0 base (8, 8) cur (5, 7) moves (3, 1)
E rot 0 base (9, 6) cur (13, 2) moves (-4, 4)
H rot 3 base (8, 10) cur (2, 16) moves (6, -6)
L rot 3 base (12, 12) cur (16, 16) moves (-4, -4)
joints [(8, 10), (9, 8), (10, 11), (11, 8), (12, 13), (13, 8), (14, 12)] n= 7
 8 ...vJhhhh
 9 eeJv....h
10 e..vvJhhh
11 eeJv.....
12 e..vvvvJl
13 eeJv....l
14 ...vvvJll

```

人工确认：读取语句是否实际执行、值是否来自旧调用、是否仍适用当前盘面、是否用于搜索或动作、与新增关卡的关系。

### cn04-2fe56bfb_p0_requests.jsonl 变量 Ycur

读取方式：direct_before_definition；类型：computed_value；定义输出行271，读取输出行279；关卡6。

定义代码：
```python

log=[]
for i in range(3):
    b=brief(current_frame); h=head_cell(b)
    if h is None: log.append('no head'); break
    r=action([click_cell(h)])
    b=brief(current_frame)
    if 'Y' not in b: log.append(('lost Y?', b.keys())); break
    Ycur=set(b['Y']); Yt3=set(b['R'])
    SH,cur,P=rebuild6(Ycur,Yt3); sol=solve6(SH,cur,P)
    log.append((h,len(Ycur),len(Yt3),b.get('W'),'sols',len(sol)))
    if sol: break
for e in log: print(e)

```

随后代码：
```python

Tb2=set(bl['p'])|{(19,14)}; Tt2=set(bl['R'])-{(7,9),(7,12),(7,13),(8,14),(9,7),(12,8),(12,13)}
Tt2={(15,12),(15,15),(18,10)}
SH,cur,P=rebuild6(Ycur,Yt3,Tb2,Tt2)
print('CUR9',cur)
sol=solve6(SH,cur,P); print('sols',len(sol))

```

实际随后输出：
```text
CUR9 {'G': (2, 2), 'O': (2, 16), 'Y': (7, 7), 'T': (15, 10), 'S': (13, 2)}
sols 0

```

人工确认：读取语句是否实际执行、值是否来自旧调用、是否仍适用当前盘面、是否用于搜索或动作、与新增关卡的关系。

### cn04-2fe56bfb_p0_requests.jsonl 变量 Yt3

读取方式：direct_before_definition；类型：computed_value；定义输出行271，读取输出行279；关卡6。

定义代码：
```python

log=[]
for i in range(3):
    b=brief(current_frame); h=head_cell(b)
    if h is None: log.append('no head'); break
    r=action([click_cell(h)])
    b=brief(current_frame)
    if 'Y' not in b: log.append(('lost Y?', b.keys())); break
    Ycur=set(b['Y']); Yt3=set(b['R'])
    SH,cur,P=rebuild6(Ycur,Yt3); sol=solve6(SH,cur,P)
    log.append((h,len(Ycur),len(Yt3),b.get('W'),'sols',len(sol)))
    if sol: break
for e in log: print(e)

```

随后代码：
```python

Tb2=set(bl['p'])|{(19,14)}; Tt2=set(bl['R'])-{(7,9),(7,12),(7,13),(8,14),(9,7),(12,8),(12,13)}
Tt2={(15,12),(15,15),(18,10)}
SH,cur,P=rebuild6(Ycur,Yt3,Tb2,Tt2)
print('CUR9',cur)
sol=solve6(SH,cur,P); print('sols',len(sol))

```

实际随后输出：
```text
CUR9 {'G': (2, 2), 'O': (2, 16), 'Y': (7, 7), 'T': (15, 10), 'S': (13, 2)}
sols 0

```

人工确认：读取语句是否实际执行、值是否来自旧调用、是否仍适用当前盘面、是否用于搜索或动作、与新增关卡的关系。

### cn04-2fe56bfb_p0_requests.jsonl 变量 bl

读取方式：direct_before_definition；类型：computed_value；定义输出行277，读取输出行279；关卡6。

定义代码：
```python

f=current_frame
bl=readblk(f)
print('p', sorted(bl.get('p',set())))
print('R', sorted(bl.get('R',set())))
print('W', sorted(bl.get('W',set())))

```

随后代码：
```python

Tb2=set(bl['p'])|{(19,14)}; Tt2=set(bl['R'])-{(7,9),(7,12),(7,13),(8,14),(9,7),(12,8),(12,13)}
Tt2={(15,12),(15,15),(18,10)}
SH,cur,P=rebuild6(Ycur,Yt3,Tb2,Tt2)
print('CUR9',cur)
sol=solve6(SH,cur,P); print('sols',len(sol))

```

实际随后输出：
```text
CUR9 {'G': (2, 2), 'O': (2, 16), 'Y': (7, 7), 'T': (15, 10), 'S': (13, 2)}
sols 0

```

人工确认：读取语句是否实际执行、值是否来自旧调用、是否仍适用当前盘面、是否用于搜索或动作、与新增关卡的关系。

### cn04-2fe56bfb_p0_requests.jsonl 变量 bl

读取方式：direct_before_definition；类型：computed_value；定义输出行287，读取输出行289；关卡6。

定义代码：
```python

import collections
def grid(fr): return fr.ascii.split('\n')
def blocks_of(S): return S
def blocks2(S): return S
def readblk(fr):
    g=grid(fr); d=collections.defaultdict(set)
    for r,row in enumerate(g):
        for c,ch in enumerate(row):
            if ch in ' \n': continue
            d[ch].add((r//3,c//3))
    return dict(d)
def blocks_from_abs(s): return {(r//3,c//3) for r,c in s}
def expand(bl): return {(r*3+dr,c*3+dc) for (r,c) in bl for dr in range(3) for dc in range(3)}
def rotb(bl,k):
    k%=4
    if k==0: return set(bl)
    if k==1: return {(c,-r) for r,c in bl}
    if k==2: return {(-r,-c) for r,c in bl}
    return {(-c,r) for r,c in bl}
def nrm(bl):
    mr=min(r for r,c in bl); mc=min(c for r,c in bl)
    return frozenset((r-mr,c-mc) for r,c in bl)
def pose4(bd,tp,k):
    bd=rotb(bd,k); tp=rotb(tp,k)
    mr=min(r for r,c in bd); mc=min(c for r,c in bd)
    return (frozenset((r-mr,c-mc) for r,c in bd), frozenset((r-mr,c-mc) for r,c in tp))
def base_of(bd,tp):
    u=set(bd)|set(tp); return (min(p[0] for p in u), min(p[1] for p in u))
def move_to(cur,tgt):
    out=[]; dr=tgt[0]-cur[0]; dc=tgt[1]-cur[1]
    out+= [{'action':'DOWN'}]*max(dr,0)+[{'action':'UP'}]*max(-dr,0)+[{'action':'RIGHT'}]*max(dc,0)+[{'action':'LEFT'}]*max(-dc,0)
    return out
def rotset(s,k): return rotb(s,k)
def to_blocks(s): return s
def norm(s): return nrm(s)
print('helpers ok')
bl=readblk(current_frame)
print({k:len(v) for k,v in bl.items()})

```

随后代码：
```python

print('R',sorted(bl['R']))
print('p',sorted(bl['p']))
print('W',sorted(bl['W']))
# charcoal components
def comps(S):
    S=set(S); out=[]
    while S:
        s=S.pop(); st=[s]; comp={s}
        while st:
            r_,c2=st.pop()
            for d in ((1,0),(-1,0),(0,1),(0,-1)):
                q=(r_+d[0],c2+d[1])
                if q in S: S.remove(q); comp.add(q); st.append(q)
        out.append(comp)
    return out
for i,cp in enumerate(comps(bl['c'])):
    print('c%d'%i,len(cp),sorted(cp) if len(cp)<=22 else 'rows %d-%d cols %d-%d'%(min(p[0] for p in cp),max(p[0] for p in cp),min(p[1] for p in cp),max(p[1] for p in cp)))

```

实际随后输出：
```text
R [(14, 11), (14, 12), (14, 16), (14, 17), (15, 11), (15, 12), (15, 16), (15, 17), (17, 9), (17, 10), (18, 9), (18, 10)]
p [(15, 11), (15, 12), (15, 16), (15, 17), (16, 10), (16, 11), (16, 12), (16, 16), (16, 17), (16, 18), (17, 10), (17, 11), (17, 12), (17, 16), (17, 17), (17, 18), (18, 10), (18, 11), (18, 12), (18, 13), (18, 14), (18, 15), (18, 16), (18, 17), (18, 18), (19, 10), (19, 11), (19, 12), (19, 13), (19, 14), (19, 15), (19, 16), (19, 17), (19, 18)]
W [(0, 5)]
c0 16 [(12, 1), (12, 2), (13, 1), (13, 2), (14, 1), (14, 2), (15, 1), (15, 2), (16, 1), (16, 2), (17, 1), (17, 2), (17, 3), (18, 1), (18, 2), (18, 3)]
c1 62 rows 0-7 cols 1-19
c2 42 rows 6-12 cols 6-14

```

人工确认：读取语句是否实际执行、值是否来自旧调用、是否仍适用当前盘面、是否用于搜索或动作、与新增关卡的关系。

### cn04-2fe56bfb_p0_requests.jsonl 变量 d0

读取方式：direct_before_definition；类型：computed_value；定义输出行303，读取输出行305；关卡6。

定义代码：
```python

def RD(fr):
    d,_=readblk_off(fr,2,2); return d
def show_sel(fr,label):
    d=RD(fr)
    body={k:v for k,v in d.items() if k not in ('R','W','c')}
    print(label,'body',{k:sorted(v) for k,v in body.items()},'tips',sorted(d.get('R',set())),'head',sorted(d.get('W',set())),'cblocks',len(d.get('c',set())))
d0=RD(current_frame)
print('T body',sorted(d0['p'])); print('T tips',sorted(d0['R'])); print('T head',sorted(d0.get('W',set())))
print('c blocks total',len(d0['c']))

```

随后代码：
```python

for i,cp in enumerate(comps(d0['c'])): print('c%d'%i,len(cp),sorted(cp))

```

实际随后输出：
```text
c0 20 [(6, 8), (6, 11), (6, 12), (7, 7), (7, 8), (7, 12), (7, 13), (8, 6), (8, 7), (8, 12), (9, 7), (9, 12), (10, 7), (10, 8), (10, 9), (10, 10), (10, 11), (10, 12), (11, 7), (11, 12)]
c1 7 [(12, 1), (13, 1), (14, 1), (15, 1), (16, 1), (17, 1), (17, 2)]
c2 14 [(1, 1), (1, 2), (1, 3), (1, 4), (1, 5), (2, 1), (2, 5), (3, 1), (3, 5), (4, 1), (5, 1), (5, 2), (5, 3), (6, 1)]
c3 10 [(1, 15), (1, 16), (1, 17), (1, 18), (2, 15), (2, 18), (3, 15), (3, 18), (4, 17), (4, 18)]

```

人工确认：读取语句是否实际执行、值是否来自旧调用、是否仍适用当前盘面、是否用于搜索或动作、与新增关卡的关系。

### cn04-2fe56bfb_p0_requests.jsonl 变量 sols

读取方式：direct_before_definition；类型：computed_value；定义输出行311，读取输出行313；关卡6。

定义代码：
```python

def solve(cap=80000):
    sols=[]; nodes=[0]; done=[True]
    tipcount={o:len(SH[o][1]) for o in NM}
    def rec(pb, free, used, rel):
        nodes[0]+=1
        if nodes[0]>cap: done[0]=False; return
        if len(rel)==5:
            if not free: sols.append((dict(rel),0))
            return
        rem=[o for o in NM if o not in rel]
        if len(free)>sum(tipcount[o] for o in rem): return
        if (len(free)+sum(tipcount[o] for o in rem))%2: return
        for X in rem:
            for kX in range(4):
                if (X,kX) not in P: continue
                xb,xtp=P[(X,kX)]
                seen=set()
                for xt in xtp:
                    for f in free:
                        t=(f[0]-xt[0],f[1]-xt[1])
                        if t in seen: continue
                        seen.add(t)
                        xbA={(p[0]+t[0],p[1]+t[1]) for p in xb}
                        if xbA & (pb|used): continue
                        xtpA={(p[0]+t[0],p[1]+t[1]) for p in xtp}
                        if xtpA & pb: continue
                        if xtpA & (used-free): continue
                        rec(pb|xbA,(free-xtpA)|(xtpA-free),used|xtpA,dict(rel,**{X:(t,kX)}))
    gb,gtp=P[('G',0)]
    rec(set(gb),set(gtp),set(gtp),{'G':((0,0),0)})
    return sols,nodes[0],done[0]
sols,nd,dn=solve(60000)
print('nodes',nd,'complete',dn,'sols',len(sols))

```

随后代码：
```python

def rotpt(p,g):
    r,c=p
    return [(r,c),(c,-r),(-r,-c),(-c,r)][g%4]
def evaluate(sols):
    out=[]
    for rel,_ in sols:
        basecells={}
        for o in NM:
            t,k=rel[o]; bd,tp=P[(o,k)]
            basecells[o]=(frozenset((t[0]+p[0],t[1]+p[1]) for p in bd), frozenset((t[0]+p[0],t[1]+p[1]) for p in tp))
        for g in range(4):
            cells={}; 
            for o in NM:
                bd,tp=basecells[o]
                cells[o]=(frozenset(rotpt(p,g) for p in bd), frozenset(rotpt(p,g) for p in tp))
            allu=set().union(*[set(cells[o][0])|set(cells[o][1]) for o in NM])
            mr=min(p[0] for p in allu); mc=min(p[1] for p in allu)
            MR=max(p[0] for p in allu); MC=max(p[1] for p in allu)
            basex={o:(min(p[0] for p in set(cells[o][0])|set(cells[o][1])), min(p[1] for p in set(cells[o][0])|set(cells[o][1]))) for o in NM}
            relx={o:(basex[o][0]-mr, basex[o][1]-mc) for o in NM}
            rotc=sum((rel[o][1]+g)%4 for o in NM)
            lo_x,hi_x=1-mr,20-MR; lo_y,hi_y=1-mc,20-MC
            if lo_x>hi_x or lo_y>hi_y: continue
            xs=sorted(CUR[o][0]-relx[o][0] for o in NM); ys=sorted(CUR[o][1]-relx[o][1] for o in NM)
            mx=(xs[1]+xs[2])//2; my=(ys[1]+ys[2])//2
            cand_x={min(max(mx,lo_x),hi_x),min(max(mx-1,lo_x),hi_x),lo_x,hi_x}
            cand_y={min(max(my,lo_y),hi_y),min(max(my-1,lo_y),hi_y),lo_y,hi_y}
            bestc=None
            for XX in cand_x:
                for YY in cand_y:
                    c=rotc+sum(abs(XX+relx[o][0]-CUR[o][0])+abs(YY+relx[o][1]-CUR[o][1]) for o in NM)
                    if bestc is None or c<bestc[0]: bestc=(c,(XX,YY))
            out.append((bestc[0],g,rel,bestc[1],relx,{o:(rel[o][1]+g)%4 for o in NM}))
    out.sort(key=lambda z:z[0])
    return out
ev=evaluate(sols)
for e in ev[:5]: print('cost',e[0],'g',e[1],'T',e[3],'rots',e[5])

```

实际随后输出：
```text
cost 30 g 0 T (2, 2) rots {'G': 0, 'O': 0, 'Y': 0, 'T': 0, 'S': 0}
cost 30 g 0 T (2, 2) rots {'G': 0, 'O': 0, 'Y': 0, 'T': 0, 'S': 0}
cost 30 g 0 T (2, 2) rots {'G': 0, 'O': 0, 'Y': 0, 'T': 0, 'S': 0}
cost 30 g 0 T (2, 2) rots {'G': 0, 'O': 0, 'Y': 0, 'T': 0, 'S': 0}
cost 30 g 0 T (2, 2) rots {'G': 0, 'O': 0, 'Y': 0, 'T': 0, 'S': 0}

```

人工确认：读取语句是否实际执行、值是否来自旧调用、是否仍适用当前盘面、是否用于搜索或动作、与新增关卡的关系。

### cn04-2fe56bfb_p0_requests.jsonl 变量 ev

读取方式：direct_before_definition；类型：computed_value；定义输出行313，读取输出行315；关卡6。

定义代码：
```python

def rotpt(p,g):
    r,c=p
    return [(r,c),(c,-r),(-r,-c),(-c,r)][g%4]
def evaluate(sols):
    out=[]
    for rel,_ in sols:
        basecells={}
        for o in NM:
            t,k=rel[o]; bd,tp=P[(o,k)]
            basecells[o]=(frozenset((t[0]+p[0],t[1]+p[1]) for p in bd), frozenset((t[0]+p[0],t[1]+p[1]) for p in tp))
        for g in range(4):
            cells={}; 
            for o in NM:
                bd,tp=basecells[o]
                cells[o]=(frozenset(rotpt(p,g) for p in bd), frozenset(rotpt(p,g) for p in tp))
            allu=set().union(*[set(cells[o][0])|set(cells[o][1]) for o in NM])
            mr=min(p[0] for p in allu); mc=min(p[1] for p in allu)
            MR=max(p[0] for p in allu); MC=max(p[1] for p in allu)
            basex={o:(min(p[0] for p in set(cells[o][0])|set(cells[o][1])), min(p[1] for p in set(cells[o][0])|set(cells[o][1]))) for o in NM}
            relx={o:(basex[o][0]-mr, basex[o][1]-mc) for o in NM}
            rotc=sum((rel[o][1]+g)%4 for o in NM)
            lo_x,hi_x=1-mr,20-MR; lo_y,hi_y=1-mc,20-MC
            if lo_x>hi_x or lo_y>hi_y: continue
            xs=sorted(CUR[o][0]-relx[o][0] for o in NM); ys=sorted(CUR[o][1]-relx[o][1] for o in NM)
            mx=(xs[1]+xs[2])//2; my=(ys[1]+ys[2])//2
            cand_x={min(max(mx,lo_x),hi_x),min(max(mx-1,lo_x),hi_x),lo_x,hi_x}
            cand_y={min(max(my,lo_y),hi_y),min(max(my-1,lo_y),hi_y),lo_y,hi_y}
            bestc=None
            for XX in cand_x:
                for YY in cand_y:
                    c=rotc+sum(abs(XX+relx[o][0]-CUR[o][0])+abs(YY+relx[o][1]-CUR[o][1]) for o in NM)
                    if bestc is None or c<bestc[0]: bestc=(c,(XX,YY))
            out.append((bestc[0],g,rel,bestc[1],relx,{o:(rel[o][1]+g)%4 for o in NM}))
    out.sort(key=lambda z:z[0])
    return out
ev=evaluate(sols)
for e in ev[:5]: print('cost',e[0],'g',e[1],'T',e[3],'rots',e[5])

```

随后代码：
```python

cost,g,rel,T,relx,rots=ev[0]
print('cost',cost,'T',T,'relx',relx)
cellsB={};cellsT={}
for o in NM:
    t=(T[0]+relx[o][0],T[1]+relx[o][1]); bd,tp=P[(o,rots[o])]
    cellsB[o]={(t[0]+p[0],t[1]+p[1]) for p in bd}; cellsT[o]={(t[0]+p[0],t[1]+p[1]) for p in tp}
    print(o,'target base',t,'cur',CUR[o],'moves',move_to(CUR[o],t).count({'action':'DOWN'}),'...')
jn={p for o in NM for p in cellsT[o] if any(p in cellsT[q] for q in NM if q!=o)}
print('joints',len(jn),sorted(jn))
U=set().union(*[cellsB[o]|cellsT[o] for o in NM])
for r_ in range(min(p[0] for p in U),max(p[0] for p in U)+1):
    row=''
    for c2 in range(min(p[1] for p in U),max(p[1] for p in U)+1):
        if (r_,c2) in jn: row+='J'
        else:
            h=[o for o in NM if (r_,c2) in cellsB[o]]
            row+= (h[0] if h else ('*' if (r_,c2) in set().union(*[cellsT[o] for o in NM]) else '.'))
    print(f'{r_:2d} '+row)

```

实际随后输出：
```text
cost 30 T (2, 2) relx {'G': (0, 0), 'O': (0, 7), 'Y': (2, 2), 'T': (7, 1), 'S': (5, 0)}
G target base (2, 2) cur (1, 1) moves 1 ...
O target base (2, 9) cur (1, 15) moves 1 ...
Y target base (4, 4) cur (6, 6) moves 0 ...
T target base (9, 3) cur (14, 9) moves 0 ...
S target base (7, 2) cur (12, 1) moves 0 ...
joints 0 []
 2 GGGGG..OOOO
 3 G...G..O..O
 4 G..**.*Y..O
 5 G.YY...Y**O
 6 GGY....Y...
 7 S.Y....Y...
 8 S.YYYYYY...
 9 S.T....T...
10 STT....TT..
11 ST......T..
12 .TTTTTTTT..

```

人工确认：读取语句是否实际执行、值是否来自旧调用、是否仍适用当前盘面、是否用于搜索或动作、与新增关卡的关系。

### cn04-2fe56bfb_p0_requests.jsonl 变量 ev

读取方式：direct_before_definition；类型：computed_value；定义输出行313，读取输出行317；关卡6。

定义代码：
```python

def rotpt(p,g):
    r,c=p
    return [(r,c),(c,-r),(-r,-c),(-c,r)][g%4]
def evaluate(sols):
    out=[]
    for rel,_ in sols:
        basecells={}
        for o in NM:
            t,k=rel[o]; bd,tp=P[(o,k)]
            basecells[o]=(frozenset((t[0]+p[0],t[1]+p[1]) for p in bd), frozenset((t[0]+p[0],t[1]+p[1]) for p in tp))
        for g in range(4):
            cells={}; 
            for o in NM:
                bd,tp=basecells[o]
                cells[o]=(frozenset(rotpt(p,g) for p in bd), frozenset(rotpt(p,g) for p in tp))
            allu=set().union(*[set(cells[o][0])|set(cells[o][1]) for o in NM])
            mr=min(p[0] for p in allu); mc=min(p[1] for p in allu)
            MR=max(p[0] for p in allu); MC=max(p[1] for p in allu)
            basex={o:(min(p[0] for p in set(cells[o][0])|set(cells[o][1])), min(p[1] for p in set(cells[o][0])|set(cells[o][1]))) for o in NM}
            relx={o:(basex[o][0]-mr, basex[o][1]-mc) for o in NM}
            rotc=sum((rel[o][1]+g)%4 for o in NM)
            lo_x,hi_x=1-mr,20-MR; lo_y,hi_y=1-mc,20-MC
            if lo_x>hi_x or lo_y>hi_y: continue
            xs=sorted(CUR[o][0]-relx[o][0] for o in NM); ys=sorted(CUR[o][1]-relx[o][1] for o in NM)
            mx=(xs[1]+xs[2])//2; my=(ys[1]+ys[2])//2
            cand_x={min(max(mx,lo_x),hi_x),min(max(mx-1,lo_x),hi_x),lo_x,hi_x}
            cand_y={min(max(my,lo_y),hi_y),min(max(my-1,lo_y),hi_y),lo_y,hi_y}
            bestc=None
            for XX in cand_x:
                for YY in cand_y:
                    c=rotc+sum(abs(XX+relx[o][0]-CUR[o][0])+abs(YY+relx[o][1]-CUR[o][1]) for o in NM)
                    if bestc is None or c<bestc[0]: bestc=(c,(XX,YY))
            out.append((bestc[0],g,rel,bestc[1],relx,{o:(rel[o][1]+g)%4 for o in NM}))
    out.sort(key=lambda z:z[0])
    return out
ev=evaluate(sols)
for e in ev[:5]: print('cost',e[0],'g',e[1],'T',e[3],'rots',e[5])

```

随后代码：
```python

cost,g,rel,T,relx,rots=ev[0]
raw={}
for o in NM:
    t,k=rel[o]; bd,tp=P[(o,k)]
    raw[o]=(frozenset((t[0]+p[0],t[1]+p[1]) for p in bd), frozenset((t[0]+p[0],t[1]+p[1]) for p in tp))
allu=set().union(*[set(raw[o][0])|set(raw[o][1]) for o in NM])
mr=min(p[0] for p in allu); mc=min(p[1] for p in allu)
sh=(T[0]-mr,T[1]-mc)
cellsB={};cellsT={}
for o in NM:
    cellsB[o]={(p[0]+sh[0],p[1]+sh[1]) for p in raw[o][0]}
    cellsT[o]={(p[0]+sh[0],p[1]+sh[1]) for p in raw[o][1]}
    print(o,'target base',(T[0]+relx[o][0],T[1]+relx[o][1]),'cur',CUR[o])
jn={p for o in NM for p in cellsT[o] if any(p in cellsT[q] for q in NM if q!=o)}
print('joints',len(jn))
U=set().union(*[cellsB[o]|cellsT[o] for o in NM])
for r_ in range(min(p[0] for p in U),max(p[0] for p in U)+1):
    row=''
    for c2 in range(min(p[1] for p in U),max(p[1] for p in U)+1):
        if (r_,c2) in jn: row+='J'
        else:
            h=[o for o in NM if (r_,c2) in cellsB[o]]
            row+=(h[0] if h else ('*' if (r_,c2) in set().union(*[cellsT[o] for o in NM]) else '.'))
    print(f'{r_:2d} '+row)
print('onboard ok?', all(0<=p[0]<=20 and 0<=p[1]<=20 for p in U))

```

实际随后输出：
```text
G target base (2, 2) cur (1, 1)
O target base (2, 9) cur (1, 15)
Y target base (4, 4) cur (6, 6)
T target base (9, 3) cur (14, 9)
S target base (7, 2) cur (12, 1)
joints 8
 2 GGGGG..OOOO
 3 G...G..O..O
 4 G...J..JY.O
 5 G..YY...YJO
 6 GGJY....Y..
 7 J..Y....Y..
 8 S..YYYYYY..
 9 S..J....J..
10 S..T....T..
11 S.TT....TT.
12 SJT......T.
13 ..TTTTTTTT.
onboard ok? True

```

人工确认：读取语句是否实际执行、值是否来自旧调用、是否仍适用当前盘面、是否用于搜索或动作、与新增关卡的关系。

### cn04-2fe56bfb_p0_requests.jsonl 变量 NM

读取方式：direct_before_definition；类型：list；定义输出行309，读取输出行319；关卡6。

定义代码：
```python

G_body={(1,1),(1,2),(1,3),(1,4),(1,5),(2,1),(2,5),(3,1),(4,1),(5,1),(5,2)}; G_tips={(3,5),(5,3),(6,1)}
O_body={(1,15),(1,16),(1,17),(1,18),(2,15),(2,18),(3,18),(4,18)}; O_tips={(3,15),(4,17)}
Y_body={(6,12),(7,7),(7,8),(7,12),(8,7),(8,12),(9,7),(9,12),(10,7),(10,8),(10,9),(10,10),(10,11),(10,12)}
Y_tips={(6,8),(6,11),(7,13),(8,6),(11,7),(11,12)}
T_body={(15,11),(15,16),(16,10),(16,11),(16,16),(16,17),(17,10),(17,17),(18,10),(18,11),(18,12),(18,13),(18,14),(18,15),(18,16),(18,17)}
T_tips={(14,11),(14,16),(17,9)}
S_body={(13,1),(14,1),(15,1),(16,1),(17,1)}; S_tips={(12,1),(17,2)}
SH={'G':(G_body,G_tips),'O':(O_body,O_tips),'Y':(Y_body,Y_tips),'T':(T_body,T_tips),'S':(S_body,S_tips)}
NM=['G','O','Y','T','S']
CUR={k:base_of(*v) for k,v in SH.items()}
P={}
for k,(bd,tp) in SH.items():
    bb=CUR[k]
    nb={(p[0]-bb[0],p[1]-bb[1]) for p in bd}; nt={(p[0]-bb[0],p[1]-bb[1]) for p in tp}
    ks=[kk for kk in range(4) if all(P.get((k,j))!=pose4(nb,nt,kk) for j in range(kk))]
    for kk in ks: P[(k,kk)]=pose4(nb,nt,kk)
    print(k,'rots',ks,'nbody',len(bd),'ntips',len(tp))
print('CUR',CUR)

```

随后代码：
```python

COL={'G':'N','O':'O','Y':'Y','T':'p','S':'S'}
OFF={}
for o in NM:
    bd,tp=SH[o]
    OFF[o]=(min(p[0] for p in bd)-min(p[0] for p in set(bd)|set(tp)), min(p[1] for p in bd)-min(p[1] for p in set(bd)|set(tp)))
print('OFF',OFF)
def base_now(o):
    d,_=readblk_off(current_frame,2,2)
    B=d.get(COL[o],set())
    if not B: return None
    return (min(p[0] for p in B)-OFF[o][0], min(p[1] for p in B)-OFF[o][1])
targets={'G':(2,2),'O':(2,9),'Y':(4,4),'T':(9,3),'S':(7,2)}
clicks={'G':(3,1),'O':(2,15),'Y':(10,9),'T':(18,13),'S':(14,1)}
plan=[]
for o in ['G','O','Y','T','S']:
    mv=move_to(CUR[o],targets[o])
    plan.append((o,clicks[o],targets[o],[a['action'] for a in mv]))
for p in plan: print(p[0],'click',p[1],'->',p[2],''.join(x[0] for x in p[3]))

```

实际随后输出：
```text
OFF {'G': (0, 0), 'O': (0, 0), 'Y': (0, 1), 'T': (1, 1), 'S': (1, 0)}
G click (3, 1) -> (2, 2) DR
O click (2, 15) -> (2, 9) DLLLLLL
Y click (10, 9) -> (4, 4) UULL
T click (18, 13) -> (9, 3) UUUUULLLLLL
S click (14, 1) -> (7, 2) UUUUUR

```

人工确认：读取语句是否实际执行、值是否来自旧调用、是否仍适用当前盘面、是否用于搜索或动作、与新增关卡的关系。

### r11l-495a7899_p0_requests.jsonl 变量 Btar

读取方式：direct_before_definition；类型：list；定义输出行43，读取输出行45；关卡2。

定义代码：
```python
from itertools import product, permutations
CUR_A = [(6,17),(9,49),(12,24)]   # handle at (6,17) after planned step5 swap
CUR_B = [(51,40),(48,54)]
# chain B targets
Btar=[]
for X in product(range(6,29), range(49,63)):
    Y=(36-X[0],114-X[1])
    if not(1<=Y[0]<64 and 0<=Y[1]<64): continue
    if ok_end(*X) and ok_end(*Y) and ok_hub(18,57,'p'):
        mid=((X[0]+51)//2,(X[1]+40)//2)
        if ok_hub(*mid):  # intermediate hub after moving handle to X (other end (51,40))
            mid2=((X[0]+51)//2,(X[1]+40)//2)
            Btar.append((X,Y))
print('B options', len(Btar), Btar[:6], Btar[-6:] if Btar else None)

```

随后代码：
```python
def mean3(pts):
    return (sum(p[0] for p in pts)//3, sum(p[1] for p in pts)//3)
def disjoint(sets):
    s=set()
    for g in sets:
        for c in g:
            if c in s: return False
            s.add(c)
    return True
Bpick = (24,60),(12,54)
print('Bpick valid?', (Bpick in Btar))
otherB = [Bpick[0],Bpick[1]]
sols=[]
rng = range(43,60)
cands=[p for p in product(rng, range(24,47)) if ok_end(*p) and abs(p[0]-51)<=7 and abs(p[1]-40)<=7 and terr[p[0]][p[1]] not in 'Op']
print('cand ends near ring', len(cands))
hubA = hubcells(51,40)
for T1,T2,T3 in permutations(cands,3):
    if (T1[0]+T2[0]+T3[0], T1[1]+T2[1]+T3[1]) != (153,120): continue
    ends=[T1,T2,T3]
    if not disjoint([diamond(*e) for e in ends]): continue
    if any(c in set(hubA) for e in ends for c in diamond(*e)): continue
    # intermediate 1: ends T1,(9,49),(12,24)
    e1=[T1,(9,49),(12,24)]; h1=mean3(e1)
    if not ok_hub(*h1): continue
    if any(c in set(hubcells(*h1)) for e in e1 for c in diamond(*e)): continue
    # intermediate 2: ends T1,T2,(12,24)
    e2=[T1,T2,(12,24)]; h2=mean3(e2)
    if not ok_hub(*h2): continue
    if any(c in set(hubcells(*h2)) for e in e2 for c in diamond(*e)): continue
    sols.append((T1,T2,T3,h1,h2))
    if len(sols)>6: break
for s_ in sols[:6]: print(s_)

```

实际随后输出：
```text
Bpick valid? True
cand ends near ring 189
((44, 44), (51, 33), (58, 43), (21, 39), (35, 33))
((44, 44), (51, 34), (58, 42), (21, 39), (35, 34))
((44, 44), (51, 35), (58, 41), (21, 39), (35, 34))
((44, 44), (52, 33), (57, 43), (21, 39), (36, 33))
((44, 44), (52, 34), (57, 42), (21, 39), (36, 34))
((44, 44), (52, 35), (57, 41), (21, 39), (36, 34))

```

人工确认：读取语句是否实际执行、值是否来自旧调用、是否仍适用当前盘面、是否用于搜索或动作、与新增关卡的关系。

### r11l-495a7899_p0_requests.jsonl 变量 cands

读取方式：direct_before_definition；类型：list；定义输出行59，读取输出行61；关卡3。

定义代码：
```python
from itertools import combinations, permutations
CB_now = [(34,37),(40,52)]
CB_hub_now = (37,44)
blocked = set()
for p in CB_now: blocked |= set(diamond(*p))
blocked |= set(hubcells(*CB_hub_now))
hubs_target_A = hubcells(53,55)
ringN = set((r,c) for r in range(50,57) for c in range(52,59) if terr[r][c]=='N')
cands=[(r,c) for r in range(45,63) for c in range(46,63)
       if ok_end(r,c) and abs(r-53)<=7 and abs(c-55)<=7
       and not (set(diamond(r,c)) & set(hubs_target_A)) and terr[r][c]!='N'
       and not (set(diamond(r,c)) & blocked)]
print('cands', len(cands))
sols=[]
seen=set()
for combo in combinations(cands,4):
    if sum(p[0] for p in combo)!=212 or sum(p[1] for p in combo)!=220: continue
    if not disjoint([diamond(*p) for p in combo]): continue
    # try orderings
    for perm in permutations(range(4)):
        fixed=[combo[i] for i in range(4)]
        # simulate: handle takes perm[0] first... fixed ends are the remaining original ones
        # need original fixed set: (9,34),(16,39),(21,23)
        orig=[(9,34),(16,39),(21,23)]
        ends_now=list(orig)  # after handle leaves to T1
        ok=True
        seq=[]
        cur=list(orig)
        for k in range(4):
            T=combo[perm[k]]
            others = cur[:]  # the 3 non-handle ends currently (orig minus those already replaced)
            newends = others+[T]
            h=(sum(p[0] for p in newends)//4, sum(p[1] for p in newends)//4)
            if k==3:
                if h!=(53,55): ok=False;break
                if not ok_hub(53,55,'N'): ok=False;break
            else:
                if not ok_hub(*h): ok=False;break
                if set(hubcells(*h)) & blocked: ok=False;break
                if any(set(diamond(*e)) & set(hubcells(*h)) for e in newends): ok=False;break
            cur = newends
            seq.append((T,h))
        if ok:
            sols.append(seq); break
    if len(sols)>=3: break
for s_ in sols: print(s_)

```

随后代码：
```python
F=[(9,34),(16,39),(21,23)]  # fixed ends in order of consumption
def sim(combo, perm):
    T=[combo[i] for i in perm]
    steps=[]
    for k in range(4):
        ends = T[:k+1] + F[k+1:]
        h=(sum(p[0] for p in ends)//4, sum(p[1] for p in ends)//4)
        steps.append((T[k],ends,h))
    return steps
sols=[]
for combo in combinations(cands,4):
    if sum(p[0] for p in combo)!=212 or sum(p[1] for p in combo)!=220: continue
    if not disjoint([diamond(*p) for p in combo]): continue
    for perm in permutations(range(4)):
        st=sim(combo,perm); ok=True
        for k,(T,ends,h) in enumerate(st):
            if k==3:
                if h!=(53,55) or not ok_hub(53,55,'N'): ok=False;break
            else:
                if not ok_hub(*h): ok=False;break
                if set(hubcells(*h)) & blocked: ok=False;break
            if any(set(diamond(*e)) & set(hubcells(*h)) for e in ends): ok=False;break
        if ok:
            sols.append([ (T,h) for T,ends,h in st]); break
    if len(sols)>=4: break
print('sols',len(sols))
for s_ in sols: print(s_)

```

实际随后输出：
```text
sols 0

```

人工确认：读取语句是否实际执行、值是否来自旧调用、是否仍适用当前盘面、是否用于搜索或动作、与新增关卡的关系。

### r11l-495a7899_p0_requests.jsonl 变量 cands

读取方式：direct_before_definition；类型：list；定义输出行59，读取输出行63；关卡3。

定义代码：
```python
from itertools import combinations, permutations
CB_now = [(34,37),(40,52)]
CB_hub_now = (37,44)
blocked = set()
for p in CB_now: blocked |= set(diamond(*p))
blocked |= set(hubcells(*CB_hub_now))
hubs_target_A = hubcells(53,55)
ringN = set((r,c) for r in range(50,57) for c in range(52,59) if terr[r][c]=='N')
cands=[(r,c) for r in range(45,63) for c in range(46,63)
       if ok_end(r,c) and abs(r-53)<=7 and abs(c-55)<=7
       and not (set(diamond(r,c)) & set(hubs_target_A)) and terr[r][c]!='N'
       and not (set(diamond(r,c)) & blocked)]
print('cands', len(cands))
sols=[]
seen=set()
for combo in combinations(cands,4):
    if sum(p[0] for p in combo)!=212 or sum(p[1] for p in combo)!=220: continue
    if not disjoint([diamond(*p) for p in combo]): continue
    # try orderings
    for perm in permutations(range(4)):
        fixed=[combo[i] for i in range(4)]
        # simulate: handle takes perm[0] first... fixed ends are the remaining original ones
        # need original fixed set: (9,34),(16,39),(21,23)
        orig=[(9,34),(16,39),(21,23)]
        ends_now=list(orig)  # after handle leaves to T1
        ok=True
        seq=[]
        cur=list(orig)
        for k in range(4):
            T=combo[perm[k]]
            others = cur[:]  # the 3 non-handle ends currently (orig minus those already replaced)
            newends = others+[T]
            h=(sum(p[0] for p in newends)//4, sum(p[1] for p in newends)//4)
            if k==3:
                if h!=(53,55): ok=False;break
                if not ok_hub(53,55,'N'): ok=False;break
            else:
                if not ok_hub(*h): ok=False;break
                if set(hubcells(*h)) & blocked: ok=False;break
                if any(set(diamond(*e)) & set(hubcells(*h)) for e in newends): ok=False;break
            cur = newends
            seq.append((T,h))
        if ok:
            sols.append(seq); break
    if len(sols)>=3: break
for s_ in sols: print(s_)

```

随后代码：
```python
cnt=0
for combo in combinations(cands,4):
    if sum(p[0] for p in combo)!=212 or sum(p[1] for p in combo)!=220: continue
    if not disjoint([diamond(*p) for p in combo]): continue
    cnt+=1
    if cnt<=3:
        st=sim(combo,(0,1,2,3))
        print([ (T,h,ok_hub(*h)) for T,ends,h in st][:4])
print('sum-valid combos', cnt)
# also check which intermediate hub positions are generally invalid
print('sample hub24,37', ok_hub(24,37))
a2=current_frame.ascii.split('\n')
print('crop rows22-26 cols34-40'); 
for rr in range(22,27): print(rr, a2[rr][34:41])

```

实际随后输出：
```text
[((46, 50), (20, 28), True), ((46, 55), (28, 32), False), ((60, 54), (38, 39), False), ((60, 61), (53, 55), True)]
[((46, 50), (20, 28), True), ((46, 55), (28, 32), False), ((60, 55), (38, 40), False), ((60, 60), (53, 55), True)]
[((46, 50), (20, 28), True), ((46, 56), (28, 32), False), ((60, 53), (38, 39), False), ((60, 61), (53, 55), True)]
sum-valid combos 21065
sample hub24,37 False
crop rows22-26 cols34-40
22 BBBBBBB
23 BBBBBBB
24 BBBBBBB
25 BBBBBBB
26 SSSSSSS

```

人工确认：读取语句是否实际执行、值是否来自旧调用、是否仍适用当前盘面、是否用于搜索或动作、与新增关卡的关系。

### r11l-495a7899_p0_requests.jsonl 变量 cands

读取方式：direct_before_definition；类型：list；定义输出行65，读取输出行67；关卡3。

定义代码：
```python
validH = set((r,c) for r in range(1,64) for c in range(64) if ok_hub(r,c))
FIX=[(9,34),(16,39),(21,23)]
Sfix=(sum(p[0] for p in FIX), sum(p[1] for p in FIX))
hubs_target_A = hubcells(53,55)
cands=[(r,c) for r in range(44,64) for c in range(45,64)
       if ok_end(r,c) and abs(r-53)<=8 and abs(c-55)<=8
       and not (set(diamond(r,c)) & set(hubs_target_A)) and terr[r][c]!='N'
       and not (set(diamond(r,c)) & blocked)]
print('cands',len(cands))
# OK1: T such that hub1 valid
OK1={T for T in cands if ((T[0]+Sfix[0])//4,(T[1]+Sfix[1])//4) in validH}
print('OK1',len(OK1))
# OK3: (T4, R1) valid: hub3 = ((212-T4r+R1r)//4, (220-T4c+R1c)//4)
OK3=set()
for T4 in cands:
    for R1 in FIX:
        if ((212-T4[0]+R1[0])//4,(220-T4[1]+R1[1])//4) in validH: OK3.add((T4,R1))
print('OK3',len(OK3))

```

随后代码：
```python
sol=None
comb_list=[]
for combo in combinations(cands,4):
    if sum(p[0] for p in combo)!=212 or sum(p[1] for p in combo)!=220: continue
    if not disjoint([diamond(*p) for p in combo]): continue
    comb_list.append(combo)
print('combos',len(comb_list))
for combo in comb_list:
    ok1=[T for T in combo if T in OK1]
    if not ok1: continue
    for T1 in ok1:
        for T4 in combo:
            if T4==T1: continue
            R1s=[R for R in FIX if (T4,R) in OK3]
            if not R1s: continue
            mid=[T for T in combo if T not in (T1,T4)]
            for T2,T3 in ((mid[0],mid[1]),(mid[1],mid[0])):
                for c1 in FIX:
                    R2=[R for R in FIX if R!=c1]
                    h1=((T1[0]+Sfix[0])//4,(T1[1]+Sfix[1])//4)
                    h2=((T1[0]+T2[0]+sum(p[0] for p in R2))//4,(T1[1]+T2[1]+sum(p[1] for p in R2))//4)
                    if h2 not in validH: continue
                    if set(hubcells(*h2)) & blocked: continue
                    for R1 in R1s:
                        R2b=[R for R in R2 if R!=R1]
                        if len(R2b)!=1: continue
                        h3=((212-T4[0]+R1[0])//4,(220-T4[1]+R1[1])//4)
                        if h3 not in validH: continue
                        if set(hubcells(*h3)) & blocked: continue
                        sol=dict(T1=T1,T2=T2,T3=T3,T4=T4,consume=[c1,R1,R2b[0]],h1=h1,h2=h2,h3=h3)
                        break
                    if sol: break
                if sol: break
            if sol: break
        if sol: break
    if sol: break
print(sol)

```

实际随后输出：
```text
combos 41089
{'T1': (45, 50), 'T2': (61, 54), 'T3': (61, 61), 'T4': (45, 55), 'consume': [(21, 23), (16, 39), (9, 34)], 'h1': (22, 36), 'h2': (32, 44), 'h3': (45, 51)}

```

人工确认：读取语句是否实际执行、值是否来自旧调用、是否仍适用当前盘面、是否用于搜索或动作、与新增关卡的关系。

### r11l-495a7899_p0_requests.jsonl 变量 A_ends

读取方式：direct_before_definition；类型：list；定义输出行79，读取输出行81；关卡4。

定义代码：
```python
a=current_frame.ascii.split('\n')
terr=[[a[r][c] for c in range(64)] for r in range(64)]
def is_obs(r,c):
    if r<1 or r>63 or c<0 or c>63: return True
    return terr[r][c] in 'Sg'
def ok_end(r,c): return all(not is_obs(x,y) for x,y in diamond(r,c))
def ok_hub(r,c): return all(not is_obs(x,y) for x,y in hubcells(r,c))
validH=set((r,c) for r in range(1,64) for c in range(64) if ok_hub(r,c))
# chains
A_ends=[(6,39),(20,23)]; A_hub=(13,31); A_t=(49,36)
B_ends=[(36,17),(47,10),(52,27)]; B_hub=(45,18); B_t=(11,51)
C_ends=[(36,46),(52,46)]; C_hub=(44,46); C_t=(54,17)
print('hub targets ok?', ok_hub(*A_t), ok_hub(*B_t), ok_hub(*C_t))
print('cur ends ok?', [ok_end(*p) for p in A_ends+B_ends+C_ends])
# handle at (20,23) in chain A
print('free cells', sum(1 for r in range(1,64) for c in range(64) if not is_obs(r,c)))

```

随后代码：
```python
def opts2(target, ends, handle_idx, blocked):
    """2-end chain: handle at ends[handle_idx]; other end F. Returns list of (U1,U2,h_int)."""
    F = ends[1-handle_idx]
    S=(2*target[0],2*target[1])
    out=[]
    for U1 in [(r,c) for r in range(1,64) for c in range(64) if ok_end(r,c)]:
        U2=(S[0]-U1[0], S[1]-U1[1])
        if not(1<=U2[0]<64 and 0<=U2[1]<64): continue
        if not ok_end(*U2): continue
        hi=((U1[0]+F[0])//2,(U1[1]+F[1])//2)
        if hi not in validH: continue
        if set(hubcells(*hi)) & blocked: continue
        if (set(diamond(*U1))|set(diamond(*U2))) & blocked: continue
        if set(diamond(*U1)) & set(diamond(*U2)): continue
        if set(hubcells(*target)) & (set(diamond(*U1))|set(diamond(*U2))): continue
        out.append((U1,U2,hi))
    return out
# chain A: blocked = other chains' current beads
blockedA = set()
for p in B_ends+C_ends: blockedA |= set(diamond(*p))
blockedA |= set(hubcells(*B_hub)) | set(hubcells(*C_hub))
oA = opts2(A_t, A_ends, 1, blockedA)
print('A opts', len(oA))
# prefer compact/symmetric: ends offset +-5 from target
def score(o):
    U1,U2,hi=o
    return abs(U1[0]-A_t[0])+abs(U1[1]-A_t[1])+abs(U2[0]-A_t[0])+abs(U2[1]-A_t[1])
oA.sort(key=score)
for o in oA[:12]: print(o, score(o))

```

实际随后输出：
```text
A opts 176
((49, 51), (49, 21), (27, 45)) 30
((48, 51), (50, 21), (27, 45)) 32
((49, 52), (49, 20), (27, 45)) 32
((50, 51), (48, 21), (28, 45)) 32
((47, 51), (51, 21), (26, 45)) 34
((48, 52), (50, 20), (27, 45)) 34
((46, 51), (52, 21), (26, 45)) 36
((47, 52), (51, 20), (26, 45)) 36
((48, 53), (50, 19), (27, 46)) 36
((54, 49), (44, 23), (30, 44)) 36
((56, 47), (42, 25), (31, 43)) 36
((45, 51), (53, 21), (25, 45)) 38

```

人工确认：读取语句是否实际执行、值是否来自旧调用、是否仍适用当前盘面、是否用于搜索或动作、与新增关卡的关系。

### r11l-495a7899_p0_requests.jsonl 变量 A_t

读取方式：direct_before_definition；类型：ordinary_value；定义输出行79，读取输出行81；关卡4。

定义代码：
```python
a=current_frame.ascii.split('\n')
terr=[[a[r][c] for c in range(64)] for r in range(64)]
def is_obs(r,c):
    if r<1 or r>63 or c<0 or c>63: return True
    return terr[r][c] in 'Sg'
def ok_end(r,c): return all(not is_obs(x,y) for x,y in diamond(r,c))
def ok_hub(r,c): return all(not is_obs(x,y) for x,y in hubcells(r,c))
validH=set((r,c) for r in range(1,64) for c in range(64) if ok_hub(r,c))
# chains
A_ends=[(6,39),(20,23)]; A_hub=(13,31); A_t=(49,36)
B_ends=[(36,17),(47,10),(52,27)]; B_hub=(45,18); B_t=(11,51)
C_ends=[(36,46),(52,46)]; C_hub=(44,46); C_t=(54,17)
print('hub targets ok?', ok_hub(*A_t), ok_hub(*B_t), ok_hub(*C_t))
print('cur ends ok?', [ok_end(*p) for p in A_ends+B_ends+C_ends])
# handle at (20,23) in chain A
print('free cells', sum(1 for r in range(1,64) for c in range(64) if not is_obs(r,c)))

```

随后代码：
```python
def opts2(target, ends, handle_idx, blocked):
    """2-end chain: handle at ends[handle_idx]; other end F. Returns list of (U1,U2,h_int)."""
    F = ends[1-handle_idx]
    S=(2*target[0],2*target[1])
    out=[]
    for U1 in [(r,c) for r in range(1,64) for c in range(64) if ok_end(r,c)]:
        U2=(S[0]-U1[0], S[1]-U1[1])
        if not(1<=U2[0]<64 and 0<=U2[1]<64): continue
        if not ok_end(*U2): continue
        hi=((U1[0]+F[0])//2,(U1[1]+F[1])//2)
        if hi not in validH: continue
        if set(hubcells(*hi)) & blocked: continue
        if (set(diamond(*U1))|set(diamond(*U2))) & blocked: continue
        if set(diamond(*U1)) & set(diamond(*U2)): continue
        if set(hubcells(*target)) & (set(diamond(*U1))|set(diamond(*U2))): continue
        out.append((U1,U2,hi))
    return out
# chain A: blocked = other chains' current beads
blockedA = set()
for p in B_ends+C_ends: blockedA |= set(diamond(*p))
blockedA |= set(hubcells(*B_hub)) | set(hubcells(*C_hub))
oA = opts2(A_t, A_ends, 1, blockedA)
print('A opts', len(oA))
# prefer compact/symmetric: ends offset +-5 from target
def score(o):
    U1,U2,hi=o
    return abs(U1[0]-A_t[0])+abs(U1[1]-A_t[1])+abs(U2[0]-A_t[0])+abs(U2[1]-A_t[1])
oA.sort(key=score)
for o in oA[:12]: print(o, score(o))

```

实际随后输出：
```text
A opts 176
((49, 51), (49, 21), (27, 45)) 30
((48, 51), (50, 21), (27, 45)) 32
((49, 52), (49, 20), (27, 45)) 32
((50, 51), (48, 21), (28, 45)) 32
((47, 51), (51, 21), (26, 45)) 34
((48, 52), (50, 20), (27, 45)) 34
((46, 51), (52, 21), (26, 45)) 36
((47, 52), (51, 20), (26, 45)) 36
((48, 53), (50, 19), (27, 46)) 36
((54, 49), (44, 23), (30, 44)) 36
((56, 47), (42, 25), (31, 43)) 36
((45, 51), (53, 21), (25, 45)) 38

```

人工确认：读取语句是否实际执行、值是否来自旧调用、是否仍适用当前盘面、是否用于搜索或动作、与新增关卡的关系。

### r11l-495a7899_p0_requests.jsonl 变量 B_ends

读取方式：direct_before_definition；类型：list；定义输出行79，读取输出行81；关卡4。

定义代码：
```python
a=current_frame.ascii.split('\n')
terr=[[a[r][c] for c in range(64)] for r in range(64)]
def is_obs(r,c):
    if r<1 or r>63 or c<0 or c>63: return True
    return terr[r][c] in 'Sg'
def ok_end(r,c): return all(not is_obs(x,y) for x,y in diamond(r,c))
def ok_hub(r,c): return all(not is_obs(x,y) for x,y in hubcells(r,c))
validH=set((r,c) for r in range(1,64) for c in range(64) if ok_hub(r,c))
# chains
A_ends=[(6,39),(20,23)]; A_hub=(13,31); A_t=(49,36)
B_ends=[(36,17),(47,10),(52,27)]; B_hub=(45,18); B_t=(11,51)
C_ends=[(36,46),(52,46)]; C_hub=(44,46); C_t=(54,17)
print('hub targets ok?', ok_hub(*A_t), ok_hub(*B_t), ok_hub(*C_t))
print('cur ends ok?', [ok_end(*p) for p in A_ends+B_ends+C_ends])
# handle at (20,23) in chain A
print('free cells', sum(1 for r in range(1,64) for c in range(64) if not is_obs(r,c)))

```

随后代码：
```python
def opts2(target, ends, handle_idx, blocked):
    """2-end chain: handle at ends[handle_idx]; other end F. Returns list of (U1,U2,h_int)."""
    F = ends[1-handle_idx]
    S=(2*target[0],2*target[1])
    out=[]
    for U1 in [(r,c) for r in range(1,64) for c in range(64) if ok_end(r,c)]:
        U2=(S[0]-U1[0], S[1]-U1[1])
        if not(1<=U2[0]<64 and 0<=U2[1]<64): continue
        if not ok_end(*U2): continue
        hi=((U1[0]+F[0])//2,(U1[1]+F[1])//2)
        if hi not in validH: continue
        if set(hubcells(*hi)) & blocked: continue
        if (set(diamond(*U1))|set(diamond(*U2))) & blocked: continue
        if set(diamond(*U1)) & set(diamond(*U2)): continue
        if set(hubcells(*target)) & (set(diamond(*U1))|set(diamond(*U2))): continue
        out.append((U1,U2,hi))
    return out
# chain A: blocked = other chains' current beads
blockedA = set()
for p in B_ends+C_ends: blockedA |= set(diamond(*p))
blockedA |= set(hubcells(*B_hub)) | set(hubcells(*C_hub))
oA = opts2(A_t, A_ends, 1, blockedA)
print('A opts', len(oA))
# prefer compact/symmetric: ends offset +-5 from target
def score(o):
    U1,U2,hi=o
    return abs(U1[0]-A_t[0])+abs(U1[1]-A_t[1])+abs(U2[0]-A_t[0])+abs(U2[1]-A_t[1])
oA.sort(key=score)
for o in oA[:12]: print(o, score(o))

```

实际随后输出：
```text
A opts 176
((49, 51), (49, 21), (27, 45)) 30
((48, 51), (50, 21), (27, 45)) 32
((49, 52), (49, 20), (27, 45)) 32
((50, 51), (48, 21), (28, 45)) 32
((47, 51), (51, 21), (26, 45)) 34
((48, 52), (50, 20), (27, 45)) 34
((46, 51), (52, 21), (26, 45)) 36
((47, 52), (51, 20), (26, 45)) 36
((48, 53), (50, 19), (27, 46)) 36
((54, 49), (44, 23), (30, 44)) 36
((56, 47), (42, 25), (31, 43)) 36
((45, 51), (53, 21), (25, 45)) 38

```

人工确认：读取语句是否实际执行、值是否来自旧调用、是否仍适用当前盘面、是否用于搜索或动作、与新增关卡的关系。

### r11l-495a7899_p0_requests.jsonl 变量 B_hub

读取方式：direct_before_definition；类型：ordinary_value；定义输出行79，读取输出行81；关卡4。

定义代码：
```python
a=current_frame.ascii.split('\n')
terr=[[a[r][c] for c in range(64)] for r in range(64)]
def is_obs(r,c):
    if r<1 or r>63 or c<0 or c>63: return True
    return terr[r][c] in 'Sg'
def ok_end(r,c): return all(not is_obs(x,y) for x,y in diamond(r,c))
def ok_hub(r,c): return all(not is_obs(x,y) for x,y in hubcells(r,c))
validH=set((r,c) for r in range(1,64) for c in range(64) if ok_hub(r,c))
# chains
A_ends=[(6,39),(20,23)]; A_hub=(13,31); A_t=(49,36)
B_ends=[(36,17),(47,10),(52,27)]; B_hub=(45,18); B_t=(11,51)
C_ends=[(36,46),(52,46)]; C_hub=(44,46); C_t=(54,17)
print('hub targets ok?', ok_hub(*A_t), ok_hub(*B_t), ok_hub(*C_t))
print('cur ends ok?', [ok_end(*p) for p in A_ends+B_ends+C_ends])
# handle at (20,23) in chain A
print('free cells', sum(1 for r in range(1,64) for c in range(64) if not is_obs(r,c)))

```

随后代码：
```python
def opts2(target, ends, handle_idx, blocked):
    """2-end chain: handle at ends[handle_idx]; other end F. Returns list of (U1,U2,h_int)."""
    F = ends[1-handle_idx]
    S=(2*target[0],2*target[1])
    out=[]
    for U1 in [(r,c) for r in range(1,64) for c in range(64) if ok_end(r,c)]:
        U2=(S[0]-U1[0], S[1]-U1[1])
        if not(1<=U2[0]<64 and 0<=U2[1]<64): continue
        if not ok_end(*U2): continue
        hi=((U1[0]+F[0])//2,(U1[1]+F[1])//2)
        if hi not in validH: continue
        if set(hubcells(*hi)) & blocked: continue
        if (set(diamond(*U1))|set(diamond(*U2))) & blocked: continue
        if set(diamond(*U1)) & set(diamond(*U2)): continue
        if set(hubcells(*target)) & (set(diamond(*U1))|set(diamond(*U2))): continue
        out.append((U1,U2,hi))
    return out
# chain A: blocked = other chains' current beads
blockedA = set()
for p in B_ends+C_ends: blockedA |= set(diamond(*p))
blockedA |= set(hubcells(*B_hub)) | set(hubcells(*C_hub))
oA = opts2(A_t, A_ends, 1, blockedA)
print('A opts', len(oA))
# prefer compact/symmetric: ends offset +-5 from target
def score(o):
    U1,U2,hi=o
    return abs(U1[0]-A_t[0])+abs(U1[1]-A_t[1])+abs(U2[0]-A_t[0])+abs(U2[1]-A_t[1])
oA.sort(key=score)
for o in oA[:12]: print(o, score(o))

```

实际随后输出：
```text
A opts 176
((49, 51), (49, 21), (27, 45)) 30
((48, 51), (50, 21), (27, 45)) 32
((49, 52), (49, 20), (27, 45)) 32
((50, 51), (48, 21), (28, 45)) 32
((47, 51), (51, 21), (26, 45)) 34
((48, 52), (50, 20), (27, 45)) 34
((46, 51), (52, 21), (26, 45)) 36
((47, 52), (51, 20), (26, 45)) 36
((48, 53), (50, 19), (27, 46)) 36
((54, 49), (44, 23), (30, 44)) 36
((56, 47), (42, 25), (31, 43)) 36
((45, 51), (53, 21), (25, 45)) 38

```

人工确认：读取语句是否实际执行、值是否来自旧调用、是否仍适用当前盘面、是否用于搜索或动作、与新增关卡的关系。

### r11l-495a7899_p0_requests.jsonl 变量 C_ends

读取方式：direct_before_definition；类型：list；定义输出行79，读取输出行81；关卡4。

定义代码：
```python
a=current_frame.ascii.split('\n')
terr=[[a[r][c] for c in range(64)] for r in range(64)]
def is_obs(r,c):
    if r<1 or r>63 or c<0 or c>63: return True
    return terr[r][c] in 'Sg'
def ok_end(r,c): return all(not is_obs(x,y) for x,y in diamond(r,c))
def ok_hub(r,c): return all(not is_obs(x,y) for x,y in hubcells(r,c))
validH=set((r,c) for r in range(1,64) for c in range(64) if ok_hub(r,c))
# chains
A_ends=[(6,39),(20,23)]; A_hub=(13,31); A_t=(49,36)
B_ends=[(36,17),(47,10),(52,27)]; B_hub=(45,18); B_t=(11,51)
C_ends=[(36,46),(52,46)]; C_hub=(44,46); C_t=(54,17)
print('hub targets ok?', ok_hub(*A_t), ok_hub(*B_t), ok_hub(*C_t))
print('cur ends ok?', [ok_end(*p) for p in A_ends+B_ends+C_ends])
# handle at (20,23) in chain A
print('free cells', sum(1 for r in range(1,64) for c in range(64) if not is_obs(r,c)))

```

随后代码：
```python
def opts2(target, ends, handle_idx, blocked):
    """2-end chain: handle at ends[handle_idx]; other end F. Returns list of (U1,U2,h_int)."""
    F = ends[1-handle_idx]
    S=(2*target[0],2*target[1])
    out=[]
    for U1 in [(r,c) for r in range(1,64) for c in range(64) if ok_end(r,c)]:
        U2=(S[0]-U1[0], S[1]-U1[1])
        if not(1<=U2[0]<64 and 0<=U2[1]<64): continue
        if not ok_end(*U2): continue
        hi=((U1[0]+F[0])//2,(U1[1]+F[1])//2)
        if hi not in validH: continue
        if set(hubcells(*hi)) & blocked: continue
        if (set(diamond(*U1))|set(diamond(*U2))) & blocked: continue
        if set(diamond(*U1)) & set(diamond(*U2)): continue
        if set(hubcells(*target)) & (set(diamond(*U1))|set(diamond(*U2))): continue
        out.append((U1,U2,hi))
    return out
# chain A: blocked = other chains' current beads
blockedA = set()
for p in B_ends+C_ends: blockedA |= set(diamond(*p))
blockedA |= set(hubcells(*B_hub)) | set(hubcells(*C_hub))
oA = opts2(A_t, A_ends, 1, blockedA)
print('A opts', len(oA))
# prefer compact/symmetric: ends offset +-5 from target
def score(o):
    U1,U2,hi=o
    return abs(U1[0]-A_t[0])+abs(U1[1]-A_t[1])+abs(U2[0]-A_t[0])+abs(U2[1]-A_t[1])
oA.sort(key=score)
for o in oA[:12]: print(o, score(o))

```

实际随后输出：
```text
A opts 176
((49, 51), (49, 21), (27, 45)) 30
((48, 51), (50, 21), (27, 45)) 32
((49, 52), (49, 20), (27, 45)) 32
((50, 51), (48, 21), (28, 45)) 32
((47, 51), (51, 21), (26, 45)) 34
((48, 52), (50, 20), (27, 45)) 34
((46, 51), (52, 21), (26, 45)) 36
((47, 52), (51, 20), (26, 45)) 36
((48, 53), (50, 19), (27, 46)) 36
((54, 49), (44, 23), (30, 44)) 36
((56, 47), (42, 25), (31, 43)) 36
((45, 51), (53, 21), (25, 45)) 38

```

人工确认：读取语句是否实际执行、值是否来自旧调用、是否仍适用当前盘面、是否用于搜索或动作、与新增关卡的关系。

### r11l-495a7899_p0_requests.jsonl 变量 C_hub

读取方式：direct_before_definition；类型：ordinary_value；定义输出行79，读取输出行81；关卡4。

定义代码：
```python
a=current_frame.ascii.split('\n')
terr=[[a[r][c] for c in range(64)] for r in range(64)]
def is_obs(r,c):
    if r<1 or r>63 or c<0 or c>63: return True
    return terr[r][c] in 'Sg'
def ok_end(r,c): return all(not is_obs(x,y) for x,y in diamond(r,c))
def ok_hub(r,c): return all(not is_obs(x,y) for x,y in hubcells(r,c))
validH=set((r,c) for r in range(1,64) for c in range(64) if ok_hub(r,c))
# chains
A_ends=[(6,39),(20,23)]; A_hub=(13,31); A_t=(49,36)
B_ends=[(36,17),(47,10),(52,27)]; B_hub=(45,18); B_t=(11,51)
C_ends=[(36,46),(52,46)]; C_hub=(44,46); C_t=(54,17)
print('hub targets ok?', ok_hub(*A_t), ok_hub(*B_t), ok_hub(*C_t))
print('cur ends ok?', [ok_end(*p) for p in A_ends+B_ends+C_ends])
# handle at (20,23) in chain A
print('free cells', sum(1 for r in range(1,64) for c in range(64) if not is_obs(r,c)))

```

随后代码：
```python
def opts2(target, ends, handle_idx, blocked):
    """2-end chain: handle at ends[handle_idx]; other end F. Returns list of (U1,U2,h_int)."""
    F = ends[1-handle_idx]
    S=(2*target[0],2*target[1])
    out=[]
    for U1 in [(r,c) for r in range(1,64) for c in range(64) if ok_end(r,c)]:
        U2=(S[0]-U1[0], S[1]-U1[1])
        if not(1<=U2[0]<64 and 0<=U2[1]<64): continue
        if not ok_end(*U2): continue
        hi=((U1[0]+F[0])//2,(U1[1]+F[1])//2)
        if hi not in validH: continue
        if set(hubcells(*hi)) & blocked: continue
        if (set(diamond(*U1))|set(diamond(*U2))) & blocked: continue
        if set(diamond(*U1)) & set(diamond(*U2)): continue
        if set(hubcells(*target)) & (set(diamond(*U1))|set(diamond(*U2))): continue
        out.append((U1,U2,hi))
    return out
# chain A: blocked = other chains' current beads
blockedA = set()
for p in B_ends+C_ends: blockedA |= set(diamond(*p))
blockedA |= set(hubcells(*B_hub)) | set(hubcells(*C_hub))
oA = opts2(A_t, A_ends, 1, blockedA)
print('A opts', len(oA))
# prefer compact/symmetric: ends offset +-5 from target
def score(o):
    U1,U2,hi=o
    return abs(U1[0]-A_t[0])+abs(U1[1]-A_t[1])+abs(U2[0]-A_t[0])+abs(U2[1]-A_t[1])
oA.sort(key=score)
for o in oA[:12]: print(o, score(o))

```

实际随后输出：
```text
A opts 176
((49, 51), (49, 21), (27, 45)) 30
((48, 51), (50, 21), (27, 45)) 32
((49, 52), (49, 20), (27, 45)) 32
((50, 51), (48, 21), (28, 45)) 32
((47, 51), (51, 21), (26, 45)) 34
((48, 52), (50, 20), (27, 45)) 34
((46, 51), (52, 21), (26, 45)) 36
((47, 52), (51, 20), (26, 45)) 36
((48, 53), (50, 19), (27, 46)) 36
((54, 49), (44, 23), (30, 44)) 36
((56, 47), (42, 25), (31, 43)) 36
((45, 51), (53, 21), (25, 45)) 38

```

人工确认：读取语句是否实际执行、值是否来自旧调用、是否仍适用当前盘面、是否用于搜索或动作、与新增关卡的关系。

### r11l-495a7899_p0_requests.jsonl 变量 A_t

读取方式：direct_before_definition；类型：ordinary_value；定义输出行79，读取输出行83；关卡4。

定义代码：
```python
a=current_frame.ascii.split('\n')
terr=[[a[r][c] for c in range(64)] for r in range(64)]
def is_obs(r,c):
    if r<1 or r>63 or c<0 or c>63: return True
    return terr[r][c] in 'Sg'
def ok_end(r,c): return all(not is_obs(x,y) for x,y in diamond(r,c))
def ok_hub(r,c): return all(not is_obs(x,y) for x,y in hubcells(r,c))
validH=set((r,c) for r in range(1,64) for c in range(64) if ok_hub(r,c))
# chains
A_ends=[(6,39),(20,23)]; A_hub=(13,31); A_t=(49,36)
B_ends=[(36,17),(47,10),(52,27)]; B_hub=(45,18); B_t=(11,51)
C_ends=[(36,46),(52,46)]; C_hub=(44,46); C_t=(54,17)
print('hub targets ok?', ok_hub(*A_t), ok_hub(*B_t), ok_hub(*C_t))
print('cur ends ok?', [ok_end(*p) for p in A_ends+B_ends+C_ends])
# handle at (20,23) in chain A
print('free cells', sum(1 for r in range(1,64) for c in range(64) if not is_obs(r,c)))

```

随后代码：
```python
def opts3(target, ends, blocked):
    """3-end chain, handle enters at one of ends. Return list of (entry, F1, F2, V1,V2,V3, h1,h2)."""
    S=(3*target[0],3*target[1])
    res=[]
    for entry in ends:
        rest=[p for p in ends if p!=entry]
        for F1,F2 in [(rest[0],rest[1]),(rest[1],rest[0])]:
            cands=[(r,c) for r in range(1,64) for c in range(64) if ok_end(r,c) and abs(r-target[0])<=10 and abs(c-target[1])<=12]
            for V1 in cands:
                h1=((V1[0]+F1[0]+F2[0])//3,(V1[1]+F1[1]+F2[1])//3)
                if h1 not in validH: continue
                if set(hubcells(*h1)) & blocked: continue
                if set(diamond(*V1)) & blocked: continue
                for V2 in cands:
                    if V2==V1: continue
                    h2=((V1[0]+V2[0]+F2[0])//3,(V1[1]+V2[1]+F2[1])//3)
                    if h2 not in validH: continue
                    if set(hubcells(*h2)) & blocked: continue
                    if set(diamond(*V2)) & blocked: continue
                    V3=(S[0]-V1[0]-V2[0], S[1]-V1[1]-V2[1])
                    if not(1<=V3[0]<64 and 0<=V3[1]<64): continue
                    if not ok_end(*V3): continue
                    if set(diamond(*V3)) & blocked: continue
                    ds=[set(diamond(*x)) for x in (V1,V2,V3)]
                    if ds[0]&ds[1] or ds[0]&ds[2] or ds[1]&ds[2]: continue
                    if set(hubcells(*target)) & (ds[0]|ds[1]|ds[2]): continue
                    res.append((entry,F1,F2,V1,V2,V3,h1,h2))
    return res
# chain B with A option 1 fixed
Aopt=oA[0]
blockedB=set()
for p in [Aopt[0],Aopt[1]]+C_ends: blockedB|=set(diamond(*p))
blockedB|=set(hubcells(*A_t))|set(hubcells(*C_hub))
oB=opts3(B_t,B_ends,blockedB)
print('B opts',len(oB))
def scoreB(o):
    e,F1,F2,V1,V2,V3,h1,h2=o
    return sum(abs(V[0]-B_t[0])+abs(V[1]-B_t[1]) for V in (V1,V2,V3))
oB.sort(key=scoreB)
for o in oB[:8]: print(o)

```

实际随后输出：
```text
B opts 2619
((52, 27), (47, 10), (36, 17), (10, 41), (10, 57), (13, 55), (31, 22), (18, 38))
((52, 27), (47, 10), (36, 17), (10, 41), (13, 55), (10, 57), (31, 22), (19, 37))
((52, 27), (47, 10), (36, 17), (11, 41), (9, 55), (13, 57), (31, 22), (18, 37))
((52, 27), (47, 10), (36, 17), (11, 41), (9, 57), (13, 55), (31, 22), (18, 38))
((52, 27), (47, 10), (36, 17), (12, 41), (9, 55), (12, 57), (31, 22), (19, 37))
((52, 27), (47, 10), (36, 17), (8, 41), (11, 57), (14, 55), (30, 22), (18, 38))
((52, 27), (47, 10), (36, 17), (8, 41), (11, 58), (14, 54), (30, 22), (18, 38))
((52, 27), (47, 10), (36, 17), (8, 41), (14, 54), (11, 58), (30, 22), (19, 37))

```

人工确认：读取语句是否实际执行、值是否来自旧调用、是否仍适用当前盘面、是否用于搜索或动作、与新增关卡的关系。

