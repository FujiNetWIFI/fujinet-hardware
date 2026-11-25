"""FujiNet-TRS80M1 Rev0 (RP2354B + ESP32-S3) -- the single source of truth.

Every part, value, footprint, MPN, LCSC code and pin->net assignment lives here.  gen_sch.py,
gen_pcb.py and export.py import it; the KiCad files are generated output.  check_nets.py does NOT
import it: it reads the netlist and the firmware sources and checks one against the other.

The card replaces the TRS-80 Model I's Expansion Interface: a 40-wire ribbon from the keyboard unit's
expansion edge to this board's 2x20 box header, every line received or driven by a 3.3 V LVC buffer
at the header (5 V-tolerant inputs, Ioff), then the RP2354B.

Firmware contract (fujinet-firmware dev tree ~/Workspace/fn-trs80m1, branch trs80m1-dev, not on
master yet):
  pico/trs80m1/firmware/include/m1_card.h   M1_PIN_A0 0 (A0-A15 = GP0-15), M1_PIN_D0 16 (D0-D7 =
      GP16-23 "through a 74LVC245"), M1_PIN_WR 24, RD 25, IN 26, OUT 27, M1_PIN_DRIVE 28 ("'245 DIR;
      OE* = DRIVE & RD* & IN* in a gate"), SYSRES 29, INT 30 / WAIT 31 ("open drain"), M1_PIN_DIP0 33
      (RAM / EI / RS-232 off, closed forces it off), TXD 44, RXD 45, LED 47
  include/pinmap/fujiversal-trs80m1.h       the S3 (SD 38-41, UART0 43/44, LED strip 48)
This board keeps that map exactly and adds INTAK* on GP32 (README "Firmware changes").
GPIO0-39 are 5 V tolerant on the QFN-80, but nothing here ever puts 5 V on the RP: the buffers run
at 3.3 V.

The expansion edge (Level II; TRS-80 Technical Reference Handbook 26-2103 p.91 + Fig. 22, checked
against the RetroStack rev G replica netlist, the Tandy 26-1132 hard-disk adapter document and
TRS-IO M1 v1.4: tools/audit/header_pinout.py has the sources):
  * Tandy's numbering is the mirror of a standard IDC card-edge connector's, so a straight ribbon
    brings the pins to the header swapped in pairs (edge_of_hdr): header 1 = edge 2, 2 = 1, 3 = 4 ...
  * grounds are 8, 29 and 37 (header 7, 30, 38); pin 39 is +5V on keyboard boards A-E and GND on rev G:
    left OPEN
  * address and RD* WR* IN* OUT* RAS* CAS* MUX come from 74LS367s (Tandy: one LS load each), SYSRES*
    from an LS02, INTAK* from an LS32; INT*, WAIT* and TEST* go straight to the Z80 with 4.7k
    pull-ups; D0-D7 IS the keyboard unit's internal data bus, driven by it except while the Z80
    reads
  * TEST* (pin 23: floats the keyboard unit's buses), RAS* CAS* MUX (the EI's DRAM timing) are not
    connected; the card's RAM is in the RP

Circuit provenance: the RP2354B core, its regulator corner (Raspberry Pi's minimal design, MIT, on the
QFN-80) and the rp-core drawing are FujiNet-StudioII / O2 Rev0's; the ESP32-S3 half and the USB-C
(USBLC6-2SC6, CP2102N with the datasheet's 1k RSTb pull-up) are the sibling carts'; the '245 symbol
and the gate drawing FujiNet-ColecoVision Rev0's.
"""

LIB = 'FujiNet-TRS80M1'
PROJECT = 'FujiNet-TRS80M1-Rev0'
NC = None  # explicit no-connect

SHEETS = [  # (file stem, title, page) -- in signal-flow order, the Model I side first
    ('m1-bus', 'Model I bus: ribbon header, LVC buffers, RP2354B GPIO', 2),
    ('rp-core', 'RP2354B core, crystal, RUN, SWD', 3),
    ('fujinet', 'FujiNet (ESP32-S3), microSD', 4),
    ('usb', 'USB-C + CP2102N', 5),
    ('power', 'Power: fuse, S3 buck, RP LDO', 6),
]
SHEET_ORDER = [s[0] for s in SHEETS]

# ---- RP2354B (QFN-80) GPIO -> package pin ---------------------------------
# Read from KiCad's MCU_RaspberryPi:RP2354B symbol (as FujiNet-StudioII Rev0); gen_sch.py re-checks
# every entry against the symbol's pin names before writing a sheet.
RP_GPIO_PIN = {0: 77, 1: 78, 2: 79, 3: 80, 4: 1, 5: 2, 6: 3, 7: 4, 8: 6, 9: 7, 10: 8, 11: 9,
               12: 11, 13: 12, 14: 13, 15: 14, 16: 16, 17: 17, 18: 18, 19: 19, 20: 20, 21: 21,
               22: 22, 23: 23, 24: 25, 25: 26, 26: 27, 27: 28, 28: 36, 29: 37, 30: 38, 31: 39,
               32: 40, 33: 42, 34: 43, 35: 44, 36: 45, 37: 46, 38: 47, 39: 48, 40: 49, 41: 52,
               42: 53, 43: 54, 44: 55, 45: 56, 46: 57, 47: 58}
RP_IOVDD_PINS = [5, 15, 24, 29, 41, 50, 60, 76]
RP_DVDD_PINS = [10, 32, 51]
RP_RAIL = '+3V3_RP'   # IOVDD x8, QSPI_IOVDD, USB_OTP_VDD, ADC_AVDD, VREG_VIN, the bus buffers
RP_IO_RAIL = RP_CORE_RAIL = RP_RAIL     # (FujiNet-StudioII Rev0's names for it, in the ported core)
S3_RAIL = '+3V3'      # the TLV62569 buck: ESP32-S3, CP2102N, microSD

# ---- the expansion edge, in Tandy's numbering (Tech Ref p.91 + Fig. 22) -----------------------------
# edge pin -> (net, symbol pin name); NC = not connected on this card
TANDY_EDGE = {1: (NC, '~{RAS}'), 2: ('M1_SYSRES_N', '~{SYSRES}'), 3: (NC, '~{CAS}'), 4: ('M1_A10', 'A10'),
        5: ('M1_A12', 'A12'), 6: ('M1_A13', 'A13'), 7: ('M1_A15', 'A15'), 8: ('GND', 'GND'),
        9: ('M1_A11', 'A11'), 10: ('M1_A14', 'A14'), 11: ('M1_A8', 'A8'), 12: ('M1_OUT_N', '~{OUT}'),
        13: ('M1_WR_N', '~{WR}'), 14: ('M1_INTAK_N', '~{INTAK}'), 15: ('M1_RD_N', '~{RD}'), 16: (NC, 'MUX'),
        17: ('M1_A9', 'A9'), 18: ('M1_D4', 'D4'), 19: ('M1_IN_N', '~{IN}'), 20: ('M1_D7', 'D7'),
        21: ('M1_INT_N', '~{INT}'), 22: ('M1_D1', 'D1'), 23: (NC, '~{TEST}'), 24: ('M1_D6', 'D6'),
        25: ('M1_A0', 'A0'), 26: ('M1_D3', 'D3'), 27: ('M1_A1', 'A1'), 28: ('M1_D5', 'D5'), 29: ('GND', 'GND'),
        30: ('M1_D0', 'D0'), 31: ('M1_A4', 'A4'), 32: ('M1_D2', 'D2'), 33: ('M1_WAIT_N', '~{WAIT}'),
        34: ('M1_A3', 'A3'), 35: ('M1_A5', 'A5'), 36: ('M1_A7', 'A7'), 37: ('GND', 'GND'), 38: ('M1_A6', 'A6'),
        39: (NC, '+5V/GND'), 40: ('M1_A2', 'A2')}
assert sorted(TANDY_EDGE) == list(range(1, 41))


def edge_of_hdr(h):
    """The Tandy edge pin a straight 40-wire IDC ribbon brings to header pin h: the pairs swapped.

    Fig. 22 numbers the edge as the MIRROR of a standard IDC card-edge connector (Buzbee / Fosdick,
    the 26-1132 adapter document: "configured opposite to other connectors on the expansion
    interface"; plugged Tandy's way, stripe right and cable down, wire 1 meets pin 39).  With the
    connector turned over, stripe at the end of Tandy's pins 1-2, wire 1 meets pin 2 and wire 2 pin 1.
    TRS-IO M1 v1.4 numbers its own edge pads the same way (pad 1 SYSRES*, pad 2 RAS*).
    """
    return h + 1 if h % 2 else h - 1


# header pin -> (net, symbol pin name): what J_M1 carries
EDGE = {h: TANDY_EDGE[edge_of_hdr(h)] for h in range(1, 41)}
EDGE_PIN = {n: p for p, (n, _) in EDGE.items() if n and n != 'GND'}

# ---- the buffers: every line in, every driven line out, at the header -------------------------
# '245 channel k: A pin 2 + k, B pin 18 - k.  Channels follow the lines' order along the header, so
# each buffer's inputs leave the header without crossing.  On the board the header lies along the west
# edge with pin 1 at its south end; the address '245s face it with their A side (pin 2, channel 0, at
# the north end), the data '245 turned round with its B side (pin 18, channel 0, at the south end).
CH245 = [(2 + k, 18 - k) for k in range(8)]
# (sorted by header pin: the address groups from the north end, the data group from the south)
ADDR_HI = sorted(['M1_A%d' % i for i in range(8, 16)], key=lambda n: -EDGE_PIN[n])   # header pins 18-3
ADDR_LO = sorted(['M1_A%d' % i for i in range(8)], key=lambda n: -EDGE_PIN[n])       # header pins 39-26
DATA = sorted(['M1_D%d' % i for i in range(8)], key=lambda n: EDGE_PIN[n])           # header pins 17-31
# 74LVC3G17 (DCT): (input pin, output pin) per Schmitt channel: 1A->1Y, 2A->2Y, 3A->3Y
CH3G17 = [(1, 7), (3, 5), (6, 2)]
STROBE_A = ['M1_SYSRES_N', 'M1_OUT_N', 'M1_WR_N']     # header pins 1, 11, 14
STROBE_B = ['M1_RD_N', 'M1_IN_N', 'M1_INTAK_N']       # header pins 16, 20, 13 (RD, IN on top: the OE gate taps them)
# 74LVC2G07: (input, open-drain output)
CH2G07 = [(1, 6), (3, 4)]

rp_of = lambda n: 'RP_' + n[3:]          # M1_A0 -> RP_A0 (the RP's side of a buffered line)
ds_of = lambda n: 'M1_DS' + n[4:]        # M1_D0 -> M1_DS0 (the data line between its series R and the '245)

# GPIO map (m1_card.h): (RP-side net, GPIO)
RP_LINES = ([('RP_A%d' % i, i) for i in range(16)] + [('RP_D%d' % i, 16 + i) for i in range(8)] +
            [('RP_WR_N', 24), ('RP_RD_N', 25), ('RP_IN_N', 26), ('RP_OUT_N', 27), ('DRIVE', 28),
             ('RP_SYSRES_N', 29), ('RP_INT_N', 30), ('RP_WAIT_N', 31), ('RP_INTAK_N', 32),
             ('DIP_RAM', 33), ('DIP_EI', 34), ('DIP_RS232', 35)])
RP_GPIO_NET = {g: NC for g in RP_GPIO_PIN}
RP_GPIO_NET.update({g: n for n, g in RP_LINES})
RP_GPIO_NET.update({44: 'DBG_TX', 45: 'DBG_RX', 47: 'RP_LED'})
assert len(RP_GPIO_NET) == 48 and set(RP_GPIO_NET) == set(RP_GPIO_PIN)
# the RP's GPIOs in five symbol units on the m1-bus sheet, one per buffer group (the order on each is
# sch_layout's): A8-A15, A0-A7, D0-D7 + DRIVE, the strobes + INT / WAIT, and the rest
GPIO_OF = {n: g for n, g in RP_LINES}
RP_UNIT_GPIOS = {1: [GPIO_OF[rp_of(n)] for n in ADDR_HI], 2: [GPIO_OF[rp_of(n)] for n in ADDR_LO],
                 3: [GPIO_OF[rp_of(n)] for n in DATA] + [GPIO_OF['DRIVE']],
                 4: [GPIO_OF[rp_of(n)] for n in STROBE_B + STROBE_A] + [GPIO_OF['RP_INT_N'], GPIO_OF['RP_WAIT_N']]}
RP_UNIT_GPIOS[5] = [g for g in sorted(RP_GPIO_PIN) if not any(g in v for v in RP_UNIT_GPIOS.values())]
RP_CORE_UNIT = 6
# the hot signals sit in GPIO0-31, one sio_hw->gpio_in read (m1_card.h)
assert all(g < 32 for n, g in RP_LINES if n.startswith('RP_') and n != 'RP_INTAK_N')

# ESP32-S3-WROOM-1 module pad -> function (pads per the KiCad symbol)
S3_PAD = {'GND': [1, 40, 41], '3V3': 2, 'EN': 3, 'IO4': 4, 'IO5': 5, 'IO6': 6,
          'IO7': 7, 'IO15': 8, 'IO16': 9, 'IO17': 10, 'IO18': 11, 'IO8': 12,
          'IO19': 13, 'IO20': 14, 'IO3': 15, 'IO46': 16, 'IO9': 17, 'IO10': 18,
          'IO11': 19, 'IO12': 20, 'IO13': 21, 'IO14': 22, 'IO21': 23,
          'IO47': 24, 'IO48': 25, 'IO45': 26, 'IO0': 27, 'IO35': 28,
          'IO36': 29, 'IO37': 30, 'IO38': 31, 'IO39': 32, 'IO40': 33,
          'IO41': 34, 'IO42': 35, 'RXD0': 36, 'TXD0': 37, 'IO2': 38, 'IO1': 39}
# include/pinmap/fujiversal-trs80m1.h (SD 38-41, UART0 43/44, LED strip 48; the RP link is the S3's own
# USB, IO19 / IO20) + the fujiversal RUN / BOOTSEL forcing pins (IO4 / IO5) and SD card detect on
# IO42, as every on-cart S3 board (README "Firmware changes": the pin map lacks them)
S3_NET = {'EN': 'S3_EN', 'IO0': 'S3_IO0', 'IO4': 'RUN_CTL', 'IO5': 'BOOTSEL_CTL',
          'IO19': 'USB_DM', 'IO20': 'USB_DP', 'IO38': 'SD_MOSI', 'IO39': 'SD_SCK',
          'IO40': 'SD_MISO', 'IO41': 'SD_CS', 'IO42': 'SD_CD', 'IO48': 'LED_STRIP',
          'RXD0': 'S3_RXD', 'TXD0': 'S3_TXD'}

# ---- common parts: footprint, (MPN, LCSC) ----------------------------------
FP = lambda n: '%s:%s' % (LIB, n)
R0603 = FP('R_0603_1608Metric')
R0402 = FP('RPI_R0402')
C0603 = FP('C_0603_1608Metric')
C0805 = FP('C_0805_2012Metric')
HDR_FP = 'IDC-Header_2x20_P2.54mm_Horizontal_BH254R-40P'
RES = {'27R': ('0603WAF270JT5E', 'C25190'), '330R': ('0603WAF3300T5E', 'C23138'),
       '680R': ('0603WAF6800T5E', 'C23228'), '1k': ('0603WAF1001T5E', 'C21190'),
       '4.7k': ('0603WAF4701T5E', 'C23162'), '5.1k': ('0603WAF5101T5E', 'C23186'),
       '10k': ('0603WAF1002T5E', 'C25804'), '22k': ('0603WAF2202T5E', 'C31850'),
       '47k': ('0603WAF4702T5E', 'C25819'), '100k': ('0603WAF1003T5E', 'C25803')}
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
RPACK = {'4x10k': ('4D03WGJ0103T5E', 'C29718'), '4x100k': ('4D03WGJ0104T5E', 'C1996'),
         '4x75R': ('4D03WGJ0750T5E', 'C25514')}

# MPN -> manufacturer (names from LCSC's / JLCPCB's pages)
MFR = {'RP2354B': 'Raspberry Pi', 'CC0603KRX7R9BB104': 'YAGEO', 'CL10A106KP8NNNC': 'Samsung Electro-Mechanics',
       'CL10A475KO8NNNC': 'Samsung Electro-Mechanics', 'CL10C150JB8NNNC': 'Samsung Electro-Mechanics',
       'CL10A105KB8NNNC': 'Samsung Electro-Mechanics', 'CL21A226MAQNNNE': 'Samsung Electro-Mechanics',
       'CL05B104KO5NNNC': 'Samsung Electro-Mechanics', 'CL05A475MP5NRNC': 'Samsung Electro-Mechanics',
       'AOTA-B201610S3R3-101-T': 'Abracon', 'ABM8-272-T3': 'Abracon', 'TS-1187A-B-A-B': 'XKB Connection',
       'KT-0603R': 'Hubei KENTO Elec', 'TYPE-C-31-M-12': 'Korean Hroparts Elec',
       'AP2112K-3.3TRG1': 'Diodes Incorporated', 'TLV62569DBVR': 'Texas Instruments',
       'ESP32-S3-WROOM-1-N16R8': 'Espressif', 'TF-015': 'SOFNG', 'WS2812B-2020-V6': 'Worldsemi',
       '4D03WGJ0103T5E': 'UNI-ROYAL', '4D03WGJ0104T5E': 'UNI-ROYAL', '4D03WGJ0750T5E': 'UNI-ROYAL',
       'CP2102N-A02-GQFN28R': 'Silicon Labs', 'UMH3N': 'Jiangsu Changjing (JSCJ)',
       'USBLC6-2SC6': 'STMicroelectronics', 'BAT54C,215': 'Nexperia', 'SWPA4030S2R2MT': 'Sunlord',
       'SN74LVC245APWR': 'Texas Instruments', 'SN74LVC3G17DCTR': 'Texas Instruments',
       'SN74LVC1G11DBVR': 'Texas Instruments', 'SN74LVC2G07DCKR': 'Texas Instruments',
       'SMD1206B110TFT': 'Brightking', 'BH254R-40P': 'XFCN', '2.54-3P TPGT': 'SHOU HAN'}
for _v in list(RES.values()) + list(RES0402.values()):
    MFR.setdefault(_v[0], 'UNI-ROYAL')

# 1G11: ((inputs), output) per gate -- for sch_layout.gate()
GATE_PINS = {'74LVC1G11': [((1, 3, 6), 4)]}


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
    drawn on its line: nets[0..3] on pins 1-4, common on 5-8 (a None line leaves that resistor's
    pin 1-4 end open; its other end still sits on the common net)."""
    mpn, lcsc = RPACK[value]
    pins = {i + 1: n for i, n in enumerate(nets)}
    pins.update({8 - i: common for i in range(4)})
    return add('RN', 'Device:R_Pack04_Split', value, FP('R_Array_Convex_4x0603'), pins, mpn=mpn, lcsc=lcsc,
               desc=desc, **k)


def RS(value, pairs, desc='', **k):
    """4 series resistors in one array: pairs[k] = (pin k+1 net, pin 8-k net)."""
    mpn, lcsc = RPACK[value]
    pins = {}
    for i, (a, b) in enumerate(pairs):
        pins[i + 1], pins[8 - i] = a, b
    return add('RN', 'Device:R_Pack04_Split', value, FP('R_Array_Convex_4x0603'), pins, mpn=mpn, lcsc=lcsc,
               desc=desc, **k)


def SW(value, net, desc, **k):
    # XKB TS-1187A-B-A-B (JLCPCB basic C318884), as FujiNet-StudioII / 5200 / 7800 / SMS / O2 Rev0
    return add('SW', 'Switch:SW_Push', value, FP('SW_SPST_TS-1187A'), {1: net, 2: 'GND'},
               mpn='TS-1187A-B-A-B', lcsc='C318884', desc=desc, **k)


def TP(net, label, desc='test pad', **k):
    return add('TP', 'Connector:TestPoint', label, FP('TestPoint_Pad_D1.5mm'), {1: net},
               desc=desc, bom=False, **k)


TI_245 = 'https://www.ti.com/lit/ds/symlink/sn74lvc245a.pdf'
TI_3G17 = 'https://www.ti.com/lit/ds/symlink/sn74lvc3g17.pdf'

# =========================================================================
sheet('m1-bus')
# -- the RP2354B (two units: GPIO here, the core on rp-core).  Declared first: the routers find it
# as U1.  Every RP supply pin and every bus buffer on +3V3_RP.
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
           mpn='RP2354B', lcsc='C39843328', desc='RP2350B + 2MB flash in package; serves the Model I bus',
           key='U_RP', ds='https://datasheets.raspberrypi.com/rp2350/rp2350-datasheet.pdf')
# drawn in six units (gen_sch.rp_split_symbol): five on the m1-bus sheet, each beside the buffer group
# it serves (RP_UNIT_GPIOS), and the core -- supplies, core regulator, crystal, RUN, SWD, USB, QSPI --
# on rp-core
U_RP.unit_sheets = {u: 'm1-bus' for u in RP_UNIT_GPIOS}
U_RP.unit_sheets[RP_CORE_UNIT] = 'rp-core'
_gp_unit = {g: u for u, gs in RP_UNIT_GPIOS.items() for g in gs}
U_RP.pin_unit = {str(pad): RP_CORE_UNIT for pad in rp}
U_RP.pin_unit.update({str(RP_GPIO_PIN[g]): u for g, u in _gp_unit.items()})

# -- the header: a right-angle shrouded 2x20 box header (keyed); the ribbon's IDC socket mates it,
# a 40-way card-edge IDC on the ribbon's other end takes the keyboard unit's edge
add('J', '%s:TRS80_M1_Expansion_40' % LIB, 'TRS-80 Model I expansion', FP(HDR_FP),
    {p: n for p, (n, _) in EDGE.items()}, mpn='BH254R-40P', lcsc='C48603651',
    desc='2x20 right-angle box header, 2.54 mm: the Model I expansion edge through a 40-wire IDC ribbon '
         '(edge pins swapped in pairs: header 1 = edge 2 SYSRES*); edge pin 39 (+5V on boards A-E, GND on G) '
         'left open', key='J_M1')

# -- A8-A15 and A0-A7: 74LVC245A, A -> B fixed (DIR high, OE low), each input pulled up by 100k to
# +3V3_RP: defined with the ribbon unplugged or the Model I off, idling where a TTL bus does (the
# strobes and SYSRES* inactive).  With the Model I on and the card off they back-feed the RP rail
# ~1 mA at most (tools/audit/margins.py); the LVC inputs themselves are Ioff
for key, lines, pd_keys, desc in (('U_AH', ADDR_HI, ('RN_AH1', 'RN_AH2'), 'A8-A15'),
                                  ('U_AL', ADDR_LO, ('RN_AL1', 'RN_AL2'), 'A0-A7')):
    pins = {1: RP_RAIL, 10: 'GND', 19: 'GND', 20: RP_RAIL}
    for (a, b), n in zip(CH245, lines):
        pins[a], pins[b] = n, rp_of(n)
    add('U', '%s:74LVC245A_Fn' % LIB, '74LVC245A', FP('TSSOP-20_4.4x6.5mm_P0.65mm'), pins,
        mpn='SN74LVC245APWR', lcsc='C7848', desc='address receiver %s (A -> B, always on)' % desc, key=key, ds=TI_245)
    C('100nF', RP_RAIL, desc='%s decoupling' % key, key='C_' + key[2:])
    for i, pk in enumerate(pd_keys):
        RN('4x100k', lines[4 * i:4 * i + 4], RP_RAIL, desc='%s pull-ups (ribbon unplugged)' % desc, key=pk)

# -- D0-D7: 74LVC245A, A = the RP, B = the bus through 75R: source termination for the ribbon (tools/audit/
# spice/ribbon.py: clean to 45 cm of cable) and the limit on the overlap current when RD rises and the
# keyboard unit's buffers take the bus back (~31 mA for <= 52 ns: tools/audit/margins.py).
# DIR = DRIVE (GP28; 1 = A -> B = onto the bus), 4.7k pull-down (under RP2350-E9's 8.2k): the buffer
# faces the RP through reset.  OE* = DRIVE . RD* . IN* (74LVC1G11, from the BUFFERED strobes): with
# DRIVE low it always listens (the RP sees write data), with DRIVE high it drives only while a read
# strobe is low, and lets go at the strobe's rising edge whatever core1 is doing.
pins = {1: 'DRIVE', 10: 'GND', 19: 'BUF_OE_N', 20: RP_RAIL}
for (a, b), n in zip(CH245, DATA):
    pins[a], pins[b] = rp_of(n), ds_of(n)
add('U', '%s:74LVC245A_Fn_BA' % LIB, '74LVC245A', FP('TSSOP-20_4.4x6.5mm_P0.65mm'), pins,
    mpn='SN74LVC245APWR', lcsc='C7848', desc='data transceiver D0-D7 (DIR = DRIVE, OE* = DRIVE.RD*.IN*)',
    key='U_DB', ds=TI_245)
C('100nF', RP_RAIL, desc='U_DB decoupling', key='C_DB')
RS('4x75R', [(n, ds_of(n)) for n in DATA[:4]], desc='data series (ribbon source termination)', key='RS_D1')
RS('4x75R', [(n, ds_of(n)) for n in DATA[4:]], desc='data series (ribbon source termination)', key='RS_D2')
RN('4x100k', [ds_of(n) for n in DATA[:4]], RP_RAIL, desc='data pull-ups (ribbon unplugged)', key='RN_D1')
RN('4x100k', [ds_of(n) for n in DATA[4:]], RP_RAIL, desc='data pull-ups (ribbon unplugged)', key='RN_D2')
R('4.7k', 'DRIVE', 'GND', desc='DRIVE pull-down: the data buffer listens through reset', key='R_DRIVE')
add('U', '74xGxx:74LVC1G11', '74LVC1G11', FP('SOT-23-6'),
    {6: 'DRIVE', 2: 'GND', 1: 'RP_RD_N', 4: 'BUF_OE_N', 5: RP_RAIL, 3: 'RP_IN_N'},
    mpn='SN74LVC1G11DBVR', lcsc='C22046', desc="data buffer OE* = DRIVE . RD* . IN*", key='U_OE',
    ds='https://www.ti.com/lit/ds/symlink/sn74lvc1g11.pdf')
C('100nF', RP_RAIL, desc='74LVC1G11 decoupling', key='C_OE')

# -- the strobes, SYSRES* and INTAK*: Schmitt-trigger receivers (74LVC3G17, hysteresis ~0.5 V at 3.3 V)
# against ringing and crosstalk on the ribbon; 100k pull-ups (no strobe = no Model I: the firmware's
# power-off rule)
for key, lines, pd in (('U_STA', STROBE_A, 'RN_STA'), ('U_STB', STROBE_B, 'RN_STB')):
    pins = {4: 'GND', 8: RP_RAIL}
    for (a, y), n in zip(CH3G17, lines):
        pins[a], pins[y] = n, rp_of(n)
    add('U', '%s:74LVC3G17_Fn' % LIB, '74LVC3G17', FP('SSOP-8_2.95x2.8mm_P0.65mm'), pins,
        mpn='SN74LVC3G17DCTR', lcsc='C18213', desc='Schmitt receivers: ' + ', '.join(n[3:] for n in lines),
        key=key, ds=TI_3G17)
    C('100nF', RP_RAIL, desc='%s decoupling' % key, key='C_' + key[2:])
RN('4x100k', STROBE_A + [None], RP_RAIL, desc='strobe pull-ups (ribbon unplugged)', key='RN_STA')
RN('4x100k', STROBE_B + [None], RP_RAIL, desc='strobe pull-ups (ribbon unplugged)', key='RN_STB')

# -- INT* and WAIT*: open drain (74LVC2G07, 5 V-tolerant outputs) onto the Z80's own 4.7k pull-ups;
# the inputs pulled up so the outputs stay off while the RP is in reset
add('U', '%s:74LVC2G07_Fn' % LIB, '74LVC2G07', FP('SOT-363_SC-70-6'),
    {1: 'RP_INT_N', 2: 'GND', 3: 'RP_WAIT_N', 4: 'M1_WAIT_N', 5: RP_RAIL, 6: 'M1_INT_N'},
    mpn='SN74LVC2G07DCKR', lcsc='C7849', desc='INT* / WAIT* open-drain drivers', key='U_OD',
    ds='https://www.ti.com/lit/ds/symlink/sn74lvc2g07.pdf')
C('100nF', RP_RAIL, desc='74LVC2G07 decoupling', key='C_OD')
R('10k', RP_RAIL, 'RP_INT_N', desc='INT driver input pull-up (off through reset)', key='R_INTPU')
R('10k', RP_RAIL, 'RP_WAIT_N', desc='WAIT driver input pull-up (off through reset)', key='R_WAITPU')
C('10uF', RP_RAIL, desc='bus-buffer bulk (+3V3_RP)', key='C_BUFBULK')

# -- the DIP switches: closed forces a block off (m1_card.h M1_PIN_DIP0, GP33-35), 10k pull-ups
add('SW', 'Switch:SW_DIP_x03', 'RAM EI RS232', FP('SW_DIP_SPSTx03_SMD_P2.54mm_HX'),
    {1: 'DIP_RAM', 2: 'DIP_EI', 3: 'DIP_RS232', 4: 'GND', 5: 'GND', 6: 'GND'},
    mpn='2.54-3P TPGT', lcsc='C7421520', desc='force off: RAM / EI / RS-232 (ON = off, for a machine with its own)',
    key='SW_DIP')
RN('4x10k', ['DIP_RAM', 'DIP_EI', 'DIP_RS232', None], RP_RAIL, desc='DIP pull-ups', key='RN_DIP')

# -- the logic-analyser header (not fitted): every buffered strobe and the bus controls, a ground
# beside each, for a 2x10 probe lead (README "Bring-up")
LA = ['RP_RD_N', 'RP_WR_N', 'RP_IN_N', 'RP_OUT_N', 'RP_SYSRES_N', 'RP_INTAK_N', 'DRIVE', 'BUF_OE_N',
      'RP_INT_N', 'RP_WAIT_N']
la = {2 * i + 1: n for i, n in enumerate(LA)}
la.update({2 * i + 2: 'GND' for i in range(10)})
add('J', '%s:LA_Probe_2x10' % LIB, 'LA probe', FP('PinHeader_2x10_P2.54mm_Vertical'), la,
    desc='logic-analyser header (DNP): the buffered strobes, DRIVE, OE*, INT, WAIT; even pins GND',
    bom=False, dnp=True, key='J_LA')

# activity LED on GP47 (m1_card.h M1_PIN_LED); red, so a 3.3 V pin lights it (~2 mA)
R('680R', 'RP_LED', 'RP_LED_A', desc='LED series (~2 mA)', key='R_LED')
add('D', 'Device:LED', 'red', FP('LED_0603_1608Metric'), {1: 'GND', 2: 'RP_LED_A'},
    mpn='KT-0603R', lcsc='C2286', desc='RP activity LED (GP47)', key='D_LED')
TP('DBG_TX', 'DBG_TX', desc='test pad: GP44, debug UART TX (3.3 V)', key='TP_DBGTX')
TP('DBG_RX', 'DBG_RX', desc='test pad: GP45, debug UART RX (3.3 V)', key='TP_DBGRX')

# =========================================================================
sheet('rp-core')
# 0402 where a pin's neighbours leave no room for an 0603 straight out of it (IOVDD 50 / DVDD 51,
# between GPIO39 and GPIO40: Raspberry Pi's 0402 land, the corner's own 100 nF part)
NARROW = (50, 51)
for pin in RP_IOVDD_PINS:      # one 100 nF per IOVDD pin; the key names the pin it sits on
    C('100nF/0402' if pin in NARROW else '100nF', RP_IO_RAIL, desc='IOVDD decoupling (pin %d)' % pin,
      key='C_IOV%d' % pin)
C('100nF', RP_IO_RAIL, desc='QSPI_IOVDD decoupling', key='C_QSPI')
C('100nF/0402', RP_IO_RAIL, desc='USB_OTP_VDD decoupling', key='C_OTP')
C('100nF', RP_IO_RAIL, desc='ADC_AVDD decoupling', key='C_ADC')
C('10uF', RP_IO_RAIL, desc='RP rail bulk (LDO output, at the RP)', key='C_IOBULK')
C('4.7uF/0402w', RP_CORE_RAIL, desc='VREG_VIN input (C_IN, at the pins)', key='C_VREGIN')
for pin in RP_DVDD_PINS:
    C('100nF/0402' if pin in NARROW else '100nF', 'DVDD', desc='DVDD decoupling (pin %d)' % pin, key='C_DV%d' % pin)
C('4.7uF/0402w', 'DVDD', desc='core regulator output (C_OUT)', key='C_DVBULK')
R4('33R', RP_CORE_RAIL, 'VREG_AVDD', desc='VREG_AVDD filter', key='R_AVDD')
C('4.7uF/0402', 'VREG_AVDD', desc='VREG_AVDD filter', key='C_AVDD')
add('L', 'Device:L', '3.3uH', FP('RPI_L_AOTA-B201610S3R3'), {1: 'DVDD', 2: 'RP_LX'},
    mpn='AOTA-B201610S3R3-101-T', lcsc='C42411119', desc='RP2350 core SMPS inductor (polarity marked)', key='L_RP')
# 12 MHz crystal (minimal design: ABM8-272-T3, 15 pF loads, 1k in XOUT)
add('Y', 'Device:Crystal_GND24', '12MHz', FP('Crystal_SMD_3225-4Pin_3.2x2.5mm'),
    {1: 'XIN', 2: 'GND', 3: 'XOUT_Y', 4: 'GND'}, mpn='ABM8-272-T3', lcsc='C20625731', desc='RP2350 12 MHz crystal',
    key='Y_RP')
C('15pF', 'XIN', desc='crystal load', key='C_XIN')
C('15pF', 'XOUT_Y', desc='crystal load', key='C_XOUT')
R('1k', 'XOUT', 'XOUT_Y', desc='crystal drive limit', key='R_XOUT')
# RUN / BOOTSEL: the buttons, and the S3 (fnPicoUpdater::forceBootselViaPins(): its pins idle as
# inputs and are driven LOW to assert).  Both chips on 3.3 V rails: a 1k series resistor is the
# whole interface, as on FujiNet-ChannelF Rev0.
R('10k', RP_IO_RAIL, 'RUN', desc='RUN pull-up', key='R_RUN')
R('1k', 'RUN_CTL', 'RUN', desc='S3 IO4 -> RP RUN (drive low = reset)', key='R_RUNCTL')
R('10k', RP_IO_RAIL, 'QSPI_SS', desc='QSPI_SS pull-up', key='R_SS')
R('1k', 'QSPI_SS', 'BOOTSEL_BTN', desc='BOOTSEL button series', key='R_BSEL')
SW('BOOTSEL', 'BOOTSEL_BTN', 'RP2354B BOOTSEL (hold while pressing RESET)', key='SW_BOOTSEL')
R('1k', 'BOOTSEL_CTL', 'QSPI_SS', desc='S3 IO5 -> RP QSPI_SS (low through reset = BOOTSEL)', key='R_BSELCTL')
# RESET resets both MCUs: the button pulls RP RUN and S3 EN low through a common-cathode pair, so
# neither chip's reset drives the other's.  It does not reset the Model I (its own RESET is an NMI).
SW('RESET', 'RST_BTN', 'card RESET: RP RUN + S3 EN through the BAT54C', key='SW_RESET')
add('D', 'Diode:BAT54C', 'BAT54C', FP('SOT-23'), {1: 'RUN', 2: 'S3_EN', 3: 'RST_BTN'},
    mpn='BAT54C,215', lcsc='C37704', desc='RESET steering, common cathode', key='D_RST')
# RP <-> S3 native USB (RP = CDC device, S3 = host), on the board: 27R series at the RP
R4('27R', 'USB_DP', 'RP_USB_DP', desc='USB series', key='R_USBP')
R4('27R', 'USB_DM', 'RP_USB_DM', desc='USB series', key='R_USBM')
# SWD (first flash: the RP's USB only reaches the S3) + a GND pad beside it, RUN and DVDD pads
TP('SWCLK', 'SWCLK', key='TP_SWCLK')
TP('SWDIO', 'SWDIO', key='TP_SWDIO')
TP('GND', 'GND', key='TP_GND')
TP('RUN', 'RUN', key='TP_RUN')
TP('DVDD', 'DVDD', desc='bring-up pad: RP core rail', key='TP_DVDD')

# =========================================================================
sheet('fujinet')
s3 = {}
for fn, pad in S3_PAD.items():
    for p in (pad if isinstance(pad, list) else [pad]):
        s3[p] = 'GND' if fn == 'GND' else '+3V3' if fn == '3V3' else S3_NET.get(fn, NC)
add('U', '%s:ESP32-S3-WROOM-1_Fn' % LIB, 'ESP32-S3-WROOM-1-N16R8', FP('ESP32-S3-WROOM-1'), s3,
    mpn='ESP32-S3-WROOM-1-N16R8', lcsc='C2913202', desc='FujiNet core (fujiversal-trs80m1)', key='U_S3')
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
# TF-015 card-detect: open with no card, closed to the shell (GND) with a card in
R('10k', '+3V3', 'SD_CD', desc='card-detect pull-up (low = card present)', key='R_SDCD')
C('10uF', '+3V3', desc='microSD supply', key='C_SD')
# WS2812B-2020-V6 datasheet: VDD +3.7..+5.3 V (NOT a 3.3 V part), VIH min 2.7 V:
# it runs on +5V and takes the S3's 3.3 V data directly
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
    mpn='TYPE-C-31-M-12', lcsc='C165948', desc='the card\'s only power + S3 programming / console', key='J_USB')
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
# The Model I's edge carries no usable supply (pin 39 is +5V only on boards A-E, and Tandy warns
# off it): the card runs from USB-C alone.  VBUS -> a 1.1 A resettable fuse -> +5V.
add('F', 'Device:Polyfuse', '1.1A', FP('Fuse_1206_3216Metric'), {1: 'VBUS', 2: '+5V'},
    mpn='SMD1206B110TFT', lcsc='C269119', desc='VBUS resettable fuse, 1.1 A hold / 2.2 A trip', key='F_VBUS')
C('22uF', '+5V', desc='+5V bulk (after the fuse; buck and LDO input)', key='C_5VBULK')
# the S3 side's 3.3 V: TLV62569, 2 A synchronous buck, 2.5-5.5 V in; VOUT = 0.6 V x (1 + 100k / 22k)
# = 3.33 V; datasheet Table 4's standard 2.2 uH / 10-22 uF output
C('10uF', '+5V', desc='buck input (datasheet C1 >= 4.7 uF)', key='C_BIN')
C('100nF', '+5V', desc='buck input HF', key='C_BINHF')
add('U', 'Regulator_Switching:TLV62569DBV', 'TLV62569DBV', FP('SOT-23-5'),
    {1: '+5V', 2: 'GND', 3: 'BUCK_SW', 4: '+5V', 5: 'BUCK_FB'},
    mpn='TLV62569DBVR', lcsc='C141836', desc='3.3V 2A buck (S3, SD, CP2102N)', key='U_BUCK',
    ds='https://www.ti.com/lit/ds/symlink/tlv62569.pdf')
add('L', 'Device:L', '2.2uH', FP('L_Sunlord_SWPA4030S'), {1: 'BUCK_SW', 2: '+3V3'},
    mpn='SWPA4030S2R2MT', lcsc='C36409', desc='buck inductor (datasheet: 2.2 uH)', key='L_BUCK')
R('100k', '+3V3', 'BUCK_FB', desc='buck feedback (R1)', key='R_FBH')
R('22k', 'BUCK_FB', 'GND', desc='buck feedback (R2): 0.6 x (1 + 100/22) = 3.33 V', key='R_FBL')
C('22uF', '+3V3', desc='buck output', key='C_BOUT1')
C('22uF', '+3V3', desc='buck output', key='C_BOUT2')
# RP rail: a fast LDO (AP2112K: ~20 us start-up) off +5V, so the RP and the bus buffers come up
# together and first
add('U', 'Regulator_Linear:AP2112K-3.3', 'AP2112K-3.3', FP('SOT-23-5'),
    {1: '+5V', 2: 'GND', 3: '+5V', 4: NC, 5: RP_RAIL},
    mpn='AP2112K-3.3TRG1', lcsc='C51118', desc='RP2354B + bus buffers 3.3V LDO, 600mA, fast start',
    key='U_LDO')
C('1uF', '+5V', desc='LDO input', key='C_LDOIN')
C('1uF', RP_RAIL, desc='LDO output', key='C_LDOOUT')
TP('VBUS', 'VBUS', desc='bring-up pad: USB VBUS', key='TP_VBUS')
TP('+5V', '+5V', desc='bring-up pad: +5V (after the fuse)', key='TP_5V')
TP(RP_RAIL, '+3V3_RP', desc='bring-up pad: +3V3_RP (RP LDO)', key='TP_3V3')
TP('+3V3', '+3V3', desc='bring-up pad: +3V3 (buck: S3 side)', key='TP_3V3S3')

# PWR_FLAGs: nets whose drivers are passive pins (VBUS the connector, +5V the fuse, +3V3 the inductor)
PWR_FLAG_NETS = ['GND', 'VBUS', '+5V', '+3V3', 'DVDD', 'VREG_AVDD']
# nets drawn as power symbols (global, never prefixed)
RAIL_NETS = ['GND', 'VBUS', '+5V', '+3V3', RP_RAIL, 'DVDD']

# ---- reference assignment (stable: declaration order) ---------------------
_count = {}
for p in PARTS:
    _count[p.prefix] = _count.get(p.prefix, 0) + 1
    p.ref = '%s%d' % (p.prefix, _count[p.prefix])

BY_REF = {p.ref: p for p in PARTS}
KEY = {p.key: p.ref for p in PARTS if p.key}
BY_KEY = {p.key: p for p in PARTS if p.key}
assert len(KEY) == len([p for p in PARTS if p.key]), 'duplicate part key'
assert BY_KEY['U_RP'].ref == 'U1', 'the RP must be U1 (finish_route / stitch_gnd)'


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
