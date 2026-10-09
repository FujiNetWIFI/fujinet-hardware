"""FujiNet-Astrocade Rev0 (RP2354A) -- the single source of truth.

Every part, value, footprint, MPN, LCSC code and pin->net assignment lives
here.  gen_sch.py, gen_pcb.py, check_nets.py and export.py all import it;
the KiCad files are generated output.  Parts are addressed by `key` (the
drawing, the audits); references are labels, frozen in tools/refs.lock (the
routed board, its silkscreen, BOM and CPL carry them).

One sheet per board region, console side first (the FujiNet-5200 Rev0
arrangement): every sheet is the board turned so the edge faces left, so the
schematic reads from the cartridge slot outward (tools/sch_layout.py).

Circuit provenance: the INTV Rev0 cart (fujinet-hardware INTV/FujiNet-INTV-Rev0,
itself adapted from PiNTY CARD, CERN-OHL-W-2.0).  Firmware contracts:
  fujinet-firmware pico/astrocade/firmware/include/astrocade_cart.h  (RP pins)
  fujinet-firmware include/pinmap/fujiversal-astrocade.h           (S3 pins)
Edge pinout (Tilton 1-26): 1 GND, 2-9 A7..A0, 10-12 D0-D2, 13 GND,
14-18 D3-D7, 19 A11, 20 A10, 21 /CCS, 22 A12, 23 A9, 24 A8, 25 +5V, 26 GND.

Rails: CONS_5V is edge land 25; +5V is the diode-OR of CONS_5V and USB VBUS;
+3V3 (AP63203 buck) feeds the S3, CP2102N and microSD; +3V3_RP (AP2112K LDO,
which follows the console rail up in dropout) feeds the whole RP2354A so its
IOVDD is up while the console bus is (RP2350 datasheet p.1332: the pads tolerate 5.5 V only
"provided IOVDD is powered to 3.3 V").  Audit: docs/design-review-rev0.md.
"""

LIB = 'FujiNet-Astrocade'
PROJECT = 'FujiNet-Astrocade-Rev0'
NC = None  # explicit no-connect

SHEETS = [  # (file stem, title, page): one sheet per board region, console side first
    ('cart-bus', 'Cart bus: edge -> RP2354A GPIO', 2),
    ('rp-core', 'RP2354A core, crystal, RUN, USB', 3),
    ('fujinet', 'FujiNet: ESP32-S3, microSD, LED', 4),
    ('usb', 'USB-C and the CP2102N bridge', 5),
    ('power', 'Power: 5V OR, 3.3V buck, RP LDO', 6),
]
SHEET_ORDER = [s[0] for s in SHEETS]

# ---- RP2354A (QFN-60) GPIO -> package pin ---------------------------------
RP_GPIO_PIN = {0: 2, 1: 3, 2: 4, 3: 5, 4: 7, 5: 8, 6: 9, 7: 10, 8: 12, 9: 13,
               10: 14, 11: 15, 12: 16, 13: 17, 14: 18, 15: 19, 16: 27, 17: 28,
               18: 29, 19: 31, 20: 32, 21: 33, 22: 34, 23: 35, 24: 36, 25: 37,
               26: 40, 27: 41, 28: 42, 29: 43}

# astrocade_cart.h: A0-A12 = GP0-12 (unshifted mask), /ENABLE = GP13,
# D0-D7 = GP14-21 (contiguous), GP22 self-test, GP25 LED, GP26 console-5V
# sense (ADC0), GP27 debug UART TX.
RP_GPIO_NET = {g: 'CA%d' % g for g in range(13)}
RP_GPIO_NET[13] = 'CCS_N'
RP_GPIO_NET.update({14 + i: 'CD%d' % i for i in range(8)})
RP_GPIO_NET.update({22: 'SELFTEST', 25: 'RP_LED', 26: 'VSENSE', 27: 'RP_DBG_TX'})
RP_RAIL = '+3V3_RP'
RP_IOVDD_PINS = [1, 11, 20, 30, 38, 45]
RP_DVDD_PINS = [6, 23, 39]

# ESP32-S3-WROOM-1 module pad -> function (pads per the KiCad symbol)
S3_PAD = {'GND': [1, 40, 41], '3V3': 2, 'EN': 3, 'IO4': 4, 'IO5': 5, 'IO6': 6,
          'IO7': 7, 'IO15': 8, 'IO16': 9, 'IO17': 10, 'IO18': 11, 'IO8': 12,
          'IO19': 13, 'IO20': 14, 'IO3': 15, 'IO46': 16, 'IO9': 17, 'IO10': 18,
          'IO11': 19, 'IO12': 20, 'IO13': 21, 'IO14': 22, 'IO21': 23,
          'IO47': 24, 'IO48': 25, 'IO45': 26, 'IO0': 27, 'IO35': 28,
          'IO36': 29, 'IO37': 30, 'IO38': 31, 'IO39': 32, 'IO40': 33,
          'IO41': 34, 'IO42': 35, 'RXD0': 36, 'TXD0': 37, 'IO2': 38, 'IO1': 39}
# fujiversal-astrocade.h + the INTV RUN/BOOTSEL forcing contract
S3_NET = {'EN': 'S3_EN', 'IO0': 'S3_IO0', 'IO4': 'RUN_CTL', 'IO5': 'BOOTSEL_CTL',
          'IO19': 'USB_DM', 'IO20': 'USB_DP', 'IO38': 'SD_MOSI', 'IO39': 'SD_SCK',
          'IO40': 'SD_MISO', 'IO41': 'SD_CS', 'IO42': 'SD_CD', 'IO48': 'LED_STRIP',
          'RXD0': 'S3_RXD', 'TXD0': 'S3_TXD'}

EDGE = {1: 'GND', 2: 'CA7', 3: 'CA6', 4: 'CA5', 5: 'CA4', 6: 'CA3', 7: 'CA2',
        8: 'CA1', 9: 'CA0', 10: 'CD0', 11: 'CD1', 12: 'CD2', 13: 'GND',
        14: 'CD3', 15: 'CD4', 16: 'CD5', 17: 'CD6', 18: 'CD7', 19: 'CA11',
        20: 'CA10', 21: 'CCS_N', 22: 'CA12', 23: 'CA9', 24: 'CA8', 25: 'CONS_5V',
        26: 'GND'}

# ---- common parts: (lib_id, footprint, MPN, LCSC) --------------------------
FP = lambda n: '%s:%s' % (LIB, n)
R0603 = FP('R_0603_1608Metric')
C0603 = FP('C_0603_1608Metric')
C0805 = FP('C_0805_2012Metric')
RES = {'27R': ('0603WAF270JT5E', 'C25190'), '33R': ('0603WAF330JT5E', 'C23140'),
       '330R': ('0603WAF3300T5E', 'C23138'), '1k': ('0603WAF1001T5E', 'C21190'),
       '5.1k': ('0603WAF5101T5E', 'C23186'), '10k': ('0603WAF1002T5E', 'C25804'),
       '22k': ('0603WAF2202T5E', 'C31850'), '47k': ('0603WAF4702T5E', 'C25819'),
       '100k': ('0603WAF1003T5E', 'C25803'), '150k': ('0603WAF1503T5E', 'C22807'),
       '15k': ('0603WAF1502T5E', 'C22809')}
CAP = {'15pF': (C0603, 'CL10C150JB8NNNC', 'C1644'),
       '100nF': (C0603, 'CC0603KRX7R9BB104', 'C14663'),
       '1uF': (C0603, 'CL10A105KB8NNNC', 'C15849'),
       '4.7uF': (C0603, 'CL10A475KO8NNNC', 'C19666'),
       '10uF': (C0603, 'CL10A106KP8NNNC', 'C19702'),
       '22uF': (C0805, 'CL21A226MAQNNNE', 'C45783')}
# 0402 parts of the RP2350 regulator corner grafted from Raspberry Pi's
# minimal design (tools/rpi_graft.py)
RES0402 = {'27R': ('0402WGF270JTCE', 'C25100'), '33R': ('0402WGF330JTCE', 'C25105')}
CAP0402 = {'100nF': (None, 'CL05B104KO5NNNC', 'C1525'), '4.7uF': (None, 'CL05A475MP5NRNC', 'C23733')}


class Part:
    def __init__(self, prefix, lib_id, value, footprint, pins, sheet,
                 mpn='', lcsc='', desc='', bom=True, dnp=False, ds='', key=None):
        self.prefix, self.lib_id, self.value, self.footprint = prefix, lib_id, value, footprint
        self.pins = {str(k): v for k, v in pins.items()}  # pad number -> net (None = NC)
        self.sheet, self.mpn, self.lcsc, self.desc, self.bom, self.dnp = sheet, mpn, lcsc, desc, bom, dnp
        self.mfr = ''
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


def R(value, a, b, desc='', size='0603', key=None):
    mpn, lcsc = RES[value] if size == '0603' else RES0402[value]
    fp = R0603 if size == '0603' else FP('RPI_R0402')
    return add('R', 'Device:R', value, fp, {1: a, 2: b}, mpn=mpn, lcsc=lcsc, desc=desc, key=key)


def C(value, a, b='GND', desc='', size=None, key=None):
    fp, mpn, lcsc = CAP[value] if size is None else CAP0402[value]
    if size is not None:
        fp = FP(size)
    return add('C', 'Device:C', value, fp, {1: a, 2: b}, mpn=mpn, lcsc=lcsc, desc=desc, key=key)


def SW(value, net, desc, key=None):
    return add('SW', 'Switch:SW_Push', value, FP('SW_SPST_TL3342'), {1: net, 2: 'GND'},
               mpn='TL3342F160QG', lcsc='C2886898', desc=desc, key=key)


def TP(net, label, key=None):
    return add('TP', 'Connector:TestPoint', label, FP('TestPoint_Pad_D1.5mm'), {1: net},
               desc='test pad', bom=False, key=key)


# =========================================================================
# cart-bus: the edge, the RP2354A's 30 GPIOs (its unit A), what hangs off them
sheet('cart-bus')
rp = {p: RP_RAIL for p in RP_IOVDD_PINS}                                     # IOVDD
rp.update({p: 'DVDD' for p in RP_DVDD_PINS})
rp.update({50: 'DVDD',                                                       # VREG_FB
      21: 'XIN', 22: 'XOUT', 24: 'SWCLK', 25: 'SWDIO', 26: 'RUN',
      44: RP_RAIL,         # ADC_AVDD
      46: 'VREG_AVDD', 47: 'GND', 48: 'RP_LX', 49: RP_RAIL,                   # VREG (VIN with AVDD: p.402)
      51: 'RP_USB_DM', 52: 'RP_USB_DP', 53: RP_RAIL, 54: RP_RAIL,
      55: NC, 56: NC, 57: NC, 58: NC, 59: NC,                                  # QSPI (flash in package)
      60: 'QSPI_SS', 61: 'GND'})
for g, pin in RP_GPIO_PIN.items():
    rp[pin] = RP_GPIO_NET.get(g, NC)
U_RP = add('U', '%s:RP2354A_Split' % LIB, 'RP2354A', FP('RPI_RP2350A_QFN60'), rp,
           mpn='RP2354A', lcsc='C41378174', desc='RP2350A + 2MB flash in package; cart bus server', key='U_RP')
# drawn in two units: A = the 30 GPIOs on the cart-bus sheet, B = supplies, core regulator,
# crystal, RUN, SWD, USB and QSPI on rp-core (gen_sch.rp_split_symbol)
U_RP.unit_sheets = {1: 'cart-bus', 2: 'rp-core'}
U_RP.pin_unit = {str(pad): 1 if pad in RP_GPIO_PIN.values() else 2 for pad in rp}
add('J', '%s:Astrocade_Cart_Edge_26' % LIB, 'Astrocade_Cart_Edge_26', FP('Astrocade_Cart_Edge_26'),
    EDGE, desc='26 contact lands on B.Cu, blade contacts from below', bom=False, key='J_EDGE')
R('10k', RP_RAIL, 'CCS_N', desc='/CCS idle-high when no console', key='R_CCS')
# GP26 is a plain (not fault-tolerant) ADC pad: 0.6 x CONS_5V = 3.0 V at 5.0 V,
# 3.15 V at 5.25 V; VIH 0.65 x IOVDD = 2.15 V is met down to 3.6 V.  10k / 15k (6 kOhm Thevenin, was
# 100k / 150k): VSENSE is a digital input in the firmware's serve gate, and on RP2350 A2 silicon erratum
# E9 holds an input-enabled pad near 2.2 V unless it is pulled down through 8.2 kOhm or less -- with
# 60 kOhm a USB-powered cart could read a switched-off console as powered (docs/design-review-rev0.md,
# Part 3, finding 1; tools/audit/e9_vsense.py).  0.2 mA from the console rail.
R('10k', 'CONS_5V', 'VSENSE', desc='console 5V sense (GP26/ADC0 is not 5V tolerant)', key='R_VSH')
R('15k', 'VSENSE', 'GND', desc='console 5V sense -> 3.0V (6 kOhm: beats RP2350-E9)', key='R_VSL')
# activity LED
R('330R', 'RP_LED', 'RP_LED_A', desc='LED series (KT-0603G VF ~2.6-2.85 V: 1.5-2 mA from 3.3 V)', key='R_LED')
add('D', 'Device:LED', 'green', FP('LED_0603_1608Metric'), {1: 'GND', 2: 'RP_LED_A'},
    mpn='KT-0603G', lcsc='C12624', desc='RP activity LED', key='D_LED')
TP('SELFTEST', 'SELFTEST', key='TP_SELFTEST')
TP('RP_DBG_TX', 'DBG_TX', key='TP_DBGTX')
# /CCS is probed at R_CCS: a pad of its own would hang a long stub on the bus

# =========================================================================
# rp-core: the RP2354A's unit B -- supplies and decoupling, core regulator, crystal,
# RUN / BOOTSEL / RESET, SWD, the USB link to the S3
sheet('rp-core')
# decoupling: one 100nF per IOVDD/DVDD/QSPI/USB/ADC supply pin, bulk on 3V3
for pin in RP_IOVDD_PINS:
    C('100nF', RP_RAIL, desc='IOVDD decoupling', key='C_IOV%d' % pin)
C('100nF', RP_RAIL, desc='QSPI_IOVDD decoupling (extra)', key='C_QSPI')
C('100nF', RP_RAIL, desc='USB_OTP_VDD + QSPI_IOVDD decoupling', size='RPI_C0402', key='C_OTP')
C('100nF', RP_RAIL, desc='ADC_AVDD decoupling', key='C_ADC')
C('4.7uF', RP_RAIL, desc='VREG_VIN bulk', size='RPI_C0402_wide', key='C_VREGIN')
C('10uF', RP_RAIL, desc='RP 3V3 bulk', key='C_IOBULK')
for pin in RP_DVDD_PINS:
    C('100nF', 'DVDD', desc='DVDD decoupling', key='C_DV%d' % pin)
C('4.7uF', 'DVDD', desc='core regulator output', size='RPI_C0402_wide', key='C_DVBULK')
R('33R', RP_RAIL, 'VREG_AVDD', desc='VREG_AVDD filter', size='0402', key='R_AVDD')
C('4.7uF', 'VREG_AVDD', desc='VREG_AVDD filter', size='RPI_C0402', key='C_AVDD')
add('L', 'Device:L', '3.3uH', FP('RPI_L_AOTA-B201610S3R3'), {1: 'DVDD', 2: 'RP_LX'},
    mpn='AOTA-B201610S3R3-101-T', lcsc='C42411119', desc='RP2350 core SMPS inductor', key='L_RP')
# 12 MHz crystal
add('Y', 'Device:Crystal_GND24', '12MHz', FP('Crystal_SMD_3225-4Pin_3.2x2.5mm'),
    {1: 'XIN', 2: 'GND', 3: 'XOUT_Y', 4: 'GND'}, mpn='ABM8-272-T3', lcsc='C20625731', key='Y_RP')
C('15pF', 'XIN', desc='crystal load', key='C_XIN')
C('15pF', 'XOUT_Y', desc='crystal load', key='C_XOUT')
R('1k', 'XOUT', 'XOUT_Y', desc='crystal drive limit', key='R_XOUT')
# RUN / BOOTSEL.  The S3 forces them exactly as fnPicoUpdater::
# forceBootselViaPins() expects: its pins idle as inputs and are driven LOW
# to assert.  Same 3.3V rail on both chips, so a 1k series resistor is the
# whole interface (an NPN driver here would invert the firmware's polarity).
R('10k', RP_RAIL, 'RUN', desc='RUN pull-up', key='R_RUN')
R('10k', RP_RAIL, 'QSPI_SS', desc='QSPI_SS pull-up', key='R_SS')
R('1k', 'QSPI_SS', 'BOOTSEL_BTN', desc='BOOTSEL button series', key='R_BSEL')
SW('BOOTSEL', 'BOOTSEL_BTN', 'RP2354 BOOTSEL (hold while pressing RESET)', key='SW_BOOTSEL')
R('1k', 'RUN_CTL', 'RUN', desc='S3 IO4 -> RP RUN (drive low = reset)', key='R_RUNCTL')
R('1k', 'BOOTSEL_CTL', 'QSPI_SS', desc='S3 IO5 -> RP QSPI_SS (low through reset = BOOTSEL)', key='R_BSELCTL')
# RP <-> S3 native USB (RP = CDC device, S3 = host)
R('27R', 'USB_DP', 'RP_USB_DP', desc='USB series', size='0402', key='R_USBP')
R('27R', 'USB_DM', 'RP_USB_DM', desc='USB series', size='0402', key='R_USBM')
TP('SWCLK', 'SWCLK', key='TP_SWCLK')
TP('SWDIO', 'SWDIO', key='TP_SWDIO')
TP('GND', 'GND', key='TP_GND')
TP('RUN', 'RUN', key='TP_RUN')
TP('QSPI_SS', 'BOOTSEL', key='TP_BOOTSEL')
# DVDD is probed at C_DVBULK: a pad of its own would hang a stub on the core rail
# top-face RESET resets both MCUs: the button pulls RP RUN and S3 EN low through
# a common-cathode pair, so neither chip's reset drives the other's
SW('RESET', 'RST_BTN', 'cart RESET: RP RUN + S3 EN via BAT54C', key='SW_RESET')
add('D', 'Diode:BAT54C', 'BAT54C', FP('SOT-23'), {1: 'RUN', 2: 'S3_EN', 3: 'RST_BTN'},
    mpn='BAT54C,215', lcsc='C37704', desc='RESET steering, common cathode', key='D_RST')

# =========================================================================
# fujinet: the ESP32-S3, microSD, the WS2812 status LED
sheet('fujinet')
s3 = {}
for fn, pad in S3_PAD.items():
    for p in (pad if isinstance(pad, list) else [pad]):
        s3[p] = 'GND' if fn == 'GND' else '+3V3' if fn == '3V3' else S3_NET.get(fn, NC)
add('U', '%s:ESP32-S3-WROOM-1_Fn' % LIB, 'ESP32-S3-WROOM-1-N16R8', FP('ESP32-S3-WROOM-1'), s3,
    mpn='ESP32-S3-WROOM-1-N16R8', lcsc='C2913202', desc='FujiNet core (fujiversal-astrocade)', key='U_S3')
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
# one symbol unit per resistor (R_Pack04_Split: unit k = pins k and 9-k), drawn on its line
add('RN', 'Device:R_Pack04_Split', '4x10k', FP('R_Array_Convex_4x0603'),
    {1: 'SD_CS', 2: 'SD_MISO', 3: 'SD_DAT1', 4: 'SD_DAT2', 5: '+3V3', 6: '+3V3', 7: '+3V3', 8: '+3V3'},
    mpn='4D03WGJ0103T5E', lcsc='C29718', desc='SD pull-ups', key='RN_SD')
# TF-015 card-detect: open with no card, closed to the shell (GND) with a card in:
# SD_CD reads LOW when a card is present
R('10k', '+3V3', 'SD_CD', desc='card-detect pull-up (low = card present)', key='R_SDCD')
C('10uF', '+3V3', desc='microSD supply', key='C_SD')
# WS2812B-2020-V6 datasheet: VDD +3.7..+5.3 V (NOT a 3.3 V part), VIH min 2.7 V:
# it runs on +5V (4.6-5.0 V after the OR diode) and takes the S3's 3.3 V data directly
R('330R', 'LED_STRIP', 'WS_DIN', desc='WS2812 data series', key='R_WS')
add('D', 'LED:WS2812B-2020', 'WS2812B-2020-V6', FP('LED_WS2812B-2020_PLCC4_2.0x2.0mm'),
    {1: NC, 2: 'GND', 3: 'WS_DIN', 4: '+5V'}, mpn='WS2812B-2020-V6', lcsc='C52917434',
    desc='status LED on +5V (datasheet VDD 3.7-5.3 V; VIH 2.7 V takes 3.3 V data)', key='D_WS')
C('100nF', '+5V', desc='WS2812 decoupling', key='C_WS')

# =========================================================================
# usb: USB-C, ESD, the CP2102N bridge and esptool's auto-program pair
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
# power: the console 5V / USB VBUS OR, the 3.3 V buck, the RP's LDO
sheet('power')
# Diode OR: no back-feed from USB into an unpowered console, nor from the
# console into the USB host.  SS34 VF ~0.35 V at the cart's ~0.4 A: +5V is
# 4.4-4.9 V on a 4.75-5.25 V console rail -- above the AP63203's 3.8 V and
# the AP2112K's 3.3 V + 0.25 V dropout; there is no 5 V logic on this board.
add('D', 'Diode:SS34', 'SS34', FP('D_SMA'), {1: '+5V', 2: 'CONS_5V'}, mpn='SS34', lcsc='C8678',
    desc='console 5V OR-ing', key='D_CONS')
add('D', 'Diode:SS34', 'SS34', FP('D_SMA'), {1: '+5V', 2: 'VBUS'}, mpn='SS34', lcsc='C8678',
    desc='USB VBUS OR-ing (no back-feed into the console)', key='D_VBUS')
C('100nF', 'CONS_5V', desc='edge 5V HF bypass', key='C_CONSHF')
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
# RP rail: AP2112K-3.3 straight off +5V.  In dropout it follows the console rail
# as it rises (1 V/ms into the rail's ~21 uF needs 21 mA, under its 50 mA
# fold-back limit), instead of waiting out the buck's UVLO + 4 ms soft-start
# (AP63203 tSS) with 5 V already on the bus pads.  VREG_VIN and
# VREG_AVDD ride on it too: they must rise together (RP2350 p.402).
add('U', 'Regulator_Linear:AP2112K-3.3', 'AP2112K-3.3', FP('SOT-23-5'),
    {1: '+5V', 2: 'GND', 3: '+5V', 4: NC, 5: RP_RAIL},
    mpn='AP2112K-3.3TRG1', lcsc='C51118', desc='RP2354A 3.3V LDO (IOVDD, VREG_VIN, VREG_AVDD), fast start',
    key='U_LDO')
C('1uF', '+5V', desc='LDO input', key='C_LDOIN')
C('1uF', RP_RAIL, desc='LDO output', key='C_LDOOUT')
TP('+5V', '+5V', key='TP_5V')
TP('+3V3', '+3V3', key='TP_3V3')
TP(RP_RAIL, '+3V3_RP', key='TP_3V3RP')

# PWR_FLAGs: nets whose drivers are passive pins
PWR_FLAG_NETS = ['GND', 'CONS_5V', 'VBUS', '+5V', '+3V3', 'DVDD', 'VREG_AVDD']   # +3V3_RP: LDO power_out
# nets drawn as power symbols (global, never prefixed): the board's planes and islands
RAIL_NETS = ['GND', 'CONS_5V', 'VBUS', '+5V', '+3V3', '+3V3_RP', 'DVDD']

# ---- references: tools/refs.lock (key -> reference), frozen from the routed Rev0 board (its
# silkscreen, BOM and CPL carry them); a part not in it gets the next free number of its prefix
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
