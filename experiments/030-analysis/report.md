# 030 持久 Python 结果分析

自动提取的跨调用读取仅供人工复核；定义存在、函数保留和工具不报错均不等于实际解题收益。

| 臂 | 平均分 | 完成关卡 | 全通 | 动作 | 记录token | 分析器token |
|---|---:|---:|---:|---:|---:|---:|
| baseline | 42.6134 | 103/183 | 5 | 5377 | 4332548 | 4461854 |
| persistent_python | 47.1699 | 102/183 | 8 | 4643 | 4408842 | 4532258 |

候选减基线平均分：4.5565。

| 游戏 | 基线 | 候选 | 分差 | 关数差 |
|---|---:|---:|---:|---:|
| r11l-495a7899 | 14.286 | 92.345 | 78.059 | 4 |
| cd82-fb555c5d | 0.000 | 68.547 | 68.547 | 5 |
| cn04-2fe56bfb | 47.619 | 100.000 | 52.381 | 2 |
| su15-1944f8ab | 13.333 | 57.829 | 44.495 | 4 |
| ft09-0d8bbf25 | 67.148 | 100.000 | 32.852 | 1 |
| sc25-635fd71a | 34.787 | 67.386 | 32.598 | 1 |
| tu93-0768757b | 68.898 | 100.000 | 31.102 | 1 |
| dc22-fdcac232 | 25.517 | 47.619 | 22.102 | 1 |
| m0r0-492f87ba | 11.206 | 28.571 | 17.365 | 1 |
| s5i5-18d95033 | 2.100 | 16.667 | 14.566 | 2 |
| tr87-cd924810 | 97.171 | 100.000 | 2.829 | 0 |
| sk48-d8078629 | 0.824 | 0.956 | 0.132 | 0 |
| ar25-0c556536 | 100.000 | 100.000 | 0.000 | 0 |
| g50t-5849a774 | 0.000 | 0.000 | 0.000 | 0 |
| lp85-305b61c3 | 100.000 | 100.000 | 0.000 | 0 |
| bp35-0a0ad940 | 5.026 | 2.222 | -2.804 | -1 |
| lf52-271a04aa | 4.791 | 1.818 | -2.973 | -1 |
| re86-8af5384d | 58.333 | 54.510 | -3.823 | 0 |
| sb26-7fbdac44 | 100.000 | 96.158 | -3.842 | 0 |
| wa30-ee6fef47 | 22.222 | 2.222 | -20.000 | -3 |
| ls20-9607627b | 35.714 | 1.921 | -33.794 | -3 |
| ka59-38d34dbb | 45.968 | 10.714 | -35.253 | -3 |
| sp80-589a99af | 47.619 | 4.762 | -42.857 | -3 |
| tn36-ef4dde99 | 62.770 | 3.571 | -59.198 | -5 |
| vc33-5430563c | 100.000 | 21.429 | -78.571 | -4 |

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

