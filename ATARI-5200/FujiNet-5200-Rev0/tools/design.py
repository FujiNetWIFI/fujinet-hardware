"""FujiNet-5200 Rev0 (RP2354B) -- the single source of truth.

Every part, value, footprint, MPN, manufacturer, LCSC code and pin->net assignment lives here.
gen_sch.py, gen_pcb.py, check_nets.py, check_glue.py and export.py import it; the KiCad files are
generated output.  Parts are addressed by `key` (the drawing, the layout, the audits); references
are labels, numbered by where each part sits on the board (tools/refs.lock, tools/annotate.py).

One sheet per board region, console side first (the FujiNet-SMS Rev0 v2 arrangement): every sheet
is the board turned so the fingers face left, so the schematic reads from the cartridge slot
outward.

Circuit provenance: FujiNet-SMS Rev0 v2 / FujiNet-7800 Rev0 (this repository) for the RP2354B
core, the ESP32-S3 / microSD / USB-UART sheets, the power OR and the S3 pin contract; the cart side
(edge, '541 data buffer, glue, PHI2 buffer, interlock, the edge's raw-DC input) is new.
Firmware contract:
  fujinet-firmware pico/atari-5200/firmware/include/a52_cart.h   (RP pins, a52_glue_drive)
  fn-5200-board include/pinmap/fujiversal-atari5200.h            (S3 pins)
The console side, from Atari's CX5200 Field Service Manual (Rev 4, July 1983: schematics of
CA018087, the original 4-port board, CA020108, the universal 4-port, and CA021374, the 2-port; the
parts lists), Atari's 1983 engineering drawings and Upgrade Bulletin VCS-01, ANALOG #15 / #16:
docs/design-review-rev0.md, Part 1.
"""

LIB = 'FujiNet-5200'
PROJECT = 'FujiNet-5200-Rev0'
NC = None  # explicit no-connect

SHEETS = [  # (file stem, title, page): one sheet per board region, console side first
    ('cart-bus', "Cart bus: edge, RP GPIO, '541 + glue", 2),
    ('rp-core', 'RP2354B core: supplies, crystal, USB, RUN', 3),
    ('fujinet', 'FujiNet: ESP32-S3, microSD, LED', 4),
    ('usb', 'USB-C and the CP2102N bridge', 5),
    ('power', 'Power: +5V OR, 5V / 3.3V bucks, RP LDO', 6),
]
SHEET_ORDER = [s[0] for s in SHEETS]

# ---- RP2354B (QFN-80) GPIO -> package pin ---------------------------------
# Read from KiCad's MCU_RaspberryPi:RP2354B symbol; gen_sch.py re-checks every
# entry against the symbol's pin names before writing a sheet.
RP_GPIO_PIN = {0: 77, 1: 78, 2: 79, 3: 80, 4: 1, 5: 2, 6: 3, 7: 4, 8: 6, 9: 7, 10: 8, 11: 9,
               12: 11, 13: 12, 14: 13, 15: 14, 16: 16, 17: 17, 18: 18, 19: 19, 20: 20, 21: 21,
               22: 22, 23: 23, 24: 25, 25: 26, 26: 27, 27: 28, 28: 36, 29: 37, 30: 38, 31: 39,
               32: 40, 33: 42, 34: 43, 35: 44, 36: 45, 37: 46, 38: 47, 39: 48, 40: 49, 41: 52,
               42: 53, 43: 54, 44: 55, 45: 56, 46: 57, 47: 58}
RP_IOVDD_PINS = [5, 15, 24, 29, 41, 50, 60, 76]
RP_DVDD_PINS = [10, 32, 51]
RP_IO_RAIL = '+3V3_RP'     # IOVDD x8, QSPI_IOVDD, USB_OTP_VDD, ADC_AVDD: the fast LDO
RP_CORE_RAIL = RP_IO_RAIL  # VREG_VIN (+ VREG_AVDD through 33R) on the same LDO rail

# a52_cart.h.  GPIO0-31 are the 5 V-tolerant bus inputs; GPIO40-47 are not and carry only the ADC
# sense and the 3.3 V debug header.
RP_GPIO_NET = {i: 'A%d' % i for i in range(14)}                     # A0_PIN 0: A0-A13
RP_GPIO_NET.update({14: 'EN40_N', 15: 'EN80_N'})                    # EN40_PIN, EN80_PIN
RP_GPIO_NET.update({16 + i: 'RP_D%d' % i for i in range(8)})        # D0_PIN 16: into the '541
RP_GPIO_NET.update({24: 'PWR_OK', 25: 'PHI2_RP', 26: 'BUF_EN', 27: 'RP_LED', 28: 'ILK'})
RP_GPIO_NET.update({g: NC for g in range(29, 40)})
RP_GPIO_NET.update({40: 'VSENSE_ADC', 41: NC, 42: NC, 43: NC, 44: 'DBG_TX', 45: 'DBG_RX', 46: NC, 47: NC})
assert len(RP_GPIO_NET) == 48 and set(RP_GPIO_NET) == set(RP_GPIO_PIN)

# ESP32-S3-WROOM-1 module pad -> function (pads per the KiCad symbol)
S3_PAD = {'GND': [1, 40, 41], '3V3': 2, 'EN': 3, 'IO4': 4, 'IO5': 5, 'IO6': 6,
          'IO7': 7, 'IO15': 8, 'IO16': 9, 'IO17': 10, 'IO18': 11, 'IO8': 12,
          'IO19': 13, 'IO20': 14, 'IO3': 15, 'IO46': 16, 'IO9': 17, 'IO10': 18,
          'IO11': 19, 'IO12': 20, 'IO13': 21, 'IO14': 22, 'IO21': 23,
          'IO47': 24, 'IO48': 25, 'IO45': 26, 'IO0': 27, 'IO35': 28,
          'IO36': 29, 'IO37': 30, 'IO38': 31, 'IO39': 32, 'IO40': 33,
          'IO41': 34, 'IO42': 35, 'RXD0': 36, 'TXD0': 37, 'IO2': 38, 'IO1': 39}
# fujiversal-atari5200.h (the fujiversal S3 contract) + RUN/BOOTSEL on IO4/IO5
S3_NET = {'EN': 'S3_EN', 'IO0': 'S3_IO0', 'IO4': 'RUN_CTL', 'IO5': 'BOOTSEL_CTL',
          'IO19': 'USB_DM', 'IO20': 'USB_DP', 'IO38': 'SD_MOSI', 'IO39': 'SD_SCK',
          'IO40': 'SD_MISO', 'IO41': 'SD_CS', 'IO42': 'SD_CD', 'IO48': 'LED_STRIP',
          'RXD0': 'S3_RXD', 'TXD0': 'S3_TXD'}

# Atari 5200 36-pin cartridge edge: (net, symbol pin name).  18 positions per face; pins 1-18 on
# the label face (F.Cu), pin 1 at the left seen from it, pin 37-k behind pin k (tools/edge_geom.py,
# tools/audit/edge_orientation.py).  Per the FSM (all three main boards unless stated):
#   9 / 10   /Y2 ($8000-$BFFF) and /Y1 ($4000-$7FFF) of a 74LS139 on A14 / A15, enable grounded:
#            pure address decodes, not qualified by PHI2; the slot has no R/W and no reset
#   11       NC on CA018087; UNREG D.C. (the adapter's raw 9-13 V, always live) on CA020108 /
#            CA021374.  Never grounded (Atari UB VCS-01: "the 5200 Power Adaptor will burn out").
#   14       GND on CA018087; PHI2 on the universal boards through a 74LS125 and CR9 (1N914,
#            anode at pin 14): the console can only pull it low, the cart pulls it up
#   18 / 36  CI1 / CI2, the interlock: a stock cart joins them; that switches VR1, the regulator
#            that feeds pin 26, the console RAM and its reset circuit.  Short fingers (last-make).
#   23       shield, GND on every board; 24 GND on CA018087, VIDEO IN through CR10 on the
#            universal boards: left open, as 28 (NC) and 30 (NC / OSC CON, the colour oscillator)
#   26       +5 V from VR1 (78M05 on CA018087, FSM parts list), through a ferrite bead
EDGE = {1: ('D0', 'D0'), 2: ('D1', 'D1'), 3: ('D2', 'D2'), 4: ('D3', 'D3'), 5: ('D4', 'D4'),
        6: ('D5', 'D5'), 7: ('D6', 'D6'), 8: ('D7', 'D7'), 9: ('EN80_N', '~{EN80}'),
        10: ('EN40_N', '~{EN40}'), 11: ('UNREG', 'UNREG'), 12: ('GND', 'GND'), 13: ('GND', 'GND'),
        14: ('PHI2', 'PHI2/GND'), 15: ('A6', 'A6'), 16: ('A5', 'A5'), 17: ('A2', 'A2'),
        18: ('ILK_A', 'CI1'), 19: ('A0', 'A0'), 20: ('A1', 'A1'), 21: ('A3', 'A3'), 22: ('A4', 'A4'),
        23: ('GND', 'GND'), 24: (NC, 'VID/GND'), 25: ('GND', 'GND'), 26: ('CONS_5V', '+5V'),
        27: ('A7', 'A7'), 28: (NC, 'NC'), 29: ('A8', 'A8'), 30: (NC, 'OSC'), 31: ('A9', 'A9'),
        32: ('A13', 'A13'), 33: ('A10', 'A10'), 34: ('A12', 'A12'), 35: ('A11', 'A11'),
        36: ('ILK_B', 'CI2')}

# ---- common parts: (lib_id, footprint, MPN, LCSC) --------------------------
FP = lambda n: '%s:%s' % (LIB, n)
R0603 = FP('R_0603_1608Metric')
C0603 = FP('C_0603_1608Metric')
C0805 = FP('C_0805_2012Metric')
SOIC14 = FP('SOIC-14_3.9x8.7mm_P1.27mm')
RES = {'2.2R': ('RC0603FR-072R2L', 'C112307'), '27R': ('0603WAF270JT5E', 'C25190'),
       '33R': ('0603WAF330JT5E', 'C23140'), '330R': ('0603WAF3300T5E', 'C23138'),
       '1k': ('0603WAF1001T5E', 'C21190'), '4.7k': ('0603WAF4701T5E', 'C23162'),
       '5.1k': ('0603WAF5101T5E', 'C23186'), '10k': ('0603WAF1002T5E', 'C25804'),
       '22k': ('0603WAF2202T5E', 'C31850'), '47k': ('0603WAF4702T5E', 'C25819'),
       '100k': ('0603WAF1003T5E', 'C25803')}
CAP = {'15pF': (C0603, 'CL10C150JB8NNNC', 'C1644'),
       '100nF': (C0603, 'CC0603KRX7R9BB104', 'C14663'),        # 50 V
       '1uF': (C0603, 'CL10A105KB8NNNC', 'C15849'),            # 50 V
       '4.7uF': (C0603, 'CL10A475KO8NNNC', 'C19666'),          # 16 V
       '10uF': (C0603, 'CL10A106KP8NNNC', 'C19702'),           # 10 V: 5 V and 3.3 V rails only
       '22uF': (C0805, 'CL21A226MAQNNNE', 'C45783')}           # 25 V: also the edge's raw DC
RPACK = {'4x10k': ('4D03WGJ0103T5E', 'C29718')}

# MPN -> manufacturer (PCBWay sources by MPN + manufacturer; names from LCSC's / JLCPCB's pages)
MFR = {'RP2354B': 'Raspberry Pi', 'CC0603KRX7R9BB104': 'YAGEO', 'CL10A106KP8NNNC': 'Samsung Electro-Mechanics',
       'CL10A475KO8NNNC': 'Samsung Electro-Mechanics', 'CL10C150JB8NNNC': 'Samsung Electro-Mechanics',
       'CL10A105KB8NNNC': 'Samsung Electro-Mechanics', 'CL21A226MAQNNNE': 'Samsung Electro-Mechanics',
       'AOTA-B201610S3R3-101-T': 'Abracon', 'ABM8-272-T3': 'Abracon',
       'TS-1187A-B-A-B': 'XKB Connection', 'BAT54C,215': 'Nexperia',
       '4D03WGJ0103T5E': 'UNI-ROYAL', 'KT-0603R': 'Hubei KENTO Elec', '2N7002': 'Jiangsu Changjing (JSCJ)',
       'PZ254V-11-03P': 'XFCN', 'SN74HCT14DR': 'Texas Instruments', 'SN74HCT08DR': 'Texas Instruments',
       'SN74HCT541PWR': 'Texas Instruments', '74LVC1G17GW,125': 'Nexperia',
       'ESP32-S3-WROOM-1-N16R8': 'Espressif', 'TF-015': 'SOFNG', 'WS2812B-2020-V6': 'Worldsemi',
       'TYPE-C-31-M-12': 'Korean Hroparts Elec', 'ESD5Z5.0T1G': 'onsemi', 'CP2102N-A02-GQFN28R': 'Silicon Labs',
       'UMH3N': 'Jiangsu Changjing (JSCJ)', 'AO3401A': 'Alpha & Omega Semiconductor',
       'SS34': 'MDD (Microdiode Semiconductor)', 'AP63203WU-7': 'Diodes Incorporated',
       'AP63205WU-7': 'Diodes Incorporated', 'SWPA4030S6R8MT': 'Sunlord', 'SWPA4030S4R7MT': 'Sunlord',
       'AP2112K-3.3TRG1': 'Diodes Incorporated', '1206L035/30WR': 'Littelfuse', 'RC0603FR-072R2L': 'YAGEO'}
for _v in RES.values():
    MFR.setdefault(_v[0], 'UNI-ROYAL')


class Part:
    def __init__(self, prefix, lib_id, value, footprint, pins, sheet,
                 mpn='', lcsc='', desc='', bom=True, dnp=False, ds='', key=None):
        self.prefix, self.lib_id, self.value, self.footprint = prefix, lib_id, value, footprint
        self.pins = {str(k): v for k, v in pins.items()}  # pad number -> net (None = NC)
        self.sheet, self.mpn, self.lcsc, self.desc, self.bom, self.dnp = sheet, mpn, lcsc, desc, bom, dnp
        self.mfr = MFR.get(mpn, '')
        self.nc_pads = ()                                  # footprint pads the symbol has no pin for (NC on the part)
        self.ds = ds                                       # datasheet URL when the stock symbol's is another part's
        self.key = key      # stable name the drawing and layout scripts use (references: refs.lock)
        self.unit_sheets = {}                              # unit -> sheet, for a part drawn on several sheets
        self.pin_unit = {}                                 # pad -> unit (only with unit_sheets)
        self.ref = None

    def sheets(self):
        return sorted(set(self.unit_sheets.values()) | {self.sheet}, key=SHEET_ORDER.index)

    def pad_sheet(self, pad):
        """The sheet a pad's pin is drawn on."""
        if self.unit_sheets:
            return self.unit_sheets[self.pin_unit[str(pad)]]
        return self.sheet


PARTS = []
_sheet = None


def sheet(name):
    global _sheet
    _sheet = name


def add(*a, **k):
    p = Part(*a, sheet=_sheet, **k)
    PARTS.append(p)
    return p


def R(value, a, b, desc='', **k):
    mpn, lcsc = RES[value]
    return add('R', 'Device:R', value, R0603, {1: a, 2: b}, mpn=mpn, lcsc=lcsc, desc=desc, **k)


def C(value, a, b='GND', desc='', **k):
    fp, mpn, lcsc = CAP[value]
    return add('C', 'Device:C', value, fp, {1: a, 2: b}, mpn=mpn, lcsc=lcsc, desc=desc, **k)


def RN(value, nets, common, desc='', **k):
    """4-resistor array: nets[0..3] on pins 1-4, common on 5-8 (R_Pack04: Rn.1 = pin n, Rn.2 = pin 9-n)."""
    mpn, lcsc = RPACK[value]
    pins = {i + 1: n for i, n in enumerate(nets)}
    pins.update({8 - i: common for i in range(4)})
    # one symbol unit per resistor (R_Pack04_Split: unit k = pins k and 9-k), drawn inline on its line
    return add('RN', 'Device:R_Pack04_Split', value, FP('R_Array_Convex_4x0603'), pins, mpn=mpn, lcsc=lcsc, desc=desc, **k)


def SW(value, net, desc, **k):
    # XKB TS-1187A-B-A-B (JLCPCB basic C318884), as FujiNet-7800 / SMS Rev0
    return add('SW', 'Switch:SW_Push', value, FP('SW_SPST_TS-1187A'), {1: net, 2: 'GND'},
               mpn='TS-1187A-B-A-B', lcsc='C318884', desc=desc, **k)


def TP(net, label, desc='test pad', **k):
    return add('TP', 'Connector:TestPoint', label, FP('TestPoint_Pad_D1.5mm'), {1: net},
               desc=desc, bom=False, **k)


def NFET(gate, source, drain, desc, **k):
    """2N7002 (JSCJ, SOT-23: 1 G, 2 S, 3 D -- datasheet p.1, as FujiNet-SMS Rev0)."""
    return add('Q', 'Transistor_FET:2N7002', '2N7002', FP('SOT-23'), {1: gate, 2: source, 3: drain},
               mpn='2N7002', lcsc='C8545', desc=desc, **k)


def JUMPER(a, b, value, desc, **k):
    """Bridged solder jumper (a copper link between the pads; cut it to open)."""
    return add('JP', 'Jumper:SolderJumper_2_Bridged', value, FP('SolderJumper-2_P1.3mm_Bridged_RoundedPad1.0x1.5mm'),
               {1: a, 2: b}, desc=desc, bom=False, **k)


# 14-pin gate packages: unit -> (input pins, output pin); 7 GND, 14 VCC.
GATE_PINS = {
    '74HCT14': [((1,), 2), ((3,), 4), ((5,), 6), ((9,), 8), ((11,), 10), ((13,), 12)],
    '74HCT08': [((1, 2), 3), ((4, 5), 6), ((9, 10), 8), ((12, 13), 11)],
}
GATE_PARTS = {  # value -> (lib_id, MPN, LCSC, datasheet); the '14 / '08 use the HC / LS symbols
    '74HCT14': ('74xx:74HC14', 'SN74HCT14DR', 'C6769', 'https://www.ti.com/lit/ds/symlink/sn74hct14.pdf'),
    # JLCPCB stocks it (C6767, 1797 on 2026-10-08, read from JLCPCB's own parts search: the
    # jlcsearch index the first Rev0 note relied on misses every 74HCT08)
    '74HCT08': ('74xx:74LS08', 'SN74HCT08DR', 'C6767', 'https://www.ti.com/lit/ds/symlink/sn74hct08.pdf'),
}


def GATES(value, gates, desc, **k):
    """A 14-pin gate package: gates = [(inputs..., output)] in unit order; an unused gate is
    (GND, ..., NC)."""
    lib_id, mpn, lcsc, ds = GATE_PARTS[value]
    pins = {7: 'GND', 14: '+5V'}
    for g, (ins, out) in zip(gates, GATE_PINS[value]):
        assert len(g) == len(ins) + 1, (value, g)
        pins.update({p: n for p, n in zip(ins, g[:-1])})
        pins[out] = g[-1]
    return add('U', lib_id, value, SOIC14, pins, mpn=mpn, lcsc=lcsc, desc=desc, ds=ds, **k)


# =========================================================================
# Declared sheet by sheet (SHEETS order).  References come from tools/refs.lock (geographic,
# from the frozen placement: tools/annotate.py); the drawing and the layout address parts by key.
sheet('cart-bus')
add('J', '%s:Atari5200_Cart_Edge_36' % LIB, 'Atari5200_Cart_Edge_36', FP('Atari5200_Cart_Edge_36'),
    {k: v[0] for k, v in EDGE.items()}, desc='Atari 5200 36-pin cartridge edge, 18 positions at 2.54 mm '
    'per face; pins 18 / 36 short (interlock, last-make)', bom=False, key='J_EDGE')

# -- the RP2354B (two units: GPIO here, the core on rp-core).  Every RP supply pin on +3V3_RP, the
# LDO off the 5 V rail, so the pads are powered whenever the cart is (its 5 V-tolerant pads need
# IOVDD up, RP2350 datasheet Table 1436).
rp = {30: 'XIN', 31: 'XOUT', 33: 'SWCLK', 34: 'SWDIO', 35: 'RUN',
      59: RP_IO_RAIL,                                                        # ADC_AVDD
      61: 'VREG_AVDD', 62: 'GND', 63: 'RP_LX', 64: RP_CORE_RAIL, 65: 'DVDD',   # VREG: AVDD PGND LX VIN FB
      66: 'RP_USB_DM', 67: 'RP_USB_DP', 68: RP_IO_RAIL, 69: RP_IO_RAIL,        # USB, USB_OTP_VDD, QSPI_IOVDD
      70: NC, 71: NC, 72: NC, 73: NC, 74: NC,                                 # QSPI (flash in package)
      75: 'QSPI_SS', 81: 'GND'}
rp.update({p: RP_IO_RAIL for p in RP_IOVDD_PINS})
rp.update({p: 'DVDD' for p in RP_DVDD_PINS})
for g, pin in RP_GPIO_PIN.items():
    rp[pin] = RP_GPIO_NET[g]
U_RP = add('U', '%s:RP2354B_Split' % LIB, 'RP2354B', FP('QFN-80-1EP_10x10mm_P0.4mm_EP3.4x3.4mm'), rp,
           mpn='RP2354B', lcsc='C39843328', desc='RP2350B + 2MB flash in package; cart bus server', key='U_RP')
# drawn in two units: A = the 48 GPIOs on the cart-bus sheet, B = supplies, core regulator,
# crystal, RUN, SWD, USB and QSPI on rp-core (gen_sch.rp_split_symbol)
U_RP.unit_sheets = {1: 'cart-bus', 2: 'rp-core'}
U_RP.pin_unit = {str(pad): 1 if pad in RP_GPIO_PIN.values() else 2 for pad in rp}

# -- the data path: the RP puts each byte on GPIO16-23, a 74HCT541 that only the enables open puts
# it on D0-D7 (a52_cart.h: software is never between an enable and the data).  Its eight channels
# are identical, so they are used in reverse (bit k on channel 8-k: A8 / Y8 carry D0): turned 270
# degrees over the D0-D7 fingers, the '541's Y row (pins 11-18) then meets the fingers in their own
# left-to-right order and its A row (pins 9-2) the RP2354B's GPIO16-23 corner in theirs -- the data
# path from the slot to the RP crosses nothing (gen_pcb.buf_fanin draws the finger side).
buf = {1: 'SERVE_N', 19: 'EN_ANY_N', 10: 'GND', 20: '+5V'}     # /OE1, /OE2 (equivalent: drive = !OE1 & !OE2)
buf.update({9 - i: 'RP_D%d' % i for i in range(8)})             # A8..A1 (pins 9..2) = bit 0..7
buf.update({11 + i: 'D%d' % i for i in range(8)})              # Y8..Y1 (pins 11..18) = D0..D7
add('U', '74xx:74HCT541', '74HCT541', FP('TSSOP-20_4.4x6.5mm_P0.65mm'), buf, mpn='SN74HCT541PWR',
    lcsc='C436096', desc="D0-D7 driver: drives only while /OE1 (served) and /OE2 (either enable) are low",
    key='U_BUF', ds='https://www.ti.com/lit/ds/symlink/sn74hct541.pdf')
C('100nF', '+5V', desc="74HCT541 VCC decoupling", key='C_BUF')
# -- the glue (a52_cart.h a52_glue_drive(); tools/check_glue.py evaluates this netlist against it for
# every input):
#   SERVE_N  = !(PWR_OK & BUF_EN)     the '541's /OE1
#   EN_ANY_N = /EN40 & /EN80          the '541's /OE2: one gate from the enables
# (the '541 drives while both are low, so the two are interchangeable: this way round the cart-bus
# sheet draws the glue without a crossing)
GATES('74HCT08', [('EN40_N', 'EN80_N', 'EN_ANY_N'), ('BUF_EN', 'PWR_OK', 'SERVE'),
                  ('GND', 'GND', NC), ('GND', 'GND', NC)],
      desc="EN_ANY_N = /EN40 & /EN80; SERVE = PWR_OK & BUF_EN", key='U_AND')
C('100nF', '+5V', desc="74HCT08 VCC decoupling", key='C_AND')
GATES('74HCT14', [('VSENSE', 'PWR_OK_N'), ('PWR_OK_N', 'PWR_OK'), ('SERVE', 'SERVE_N'),
                  ('GND', NC), ('GND', NC), ('GND', NC)],
      desc="PWR_OK from the console 5V sense; SERVE inversion", key='U_INV')
C('100nF', '+5V', desc="74HCT14 VCC decoupling", key='C_INV')
C('10uF', '+5V', desc='5V logic domain bulk', key='C_GLUEBULK')
# -- console power sense: edge pin 26 (VR1, before the P-FET) -> 22k / 100k (0.82 x) -> the '14
# Schmitt (TTL thresholds: VT+ 1.2-1.9 V at VCC 4.5 V, TI SCLS225G 6.5): a console-present sense,
# as FujiNet-SMS Rev0.
R('22k', 'CONS_5V', 'VSENSE', desc='console 5V sense divider', key='R_VSH')
R('100k', 'VSENSE', 'GND', desc='console 5V sense -> 0.82 x CONS_5V', key='R_VSL')
# -- BUF_EN is defined before the firmware runs: RP2350-E9 can leave an input-enabled pad at ~2.2 V,
# over the 74HCT VIH of 2.0 V; "8.2 kOhm or less" holds it low, and the '541 off.
R('4.7k', 'BUF_EN', 'GND', desc="BUF_EN low until the firmware drives it (RP2350-E9: <= 8.2k)", key='R_PDBUF')
# -- PHI2 (edge 14): GND on CA018087; on the universal boards PHI2 through a 74LS125 and CR9 (1N914,
# anode at pin 14), so the console only pulls it low, to VOL(LS125) + VF(1N914) <= ~1.15 V: over the
# RP2350's VIL of 0.8 V (Table 1436).  A 74LVC1G17 Schmitt on +5V reads it (VT- >= 1.32 V at VCC
# 4.5 V, Nexperia 74LVC1G17 Table 8) and drives GPIO25 (5 V tolerant).  The pull-up comes from the
# console's own 5 V, so nothing is pushed into an unpowered console; 4.7k reaches VT+ in ~60 ns.
R('4.7k', 'CONS_5V', 'PHI2', desc='PHI2 pull-up (the console drives pin 14 only low, through a diode)',
  key='R_PHI2PU')
add('U', '74xGxx:74LVC1G17', '74LVC1G17', FP('SOT-353_SC-70-5'), {1: NC, 2: 'PHI2', 3: 'GND', 4: 'PHI2_RP',
    5: '+5V'}, mpn='74LVC1G17GW,125', lcsc='C426705', desc='PHI2 Schmitt buffer: CMOS thresholds for the '
    'diode-isolated clock', key='U_PHI2', ds='https://assets.nexperia.com/documents/data-sheet/74LVC1G17.pdf')
C('100nF', '+5V', desc='74LVC1G17 VCC decoupling', key='C_PHI2')
# -- the interlock, edge 18 (CI1) / 36 (CI2): the jumper of every stock cart closes the base circuit
# of Q6, the switch in front of VR1 (pin 26, console RAM, reset).  ~34 mA (61 mA on CA020108) flows
# through it at ~0.2 V (Q8 pulls CI1 low); open, CI2 sits at the raw DC through 4.7k + 330R.
JUMPER('ILK_A', 'ILK_B', 'ILK', 'interlock 18-36, closed as on a stock cart (cut to hand it to Q_ILK)',
       key='JP_ILK')
# DNP: a firmware-controlled interlock (a console power cycle = its only reset).  The jumper sits at
# ground potential when closed, so the switch is an N-FET on the low side: D on CI2 (pin 36), S on CI1
# (pin 18), gate pulled up to +5V (closed whenever the cart has power); GPIO28 high turns Q_ILKDRV on
# and opens it.  Needs the cart powered from USB or the edge's raw DC once JP_ILK is cut.
NFET('ILK_G', 'ILK_A', 'ILK_B', 'interlock switch (DNP): D = CI2 (pin 36), S = CI1 (pin 18)', dnp=True,
     key='Q_ILK')
R('10k', '+5V', 'ILK_G', desc='interlock switch closed by default (DNP)', dnp=True, key='R_ILKG')
NFET('ILK', 'GND', 'ILK_G', 'interlock switch driver, G = GPIO28: high opens the interlock (DNP)', dnp=True,
     key='Q_ILKDRV')
R('4.7k', 'ILK', 'GND', desc='GPIO28 low until the firmware drives it (RP2350-E9: <= 8.2k; DNP)', dnp=True,
  key='R_ILKPD')
# -- VR1 (the console 5 V that feeds the cart) for the ADC (GPIO40, not 5 V tolerant): 100k / 100k =
# 0.5 x, 5.5 V reads 2.75 V; 100 nF for the ADC's sample capacitor
R('100k', 'CONS_5V', 'VSENSE_ADC', desc='console 5V -> ADC divider (0.5 x)', key='R_ADCH')
R('100k', 'VSENSE_ADC', 'GND', desc='console 5V -> ADC divider', key='R_ADCL')
C('100nF', 'VSENSE_ADC', desc='ADC sample reservoir', key='C_ADCF')
# -- activity LED straight off GPIO27 (3.3 V): red, ~1.3 mA
R('1k', 'RP_LED', 'RP_LED_A', desc='activity LED series', key='R_LED')
add('D', 'Device:LED', 'red', FP('LED_0603_1608Metric'), {1: 'GND', 2: 'RP_LED_A'},
    mpn='KT-0603R', lcsc='C2286', desc='activity LED (GPIO27)', key='D_LED')
# -- debug UART (GPIO44 TX, GPIO45 RX; 3.3 V only), DNP: fit for bring-up
add('J', 'Connector_Generic:Conn_01x03', 'DBG UART', FP('PinHeader_1x03_P2.54mm_Vertical'),
    {1: 'DBG_TX', 2: 'DBG_RX', 3: 'GND'}, mpn='PZ254V-11-03P', lcsc='C2937625',
    desc='RP debug UART, 3.3 V: 1 TX (GPIO44), 2 RX (GPIO45), 3 GND; fit for bring-up', dnp=True, key='J_DBG')
# -- bring-up pads: the enables, PHI2 and the '541's two enables, PWR_OK, with a scope ground
TP('EN40_N', '/EN40', desc='scope pad: console /Enable $40-$7F', key='TP_EN40')
TP('EN80_N', '/EN80', desc='scope pad: console /Enable $80-$BF', key='TP_EN80')
TP('PHI2', 'PHI2', desc='scope pad: edge 14 (PHI2 on the universal boards, GND on CA018087)', key='TP_PHI2')
TP('SERVE_N', '/OE1', desc="scope pad: '541 /OE1 (PWR_OK & BUF_EN)", key='TP_OE1')
TP('EN_ANY_N', '/OE2', desc="scope pad: '541 /OE2 (either enable)", key='TP_OE2')
TP('PWR_OK', 'PWR_OK', desc='scope pad: console power sense', key='TP_PWROK')
TP('GND', 'GND', desc='scope ground by the bus pads', key='TP_GNDBUS')

# =========================================================================
sheet('rp-core')
for pin in RP_IOVDD_PINS:      # one 100 nF per IOVDD pin; the key names the pin it sits on
    C('100nF', RP_IO_RAIL, desc='IOVDD decoupling', key='C_IOV%d' % pin)
C('100nF', RP_IO_RAIL, desc='QSPI_IOVDD decoupling', key='C_QSPI')
C('100nF', RP_IO_RAIL, desc='USB_OTP_VDD decoupling', key='C_OTP')
C('100nF', RP_IO_RAIL, desc='ADC_AVDD decoupling', key='C_ADC')
C('10uF', RP_IO_RAIL, desc='RP IO rail bulk (LDO output)', key='C_IOBULK')
C('4.7uF', RP_CORE_RAIL, desc='VREG_VIN bulk (LDO rail)', key='C_VREGIN')
for pin in RP_DVDD_PINS:
    C('100nF', 'DVDD', desc='DVDD decoupling', key='C_DV%d' % pin)
C('4.7uF', 'DVDD', desc='core regulator output', key='C_DVBULK')
R('33R', RP_CORE_RAIL, 'VREG_AVDD', desc='VREG_AVDD filter', key='R_AVDD')
C('4.7uF', 'VREG_AVDD', desc='VREG_AVDD filter', key='C_AVDD')
add('L', 'Device:L', '3.3uH', FP('RPI_L_AOTA-B201610S3R3'), {1: 'DVDD', 2: 'RP_LX'},
    mpn='AOTA-B201610S3R3-101-T', lcsc='C42411119', desc='RP2350 core SMPS inductor', key='L_RP')
add('Y', 'Device:Crystal_GND24', '12MHz', FP('Crystal_SMD_3225-4Pin_3.2x2.5mm'),
    {1: 'XIN', 2: 'GND', 3: 'XOUT_Y', 4: 'GND'}, mpn='ABM8-272-T3', lcsc='C20625731', desc='RP2350 12 MHz crystal',
    key='Y_RP')
C('15pF', 'XIN', desc='crystal load', key='C_XIN')
C('15pF', 'XOUT_Y', desc='crystal load', key='C_XOUT')
R('1k', 'XOUT', 'XOUT_Y', desc='crystal drive limit', key='R_XOUT')
SW('RESET', 'RST_BTN', 'cart RESET: RP RUN + S3 EN via BAT54C', key='SW_RESET')
add('D', 'Diode:BAT54C', 'BAT54C', FP('SOT-23'), {1: 'RUN', 2: 'S3_EN', 3: 'RST_BTN'},
    mpn='BAT54C,215', lcsc='C37704', desc='RESET steering, common cathode', key='D_RST')
# RUN / BOOTSEL: the S3 drives them low to assert (fnPicoUpdater::forceBootselViaPins)
R('10k', RP_IO_RAIL, 'RUN', desc='RUN pull-up', key='R_RUN')
R('10k', RP_IO_RAIL, 'QSPI_SS', desc='QSPI_SS pull-up', key='R_SS')
R('1k', 'QSPI_SS', 'BOOTSEL_BTN', desc='BOOTSEL button series', key='R_BSEL')
SW('BOOTSEL', 'BOOTSEL_BTN', 'RP2354 BOOTSEL (hold while pressing RESET)', key='SW_BOOTSEL')
R('1k', 'RUN_CTL', 'RUN', desc='S3 IO4 -> RP RUN (drive low = reset)', key='R_RUNCTL')
R('1k', 'BOOTSEL_CTL', 'QSPI_SS', desc='S3 IO5 -> RP QSPI_SS (low through reset = BOOTSEL)', key='R_BSELCTL')
R('27R', 'USB_DP', 'RP_USB_DP', desc='USB series', key='R_USBP')
R('27R', 'USB_DM', 'RP_USB_DM', desc='USB series', key='R_USBM')
TP('SWCLK', 'SWCLK', key='TP_SWCLK')
TP('SWDIO', 'SWDIO', key='TP_SWDIO')
TP('GND', 'GND', key='TP_GND')
TP('RUN', 'RUN', key='TP_RUN')
TP('DVDD', 'DVDD', desc='bring-up pad: RP core rail', key='TP_DVDD')

# =========================================================================
# The FujiNet half: the NES / SMS / 7800 Rev0 circuits.
sheet('fujinet')
s3 = {}
for fn, pad in S3_PAD.items():
    for p in (pad if isinstance(pad, list) else [pad]):
        s3[p] = 'GND' if fn == 'GND' else '+3V3' if fn == '3V3' else S3_NET.get(fn, NC)
add('U', '%s:ESP32-S3-WROOM-1_Fn' % LIB, 'ESP32-S3-WROOM-1-N16R8', FP('ESP32-S3-WROOM-1'), s3,
    mpn='ESP32-S3-WROOM-1-N16R8', lcsc='C2913202', desc='FujiNet core (fujiversal-atari5200)', key='U_S3')
C('22uF', '+3V3', desc='S3 bulk (WiFi TX bursts)', key='C_S3BULK')
C('100nF', '+3V3', desc='S3 decoupling', key='C_S3')
R('10k', '+3V3', 'S3_EN', desc='EN pull-up', key='R_EN')
C('1uF', 'S3_EN', desc='EN power-on delay', key='C_EN')
SW('S3_RST', 'S3_EN', 'ESP32-S3 EN', key='SW_S3EN')
SW('S3_BOOT', 'S3_IO0', 'ESP32-S3 BOOT (IO0)', key='SW_S3BOOT')
add('J', '%s:MicroSD_TF015' % LIB, 'microSD', FP('TF-SMD_TF-015'),
    {1: 'SD_DAT2', 2: 'SD_CS', 3: 'SD_MOSI', 4: '+3V3', 5: 'SD_SCK', 6: 'GND',
     7: 'SD_MISO', 8: 'SD_DAT1', 9: 'SD_CD', 10: 'GND', 11: 'GND', 12: 'GND', 13: 'GND'},
    mpn='TF-015', lcsc='C113206', desc='microSD push-push, SPI mode', key='J_SD')
RN('4x10k', ['SD_CS', 'SD_MISO', 'SD_DAT1', 'SD_DAT2'], '+3V3', desc='SD pull-ups', key='RN_SD')
R('10k', '+3V3', 'SD_CD', desc='card-detect pull-up', key='R_SDCD')
C('10uF', '+3V3', desc='microSD supply', key='C_SD')
R('330R', 'LED_STRIP', 'WS_DIN', desc='WS2812 data series', key='R_WS')
# WS2812B-2020-V6 (JLCPCB C52917434, 652k on 2026-10-08; the WS2812C-2020-V1 of FujiNet-7800 / SMS
# Rev0 is at 0): same 2.0 x 2.0 package and land, same pins (1 DO, 2 GND, 3 DI, 4 VDD), VDD
# 3.7-5.3 V, VIH 2.7 V at VDD 5 V (datasheet p.2-3), 12 mA per channel.
add('D', 'LED:WS2812B-2020', 'WS2812B-2020-V6', FP('LED_WS2812B-2020_PLCC4_2.0x2.0mm'),
    {1: NC, 2: 'GND', 3: 'WS_DIN', 4: '+5V'}, mpn='WS2812B-2020-V6', lcsc='C52917434',
    desc='status LED on +5V (datasheet VDD 3.7-5.3 V; VIH 2.7 V takes the S3 3.3 V data directly)', key='D_WS')
C('100nF', '+5V', desc='WS2812 decoupling', key='C_WS')

# =========================================================================
sheet('usb')
add('J', '%s:USB_C_USB2.0_16P_Fn' % LIB, 'USB-C', FP('USB_C_Receptacle_HRO_TYPE-C-31-M-12'),
    {'A1': 'GND', 'A4': 'VBUS', 'A5': 'CC1', 'A6': 'UBRG_DP', 'A7': 'UBRG_DM', 'A8': NC,
     'A9': 'VBUS', 'A12': 'GND', 'B1': 'GND', 'B4': 'VBUS', 'B5': 'CC2', 'B6': 'UBRG_DP',
     'B7': 'UBRG_DM', 'B8': NC, 'B9': 'VBUS', 'B12': 'GND', 'SH': 'GND'},
    mpn='TYPE-C-31-M-12', lcsc='C165948', desc='power + S3 programming', key='J_USB')
R('5.1k', 'CC1', 'GND', desc='UFP Rd', key='R_CC1')
R('5.1k', 'CC2', 'GND', desc='UFP Rd', key='R_CC2')
for n, k in (('UBRG_DP', 'D_ESDP'), ('UBRG_DM', 'D_ESDM'), ('VBUS', 'D_ESDV')):
    add('D', 'Diode:ESD5Zxx', 'ESD5Z5.0T1G', FP('D_SOD-523'), {1: n, 2: 'GND'},
        mpn='ESD5Z5.0T1G', lcsc='C82044', desc='ESD', key=k)
C('1uF', 'VBUS', desc='VBUS decoupling at the connector', key='C_VBUS')
C('100nF', 'VBUS', desc='VBUS HF decoupling at the connector', key='C_VBUSHF')
cp = {i: NC for i in range(1, 30)}
cp.update({3: 'GND', 4: 'UBRG_DP', 5: 'UBRG_DM', 6: '+3V3', 7: '+3V3', 8: 'VBUS_SNS',
           9: 'CP_RST', 23: 'GND', 24: 'UART_RTS', 25: 'S3_TXD', 26: 'S3_RXD',
           28: 'UART_DTR', 29: 'GND'})
add('U', 'Interface_USB:CP2102N-Axx-xQFN28', 'CP2102N-A02-GQFN28', FP('QFN-28-1EP_5x5mm_P0.5mm_EP3.35x3.35mm'),
    cp, mpn='CP2102N-A02-GQFN28R', lcsc='C964632', desc='USB-UART for S3 flashing/console (self-powered)',
    key='U_UART')
C('100nF', '+3V3', desc='CP2102N VDD', key='C_UART')
C('4.7uF', '+3V3', desc='CP2102N VDD bulk', key='C_UARTBULK')
R('22k', 'VBUS', 'VBUS_SNS', desc='VBUS sense divider', key='R_VBSH')
R('47k', 'VBUS_SNS', 'GND', desc='VBUS sense divider', key='R_VBSL')
R('10k', '+3V3', 'CP_RST', desc='/RST pull-up', key='R_CPRST')
add('U', 'Transistor_BJT:UMH3N', 'UMH3N', FP('SOT-363_SC-70-6'),
    {1: 'UART_RTS', 2: 'UART_DTR', 6: 'S3_EN', 3: 'S3_IO0', 4: 'UART_DTR', 5: 'UART_RTS'},
    mpn='UMH3N', lcsc='C62892', desc='esptool auto-program (DevKitC-1 style)', key='U_AUTOPROG')

# =========================================================================
sheet('power')
# +5V (RP LDO, the glue, the WS2812, the 3.3 V buck) is the OR of three sources:
#   CONS_5V  edge 26, VR1 -- through Q_CONS, a P-FET (D = CONS_5V, S = +5V), on unless its gate
#            (CONS_OFF) is high: nothing is ever pushed back into the console's 5 V
#   VBUS     USB-C, through an SS34
#   PRE5V    edge 11, the adapter's raw DC on the universal boards, through a fuse and a 5 V buck
#            and an SS34.  VR1 is a 78M05 (0.5 A) on CA018087 that also feeds the console's RAM and
#            controllers; where the raw DC is there, the cart takes nothing from VR1, and it is
#            running before the console is switched on (pin 11 is ahead of the power switch).
# CONS_OFF = VBUS | PRE5V (BAT54C): either one turns the console path off.
add('Q', 'Transistor_FET:AO3401A', 'AO3401A', FP('SOT-23'), {1: 'CONS_OFF', 2: '+5V', 3: 'CONS_5V'},
    mpn='AO3401A', lcsc='C15127', desc='console 5V switch: G = CONS_OFF, S = +5V, D = CONS_5V; body diode '
    'CONS_5V -> +5V', key='Q_CONS')
add('D', 'Diode:BAT54C', 'BAT54C', FP('SOT-23'), {1: 'VBUS', 2: 'PRE5V', 3: 'CONS_OFF'},
    mpn='BAT54C,215', lcsc='C37704', desc='CONS_OFF = VBUS OR PRE5V (common cathode)', key='D_OFF')
R('100k', 'CONS_OFF', 'GND', desc='console path on by default', key='R_OFFPD')
add('D', 'Diode:SS34', 'SS34', FP('D_SMA'), {1: '+5V', 2: 'VBUS'}, mpn='SS34', lcsc='C8678',
    desc='USB VBUS OR-ing (no back-feed into the console or the host)', key='D_VBUS')
# The SS34s are reverse-biased by +5V whenever another source runs the cart, and their leakage (IR
# 0.5 mA at 25 C, 20 mA at 100 C, datasheet p.2) flows into VBUS / PRE5V -- the anodes of the gate
# OR.  4.7k each holds them under ~2.4 V at 500 uA, so the console path stays on (FujiNet-SMS Rev0
# R3, tools/audit/spice_checks.py).
R('4.7k', 'VBUS', 'GND', desc='VBUS pull-down against the SS34 reverse leakage', key='R_VBPD')
# The console's VR1 feeds the cart where there is no raw DC: bulk at the edge
C('10uF', 'CONS_5V', desc='edge 5V bulk', key='C_CONS')
C('100nF', 'CONS_5V', desc='edge 5V HF bypass', key='C_CONSHF')
# -- edge 11: the raw DC.  A bridged jumper (cut it to take nothing from pin 11), a 0.35 A PTC so a
# fault on the cart never loads the adapter, 2.2R against the inrush into the buck's input when the
# cart goes in with the adapter live, the AP63205 (3.8-32 V in, 5 V 2 A), an SS34 onto +5V.
JUMPER('UNREG', 'UNREG_J', 'RAWDC', 'edge 11 raw DC input, closed (cut to take nothing from pin 11)',
       key='JP_UNREG')
add('F', 'Device:Polyfuse', '0.35A', FP('Fuse_1206_3216Metric'), {1: 'UNREG_J', 2: 'UNREG_F'},
    mpn='1206L035/30WR', lcsc='C2153989', desc='PTC 0.35 A hold, 30 V: the adapter is never loaded by a cart fault',
    key='F_UNREG')
R('2.2R', 'UNREG_F', 'PRE_VIN', desc='inrush limit into the buck input', key='R_UNREG')
C('22uF', 'PRE_VIN', desc='raw DC buck input (25 V)', key='C_PREIN1')
C('22uF', 'PRE_VIN', desc='raw DC buck input (25 V)', key='C_PREIN2')
C('100nF', 'PRE_VIN', desc='raw DC buck input HF (50 V)', key='C_PREINHF')
add('U', 'Regulator_Switching:AP63205WU', 'AP63205WU', FP('TSOT-23-6'),
    {1: 'PRE5V', 2: 'PRE_VIN', 3: 'PRE_VIN', 4: 'GND', 5: 'PRE_SW', 6: 'PRE_BST'},
    mpn='AP63205WU-7', lcsc='C2071056', desc='edge raw DC (9-13 V) -> 5 V, 2 A buck', key='U_PRE')
C('100nF', 'PRE_SW', 'PRE_BST', desc='bootstrap', key='C_PREBST')
add('L', 'Device:L', '4.7uH', FP('L_Sunlord_SWPA4030S'), {1: 'PRE_SW', 2: 'PRE5V'},
    mpn='SWPA4030S4R7MT', lcsc='C57269', desc='raw DC buck inductor (datasheet Table 3: 4.7 uH at 5 V)',
    key='L_PRE')
C('22uF', 'PRE5V', desc='raw DC buck output', key='C_PREOUT1')
C('22uF', 'PRE5V', desc='raw DC buck output', key='C_PREOUT2')
add('D', 'Diode:SS34', 'SS34', FP('D_SMA'), {1: '+5V', 2: 'PRE5V'}, mpn='SS34', lcsc='C8678',
    desc='raw DC buck OR-ing onto +5V', key='D_PRE')
R('4.7k', 'PRE5V', 'GND', desc='PRE5V pull-down against the SS34 reverse leakage', key='R_PREPD')
# -- +5V bulk and the 3.3 V buck (S3, microSD, CP2102N)
C('22uF', '+5V', desc='buck input', key='C_BIN1')
C('22uF', '+5V', desc='buck input', key='C_BIN2')
C('22uF', '+5V', desc='+5V bulk', key='C_5VBULK')
C('100nF', '+5V', desc='buck input HF', key='C_BINHF')
add('U', 'Regulator_Switching:AP63203WU', 'AP63203WU', FP('TSOT-23-6'),
    {1: '+3V3', 2: '+5V', 3: '+5V', 4: 'GND', 5: 'BUCK_SW', 6: 'BUCK_BST'},
    mpn='AP63203WU-7', lcsc='C780769', desc='3.3V 2A buck', key='U_BUCK')
C('100nF', 'BUCK_SW', 'BUCK_BST', desc='bootstrap', key='C_BST')
add('L', 'Device:L', '6.8uH', FP('L_Sunlord_SWPA4030S'), {1: 'BUCK_SW', 2: '+3V3'},
    mpn='SWPA4030S6R8MT', lcsc='C62684', desc='buck inductor', key='L_BUCK')
C('22uF', '+3V3', desc='buck output', key='C_BOUT1')
C('22uF', '+3V3', desc='buck output', key='C_BOUT2')
# RP rail: a fast LDO straight off the 5 V rail, so IOVDD tracks the cart rail as it rises.
add('U', 'Regulator_Linear:AP2112K-3.3', 'AP2112K-3.3', FP('SOT-23-5'),
    {1: '+5V', 2: 'GND', 3: '+5V', 4: NC, 5: RP_IO_RAIL},
    mpn='AP2112K-3.3TRG1', lcsc='C51118', desc='RP2354B 3.3V LDO (IOVDD, VREG_VIN, VREG_AVDD), 600mA, fast start',
    key='U_LDO')
C('1uF', '+5V', desc='LDO input', key='C_LDOIN')
C('1uF', RP_IO_RAIL, desc='LDO output', key='C_LDOOUT')
# bring-up pads on every rail and source
TP('CONS_5V', 'CONS_5V', desc='bring-up pad: console 5V (edge 26)', key='TP_CONS5V')
TP('UNREG_F', 'RAWDC', desc='bring-up pad: edge 11 raw DC behind the PTC', key='TP_UNREG')
TP('PRE5V', 'PRE5V', desc='bring-up pad: raw DC buck output', key='TP_PRE5V')
TP('+5V', '+5V', desc='bring-up pad: +5V', key='TP_5V')
TP('+3V3', '+3V3', desc='bring-up pad: +3V3', key='TP_3V3')
TP(RP_IO_RAIL, '+3V3_RP', desc='bring-up pad: +3V3_RP', key='TP_3V3RP')

# PWR_FLAGs: nets whose drivers are passive pins
PWR_FLAG_NETS = ['GND', 'CONS_5V', 'VBUS', '+5V', '+3V3', 'DVDD', 'VREG_AVDD', 'PRE_VIN', 'PRE5V']
# nets drawn as power symbols (global, never prefixed): the board's planes and islands
RAIL_NETS = ['GND', 'CONS_5V', 'VBUS', '+5V', '+3V3', '+3V3_RP', 'DVDD']

# ---- references: tools/refs.lock (geographic, written by tools/annotate.py from the frozen
# placement); a part not in it yet gets the next free number of its prefix, in declaration order
import json as _json, os as _os
_LOCK = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), 'refs.lock')
_locked = _json.load(open(_LOCK)) if _os.path.exists(_LOCK) else {}
_used = {}
for p in PARTS:
    if p.key in _locked:
        p.ref = _locked[p.key]
        _used.setdefault(p.prefix, set()).add(int(p.ref[len(p.prefix):]))
for p in PARTS:
    if p.ref is None:
        n = 1
        while n in _used.setdefault(p.prefix, set()):
            n += 1
        _used[p.prefix].add(n)
        p.ref = '%s%d' % (p.prefix, n)
assert len({p.ref for p in PARTS}) == len(PARTS), 'duplicate reference in refs.lock'

BY_REF = {p.ref: p for p in PARTS}
KEY = {p.key: p.ref for p in PARTS if p.key}
assert len(KEY) == len(PARTS), 'every part needs a unique key: %s' % sorted(
    p.ref for p in PARTS if not p.key)
BY_KEY = {p.key: p for p in PARTS}
assert [p.sheet for p in PARTS] == sorted((p.sheet for p in PARTS), key=SHEET_ORDER.index), \
    'parts must be declared sheet by sheet in SHEETS order'
assert all(p.mfr for p in PARTS if p.bom), 'manufacturer missing: %s' % [p.mpn for p in PARTS if p.bom and not p.mfr]


def nets():
    out = {}
    for p in PARTS:
        for pad, n in p.pins.items():
            if n:
                out.setdefault(n, []).append((p.ref, pad))
    return out


def sheet_nets():
    """net -> the set of sheets it has pins on (a part drawn on several sheets counts each pin
    on the sheet of its unit)."""
    out = {}
    for p in PARTS:
        for pad, n in p.pins.items():
            if n:
                out.setdefault(n, set()).add(p.pad_sheet(pad))
    return out


if __name__ == '__main__':
    for p in PARTS:
        print(p.sheet, p.ref, p.key, p.value, p.footprint.split(':')[1], p.lcsc, 'DNP' if p.dnp else '')
    ns = nets()
    print(len(PARTS), 'parts', len(ns), 'nets')
    for n, pp in sorted(ns.items()):
        if len(pp) < 2:
            print('SINGLE-PIN NET', n, pp)
