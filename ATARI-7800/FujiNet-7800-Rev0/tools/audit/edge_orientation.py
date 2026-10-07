#!/usr/bin/env python3
"""Check FujiNet-7800.pretty/Atari7800_Cart_Edge_32.kicad_mod (and tools/edge_geom.py's slots and
tab) against the sources for the Atari 7800 cartridge edge, collected 2026-10-07.  The schematic-
only Rev0's first footprint had 16 contiguous positions: pins 1, 2, 15, 16 (and 32, 31, 18, 17)
sat one pitch inward, on the console's key positions, with no slots and a 42.6 mm tab.

  [1] karrika/Otaku-flash (KiCad), Otaku/Otaku.pretty/A7800.kicad_mod + Otaku.kicad_pcb:
      F.Cu pads 1-16 at x -21.59, -19.05, -13.97 .. +13.97, +19.05, +21.59; B.Cu pad 33-k behind
      pad k; nets 1 R/W, 2 /Halt, 3 D3 .. 13 +5V, 14 GND, 15 A13, 16 A14, 17 A15, 18 Exaudio,
      32 PHI2; pads 2 x 7 mm, copper 0.31-7.31 mm in; Edge.Cuts slots x -17.7..-15.2 and
      +15.3..+17.9, 9.7 mm deep; tab 47.6 x 16.5 mm.
  [2] tdididit/a78-flashcartplus (Eagle), ATARI-7800-LARGE: pads 1-16 Top, 17-32 Bottom, same x,
      pin 1 RW at -21.59, 32 PHI2; 1.524 x 6.477 mm, copper 0.57-7.05 mm in; slots
      +-16.19..17.78, 8.89 mm deep; tab 46.99 mm; T-bar board 72.39 x 82.55 mm.
  [3] tdididit/a78-devcart gerbers: 16 fingers per face, 1.52 x 6.48 mm, at 0.585, 0.685,
      [gap], 0.885 .. 1.985, [gap], 2.185, 2.285 in; tab 1.85 in.
  [4] AtariAge 348171 (karri, Dissy614): a real cart measured 1.5 mm thick, pads 7 x 2 mm,
      connector 47.6 mm, cut width 2.4 mm, "the center of the cut is exactly where the pads 3
      and 16 would have been if the edge connector had 18 pads"; pitch 2.54; 1.6 mm FR4 fits.
  [5] J. Wierer, "Creating a 32K Atari 7800 Custom Cartridge" (digitpress): "Top/Component
      Side ... 1 2 | 3 ... 14 | 15 16" over "32 31 | 30 ... 19 | 18 17"; photos of an Atari
      C024926-001 board.
  [6] This repository's ATARI-2600/FujiPlusCart-Prototype gerbers (a working 2600 board, silk
      "THIS SIDE TO CONSOLE REAR" on the component face): Top fingers = 2600 pins 13-24
      (= 7800 pins 3-14), the two rightmost carrying 0.4 mm power traces (+5V, GND); Bottom
      leftmost (2600 pin 12 GND = 7800 pin 30) the third.  Parsed below.
  Faces: 7800 manuals ("hold the cartridge so the name on the label faces away from you"; PAL
  C301135-002 "the large label towards the back of the 7800"), UnoCart-2600 breakout and [6]
  put the D3..GND (pins 3-14) face toward the console's rear.
  Pin functions: Dan Boris, atarihq.com/danb/7800cart; Jindroush; HwB; [5].
"""
import os, re, sys
TOOLS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PRJ = os.path.dirname(TOOLS)
sys.path.insert(0, TOOLS)
from sexpr import parse, findall, find
import edge_geom as E

ok = True


def chk(msg, cond):
    global ok
    ok &= bool(cond)
    print('%-4s %s' % ('OK' if cond else 'FAIL', msg))


# ---- the footprint as written ----
fp = parse(open(os.path.join(PRJ, 'FujiNet-7800.pretty', 'Atari7800_Cart_Edge_32.kicad_mod')).read())
pads = {}
for p in findall(fp, 'pad'):
    at, size, lay = find(p, 'at'), find(p, 'size'), find(p, 'layers')
    pads[int(p[1])] = (float(at[1]), -float(at[2]), float(size[1]), float(size[2]), lay[1][0])
chk('32 pads, numbered 1-32', sorted(pads) == list(range(1, 33)))
chk('no Edge.Cuts in the footprint (the slots belong to the board outline)',
    'Edge.Cuts' not in open(os.path.join(PRJ, 'FujiNet-7800.pretty', 'Atari7800_Cart_Edge_32.kicad_mod')).read())

# ---- [1] [2] [5]: finger x, faces, k over 33-k ----
SRC_X = [-21.59, -19.05] + [round(-13.97 + 2.54 * i, 2) for i in range(12)] + [19.05, 21.59]
for k in range(1, 17):
    xf, _, _, _, lf = pads[k]
    xb, _, _, _, lb = pads[33 - k]
    chk('pin %2d at x %+6.2f on %s.Cu, pin %2d behind it on %s.Cu  (sources [1][2]: %+6.2f)'
        % (k, xf, lf, 33 - k, lb, SRC_X[k - 1]),
        abs(xf - SRC_X[k - 1]) < 1e-6 and abs(xb - xf) < 1e-6 and lf == 'F' and lb == 'B')
# [3] devcart, inches from its own origin: same spacing
DEV = [0.585, 0.685] + [round(0.885 + 0.1 * i, 3) for i in range(12)] + [2.185, 2.285]
d0 = (DEV[0] + DEV[-1]) / 2
chk('devcart [3] finger spacing equals ours', all(abs((d - d0) * 25.4 - SRC_X[i]) < 0.01 for i, d in enumerate(DEV)))

# ---- finger size and copper span against every source ----
w, h = pads[1][2], pads[1][3]
y0, y1 = abs(pads[1][1]) - h / 2, abs(pads[1][1]) + h / 2
SPANS = {'Otaku [1]': (2.0, 0.31, 7.31), 'tdididit [2]': (1.524, 0.57, 7.05),
         'devcart [3]': (1.52, 0.57, 7.05), 'FujiPlusCart [6]': (1.5, 0.58, 7.08)}
for name, (sw, c0, c1) in SPANS.items():
    print('     %-17s finger %.2f wide, copper %.2f-%.2f mm in' % (name, sw, c0, c1))
chk('ours %.2f wide, copper %.2f-%.2f: covers the span of [2][3][6] and is no wider than [1]'
    % (w, y0, y1), 1.27 <= w <= 2.0 and y0 <= 0.58 and y1 >= 7.05)

# ---- key slots ----
for sx in E.SLOT_X:
    a, b = abs(sx) - E.SLOT_W / 2, abs(sx) + E.SLOT_W / 2
    keys = {'karri/Otaku centre 16.51': 16.51, 'tdididit centre 16.99': 16.99}
    for name, kc in keys.items():   # a 1.0 mm key (Dissy614 measured) +- 0.2 mm
        chk('slot |x| %.2f-%.2f clears a 1.0 mm key at %s with >= 0.2 mm' % (a, b, name),
            a <= kc - 0.7 and b >= kc + 0.7)
chk('slot to finger copper >= 0.55 mm (%.2f)' % E.slot_clearance(), E.slot_clearance() >= 0.55)
chk('slot depth %.1f >= the deepest source cut (9.7) and > finger copper (%.1f)' % (E.SLOT_D, y1),
    E.SLOT_D >= 9.7 and E.SLOT_D > y1)
chk('tab %.1f mm inside the sources (45.85-47.6) and >= 1 mm beyond the outer fingers'
    % E.TAB_W, 45.85 <= E.TAB_W <= 47.6 and E.TAB_W / 2 - (21.59 + w / 2) >= 1.0)

# ---- [6] the working 2600 prototype: positions, faces and the power fingers ----
GB = os.path.join(PRJ, '..', '..', 'ATARI-2600', 'FujiPlusCart-Prototype')


def gerber(fn):
    ap = None; x = y = 0.0; segs = []; flashes = []; fmt = None
    for line in open(os.path.join(GB, fn)):
        line = line.strip()
        m = re.match(r'^%ADD(\d+)R,([\d.]+)X([\d.]+)\*%$', line)
        if m:
            fmt = fmt or {}
            fmt[int(m.group(1))] = (float(m.group(2)), float(m.group(3)))
        m = re.match(r'^D(\d+)\*$', line)
        if m:
            ap = int(m.group(1)); continue
        m = re.match(r'^(?:X(-?\d+))?(?:Y(-?\d+))?D0?([123])\*$', line)
        if m:
            nx = int(m.group(1)) / 1e6 if m.group(1) else x
            ny = int(m.group(2)) / 1e6 if m.group(2) else y
            if m.group(3) == '1':
                segs.append((ap, (x, y), (nx, ny)))
            elif m.group(3) == '3':
                flashes.append((ap, nx, ny))
            x, y = nx, ny
    return fmt or {}, segs, flashes


try:
    rects, top_s, top_f = gerber('Top.gbr')
    _, bot_s, bot_f = gerber('Bottom.gbr')
    fing = [a for a, (wx, hy) in rects.items() if abs(wx * 25.4 - 1.5) < 0.05 and hy * 25.4 > 6]
    tf = sorted(x for a, x, y in top_f if a in fing)
    bf = sorted(x for a, x, y in bot_f if a in fing)
    fy = {'top': [y for a, x, y in top_f if a in fing][0], 'bot': [y for a, x, y in bot_f if a in fing][0]}
    c = (tf[0] + tf[-1]) / 2
    chk('[6] 12 fingers per face, 2.54 mm pitch, faces aligned', len(tf) == len(bf) == 12 and tf == bf)
    chk('[6] prototype Top fingers (2600 13..24, left to right from the component side) sit at our '
        'pins 3..14', all(abs((x - c) * 25.4 - pads[3 + i][0]) < 0.01 for i, x in enumerate(tf)))

    def power(segs, fx, y):   # does a 0.4 mm trace (aperture 13, 0.015748 in) end on this finger?
        return any(ap == 13 and any(abs(p[0] - fx) < 0.03 and y - 0.13 < p[1] < y + 0.18 for p in (a, b))
                   for ap, a, b in segs)
    tp = [i for i, x in enumerate(tf) if power(top_s, x, fy['top'])]
    bp = [i for i, x in enumerate(bf) if power(bot_s, x, fy['bot'])]
    chk('[6] power traces on Top fingers 11, 12 (2600 23 +5V, 24 GND = 7800 pins 13, 14 at the right) '
        'and Bottom finger 1 (2600 12 GND = 7800 pin 30, behind pin 3)', tp == [10, 11] and bp == [0])
except FileNotFoundError as e:
    chk('[6] FujiPlusCart prototype gerbers present (%s)' % e, False)

print('RESULT:', 'pins 1-16 F.Cu (console rear), pin 1 left, 18 positions with key slots at 3 / 16: '
      'matches [1]-[6]' if ok else 'MISMATCH')
sys.exit(0 if ok else 1)
