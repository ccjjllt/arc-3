def norm(mm):
    rows=[r for r in mm if '#' in r]
    if not rows: return ()
    r0=min(r.index('#') for r in rows); r1=max(len(r)-1-r.rindex('#') for r in rows)
    return tuple(r[r0:len(r)-r1] for r in rows)

def rotCW(b):
    R=len(b); C=len(b[0])
    return norm([''.join(b[R-1-r][c] for r in range(R)) for c in range(C)])

def canon(b):
    cur=norm(b); best=None
    for _ in range(4):
        if best is None or cur<best: best=cur
        cur=rotCW(cur)
    return best
