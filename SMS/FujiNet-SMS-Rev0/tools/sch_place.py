"""The schematic mirrors the board: page = the board turned so that the fingers face left.

    board south (the edge)        -> page left      (signals flow left to right: console -> FujiNet)
    board north (USB-C, antenna)  -> page right
    board west                    -> page top
    board east                    -> page bottom

sch_layout.py places each sheet's parts by hand from where they sit on the board under this
turn; mirror_check() holds the result to it: for every major part on a sheet (ICs, connectors,
transistors, switches, the crystal, the LEDs) the order of the parts across the page and down it
agrees with their order on the board (Kendall tau >= TAU on each axis), and no major part sits in
the wrong quadrant of the sheet's spread.

A part drawn as several units counts once, at the centre of its units on the sheet; the 74HCT
glue packages count once together, as the glue network (their gates are drawn by logic depth,
not package by package).  Two parts less than TIE_MM apart along an axis on the board are level
on it: their order on the page is free.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import design as D

TAU = 0.85
TIE_MM = 5.0
MAJOR = ('U', 'J', 'Q', 'SW', 'Y')
MAJOR_KEYS = ('D_WS', 'D_LED', 'D_RST', 'D_VBUS')


def page_xy(bx, by):
    """Board (x, y) -> an unscaled page direction: (north-ness, east-ness)."""
    return (-by, bx)


def kendall(a, b, tie=0.0):
    """Kendall tau between two equal-length sequences (ties count as neither; a pair whose a
    values are closer than `tie` is a tie)."""
    n, c, d = len(a), 0, 0
    for i in range(n):
        for j in range(i + 1, n):
            if abs(a[i] - a[j]) < tie:
                continue
            s = (a[i] - a[j]) * (b[i] - b[j])
            c += s > 0
            d += s < 0
    return (c - d) / (c + d) if c + d else 1.0


def major(p, unit):
    return (p.prefix in MAJOR or p.key in MAJOR_KEYS) and (not p.unit_sheets or unit == min(
        u for u, s in p.unit_sheets.items() if s == p.unit_sheets[unit]))


def mirror_check(sheet, place):
    """sheet: a drawn sch_draw.Sheet; place: gen_pcb.PLACE (ref -> (x, y, rot)).  Returns
    (tau_x, tau_y, problems)."""
    groups = {}                  # group -> ([board page_xy], [page centres])
    for (ref, u), d in sheet.placed.items():
        p = d['part']
        if not major(p, u) or ref not in place:
            continue
        g = 'glue' if p.value.startswith('74') else ref
        bx, by, _ = place[ref]
        cx = (d['body'][0] + d['body'][2]) / 2
        cy = (d['body'][1] + d['body'][3]) / 2
        b, c = groups.setdefault(g, ({}, []))
        b[ref] = page_xy(bx, by)
        c.append((cx, cy))
    mean = lambda v: (sum(q[0] for q in v) / len(v), sum(q[1] for q in v) / len(v))
    pts = [(g, mean(list(b.values())), mean(c)) for g, (b, c) in groups.items()]
    if len(pts) < 3:
        return 1.0, 1.0, []
    tx = kendall([q[1][0] for q in pts], [q[2][0] for q in pts], TIE_MM)
    ty = kendall([q[1][1] for q in pts], [q[2][1] for q in pts], TIE_MM)
    probs = []
    if tx < TAU:
        probs.append('%s: left-right order vs the board (north-ness) tau %.2f < %.2f' % (sheet.stem, tx, TAU))
    if ty < TAU:
        probs.append('%s: top-bottom order vs the board (east-ness) tau %.2f < %.2f' % (sheet.stem, ty, TAU))
    # quadrants about the medians
    import statistics as st
    mbx = st.median(q[1][0] for q in pts); mby = st.median(q[1][1] for q in pts)
    mpx = st.median(q[2][0] for q in pts); mpy = st.median(q[2][1] for q in pts)
    for ref, b, pg in pts:
        if (b[0] - mbx) * (pg[0] - mpx) < 0 and abs(b[0] - mbx) > 8 or \
                (b[1] - mby) * (pg[1] - mpy) < 0 and abs(b[1] - mby) > 8:
            probs.append('%s: %s is on the wrong side of the sheet for its board position'
                         % (sheet.stem, ref if ref == 'glue' else '%s (%s)' % (ref, D.BY_REF[ref].key)))
    return tx, ty, probs
