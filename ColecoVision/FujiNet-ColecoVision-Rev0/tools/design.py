"""FujiNet-ColecoVision Rev0 (RP2350A + W25Q16 + ESP32-S3) -- the single source of truth.

Every part, value, footprint, MPN, LCSC code and pin->net assignment lives
here.  gen_sch.py, gen_pcb.py and export.py import it; the KiCad files are
generated output.  check_nets.py does NOT import it: it reads the netlist and
the firmware sources and checks one against the other.

Firmware contract (fujinet-firmware master, pico/coleco):
  pico/coleco/firmware/include/coleco_cart.h   GP0-14 = A0-A14 (ADDR_MASK 0x7FFF), GP15-22 = D0-D7
                                               (D0_PIN 15), GP26 /CE = the AND of /8000 /A000 /C000
                                               /E000 (CE_PIN), GP27 DIR, 1 = console -> cart (DIR_PIN),
                                               GP28 PWR, the console's 5 V through a divider (PWR_PIN),
                                               GP25 LED (PICO_DEFAULT_LED_PIN)
  pico/coleco/firmware/src/coleco_cart.c       core1 drives D0-D7 off the bare address, RAM and BIOS
                                               cycles included; the data buffer's /OE is the select
                                               itself, so a byte driven for another cycle goes nowhere
  pico/coleco/firmware/boards/fujicoleco.*     (a stock Pico today: README "Firmware changes")
  include/pinmap/fujiversal-coleco.h           S3 pins (SD, LED strip, UART0)
The RP2350A keeps that map exactly.  GPIO0-25 are 5 V tolerant on the QFN-60 (RP2350 datasheet:
"Digital IO (FT)"), so A0-A14 come straight from the edge through 330R; /CE, DIR and PWR (GP26-28,
the ADC pins, not 5 V tolerant) only ever see 3.3 V: the AND gates', the RP's own and the divider's.
The flash is a W25Q16JV beside it (the RP2354A, the same die with it in the package, was out of stock
at JLCPCB and LCSC on 2026-11-04).
Edge pinout: MAME bus/coleco/cartridge/exp.h = the Coleco ADAM Technical Reference Manual's J1, checked
against three built carts (tools/edge_geom.py has the sources; tools/audit/edge_orientation.py the
cross-check).

Circuit:
  * the bus side is what coleco_cart.h asks for: the four selects ANDed outside the RP (74LVC1G11 +
    74LVC1G08: no 74LVC21 is stocked), that /CE on GP26 and on the 74LVC245A's /OE; the '245 at
    3.3 V (5 V-tolerant inputs, as the header requires: not a 74HCT245) between the edge's D0-D7 (its
    A port) and GP15-22 (its B port), DIR from GP27 with a pull-up so it faces the RP through reset;
    the address lines into the RP through 330R as every FujiNet cart's 5 V bus does (it limits the
    current into a pad while IOVDD is still rising);
  * the RP2350A core and its regulator corner (Raspberry Pi's minimal design, MIT) are FujiNet-Arcadia
    Rev0's, plus the QSPI flash;
  * the ESP32-S3 half, the USB-C (USBLC6-2SC6, CP2102N with the datasheet's 1k RSTb pull-up) and the
    power mux (TPS2116: USB first, the console second) are FujiNet-ColecoVision / Arcadia / StudioII Rev0's.
"""

LIB = 'FujiNet-ColecoVision'
PROJECT = 'FujiNet-ColecoVision-Rev0'
NC = None  # explicit no-connect

SHEETS = [  # (file stem, title, page) -- in signal-flow order, console side first
    ('cart-bus', 'Cart bus: edge, select AND, data buffer, RP2350A GPIO', 2),
    ('rp-core', 'RP2350A core, QSPI flash, crystal, RUN, SWD', 3),
    ('fujinet', 'FujiNet (ESP32-S3), microSD', 4),
    ('usb', 'USB-C + CP2102N', 5),
    ('power', 'Power: mux, S3 buck, RP LDO', 6),
]
SHEET_ORDER = [s[0] for s in SHEETS]

# ---- RP2350A (QFN-60) -------------------------------------------------------
# GPIO -> package pin: RP2350 datasheet (QFN-60 column); gen_sch.py re-checks every entry against
# the KiCad symbol's pin names.
RP_GPIO_PIN = {0: 2, 1: 3, 2: 4, 3: 5, 4: 7, 5: 8, 6: 9, 7: 10, 8: 12, 9: 13, 10: 14, 11: 15,
               12: 16, 13: 17, 14: 18, 15: 19, 16: 27, 17: 28, 18: 29, 19: 31, 20: 32, 21: 33,
               22: 34, 23: 35, 24: 36, 25: 37, 26: 40, 27: 41, 28: 42, 29: 43}
RP_IOVDD_PINS = [1, 11, 20, 30, 38, 45]
RP_DVDD_PINS = [6, 23, 39]
RP_RAIL = '+3V3_RP'   # IOVDD x6, QSPI_IOVDD, USB_OTP_VDD, ADC_AVDD, VREG_VIN, (VREG_AVDD through 33R),
                      # the flash, the '245 and the two AND gates
S3_RAIL = '+3V3'      # the AP63203 buck: ESP32-S3, CP2102N, microSD

# coleco_cart.h: A0-A14 on GP0-14 (through 330R: RP_A*), D0-D7 on GP15-22 (the '245's B port: RP_D*)
RP_GPIO_NET = {i: 'RP_A%d' % i for i in range(15)}
RP_GPIO_NET.update({15 + i: 'RP_D%d' % i for i in range(8)})
RP_GPIO_NET.update({23: 'GP23', 24: 'DBG_TX', 25: 'RP_LED', 26: 'CART_CE_N', 27: 'BUF_DIR', 28: 'VSENSE',
                    29: 'SELFTEST'})
assert set(RP_GPIO_NET) == set(RP_GPIO_PIN)
# Only the FT pins may meet the 5 V bus: GPIO26-29 are the ADC pins (VPIN max IOVDD + 0.5 V)
assert all(g <= 25 for g, n in RP_GPIO_NET.items() if n and n[:4] in ('RP_A', 'RP_D'))

# ESP32-S3-WROOM-1 module pad -> function (pads per the KiCad symbol)
S3_PAD = {'GND': [1, 40, 41], '3V3': 2, 'EN': 3, 'IO4': 4, 'IO5': 5, 'IO6': 6,
          'IO7': 7, 'IO15': 8, 'IO16': 9, 'IO17': 10, 'IO18': 11, 'IO8': 12,
          'IO19': 13, 'IO20': 14, 'IO3': 15, 'IO46': 16, 'IO9': 17, 'IO10': 18,
          'IO11': 19, 'IO12': 20, 'IO13': 21, 'IO14': 22, 'IO21': 23,
          'IO47': 24, 'IO48': 25, 'IO45': 26, 'IO0': 27, 'IO35': 28,
          'IO36': 29, 'IO37': 30, 'IO38': 31, 'IO39': 32, 'IO40': 33,
          'IO41': 34, 'IO42': 35, 'RXD0': 36, 'TXD0': 37, 'IO2': 38, 'IO1': 39}
# include/pinmap/fujiversal-coleco.h (SD 38-41, UART0 43/44, LED strip 48; the RP link is the S3's own
# USB, IO19 / IO20) + the fujiversal RUN / BOOTSEL forcing pins (IO4 / IO5) and SD card detect on
# IO42, as every on-cart S3 board (README "Firmware changes": the pin map lacks them)
S3_NET = {'EN': 'S3_EN', 'IO0': 'S3_IO0', 'IO4': 'RUN_CTL', 'IO5': 'BOOTSEL_CTL',
          'IO19': 'USB_DM', 'IO20': 'USB_DP', 'IO38': 'SD_MOSI', 'IO39': 'SD_SCK',
          'IO40': 'SD_MISO', 'IO41': 'SD_CS', 'IO42': 'SD_CD', 'IO48': 'LED_STRIP',
          'RXD0': 'S3_RXD', 'TXD0': 'S3_TXD'}

# ColecoVision cartridge port: pin -> (net, symbol pin name).  MAME bus/coleco/cartridge/exp.h and the
# ADAM Technical Reference Manual (J1): odd pins on the back (B.Cu), even pins on the component face
# (F.Cu), pin 2 behind pin 1.  The selects come from the console's '138, enabled by /MREQ and RFSH: a
# write selects as a read does, refresh never.  Pin 13 "SHLD" (ADAM: RF ground) is tied to GND here,
# as ThatOldNerd's and mheironimus's carts do.  No /RD, /WR, A15, clock or reset reach the cart.
SELECTS = ['SEL8000_N', 'SELA000_N', 'SELC000_N', 'SELE000_N']
EDGE = {1: ('CD2', 'D2'), 3: ('CD1', 'D1'), 5: ('CD0', 'D0'), 7: ('CA0', 'A0'), 9: ('CA1', 'A1'),
        11: ('CA2', 'A2'), 13: ('GND', 'SHLD'), 15: ('CA3', 'A3'), 17: ('CA4', 'A4'), 19: ('CA13', 'A13'),
        21: ('CA5', 'A5'), 23: ('CA6', 'A6'), 25: ('CA7', 'A7'), 27: ('SELE000_N', '~{E000}'), 29: ('GND', 'GND'),
        2: ('SELC000_N', '~{C000}'), 4: ('CD3', 'D3'), 6: ('CD4', 'D4'), 8: ('CD5', 'D5'), 10: ('CD6', 'D6'),
        12: ('CD7', 'D7'), 14: ('CA11', 'A11'), 16: ('CA10', 'A10'), 18: ('SEL8000_N', '~{8000}'),
        20: ('CA14', 'A14'), 22: ('SELA000_N', '~{A000}'), 24: ('CA12', 'A12'), 26: ('CA9', 'A9'),
        28: ('CA8', 'A8'), 30: ('CONS_5V', '+5V')}
assert sorted(EDGE) == list(range(1, 31))
EDGE = {str(k): v for k, v in EDGE.items()}
assert sorted(n for n, _ in EDGE.values() if n.startswith('CA')) == sorted('CA%d' % i for i in range(15))
assert sorted(n for n, _ in EDGE.values() if n.startswith('CD')) == sorted('CD%d' % i for i in range(8))

# the 15 address lines, in GPIO order, through 330R in four 4-resistor arrays (unit k = pins k / 9-k):
# (array key, [edge-side nets of resistors 1-4]); the fourth array's fourth resistor is unused
ADDR_PACKS = [('RN_A0', ['CA0', 'CA1', 'CA2', 'CA3']), ('RN_A4', ['CA4', 'CA5', 'CA6', 'CA7']),
              ('RN_A8', ['CA8', 'CA9', 'CA10', 'CA11']), ('RN_A12', ['CA12', 'CA13', 'CA14', None])]

# gate value -> [((input pads), output pad)] per unit (KiCad 74xGxx pin numbers)
GATE_PINS = {'74LVC1G11': [((1, 3, 6), 4)], '74LVC1G08': [((1, 2), 4)]}

# ---- common parts: footprint, (MPN, LCSC) ----------------------------------
FP = lambda n: '%s:%s' % (LIB, n)
R0603 = FP('R_0603_1608Metric')
R0402 = FP('RPI_R0402')
C0603 = FP('C_0603_1608Metric')
C0805 = FP('C_0805_2012Metric')
RES = {'27R': ('0603WAF270JT5E', 'C25190'), '330R': ('0603WAF3300T5E', 'C23138'),
       '680R': ('0603WAF6800T5E', 'C23228'), '1k': ('0603WAF1001T5E', 'C21190'),
       '5.1k': ('0603WAF5101T5E', 'C23186'), '10k': ('0603WAF1002T5E', 'C25804'),
       '15k': ('0603WAF1502T5E', 'C22809'), '22k': ('0603WAF2202T5E', 'C31850'),
       '33k': ('0603WAF3302T5E', 'C4216'), '47k': ('0603WAF4702T5E', 'C25819')}
RES0402 = {'27R': ('0402WGF270JTCE', 'C25100'), '33R': ('0402WGF330JTCE', 'C25105')}
CAP = {'15pF': (C0603, 'CL10C150JB8NNNC', 'C1644'),
       '100nF': (C0603, 'CC0603KRX7R9BB104', 'C14663'),
       '1uF': (C0603, 'CL10A105KB8NNNC', 'C15849'),
       '4.7uF': (C0603, 'CL10A475KO8NNNC', 'C19666'),
       '10uF': (C0603, 'CL10A106KP8NNNC', 'C19702'),
       '22uF': (C0805, 'CL21A226MAQNNNE', 'C45783'),
       # RP2350 core-regulator corner: Raspberry Pi's minimal-design 0402 parts
       '100nF/0402': (FP('RPI_C0402'), 'CL05B104KO5NNNC', 'C1525'),
       '4.7uF/0402': (FP('RPI_C0402'), 'CL05A475MP5NRNC', 'C23733'),
       '4.7uF/0402w': (FP('RPI_C0402_wide'), 'CL05A475MP5NRNC', 'C23733')}
RPACK = {'4x10k': ('4D03WGJ0103T5E', 'C29718'), '4x330R': ('4D03WGJ0331T5E', 'C12018')}

# MPN -> manufacturer (names from LCSC's / JLCPCB's pages)
MFR = {'RP2350A': 'Raspberry Pi', 'W25Q16JVUXIQ': 'Winbond', 'SN74LVC245APWR': 'Texas Instruments',
       'SN74LVC1G11DBVR': 'Texas Instruments', 'SN74LVC1G08DBVR': 'Texas Instruments',
       'CC0603KRX7R9BB104': 'YAGEO', 'CL10A106KP8NNNC': 'Samsung Electro-Mechanics',
       'CL10A475KO8NNNC': 'Samsung Electro-Mechanics', 'CL10C150JB8NNNC': 'Samsung Electro-Mechanics',
       'CL10A105KB8NNNC': 'Samsung Electro-Mechanics', 'CL21A226MAQNNNE': 'Samsung Electro-Mechanics',
       'CL05B104KO5NNNC': 'Samsung Electro-Mechanics', 'CL05A475MP5NRNC': 'Samsung Electro-Mechanics',
       'AOTA-B201610S3R3-101-T': 'Abracon', 'ABM8-272-T3': 'Abracon', 'TS-1187A-B-A-B': 'XKB Connection',
       'KT-0603R': 'Hubei KENTO Elec', 'TYPE-C-31-M-12': 'Korean Hroparts Elec',
       'AP2112K-3.3TRG1': 'Diodes Incorporated', 'AP63203WU-7': 'Diodes Incorporated',
       'ESP32-S3-WROOM-1-N16R8': 'Espressif', 'TF-015': 'SOFNG', 'WS2812B-2020-V6': 'Worldsemi',
       '4D03WGJ0103T5E': 'UNI-ROYAL', '4D03WGJ0331T5E': 'UNI-ROYAL', 'CP2102N-A02-GQFN28R': 'Silicon Labs',
       'UMH3N': 'Jiangsu Changjing (JSCJ)', 'USBLC6-2SC6': 'STMicroelectronics', 'BAT54C,215': 'Nexperia',
       'TPS2116DRLR': 'Texas Instruments', 'SWPA4030S6R8MT': 'Sunlord'}
for _v in list(RES.values()) + list(RES0402.values()):
    MFR.setdefault(_v[0], 'UNI-ROYAL')


class Part:
    def __init__(self, prefix, lib_id, value, footprint, pins, sheet,
                 mpn='', lcsc='', desc='', bom=True, dnp=False, key=None, ds=''):
        self.prefix, self.lib_id, self.value, self.footprint = prefix, lib_id, value, footprint
        self.pins = {str(k): v for k, v in pins.items()}  # pad number -> net (None = NC)
        self.sheet, self.mpn, self.lcsc, self.desc, self.bom, self.dnp = sheet, mpn, lcsc, desc, bom, dnp
        self.mfr = MFR.get(mpn, '')
        self.nc_pads = ()   # footprint pads the symbol has no pin for (NC on the part)
        self.ds = ds        # datasheet URL when the stock symbol's is another part's
        self.key = key      # stable name the layout scripts use (references follow declaration order)
        self.unit_sheets = {}   # unit -> sheet, for a part drawn on several sheets
        self.pin_unit = {}      # pad -> unit (only with unit_sheets)
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


def R4(value, a, b, desc='', **k):
    mpn, lcsc = RES0402[value]
    return add('R', 'Device:R', value, R0402, {1: a, 2: b}, mpn=mpn, lcsc=lcsc, desc=desc, **k)


def C(value, a, b='GND', desc='', **k):
    fp, mpn, lcsc = CAP[value]
    return add('C', 'Device:C', value.split('/')[0], fp, {1: a, 2: b}, mpn=mpn, lcsc=lcsc, desc=desc, **k)


def RN(value, nets, common, desc='', **k):
    """4-resistor array, one symbol unit per resistor (R_Pack04_Split: unit k = pins k and 9-k), each
    drawn on its line: nets[0..3] on pins 1-4, common on 5-8."""
    mpn, lcsc = RPACK[value]
    pins = {i + 1: n for i, n in enumerate(nets)}
    pins.update({8 - i: common for i in range(4)})
    return add('RN', 'Device:R_Pack04_Split', value, FP('R_Array_Convex_4x0603'), pins, mpn=mpn, lcsc=lcsc,
               desc=desc, **k)


def SW(value, net, desc, **k):
    # XKB TS-1187A-B-A-B (JLCPCB basic C318884), as FujiNet-StudioII / 5200 / 7800 / SMS Rev0
    return add('SW', 'Switch:SW_Push', value, FP('SW_SPST_TS-1187A'), {1: net, 2: 'GND'},
               mpn='TS-1187A-B-A-B', lcsc='C318884', desc=desc, **k)


def TP(net, label, desc='test pad', **k):
    return add('TP', 'Connector:TestPoint', label, FP('TestPoint_Pad_D1.5mm'), {1: net},
               desc=desc, bom=False, **k)


def RS(value, pairs, desc='', **k):
    """4-resistor array as four series resistors (R_Pack04_Split: unit k = pins k and 9-k):
    pairs[k-1] = (net on pin k, net on pin 9-k); (None, None) leaves that resistor unused."""
    mpn, lcsc = RPACK[value]
    pins = {}
    for i, (a, b) in enumerate(pairs):
        pins[i + 1], pins[8 - i] = a, b
    return add('RN', 'Device:R_Pack04_Split', value, FP('R_Array_Convex_4x0603'), pins, mpn=mpn, lcsc=lcsc,
               desc=desc, **k)


# =========================================================================
sheet('cart-bus')
add('J', '%s:Coleco_Cart_Edge_30' % LIB, 'Coleco_Cart_Edge_30', FP('Coleco_Cart_Edge_30'),
    {k: v[0] for k, v in EDGE.items()}, desc='ColecoVision cartridge edge, 2x15 gold fingers, 2.54 mm pitch; '
    'odd pins on the back, even pins on the component face', bom=False, key='J_EDGE')
# -- the RP2350A first, so it is U1 (stitch_gnd / finish_route find it by that reference).  Two units:
# GPIO here, the core on rp-core.  Every RP supply pin on +3V3_RP, the LDO off the cart's +5V, so the
# pads are powered whenever the cart is (its 5 V-tolerant pads need IOVDD up).
rp = {21: 'XIN', 22: 'XOUT', 24: 'SWCLK', 25: 'SWDIO', 26: 'RUN',
      44: RP_RAIL,                                                  # ADC_AVDD
      46: 'VREG_AVDD', 47: 'GND', 48: 'RP_LX', 49: RP_RAIL, 50: 'DVDD',   # VREG: AVDD PGND LX VIN FB
      51: 'RP_USB_DM', 52: 'RP_USB_DP', 53: RP_RAIL, 54: RP_RAIL,     # USB, USB_OTP_VDD, QSPI_IOVDD
      55: 'QSPI_SD3', 56: 'QSPI_SCLK', 57: 'QSPI_SD0', 58: 'QSPI_SD2', 59: 'QSPI_SD1',   # the W25Q16
      60: 'QSPI_SS', 61: 'GND'}
rp.update({p: RP_RAIL for p in RP_IOVDD_PINS})
rp.update({p: 'DVDD' for p in RP_DVDD_PINS})
for g, pin in RP_GPIO_PIN.items():
    rp[pin] = RP_GPIO_NET[g]
U_RP = add('U', '%s:RP2350A_Split' % LIB, 'RP2350A', FP('RPI_RP2350A_QFN60'), rp,
           mpn='RP2350A', lcsc='C42411118', desc='RP2350A: serves the ColecoVision cart bus (fujicoleco)',
           key='U_RP', ds='https://datasheets.raspberrypi.com/rp2350/rp2350-datasheet.pdf')
# drawn in two units: A = the 30 GPIOs on the cart-bus sheet, B = supplies, core regulator, crystal,
# RUN, SWD, USB and QSPI on rp-core (gen_sch.rp_split_symbol)
U_RP.unit_sheets = {1: 'cart-bus', 2: 'rp-core'}
U_RP.pin_unit = {str(pad): 1 if pad in RP_GPIO_PIN.values() else 2 for pad in rp}
# -- A0-A14: straight into GP0-14 through 330R (four arrays, GPIO order)
for key, nets in ADDR_PACKS:
    RS('4x330R', [(n, 'RP_A' + n[2:]) if n else (NC, NC) for n in nets],
       desc='address series, %s' % ', '.join(n[1:] for n in nets if n), key=key)
# -- the chip select: /8000 /A000 /C000 /E000 ANDed (any one low = a cart access, read or write).
# Pulled up so a cart on USB alone, out of a console, reads none selected.  74LVC: 5 V-tolerant
# inputs at 3.3 V (VIH 2.0 V against the LS138's VOH 2.7 V).
# units 1-4 west to east on the board, in the order the select fingers come from (/C000 at the far west)
SEL_PULLUPS = ['SELC000_N', 'SEL8000_N', 'SELA000_N', 'SELE000_N']
RN('4x10k', SEL_PULLUPS, RP_RAIL, desc='select pull-ups (no console: none selected)', key='RN_SEL')
add('U', '74xGxx:74LVC1G11', '74LVC1G11', FP('SOT-23-6'),
    {1: 'SEL8000_N', 2: 'GND', 3: 'SELA000_N', 4: 'SEL_ABC_N', 5: RP_RAIL, 6: 'SELC000_N'},
    mpn='SN74LVC1G11DBVR', lcsc='C22046', desc='select AND: /8000 . /A000 . /C000', key='U_AND3')
C('100nF', RP_RAIL, desc='74LVC1G11 decoupling', key='C_AND3')
add('U', '74xGxx:74LVC1G08', '74LVC1G08', FP('SOT-23-5'),
    {1: 'SEL_ABC_N', 2: 'SELE000_N', 3: 'GND', 4: 'CART_CE_N', 5: RP_RAIL},
    mpn='SN74LVC1G08DBVR', lcsc='C7666', desc='select AND: . /E000 = /CE (GP26 and the buffer /OE)', key='U_AND2')
C('100nF', RP_RAIL, desc='74LVC1G08 decoupling', key='C_AND2')
# -- D0-D7 through the 74LVC245A: A port = the edge, B port = GP15-22 (A0..A7 pins 2-9, B0..B7 pins
# 18-11).  /OE = /CE: it drives the console only during a cart select.  DIR high = A -> B = console
# -> cart (coleco_cart.h DIR 1); the 10k holds it there while the RP is in reset.
buf = {1: 'BUF_DIR', 10: 'GND', 19: 'CART_CE_N', 20: RP_RAIL}
buf.update({2 + i: 'CD%d' % i for i in range(8)})
buf.update({18 - i: 'RP_D%d' % i for i in range(8)})
add('U', '%s:74LVC245A_Fn' % LIB, '74LVC245A', FP('TSSOP-20_4.4x6.5mm_P0.65mm'), buf,
    mpn='SN74LVC245APWR', lcsc='C7848', desc='data buffer, 5V-tolerant at 3.3V: edge D0-D7 <-> GP15-22',
    key='U_BUF', ds='https://www.ti.com/lit/ds/symlink/sn74lvc245a.pdf')
C('100nF', RP_RAIL, desc='74LVC245A decoupling', key='C_BUF')
R('10k', RP_RAIL, 'BUF_DIR', desc='DIR pull-up: console -> cart while the RP is in reset', key='R_DIR')
# activity LED on GP25 (PICO_DEFAULT_LED_PIN); red, so a 3.3 V pin lights it (~2 mA)
R('680R', 'RP_LED', 'RP_LED_A', desc='LED series (~2 mA)', key='R_LED')
add('D', 'Device:LED', 'red', FP('LED_0603_1608Metric'), {1: 'GND', 2: 'RP_LED_A'},
    mpn='KT-0603R', lcsc='C2286', desc='RP activity LED (GP25)', key='D_LED')
# console 5 V sense (GP28 = coleco_cart.h PWR, read as a digital input; ADC2, not 5 V tolerant):
# 10k / 15k = 0.6 x CONS_5V, 3.0 V at 5.0 V; 6 kOhm source, under RP2350-E9's 8.2 kOhm; 100 nF ~0.6 ms
# filter.  Taken at the edge, ahead of the mux: a cart on USB in a console that is off reads 0.
R('10k', 'CONS_5V', 'VSENSE', desc='console 5V sense divider', key='R_VSH')
R('15k', 'VSENSE', 'GND', desc='console 5V sense divider (0.6 x CONS_5V)', key='R_VSL')
C('100nF', 'VSENSE', desc='console 5V sense filter', key='C_VS')
TP('SELFTEST', 'SELFTEST', desc='test pad: GP29, a self-test trigger for bring-up', key='TP_SELFTEST')
TP('DBG_TX', 'DBG_TX', desc='test pad: GP24 (UART1 TX), debug UART (3.3 V)', key='TP_DBGTX')
TP('GP23', 'GP23', desc='test pad: GP23, spare', key='TP_GP23')

# =========================================================================
sheet('rp-core')
# RP2350 datasheet section 6.3.7 Figure 19 ("combined supplies"): VREG_VIN and VREG_AVDD (through 33R)
# from one 3.3 V supply, 3.3 uH + 4.7 uF core regulator; DVDD 100 nF on the two pins nearest the
# regulator (39, 6), 4.7 uF on the far one (23).  The regulator corner is Raspberry Pi's own RP2350A
# minimal-design layout (0402 parts, gen_pcb.py grafts it).  FujiNet-Arcadia Rev0's core.
for pin in RP_IOVDD_PINS:
    # the three south of the RP in Raspberry Pi's 0402 (their column sits beside the W25Q16's QSPI lines)
    C('100nF/0402' if pin in (1, 11, 20) else '100nF', RP_RAIL, desc='IOVDD decoupling (pin %d)' % pin,
      key='C_IOVDD%d' % pin)
C('100nF', RP_RAIL, desc='ADC_AVDD decoupling', key='C_ADC')
C('100nF/0402', RP_RAIL, desc='USB_OTP_VDD + QSPI_IOVDD decoupling', key='C_OTP')
C('10uF', RP_RAIL, desc='+3V3_RP bulk at the RP', key='C_RPBULK')
C('4.7uF/0402w', RP_RAIL, desc='VREG_VIN input (C_IN)', key='C_VIN')
R4('33R', RP_RAIL, 'VREG_AVDD', desc='VREG_AVDD RC filter (R_FILT)', key='R_FILT')
C('4.7uF/0402', 'VREG_AVDD', desc='VREG_AVDD RC filter (C_FILT)', key='C_FILT')
add('L', 'Device:L', '3.3uH', FP('RPI_L_AOTA-B201610S3R3'), {1: 'DVDD', 2: 'RP_LX'},
    mpn='AOTA-B201610S3R3-101-T', lcsc='C42411119', desc='RP2350 core SMPS inductor (polarity marked)', key='L_VREG')
C('4.7uF/0402w', 'DVDD', desc='core regulator output (C_OUT)', key='C_VOUT')
C('100nF/0402', 'DVDD', desc='DVDD decoupling (pin 39)', key='C_DVDD39')
C('100nF/0402', 'DVDD', desc='DVDD decoupling (pin 6)', key='C_DVDD6')
C('4.7uF/0402', 'DVDD', desc='DVDD decoupling (pin 23, far from the regulator)', key='C_DVDD23')
# QSPI boot flash: 2 MB (W25Q080-compatible boot2, as a Pico 2's), the RP2350 hardware design guide's
# wiring; its /CS is QSPI_SS, the BOOTSEL strap.  USON-8: the exposed pad is left unconnected (Winbond:
# "the exposed pad may be left floating or connected to GND").
fl = add('U', '%s:W25Q16JV_Fn' % LIB, 'W25Q16JVUXIQ', FP('Winbond_USON-8-1EP_3x2mm_P0.5mm_EP0.2x1.6mm'),
         {1: 'QSPI_SS', 2: 'QSPI_SD1', 3: 'QSPI_SD2', 4: 'GND', 5: 'QSPI_SD0', 6: 'QSPI_SCLK', 7: 'QSPI_SD3',
          8: RP_RAIL}, mpn='W25Q16JVUXIQ', lcsc='C2843335', desc='2 MB QSPI boot flash', key='U_FLASH',
         ds='https://www.winbond.com/resource-files/w25q16jv%20spi%20revd%2008122016.pdf')
fl.nc_pads = ('9',)
C('100nF', RP_RAIL, desc='flash decoupling', key='C_FLASH')
# 12 MHz crystal (minimal design: ABM8-272-T3, 15 pF loads, 1k in XOUT)
add('Y', 'Device:Crystal_GND24', '12MHz', FP('Crystal_SMD_3225-4Pin_3.2x2.5mm'),
    {1: 'XIN', 2: 'GND', 3: 'XOUT_Y', 4: 'GND'}, mpn='ABM8-272-T3', lcsc='C20625731', desc='RP2350 12 MHz crystal',
    key='Y_XTAL')
C('15pF', 'XIN', desc='crystal load', key='C_XIN')
C('15pF', 'XOUT_Y', desc='crystal load', key='C_XOUT')
R('1k', 'XOUT', 'XOUT_Y', desc='crystal drive limit', key='R_XOUT')
# RESET: one button resets both MCUs (the way back to the FujiNet CONFIG: the edge has no reset line);
# it pulls RP RUN and S3 EN low through a common-cathode pair, so neither chip's reset drives the other's
SW('RESET', 'RST_BTN', 'cart RESET: RP RUN + S3 EN through the BAT54C', key='SW_RESET')
add('D', 'Diode:BAT54C', 'BAT54C', FP('SOT-23'), {1: 'RUN', 2: 'S3_EN', 3: 'RST_BTN'},
    mpn='BAT54C,215', lcsc='C37704', desc='RESET steering, common cathode', key='D_RST')
# RUN / BOOTSEL, forced by the S3 exactly as fnPicoUpdater::forceBootselViaPins() expects: its pins
# idle as inputs and drive LOW to assert, so with 3.3 V on both chips a 1k series resistor is the
# whole interface.
R('10k', RP_RAIL, 'RUN', desc='RUN pull-up', key='R_RUNPU')
R('1k', 'RUN_CTL', 'RUN', desc='S3 IO4 -> RP RUN (low = reset)', key='R_RUNCTL')
R('10k', RP_RAIL, 'QSPI_SS', desc='QSPI_SS pull-up (flash /CS high at power-up)', key='R_SSPU')
R('1k', 'QSPI_SS', 'BOOTSEL_BTN', desc='BOOTSEL button series', key='R_SSBTN')
SW('BOOTSEL', 'BOOTSEL_BTN', 'RP2350A BOOTSEL (hold while pressing RESET)', key='SW_BOOTSEL')
R('1k', 'BOOTSEL_CTL', 'QSPI_SS', desc='S3 IO5 -> RP QSPI_SS (low through reset = BOOTSEL)', key='R_SSCTL')
# RP <-> S3 native USB (RP = CDC device, S3 = host): 27R series (datasheet: USB IO)
R4('27R', 'USB_DP', 'RP_USB_DP', desc='USB series', key='R_USBP')
R4('27R', 'USB_DM', 'RP_USB_DM', desc='USB series', key='R_USBM')
# SWD (first flash: the RP's USB only reaches the S3) + a GND pad beside it, and RUN
TP('SWCLK', 'SWCLK', key='TP_SWCLK')
TP('SWDIO', 'SWDIO', key='TP_SWDIO')
TP('GND', 'GND', key='TP_GND')
TP('RUN', 'RUN', key='TP_RUN')

# =========================================================================
sheet('fujinet')
s3 = {}
for fn, pad in S3_PAD.items():
    for p in (pad if isinstance(pad, list) else [pad]):
        s3[p] = 'GND' if fn == 'GND' else '+3V3' if fn == '3V3' else S3_NET.get(fn, NC)
add('U', '%s:ESP32-S3-WROOM-1_Fn' % LIB, 'ESP32-S3-WROOM-1-N16R8', FP('ESP32-S3-WROOM-1'), s3,
    mpn='ESP32-S3-WROOM-1-N16R8', lcsc='C2913202', desc='FujiNet core (fujiversal-coleco)', key='U_S3')
C('22uF', '+3V3', desc='S3 bulk (WiFi TX bursts)', key='C_S3BULK')
C('100nF', '+3V3', desc='S3 decoupling', key='C_S3')
R('10k', '+3V3', 'S3_EN', desc='EN pull-up', key='R_EN')
C('1uF', 'S3_EN', desc='EN power-on delay', key='C_EN')
# no separate S3 EN button (the 40 mm board has no room): RESET pulls S3 EN low through the BAT54C
SW('S3_BOOT', 'S3_IO0', 'ESP32-S3 BOOT (IO0)', key='SW_S3BOOT')
add('J', '%s:MicroSD_TF015' % LIB, 'microSD', FP('TF-SMD_TF-015'),
    {1: 'SD_DAT2', 2: 'SD_CS', 3: 'SD_MOSI', 4: '+3V3', 5: 'SD_SCK', 6: 'GND',
     7: 'SD_MISO', 8: 'SD_DAT1', 9: 'SD_CD', 10: 'GND', 11: 'GND', 12: 'GND', 13: 'GND'},
    mpn='TF-015', lcsc='C113206', desc='microSD push-push, SPI mode', key='J_SD')
RN('4x10k', ['SD_CS', 'SD_MISO', 'SD_DAT1', 'SD_DAT2'], '+3V3', desc='SD pull-ups', key='RN_SD')
# TF-015 card-detect: open with no card, closed to the shell (GND) with a card in
R('10k', '+3V3', 'SD_CD', desc='card-detect pull-up (low = card present)', key='R_SDCD')
C('10uF', '+3V3', desc='microSD supply', key='C_SD')
# WS2812B-2020-V6 datasheet: VDD +3.7..+5.3 V (NOT a 3.3 V part), VIH min 2.7 V:
# it runs on +5V (the mux's output) and takes the S3's 3.3 V data directly
R('330R', 'LED_STRIP', 'WS_DIN', desc='WS2812 data series', key='R_WS')
add('D', 'LED:WS2812B-2020', 'WS2812B-2020-V6', FP('LED_WS2812B-2020_PLCC4_2.0x2.0mm'),
    {1: NC, 2: 'GND', 3: 'WS_DIN', 4: '+5V'}, mpn='WS2812B-2020-V6', lcsc='C52917434',
    desc='status LED on +5V (datasheet VDD 3.7-5.3 V; VIH 2.7 V takes 3.3 V data)', key='D_WS')
C('100nF', '+5V', desc='WS2812 decoupling', key='C_WS')

# =========================================================================
sheet('usb')
add('J', '%s:USB_C_USB2.0_16P_Fn' % LIB, 'USB-C', FP('USB_C_Receptacle_HRO_TYPE-C-31-M-12'),
    {'A1': 'GND', 'A4': 'VBUS', 'A5': 'CC1', 'A6': 'UBRG_DP', 'A7': 'UBRG_DM', 'A8': NC,
     'A9': 'VBUS', 'A12': 'GND', 'B1': 'GND', 'B4': 'VBUS', 'B5': 'CC2', 'B6': 'UBRG_DP',
     'B7': 'UBRG_DM', 'B8': NC, 'B9': 'VBUS', 'B12': 'GND', 'SH': 'GND'},
    mpn='TYPE-C-31-M-12', lcsc='C165948', desc='power + S3 programming / console', key='J_USB')
R('5.1k', 'CC1', 'GND', desc='UFP Rd', key='R_CC1')
R('5.1k', 'CC2', 'GND', desc='UFP Rd', key='R_CC2')
# USBLC6-2SC6: ~3.5 pF per line (an ESD5Z per line would add up to 80 pF), VBUS clamp on pin 5;
# flow-through: I/O1 (pins 1 / 6, joined inside) carries D-, I/O2 (3 / 4) D+
add('U', 'Power_Protection:USBLC6-2SC6', 'USBLC6-2SC6', FP('SOT-23-6'),
    {1: 'UBRG_DM', 2: 'GND', 3: 'UBRG_DP', 4: 'UBRG_DP', 5: 'VBUS', 6: 'UBRG_DM'},
    mpn='USBLC6-2SC6', lcsc='C7519', desc='USB ESD: D+, D-, VBUS', key='U_ESD')
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
# VBUS sense (datasheet: VBUS pin max VDD + 2.5 V on a self-powered design): 22k / 47k = 3.4 V
R('22k', 'VBUS', 'VBUS_SNS', desc='VBUS sense divider', key='R_VBSH')
R('47k', 'VBUS_SNS', 'GND', desc='VBUS sense divider', key='R_VBSL')
# /RSTb: "In all cases, a 1 kOhm pull-up on the RSTb pin is recommended" (CP2102N datasheet)
R('1k', '+3V3', 'CP_RST', desc='/RST pull-up (datasheet: 1k)', key='R_CPRST')
add('U', 'Transistor_BJT:UMH3N', 'UMH3N', FP('SOT-363_SC-70-6'),
    {1: 'UART_RTS', 2: 'UART_DTR', 6: 'S3_EN', 3: 'S3_IO0', 4: 'UART_DTR', 5: 'UART_RTS'},
    mpn='UMH3N', lcsc='C62892', desc='esptool auto-program (DevKitC-1 style)', key='U_AUTOPROG')

# =========================================================================
sheet('power')
# +5V (the RP's LDO, the S3's buck, the WS2812) is the TPS2116 power mux's output:
#   VIN1  USB VBUS -- the priority input: MODE on VIN1, PR1 from a 33k / 10k divider, so VBUS above
#         VREF x 4.3 (3.96-4.64 V) runs the cart and the console's supply delivers nothing
#   VIN2  CONS_5V, edge pin 30, the console's 5 V (the ADAM Technical Reference Manual gives its cart
#         slot "typical available current 0.2A"; the ColecoVision's is not published: README "Power")
#         -- whenever VBUS is absent
# 37-60 mOhm either way; reverse current blocking: neither source can back-feed the other, so the
# cart on USB never powers a console that is off.  ST (open drain, low on VIN2) is not used.
add('U', 'Power_Management:TPS2116DRL', 'TPS2116', FP('SOT-583-8'),
    {1: 'GND', 2: '+5V', 3: 'VBUS', 4: 'VBUS_PR', 5: 'VBUS', 6: 'CONS_5V', 7: '+5V', 8: NC},
    mpn='TPS2116DRLR', lcsc='C3235557', desc='power mux: VBUS first, console 5V second', key='U_MUX')
R('33k', 'VBUS', 'VBUS_PR', desc='mux priority threshold (VBUS > 4.3 V)', key='R_PRH')
R('10k', 'VBUS_PR', 'GND', desc='mux priority threshold', key='R_PRL')
C('1uF', 'VBUS', desc='mux VIN1 (datasheet: 1 uF at the input)', key='C_MUXV1')
C('10uF', 'CONS_5V', desc='edge 5V bulk, mux VIN2', key='C_CONS')
C('100nF', 'CONS_5V', desc='edge 5V HF bypass', key='C_CONSHF')
C('22uF', '+5V', desc='+5V bulk (mux output; buck input)', key='C_5VBULK')
# the S3 side's 3.3 V: AP63203, 2 A synchronous buck; WiFi bursts ~400 mA
C('22uF', '+5V', desc='buck input', key='C_BIN')
C('100nF', '+5V', desc='buck input HF', key='C_BINHF')
add('U', 'Regulator_Switching:AP63203WU', 'AP63203WU', FP('TSOT-23-6'),
    {1: '+3V3', 2: '+5V', 3: '+5V', 4: 'GND', 5: 'BUCK_SW', 6: 'BUCK_BST'},
    mpn='AP63203WU-7', lcsc='C780769', desc='3.3V 2A buck (S3, SD, CP2102N)', key='U_BUCK')
C('100nF', 'BUCK_SW', 'BUCK_BST', desc='bootstrap', key='C_BST')
add('L', 'Device:L', '6.8uH', FP('L_Sunlord_SWPA4030S'), {1: 'BUCK_SW', 2: '+3V3'},
    mpn='SWPA4030S6R8MT', lcsc='C62684', desc='buck inductor', key='L_BUCK')
C('22uF', '+3V3', desc='buck output', key='C_BOUT1')
C('22uF', '+3V3', desc='buck output', key='C_BOUT2')
# RP rail: a fast LDO (AP2112K: ~20 us start-up) straight off +5V, so IOVDD tracks the console rail
# as it rises and the FT pads are never unpowered with 5 V on them (the buck waits out UVLO + 4 ms
# soft start: Astrocade Rev0's lesson).
add('U', 'Regulator_Linear:AP2112K-3.3', 'AP2112K-3.3', FP('SOT-23-5'),
    {1: '+5V', 2: 'GND', 3: '+5V', 4: NC, 5: RP_RAIL},
    mpn='AP2112K-3.3TRG1', lcsc='C51118', desc='RP2350A 3.3V LDO (IOVDD, VREG_VIN, VREG_AVDD, flash, bus logic), 600mA, fast start',
    key='U_LDO')
C('1uF', '+5V', desc='LDO input', key='C_LDOIN')
C('1uF', RP_RAIL, desc='LDO output', key='C_LDOOUT')
TP('CONS_5V', 'CONS_5V', desc='bring-up pad: console 5V (edge pin 30)', key='TP_CONS5V')
TP('VBUS', 'VBUS', desc='bring-up pad: USB VBUS', key='TP_VBUS')
TP('+5V', '+5V', desc='bring-up pad: +5V (mux output)', key='TP_5V')
TP(RP_RAIL, '+3V3_RP', desc='bring-up pad: +3V3_RP (RP LDO)', key='TP_3V3')
TP('+3V3', '+3V3', desc='bring-up pad: +3V3 (buck: S3 side)', key='TP_3V3S3')

# PWR_FLAGs: nets whose drivers are passive pins (+5V is the mux's VOUT, +3V3_RP the LDO's)
PWR_FLAG_NETS = ['GND', 'CONS_5V', 'VBUS', '+3V3', 'DVDD', 'VREG_AVDD']
# nets drawn as power symbols (global, never prefixed)
RAIL_NETS = ['GND', 'CONS_5V', 'VBUS', '+5V', '+3V3', RP_RAIL, 'DVDD']

# ---- reference assignment (stable: declaration order) ---------------------
_count = {}
for p in PARTS:
    _count[p.prefix] = _count.get(p.prefix, 0) + 1
    p.ref = '%s%d' % (p.prefix, _count[p.prefix])

BY_REF = {p.ref: p for p in PARTS}
KEY = {p.key: p.ref for p in PARTS if p.key}
BY_KEY = {p.key: p for p in PARTS if p.key}
assert len(KEY) == len([p for p in PARTS if p.key]), 'duplicate part key'


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
