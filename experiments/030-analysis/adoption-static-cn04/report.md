# 030 持久 Python 结果分析

自动提取的跨调用读取仅供人工复核；定义存在、函数保留和工具不报错均不等于实际解题收益。


## 实际 Python 调用与读取候选

| 文件 | 去重调用 | 异常 | 超时 | 状态丢失通知 | 成功读取候选调用 |
|---|---:|---:|---:|---:|---:|
| cn04-2fe56bfb_p0_requests.jsonl | 158 | 20 | 1 | 2 | 61 |

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

