"""How each sheet is drawn: placement and wiring, one function per sheet, and the root.

design.py owns the circuit (Yannick Erb's board, written out); these functions only say where each
part sits and how its pins are joined (sch_draw.Sheet).  Parts are addressed by reference (they are
the board's).  A sheet without a drawing function is drawn as a draft (sch_draft.py: every pin
labelled) -- electrically identical.  sch_draw.Sheet.check(), gen_sch.check_hierarchy() and
gen_sch.netlist_parity() prove the drawing is exactly design.py's netlist, so a wiring slip here
fails the build.  The helpers are FujiNet-ColecoVision Rev0's.
"""
import os
import design as D
import sch_draft
from sch_draw import Sheet, Pt, snap

DRAW = {}
PAPER = {'cart-bus': 'A3', 'rp-core': 'A3', 'fujinet': 'A3', 'usb': 'A3', 'power': 'A3'}
G = 2.54
# cart-bus rows (2.54 mm each): the edge symbol and the RP2354A's unit A are built on them
# (gen_sch.edge_symbol / rp_split_symbol), so every bus line is one straight wire:
#   rows 0-15   AD0-15 (GP0-15)                    rows 17-20   MSYNC, BDIR, BC1, BC2 (GP21, 22, 26, 27)
#   row 23      /RESET from Q1's collector; GP20 drives its base through R13 two rows below (row 25)
#   row 29      EXT_AUDIO from GP28 (PWM) through R5
# the edge's left side: the three pass-through pairs, then the six unconnected fingers; the RP's
# right side: the TX / RX pads (GP16, 17), then its unconnected GPIOs
_EP = {}
for _pad, (_net, _nm) in D.EDGE.items():
    _EP.setdefault(_net, []).append(_pad)
_sig = {D.EDGE_SIGNAL[D.EDGE_PAD[p]]: p for p in D.EDGE}
ROW = {'N': 30,
       'EDGE': dict([(g, _sig['D%d' % g]) for g in range(16)] +
                    [(17, _sig['~{MSYNC}']), (18, _sig['BDIR']), (19, _sig['BC1']), (20, _sig['BC2']),
                     (23, _sig['~{RESET}']), (29, _sig['EXT_AUDIO'])]),
       'EDGE_LEFT': dict(list(zip((0, 1, 3, 4, 6, 7), sorted(_EP['PASS_A'] + _EP['PASS_B'] + _EP['PASS_C'],
                                                             key=lambda p: (D.EDGE[p][0], D.EDGE_PAD[p])))) +
                         list(zip(range(10, 16), sorted((p for p in D.EDGE if D.EDGE[p][0] is None),
                                                        key=lambda p: D.EDGE_PAD[p])))),
       'EDGE_TOP': _EP['VSYS'][0],
       'LEFT': dict([(g, g) for g in range(16)] + [(17, 21), (18, 22), (19, 26), (20, 27), (25, 20), (29, 28)]),
       'RIGHT': {0: 16, 2: 17, 5: 18, 6: 19, 7: 23, 8: 24, 9: 25, 10: 29}}
assert sorted(ROW['LEFT'].values()) == sorted(set(range(30)) - set(ROW['RIGHT'].values()))
assert len(ROW['EDGE']) + len(ROW['EDGE_LEFT']) + 1 + len(_EP['GND']) == 44


class KSheet(Sheet):
    """A Sheet whose parts are addressed by design.py key (references also work)."""
    def place(self, ref, *a, **k):
        return Sheet.place(self, D.KEY.get(ref, ref), *a, **k)

    def N(self, ref, net):
        return Sheet.N(self, D.KEY.get(ref, ref), net)

    def P(self, ref, num, unit=None):
        return Sheet.P(self, D.KEY.get(ref, ref), num, unit)


def sheet(stem):
    def deco(f):
        DRAW[stem] = f
        return f
    return deco


def draw(stem, syms, parts, cross):
    sh = KSheet(stem, syms, parts, PAPER[stem])
    if stem in DRAW and not os.environ.get('SCH_ALL_DRAFT'):
        DRAW[stem](sh)
    else:
        sch_draft.draft(sh, cross)
    return sh


def draw_root(syms, sheets):
    if os.environ.get('SCH_ALL_DRAFT') or 'root' not in DRAW:
        return sch_draft.draft_root(syms, sheets)
    return DRAW['root'](Sheet('root', syms, [], 'A3'), sheets)


# =========================================================================
# helpers
L_, R_, U_, D_ = (-1, 0), (1, 0), (0, -1), (0, 1)


def pin_place(sh, key, unit, pad, xy, **kw):
    """Place a unit so that pin `pad` lands on xy (both on the grid)."""
    d = sh.place(key, 0, 0, unit=unit, **kw)
    p = d['pins'][str(pad)]
    return sh.place(key, snap(xy[0] - p[0]), snap(xy[1] - p[1]), unit=unit, **kw)


def npin(sh, key, net, unit=None):
    """The pin end of `key`'s pin on `net` (in `unit` if given)."""
    ref = D.KEY[key]
    for (r, u), d in sh.placed.items():
        if r == ref and (unit is None or u == unit):
            for num, pt in d['pins'].items():
                if d['part'].pins.get(num) == net:
                    return pt
    raise KeyError('%s: %s has no placed pin on %s' % (sh.stem, key, net))


def fit(sh, key, pad, xy, want, unit=1, **kw):
    """Place a unit with pin `pad` on xy, turned (mirrored if need be) so that every pin in
    `want` ({pad: (dx, dy)}) points out that way."""
    for mirror in (None, 'x', 'y'):
        for rot in (0, 90, 180, 270):
            d = pin_place(sh, key, unit, pad, xy, rot=rot, mirror=mirror, **kw)
            if all((d['pins'][str(k)].dx, d['pins'][str(k)].dy) == v for k, v in want.items()):
                return d
    raise ValueError('%s: no orientation of %s fits %s' % (sh.stem, key, want))


def ncs(sh, key, unit=1):
    """No-connect flags on every unused pin of a placed unit."""
    ref = D.KEY[key]
    for num, pt in sh.placed[(ref, unit)]['pins'].items():
        if sh.parts[ref].pins[num] is None:
            sh.nc(pt)


def ground(sh, pin, n=2.54):
    """A pin to GND: a short stub, then the symbol hanging below (sideways pins turn down)."""
    if (pin.dx, pin.dy) == (0, 1):
        return sh.gnd(pin, n)
    e = sh.stub(pin, n)
    sh.rail(e, 'GND', 0)
    return e


def rail_pad(ref):
    """The pad of a two-pin part that is not on GND (Yannick's capacitors mostly have pin 1 on GND)."""
    return next(k for k, v in sorted(D.BY_REF[ref].pins.items()) if v != 'GND')


def gnd_pad(ref):
    return next(k for k, v in sorted(D.BY_REF[ref].pins.items()) if v == 'GND')


def pad_on(ref, net):
    return next(k for k, v in sorted(D.BY_REF[ref].pins.items()) if v == net)


def tee_cap(sh, key, pt, fields='right'):
    """A capacitor hanging from a point ON a horizontal line (the caller splits the line there),
    its ground under it."""
    rp = rail_pad(key)
    fit(sh, key, rp, (pt[0], snap(pt[1] + 2.54)), {rp: U_}, fields=fields)
    sh.wire(pt, sh.P(key, rp))
    sh.gnd(sh.P(key, gnd_pad(key)))


def tee_tp(sh, key, pt, fields='right', up=True):
    """A bring-up pad standing on (up) or hanging from (not up) a point of a horizontal line."""
    if up:
        fit(sh, key, 1, (pt[0], snap(pt[1] - 2.54)), {1: D_}, fields=fields)
    else:
        fit(sh, key, 1, (pt[0], snap(pt[1] + 2.54)), {1: U_}, fields=fields)
    sh.wire(pt, sh.P(key, 1))


def rail_line(sh, a, xs):
    """A horizontal line from a, split at every x in xs (so tees land on wire ends)."""
    pts = [a] + [(x, a[1]) for x in xs]
    for p, q in zip(pts, pts[1:]):
        sh.wire(p, q)
    return pts[-1]


def supply_pin(sh, pin, net, cap=None, fields=None):
    """A supply pin wired straight out to its rail symbol, its decoupling capacitor on a tee
    beside it, hanging down from a short stub (to the right of a vertical pin, below a horizontal
    one) with its ground under it -- beside the pin it serves."""
    o = (pin.dx, pin.dy)
    out, t = {(0, -1): (22.86, 15.24), (0, 1): (22.86, 7.62), (1, 0): (22.86, 7.62), (-1, 0): (22.86, 7.62)}[o]
    end = (snap(pin[0] + o[0] * out), snap(pin[1] + o[1] * out))
    sh.wire(pin, end)
    if net == 'GND':
        sh.rail(end, 'GND', {(0, 1): 0, (1, 0): 90, (0, -1): 180, (-1, 0): 270}[o])
    else:
        sh.rail(end, net, {(0, -1): 0, (-1, 0): 90, (0, 1): 180, (1, 0): 270}[o])
    if not cap:
        return end
    tee = (snap(pin[0] + o[0] * t), snap(pin[1] + o[1] * t))
    st = (tee[0] + 5.08, tee[1]) if o[1] != 0 else (tee[0], tee[1] + 2.54)
    sh.wire(tee, st)
    rp = rail_pad(cap)
    fit(sh, cap, rp, st, {rp: U_}, fields=fields or ('left' if o == (-1, 0) else 'right'))
    sh.gnd(sh.P(cap, gnd_pad(cap)))
    return end


def gate(sh, key, unit, out_xy, mirror=None, fields='above'):
    """Place one gate unit with its output pin end on out_xy; returns ({net: [input pins, top first]},
    output pin)."""
    d = pin_place(sh, key, unit, _out_pad(key, unit), out_xy, mirror=mirror, fields=fields)
    part = D.BY_KEY[key]
    ins = {}
    out = None
    for num, p in sorted(d['pins'].items(), key=lambda kv: kv[1][1]):
        if num == _out_pad(key, unit):
            out = p
        else:
            ins.setdefault(part.pins[num], []).append(p)
    return ins, out


def _out_pad(key, unit):
    v = D.BY_KEY[key].value
    return str(D.GATE_PINS[v][unit - 1][1])


def hres(sh, key, xy):
    """A horizontal resistor, pin 1 on xy facing left, its reference and value side by side above
    it (a ladder of these 2 x 2.54 apart keeps every name clear of the neighbouring lines)."""
    d = fit(sh, key, 1, xy, {1: L_})
    cx = (sh.P(key, 1)[0] + sh.P(key, 2)[0]) / 2
    y = snap(xy[1] - 2.54)
    d['fields'] = [(round(cx - 0.635, 3), y, 'right'), (round(cx + 0.635, 3), y, 'left')]
    return d


def hres_u(sh, key, unit, xy):
    """hres() for one resistor of a 4-resistor array (unit u = pins u and 9-u), pin u on xy facing left."""
    d = fit(sh, key, unit, xy, {unit: L_}, unit=unit)
    cx = (sh.P(key, unit, unit)[0] + sh.P(key, 9 - unit, unit)[0]) / 2
    y = snap(xy[1] - 2.54)
    d['fields'] = [(round(cx - 0.635, 3), y, 'right'), (round(cx + 0.635, 3), y, 'left')]
    return d




RN_UNIT = {pad: k for k, pad in enumerate((1, 2, 3, 4, 6, 7, 8, 9), 1)}   # gen_sch.RN_ELEMENTS


def pullup(sh, pad, xy, fields='right'):
    """One RN1 element standing on a horizontal line at xy (its element pin down onto the line),
    its common up to 3V3."""
    u = RN_UNIT[pad]
    fit(sh, 'RN1', pad, (xy[0], snap(xy[1] - 2.54)), {pad: D_}, unit=u, fields=fields)
    sh.wire(xy, sh.P('RN1', pad, u))
    sh.sup(sh.P('RN1', 5, u), '3V3')
    return u


# =========================================================================
@sheet('fujinet')
def fujinet(sh):
    """The ESP32-S3 and what hangs off it (FujiNet-ColecoVision Rev0's drawing): the module's 3V3
    decoupling above it; EN's power-on RC and the RESET button (SW2) on the EN line above its left
    end, BOOT (SW1), its 100 nF and pull-up on IO0 left of it; the RP2354A's RUN / BOOTSEL controls and
    USB pair in from the left (the rp-core sheet); the UART out to the USB bridge on the right; the
    microSD below it, its SPI lines stepping down into the socket with the pull-ups between them; the
    status LED at the page's foot."""
    sh.wired = True
    sh.crossing_budget = 0                         # planar
    U = 'U7'
    d = sh.place(U, 190.5, 116.84, fields='abovebelow')
    b = d['body']
    d['fields'][1] = (b[0] - 1.27, b[3] + 1.778, 'right')
    P = lambda n: sh.P(U, n)
    ncs(sh, U)
    x = 190.5
    y_t = b[1]
    # ---- 3V3 and its decoupling, bulk to the right -----------------------------------------------
    v = P(2)
    yt = snap(v[1] - 15.24)
    sh.wire(v, (v[0], snap(v[1] - 22.86)))
    sh.sup((v[0], snap(v[1] - 22.86)), '3V3')
    tops = []
    for c, dx in (('C26', 7.62), ('C24', 20.32)):
        rp = rail_pad(c)
        tops.append(fit(sh, c, rp, (snap(v[0] + dx), yt), {rp: U_}, fields='right')['pins'][rp])
        sh.gnd(sh.P(c, gnd_pad(c)))
    sh.wire((v[0], yt), tops[0])
    sh.wire(tops[0], tops[1])
    # ---- EN: up to its line; the 10k pull-up, the 1 uF delay, RESET, then out left ----------------
    en = P(3)
    y_en = snap(y_t - 20.32)
    x_l = snap(x - 121.92)                             # the page's left-hand port column
    sh.wire(en, (en[0], y_en), (x_l, y_en))
    sh.hlabel(Pt(x_l, y_en, -1, 0), 'S3_EN', 'L', 'bidirectional')
    fit(sh, 'R17', 2, (snap(en[0] - 7.62), snap(y_en - 2.54)), {2: D_}, fields='right')
    sh.wire((snap(en[0] - 7.62), y_en), sh.P('R17', 2))
    sh.sup(sh.P('R17', 1), '3V3')
    tee_cap(sh, 'C2', (snap(en[0] - 15.24), y_en))
    xr = snap(en[0] - 33.02)
    fit(sh, 'SW2', 1, (xr, snap(y_en + 2.54)), {1: U_}, fields='left')
    sh.wire((xr, y_en), sh.P('SW2', 1))
    sh.gnd(sh.P('SW2', 2))
    # ---- IO0: BOOT, its 100 nF and its pull-up on tees, then out left (the auto-program pair) --------
    io0 = P(27)
    sh.wire(io0, (x_l, io0[1]))
    sh.hlabel(Pt(x_l, io0[1], -1, 0), 'S3_IO0', 'L', 'bidirectional')
    xb = snap(x - 88.9)
    fit(sh, 'SW1', 1, (xb, snap(io0[1] + 2.54)), {1: U_}, fields='left')
    sh.wire((xb, io0[1]), sh.P('SW1', 1))
    sh.gnd(sh.P('SW1', 2))
    tee_cap(sh, 'C3', (snap(xb + 12.7), io0[1]))
    pullup(sh, 9, (snap(xb + 25.4), io0[1]))
    # ---- the RP2354A's controls and USB, straight in from the left -----------------------------
    for n, net, shape in ((4, 'RUN_CTL', 'output'), (5, 'BOOTSEL_CTL', 'output'),
                          (14, 'USB_DP', 'bidirectional'), (13, 'USB_DM', 'bidirectional')):
        p = P(n)
        sh.wire(p, (x_l, p[1]))
        sh.hlabel(Pt(x_l, p[1], -1, 0), net, 'L', shape)
    # ---- the UART to the CP2102N, out right ----------------------------------------------------
    x_r = snap(x + 88.9)
    for n, net, shape in ((37, 'S3_TXD', 'output'), (36, 'S3_RXD', 'input')):
        p = P(n)
        sh.wire(p, (x_r, p[1]))
        sh.hlabel(Pt(x_r, p[1], 1, 0), net, 'R', shape)
    sh.gnd(P(1))
    # ---- the microSD: the SPI lines step down and right into the socket --------------------------
    y_b = P(31)[1]
    x_j = snap(x + 53.34)
    J = 'U8'
    d = sh.place(J, 0, 0, fields='abovebelow')
    dy = snap(y_b + 10.16 - d['pins']['8'][1])
    dx = snap(x_j - d['pins']['8'][0])
    d = sh.place(J, dx, dy, fields='abovebelow')
    jb = d['body']
    d['fields'][1] = (jb[2] + 1.27, jb[3] - 1.27, 'left')
    for net in ('SD_MOSI', 'SD_SCK', 'SD_MISO', 'SD_CS'):
        a, b = sh.N(U, net), sh.N(J, net)
        sh.wire(a, (a[0], b[1]), b)
        sh.label((snap(x_j - 12.7), b[1]), net, 'R')
    sh.nc(sh.P(J, 9))                                  # card detect: not used (PIN_CARD_DETECT NC)
    # pull-ups: CS, MISO and MOSI each in the gap right of its line, DAT1 / DAT2 off the socket's pins
    for net, pad in (('SD_CS', 3), ('SD_MISO', 1), ('SD_MOSI', 2)):
        a, b = sh.N(U, net), sh.N(J, net)
        pullup(sh, pad, (snap(a[0] + 5.08), b[1]))
    for net, pad, xp in (('SD_DAT1', 6, snap(x + 40.64)), ('SD_DAT2', 4, snap(x + 33.02))):
        b = sh.N(J, net)
        sh.wire(b, (xp, b[1]))
        pullup(sh, pad, (xp, b[1]))
        sh.label((snap(xp + 1.27 if pad == 6 else x_j - 12.7), b[1]), net, 'R')
    # the two unused elements, over the socket
    for pad, xp in ((7, snap(x + 60.96)), (8, snap(x + 68.58))):
        u = RN_UNIT[pad]
        top = (xp, snap(y_b - 7.62))
        fit(sh, 'RN1', 5, top, {5: U_}, unit=u, fields='right')
        sh.sup(sh.P('RN1', 5, u), '3V3')
        sh.nc(sh.P('RN1', pad, u))
    for u in (1, 2, 3, 4, 6, 7, 8):                    # the array named once, on its DAT1 element
        sh.placed[('RN1', u)]['hide_fields'] = ('Reference', 'Value')
    # the socket's supply with its 10 uF and 100 nF, its ground and the shell
    vdd, vss = sh.N(J, '3V3'), sh.P(J, 6)
    e = (snap(vdd[0] - 25.4), vdd[1])
    sh.wire(vdd, (snap(vdd[0] - 7.62), vdd[1]), (snap(vdd[0] - 20.32), vdd[1]), e)
    sh.sup(e, '3V3', rot=90)
    for c, dxc, side in (('C28', 7.62, 'left'), ('C27', 20.32, 'left')):
        rp = rail_pad(c)
        fit(sh, c, rp, (snap(vdd[0] - dxc), snap(vdd[1] + 5.08)), {rp: U_}, fields=side)
        sh.wire((snap(vdd[0] - dxc), vdd[1]), sh.P(c, rp))
        sh.gnd(sh.P(c, gnd_pad(c)))
    ground(sh, vss)
    sh.gnd(sh.P(J, 10), 2.54)
    # ---- the status LED: IO48 -> 330R -> SK6805 DIN, on 3V3, at the page's foot -------------------
    led = P(25)
    y_l = snap((jb[1] + jb[3]) / 2 + 22.86)
    x_w = snap(x - 58.42)
    fit(sh, 'R15', 1, (snap(x_w + 22.86), y_l), {1: R_}, fields='above')
    sh.wire(led, (led[0], y_l), sh.P('R15', 1))
    sh.label((led[0], snap(led[1] + 1.27)), 'LED_STRIP', 'D')
    d = fit(sh, 'D6', 2, (x_w, y_l), {2: R_, 3: U_}, fields='right')
    wb = d['body']
    d['fields'] = [(wb[2] + 1.27, y_l + 3.81, 'left'), (wb[2] + 1.27, y_l + 6.35, 'left')]
    sh.wire(sh.P('R15', 2), sh.P('D6', 2))
    sh.label((snap(sh.P('R15', 2)[0] - 1.27), y_l), 'LED_DIN', 'L')
    sh.nc(sh.P('D6', 4))
    sh.gnd(sh.P('D6', 1))
    vd = sh.P('D6', 3)
    t5 = (vd[0], snap(vd[1] - 5.08))
    sh.wire(vd, t5, (vd[0], snap(vd[1] - 7.62)))
    sh.sup((vd[0], snap(vd[1] - 7.62)), '3V3')
    rp = rail_pad('C1')
    fit(sh, 'C1', rp, (snap(vd[0] - 12.7), snap(t5[1] + 2.54)), {rp: U_}, fields='left')
    sh.wire(t5, (snap(vd[0] - 12.7), t5[1]), sh.P('C1', rp))
    sh.gnd(sh.P('C1', gnd_pad('C1')))
    sh.text((snap(x_l - 2.54), 30.48),
            'ESP32-S3-WROOM-1-N16R8: the FujiNet (include/pinmap/fujiversal-intv.h), on 3V3 (the buck).\n'
            'EN: 10k / 1 uF power-on delay; RESET (SW2) and the USB bridge\'s auto-program pair\n'
            '(usb sheet) pull it low; BOOT (SW1) and the same pair pull IO0 (100 nF, 10k up).\n'
            'IO4 / IO5 drive the RP2354A\'s RUN and BOOTSEL through Q4 / Q3 (rp-core: high = asserted);\n'
            'IO19 / IO20, the S3\'s own USB, host the RP\'s.\n'
            'microSD in SPI mode, the YC158 array\'s 10k on CS, DO, DI, DAT1 and DAT2; card detect unused.\n'
            'SK6805-EC20 status LED on IO48 through 330R, on 3V3.\n'
            'The spare GPIOs (right) are not connected.')
    return sh


# =========================================================================
@sheet('usb')
def usb(sh):
    """USB-C to the ESP32-S3, right to left (FujiNet-ColecoVision Rev0's drawing, the receptacle on the
    page's right): VBUS up and along the top with its ESD diode and the bridge's VBUS-sense divider;
    CC1 / CC2 to their 5.1k; the D- / D+ pair straight into the CP2102N (drawn mirrored, USB side
    toward the receptacle), each line with its ESD5Z; the bridge's UART out to the S3 on the left and
    its RTS / DTR into the esptool auto-program pair (UMH3N), whose collectors pull the S3's EN and
    IO0.  That pair is the page's one crossing: RTS and DTR leave the bridge side by side and each
    reaches the base of one transistor and the emitter of the other."""
    sh.wired = True
    sh.crossing_budget = 1
    U, J, Q = 'U3', 'J1', 'Q2'
    xc, yc = 165.1, 139.7
    d = fit(sh, U, '4', (snap(xc + 12.7), snap(yc - 10.16)), {'4': R_, '25': L_, '6': U_}, fields='abovebelow')
    d['fields'][1] = (d['body'][2] + 1.27, d['body'][3] + 1.778, 'left')
    P = lambda n: sh.P(U, n)
    ncs(sh, U)
    sh.gnd(P(3))
    x_l = snap(xc - 88.9)                              # the left-hand port column, to the S3
    # ---- the bridge's supply: VDD and VREGIN on 3V3, its 100 nF to the right -------------------
    vdd, vri = P(6), P(7)
    y_bar = snap(vdd[1] - 12.7)
    sh.wire(vdd, (vdd[0], y_bar))
    sh.wire(vri, (vri[0], y_bar))
    a, b = sorted(((vdd[0], y_bar), (vri[0], y_bar)))
    sh.wire(a, b)
    rp = rail_pad('C23')
    cu = fit(sh, 'C23', rp, (snap(b[0] + 7.62), y_bar), {rp: U_}, fields='right')['pins'][rp]
    sh.wire(b, cu)
    sh.sup(cu, '3V3')
    sh.gnd(sh.P('C23', gnd_pad('C23')))
    # ---- the UART, out left to the S3 -------------------------------------------------------------
    for n, net, shape in (('26', 'S3_RXD', 'output'), ('25', 'S3_TXD', 'input')):
        p = P(n)
        sh.wire(p, (x_l, p[1]))
        sh.hlabel(Pt(x_l, p[1], -1, 0), net, 'L', shape)
    e = sh.stub(P('23'), 2.54)                         # /CTS held asserted
    sh.rail(e, 'GND', 270)
    # ---- RTS / DTR into the auto-program pair: transistor 1 (DTR base) pulls EN, 2 (RTS base) IO0 ---
    rts, dtr = P('24'), P('28')
    x_j2, x_j1 = snap(rts[0] - 12.7), snap(rts[0] - 20.32)
    y_q2 = snap(rts[1] + 15.24)
    y_q1 = snap(y_q2 + 17.78)
    x_q2b = snap(x_j1 - 12.7)

    def q_fields(d):                                   # ref / value right of the body, under the base line
        b = d['body']
        d['fields'] = [(b[2] + 1.27, d['y'] + 3.81, 'left'), (b[2] + 1.27, d['y'] + 6.35, 'left')]
    q_fields(fit(sh, Q, '5', (x_q2b, y_q2), {'5': R_, '3': U_}, unit=2))
    sh.wire(rts, (x_j1, rts[1]), (x_j1, y_q2), (x_q2b, y_q2))
    sh.label((snap(rts[0] - 2.54), rts[1]), 'UART_RTS', 'L')
    e2 = sh.P(Q, '4', 2)
    x_q1b = snap(e2[0] - 7.62)
    q_fields(fit(sh, Q, '2', (x_q1b, y_q1), {'2': R_, '6': U_}, unit=1))
    sh.wire(dtr, (x_j2, dtr[1]), (x_j2, y_q1), (x_q1b, y_q1))
    sh.label((snap(dtr[0] - 2.54), dtr[1]), 'UART_DTR', 'L')
    sh.wire(e2, (e2[0], y_q1))
    c2 = sh.P(Q, '3', 2)
    y_io = snap(c2[1] - 2.54)
    sh.wire(c2, (c2[0], y_io), (x_l, y_io))
    sh.hlabel(Pt(x_l, y_io, -1, 0), 'S3_IO0', 'L', 'bidirectional')
    c1 = sh.P(Q, '6', 1)
    y_en = snap(y_q2 + 5.08)
    sh.wire(c1, (c1[0], y_en), (x_l, y_en))
    sh.hlabel(Pt(x_l, y_en, -1, 0), 'S3_EN', 'L', 'bidirectional')
    e1 = sh.P(Q, '1', 1)
    x_t = snap(x_q2b + 7.62)
    y_low = snap(e1[1] + 5.08)
    sh.wire(e1, (e1[0], y_low), (x_t, y_low), (x_t, y_q2))
    sh.text((snap(x_l + 2.54), snap(y_low + 7.62)),
            "esptool's auto-program pair, as on the ESP32-S3-DevKitC-1:\n"
            'DTR low with RTS high pulls EN low; RTS low with DTR high pulls\n'
            'IO0 low; both high or both low leave the S3 alone.', 1.27)
    # ---- the USB side: reset pull-up, VBUS sense, the pair to the receptacle ---------------------
    rst = P('9')
    x_rst = snap(rst[0] + 12.7)
    fit(sh, 'R10', 1, (x_rst, snap(rst[1] - 2.54)), {1: D_}, fields='right')
    sh.wire(rst, (x_rst, rst[1]), sh.P('R10', 1))
    sh.sup(sh.P('R10', 2), '3V3')
    sh.label((snap(rst[0] + 1.27), rst[1]), 'CP_RST', 'R')
    dm, dp, sns = P('5'), P('4'), P('8')
    y_m = dm[1]
    x_n = snap(dm[0] + 25.4)
    x_em = snap(x_n + 38.1)
    x_u = snap(x_em + 22.86)
    d = fit(sh, J, '7', (x_u, y_m), {'7': L_}, fields='abovebelow')
    d['fields'][1] = (d['body'][2] + 1.27, d['body'][3] - 1.27, 'left')
    JP = lambda n: sh.P(J, n)
    # VBUS: up from the receptacle and along the top, its ESD diode hanging from it
    v = JP('2')
    y_v = snap(y_m - 33.02)
    sh.wire(v, (v[0], y_v), (x_n, y_v))
    sh.rail((v[0], y_v), 'VBUS', 0)
    xx = snap(x_u - 38.1)
    fit(sh, 'D5', '1', (xx, snap(y_v + 2.54)), {'1': U_}, fields='right')
    sh.wire((xx, y_v), sh.P('D5', '1'))
    sh.gnd(sh.P('D5', '2'))
    # the sense divider: 22.1k from VBUS down to the node, 47.5k from it to GND
    node = (x_n, sns[1])
    fit(sh, 'R9', 2, (x_n, snap(y_v + 2.54)), {2: U_}, fields='left')
    sh.wire((x_n, y_v), sh.P('R9', 2))
    sh.wire(sh.P('R9', 1), node)
    sh.wire(sns, node)
    sh.label((snap(sns[0] + 1.27), sns[1]), 'VBUS_SNS', 'R')
    fit(sh, 'R18', 2, (snap(x_n + 5.08), sns[1]), {2: L_}, fields='above')
    sh.wire(node, sh.P('R18', 2))
    sh.rail(sh.P('R18', 1), 'GND', 90)
    # CC1 / CC2: 5.1k to GND right at the receptacle
    for pin, key in (('4', 'R7'), ('10', 'R8')):
        p = JP(pin)
        fit(sh, key, 2, (snap(p[0] - 7.62), p[1]), {2: R_}, fields='above')
        sh.wire(p, sh.P(key, 2))
        sh.rail(sh.P(key, 1), 'GND', 270)
        sh.label((snap(p[0] - 6.35), p[1]), sh.parts[key].pins['2'], 'R')
    # D- and D+ straight from the bridge to the receptacle, each with its ESD5Z on a tee: D-'s
    # standing above its line, D+'s hanging under its own
    x_e = snap(x_n + 20.32)
    sh.wire(dm, JP('7'))
    sh.label((snap(dm[0] + 1.27), y_m), 'UBRTG_DM', 'R')
    fit(sh, 'D3', '1', (x_e, snap(y_m - 2.54)), {'1': D_}, fields='right')
    sh.wire((x_e, y_m), sh.P('D3', '1'))
    sh.rail(sh.P('D3', '2'), 'GND', 180)
    b7 = JP('5')
    sh.wire(b7, (snap(b7[0] - 2.54), b7[1]), (snap(b7[0] - 2.54), y_m))
    a6 = JP('6')
    if dp[1] == a6[1]:
        sh.wire(dp, a6)
    else:
        x_s = snap(x_e - 7.62)
        sh.wire(dp, (x_s, dp[1]), (x_s, a6[1]), a6)
    sh.label((snap(dp[0] + 1.27), dp[1]), 'UBRTG_DP', 'R')
    x_e2 = snap(x_e + 7.62)
    fit(sh, 'D4', '1', (x_e2, snap(a6[1] + 2.54)), {'1': U_}, fields='right')
    sh.wire((x_e2, a6[1]), sh.P('D4', '1'))
    sh.gnd(sh.P('D4', '2'))
    b6 = JP('8')
    sh.wire(b6, (snap(b6[0] - 2.54), b6[1]), (snap(b6[0] - 2.54), a6[1]))
    for n in ('9', '3'):
        sh.nc(JP(n))
    sh.gnd(JP('1'))
    sh.gnd(JP('13'))
    return sh


# =========================================================================
@sheet('power')
def power(sh):
    """The power tree, left to right: the console's +5V (VSYS, the edge's pin 43) and USB's VBUS,
    each through an SS34 into VIN (whichever is higher feeds the board); VIN's bulk on tees; the
    AP63203 buck under the line, its bootstrap and inductor on its right, out to 3V3, the board's
    one logic rail (the RP2354A, the ESP32-S3, the CP2102N, the microSD and the LED).  The PWR_FLAGs
    of the rails only passive parts drive sit together, bottom left; the shell's two holes, bottom
    right."""
    sh.wired = True
    sh.crossing_budget = 0
    x0, y1 = 76.2, 101.6
    y2 = snap(y1 + 15.24)
    xd = snap(x0 + 25.4)                               # the diodes' anodes
    for net, ref, y in (('VSYS', 'D1', y1), ('VBUS', 'D2', y2)):
        fit(sh, ref, '2', (xd, y), {'2': L_, '1': R_}, fields='above')
        sh.wire((x0, y), sh.P(ref, '2'))
        sh.rail((x0, y), net, 90)
    xj = snap(sh.P('D1', '1')[0] + 7.62)
    sh.wire(sh.P('D1', '1'), (xj, y1))
    sh.wire(sh.P('D2', '1'), (xj, y2), (xj, y1))
    # ---- VIN: the bulk, the buck's input cap, the rail symbol, then down into the buck ------------
    x_c29, x_c25, x_sym = snap(xj + 10.16), snap(xj + 22.86), snap(xj + 33.02)
    x_bk = snap(xj + 43.18)
    rail_line(sh, (xj, y1), [x_c29, x_c25, x_sym, x_bk])
    tee_cap(sh, 'C29', (x_c29, y1))
    tee_cap(sh, 'C25', (x_c25, y1))
    sh.wire((x_sym, y1), (x_sym, snap(y1 - 2.54)))
    sh.rail((x_sym, snap(y1 - 2.54)), 'VIN', 0)
    d = fit(sh, 'U2', '3', (snap(x_bk + 5.08), snap(y1 + 17.78)), {'3': L_, '5': R_, '4': D_}, fields='below')
    d['fields'] = [(d['body'][0], d['body'][1] - 1.778, 'left'), (d['body'][0] - 1.27, d['body'][3] + 1.778, 'right')]
    vin, en = sh.P('U2', 3), sh.P('U2', 2)
    sh.wire((x_bk, y1), (x_bk, vin[1]), (x_bk, en[1]), en)
    sh.wire((x_bk, vin[1]), vin)
    sh.gnd(sh.P('U2', 4))
    sw, bst, fb = sh.P('U2', 5), sh.P('U2', 6), sh.P('U2', 1)
    y_top = snap(sw[1] - 10.16)
    x_s, x_c = snap(sw[0] + 2.54), snap(sw[0] + 7.62)
    fit(sh, 'C21', 1, (x_c, y_top), {1: U_}, fields='right')
    sh.wire(sw, (x_s, sw[1]), (x_s, y_top), sh.P('C21', 1))
    sh.wire(bst, (x_c, bst[1]), sh.P('C21', 2))
    sh.label((x_s, snap(sw[1] - 1.27)), 'BUCK_SW', 'U')
    sh.label((snap(bst[0] + 1.27), bst[1]), 'BUCK_BST', 'R')
    sh.sup(fb, '3V3', 2.54, rot=270)                   # FB senses the output (3.3 V fixed)
    fit(sh, 'L2', 1, (snap(x_c + 7.62), y_top), {1: L_}, fields='above')
    sh.wire(sh.P('C21', 1), sh.P('L2', 1))
    bo = sh.P('L2', 2)
    xs = [snap(bo[0] + 7.62), snap(bo[0] + 17.78), snap(bo[0] + 27.94)]
    rail_line(sh, bo, xs)
    tee_cap(sh, 'C4', (xs[0], y_top))
    tee_cap(sh, 'C22', (xs[1], y_top))
    sh.wire((xs[2], y_top), (xs[2], snap(y_top - 2.54)))
    sh.rail((xs[2], snap(y_top - 2.54)), '3V3', 0)
    # ---- PWR_FLAGs: the rails driven only through passive parts --------------------------------
    y_f = snap(y2 + 38.1)
    for k_, net in enumerate(('GND', 'VSYS', 'VBUS', 'VIN', '3V3')):
        x = snap(x0 + 25.4 * k_)
        sh.wire((x, y_f), (snap(x + 10.16), y_f))
        sh.flag((snap(x + 10.16), y_f), net)
        sh.rail((x, y_f), net, 0)
    sh.text((x0, snap(y_f - 12.7)), "PWR_FLAG: these rails reach their loads only through passive parts (the edge "
            "finger, USB-C, the diodes, the buck's inductor).", 1.27)
    # ---- the shell's post holes -----------------------------------------------------------------
    for k_, h in enumerate(('H1', 'H2')):
        sh.place(h, snap(x0 + 165.1 + 30.48 * k_), y_f, fields='below')
    sh.text((snap(x0 + 157.48), snap(y_f - 12.7)), 'H1, H2: the shell\'s post holes, 5.127 mm NPTH.', 1.27)
    sh.text((x0, 25.4),
            "Power tree: VIN is the higher of the console's +5V (VSYS, edge pin 43) and USB VBUS (usb sheet), each through\n"
            'an SS34 Schottky (D1, D2): neither source back-feeds the other, and a cart on USB never powers a console that is off.\n'
            'C29 100 uF and C25 10 uF hold VIN.  U2 AP63203, 3.3 V / 2 A synchronous buck (4.7 uH, 22 uF + 100 nF out), makes 3V3,\n'
            'the board\'s one logic rail: the RP2354A (its core regulator makes 1V1, rp-core), the ESP32-S3, the CP2102N, the\n'
            'microSD and the status LED.  VSYS and VBUS are global: the edge (cart-bus) and the USB-C (usb) carry them here.', 1.27)
    return sh


def npn(sh, q, x_col, y_base, fields='right', base=L_):
    """A BC847 with its collector's pin end on the column x_col, its base pin end on the row y_base,
    the base facing `base` (left, or right: mirrored), collector up, emitter down to GND; returns
    (collector, base) pin ends."""
    fit(sh, q, '1', (x_col, y_base), {'1': base, '3': U_}, fields=fields)
    dx = snap(x_col - sh.P(q, '3')[0])
    fit(sh, q, '1', (snap(sh.P(q, '1')[0] + dx), y_base), {'1': base, '3': U_}, fields=fields)
    sh.gnd(sh.P(q, '2'))
    return sh.P(q, '3'), sh.P(q, '1')


# =========================================================================
@sheet('rp-core')
def rp_core(sh):
    """The RP2354A's own circuit around its core unit (FujiNet-ColecoVision Rev0's drawing, the
    QFN-60's pins): every supply pin with its capacitor beside it; along the top the QSPI_SS strap
    with its pull-up, RP-BOOT and the S3's BOOTSEL transistor, the USB pair and the core-regulator
    corner (VREG_LX -> 3.3 uH -> 1V1, VREG_AVDD through 27R); along the bottom the crystal, SWD and
    RUN with its pull-up, RP-RUN and the S3's RUN transistor.  The USB pair and the S3's BOOTSEL /
    RUN controls leave on the right, to the fujinet sheet."""
    sh.wired = True
    sh.crossing_budget = 0
    U = 'U1'
    sh.place(U, 210.82, 160.02, unit=2, fields='abovebelow')
    P = lambda n: sh.P(U, n, 2)
    R3, DV = '3V3', '1V1'
    # ---- the decoupling ring: every supply pin to its rail, its cap beside it ------------------
    for n, cap in ((45, 'C7'), (54, 'C10'), (53, None), (49, 'C18')):
        supply_pin(sh, P(n), R3, cap)                  # C10 serves QSPI_IOVDD and USB_OTP_VDD
    for n, cap in ((38, 'C8'), (44, None), (20, 'C12'), (30, 'C13'), (1, 'C9'), (11, 'C11')):
        supply_pin(sh, P(n), R3, cap)
    for n, cap in ((39, 'C16'), (23, 'C15'), (6, 'C14')):
        supply_pin(sh, P(n), DV, cap)
    supply_pin(sh, P(50), DV)                          # VREG_FB senses 1V1
    for n in (47, 61):
        supply_pin(sh, P(n), 'GND')
    for n in (55, 56, 57, 58, 59):                     # QSPI data and clock: the flash inside the package
        sh.nc(P(n))
    # ---- the core regulator: VREG_LX -> 3.3 uH -> 1V1; VREG_AVDD through 27R from 3V3 ------------
    lx = P(48)
    fit(sh, 'L1', 1, (lx[0], snap(lx[1] - 10.16)), {1: D_}, fields='right')
    sh.wire(lx, sh.P('L1', 1))
    sh.label((lx[0], snap(lx[1] - 1.27)), 'VREG_LX', 'U')
    sh.sup(sh.P('L1', 2), DV)
    av = P(46)
    tee = (av[0], snap(av[1] - 12.7))
    fit(sh, 'R6', 2, tee, {2: D_}, fields='right')
    sh.wire(av, tee)
    sh.label((av[0], snap(av[1] - 1.27)), 'VREG_AVDD', 'U')
    sh.sup(sh.P('R6', 1), R3)
    st = (snap(tee[0] + 12.7), tee[1])
    sh.wire(tee, st)
    rp = rail_pad('C19')
    fit(sh, 'C19', rp, st, {rp: U_}, fields='right')
    sh.gnd(sh.P('C19', gnd_pad('C19')))
    sh.flag(st, 'VREG_AVDD')
    # the regulator's output capacitor and 1V1's PWR_FLAG (the regulator drives it through the inductor)
    xd, yd = snap(st[0] + 15.24), snap(tee[1] - 5.08)
    sh.rail((xd, yd), DV, 0)
    e = sh.wire((xd, yd), (snap(xd + 12.7), yd))
    rp = rail_pad('C17')
    fit(sh, 'C17', rp, (xd, yd), {rp: U_}, fields='right')
    sh.gnd(sh.P('C17', gnd_pad('C17')))
    sh.flag(e, DV)
    # ---- above the RP: the USB pair out to the fujinet sheet ---------------------------------------
    xr = snap(P(38)[0] + 63.5)                         # the page's right-hand port column
    y_bs, y_ss, y_usb = 58.42, 68.58, 83.82
    for n, rkey, net, inner, y in ((52, 'R4', 'USB_DP', 'USB_D+', y_usb),
                                   (51, 'R3', 'USB_DM', 'USB_D-', snap(y_usb + 2.54))):
        p = P(n)
        fit(sh, rkey, 1, (p[0], snap(p[1] - 15.24)), {1: D_}, fields='left' if n == 52 else 'right')
        sh.wire(p, sh.P(rkey, 1))
        sh.label((p[0], snap(p[1] - 1.27)), inner, 'U')
        b = sh.P(rkey, 2)
        sh.wire(b, (b[0], y), (xr, y))
        sh.hlabel(Pt(xr, y, 1, 0), net, 'R', 'bidirectional')
    # ---- QSPI_SS: up to the BOOTSEL row, its pull-up on a tee; R11 -> RP-BOOT, Q3 on that node ------
    ss = P(60)
    sh.label((ss[0], snap(ss[1] - 1.27)), 'QSPI_SS', 'U')
    sh.wire(ss, (ss[0], y_ss), (ss[0], y_bs))
    xs = snap(ss[0] - 5.08)
    sh.wire((ss[0], y_ss), (xs, y_ss))
    fit(sh, 'R12', 2, (xs, snap(y_ss - 2.54)), {2: D_}, fields='left')
    sh.wire((xs, y_ss), sh.P('R12', 2))
    sh.sup(sh.P('R12', 1), R3)
    fit(sh, 'R11', 1, (snap(ss[0] + 7.62), y_bs), {1: L_}, fields='above')
    sh.wire((ss[0], y_bs), sh.P('R11', 1))
    r11 = sh.P('R11', 2)
    x_q3 = snap(r11[0] + 10.16)
    x_sw = snap(r11[0] + 30.48)
    fit(sh, 'SW3', 1, (x_sw, y_bs), {1: L_}, fields='above')
    ground(sh, sh.P('SW3', 2))
    sh.wire(r11, (x_q3, y_bs), sh.P('SW3', 1))
    sh.label((snap(r11[0] + 1.27), y_bs), 'BOOTSEL_BTN', 'R')
    # Q3 hangs under the BOOTSEL_BTN line: collector up to it, base (right) from BOOTSEL_CTL via R1
    y_b3 = snap(y_bs + 10.16)
    col, base = npn(sh, 'Q3', x_q3, y_b3, fields='left', base=R_)
    sh.wire(col, (x_q3, y_bs))
    fit(sh, 'R1', 1, (snap(base[0] + 15.24), y_b3), {1: L_}, fields='below')
    sh.wire(base, sh.P('R1', 1))
    sh.label((snap(base[0] + 1.27), y_b3), 'BOOTSEL_Q_B', 'R')
    sh.wire(sh.P('R1', 2), (xr, y_b3))
    sh.hlabel(Pt(xr, y_b3, 1, 0), 'BOOTSEL_CTL', 'R', 'input')
    # ---- the crystal: XIN straight into it, XOUT through 1k, both 15 pF to GND -------------------
    xi, xo = P(21), P(22)
    fit(sh, 'R2', 1, (xo[0], snap(xo[1] + 7.62)), {1: U_}, fields='right')
    sh.wire(xo, sh.P('R2', 1))
    sh.label((xo[0], snap(xo[1] + 6.35)), 'XOUT', 'U')
    y_c = snap(sh.P('R2', 2)[1] + 10.16)
    fit(sh, 'U5', 1, (snap(xi[0] + 2.54), y_c), {1: L_, 3: R_}, fields='above')
    sh.gnd(sh.P('U5', 2))
    for col, ykey, cap in ((xi, 1, 'C5'), (sh.P('R2', 2), 3, 'C6')):
        rp = rail_pad(cap)
        fit(sh, cap, rp, (col[0], snap(y_c + 5.08)), {rp: U_}, fields='left' if cap == 'C5' else 'right')
        sh.wire(col, sh.P(cap, rp))
        sh.wire((col[0], y_c), sh.P('U5', ykey))
        sh.gnd(sh.P(cap, gnd_pad(cap)))
    sh.label((xi[0], snap(xi[1] + 6.35)), 'XIN', 'U')
    sh.label((xo[0], snap(y_c - 1.27)), 'XOUT_Y', 'U')
    # ---- SWD: down and left under the crystal to the bring-up pads -------------------------------
    y1 = snap(y_c + 22.86)
    rows = {'SWCLK': y1, 'SWD': snap(y1 + 5.08)}
    x_tp = snap(P(20)[0] - 5.08)
    for n, tp in (('SWCLK', 'TP5'), ('SWD', 'TP4')):
        p = sh.N(U, n)
        fit(sh, tp, 1, (x_tp, rows[n]), {1: R_}, fields='left')
        sh.wire(p, (p[0], rows[n]), sh.P(tp, 1))
        sh.label((p[0], snap(p[1] + 6.35)), n, 'U')
    yg = snap(rows['SWD'] + 5.08)
    fit(sh, 'TP1', 1, (x_tp, yg), {1: R_}, fields='left')
    ground(sh, sh.P('TP1', 1))
    # ---- RUN: down to its line; the pull-up, RP-RUN, and Q4 (the S3's RUN_CTL through R16) ---------
    run = P(26)
    sh.label((run[0], snap(run[1] + 6.35)), 'RUN', 'U')
    y_r = snap(P(47)[1] + 33.02)
    x_pu = snap(P(61)[0] + 10.16)
    x_q4, x_sw4 = snap(x_pu + 30.48), snap(x_pu + 40.64)
    sh.wire(run, (run[0], y_r))
    rail_line(sh, (run[0], y_r), [x_pu, x_q4, x_sw4])
    fit(sh, 'R14', 2, (x_pu, snap(y_r - 2.54)), {2: D_}, fields='left')
    sh.wire((x_pu, y_r), sh.P('R14', 2))
    sh.sup(sh.P('R14', 1), R3)
    fit(sh, 'SW4', 1, (x_sw4, snap(y_r + 2.54)), {1: U_}, fields='right')
    sh.wire((x_sw4, y_r), sh.P('SW4', 1))
    sh.gnd(sh.P('SW4', 2))
    # Q4 hangs under the RUN line: collector up to it, base (left) from RUN_CTL via R16, which runs
    # out under everything to the port column
    y_b4 = snap(y_r + 10.16)
    col, base = npn(sh, 'Q4', x_q4, y_b4)
    sh.wire(col, (x_q4, y_r))
    fit(sh, 'R16', 1, (snap(base[0] - 15.24), y_b4), {1: R_}, fields='below')
    sh.wire(sh.P('R16', 1), base)
    sh.label((snap(sh.P('R16', 1)[0] + 1.27), y_b4), 'RUN_Q_B', 'R')
    r16 = sh.P('R16', 2)
    y_rc = snap(y_b4 + 15.24)
    x_rc = snap(r16[0] - 2.54)
    sh.wire(r16, (x_rc, y_b4), (x_rc, y_rc), (xr, y_rc))
    sh.hlabel(Pt(xr, y_rc, 1, 0), 'RUN_CTL', 'R', 'input')
    sh.text((snap(P(1)[0] - 40.64), 25.4),
            'Supplies (RP2350 datasheet): IOVDD, QSPI_IOVDD, USB_OTP_VDD, ADC_AVDD and VREG_VIN on 3V3 (the buck, power sheet);\n'
            'the core regulator switches VREG_LX through 3.3 uH onto 1V1 (VREG_FB senses it), its analog supply VREG_AVDD\n'
            'through 27R / 4.7 uF.  Capacitors as Yannick placed them, each drawn at the pin it serves (C10 at QSPI_IOVDD and\n'
            'USB_OTP_VDD; ADC_AVDD and USB_OTP_VDD have none of their own).  The RP2354A\'s 2 MB flash is in the package:\n'
            'its QSPI data and clock pins are not connected; QSPI_SS is the BOOTSEL strap (10k up).\n'
            'RP-BOOT (SW3) pulls it low through R11; so does Q3 when the S3 raises BOOTSEL_CTL (IO5).  RP-RUN (SW4) resets\n'
            'the RP; so does Q4 when the S3 raises RUN_CTL (IO4): high = asserted (README: firmware).  USB: 27R at the RP,\n'
            'the S3 is the host.  SWD and GND on bring-up pads (TP4, TP5, TP1).')
    return sh


# =========================================================================
@sheet('cart-bus')
def cart_bus(sh):
    """The 44-finger edge on the left and the RP2354A's GPIO unit on the right, mirrored row for row
    (ROW): AD0-15 and MSYNC / BDIR / BC1 / BC2 each one straight wire from its finger to its GPIO;
    the console's /RESET from Q1's collector, which GP20 drives through R13 two rows below; the ECS
    audio from GP28 (PWM) through R5 into EXT_AUDIO.  The edge's left side: the three pass-through
    pairs, each joined round its own two fingers, and the six unconnected fingers; +5V (VSYS) on top,
    the nine GND fingers below (stacked).  The RP's right side: the TX / RX pads (GP16, GP17) and its
    unconnected GPIOs."""
    sh.wired = True
    sh.crossing_budget = 0
    x_e, x_r, y0 = 101.6, 251.46, 101.6
    de = sh.place('K1', x_e, y0, fields='abovebelow')
    de['fields'][1] = (de['body'][0] - 1.27, de['body'][3] + 1.778, 'right')   # clear of the GND pin
    dr = sh.place('U1', x_r, y0, unit=1, fields='abovebelow')
    E = lambda pad: sh.P('K1', pad)
    G = lambda g: sh.P('U1', D.RP_GPIO_PIN[g], 1)
    # ---- the bus: straight across, a label on each line by the RP ---------------------------------
    for r, pad in ROW['EDGE'].items():
        g = ROW['LEFT'].get(r)
        net = D.EDGE[pad][0]
        if net in ('CART_RST', 'AUD'):
            continue
        a, b = E(pad), G(g)
        assert a[1] == b[1], (pad, g, a, b)
        sh.wire(a, b)
        sh.label((snap(b[0] - 12.7), a[1]), net, 'R')
    # ---- the console reset: GP20 -> R13 -> Q1's base; Q1's collector up onto /RESET's row -----------
    rst, g20 = E(_sig['~{RESET}']), G(20)
    x_q = snap(x_e + 50.8)
    col, base = npn(sh, 'Q1', x_q, g20[1], fields='left', base=R_)
    assert col[1] == rst[1], (col, rst)
    sh.wire(rst, col)
    sh.label((snap(rst[0] + 5.08), rst[1]), 'CART_RST', 'R')
    fit(sh, 'R13', 1, (snap(base[0] + 15.24), g20[1]), {1: L_}, fields='above')
    sh.wire(base, sh.P('R13', 1))
    sh.label((snap(base[0] + 1.27), g20[1]), 'RST_Q_B', 'R')
    sh.wire(sh.P('R13', 2), g20)
    sh.label((snap(g20[0] - 12.7), g20[1]), 'GPIO20', 'R')
    # ---- the ECS audio: GP28 (PWM) -> R5 -> EXT_AUDIO ------------------------------------------------
    au, g28 = E(_sig['EXT_AUDIO']), G(28)
    assert au[1] == g28[1]
    fit(sh, 'R5', 1, (snap(x_q + 15.24), au[1]), {1: L_}, fields='above')
    sh.wire(au, sh.P('R5', 1))
    sh.label((snap(au[0] + 5.08), au[1]), 'AUD', 'R')
    sh.wire(sh.P('R5', 2), g28)
    sh.label((snap(g28[0] - 12.7), g28[1]), 'PWM', 'R')
    # ---- the edge's left side: the pass-through pairs, the unconnected fingers ------------------------
    rows = sorted(ROW['EDGE_LEFT'].items())
    for (r1, p1), (r2, p2) in zip(rows[0:6:2], rows[1:6:2]):
        a, b = E(p1), E(p2)
        xl = snap(a[0] - 5.08)
        sh.wire(a, (xl, a[1]), (xl, b[1]), b)
        sh.label((snap(a[0] - 1.27), a[1]), D.EDGE[p1][0], 'L')
    for r, p in rows[6:]:
        sh.nc(E(p))
    # ---- +5V and the grounds ----------------------------------------------------------------------
    sh.sup(E(ROW['EDGE_TOP']), 'VSYS', 2.54)
    gnd = sorted((p for p, v in D.EDGE.items() if v[0] == 'GND'), key=lambda p: D.EDGE_PAD[p])
    sh.gnd(E(gnd[0]), 2.54)
    # ---- the RP's right side: TX / RX pads, the unconnected GPIOs ------------------------------------
    for g, tp in ((16, 'TP2'), (17, 'TP3')):
        p = G(g)
        fit(sh, tp, 1, (snap(p[0] + 17.78), p[1]), {1: L_}, fields='right')
        sh.wire(p, sh.P(tp, 1))
        sh.label((snap(p[0] + 1.27), p[1]), 'GPIO%02d' % g, 'R')
    ncs(sh, 'U1', unit=1)
    sh.text((snap(x_e - 25.4), 25.4),
            "The Intellivision's cartridge port: 44 contacts, 2 x 22 at 2.54 mm.  Yannick's footprint numbers the fingers A1-A22\n"
            '(component face) and B1-B22 (back), left to right seen from the component face, contacts down: finger A(k) is INTV\n'
            'pin 46 - 2k, B(k) pin 45 - 2k (even pins in front, odd behind); each pin is named with its INTV number.\n'
            'The CP1610 bus (AD0-15, BDIR, BC1, BC2) and MSYNC reach the RP2354A straight (fujinet-firmware pico/intellivision\n'
            'boards/fujicard.h: MI_AD0_PIN 0, MSYNC 21, BDIR 22, BC1 26, BC2 27, RST 20).  GP26 / GP27 (BC1 / BC2) are ADC pins,\n'
            'not 5 V tolerant (GP0-25 are), as on the PiNTY CARD.  GP20 high turns Q1 on: the console\'s /RESET (pin 12) low.\n'
            'GP28 drives EXT_AUDIO (pin 6, the ECS audio) through 1k (pintycard.h MI_AUDIO_PIN 28).  The three shorted pairs pass a\n'
            'console signal through the cart (32 / 42, 34 / 40, 36 / 38).  GP16 / GP17 go to the TX / RX pads.')
    return sh


# =========================================================================
ROOT_NOTES = """Inty-FujiCard v1.1: Yannick Erb's PINTY-FUJI-CARD, FujiNet for the Intellivision on one cartridge:
an RP2354A on the console's bus + an ESP32-S3.

The cart serves the CP1610's bus in software (fujinet-firmware pico/intellivision, board fujicard); the
S3 is the FujiNet (fujiversal-intv) and the RP's USB host.

  cart-bus   the 44-finger edge, the bus straight into GP0-15 / 21 / 22 / 26 / 27, the console reset
             (GP20, Q1), the ECS audio (GP28, R5), the TX / RX pads
  rp-core    the RP2354A's supplies and decoupling, core regulator, crystal, SWD, RUN / BOOTSEL with
             their buttons and the S3's transistors, its USB out to the S3
  fujinet    the ESP32-S3, its EN / BOOT buttons, microSD, SK6805 status LED
  usb        USB-C, ESD diodes, the CP2102N bridge and esptool's auto-program pair
  power      VIN = the console's +5V or USB VBUS (two SS34), the AP63203 buck: 3V3 for everything

Rails (GND, VSYS, VBUS, VIN, 3V3, 1V1) join by their power symbols.

The board came first: tools/convert.py brought Yannick's EasyEDA layout to KiCad unchanged, and this
schematic is drawn from its netlist (tools/design.py, checked against the board by
tools/board_netlist.py; the board against this schematic by KiCad's DRC parity).
tools/check_nets.py checks this netlist against the firmware (README: firmware)."""


def root(sh, sheets):
    """The block diagram in signal-flow order: cart-bus and rp-core on the left, then the FujiNet
    half -- fujinet with usb under it -- on the right, power above; the eight signals between sheets
    wired without a crossing: the RP's controls and USB straight across to the S3; S3_EN, S3_IO0 and
    the UART down nested channels to the USB bridge."""
    b, i, o = 'bidirectional', 'input', 'output'
    sh.block('power', 30.48, 33.02, 63.5, 20.32)
    sh.block('cart-bus', 30.48, 172.72, 63.5, 20.32)
    rp = sh.block('rp-core', 30.48, 76.2, 63.5, 81.28,
                  right=[('USB_DP', b), ('USB_DM', b), ('RUN_CTL', i), ('BOOTSEL_CTL', i)])
    fj = sh.block('fujinet', 132.08, 33.02, 30.48, 99.06,
                  left=[None] * 17 + [('USB_DP', b), ('USB_DM', b), ('RUN_CTL', o), ('BOOTSEL_CTL', o)]
                  + [None] * 10 + [('S3_EN', b), ('S3_IO0', b), ('S3_TXD', o), ('S3_RXD', i)])
    us = sh.block('usb', 132.08, 152.4, 30.48, 35.56,
                  left=[('S3_RXD', o), ('S3_TXD', i), ('S3_IO0', b), ('S3_EN', b)])
    for n in ('USB_DP', 'USB_DM', 'RUN_CTL', 'BOOTSEL_CTL'):
        assert rp[n][1] == fj[n][1], (n, rp[n], fj[n])
        sh.wire(rp[n], fj[n])
        sh.label((snap(rp[n][0] + 1.27), rp[n][1]), n)
    for k, n in enumerate(('S3_EN', 'S3_IO0', 'S3_TXD', 'S3_RXD')):
        xc = snap(fj[n][0] - 10.16 + 2.54 * k)
        sh.wire(fj[n], (xc, fj[n][1]), (xc, us[n][1]), us[n])
        sh.label((xc, snap(us[n][1] - 1.27)), n, 'U')
    sh.text((30.48, 203.2), 'the console cartridge slot (the 44-finger edge) is on cart-bus', 1.27)
    sh.text((187.96, 25.4), ROOT_NOTES, 1.27)
    for stem, title, page in D.SHEETS:
        have = {l[1] for l in sheets[stem].labels if l[0] == 'hierarchical_label'}
        blk = next(x for x in sh.blocks if x['stem'] == stem)
        assert have == set(blk['pins']), (stem, sorted(have ^ set(blk['pins'])))
    return sh


DRAW['root'] = root
