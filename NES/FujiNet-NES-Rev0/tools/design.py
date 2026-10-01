"""FujiNet-NES Rev0 (RP2354B) -- the single source of truth.

Every part, value, footprint, MPN, LCSC code and pin->net assignment lives
here.  gen_sch.py, check_nets.py and export.py import it; the KiCad files
are generated output.

Circuit provenance: FujiNet-Astrocade-Rev0 (this repository), itself from the
INTV Rev0 cart / PiNTY CARD (CERN-OHL-W-2.0).  Firmware contracts:
  fujinet-firmware pico/nes/firmware/include/nes_cart.h   (RP pins, '595 bits)
  fujinet-firmware pico/nes/README.md                     (decode equations)
  fujinet-firmware include/pinmap/fujiversal-nes.h        (S3 pins)
Edge pinout: nesdev wiki "Cartridge connector", 72-pin NES.
"""

LIB = 'FujiNet-NES'
PROJECT = 'FujiNet-NES-Rev0'
NC = None  # explicit no-connect

SHEETS = [  # (file stem, title, page)
    ('cart-rp2354b', 'RP2354B bus controller, PRG/CHR SRAM, 5V glue, 72-pin edge', 2),
    ('esp32s3-sd', 'ESP32-S3 FujiNet core, microSD, status LED', 3),
    ('usb-uart', 'USB-C, CP2102N programming bridge', 4),
    ('power', 'Power: console 5V / USB VBUS OR, 3.3V buck', 5),
]

# ---- RP2354B (QFN-80) GPIO -> package pin ---------------------------------
# Read from KiCad's MCU_RaspberryPi:RP2350B symbol; gen_sch.py re-checks every
# entry against the symbol's pin names before writing a sheet.
RP_GPIO_PIN = {0: 77, 1: 78, 2: 79, 3: 80, 4: 1, 5: 2, 6: 3, 7: 4, 8: 6, 9: 7, 10: 8, 11: 9,
               12: 11, 13: 12, 14: 13, 15: 14, 16: 16, 17: 17, 18: 18, 19: 19, 20: 20, 21: 21,
               22: 22, 23: 23, 24: 25, 25: 26, 26: 27, 27: 28, 28: 36, 29: 37, 30: 38, 31: 39,
               32: 40, 33: 42, 34: 43, 35: 44, 36: 45, 37: 46, 38: 47, 39: 48, 40: 49, 41: 52,
               42: 53, 43: 54, 44: 55, 45: 56, 46: 57, 47: 58}
RP_IOVDD_PINS = [5, 15, 24, 29, 41, 50, 60, 76]
RP_DVDD_PINS = [10, 32, 51]

# nes_cart.h: all 48 GPIOs.
RP_GPIO_NET = {g: 'CA%d' % g for g in range(13)}                    # CA0_PIN 0
RP_GPIO_NET.update({13 + i: 'CD%d' % i for i in range(8)})          # CD0_PIN 13
RP_GPIO_NET.update({21: 'M2', 22: 'RW', 23: 'ROMSEL_N', 24: 'CA13', 25: 'CA14',
                    26: 'PA10', 27: 'PA11', 28: 'PA12',
                    29: 'SR_SER', 30: 'SR_SCK', 31: 'SR_RCK', 32: 'IRQ_N'})
RP_GPIO_NET.update({33 + i: 'PRG_A%d' % (13 + i) for i in range(6)})   # PRG_BANK_PIN 33
RP_GPIO_NET.update({39 + i: 'CHR_A%d' % (10 + i) for i in range(9)})   # CHR_BANK_PIN 39
assert len(RP_GPIO_NET) == 48 and set(RP_GPIO_NET) == set(RP_GPIO_PIN)

# ESP32-S3-WROOM-1 module pad -> function (pads per the KiCad symbol)
S3_PAD = {'GND': [1, 40, 41], '3V3': 2, 'EN': 3, 'IO4': 4, 'IO5': 5, 'IO6': 6,
          'IO7': 7, 'IO15': 8, 'IO16': 9, 'IO17': 10, 'IO18': 11, 'IO8': 12,
          'IO19': 13, 'IO20': 14, 'IO3': 15, 'IO46': 16, 'IO9': 17, 'IO10': 18,
          'IO11': 19, 'IO12': 20, 'IO13': 21, 'IO14': 22, 'IO21': 23,
          'IO47': 24, 'IO48': 25, 'IO45': 26, 'IO0': 27, 'IO35': 28,
          'IO36': 29, 'IO37': 30, 'IO38': 31, 'IO39': 32, 'IO40': 33,
          'IO41': 34, 'IO42': 35, 'RXD0': 36, 'TXD0': 37, 'IO2': 38, 'IO1': 39}
# fujiversal-nes.h + the fujiversal RUN/BOOTSEL forcing contract (IO4/IO5)
S3_NET = {'EN': 'S3_EN', 'IO0': 'S3_IO0', 'IO4': 'RUN_CTL', 'IO5': 'BOOTSEL_CTL',
          'IO19': 'USB_DM', 'IO20': 'USB_DP', 'IO38': 'SD_MOSI', 'IO39': 'SD_SCK',
          'IO40': 'SD_MISO', 'IO41': 'SD_CS', 'IO42': 'SD_CD', 'IO48': 'LED_STRIP',
          'RXD0': 'S3_RXD', 'TXD0': 'S3_TXD'}

# NES 72-pin edge (nesdev).  (net, symbol pin name).  EXP0-9, the four CIC
# pins and SYSTEM CLK stay unconnected: the CIC is an external CIClone later.
EDGE = {1: ('GND', 'GND'), 2: ('CA11', 'CPU A11'), 3: ('CA10', 'CPU A10'), 4: ('CA9', 'CPU A9'),
        5: ('CA8', 'CPU A8'), 6: ('CA7', 'CPU A7'), 7: ('CA6', 'CPU A6'), 8: ('CA5', 'CPU A5'),
        9: ('CA4', 'CPU A4'), 10: ('CA3', 'CPU A3'), 11: ('CA2', 'CPU A2'), 12: ('CA1', 'CPU A1'),
        13: ('CA0', 'CPU A0'), 14: ('RW', 'CPU R/W'), 15: ('IRQ_N', '~{IRQ}'),
        16: (NC, 'EXP0'), 17: (NC, 'EXP1'), 18: (NC, 'EXP2'), 19: (NC, 'EXP3'), 20: (NC, 'EXP4'),
        21: ('PPU_RD_N', 'PPU ~{RD}'), 22: ('CIRAM_A10', 'CIRAM A10'),
        23: ('PA6', 'PPU A6'), 24: ('PA5', 'PPU A5'), 25: ('PA4', 'PPU A4'), 26: ('PA3', 'PPU A3'),
        27: ('PA2', 'PPU A2'), 28: ('PA1', 'PPU A1'), 29: ('PA0', 'PPU A0'),
        30: ('PD0', 'PPU D0'), 31: ('PD1', 'PPU D1'), 32: ('PD2', 'PPU D2'), 33: ('PD3', 'PPU D3'),
        34: (NC, 'CIC toPak'), 35: (NC, 'CIC toMB'), 36: ('CONS_5V', '+5V'),
        37: (NC, 'SYSTEM CLK'), 38: ('M2', 'M2'), 39: ('CA12', 'CPU A12'), 40: ('CA13', 'CPU A13'),
        41: ('CA14', 'CPU A14'), 42: ('CD7', 'CPU D7'), 43: ('CD6', 'CPU D6'), 44: ('CD5', 'CPU D5'),
        45: ('CD4', 'CPU D4'), 46: ('CD3', 'CPU D3'), 47: ('CD2', 'CPU D2'), 48: ('CD1', 'CPU D1'),
        49: ('CD0', 'CPU D0'), 50: ('ROMSEL_N', '~{ROMSEL}'),
        51: (NC, 'EXP9'), 52: (NC, 'EXP8'), 53: (NC, 'EXP7'), 54: (NC, 'EXP6'), 55: (NC, 'EXP5'),
        56: ('PPU_WR_N', 'PPU ~{WR}'), 57: ('CIRAM_CE_N', 'CIRAM ~{CE}'), 58: ('PA13_N', 'PPU ~{A13}'),
        59: ('PA7', 'PPU A7'), 60: ('PA8', 'PPU A8'), 61: ('PA9', 'PPU A9'), 62: ('PA11', 'PPU A11'),
        63: ('PA10', 'PPU A10'), 64: ('PA12', 'PPU A12'), 65: ('PA13', 'PPU A13'),
        66: ('PD7', 'PPU D7'), 67: ('PD6', 'PPU D6'), 68: ('PD5', 'PPU D5'), 69: ('PD4', 'PPU D4'),
        70: (NC, 'CIC +RST'), 71: (NC, 'CIC CLK'), 72: ('GND', 'GND')}

# AS6C4008 32-pin TSOP-I / sTSOP pin assignment (Alliance datasheet, PIN
# CONFIGURATION).  It is NOT the DIP/SOP order, and pins 6/9 (A17/A18) differ
# from ISSI's TSOP part.
SRAM_PIN = {'A0': 20, 'A1': 19, 'A2': 18, 'A3': 17, 'A4': 16, 'A5': 15, 'A6': 14, 'A7': 13,
            'A8': 3, 'A9': 2, 'A10': 31, 'A11': 1, 'A12': 12, 'A13': 4, 'A14': 11, 'A15': 7,
            'A16': 10, 'A17': 6, 'A18': 9,
            'DQ0': 21, 'DQ1': 22, 'DQ2': 23, 'DQ3': 25, 'DQ4': 26, 'DQ5': 27, 'DQ6': 28, 'DQ7': 29,
            'CE#': 30, 'OE#': 32, 'WE#': 5, 'VCC': 8, 'VSS': 24}

# ---- common parts: (lib_id, footprint, MPN, LCSC) --------------------------
FP = lambda n: '%s:%s' % (LIB, n)
R0603 = FP('R_0603_1608Metric')
C0603 = FP('C_0603_1608Metric')
C0805 = FP('C_0805_2012Metric')
SOIC14 = FP('SOIC-14_3.9x8.7mm_P1.27mm')
SOIC16 = FP('SOIC-16_3.9x9.9mm_P1.27mm')
RES = {'27R': ('0603WAF270JT5E', 'C25190'), '33R': ('0603WAF330JT5E', 'C23140'),
       '330R': ('0603WAF3300T5E', 'C23138'), '1k': ('0603WAF1001T5E', 'C21190'),
       '5.1k': ('0603WAF5101T5E', 'C23186'), '10k': ('0603WAF1002T5E', 'C25804'),
       '22k': ('0603WAF2202T5E', 'C31850'), '47k': ('0603WAF4702T5E', 'C25819'),
       '100k': ('0603WAF1003T5E', 'C25803'), '150k': ('0603WAF1503T5E', 'C22807')}
CAP = {'15pF': (C0603, 'CL10C150JB8NNNC', 'C1644'),
       '100nF': (C0603, 'CC0603KRX7R9BB104', 'C14663'),
       '1uF': (C0603, 'CL10A105KB8NNNC', 'C15849'),
       '4.7uF': (C0603, 'CL10A475KO8NNNC', 'C19666'),
       '10uF': (C0603, 'CL10A106KP8NNNC', 'C19702'),
       '22uF': (C0805, 'CL21A226MAQNNNE', 'C45783')}


class Part:
    def __init__(self, prefix, lib_id, value, footprint, pins, sheet,
                 mpn='', lcsc='', desc='', bom=True):
        self.prefix, self.lib_id, self.value, self.footprint = prefix, lib_id, value, footprint
        self.pins = {str(k): v for k, v in pins.items()}  # pad number -> net (None = NC)
        self.sheet, self.mpn, self.lcsc, self.desc, self.bom = sheet, mpn, lcsc, desc, bom
        self.ref = None


PARTS = []
_sheet = None


def sheet(name):
    global _sheet
    _sheet = name


def add(*a, **k):
    p = Part(*a, sheet=_sheet, **k)
    PARTS.append(p)
    return p


def R(value, a, b, desc=''):
    mpn, lcsc = RES[value]
    return add('R', 'Device:R', value, R0603, {1: a, 2: b}, mpn=mpn, lcsc=lcsc, desc=desc)


def C(value, a, b='GND', desc=''):
    fp, mpn, lcsc = CAP[value]
    return add('C', 'Device:C', value, fp, {1: a, 2: b}, mpn=mpn, lcsc=lcsc, desc=desc)


def SW(value, net, desc):
    return add('SW', 'Switch:SW_Push', value, FP('SW_SPST_TL3342'), {1: net, 2: 'GND'},
               mpn='TL3342F160QG', lcsc='C2886898', desc=desc)


def TP(net, label):
    return add('TP', 'Connector:TestPoint', label, FP('TestPoint_Pad_D1.5mm'), {1: net},
               desc='test pad', bom=False)


def SRAM(addr, data, ce, oe, we, desc):
    """AS6C4008-55TIN: addr = nets for A0..A18, data = nets for DQ0..DQ7."""
    pins = {SRAM_PIN['A%d' % i]: n for i, n in enumerate(addr)}
    pins.update({SRAM_PIN['DQ%d' % i]: n for i, n in enumerate(data)})
    pins.update({SRAM_PIN['CE#']: ce, SRAM_PIN['OE#']: oe, SRAM_PIN['WE#']: we,
                 SRAM_PIN['VCC']: '+5V', SRAM_PIN['VSS']: 'GND'})
    return add('U', '%s:AS6C4008-55TIN' % LIB, 'AS6C4008-55TIN', FP('TSOP-I-32_18.4x8mm_P0.5mm'), pins,
               mpn='AS6C4008-55TIN', lcsc='C5569980', desc=desc)


def GATES4(lib_id, value, mpn, lcsc, gates, desc):
    """Quad 2-input gate, 14-pin: gates = [(in_a, in_b, out)] x4 in package order."""
    pins = {7: 'GND', 14: '+5V'}
    for (a, b, y), (pa, pb, py) in zip(gates, [(1, 2, 3), (4, 5, 6), (9, 10, 8), (12, 13, 11)]):
        pins.update({pa: a, pb: b, py: y})
    return add('U', lib_id, value, SOIC14, pins, mpn=mpn, lcsc=lcsc, desc=desc)


# =========================================================================
sheet('cart-rp2354b')
# -- RP2354B core: the Astrocade RP2354A circuit on the QFN-80 pin-out
rp = {30: 'XIN', 31: 'XOUT', 33: 'SWCLK', 34: 'SWDIO', 35: 'RUN',
      59: '+3V3',                                                   # ADC_AVDD
      61: 'VREG_AVDD', 62: 'GND', 63: 'RP_LX', 64: '+3V3', 65: 'DVDD',   # VREG: AVDD PGND LX VIN FB
      66: 'RP_USB_DM', 67: 'RP_USB_DP', 68: '+3V3', 69: '+3V3',           # USB, USB_OTP_VDD, QSPI_IOVDD
      70: NC, 71: NC, 72: NC, 73: NC, 74: NC,                            # QSPI (flash in package)
      75: 'QSPI_SS', 81: 'GND'}
rp.update({p: '+3V3' for p in RP_IOVDD_PINS})
rp.update({p: 'DVDD' for p in RP_DVDD_PINS})
for g, pin in RP_GPIO_PIN.items():
    rp[pin] = RP_GPIO_NET[g]
add('U', 'MCU_RaspberryPi:RP2354B', 'RP2354B', FP('QFN-80-1EP_10x10mm_P0.4mm_EP3.4x3.4mm'), rp,
    mpn='RP2354B', lcsc='C39843328', desc='RP2350B + 2MB flash in package; cart bus server + bank tables')
add('J', '%s:NES_Cart_Edge_72' % LIB, 'NES_Cart_Edge_72', FP('NES_Cart_Edge_72'),
    {k: v[0] for k, v in EDGE.items()}, desc='72-pin NES cartridge edge, 2.50 mm pitch', bom=False)
# decoupling: one 100nF per IOVDD/DVDD/QSPI/USB/ADC supply pin, bulk on 3V3
for _ in RP_IOVDD_PINS:
    C('100nF', '+3V3', desc='IOVDD decoupling')
C('100nF', '+3V3', desc='QSPI_IOVDD decoupling')
C('100nF', '+3V3', desc='USB_OTP_VDD decoupling')
C('100nF', '+3V3', desc='ADC_AVDD decoupling')
C('4.7uF', '+3V3', desc='VREG_VIN bulk')
C('10uF', '+3V3', desc='RP 3V3 bulk')
for _ in RP_DVDD_PINS:
    C('100nF', 'DVDD', desc='DVDD decoupling')
C('4.7uF', 'DVDD', desc='core regulator output')
R('33R', '+3V3', 'VREG_AVDD', desc='VREG_AVDD filter')
C('4.7uF', 'VREG_AVDD', desc='VREG_AVDD filter')
add('L', 'Device:L', '3.3uH', FP('RPI_L_AOTA-B201610S3R3'), {1: 'DVDD', 2: 'RP_LX'},
    mpn='AOTA-B201610S3R3-101-T', lcsc='C42411119', desc='RP2350 core SMPS inductor')
# 12 MHz crystal
add('Y', 'Device:Crystal_GND24', '12MHz', FP('Crystal_SMD_3225-4Pin_3.2x2.5mm'),
    {1: 'XIN', 2: 'GND', 3: 'XOUT_Y', 4: 'GND'}, mpn='ABM8-272-T3', lcsc='C20625731')
C('15pF', 'XIN', desc='crystal load')
C('15pF', 'XOUT_Y', desc='crystal load')
R('1k', 'XOUT', 'XOUT_Y', desc='crystal drive limit')
# top-face RESET resets both MCUs
SW('RESET', 'RST_BTN', 'cart RESET: RP RUN + S3 EN via BAT54C')
add('D', 'Diode:BAT54C', 'BAT54C', FP('SOT-23'), {1: 'RUN', 2: 'S3_EN', 3: 'RST_BTN'},
    mpn='BAT54C,215', lcsc='C37704', desc='RESET steering, common cathode')
# RUN / BOOTSEL.  The S3 forces them exactly as fnPicoUpdater::
# forceBootselViaPins() expects: its pins idle as inputs and are driven LOW
# to assert.  Same 3.3V rail on both chips, so a 1k series resistor is the
# whole interface (an NPN driver here would invert the firmware's polarity).
R('10k', '+3V3', 'RUN', desc='RUN pull-up')
R('10k', '+3V3', 'QSPI_SS', desc='QSPI_SS pull-up')
R('1k', 'QSPI_SS', 'BOOTSEL_BTN', desc='BOOTSEL button series')
SW('BOOTSEL', 'BOOTSEL_BTN', 'RP2354 BOOTSEL (hold while pressing RESET)')
R('1k', 'RUN_CTL', 'RUN', desc='S3 IO4 -> RP RUN (drive low = reset)')
R('1k', 'BOOTSEL_CTL', 'QSPI_SS', desc='S3 IO5 -> RP QSPI_SS (low through reset = BOOTSEL)')
# RP <-> S3 native USB (RP = CDC device, S3 = host)
R('27R', 'USB_DP', 'RP_USB_DP', desc='USB series')
R('27R', 'USB_DM', 'RP_USB_DM', desc='USB series')
TP('SWCLK', 'SWCLK')
TP('SWDIO', 'SWDIO')
TP('GND', 'GND')
TP('RUN', 'RUN')
TP('M2', 'M2')
TP('SR_SPARE', 'SR_SPARE')

# -- console power sense: edge +5V (before the OR diode) -> 3.0V -> '14
R('100k', 'CONS_5V', 'VSENSE', desc='console 5V sense divider')
R('150k', 'VSENSE', 'GND', desc='console 5V sense -> 3.0V')

# -- PRG / CHR SRAM on the 5V rail: their outputs drive the 5V bus directly
SRAM(['CA%d' % i for i in range(13)] + ['PRG_A%d' % i for i in range(13, 19)],
     ['CD%d' % i for i in range(8)], 'PRG_CE_N', 'PRG_OE_N', 'PRG_WE_N',
     desc='PRG SRAM 512Kx8: $8000-$FFFF through the 4 x 8K bank table (GP33-38)')
SRAM(['PA%d' % i for i in range(10)] + ['CHR_A%d' % i for i in range(10, 19)],
     ['PD%d' % i for i in range(8)], 'PA13', 'CHR_OE_N', 'CHR_WE_N',
     desc='CHR SRAM 512Kx8: PPU $0000-$1FFF through the 8 x 1K bank table (GP39-47)')
C('100nF', '+5V', desc='PRG SRAM decoupling')
C('100nF', '+5V', desc='CHR SRAM decoupling')
C('10uF', '+5V', desc='5V logic domain bulk')

# -- 74HCT595: the slow control bits, Q0 first (SR_* in nes_cart.h)
add('U', '74xx:74HCT595', '74HCT595', SOIC16,
    {14: 'SR_SER', 11: 'SR_SCK', 12: 'SR_RCK', 13: 'GND', 10: '+5V',          # SER SRCLK RCLK /OE /SRCLR
     15: 'SRAM_EN', 1: 'PRG_WE_EN', 2: 'CHR_WE_EN', 3: 'MIR0', 4: 'MIR1',     # QA..QE
     5: 'FOURSCREEN', 6: 'SR_LED', 7: 'SR_SPARE', 9: NC, 8: 'GND', 16: '+5V'},  # QF QG QH QH'
    mpn='74HCT595D,118', lcsc='C282339', desc='control bits: SRAM_EN PRG_WE_EN CHR_WE_EN MIR0 MIR1 FOURSCREEN LED spare')
# -- 74HCT253 half a: CIRAM A10 = {PA10, PA11, 0, 1}[MIR1:MIR0], released when the console is off
add('U', '74xx:74LS253', '74HCT253', SOIC16,
    {1: 'PWR_OK_N', 6: 'PA10', 5: 'PA11', 4: 'GND', 3: '+5V', 7: 'CIRAM_A10',   # /OEa I0a I1a I2a I3a Za
     14: 'MIR0', 2: 'MIR1',                                                    # A0 A1 (shared selects)
     15: '+5V', 10: 'GND', 11: 'GND', 12: 'GND', 13: 'GND', 9: NC,             # half b unused
     8: 'GND', 16: '+5V'},
    mpn='74HCT253D,653', lcsc='C547509', desc='CIRAM A10 mirroring mux (tri-state, /OE = PWR_OK_N)')
# -- 74HCT14: PWR_OK, and the inversions the gates below need
add('U', '74xx:74HC14', '74HCT14', SOIC14,
    {1: 'VSENSE', 2: 'PWR_OK_N', 3: 'PWR_OK_N', 4: 'PWR_OK', 5: 'ROMSEL_N', 6: 'ROMSEL',
     9: 'CHR_WE_EN', 8: 'CHR_WE_EN_N', 11: 'FOURSCREEN_OK_N', 10: 'FOURSCREEN_OK',
     13: 'GND', 12: NC, 7: 'GND', 14: '+5V'},
    mpn='SN74HCT14DR', lcsc='C6769', desc='PWR_OK / PWR_OK_N from the console 5V sense; ROMSEL, CHR_WE_EN, FOURSCREEN inversions')
# -- 74HCT00
GATES4('74xx:74HCT00', '74HCT00', 'SN74HCT00DR', 'C6764',
       [('ROMSEL', 'SRAM_EN', 'PRG_CE_N'),            # /CE = !(!ROMSEL & SRAM_EN)
        ('RW', 'PWR_OK', 'PRG_OE_N'),                 # /OE = !(R/W & PWR_OK)
        ('ROMSEL', 'PRG_WE_EN', 'PRG_WGATE_N'),       # !(!ROMSEL & PRG_WE_EN), ORed with R/W below
        ('FOURSCREEN', 'PWR_OK', 'FOURSCREEN_OK_N')], # FOURSCREEN only while the console is powered
       desc='PRG SRAM /CE, /OE, write gate; FOURSCREEN & PWR_OK')
# -- 74HCT32
GATES4('74xx:74LS32', '74HCT32', '74HCT32D,653', 'C5985',
       [('PPU_RD_N', 'PWR_OK_N', 'CHR_OE_N'),         # /OE = !(!/RD & PWR_OK)
        ('PPU_WR_N', 'CHR_WE_EN_N', 'CHR_WE_N'),      # /WE = /WR | !CHR_WE_EN
        ('PRG_WGATE_N', 'RW', 'PRG_WE_N'),            # /WE = !(!ROMSEL & !R/W & PRG_WE_EN)
        ('PA13_N', 'FOURSCREEN_OK', 'CIRAM_CE_N')],   # CIRAM /CE = /A13 | FOURSCREEN
       desc='CHR SRAM /OE, /WE; PRG SRAM /WE; CIRAM /CE')
for n in ('74HCT595', '74HCT253', '74HCT14', '74HCT00', '74HCT32'):
    C('100nF', '+5V', desc=n + ' VCC decoupling')
# -- activity LED from the '595 (5V, 1k: ~3 mA)
R('1k', 'SR_LED', 'SR_LED_A', desc='LED series')
add('D', 'Device:LED', 'green', FP('LED_0603_1608Metric'), {1: 'GND', 2: 'SR_LED_A'},
    mpn='KT-0603G', lcsc='C12624', desc="activity LED ('595 QG)")

# =========================================================================
sheet('esp32s3-sd')
s3 = {}
for fn, pad in S3_PAD.items():
    for p in (pad if isinstance(pad, list) else [pad]):
        s3[p] = 'GND' if fn == 'GND' else '+3V3' if fn == '3V3' else S3_NET.get(fn, NC)
add('U', 'RF_Module:ESP32-S3-WROOM-1', 'ESP32-S3-WROOM-1-N16R8', FP('ESP32-S3-WROOM-1'), s3,
    mpn='ESP32-S3-WROOM-1-N16R8', lcsc='C2913202', desc='FujiNet core (fujiversal-nes)')
C('22uF', '+3V3', desc='S3 bulk (WiFi TX bursts)')
C('100nF', '+3V3', desc='S3 decoupling')
R('10k', '+3V3', 'S3_EN', desc='EN pull-up')
C('1uF', 'S3_EN', desc='EN power-on delay')
SW('S3_RST', 'S3_EN', 'ESP32-S3 EN')
SW('S3_BOOT', 'S3_IO0', 'ESP32-S3 BOOT (IO0)')
add('J', '%s:MicroSD_TF015' % LIB, 'microSD', FP('TF-SMD_TF-015'),
    {1: 'SD_DAT2', 2: 'SD_CS', 3: 'SD_MOSI', 4: '+3V3', 5: 'SD_SCK', 6: 'GND',
     7: 'SD_MISO', 8: 'SD_DAT1', 9: 'SD_CD', 10: 'GND', 11: 'GND', 12: 'GND', 13: 'GND'},
    mpn='TF-015', lcsc='C113206', desc='microSD push-push, SPI mode')
add('RN', 'Device:R_Pack04', '4x10k', FP('R_Array_Convex_4x0603'),
    {1: 'SD_CS', 2: 'SD_MISO', 3: 'SD_DAT1', 4: 'SD_DAT2', 5: '+3V3', 6: '+3V3', 7: '+3V3', 8: '+3V3'},
    mpn='4D03WGJ0103T5E', lcsc='C29718', desc='SD pull-ups')
R('10k', '+3V3', 'SD_CD', desc='card-detect pull-up')
C('10uF', '+3V3', desc='microSD supply')
R('330R', 'LED_STRIP', 'WS_DIN', desc='WS2812 data series')
add('D', 'LED:WS2812B-2020', 'WS2812B-2020-V6', FP('LED_WS2812B-2020_PLCC4_2.0x2.0mm'),
    {1: NC, 2: 'GND', 3: 'WS_DIN', 4: '+3V3'}, mpn='WS2812B-2020-V6', lcsc='C52917434',
    desc='status LED (3.3V-rated V6 part: no data-level shifting needed)')
C('100nF', '+3V3', desc='WS2812 decoupling')

# =========================================================================
sheet('usb-uart')
add('J', 'Connector:USB_C_Receptacle_USB2.0_16P', 'USB-C', FP('USB_C_Receptacle_HRO_TYPE-C-31-M-12'),
    {'A1': 'GND', 'A4': 'VBUS', 'A5': 'CC1', 'A6': 'UBRG_DP', 'A7': 'UBRG_DM', 'A8': NC,
     'A9': 'VBUS', 'A12': 'GND', 'B1': 'GND', 'B4': 'VBUS', 'B5': 'CC2', 'B6': 'UBRG_DP',
     'B7': 'UBRG_DM', 'B8': NC, 'B9': 'VBUS', 'B12': 'GND', 'SH': 'GND'},
    mpn='TYPE-C-31-M-12', lcsc='C165948', desc='power + S3 programming')
R('5.1k', 'CC1', 'GND', desc='UFP Rd')
R('5.1k', 'CC2', 'GND', desc='UFP Rd')
for n in ('UBRG_DP', 'UBRG_DM', 'VBUS'):
    add('D', 'Diode:ESD5Zxx', 'ESD5Z5.0T1G', FP('D_SOD-523'), {1: n, 2: 'GND'},
        mpn='ESD5Z5.0T1G', lcsc='C82044', desc='ESD')
cp = {i: NC for i in range(1, 30)}
cp.update({3: 'GND', 4: 'UBRG_DP', 5: 'UBRG_DM', 6: '+3V3', 7: '+3V3', 8: 'VBUS_SNS',
           9: 'CP_RST', 23: 'GND', 24: 'UART_RTS', 25: 'S3_TXD', 26: 'S3_RXD',
           28: 'UART_DTR', 29: 'GND'})
add('U', 'Interface_USB:CP2102N-Axx-xQFN28', 'CP2102N-A02-GQFN28', FP('QFN-28-1EP_5x5mm_P0.5mm_EP3.35x3.35mm'),
    cp, mpn='CP2102N-A02-GQFN28R', lcsc='C964632', desc='USB-UART for S3 flashing/console (self-powered)')
C('100nF', '+3V3', desc='CP2102N VDD')
C('4.7uF', '+3V3', desc='CP2102N VDD bulk')
R('22k', 'VBUS', 'VBUS_SNS', desc='VBUS sense divider')
R('47k', 'VBUS_SNS', 'GND', desc='VBUS sense divider')
R('10k', '+3V3', 'CP_RST', desc='/RST pull-up')
add('U', 'Transistor_BJT:UMH3N', 'UMH3N', FP('SOT-363_SC-70-6'),
    {1: 'UART_RTS', 2: 'UART_DTR', 6: 'S3_EN', 3: 'S3_IO0', 4: 'UART_DTR', 5: 'UART_RTS'},
    mpn='UMH3N', lcsc='C62892', desc='esptool auto-program (DevKitC-1 style)')

# =========================================================================
sheet('power')
# CONS_5V is the edge rail, +5V the diode-OR of it and VBUS: the buck input
# AND the supply of the 5V logic and both SRAMs.
add('D', 'Diode:SS34', 'SS34', FP('D_SMA'), {1: '+5V', 2: 'CONS_5V'}, mpn='SS34', lcsc='C8678',
    desc='console 5V OR-ing')
add('D', 'Diode:SS34', 'SS34', FP('D_SMA'), {1: '+5V', 2: 'VBUS'}, mpn='SS34', lcsc='C8678',
    desc='USB VBUS OR-ing (no back-feed into the console)')
C('100nF', 'CONS_5V', desc='edge 5V HF bypass')
C('22uF', '+5V', desc='buck input')
C('22uF', '+5V', desc='buck input')
C('22uF', '+5V', desc='+5V bulk')
C('100nF', '+5V', desc='buck input HF')
add('U', 'Regulator_Switching:AP63203WU', 'AP63203WU', FP('TSOT-23-6'),
    {1: '+3V3', 2: '+5V', 3: '+5V', 4: 'GND', 5: 'BUCK_SW', 6: 'BUCK_BST'},
    mpn='AP63203WU-7', lcsc='C780769', desc='3.3V 2A buck')
C('100nF', 'BUCK_SW', 'BUCK_BST', desc='bootstrap')
add('L', 'Device:L', '6.8uH', FP('L_Sunlord_SWPA4030S'), {1: 'BUCK_SW', 2: '+3V3'},
    mpn='SWPA4030S6R8MT', lcsc='C62684', desc='buck inductor')
C('22uF', '+3V3', desc='buck output')
C('22uF', '+3V3', desc='buck output')

# PWR_FLAGs: nets whose drivers are passive pins
PWR_FLAG_NETS = ['GND', 'CONS_5V', 'VBUS', '+5V', '+3V3', 'DVDD', 'VREG_AVDD']

# ---- reference assignment (stable: declaration order) ---------------------
_count = {}
for p in PARTS:
    _count[p.prefix] = _count.get(p.prefix, 0) + 1
    p.ref = '%s%d' % (p.prefix, _count[p.prefix])

BY_REF = {p.ref: p for p in PARTS}


def nets():
    out = {}
    for p in PARTS:
        for pad, n in p.pins.items():
            if n:
                out.setdefault(n, []).append((p.ref, pad))
    return out


if __name__ == '__main__':
    for p in PARTS:
        print(p.sheet, p.ref, p.value, p.footprint.split(':')[1], p.lcsc)
    ns = nets()
    print(len(PARTS), 'parts', len(ns), 'nets')
    for n, pp in sorted(ns.items()):
        if len(pp) < 2:
            print('SINGLE-PIN NET', n, pp)
