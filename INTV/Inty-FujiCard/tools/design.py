"""Inty-FujiCard (Yannick Erb's PINTY-FUJI-CARD v1.1: RP2354A + ESP32-S3) -- the circuit, written out.

The board came first: Yannick's EasyEDA layout is the design (tools/convert.py brings it to KiCad
unchanged), and this file is its circuit, written by hand in the house form so the schematic can
be drawn from it (gen_sch.py) and every part carries its MPN and LCSC code (export.py).  It cannot
change a connection: tools/board_netlist.py --check proves every net here is exactly one of the
board's (the same pads), every pad the board leaves open is NC here, and every reference, value
and footprint is the board's.  check_nets.py does NOT import it: it reads the netlist and the
firmware sources and checks one against the other.

Net names are Yannick's (GPIO00-27, VSYS, 3V3, 1V1, RUN_CTL, BOOTSEL_CTL, S3_EN, USB_D+ ...);
only EasyEDA's automatic ones (R13_1, U2_5, ...) get a name here (NET_ALIAS).  References are
his, numbered where KiCad needs a number (tools/convert.py RENAME: BOOT -> SW1 ...).

Firmware contract (fujinet-firmware master):
  pico/intellivision/firmware/boards/fujicard.h   MI_AD0_PIN 0 (GP0-15 = the bus's AD0-15),
                                                  MI_RST_PIN 20, MI_MSYNC_PIN 21, MI_BDIR_PIN 22,
                                                  MI_BC1_PIN 26, MI_BC2_PIN 27 (and MI_LED_PIN 25,
                                                  the debug TX on 24, the self-test on 23: this
                                                  board has none of them, README "Firmware")
  pico/intellivision/firmware/boards/pintycard.h  MI_AUDIO_PIN 28 (ECS audio; fujicard.h has none)
  include/pinmap/fujiversal-intv.h               SD 38-41, UART0 43/44, LED strip 48, RP RUN on
                                                  IO4, RP BOOTSEL on IO5, the RP link on the S3's
                                                  own USB (IO19 / IO20)
"""

LIB = 'Inty-FujiCard'
PROJECT = 'Inty-FujiCard'
NC = None  # explicit no-connect

SHEETS = [  # (file stem, title, page) -- in signal-flow order, console side first
    ('cart-bus', 'Cart bus: the edge, RP2354A GPIO', 2),
    ('rp-core', 'RP2354A core, RUN / BOOTSEL, SWD', 3),
    ('fujinet', 'FujiNet: ESP32-S3, microSD, LED', 4),
    ('usb', 'USB-C + CP2102N', 5),
    ('power', 'Power: diode-OR, 3.3 V buck', 6),
]
SHEET_ORDER = [s[0] for s in SHEETS]

# ---- RP2354A (QFN-60, the RP2350A's package with 2 MB of flash inside) -------------------------
# GPIO -> package pin: RP2350 datasheet (QFN-60 column); gen_sch.py re-checks every entry against
# the KiCad symbol's pin names.
RP_GPIO_PIN = {0: 2, 1: 3, 2: 4, 3: 5, 4: 7, 5: 8, 6: 9, 7: 10, 8: 12, 9: 13, 10: 14, 11: 15,
               12: 16, 13: 17, 14: 18, 15: 19, 16: 27, 17: 28, 18: 29, 19: 31, 20: 32, 21: 33,
               22: 34, 23: 35, 24: 36, 25: 37, 26: 40, 27: 41, 28: 42, 29: 43}
RP_IOVDD_PINS = [1, 11, 20, 30, 38, 45]
RP_DVDD_PINS = [6, 23, 39]
# Yannick's GPIO nets: GP0-15 the bus (AD0-15, fujicard.h MI_AD0_PIN 0), GP16 / GP17 the TX / RX
# pads, GP20 the console reset through Q1, GP21 MSYNC, GP22 BDIR, GP26 BC1, GP27 BC2, GP28 the
# ECS audio (PWM, through R5 to the edge); GP18, 19, 23-25 and 29 are not connected.
RP_GPIO_NET = {g: 'GPIO%02d' % g for g in list(range(18)) + [20, 21, 22, 26, 27]}
RP_GPIO_NET.update({28: 'PWM', 18: NC, 19: NC, 23: NC, 24: NC, 25: NC, 29: NC})
assert set(RP_GPIO_NET) == set(RP_GPIO_PIN)

# ESP32-S3-WROOM-1 module pad -> function (pads per the KiCad symbol; Yannick's footprint has the
# exposed pad as nine pads numbered 41)
S3_PAD = {'GND': [1, 40, 41], '3V3': 2, 'EN': 3, 'IO4': 4, 'IO5': 5, 'IO6': 6,
          'IO7': 7, 'IO15': 8, 'IO16': 9, 'IO17': 10, 'IO18': 11, 'IO8': 12,
          'IO19': 13, 'IO20': 14, 'IO3': 15, 'IO46': 16, 'IO9': 17, 'IO10': 18,
          'IO11': 19, 'IO12': 20, 'IO13': 21, 'IO14': 22, 'IO21': 23,
          'IO47': 24, 'IO48': 25, 'IO45': 26, 'IO0': 27, 'IO35': 28,
          'IO36': 29, 'IO37': 30, 'IO38': 31, 'IO39': 32, 'IO40': 33,
          'IO41': 34, 'IO42': 35, 'RXD0': 36, 'TXD0': 37, 'IO2': 38, 'IO1': 39}
S3_NET = {'EN': 'S3_EN', 'IO0': 'S3_IO0', 'IO4': 'RUN_CTL', 'IO5': 'BOOTSEL_CTL',
          'IO19': 'USB_DM', 'IO20': 'USB_DP', 'IO38': 'SD_MOSI', 'IO39': 'SD_SCK',
          'IO40': 'SD_MISO', 'IO41': 'SD_CS', 'IO48': 'LED_STRIP',
          'RXD0': 'S3_RXD', 'TXD0': 'S3_TXD'}

# Intellivision cartridge port: the board's finger -> (net, INTV pin, signal).  Yannick's
# footprint numbers the fingers A1-A22 (component face, F.Cu) and B1-B22 (back, B.Cu), left to
# right seen from the component face, contacts down; the INTV pin is 46 - 2k on A(k) and
# 45 - 2k on B(k): even pins in front, odd behind (the attic FujiNet-INTV-Rev0's edge, traced
# from the PiNTY CARD's gerbers, and the firmware's bus map agree on every finger, check_nets.py).
# The three shorted pairs pass a console signal through the cart (32/42, 34/40, 36/38).
EDGE_SIGNAL = {1: 'GND', 2: 'NC', 3: '~{MSYNC}', 4: 'NC', 5: 'D7', 6: 'EXT_AUDIO', 7: 'D8', 8: 'GND',
               9: 'D6', 10: 'GND', 11: 'D9', 12: '~{RESET}', 13: 'D5', 14: 'NC', 15: 'D10', 16: 'NC',
               17: 'D4', 18: 'NC', 19: 'D11', 20: 'GND', 21: 'D3', 22: 'GND', 23: 'D12', 24: 'GND',
               25: 'D13', 26: 'GND', 27: 'D2', 28: 'GND', 29: 'D14', 30: 'NC', 31: 'D1', 32: 'PASS_A',
               33: 'D0', 34: 'PASS_B', 35: 'D15', 36: 'PASS_C', 37: 'BDIR', 38: 'PASS_C', 39: 'BC2',
               40: 'PASS_B', 41: 'BC1', 42: 'PASS_A', 43: '+5V', 44: 'GND'}
EDGE_PAD = {}       # board pad -> INTV pin
for _k in range(1, 23):
    EDGE_PAD['A%d' % _k] = 46 - 2 * _k
    EDGE_PAD['B%d' % _k] = 45 - 2 * _k
assert sorted(EDGE_PAD.values()) == list(range(1, 45))


def _edge_net(pin):
    s = EDGE_SIGNAL[pin]
    if s == 'GND':
        return 'GND'
    if s == '+5V':
        return 'VSYS'
    if s in ('NC',):
        return NC
    if s.startswith('PASS_'):
        return s
    if s[0] == 'D' and s[1:].isdigit():
        return 'GPIO%02d' % int(s[1:])
    return {'~{MSYNC}': 'GPIO21', 'BDIR': 'GPIO22', 'BC1': 'GPIO26', 'BC2': 'GPIO27',
            '~{RESET}': 'CART_RST', 'EXT_AUDIO': 'AUD'}[s]


EDGE = {pad: (_edge_net(pin), '%s (%d)' % (EDGE_SIGNAL[pin], pin)) for pad, pin in EDGE_PAD.items()}

# EasyEDA's automatic net names -> names here (Yannick's own names are kept as they are)
NET_ALIAS = {'R13_1': 'RST_Q_B', 'R1_1': 'BOOTSEL_Q_B', 'R11_2': 'BOOTSEL_BTN', 'R16_1': 'RUN_Q_B',
             'U2_5': 'BUCK_SW', 'U2_6': 'BUCK_BST', 'U8_1': 'SD_DAT2', 'U8_8': 'SD_DAT1',
             'U1_46': 'VREG_AVDD', 'L1_1': 'VREG_LX', 'LED_2': 'LED_DIN', 'U5_3': 'XOUT_Y',
             'K1_A2': 'PASS_A', 'K1_A3': 'PASS_B', 'K1_A4': 'PASS_C'}

# ---- parts: footprint, (MPN, LCSC), from Yannick's BOM (Original/BOM_*.csv) ------------------
FP = lambda n: '%s:%s' % (LIB, n)
R0402, C0402, C0603 = FP('R0402'), FP('C0402'), FP('C0603')
RES = {'1k': ('0402WGF1001TCE', 'C11702', 'UNI-ROYAL'), '330R': ('0402WGF3300TCE', 'C25104', 'UNI-ROYAL'),
       '47.5k': ('RC0402FR-0747K5L', 'C137974', 'YAGEO'), '10k': ('0402WGF1002TCE', 'C25744', 'UNI-ROYAL'),
       '5.1k': ('0402WGF5101TCE', 'C25905', 'UNI-ROYAL'), '22.1k': ('AC0402FR-0722K1L', 'C226356', 'YAGEO'),
       '27R': ('0402WGF270JTCE', 'C25100', 'UNI-ROYAL')}
CAP = {'100nF': (C0402, 'CL05B104KO5NNNC', 'C1525'), '1uF': (C0402, 'CL05A105KA5NQNC', 'C52923'),
       '15pF': (C0402, '0402CG150J500NT', 'C1548'), '4.7uF/0402': (C0402, 'CL05A475MP5NRNC', 'C23733'),
       '4.7uF': (C0603, 'CL10A475KO8NNNC', 'C19666'), '10uF': (C0603, 'CL10A106KP8NNNC', 'C19702'),
       '22uF': (C0603, 'CL10A226MQ8NRNC', 'C59461')}
# MPN -> manufacturer (his BOM's names, the Chinese name in brackets left out)
MFR = {'CL05B104KO5NNNC': 'SAMSUNG', 'CL05A105KA5NQNC': 'SAMSUNG', 'CL05A475MP5NRNC': 'SAMSUNG',
       'CL10A475KO8NNNC': 'SAMSUNG', 'CL10A106KP8NNNC': 'SAMSUNG', 'CL10A226MQ8NRNC': 'SAMSUNG',
       '0402CG150J500NT': 'FH', 'VE-101M1ATR-0505': 'Lelon', 'YC158TJR-0710KL': 'YAGEO',
       'YNR3015-4R7M': 'YJYCOIN', 'AOTA-B201610S3R3-101-T': 'ABRACON', 'ABM8-272-T3': 'ABRACON',
       'AP63203WU-7': 'DIODES', 'SK6805-EC20': 'OPSCO Optoelectronics', 'TYPE-C 16PIN 2MD(073)': 'SHOU HAN',
       'TS-1088-AR02016': 'XUNPU', 'BC847BT': 'Slkor', 'TF-CARD-9P': 'BXCONN',
       'CP2102N-A02-GQFN28R': 'SKYWORKS/SILICON LABS', 'UMH3NTN': 'ROHM', 'ESP32-S3-WROOM-1-N16R8': 'ESPRESSIF',
       'SS34': 'MDD', 'ESD5Z5.0T1G': 'BORN', 'RP2354A': 'Raspberry Pi'}
for _v in RES.values():
    MFR[_v[0]] = _v[2]


class Part:
    def __init__(self, ref, lib_id, value, footprint, pins, sheet,
                 mpn='', lcsc='', desc='', bom=True, dnp=False, ds=''):
        self.ref, self.lib_id, self.value, self.footprint = ref, lib_id, value, footprint
        self.prefix = ref.rstrip('0123456789')
        self.pins = {str(k): v for k, v in pins.items()}  # pad number -> net (None = NC)
        self.sheet, self.mpn, self.lcsc, self.desc, self.bom, self.dnp = sheet, mpn, lcsc, desc, bom, dnp
        self.mfr = MFR.get(mpn, '')
        self.nc_pads = ()   # footprint pads the symbol has no pin for
        self.ds = ds        # datasheet URL when the stock symbol's is another part's
        self.key = ref      # the drawing scripts address parts by reference here (they are Yannick's)
        self.unit_sheets = {}   # unit -> sheet, for a part drawn on several sheets
        self.pin_unit = {}      # pad -> unit (only with unit_sheets)

    def sheets(self):
        return sorted(set(self.unit_sheets.values()) | {self.sheet}, key=SHEET_ORDER.index)

    def pad_sheet(self, pad):
        if self.unit_sheets:
            return self.unit_sheets[self.pin_unit[str(pad)]]
        return self.sheet


PARTS = []
_sheet = None


def sheet(name):
    global _sheet
    _sheet = name


def add(ref, *a, **k):
    p = Part(ref, *a, sheet=_sheet, **k)
    PARTS.append(p)
    return p


def R(ref, value, a, b, desc=''):
    mpn, lcsc, _ = RES[value]
    return add(ref, 'Device:R', value, R0402, {1: a, 2: b}, mpn=mpn, lcsc=lcsc, desc=desc)


def C(ref, value, a, b='GND', desc=''):
    """Capacitor: pin 1 on a, pin 2 on b (as Yannick placed it: most have pin 1 on GND, see C())."""
    fp, mpn, lcsc = CAP[value]
    return add(ref, 'Device:C', value.split('/')[0], fp, {1: a, 2: b}, mpn=mpn, lcsc=lcsc, desc=desc)


def Cg(ref, value, net, desc=''):
    """Capacitor with pin 1 on GND, pin 2 on net (EasyEDA's 0402 / 0603 orientation on this board)."""
    return C(ref, value, 'GND', net, desc)


def SW(ref, net, desc):
    return add(ref, 'Switch:SW_Push', 'TS-1088-AR02016', FP('SW-SMD_L3.9-W3.0-P4.45'), {1: net, 2: 'GND'},
               mpn='TS-1088-AR02016', lcsc='C720477', desc=desc)


def TP(ref, net, label, desc):
    return add(ref, 'Connector:TestPoint', label, FP('TESTPOINT_PAD_D1.5MM'), {1: net}, desc=desc, bom=False)


def NPN(ref, b, e, c, desc):
    # BC847BT, SOT-523: 1 = B, 2 = E, 3 = C (KiCad's BC847: Q_NPN_BEC)
    return add(ref, 'Transistor_BJT:BC847', 'BC847BT', FP('SOT-523-3_L1.6-W0.8-P1.00-LS1.6-BR'),
               {1: b, 2: e, 3: c}, mpn='BC847BT', lcsc='C5186022', desc=desc)


# =========================================================================
sheet('cart-bus')
add('K1', '%s:INTV_Cart_Edge_44' % LIB, 'INTV_Cart_Edge_44', FP('PCB_EDGE_CONNECTOR_22X2'),
    {pad: v[0] for pad, v in EDGE.items()}, bom=False,
    desc='Intellivision cartridge edge, 2 x 22 gold fingers, 2.54 mm: A1-A22 component face, B1-B22 back')
# The RP2354A in two units: GPIO here, the core on rp-core.  Every supply pin on 3V3 (the buck:
# one rail for the whole board), the core on 1V1 from its own regulator (L1).
rp = {21: 'XIN', 22: 'XOUT', 24: 'SWCLK', 25: 'SWD', 26: 'RUN',
      44: '3V3',                                                    # ADC_AVDD
      46: 'VREG_AVDD', 47: 'GND', 48: 'VREG_LX', 49: '3V3', 50: '1V1',   # VREG: AVDD PGND LX VIN FB
      51: 'USB_D-', 52: 'USB_D+', 53: '3V3', 54: '3V3',              # USB, USB_OTP_VDD, QSPI_IOVDD
      55: NC, 56: NC, 57: NC, 58: NC, 59: NC,                         # QSPI: the flash inside the package
      60: 'QSPI_SS', 61: 'GND'}
rp.update({p: '3V3' for p in RP_IOVDD_PINS})
rp.update({p: '1V1' for p in RP_DVDD_PINS})
for g, pin in RP_GPIO_PIN.items():
    rp[pin] = RP_GPIO_NET[g]
U_RP = add('U1', '%s:RP2354A_Split' % LIB, 'RP2354A', FP('QFN-60_L7.0-W7.0-P0.40-TL-EP3.4'), rp,
           mpn='RP2354A', lcsc='C41378174', desc='RP2354A: serves the Intellivision cartridge bus (fujicard)',
           ds='https://datasheets.raspberrypi.com/rp2350/rp2350-datasheet.pdf')
U_RP.unit_sheets = {1: 'cart-bus', 2: 'rp-core'}
U_RP.pin_unit = {str(pad): 1 if pad in RP_GPIO_PIN.values() else 2 for pad in rp}
# the console reset: GP20 high turns Q1 on, which pulls the edge's /RESET low (open collector)
R('R13', '1k', 'RST_Q_B', 'GPIO20', desc='Q1 base (GP20)')
NPN('Q1', 'RST_Q_B', 'GND', 'CART_RST', desc='console /RESET, open collector (GP20 high = reset)')
# ECS audio: GP28's PWM through 1k into the edge's EXT_AUDIO (pin 6)
R('R5', '1k', 'AUD', 'PWM', desc='ECS audio: GP28 PWM -> edge pin 6')
TP('TP2', 'GPIO16', 'TX', desc='test pad: GP16 (silk TX)')
TP('TP3', 'GPIO17', 'RX', desc='test pad: GP17 (silk RX)')

# =========================================================================
sheet('rp-core')
# Raspberry Pi's combined-supply arrangement (RP2350 datasheet): VREG_VIN from 3V3 with C18,
# VREG_AVDD through R6 27R + C19, the 3.3 uH core inductor L1 with C17 at its output (1V1)
Cg('C9', '100nF', '3V3', desc='IOVDD decoupling (pin 1)')
Cg('C11', '100nF', '3V3', desc='IOVDD decoupling (pin 11)')
Cg('C12', '100nF', '3V3', desc='IOVDD decoupling (pin 20)')
Cg('C13', '100nF', '3V3', desc='IOVDD decoupling (pin 30)')
Cg('C8', '100nF', '3V3', desc='IOVDD decoupling (pin 38)')
Cg('C7', '100nF', '3V3', desc='IOVDD decoupling (pin 45)')
Cg('C10', '100nF', '3V3', desc='USB_OTP_VDD / QSPI_IOVDD decoupling (pins 53, 54)')
Cg('C18', '4.7uF', '3V3', desc='VREG_VIN input (C_IN)')
R('R6', '27R', '3V3', 'VREG_AVDD', desc='VREG_AVDD RC filter (R_FILT)')
Cg('C19', '4.7uF/0402', 'VREG_AVDD', desc='VREG_AVDD RC filter (C_FILT)')
add('L1', 'Device:L', '3.3uH', FP('IND-SMD_L2.0-W1.6_AOTA-B201610S3R3-101-T'), {1: 'VREG_LX', 2: '1V1'},
    mpn='AOTA-B201610S3R3-101-T', lcsc='C42411119', desc='RP2350 core SMPS inductor')
Cg('C17', '4.7uF', '1V1', desc='core regulator output (C_OUT)')
Cg('C16', '100nF', '1V1', desc='DVDD decoupling (pin 39)')
Cg('C14', '100nF', '1V1', desc='DVDD decoupling (pin 6)')
Cg('C15', '100nF', '1V1', desc='DVDD decoupling (pin 23)')
# 12 MHz crystal (Raspberry Pi's minimal design: ABM8-272-T3, 15 pF, 1k in XOUT)
add('U5', 'Device:Crystal_GND24', '12MHz', FP('CRYSTAL-SMD_4P-L3.2-W2.5-BL'),
    {1: 'XIN', 2: 'GND', 3: 'XOUT_Y', 4: 'GND'}, mpn='ABM8-272-T3', lcsc='C20625731', desc='RP2354A 12 MHz crystal')
Cg('C5', '15pF', 'XIN', desc='crystal load')
Cg('C6', '15pF', 'XOUT_Y', desc='crystal load')
R('R2', '1k', 'XOUT', 'XOUT_Y', desc='crystal drive limit')
# RP <-> S3 native USB (the RP is a CDC device, the S3 the host): 27R series
R('R3', '27R', 'USB_D-', 'USB_DM', desc='USB series (D-)')
R('R4', '27R', 'USB_D+', 'USB_DP', desc='USB series (D+)')
# BOOTSEL: QSPI_SS pulled up (R12), pulled low through R11 by the RP-BOOT button (SW3) or by Q3
# when the S3 raises BOOTSEL_CTL (IO5)
R('R12', '10k', '3V3', 'QSPI_SS', desc='QSPI_SS pull-up')
R('R11', '1k', 'QSPI_SS', 'BOOTSEL_BTN', desc='BOOTSEL series')
SW('SW3', 'BOOTSEL_BTN', 'RP2354A BOOTSEL (silk RP-BOOT)')
R('R1', '1k', 'BOOTSEL_Q_B', 'BOOTSEL_CTL', desc='Q3 base (S3 IO5)')
NPN('Q3', 'BOOTSEL_Q_B', 'GND', 'BOOTSEL_BTN', desc='S3 IO5 high = RP BOOTSEL')
# RUN: pulled up (R14), the RP-RUN button (SW4), Q4 when the S3 raises RUN_CTL (IO4)
R('R14', '10k', '3V3', 'RUN', desc='RUN pull-up')
SW('SW4', 'RUN', 'RP2354A reset (silk RP-RUN)')
R('R16', '1k', 'RUN_Q_B', 'RUN_CTL', desc='Q4 base (S3 IO4)')
NPN('Q4', 'RUN_Q_B', 'GND', 'RUN', desc='S3 IO4 high = RP in reset')
# SWD (first flash) and a GND pad beside it
TP('TP4', 'SWD', 'SWD', desc='test pad: SWDIO')
TP('TP5', 'SWCLK', 'SWCLK', desc='test pad: SWCLK')
TP('TP1', 'GND', 'GND', desc='test pad: GND')

# =========================================================================
sheet('fujinet')
s3 = {}
for fn, pad in S3_PAD.items():
    for p in (pad if isinstance(pad, list) else [pad]):
        s3[p] = 'GND' if fn == 'GND' else '3V3' if fn == '3V3' else S3_NET.get(fn, NC)
add('U7', '%s:ESP32-S3-WROOM-1_Fn' % LIB, 'ESP32-S3-WROOM-1-N16R8', FP('WIRELM-SMD_ESP32-S3-WROOM-1'), s3,
    mpn='ESP32-S3-WROOM-1-N16R8', lcsc='C2913202', desc='FujiNet core (fujiversal-intv)')
Cg('C24', '22uF', '3V3', desc='S3 bulk (WiFi TX bursts)')
Cg('C26', '100nF', '3V3', desc='S3 decoupling')
R('R17', '10k', '3V3', 'S3_EN', desc='EN pull-up')
Cg('C2', '1uF', 'S3_EN', desc='EN power-on delay')
SW('SW2', 'S3_EN', 'ESP32-S3 reset (silk RESET)')
SW('SW1', 'S3_IO0', 'ESP32-S3 BOOT (IO0, silk BOOT)')
Cg('C3', '100nF', 'S3_IO0', desc='IO0 debounce')
add('U8', '%s:MicroSD_XDFP-0090-012' % LIB, 'microSD', FP('SIM-SMD_LX_XDFP-0090-012'),
    {1: 'SD_DAT2', 2: 'SD_CS', 3: 'SD_MOSI', 4: '3V3', 5: 'SD_SCK', 6: 'GND', 7: 'SD_MISO', 8: 'SD_DAT1',
     9: NC, 10: 'GND'}, mpn='TF-CARD-9P', lcsc='C53144700', desc='microSD push-push, SPI mode (card detect unused)')
# YC158: eight 10k resistors in a 1206 array, bussed: 5 and 10 the common, on 3V3
add('RN1', '%s:R_Network08_YC158' % LIB, '8x10k', FP('RES-ARRAY-SMD_1206-L3.2-W1.6-P0.64'),
    {1: 'SD_MISO', 2: 'SD_MOSI', 3: 'SD_CS', 4: 'SD_DAT2', 5: '3V3', 6: 'SD_DAT1', 7: NC, 8: NC, 9: 'S3_IO0',
     10: '3V3'}, mpn='YC158TJR-0710KL', lcsc='C309679', desc='pull-ups: microSD lines, S3 IO0')
Cg('C27', '100nF', '3V3', desc='microSD decoupling')
C('C28', '10uF', '3V3', 'GND', desc='microSD supply')
R('R15', '330R', 'LED_STRIP', 'LED_DIN', desc='status LED data series')
add('D6', '%s:SK6805-EC20' % LIB, 'SK6805-EC20', FP('LED-SMD_4P-L2.0-W2.0-TL_J-ST2020RGB-IC-P4-5-SO1'),
    {1: 'GND', 2: 'LED_DIN', 3: '3V3', 4: NC}, mpn='SK6805-EC20', lcsc='C2890036', desc='status LED (IO48), on 3V3')
Cg('C1', '100nF', '3V3', desc='status LED decoupling')

# =========================================================================
sheet('usb')
add('J1', '%s:USB_C_16P_2MD073' % LIB, 'USB-C', FP('USB-C-SMD_TYPE-C-6PIN-2MD-073'),
    {1: 'GND', 2: 'VBUS', 3: NC, 4: 'CC1', 5: 'UBRTG_DM', 6: 'UBRTG_DP', 7: 'UBRTG_DM', 8: 'UBRTG_DP', 9: NC,
     10: 'CC2', 11: 'VBUS', 12: 'GND', 13: 'GND', 14: 'GND'},
    mpn='TYPE-C 16PIN 2MD(073)', lcsc='C2765186', desc='power + S3 programming / console')
R('R7', '5.1k', 'GND', 'CC1', desc='UFP Rd (CC1)')
R('R8', '5.1k', 'GND', 'CC2', desc='UFP Rd (CC2)')
_esd = dict(mpn='ESD5Z5.0T1G', lcsc='C343989')
add('D3', 'Diode:ESD5Zxx', 'ESD5Z5.0T1G', FP('SOD-523_L1.2-W0.8-LS1.6-RD'), {1: 'UBRTG_DM', 2: 'GND'},
    desc='USB D- ESD', **_esd)
add('D4', 'Diode:ESD5Zxx', 'ESD5Z5.0T1G', FP('SOD-523_L1.2-W0.8-LS1.6-RD'), {1: 'UBRTG_DP', 2: 'GND'},
    desc='USB D+ ESD', **_esd)
add('D5', 'Diode:ESD5Zxx', 'ESD5Z5.0T1G', FP('SOD-523_L1.2-W0.8-LS1.6-RD'), {1: 'VBUS', 2: 'GND'},
    desc='VBUS ESD', **_esd)
cp = {i: NC for i in range(1, 30)}
cp.update({3: 'GND', 4: 'UBRTG_DP', 5: 'UBRTG_DM', 6: '3V3', 7: '3V3', 8: 'VBUS_SNS', 9: 'CP_RST',
           23: 'GND', 24: 'UART_RTS', 25: 'S3_TXD', 26: 'S3_RXD', 28: 'UART_DTR', 29: 'GND'})
add('U3', 'Interface_USB:CP2102N-Axx-xQFN28', 'CP2102N-A02-GQFN28', FP('QFN-28_L5.0-W5.0-P0.50-TL-EP3.3'), cp,
    mpn='CP2102N-A02-GQFN28R', lcsc='C964632', desc='USB-UART for S3 flashing / console (self-powered)')
Cg('C23', '100nF', '3V3', desc='CP2102N VDD')
# VBUS sense (datasheet: the VBUS pin of a self-powered design stays under VDD + 2.5 V): 22.1k / 47.5k
R('R9', '22.1k', 'VBUS_SNS', 'VBUS', desc='VBUS sense divider')
R('R18', '47.5k', 'GND', 'VBUS_SNS', desc='VBUS sense divider')
R('R10', '1k', 'CP_RST', '3V3', desc='/RST pull-up (datasheet: 1k)')
add('Q2', 'Transistor_BJT:UMH3N', 'UMH3NTN', FP('SOT-363_L2.0-W1.3-P0.65-LS2.1-TL'),
    {1: 'UART_RTS', 2: 'UART_DTR', 3: 'S3_IO0', 4: 'UART_DTR', 5: 'UART_RTS', 6: 'S3_EN'},
    mpn='UMH3NTN', lcsc='C123008', desc='esptool auto-program (DevKitC-1 style)')

# =========================================================================
sheet('power')
# VIN: the console's +5V (VSYS, edge pin 43) and USB VBUS, each through an SS34, whichever is higher
add('D1', 'Diode:SS34', 'SS34', FP('SMA_L4.3-W2.6-LS5.2-RD'), {1: 'VIN', 2: 'VSYS'}, mpn='SS34', lcsc='C8678',
    desc='console +5V -> VIN')
add('D2', 'Diode:SS34', 'SS34', FP('SMA_L4.3-W2.6-LS5.2-RD'), {1: 'VIN', 2: 'VBUS'}, mpn='SS34', lcsc='C8678',
    desc='USB VBUS -> VIN')
add('C29', 'Device:C_Polarized', '100uF', FP('CAP-SMD_BD5.0-L5.3-W5.3-RD'), {1: 'VIN', 2: 'GND'},
    mpn='VE-101M1ATR-0505', lcsc='C134722', desc='VIN bulk')
Cg('C25', '10uF', 'VIN', desc='buck input')
add('U2', 'Regulator_Switching:AP63203WU', 'AP63203WU', FP('TSOT-26_L2.9-W1.6-P0.95-LS2.8-BL'),
    {1: '3V3', 2: 'VIN', 3: 'VIN', 4: 'GND', 5: 'BUCK_SW', 6: 'BUCK_BST'},
    mpn='AP63203WU-7', lcsc='C780769', desc='3.3V 2A buck: the whole board')
C('C21', '100nF', 'BUCK_SW', 'BUCK_BST', desc='bootstrap')
add('L2', 'Device:L', '4.7uH', FP('IND-SMD_L3.0-W3.0-1'), {1: 'BUCK_SW', 2: '3V3'},
    mpn='YNR3015-4R7M', lcsc='C340361', desc='buck inductor')
Cg('C4', '22uF', '3V3', desc='buck output')
Cg('C22', '100nF', '3V3', desc='buck output HF')

# mounting holes: in the netlist (board-only footprints, no pins), out of the BOM
add('H1', 'Mechanical:MountingHole', 'Hole_D5.127mm', FP('Hole_D5.127mm_NPTH'), {}, bom=False,
    desc='shell post hole, 5.127 mm NPTH')
add('H2', 'Mechanical:MountingHole', 'Hole_D5.127mm', FP('Hole_D5.127mm_NPTH'), {}, bom=False,
    desc='shell post hole, 5.127 mm NPTH')

# PWR_FLAGs: nets whose drivers are passive pins
PWR_FLAG_NETS = ['GND', 'VSYS', 'VBUS', 'VIN', '3V3', '1V1', 'VREG_AVDD']
# nets drawn as power symbols (global, never prefixed): net -> stock power symbol
RAIL_SYMBOL = {'GND': 'power:GND', 'VSYS': 'power:+5V', 'VBUS': 'power:VBUS', 'VIN': 'power:VCC',
               '3V3': 'power:+3V3', '1V1': 'power:+1V1'}
RAIL_NETS = list(RAIL_SYMBOL)

BY_REF = {p.ref: p for p in PARTS}
KEY = {p.ref: p.ref for p in PARTS}
BY_KEY = BY_REF
assert len(BY_REF) == len(PARTS), 'duplicate reference'


def nets():
    out = {}
    for p in PARTS:
        for pad, n in p.pins.items():
            if n:
                out.setdefault(n, []).append((p.ref, pad))
    return out


def sheet_nets():
    out = {}
    for p in PARTS:
        for pad, n in p.pins.items():
            if n:
                out.setdefault(n, set()).add(p.pad_sheet(pad))
    return out


if __name__ == '__main__':
    for p in PARTS:
        print(p.sheet, p.ref, p.value, p.footprint.split(':')[1], p.lcsc)
    ns = nets()
    print(len(PARTS), 'parts', len(ns), 'nets')
    for n, pp in sorted(ns.items()):
        if len(pp) < 2:
            print('SINGLE-PIN NET', n, pp)
