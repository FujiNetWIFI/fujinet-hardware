"""FujiNet-7800 Rev0 (RP2354B) -- the single source of truth.

Every part, value, footprint, MPN, LCSC code and pin->net assignment lives
here.  gen_sch.py, check_nets.py, check_glue.py and export.py import it; the
KiCad files are generated output.

Circuit provenance: FujiNet-SMS-Rev0 / FujiNet-NES-Rev0 (this repository) for
the RP2354B core, the ESP32-S3 / microSD / USB-UART / power sheets and the S3
pin contract; the cart side (edge, SRAM, glue, audio) is new.  Firmware contract:
  fujinet-firmware pico/atari-7800/firmware/include/a78_cart.h  (RP pins, glue equations)
  fujinet-firmware pico/atari-7800/firmware/include/a78map.h    (slot word: GPIO32-40)
Edge pinout: Dan Boris, "Atari 7800 cartridge" (see EDGE below).
"""

LIB = 'FujiNet-7800'
PROJECT = 'FujiNet-7800-Rev0'
NC = None  # explicit no-connect

SHEETS = [  # (file stem, title, page) -- in signal-flow order, console side first
    ('edge', '32-pin 7800 cart edge, cart audio', 2),
    ('rp2354b', 'RP2354B bus controller', 3),
    ('sram', '512K SRAM: AS6C4008', 4),
    ('glue', '5V glue: CARTSEL, SRAM /OE, /WE, A8, PWR_OK', 5),
    ('esp32s3-sd', 'ESP32-S3, microSD, status LED', 6),
    ('usb-uart', 'USB-C, CP2102N bridge', 7),
    ('power', 'Power: 5V OR, 3.3V buck, RP LDO', 8),
]

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

# a78_cart.h.  GPIO0-31 are the 5 V-tolerant bus inputs; GPIO40-47 are not and
# only drive 5 V CMOS inputs (A8MASK) or the 3.3 V debug header.
RP_GPIO_NET = {i: 'RP_D%d' % i for i in range(8)}                    # D0_PIN 0 (100R to D0-D7)
RP_GPIO_NET.update({8 + i: 'A%d' % i for i in range(16)})           # A0_PIN 8
RP_GPIO_NET.update({24: 'RW', 25: 'PHI2', 26: 'HALT_N', 27: 'PWR_OK', 28: 'IRQ_GATE',
                    29: 'AUD_PWM', 30: 'RP_LED', 31: NC})
RP_GPIO_NET.update({32 + i: 'SA%d' % (13 + i) for i in range(6)})   # SLOT_PIN 32: SRAM A13-A18
RP_GPIO_NET.update({38: 'ROM_EN', 39: 'RAM_EN', 40: 'A8MASK', 41: NC, 42: NC, 43: NC,
                    44: 'DBG_TX', 45: 'DBG_RX', 46: NC, 47: NC})
assert len(RP_GPIO_NET) == 48 and set(RP_GPIO_NET) == set(RP_GPIO_PIN)

# ESP32-S3-WROOM-1 module pad -> function (pads per the KiCad symbol)
S3_PAD = {'GND': [1, 40, 41], '3V3': 2, 'EN': 3, 'IO4': 4, 'IO5': 5, 'IO6': 6,
          'IO7': 7, 'IO15': 8, 'IO16': 9, 'IO17': 10, 'IO18': 11, 'IO8': 12,
          'IO19': 13, 'IO20': 14, 'IO3': 15, 'IO46': 16, 'IO9': 17, 'IO10': 18,
          'IO11': 19, 'IO12': 20, 'IO13': 21, 'IO14': 22, 'IO21': 23,
          'IO47': 24, 'IO48': 25, 'IO45': 26, 'IO0': 27, 'IO35': 28,
          'IO36': 29, 'IO37': 30, 'IO38': 31, 'IO39': 32, 'IO40': 33,
          'IO41': 34, 'IO42': 35, 'RXD0': 36, 'TXD0': 37, 'IO2': 38, 'IO1': 39}
# the SMS board's S3 side (fujiversal-sms.h + the RUN/BOOTSEL forcing contract on IO4/IO5)
S3_NET = {'EN': 'S3_EN', 'IO0': 'S3_IO0', 'IO4': 'RUN_CTL', 'IO5': 'BOOTSEL_CTL',
          'IO19': 'USB_DM', 'IO20': 'USB_DP', 'IO38': 'SD_MOSI', 'IO39': 'SD_SCK',
          'IO40': 'SD_MISO', 'IO41': 'SD_CS', 'IO42': 'SD_CD', 'IO48': 'LED_STRIP',
          'RXD0': 'S3_RXD', 'TXD0': 'S3_TXD'}

# Atari 7800 32-pin cartridge edge: (net, symbol pin name).  Dan Boris
# (atarihq.com/danb/7800cart), hardwarebook.info and allpinouts agree; pins
# 3-14 and 19-30 are the 2600's 24.  Pins 1-16 on one face, 17-32 on the
# other, pin k over pin 33-k.  Every pin is used.
EDGE = {1: ('RW', 'R/~{W}'), 2: ('HALT_N', '~{HALT}'), 3: ('D3', 'D3'), 4: ('D4', 'D4'),
        5: ('D5', 'D5'), 6: ('D6', 'D6'), 7: ('D7', 'D7'), 8: ('A12', 'A12'), 9: ('A10', 'A10'),
        10: ('A11', 'A11'), 11: ('A9', 'A9'), 12: ('A8', 'A8'), 13: ('CONS_5V', '+5V'),
        14: ('GND', 'GND'), 15: ('A13', 'A13'), 16: ('A14', 'A14'), 17: ('A15', 'A15'),
        18: ('EAUDIO', 'EAUDIO'), 19: ('A7', 'A7'), 20: ('A6', 'A6'), 21: ('A5', 'A5'),
        22: ('A4', 'A4'), 23: ('A3', 'A3'), 24: ('A2', 'A2'), 25: ('A1', 'A1'), 26: ('A0', 'A0'),
        27: ('D0', 'D0'), 28: ('D1', 'D1'), 29: ('D2', 'D2'), 30: ('GND', 'GND'),
        31: ('IRQ_N', '~{IRQ}'), 32: ('PHI2', 'PHI2')}

# AS6C4008 32-pin TSOP-I / sTSOP pin assignment (Alliance datasheet, PIN
# CONFIGURATION), as verified for the NES board.  NOT the DIP/SOP order.
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
RES = {'27R': ('0603WAF270JT5E', 'C25190'), '33R': ('0603WAF330JT5E', 'C23140'),
       '330R': ('0603WAF3300T5E', 'C23138'), '1k': ('0603WAF1001T5E', 'C21190'),
       '1.5k': ('0603WAF1501T5E', 'C22843'),
       '5.1k': ('0603WAF5101T5E', 'C23186'), '10k': ('0603WAF1002T5E', 'C25804'),
       '22k': ('0603WAF2202T5E', 'C31850'), '47k': ('0603WAF4702T5E', 'C25819'),
       '100k': ('0603WAF1003T5E', 'C25803')}
CAP = {'15pF': (C0603, 'CL10C150JB8NNNC', 'C1644'),
       '10nF': (C0603, '0603B103K500NT', 'C57112'),
       '100nF': (C0603, 'CC0603KRX7R9BB104', 'C14663'),
       '1uF': (C0603, 'CL10A105KB8NNNC', 'C15849'),
       '4.7uF': (C0603, 'CL10A475KO8NNNC', 'C19666'),
       '10uF': (C0603, 'CL10A106KP8NNNC', 'C19702'),
       '22uF': (C0805, 'CL21A226MAQNNNE', 'C45783')}
RPACK = {'4x10k': ('4D03WGJ0103T5E', 'C29718'), '4x100R': ('4D03WGJ0101T5E', 'C25506')}


class Part:
    def __init__(self, prefix, lib_id, value, footprint, pins, sheet,
                 mpn='', lcsc='', desc='', bom=True, dnp=False, ds=''):
        self.prefix, self.lib_id, self.value, self.footprint = prefix, lib_id, value, footprint
        self.pins = {str(k): v for k, v in pins.items()}  # pad number -> net (None = NC)
        self.sheet, self.mpn, self.lcsc, self.desc, self.bom, self.dnp = sheet, mpn, lcsc, desc, bom, dnp
        self.ds = ds                                       # datasheet URL when the stock symbol's is another part's
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


def R(value, a, b, desc='', **k):
    mpn, lcsc = RES[value]
    return add('R', 'Device:R', value, R0603, {1: a, 2: b}, mpn=mpn, lcsc=lcsc, desc=desc, **k)


def C(value, a, b='GND', desc='', **k):
    fp, mpn, lcsc = CAP[value]
    return add('C', 'Device:C', value, fp, {1: a, 2: b}, mpn=mpn, lcsc=lcsc, desc=desc, **k)


def RN(value, nets, common, desc=''):
    """4-resistor array: nets[0..3] on pins 1-4, common on 5-8 (R_Pack04: Rn.1 = pin n, Rn.2 = pin 9-n)."""
    return RN4(value, nets, [common] * 4, desc)


def RN4(value, a, b, desc=''):
    """4-resistor array, four separate resistors: a[k] on pin k+1, b[k] on pin 8-k."""
    mpn, lcsc = RPACK[value]
    pins = {i + 1: n for i, n in enumerate(a)}
    pins.update({8 - i: n for i, n in enumerate(b)})
    return add('RN', 'Device:R_Pack04', value, FP('R_Array_Convex_4x0603'), pins, mpn=mpn, lcsc=lcsc, desc=desc)


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


# 14-pin gate packages: unit -> (input pins, output pin); 7 GND, 14 VCC.
# The '20's pins 3 and 11 are NC (no pin in the symbol).
GATE_PINS = {
    '74HCT14': [((1,), 2), ((3,), 4), ((5,), 6), ((9,), 8), ((11,), 10), ((13,), 12)],
    '74HCT00': [((1, 2), 3), ((4, 5), 6), ((9, 10), 8), ((12, 13), 11)],
    '74HCT20': [((1, 2, 4, 5), 6), ((9, 10, 12, 13), 8)],
}
GATE_PARTS = {  # value -> (lib_id, MPN, LCSC, datasheet); the '20 / '14 use the LS / HC symbols
    '74HCT14': ('74xx:74HC14', 'SN74HCT14DR', 'C6769', 'https://www.ti.com/lit/ds/symlink/sn74hct14.pdf'),
    '74HCT00': ('74xx:74HCT00', 'SN74HCT00DR', 'C6764', 'https://www.ti.com/lit/ds/symlink/sn74hct00.pdf'),
    '74HCT20': ('74xx:74LS20', 'CD74HCT20M96', 'C2878717', 'https://www.ti.com/lit/ds/symlink/cd74hct20.pdf'),
}


def GATES(value, gates, desc):
    """A 14-pin gate package: gates = [(inputs..., output)] in unit order."""
    lib_id, mpn, lcsc, ds = GATE_PARTS[value]
    pins = {7: 'GND', 14: '+5V'}
    for g, (ins, out) in zip(gates, GATE_PINS[value]):
        assert len(g) == len(ins) + 1, (value, g)
        pins.update({p: n for p, n in zip(ins, g[:-1])})
        pins[out] = g[-1]
    return add('U', lib_id, value, SOIC14, pins, mpn=mpn, lcsc=lcsc, desc=desc, ds=ds)


# =========================================================================
sheet('rp2354b')
# -- RP2354B core: the NES / SMS Rev0 circuit unchanged (declared in the same
# order, so the references match those boards').  Every RP supply pin on
# +3V3_RP, the LDO that tracks the 5 V rail, so the pads are powered before the
# console's bus levels reach them.
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
add('U', 'MCU_RaspberryPi:RP2354B', 'RP2354B', FP('QFN-80-1EP_10x10mm_P0.4mm_EP3.4x3.4mm'), rp,
    mpn='RP2354B', lcsc='C39843328', desc='RP2350B + 2MB flash in package; cart bus server + slot table')
sheet('edge')
add('J', '%s:Atari7800_Cart_Edge_32' % LIB, 'Atari7800_Cart_Edge_32', FP('Atari7800_Cart_Edge_32'),
    {k: v[0] for k, v in EDGE.items()}, desc='Atari 7800 32-pin cartridge edge, 2.54 mm pitch', bom=False)
sheet('rp2354b')
for _ in RP_IOVDD_PINS:
    C('100nF', RP_IO_RAIL, desc='IOVDD decoupling')
C('100nF', RP_IO_RAIL, desc='QSPI_IOVDD decoupling')
C('100nF', RP_IO_RAIL, desc='USB_OTP_VDD decoupling')
C('100nF', RP_IO_RAIL, desc='ADC_AVDD decoupling')
C('10uF', RP_IO_RAIL, desc='RP IO rail bulk (LDO output)')
C('4.7uF', RP_CORE_RAIL, desc='VREG_VIN bulk (LDO rail)')
for _ in RP_DVDD_PINS:
    C('100nF', 'DVDD', desc='DVDD decoupling')
C('4.7uF', 'DVDD', desc='core regulator output')
R('33R', RP_CORE_RAIL, 'VREG_AVDD', desc='VREG_AVDD filter')
C('4.7uF', 'VREG_AVDD', desc='VREG_AVDD filter')
add('L', 'Device:L', '3.3uH', FP('RPI_L_AOTA-B201610S3R3'), {1: 'DVDD', 2: 'RP_LX'},
    mpn='AOTA-B201610S3R3-101-T', lcsc='C42411119', desc='RP2350 core SMPS inductor')
add('Y', 'Device:Crystal_GND24', '12MHz', FP('Crystal_SMD_3225-4Pin_3.2x2.5mm'),
    {1: 'XIN', 2: 'GND', 3: 'XOUT_Y', 4: 'GND'}, mpn='ABM8-272-T3', lcsc='C20625731', desc='RP2350 12 MHz crystal')
C('15pF', 'XIN', desc='crystal load')
C('15pF', 'XOUT_Y', desc='crystal load')
R('1k', 'XOUT', 'XOUT_Y', desc='crystal drive limit')
SW('RESET', 'RST_BTN', 'cart RESET: RP RUN + S3 EN via BAT54C')
add('D', 'Diode:BAT54C', 'BAT54C', FP('SOT-23'), {1: 'RUN', 2: 'S3_EN', 3: 'RST_BTN'},
    mpn='BAT54C,215', lcsc='C37704', desc='RESET steering, common cathode')
# RUN / BOOTSEL: the S3 drives them low to assert (fnPicoUpdater::forceBootselViaPins)
R('10k', RP_IO_RAIL, 'RUN', desc='RUN pull-up')
R('10k', RP_IO_RAIL, 'QSPI_SS', desc='QSPI_SS pull-up')
R('1k', 'QSPI_SS', 'BOOTSEL_BTN', desc='BOOTSEL button series')
SW('BOOTSEL', 'BOOTSEL_BTN', 'RP2354 BOOTSEL (hold while pressing RESET)')
R('1k', 'RUN_CTL', 'RUN', desc='S3 IO4 -> RP RUN (drive low = reset)')
R('1k', 'BOOTSEL_CTL', 'QSPI_SS', desc='S3 IO5 -> RP QSPI_SS (low through reset = BOOTSEL)')
R('27R', 'USB_DP', 'RP_USB_DP', desc='USB series')
R('27R', 'USB_DM', 'RP_USB_DM', desc='USB series')
TP('SWCLK', 'SWCLK')
TP('SWDIO', 'SWDIO')
TP('GND', 'GND')
TP('RUN', 'RUN')
# -- the 7800 cart side of the RP.  D0-D7 through 100R: the RP and the SRAM /
# console never fight at full drive if a turnaround overlaps.
RN4('4x100R', ['RP_D%d' % i for i in range(4)], ['D%d' % i for i in range(4)],
    desc='D0-D7 100R series: RN1 GPIO0-3, RN2 GPIO4-7')
RN4('4x100R', ['RP_D%d' % i for i in range(4, 8)], ['D%d' % i for i in range(4, 8)],
    desc='D0-D7 100R series: RN1 GPIO0-3, RN2 GPIO4-7')
# activity LED straight off GPIO30 (3.3 V): red, ~1.3 mA
R('1k', 'RP_LED', 'RP_LED_A', desc='activity LED series')
add('D', 'Device:LED', 'red', FP('LED_0603_1608Metric'), {1: 'GND', 2: 'RP_LED_A'},
    mpn='KT-0603R', lcsc='C2286', desc='activity LED (GPIO30)')
# /IRQ: GPIO28 high = the 2N7002 pulls console /IRQ low.  Fitted, never
# asserted by the firmware; the gate pull-down keeps /IRQ released until the
# firmware drives GPIO28 low.
add('Q', 'Transistor_FET:2N7002', '2N7002', FP('SOT-23'), {1: 'IRQ_GATE', 2: 'GND', 3: 'IRQ_N'},
    mpn='2N7002', lcsc='C8545', desc='console /IRQ pull-down (G = GPIO28); never asserted')
R('10k', 'IRQ_GATE', 'GND', desc='/IRQ released from power-on until the firmware drives GPIO28')
# debug UART (GPIO44 TX, GPIO45 RX; 3.3 V only), DNP: fit for bring-up
add('J', 'Connector_Generic:Conn_01x03', 'DBG UART', FP('PinHeader_1x03_P2.54mm_Vertical'),
    {1: 'DBG_TX', 2: 'DBG_RX', 3: 'GND'}, mpn='PZ254V-11-03P', lcsc='C2937625',
    desc='RP debug UART, 3.3 V: 1 TX (GPIO44), 2 RX (GPIO45), 3 GND; fit for bring-up', dnp=True)

sheet('edge')
# -- cart audio: GPIO29 PWM (833 kHz carrier, a78 fuji_audio.c) -> 1.5k / 10n
# (fc 10.6 kHz) -> 10k level (PROVISIONAL) -> 1u DC block -> edge 18 EAUDIO.
# The block leaves the console's audio node at its no-cart DC level.
R('1.5k', 'AUD_PWM', 'AUD_LP', desc='audio PWM low-pass, fc 10.6 kHz')
C('10nF', 'AUD_LP', desc='audio PWM low-pass, fc 10.6 kHz')
R('10k', 'AUD_LP', 'AUD_LVL', desc='EAUDIO level (PROVISIONAL)')
C('1uF', 'AUD_LVL', 'EAUDIO', desc='EAUDIO DC block')

sheet('sram')
# -- 512K on the 5 V rail: console A0-A7, A9-A12 and D0-D7 direct; A8 through
# the glue (A8MASK); the RP's slot lines SA13-SA18.  /CE tied active.
SRAM(['A%d' % i for i in range(8)] + ['SA8'] + ['A%d' % i for i in range(9, 13)] +
     ['SA%d' % i for i in range(13, 19)],
     ['D%d' % i for i in range(8)], 'GND', 'SRAM_OE_N', 'SRAM_WE_N',
     desc='512Kx8 SRAM, 5 V: 64 x 8K pages, slot page from the PIO table')
C('100nF', '+5V', desc='SRAM decoupling')
C('10uF', '+5V', desc='5V logic domain bulk')

sheet('glue')
# -- console power sense: edge +5V (before the P-FET) -> 0.82 x -> '14 Schmitt
R('22k', 'CONS_5V', 'VSENSE', desc='console 5V sense divider')
R('100k', 'VSENSE', 'GND', desc='console 5V sense -> 0.82 x CONS_5V')
# -- the glue, four packages, every gate used (a78_cart.h a78_cartsel,
# a78_glue_oe / _we / _a8; tools/check_glue.py evaluates this netlist against
# them for every input).  PWR_OK is folded into CARTSEL:
#   LOW_X   = A13 | !A11                                $x000-$x7FF or A13
#   CSEL_P  = PWR_OK & (A15 | A14 | A12 & LOW_X)        = PWR_OK & CARTSEL
#   /OE     = !(CSEL_P & RW & ROM_EN)
#   /WE     = !(CSEL_P & !RW & PHI2 & RAM_EN)           PHI2 one gate from /WE
#   SRAM A8 = A8 & !A8MASK
GATES('74HCT14', [('VSENSE', 'PWR_OK_N'), ('PWR_OK_N', 'PWR_OK'), ('A13', 'A13_N'),
                  ('RW', 'RW_N'), ('A8MASK', 'A8MASK_N'), ('SA8_N', 'SA8')],
      desc='PWR_OK from the console 5V sense; A13, R/W, A8MASK, SRAM A8 inversions')
GATES('74HCT00', [('A13_N', 'A11', 'LOW_X'),
                  ('A15', 'PWR_OK', 'A15_P_N'),
                  ('A14', 'PWR_OK', 'A14_P_N'),
                  ('A8', 'A8MASK_N', 'SA8_N')],
      desc='LOW_X = A13 | !A11; A15, A14 & PWR_OK; SRAM A8 mask')
GATES('74HCT20', [('A12', 'LOW_X', 'PWR_OK', '+5V', 'LOW_P_N'),
                  ('A15_P_N', 'A14_P_N', 'LOW_P_N', '+5V', 'CSEL_P')],
      desc='U5: CSEL_P = PWR_OK & CARTSEL; U6: SRAM /OE, /WE')
GATES('74HCT20', [('CSEL_P', 'RW', 'ROM_EN', '+5V', 'SRAM_OE_N'),
                  ('CSEL_P', 'RW_N', 'PHI2', 'RAM_EN', 'SRAM_WE_N')],
      desc='U5: CSEL_P = PWR_OK & CARTSEL; U6: SRAM /OE, /WE')
for n in ('74HCT14', '74HCT00', '74HCT20 (CARTSEL)', '74HCT20 (strobes)'):
    C('100nF', '+5V', desc=n + ' VCC decoupling')

# =========================================================================
# The FujiNet half: the NES / SMS Rev0 sheets, declared in the same order.
sheet('esp32s3-sd')
s3 = {}
for fn, pad in S3_PAD.items():
    for p in (pad if isinstance(pad, list) else [pad]):
        s3[p] = 'GND' if fn == 'GND' else '+3V3' if fn == '3V3' else S3_NET.get(fn, NC)
add('U', 'RF_Module:ESP32-S3-WROOM-1', 'ESP32-S3-WROOM-1-N16R8', FP('ESP32-S3-WROOM-1'), s3,
    mpn='ESP32-S3-WROOM-1-N16R8', lcsc='C2913202', desc='FujiNet core (fujiversal-atari7800)')
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
RN('4x10k', ['SD_CS', 'SD_MISO', 'SD_DAT1', 'SD_DAT2'], '+3V3', desc='SD pull-ups')
R('10k', '+3V3', 'SD_CD', desc='card-detect pull-up')
C('10uF', '+3V3', desc='microSD supply')
R('330R', 'LED_STRIP', 'WS_DIN', desc='WS2812 data series')
add('D', 'LED:WS2812B-2020', 'WS2812B-2020-V6', FP('LED_WS2812B-2020_PLCC4_2.0x2.0mm'),
    {1: NC, 2: 'GND', 3: 'WS_DIN', 4: '+5V'}, mpn='WS2812B-2020-V6', lcsc='C52917434',
    desc='status LED on +5V (datasheet VDD 3.7-5.3 V; VIH 2.7 V takes the S3 3.3 V data directly)')
C('100nF', '+5V', desc='WS2812 decoupling')

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
C('1uF', 'VBUS', desc='VBUS decoupling at the connector')
C('100nF', 'VBUS', desc='VBUS HF decoupling at the connector')
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
# CONS_5V is the edge rail, +5V the OR of it and VBUS: the buck input, the RP
# LDO input and the supply of the 5 V glue and the SRAM.  Console side: a
# P-FET (D = CONS_5V, S = +5V, G = VBUS), fully on without USB (74HCT needs
# VCC >= 4.5 V; a Schottky drop here leaves no margin), body diode only when
# USB is in, so nothing back-feeds the console.  USB side: an SS34.
add('Q', 'Transistor_FET:AO3401A', 'AO3401A', FP('SOT-23'), {1: 'VBUS', 2: '+5V', 3: 'CONS_5V'},
    mpn='AO3401A', lcsc='C15127', desc='console 5V switch: G = VBUS, S = +5V, D = CONS_5V; body diode CONS_5V -> +5V')
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
# RP rail: a fast LDO straight off the 5 V rail, so IOVDD tracks the console
# rail as it rises and the 5 V-tolerant pads are never unpowered with 5 V on them.
add('U', 'Regulator_Linear:AP2112K-3.3', 'AP2112K-3.3', FP('SOT-23-5'),
    {1: '+5V', 2: 'GND', 3: '+5V', 4: NC, 5: RP_IO_RAIL},
    mpn='AP2112K-3.3TRG1', lcsc='C51118', desc='RP2354B 3.3V LDO (IOVDD, VREG_VIN, VREG_AVDD), 600mA, fast start')
C('1uF', '+5V', desc='LDO input')
C('1uF', RP_IO_RAIL, desc='LDO output')

# PWR_FLAGs: nets whose drivers are passive pins
PWR_FLAG_NETS = ['GND', 'CONS_5V', 'VBUS', '+5V', '+3V3', 'DVDD', 'VREG_AVDD']   # +3V3_RP is the LDO's power_out

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
        print(p.sheet, p.ref, p.value, p.footprint.split(':')[1], p.lcsc, 'DNP' if p.dnp else '')
    ns = nets()
    print(len(PARTS), 'parts', len(ns), 'nets')
    for n, pp in sorted(ns.items()):
        if len(pp) < 2:
            print('SINGLE-PIN NET', n, pp)
