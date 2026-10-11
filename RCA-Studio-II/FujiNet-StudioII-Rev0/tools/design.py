"""FujiNet-StudioII Rev0 (RP2354B + ESP32-S3) -- the single source of truth.

Every part, value, footprint, MPN, manufacturer, LCSC code and pin->net assignment lives here.
gen_sch.py, check_nets.py, check_glue.py and export.py import it; the KiCad files are generated
output.  Parts are addressed by `key` (the drawing, the audits); references are labels, numbered
in declaration order (sheet by sheet) unless tools/refs.lock pins them.

One cart, two MCUs, as on FujiNet-ChannelF Rev0: the RP2354B serves the console's bus, and the
ESP32-S3-WROOM-1 (the FujiNet, fujiversal-studio2) is its USB host over an on-board USB link, with a
microSD, a WS2812 status light and a CP2102N USB-C bridge for flashing it.  The S3 also holds the
RP2354B's RUN and BOOTSEL (IO4 / IO5, the fujiversal-intv pins), so it can re-flash it.

Circuit provenance: FujiNet-5200 Rev0 (this repository's ATARI-5200) for the RP2354B core, the
'541 data buffer, the PWR_OK and ADC senses, the debug header and the generators; FujiNet-ChannelF
Rev0 for the ESP32-S3 half (S3, microSD, WS2812, CP2102N, auto-program pair, 3.3 V buck, RESET
steering).  The cart side (edge, series resistors, '541 enables, CART CS NOR) is new; so is the
power mux (TPS2116: USB first, the console's 5 V second, ~20 mV drop either way).
Firmware contract:
  fujinet-firmware pico/studio2/firmware/include/s2_cart.h   (RP pins, s2_glue_drive, s2_glue_cartcs)
  include/pinmap/fujiversal-studio2.h (the S3: SD 38-41, UART0 43/44, WS2812 48, USB host 19/20);
      RUN / BOOTSEL forcing on IO4 / IO5 as fujiversal-intv.h declares them
The edge: EJK's Studio II schematic, Paul Robson's notes and the FliP multicart, as collected in
the bring-up plan; the geometry is FliP's multicart v5.1 board (tools/edge_geom.py, checked by
tools/audit/edge_orientation.py).
The RP2350 core-regulator corner (L_RP, C_VREGIN, C_DVBULK, R_AVDD / C_AVDD, the 27R, C_OTP) is
Raspberry Pi's minimal design (MIT, tools/RPI-MINIMAL-LICENSE.txt): its 0402 parts and its layout,
grafted onto the QFN-80 by gen_pcb.py, as on Fujiversal-Atari2600 Rev1.
"""

LIB = 'FujiNet-StudioII'
PROJECT = 'FujiNet-StudioII-Rev0'
NC = None  # explicit no-connect

SHEETS = [  # (file stem, title, page)
    ('cart-bus', "Cart bus: edge, glue, RP GPIO", 2),
    ('rp-core', 'RP2354B core, crystal, RUN, SWD', 3),
    ('fujinet', 'FujiNet (ESP32-S3), microSD', 4),
    ('usb', 'USB-C + CP2102N', 5),
    ('power', 'Power: mux, S3 buck, RP LDO', 6),
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
RP_IO_RAIL = '+3V3'        # IOVDD x8, QSPI_IOVDD, USB_OTP_VDD, ADC_AVDD: the RP's own LDO
RP_CORE_RAIL = RP_IO_RAIL  # VREG_VIN (+ VREG_AVDD through 33R) on the same LDO rail
S3_RAIL = '+3V3_S3'        # the AP63203 buck: ESP32-S3, CP2102N, microSD

# ESP32-S3-WROOM-1 module pad -> function (pads per the KiCad symbol)
S3_PAD = {'GND': [1, 40, 41], '3V3': 2, 'EN': 3, 'IO4': 4, 'IO5': 5, 'IO6': 6,
          'IO7': 7, 'IO15': 8, 'IO16': 9, 'IO17': 10, 'IO18': 11, 'IO8': 12,
          'IO19': 13, 'IO20': 14, 'IO3': 15, 'IO46': 16, 'IO9': 17, 'IO10': 18,
          'IO11': 19, 'IO12': 20, 'IO13': 21, 'IO14': 22, 'IO21': 23,
          'IO47': 24, 'IO48': 25, 'IO45': 26, 'IO0': 27, 'IO35': 28,
          'IO36': 29, 'IO37': 30, 'IO38': 31, 'IO39': 32, 'IO40': 33,
          'IO41': 34, 'IO42': 35, 'RXD0': 36, 'TXD0': 37, 'IO2': 38, 'IO1': 39}
# fujiversal-studio2.h (SD, UART0, LED strip; the RP link is the S3's own USB, IO19 / IO20) + the RUN /
# BOOTSEL forcing pins fujiversal-intv.h declares (IO4 / IO5); SD card-detect on IO42, as FujiNet-ChannelF
S3_NET = {'EN': 'S3_EN', 'IO0': 'S3_IO0', 'IO4': 'RUN_CTL', 'IO5': 'BOOTSEL_CTL',
          'IO19': 'USB_DM', 'IO20': 'USB_DP', 'IO38': 'SD_MOSI', 'IO39': 'SD_SCK',
          'IO40': 'SD_MISO', 'IO41': 'SD_CS', 'IO42': 'SD_CD', 'IO48': 'LED_STRIP',
          'RXD0': 'S3_RXD', 'TXD0': 'S3_TXD'}

# s2_cart.h.  GPIO0-31 are the 5 V-tolerant bus pins; GPIO40-47 are not and carry only the ADC
# sense and the 3.3 V debug header.  The console's lines reach the RP through 330R (RP_*).
RP_GPIO_NET = {i: 'RP_MA%d' % i for i in range(8)}                  # MA0_PIN 0: MA0-MA7
RP_GPIO_NET.update({8: 'RP_TPA', 9: 'RP_MRD'})                      # TPA_PIN, MRD_PIN
RP_GPIO_NET.update({g: NC for g in range(10, 16)})
RP_GPIO_NET.update({16 + i: 'RP_D%d' % i for i in range(8)})        # D0_PIN 16: into the '541
RP_GPIO_NET.update({24: 'DRIVE_N', 25: 'CLAIM_N', 26: 'PWR_OK', 27: 'RP_LED'})
RP_GPIO_NET.update({g: NC for g in range(28, 40)})
RP_GPIO_NET.update({40: 'VSENSE_ADC', 41: NC, 42: NC, 43: NC, 44: 'DBG_TX', 45: 'DBG_RX', 46: NC, 47: NC})
assert len(RP_GPIO_NET) == 48 and set(RP_GPIO_NET) == set(RP_GPIO_PIN)

# RCA Studio II 22-pin cartridge edge, 0.156" pitch, contacts on one face: (net, symbol pin name).
# The console's CN1 is a 2x22 connector whose lettered row is unconnected (EJK's schematic); a cart
# carries its 22 contacts on one face (FliP's multicart, the original board: tools/edge_geom.py).  Pin 6 is the console's ROM DISABLE: grounded, as a cart does, it removes the
# built-in games at $0400-$07FF.  Pin 19 is TPA gated by /MRD in the console: it pulses on memory
# reads only.  Pin 22 is the cart's CART CS output: high turns the console RAM off.
EDGE = {1: ('D7', 'D7'), 2: ('D6', 'D6'), 3: ('D5', 'D5'), 4: ('D4', 'D4'), 5: ('D3', 'D3'),
        6: ('GND', '~{ROM_DIS}'), 7: ('GND', 'GND'), 8: ('D2', 'D2'), 9: ('D1', 'D1'), 10: ('D0', 'D0'),
        11: ('MA0', 'MA0'), 12: ('MA1', 'MA1'), 13: ('MA2', 'MA2'), 14: ('MA3', 'MA3'),
        15: ('CONS_5V', '+5V'), 16: ('MA4', 'MA4'), 17: ('MA5', 'MA5'), 18: ('MA6', 'MA6'),
        19: ('TPA', 'TPA'), 20: ('MA7', 'MA7'), 21: ('MRD_N', '~{MRD}'), 22: ('CART_CS', 'CART_CS')}

# ---- common parts: (lib_id, footprint, MPN, LCSC) --------------------------
FP = lambda n: '%s:%s' % (LIB, n)
R0603 = FP('R_0603_1608Metric')
R0402 = FP('RPI_R0402')            # Raspberry Pi's minimal-design 0402 lands (the regulator corner)
C0603 = FP('C_0603_1608Metric')
C0805 = FP('C_0805_2012Metric')
SOIC14 = FP('SOIC-14_3.9x8.7mm_P1.27mm')
RES = {'27R': ('0603WAF270JT5E', 'C25190'), '33R': ('0603WAF330JT5E', 'C23140'),
       '330R': ('0603WAF3300T5E', 'C23138'), '1k': ('0603WAF1001T5E', 'C21190'),
       '4.7k': ('0603WAF4701T5E', 'C23162'), '5.1k': ('0603WAF5101T5E', 'C23186'),
       '10k': ('0603WAF1002T5E', 'C25804'), '22k': ('0603WAF2202T5E', 'C31850'),
       '33k': ('0603WAF3302T5E', 'C4216'), '47k': ('0603WAF4702T5E', 'C25819'),
       '100k': ('0603WAF1003T5E', 'C25803')}
RES0402 = {'27R': ('0402WGF270JTCE', 'C25100'), '33R': ('0402WGF330JTCE', 'C25105')}
CAP = {'15pF': (C0603, 'CL10C150JB8NNNC', 'C1644'),
       '100nF': (C0603, 'CC0603KRX7R9BB104', 'C14663'),        # 50 V
       '1uF': (C0603, 'CL10A105KB8NNNC', 'C15849'),            # 50 V
       '4.7uF': (C0603, 'CL10A475KO8NNNC', 'C19666'),          # 16 V
       '10uF': (C0603, 'CL10A106KP8NNNC', 'C19702'),           # 10 V: 5 V and 3.3 V rails only
       '22uF': (C0805, 'CL21A226MAQNNNE', 'C45783'),           # 25 V
       # the RP2350 core-regulator corner: Raspberry Pi's minimal-design 0402 parts and lands
       '100nF/0402': (FP('RPI_C0402'), 'CL05B104KO5NNNC', 'C1525'),
       '4.7uF/0402': (FP('RPI_C0402'), 'CL05A475MP5NRNC', 'C23733'),
       '4.7uF/0402w': (FP('RPI_C0402_wide'), 'CL05A475MP5NRNC', 'C23733')}

# MPN -> manufacturer (names from LCSC's / JLCPCB's pages)
MFR = {'RP2354B': 'Raspberry Pi', 'CC0603KRX7R9BB104': 'YAGEO', 'CL10A106KP8NNNC': 'Samsung Electro-Mechanics',
       'CL10A475KO8NNNC': 'Samsung Electro-Mechanics', 'CL10C150JB8NNNC': 'Samsung Electro-Mechanics',
       'CL10A105KB8NNNC': 'Samsung Electro-Mechanics', 'AOTA-B201610S3R3-101-T': 'Abracon',
       'CL05B104KO5NNNC': 'Samsung Electro-Mechanics', 'CL05A475MP5NRNC': 'Samsung Electro-Mechanics',
       'ABM8-272-T3': 'Abracon', 'TS-1187A-B-A-B': 'XKB Connection', 'KT-0603R': 'Hubei KENTO Elec',
       'PZ254V-11-03P': 'XFCN', 'SN74HCT14DR': 'Texas Instruments', 'SN74HCT541PWR': 'Texas Instruments',
       'SN74HCT32DR': 'Texas Instruments',
       '74HCT1G02GV,125': 'Nexperia', 'TYPE-C-31-M-12': 'Korean Hroparts Elec',
       'AP2112K-3.3TRG1': 'Diodes Incorporated', 'CL21A226MAQNNNE': 'Samsung Electro-Mechanics',
       'ESP32-S3-WROOM-1-N16R8': 'Espressif', 'TF-015': 'SOFNG', 'WS2812B-2020-V6': 'Worldsemi',
       '4D03WGJ0103T5E': 'UNI-ROYAL', 'CP2102N-A02-GQFN28R': 'Silicon Labs', 'UMH3N': 'Jiangsu Changjing (JSCJ)',
       'USBLC6-2SC6': 'STMicroelectronics', 'BAT54C,215': 'Nexperia', 'TPS2116DRLR': 'Texas Instruments',
       'AP63203WU-7': 'Diodes Incorporated', 'SWPA4030S6R8MT': 'Sunlord'}
for _v in list(RES.values()) + list(RES0402.values()):
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
        self.key = key      # stable name the drawing scripts use (references: refs.lock)
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


def R4(value, a, b, desc='', **k):
    mpn, lcsc = RES0402[value]
    return add('R', 'Device:R', value, R0402, {1: a, 2: b}, mpn=mpn, lcsc=lcsc, desc=desc, **k)


def C(value, a, b='GND', desc='', **k):
    fp, mpn, lcsc = CAP[value]
    return add('C', 'Device:C', value.split('/')[0], fp, {1: a, 2: b}, mpn=mpn, lcsc=lcsc, desc=desc, **k)


def SW(value, net, desc, **k):
    # XKB TS-1187A-B-A-B (JLCPCB basic C318884), as FujiNet-5200 / 7800 / SMS Rev0
    return add('SW', 'Switch:SW_Push', value, FP('SW_SPST_TS-1187A'), {1: net, 2: 'GND'},
               mpn='TS-1187A-B-A-B', lcsc='C318884', desc=desc, **k)


def TP(net, label, desc='test pad', **k):
    return add('TP', 'Connector:TestPoint', label, FP('TestPoint_Pad_D1.5mm'), {1: net},
               desc=desc, bom=False, **k)


# 14-pin gate packages: unit -> (input pins, output pin); 7 GND, 14 VCC.
GATE_PINS = {
    '74HCT14': [((1,), 2), ((3,), 4), ((5,), 6), ((9,), 8), ((11,), 10), ((13,), 12)],
    '74HCT32': [((1, 2), 3), ((4, 5), 6), ((9, 10), 8), ((12, 13), 11)],
}
GATE_PARTS = {  # value -> (lib_id, MPN, LCSC, datasheet); the HC / LS symbols (same pinouts)
    '74HCT14': ('74xx:74HC14', 'SN74HCT14DR', 'C6769', 'https://www.ti.com/lit/ds/symlink/sn74hct14.pdf'),
    # no 74HCT27 is stocked at JLCPCB (2026-10-10): a quad OR and the 1G02 make the 3-input NOR
    '74HCT32': ('74xx:74LS32', 'SN74HCT32DR', 'C6781', 'https://www.ti.com/lit/ds/symlink/sn74hct32.pdf'),
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
# Declared sheet by sheet (SHEETS order).
sheet('cart-bus')
add('J', '%s:StudioII_Cart_Edge_22' % LIB, 'StudioII_Cart_Edge_22', FP('StudioII_Cart_Edge_22'),
    {k: v[0] for k, v in EDGE.items()}, desc='RCA Studio II 22-pin cartridge edge, 0.156" (3.9624 mm) pitch, '
    'contacts on one face (B.Cu), FliP multicart geometry', bom=False, key='J_EDGE')

# -- the RP2354B (two units: GPIO here, the core on rp-core).  Every RP supply pin on +3V3, the LDO
# off the cart's +5V, so the pads are powered whenever the cart is (its 5 V-tolerant pads need IOVDD
# up, RP2350 datasheet Table 1436).
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

# -- the console's bus into the RP: every line through 330R (limits the current into a 5 V-tolerant
# pad while IOVDD is still rising; 330R x ~5 pF is under 2 ns).  /MRD itself, ahead of its resistor,
# also opens the '541 and feeds the NOR.
for i in range(8):
    R('330R', 'MA%d' % i, 'RP_MA%d' % i, desc='MA%d series' % i, key='R_MA%d' % i)
R('330R', 'TPA', 'RP_TPA', desc='TPA series', key='R_TPA')
R('330R', 'MRD_N', 'RP_MRD', desc='/MRD series', key='R_MRD')

# -- the data path: the RP puts each byte on GPIO16-23; the 74HCT541 drives D0-D7 while /OE1 (/MRD)
# and /OE2 (/DRIVE | /PWROK) are both low (s2_glue_drive).  5 V CMOS levels: the 1802's VIH is
# 3.5 V at 5 V.  /MRD reaches /OE1 with no gate, so the end of a read releases the bus at once.
# Channels taken in reverse (A8 / Y8 = bit 0, as on FujiNet-5200 Rev0): the edge runs D0..D7 west to
# east seen from the parts side, and the '541 at rotation 270 over those fingers then meets them
# and the RP's GPIO16-23 corner with no crossing (a flow-through buffer cannot reverse a bus).
buf = {1: 'MRD_N', 19: 'OE2_N', 10: 'GND', 20: '+5V'}
buf.update({9 - i: 'RP_D%d' % i for i in range(8)})              # A8..A1 (pins 9..2) = bit 0..7
buf.update({11 + i: 'D%d' % i for i in range(8)})               # Y8..Y1 (pins 11..18) = D0..D7
add('U', '74xx:74HCT541', '74HCT541', FP('TSSOP-20_4.4x6.5mm_P0.65mm'), buf, mpn='SN74HCT541PWR',
    lcsc='C436096', desc="D0-D7 driver: drives only while /OE1 (/MRD) and /OE2 (/DRIVE) are low",
    key='U_BUF', ds='https://www.ti.com/lit/ds/symlink/sn74hct541.pdf')
C('100nF', '+5V', desc='74HCT541 VCC decoupling', key='C_BUF')
# -- CART CS = NOR(/MRD, /CLAIM, /PWROK) (s2_glue_cartcs): high, and the console RAM off, only inside a
# read the RP claims with the console powered; /MRD alone ends it.  74HCT1G02 (Nexperia: 1 B, 2 A,
# 3 GND, 4 Y, 5 VCC) on /MRD and CS_REQ_N = /CLAIM | /PWROK.
add('U', '74xGxx:74LVC1G02', '74HCT1G02', FP('SOT-23-5'), {1: 'MRD_N', 2: 'CS_REQ_N', 3: 'GND', 4: 'CART_CS',
    5: '+5V'}, mpn='74HCT1G02GV,125', lcsc='C12504', desc='CART CS = NOR(/MRD, CS_REQ_N), 5 V CMOS out',
    key='U_NOR', ds='https://assets.nexperia.com/documents/data-sheet/74HCT1G02.pdf')
C('100nF', '+5V', desc='74HCT1G02 VCC decoupling', key='C_NOR')
# -- the console-power gate: with the console off (PWR_OK_N high) /OE2 and CS_REQ_N are high whatever
# the RP, running from USB, has left on /DRIVE and /CLAIM, so nothing is driven into a dead console.
GATES('74HCT32', [('DRIVE_N', 'PWR_OK_N', 'OE2_N'), ('PWR_OK_N', 'CLAIM_N', 'CS_REQ_N'),
                  ('GND', 'GND', NC), ('GND', 'GND', NC)],
      desc="/OE2 = /DRIVE | /PWROK; CS_REQ_N = /CLAIM | /PWROK", key='U_OR')
C('100nF', '+5V', desc='74HCT32 VCC decoupling', key='C_OR')
# -- /DRIVE and /CLAIM are high (the cart silent) until the firmware drives them: 10k to the glue's
# own +5V beats the RP2350's reset pull-down (RP2350-E9 latches a pulled-down pad near 2.2 V).
R('10k', '+5V', 'DRIVE_N', desc="/DRIVE pull-up: the '541 off while the RP is unpowered or booting",
  key='R_PUDRIVE')
R('10k', '+5V', 'CLAIM_N', desc='/CLAIM pull-up: CART CS low while the RP is unpowered or booting',
  key='R_PUCLAIM')
# -- PWR_OK: edge 15 (the console 5 V, before the TPS2116 mux) -> 22k / 100k (0.82 x) -> two '14 Schmitt
# stages (TTL thresholds: VT+ 1.2-1.9 V at VCC 4.5 V, TI SCLS225G 6.5) -> GPIO26; the first stage's
# PWR_OK_N gates the '32.  Console off with the cart on USB: PWR_OK 0, PWR_OK_N 1.
GATES('74HCT14', [('VSENSE', 'PWR_OK_N'), ('PWR_OK_N', 'PWR_OK'), ('GND', NC), ('GND', NC),
                  ('GND', NC), ('GND', NC)], desc='PWR_OK from the console 5V sense', key='U_INV')
C('100nF', '+5V', desc='74HCT14 VCC decoupling', key='C_INV')
C('10uF', '+5V', desc='5V logic domain bulk', key='C_GLUEBULK')
R('22k', 'CONS_5V', 'VSENSE', desc='console 5V sense divider', key='R_VSH')
R('100k', 'VSENSE', 'GND', desc='console 5V sense -> 0.82 x CONS_5V', key='R_VSL')
# -- the console 5 V for the ADC (GPIO40, not 5 V tolerant): 100k / 100k = 0.5 x, 5.5 V reads 2.75 V;
# 100 nF for the ADC's sample capacitor
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
# -- bring-up pads: the read strobe and TPA, the two glue outputs and their controls, PWR_OK
TP('MRD_N', '/MRD', desc='scope pad: console /MRD (edge 21)', key='TP_MRD')
TP('TPA', 'TPA', desc='scope pad: console TPA, gated by /MRD (edge 19)', key='TP_TPA')
TP('CART_CS', 'CART_CS', desc='scope pad: CART CS (edge 22)', key='TP_CARTCS')
TP('DRIVE_N', '/DRIVE', desc='scope pad: /DRIVE (GPIO24)', key='TP_DRIVE')
TP('CLAIM_N', '/CLAIM', desc='scope pad: NOR input (GPIO25)', key='TP_CLAIM')
TP('PWR_OK', 'PWR_OK', desc='scope pad: console power sense', key='TP_PWROK')
TP('GND', 'GND', desc='scope ground by the bus pads', key='TP_GNDBUS')

# =========================================================================
sheet('rp-core')
# 0402 where a pin's neighbours leave no room for an 0603 straight out of it (IOVDD 50 / DVDD 51, between
# the debug UART and GPIO40: Raspberry Pi's 0402 land, the corner's own 100 nF part)
NARROW = (50, 51)
for pin in RP_IOVDD_PINS:      # one 100 nF per IOVDD pin; the key names the pin it sits on
    C('100nF/0402' if pin in NARROW else '100nF', RP_IO_RAIL, desc='IOVDD decoupling', key='C_IOV%d' % pin)
C('100nF', RP_IO_RAIL, desc='QSPI_IOVDD decoupling', key='C_QSPI')
C('100nF/0402', RP_IO_RAIL, desc='USB_OTP_VDD decoupling', key='C_OTP')
C('100nF', RP_IO_RAIL, desc='ADC_AVDD decoupling', key='C_ADC')
C('10uF', RP_IO_RAIL, desc='RP IO rail bulk (LDO output)', key='C_IOBULK')
C('4.7uF/0402w', RP_CORE_RAIL, desc='VREG_VIN input (C_IN, at the pins)', key='C_VREGIN')
for pin in RP_DVDD_PINS:
    C('100nF/0402' if pin in NARROW else '100nF', 'DVDD', desc='DVDD decoupling', key='C_DV%d' % pin)
C('4.7uF/0402w', 'DVDD', desc='core regulator output (C_OUT)', key='C_DVBULK')
R4('33R', RP_CORE_RAIL, 'VREG_AVDD', desc='VREG_AVDD filter', key='R_AVDD')
C('4.7uF/0402', 'VREG_AVDD', desc='VREG_AVDD filter', key='C_AVDD')
add('L', 'Device:L', '3.3uH', FP('RPI_L_AOTA-B201610S3R3'), {1: 'DVDD', 2: 'RP_LX'},
    mpn='AOTA-B201610S3R3-101-T', lcsc='C42411119', desc='RP2350 core SMPS inductor', key='L_RP')
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
SW('BOOTSEL', 'BOOTSEL_BTN', 'RP2354 BOOTSEL (hold while pressing RESET)', key='SW_BOOTSEL')
R('1k', 'BOOTSEL_CTL', 'QSPI_SS', desc='S3 IO5 -> RP QSPI_SS (low through reset = BOOTSEL)', key='R_BSELCTL')
# RESET resets both MCUs: the button pulls RP RUN and S3 EN low through a common-cathode pair, so
# neither chip's reset drives the other's.  The edge has no reset line: RESET is the way back to the
# FujiNet's CONFIG screen.
SW('RESET', 'RST_BTN', 'cart RESET: RP RUN + S3 EN via BAT54C', key='SW_RESET')
add('D', 'Diode:BAT54C', 'BAT54C', FP('SOT-23'), {1: 'RUN', 2: 'S3_EN', 3: 'RST_BTN'},
    mpn='BAT54C,215', lcsc='C37704', desc='RESET steering, common cathode', key='D_RST')
# RP <-> S3 native USB (RP = CDC device, S3 = host), on the board: 27R series at the RP
R4('27R', 'USB_DP', 'RP_USB_DP', desc='USB series', key='R_USBP')
R4('27R', 'USB_DM', 'RP_USB_DM', desc='USB series', key='R_USBM')
TP('SWCLK', 'SWCLK', key='TP_SWCLK')
TP('SWDIO', 'SWDIO', key='TP_SWDIO')
TP('GND', 'GND', key='TP_GND')
TP('RUN', 'RUN', key='TP_RUN')
TP('DVDD', 'DVDD', desc='bring-up pad: RP core rail', key='TP_DVDD')

# =========================================================================
# fujinet: the ESP32-S3, microSD, the WS2812 status LED (FujiNet-ChannelF Rev0's circuit)
sheet('fujinet')
s3 = {}
for fn, pad in S3_PAD.items():
    for p in (pad if isinstance(pad, list) else [pad]):
        s3[p] = 'GND' if fn == 'GND' else S3_RAIL if fn == '3V3' else S3_NET.get(fn, NC)
add('U', '%s:ESP32-S3-WROOM-1_Fn' % LIB, 'ESP32-S3-WROOM-1-N16R8', FP('ESP32-S3-WROOM-1'), s3,
    mpn='ESP32-S3-WROOM-1-N16R8', lcsc='C2913202', desc='FujiNet core (fujiversal-studio2)', key='U_S3')
C('22uF', S3_RAIL, desc='S3 bulk (WiFi TX bursts)', key='C_S3BULK')
C('100nF', S3_RAIL, desc='S3 decoupling', key='C_S3')
R('10k', S3_RAIL, 'S3_EN', desc='EN pull-up', key='R_EN')
C('1uF', 'S3_EN', desc='EN power-on delay', key='C_EN')
SW('S3_RST', 'S3_EN', 'ESP32-S3 EN', key='SW_S3EN')
SW('S3_BOOT', 'S3_IO0', 'ESP32-S3 BOOT (IO0)', key='SW_S3BOOT')
add('J', '%s:MicroSD_TF015' % LIB, 'microSD', FP('TF-SMD_TF-015'),
    {1: 'SD_DAT2', 2: 'SD_CS', 3: 'SD_MOSI', 4: S3_RAIL, 5: 'SD_SCK', 6: 'GND',
     7: 'SD_MISO', 8: 'SD_DAT1', 9: 'SD_CD', 10: 'GND', 11: 'GND', 12: 'GND', 13: 'GND'},
    mpn='TF-015', lcsc='C113206', desc='microSD push-push, SPI mode', key='J_SD')
# one symbol unit per resistor (R_Pack04_Split: unit k = pins k and 9-k), drawn on its line
add('RN', 'Device:R_Pack04_Split', '4x10k', FP('R_Array_Convex_4x0603'),
    {1: 'SD_CS', 2: 'SD_MISO', 3: 'SD_DAT1', 4: 'SD_DAT2', 5: S3_RAIL, 6: S3_RAIL, 7: S3_RAIL, 8: S3_RAIL},
    mpn='4D03WGJ0103T5E', lcsc='C29718', desc='SD pull-ups', key='RN_SD')
# TF-015 card-detect: open with no card, closed to the shell (GND) with a card in
R('10k', S3_RAIL, 'SD_CD', desc='card-detect pull-up (low = card present)', key='R_SDCD')
C('10uF', S3_RAIL, desc='microSD supply', key='C_SD')
# WS2812B-2020-V6 datasheet: VDD +3.7..+5.3 V (NOT a 3.3 V part), VIH min 2.7 V:
# it runs on +5V (the mux's output, 4.7-5.25 V) and takes the S3's 3.3 V data directly
R('330R', 'LED_STRIP', 'WS_DIN', desc='WS2812 data series', key='R_WS')
add('D', 'LED:WS2812B-2020', 'WS2812B-2020-V6', FP('LED_WS2812B-2020_PLCC4_2.0x2.0mm'),
    {1: NC, 2: 'GND', 3: 'WS_DIN', 4: '+5V'}, mpn='WS2812B-2020-V6', lcsc='C52917434',
    desc='status LED on +5V (datasheet VDD 3.7-5.3 V; VIH 2.7 V takes 3.3 V data)', key='D_WS')
C('100nF', '+5V', desc='WS2812 decoupling', key='C_WS')

# =========================================================================
# usb: USB-C, ESD, the CP2102N bridge and esptool's auto-program pair (FujiNet-ChannelF Rev0's circuit)
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
cp.update({3: 'GND', 4: 'UBRG_DP', 5: 'UBRG_DM', 6: S3_RAIL, 7: S3_RAIL, 8: 'VBUS_SNS',
           9: 'CP_RST', 23: 'GND', 24: 'UART_RTS', 25: 'S3_TXD', 26: 'S3_RXD',
           28: 'UART_DTR', 29: 'GND'})
add('U', 'Interface_USB:CP2102N-Axx-xQFN28', 'CP2102N-A02-GQFN28', FP('QFN-28-1EP_5x5mm_P0.5mm_EP3.35x3.35mm'),
    cp, mpn='CP2102N-A02-GQFN28R', lcsc='C964632', desc='USB-UART for S3 flashing/console (self-powered)',
    key='U_UART')
C('100nF', S3_RAIL, desc='CP2102N VDD', key='C_UART')
C('4.7uF', S3_RAIL, desc='CP2102N VDD bulk', key='C_UARTBULK')
# VBUS sense (datasheet: VBUS pin max VDD + 2.5 V on a self-powered design): 22k / 47k = 3.4 V
R('22k', 'VBUS', 'VBUS_SNS', desc='VBUS sense divider', key='R_VBSH')
R('47k', 'VBUS_SNS', 'GND', desc='VBUS sense divider', key='R_VBSL')
# /RSTb: "In all cases, a 1 kOhm pull-up on the RSTb pin is recommended" (CP2102N datasheet)
R('1k', S3_RAIL, 'CP_RST', desc='/RST pull-up (datasheet: 1k)', key='R_CPRST')
add('U', 'Transistor_BJT:UMH3N', 'UMH3N', FP('SOT-363_SC-70-6'),
    {1: 'UART_RTS', 2: 'UART_DTR', 6: 'S3_EN', 3: 'S3_IO0', 4: 'UART_DTR', 5: 'UART_RTS'},
    mpn='UMH3N', lcsc='C62892', desc='esptool auto-program (DevKitC-1 style)', key='U_AUTOPROG')

# =========================================================================
sheet('power')
# +5V (the glue, the RP's LDO, the S3's buck, the WS2812) is the TPS2116 power mux's output:
#   VIN1  USB VBUS -- the priority input: MODE on VIN1, PR1 from a 33k / 10k divider, so VBUS above
#         VREF x 4.3 (3.96-4.64 V) runs the cart and the console's 7805 supplies nothing
#   VIN2  CONS_5V, edge 15, the console's 7805 -- whenever VBUS is absent
# 37-60 mOhm either way (~20 mV at the cart's peak), so the 74HCT glue sits within 4.7-5.25 V on
# either source; reverse current blocking: neither source can back-feed the other.  ST (open
# drain, low on VIN2) is not used.
add('U', 'Power_Management:TPS2116DRL', 'TPS2116', FP('SOT-583-8'),
    {1: 'GND', 2: '+5V', 3: 'VBUS', 4: 'VBUS_PR', 5: 'VBUS', 6: 'CONS_5V', 7: '+5V', 8: NC},
    mpn='TPS2116DRLR', lcsc='C3235557', desc='power mux: VBUS first, console 5V second', key='U_MUX')
R('33k', 'VBUS', 'VBUS_PR', desc='mux priority threshold (VBUS > 4.3 V)', key='R_PRH')
R('10k', 'VBUS_PR', 'GND', desc='mux priority threshold', key='R_PRL')
C('1uF', 'VBUS', desc='mux VIN1 (datasheet: 1 uF at the input)', key='C_MUXV1')
C('10uF', 'CONS_5V', desc='edge 5V bulk, mux VIN2', key='C_CONS')
C('100nF', 'CONS_5V', desc='edge 5V HF bypass', key='C_CONSHF')
C('22uF', '+5V', desc='+5V bulk (mux output; buck input)', key='C_5VBULK')
# the S3 side's 3.3 V: AP63203, 2 A synchronous buck (FujiNet-ChannelF Rev0); WiFi bursts ~400 mA
C('22uF', '+5V', desc='buck input', key='C_BIN')
C('100nF', '+5V', desc='buck input HF', key='C_BINHF')
add('U', 'Regulator_Switching:AP63203WU', 'AP63203WU', FP('TSOT-23-6'),
    {1: S3_RAIL, 2: '+5V', 3: '+5V', 4: 'GND', 5: 'BUCK_SW', 6: 'BUCK_BST'},
    mpn='AP63203WU-7', lcsc='C780769', desc='3.3V 2A buck for the S3 side', key='U_BUCK')
C('100nF', 'BUCK_SW', 'BUCK_BST', desc='bootstrap', key='C_BST')
add('L', 'Device:L', '6.8uH', FP('L_Sunlord_SWPA4030S'), {1: 'BUCK_SW', 2: S3_RAIL},
    mpn='SWPA4030S6R8MT', lcsc='C62684', desc='buck inductor', key='L_BUCK')
C('22uF', S3_RAIL, desc='buck output', key='C_BOUT1')
C('22uF', S3_RAIL, desc='buck output', key='C_BOUT2')
# RP rail: a fast LDO (AP2112K: ~20 us start-up) straight off +5V, so IOVDD tracks the cart rail as it
# rises and the pads are never unpowered with 5 V on them (the buck waits out UVLO + 4 ms soft start).
add('U', 'Regulator_Linear:AP2112K-3.3', 'AP2112K-3.3', FP('SOT-23-5'),
    {1: '+5V', 2: 'GND', 3: '+5V', 4: NC, 5: RP_IO_RAIL},
    mpn='AP2112K-3.3TRG1', lcsc='C51118', desc='RP2354B 3.3V LDO (IOVDD, VREG_VIN, VREG_AVDD), 600mA, fast start',
    key='U_LDO')
C('1uF', '+5V', desc='LDO input', key='C_LDOIN')
C('1uF', RP_IO_RAIL, desc='LDO output', key='C_LDOOUT')
TP('CONS_5V', 'CONS_5V', desc='bring-up pad: console 5V (edge 15)', key='TP_CONS5V')
TP('VBUS', 'VBUS', desc='bring-up pad: USB VBUS', key='TP_VBUS')
TP('+5V', '+5V', desc='bring-up pad: +5V', key='TP_5V')
TP(RP_IO_RAIL, '+3V3', desc='bring-up pad: +3V3 (RP)', key='TP_3V3')
TP(S3_RAIL, '+3V3_S3', desc='bring-up pad: +3V3_S3 (S3 side)', key='TP_3V3S3')

# PWR_FLAGs: nets whose drivers are passive pins
PWR_FLAG_NETS = ['GND', 'CONS_5V', 'VBUS', S3_RAIL, 'DVDD', 'VREG_AVDD']   # +5V: the mux's VOUT; +3V3: the LDO's
# nets drawn as power symbols (global, never prefixed)
RAIL_NETS = ['GND', 'CONS_5V', 'VBUS', '+5V', '+3V3', S3_RAIL, 'DVDD']

# ---- references: tools/refs.lock (frozen with the board: the schematic's numbering as first drawn),
# else the next free number of each prefix in declaration order
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
