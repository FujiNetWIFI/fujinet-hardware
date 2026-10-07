"""Fujiversal-Atari2600 Rev1 (RP2354A + ESP32-S3) -- the single source of truth.

Every part, value, footprint, MPN, LCSC code and pin->net assignment lives
here.  gen_sch.py, gen_pcb.py and export.py import it; the KiCad files are
generated output.  check_nets.py does NOT import it: it reads the netlist and
the firmware headers and checks one against the other.

Firmware contract (fujinet-firmware branch 2600-experiment, worktree
~/Workspace/fn-2600):
  pico/atari-2600/firmware/include/vcs_pins.h       A0-A12 GP2-14, D0-D7 GP15-22
  pico/atari-2600/firmware/boards/fujivcs.h         LED = PICO_DEFAULT_LED_PIN (GP25)
  include/pinmap/fujiversal-atari2600.h             S3 pins (SD, LED, UART0, RUN/BOOTSEL)
Edge pinout: the standard 2600 24-pin cartridge port; geometry and face
orientation from the FujiPlusCart prototype gerbers (make_edge_fp.py).

What changed from Rev0 (RP2040 + W25Q16 + 3x 74LVC245A):
  * RP2354A (RP2350A + 2 MB flash stacked in the package), wired straight to
    the 5 V edge.  Its GPIO0-25 are "Digital IO (FT)": they tolerate 5.5 V
    while IOVDD is 3.3 V (RP2350 datasheet, pin types / VPIN_FT), and a 3.3 V
    high clears the 6507's TTL VIH (2.0 V).  No buffers, so no DIR pin: the
    firmware's per-access output enable (DATA_DRIVE / DATA_RELEASE) is the
    whole direction control.  The RP2040 board's DIR (GP26) is not wired.
  * The whole RP runs from its own fast LDO (+3V3_RP) off the 5 V rail, so
    IOVDD rises with the console's 5 V and the pads are powered before the
    bus can carry 5 V into them.  VREG_VIN and VREG_AVDD share that rail
    (datasheet: power them up together; "combined supplies", Figure 19).
  * Console 5 V sense on GP27 (ADC1, not 5 V-tolerant: 100k/150k = 3.0 V at
    5.0 V): the firmware can tell a powered console from a USB-only cart.
  * Console 5 V enters through a P-FET (gate = VBUS) instead of a Schottky.
"""

LIB = 'Fujiversal-Atari2600'
PROJECT = 'Fujiversal-Atari2600-Rev1'
NC = None  # explicit no-connect

SHEETS = [  # (file stem, title, page) -- in signal-flow order, console side first
    ('edge-rp2354a', 'Cart edge straight into the RP2354A (5 V-tolerant pads)', 2),
    ('esp32s3-sd', 'ESP32-S3, microSD, status LED', 3),
    ('usb-uart', 'USB-C, CP2102N bridge', 4),
    ('power', 'Power: console 5V / USB OR, 3.3V buck, RP LDO', 5),
]

# ---- RP2354A (QFN-60) -------------------------------------------------------
# GPIO -> package pin: RP2350 datasheet Table 1427 (QFN-60 column); gen_sch.py
# re-checks every entry against the KiCad symbol's pin names.
RP_GPIO_PIN = {0: 2, 1: 3, 2: 4, 3: 5, 4: 7, 5: 8, 6: 9, 7: 10, 8: 12, 9: 13, 10: 14, 11: 15,
               12: 16, 13: 17, 14: 18, 15: 19, 16: 27, 17: 28, 18: 29, 19: 31, 20: 32, 21: 33,
               22: 34, 23: 35, 24: 36, 25: 37, 26: 40, 27: 41, 28: 42, 29: 43}
RP_IOVDD_PINS = [1, 11, 20, 30, 38, 45]
RP_DVDD_PINS = [6, 23, 39]
RP_RAIL = '+3V3_RP'   # IOVDD x6, QSPI_IOVDD, USB_OTP_VDD, ADC_AVDD, VREG_VIN, (VREG_AVDD through 33R)

# vcs_pins.h: ADDR_PIN 2 (A0-A12), D0_PIN 15 (D0-D7); fujivcs.h: LED GP25
RP_GPIO_NET = {2 + i: 'CA%d' % i for i in range(13)}
RP_GPIO_NET.update({15 + i: 'CD%d' % i for i in range(8)})
RP_GPIO_NET.update({0: 'RP_TX', 1: 'RP_RX', 23: NC, 24: NC, 25: 'RP_LED',
                    26: NC, 27: 'VSENSE', 28: NC, 29: NC})
assert set(RP_GPIO_NET) == set(RP_GPIO_PIN)
# Only the FT pins may meet the 5 V bus: GPIO26-29 are the ADC pins (VPIN max IOVDD + 0.5 V)
assert all(g <= 25 for g, n in RP_GPIO_NET.items() if n and n[:2] in ('CA', 'CD'))

# ESP32-S3-WROOM-1 module pad -> function (pads per the KiCad symbol)
S3_PAD = {'GND': [1, 40, 41], '3V3': 2, 'EN': 3, 'IO4': 4, 'IO5': 5, 'IO6': 6,
          'IO7': 7, 'IO15': 8, 'IO16': 9, 'IO17': 10, 'IO18': 11, 'IO8': 12,
          'IO19': 13, 'IO20': 14, 'IO3': 15, 'IO46': 16, 'IO9': 17, 'IO10': 18,
          'IO11': 19, 'IO12': 20, 'IO13': 21, 'IO14': 22, 'IO21': 23,
          'IO47': 24, 'IO48': 25, 'IO45': 26, 'IO0': 27, 'IO35': 28,
          'IO36': 29, 'IO37': 30, 'IO38': 31, 'IO39': 32, 'IO40': 33,
          'IO41': 34, 'IO42': 35, 'RXD0': 36, 'TXD0': 37, 'IO2': 38, 'IO1': 39}
# include/pinmap/fujiversal-atari2600.h + the fujiversal RUN/BOOTSEL forcing contract (IO4/IO5)
S3_NET = {'EN': 'S3_EN', 'IO0': 'S3_IO0', 'IO4': 'RUN_CTL', 'IO5': 'BOOTSEL_CTL',
          'IO19': 'USB_DM', 'IO20': 'USB_DP', 'IO38': 'SD_MOSI', 'IO39': 'SD_SCK',
          'IO40': 'SD_MISO', 'IO41': 'SD_CS', 'IO42': 'SD_CD', 'IO48': 'LED_STRIP',
          'RXD0': 'S3_RXD', 'TXD0': 'S3_TXD'}

# 2600 cartridge port: pin -> (net, symbol pin name).  Pins 1-12 on the label
# face (B.Cu, console front), 13-24 on the component face (F.Cu, console rear).
EDGE = {1: ('CA7', 'A7'), 2: ('CA6', 'A6'), 3: ('CA5', 'A5'), 4: ('CA4', 'A4'), 5: ('CA3', 'A3'),
        6: ('CA2', 'A2'), 7: ('CA1', 'A1'), 8: ('CA0', 'A0'), 9: ('CD0', 'D0'), 10: ('CD1', 'D1'),
        11: ('CD2', 'D2'), 12: ('GND', 'GND'), 13: ('CD3', 'D3'), 14: ('CD4', 'D4'), 15: ('CD5', 'D5'),
        16: ('CD6', 'D6'), 17: ('CD7', 'D7'), 18: ('CA12', 'A12'), 19: ('CA10', 'A10'),
        20: ('CA11', 'A11'), 21: ('CA9', 'A9'), 22: ('CA8', 'A8'), 23: ('CONS_5V', '+5V'),
        24: ('GND', 'GND')}

# ---- common parts: footprint, (MPN, LCSC) ----------------------------------
FP = lambda n: '%s:%s' % (LIB, n)
R0603 = FP('R_0603_1608Metric')
R0402 = FP('RPI_R0402')
C0603 = FP('C_0603_1608Metric')
C0805 = FP('C_0805_2012Metric')
RES = {'27R': ('0603WAF270JT5E', 'C25190'), '330R': ('0603WAF3300T5E', 'C23138'),
       '680R': ('0603WAF6800T5E', 'C23228'), '1k': ('0603WAF1001T5E', 'C21190'),
       '4.7k': ('0603WAF4701T5E', 'C23162'), '5.1k': ('0603WAF5101T5E', 'C23186'), '10k': ('0603WAF1002T5E', 'C25804'),
       '22k': ('0603WAF2202T5E', 'C31850'), '47k': ('0603WAF4702T5E', 'C25819'),
       '100k': ('0603WAF1003T5E', 'C25803'), '150k': ('0603WAF1503T5E', 'C22807')}
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
RPACK = {'4x10k': ('4D03WGJ0103T5E', 'C29718')}


class Part:
    def __init__(self, prefix, lib_id, value, footprint, pins, sheet,
                 mpn='', lcsc='', desc='', bom=True, dnp=False, key=None):
        self.prefix, self.lib_id, self.value, self.footprint = prefix, lib_id, value, footprint
        self.pins = {str(k): v for k, v in pins.items()}  # pad number -> net (None = NC)
        self.sheet, self.mpn, self.lcsc, self.desc, self.bom, self.dnp = sheet, mpn, lcsc, desc, bom, dnp
        self.key = key      # stable name the layout scripts use (references follow declaration order)
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


def R4(value, a, b, desc='', **k):
    mpn, lcsc = RES0402[value]
    return add('R', 'Device:R', value, R0402, {1: a, 2: b}, mpn=mpn, lcsc=lcsc, desc=desc, **k)


def C(value, a, b='GND', desc='', **k):
    fp, mpn, lcsc = CAP[value]
    return add('C', 'Device:C', value.split('/')[0], fp, {1: a, 2: b}, mpn=mpn, lcsc=lcsc, desc=desc, **k)


def RN(value, nets, common, desc='', **k):
    """4-resistor array: nets[0..3] on pins 1-4, common on 5-8 (R_Pack04: Rn.1 = pin n, Rn.2 = pin 9-n)."""
    mpn, lcsc = RPACK[value]
    pins = {i + 1: n for i, n in enumerate(nets)}
    pins.update({8 - i: common for i in range(4)})
    return add('RN', 'Device:R_Pack04', value, FP('R_Array_Convex_4x0603'), pins, mpn=mpn, lcsc=lcsc,
               desc=desc, **k)


def SW(value, net, desc, **k):
    return add('SW', 'Switch:SW_Push', value, FP('SW_SPST_TL3342'), {1: net, 2: 'GND'},
               mpn='TL3342F160QG', lcsc='C2886898', desc=desc, **k)


def TP(net, label, **k):
    return add('TP', 'Connector:TestPoint', label, FP('TestPoint_Pad_D1.5mm'), {1: net},
               desc='test pad', bom=False, **k)


# =========================================================================
sheet('edge-rp2354a')
add('J', '%s:Atari2600_Cart_Edge_24' % LIB, 'Atari2600_Cart_Edge_24', FP('Atari2600_Cart_Edge_24'),
    {k: v[0] for k, v in EDGE.items()}, desc='Atari 2600 cartridge edge, 2x12 gold fingers, 2.54 mm pitch',
    bom=False, key='J_EDGE')
# -- RP2354A.  RP2350 datasheet section 6.3.7 Figure 19 ("combined supplies"):
# VREG_VIN and VREG_AVDD (through 33R) from one 3.3 V supply, 3.3 uH + 4.7 uF
# core regulator; DVDD 100 nF on the two pins nearest the regulator (39, 6),
# 4.7 uF on the far one (23).  The regulator corner is Raspberry Pi's own
# RP2350A minimal-design layout (0402 parts, gen_pcb.py grafts it).
rp = {21: 'XIN', 22: 'XOUT', 24: 'SWCLK', 25: 'SWDIO', 26: 'RUN',
      44: RP_RAIL,                                                  # ADC_AVDD
      46: 'VREG_AVDD', 47: 'GND', 48: 'RP_LX', 49: RP_RAIL, 50: 'DVDD',   # VREG: AVDD PGND LX VIN FB
      51: 'RP_USB_DM', 52: 'RP_USB_DP', 53: RP_RAIL, 54: RP_RAIL,     # USB, USB_OTP_VDD, QSPI_IOVDD
      55: NC, 56: NC, 57: NC, 58: NC, 59: NC,                       # QSPI data/clock: the flash is in the package
      60: 'QSPI_SS', 61: 'GND'}
rp.update({p: RP_RAIL for p in RP_IOVDD_PINS})
rp.update({p: 'DVDD' for p in RP_DVDD_PINS})
for g, pin in RP_GPIO_PIN.items():
    rp[pin] = RP_GPIO_NET[g]
add('U', 'MCU_RaspberryPi:RP2354A', 'RP2354A', FP('RPI_RP2350A_QFN60'), rp,
    mpn='RP2354A', lcsc='C41378174', desc='RP2350A + 2MB flash in package; serves the 2600 cart bus', key='U_RP')
# decoupling: 100 nF per IOVDD pin and ADC_AVDD; USB_OTP_VDD + QSPI_IOVDD share
# one (as the minimal design does), bulk on the rail
for i, pin in enumerate(RP_IOVDD_PINS):
    C('100nF', RP_RAIL, desc='IOVDD decoupling (pin %d)' % pin, key='C_IOVDD%d' % pin)
C('100nF', RP_RAIL, desc='ADC_AVDD decoupling', key='C_ADC')
C('100nF/0402', RP_RAIL, desc='USB_OTP_VDD + QSPI_IOVDD decoupling', key='C_OTP')
C('10uF', RP_RAIL, desc='+3V3_RP bulk at the RP', key='C_RPBULK')
# core regulator (Figure 19 values; Raspberry Pi minimal-design parts)
C('4.7uF/0402w', RP_RAIL, desc='VREG_VIN input (C_IN)', key='C_VIN')
R4('33R', RP_RAIL, 'VREG_AVDD', desc='VREG_AVDD RC filter (R_FILT)', key='R_FILT')
C('4.7uF/0402', 'VREG_AVDD', desc='VREG_AVDD RC filter (C_FILT)', key='C_FILT')
add('L', 'Device:L', '3.3uH', FP('RPI_L_AOTA-B201610S3R3'), {1: 'DVDD', 2: 'RP_LX'},
    mpn='AOTA-B201610S3R3-101-T', lcsc='C42411119', desc='RP2350 core SMPS inductor (polarity marked)', key='L_VREG')
C('4.7uF/0402w', 'DVDD', desc='core regulator output (C_OUT)', key='C_VOUT')
C('100nF', 'DVDD', desc='DVDD decoupling (pin 39)', key='C_DVDD39')
C('100nF', 'DVDD', desc='DVDD decoupling (pin 6)', key='C_DVDD6')
C('4.7uF', 'DVDD', desc='DVDD decoupling (pin 23, far from the regulator)', key='C_DVDD23')
# 12 MHz crystal (minimal design: ABM8-272-T3, 15 pF loads, 1k in XOUT)
add('Y', 'Device:Crystal_GND24', '12MHz', FP('Crystal_SMD_3225-4Pin_3.2x2.5mm'),
    {1: 'XIN', 2: 'GND', 3: 'XOUT_Y', 4: 'GND'}, mpn='ABM8-272-T3', lcsc='C20625731', key='Y_XTAL')
C('15pF', 'XIN', desc='crystal load', key='C_XIN')
C('15pF', 'XOUT_Y', desc='crystal load', key='C_XOUT')
R('1k', 'XOUT', 'XOUT_Y', desc='crystal drive limit', key='R_XOUT')
# RESET: one top-face button resets both MCUs (the way back to the browser)
SW('RESET', 'RST_BTN', 'cart RESET: RP RUN + S3 EN through the BAT54C', key='SW_RESET')
add('D', 'Diode:BAT54C', 'BAT54C', FP('SOT-23'), {1: 'RUN', 2: 'S3_EN', 3: 'RST_BTN'},
    mpn='BAT54C,215', lcsc='C37704', desc='RESET steering, common cathode', key='D_RST')
# RUN / BOOTSEL, forced by the S3 exactly as fnPicoUpdater::forceBootselViaPins()
# expects: its pins idle as inputs and drive LOW to assert, so with 3.3 V on
# both chips a 1k series resistor is the whole interface.
R('10k', RP_RAIL, 'RUN', desc='RUN pull-up', key='R_RUNPU')
R('1k', 'RUN_CTL', 'RUN', desc='S3 IO4 -> RP RUN (low = reset)', key='R_RUNCTL')
R('10k', RP_RAIL, 'QSPI_SS', desc='QSPI_SS pull-up', key='R_SSPU')
R('1k', 'QSPI_SS', 'BOOTSEL_BTN', desc='BOOTSEL button series', key='R_SSBTN')
SW('BOOTSEL', 'BOOTSEL_BTN', 'RP2354A BOOTSEL (hold while pressing RESET)', key='SW_BOOTSEL')
R('1k', 'BOOTSEL_CTL', 'QSPI_SS', desc='S3 IO5 -> RP QSPI_SS (low through reset = BOOTSEL)', key='R_SSCTL')
# RP <-> S3 native USB (RP = CDC device, S3 = host): 27R series (datasheet: USB IO)
R4('27R', 'USB_DP', 'RP_USB_DP', desc='USB series', key='R_USBP')
R4('27R', 'USB_DM', 'RP_USB_DM', desc='USB series', key='R_USBM')
# activity LED on GP25 (PICO_DEFAULT_LED_PIN); red, so a 3.3 V pin lights it
R('680R', 'RP_LED', 'RP_LED_A', desc='LED series (~2 mA)', key='R_LED')
add('D', 'Device:LED', 'red', FP('LED_0603_1608Metric'), {1: 'GND', 2: 'RP_LED_A'},
    mpn='KT-0603R', lcsc='C2286', desc='RP activity LED (GP25)', key='D_LED')
# SWD (first flash: the RP's USB only reaches the S3) + the debug UART (GP0/GP1)
TP('SWCLK', 'SWCLK', key='TP_SWCLK')
TP('SWDIO', 'SWDIO', key='TP_SWDIO')
TP('GND', 'GND', key='TP_GND')
TP('RP_TX', 'RP_TX', key='TP_TX')
TP('RP_RX', 'RP_RX', key='TP_RX')

# =========================================================================
sheet('esp32s3-sd')
s3 = {}
for fn, pad in S3_PAD.items():
    for p in (pad if isinstance(pad, list) else [pad]):
        s3[p] = 'GND' if fn == 'GND' else '+3V3' if fn == '3V3' else S3_NET.get(fn, NC)
add('U', 'RF_Module:ESP32-S3-WROOM-1', 'ESP32-S3-WROOM-1-N16R8', FP('ESP32-S3-WROOM-1'), s3,
    mpn='ESP32-S3-WROOM-1-N16R8', lcsc='C2913202', desc='FujiNet core (fujiversal-atari2600)', key='U_S3')
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
R('10k', '+3V3', 'SD_CD', desc='card-detect pull-up', key='R_CD')
C('10uF', '+3V3', desc='microSD supply', key='C_SD')
# WS2812B-2020: VDD 3.7-5.3 V, so it runs on the 5 V rail; the S3's 3.3 V data
# line drives it (VIH checked against the datasheet in docs/design-review-rev1.md)
R('330R', 'LED_STRIP', 'WS_DIN', desc='WS2812 data series', key='R_WS')
add('D', 'LED:WS2812B-2020', 'WS2812B-2020-V6', FP('LED_WS2812B-2020_PLCC4_2.0x2.0mm'),
    {1: NC, 2: 'GND', 3: 'WS_DIN', 4: '+5V'}, mpn='WS2812B-2020-V6', lcsc='C52917434',
    desc='status LED on +5V', key='D_WS')
C('100nF', '+5V', desc='WS2812 decoupling', key='C_WS')

# =========================================================================
sheet('usb-uart')
add('J', 'Connector:USB_C_Receptacle_USB2.0_16P', 'USB-C', FP('USB_C_Receptacle_HRO_TYPE-C-31-M-12'),
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
C('100nF', '+3V3', desc='CP2102N VDD', key='C_CP')
C('4.7uF', '+3V3', desc='CP2102N VDD bulk', key='C_CPBULK')
R('22k', 'VBUS', 'VBUS_SNS', desc='VBUS sense divider', key='R_VBH')
R('47k', 'VBUS_SNS', 'GND', desc='VBUS sense divider', key='R_VBL')
R('10k', '+3V3', 'CP_RST', desc='/RST pull-up', key='R_CPRST')
add('U', 'Transistor_BJT:UMH3N', 'UMH3N', FP('SOT-363_SC-70-6'),
    {1: 'UART_RTS', 2: 'UART_DTR', 6: 'S3_EN', 3: 'S3_IO0', 4: 'UART_DTR', 5: 'UART_RTS'},
    mpn='UMH3N', lcsc='C62892', desc='esptool auto-program (DevKitC-1 style)', key='Q_AUTO')

# =========================================================================
sheet('power')
# CONS_5V is the edge rail, +5V the OR of it and VBUS: the buck input, the RP
# LDO input and the WS2812.  Console side: a P-FET (D = CONS_5V, S = +5V).  With
# no USB its gate (VBUS, held at 0 V by the 22k/47k VBUS sense divider) is low
# and the FET is fully on.  With VBUS present the gate sits at VBUS, the FET is
# off and only its body diode remains, pointing into the cart: nothing ever
# back-feeds the console.  With both present USB wins through the SS34.
add('Q', 'Transistor_FET:AO3401A', 'AO3401A', FP('SOT-23'), {1: 'VBUS', 2: '+5V', 3: 'CONS_5V'},
    mpn='AO3401A', lcsc='C15127', desc='console 5V switch: G = VBUS, S = +5V, D = CONS_5V; body diode CONS_5V -> +5V',
    key='Q_CONS')
add('D', 'Diode:SS34', 'SS34', FP('D_SMA'), {1: '+5V', 2: 'VBUS'}, mpn='SS34', lcsc='C8678',
    desc='USB VBUS OR-ing (no back-feed into the console)', key='D_VBUS')
# The SS34 is reverse-biased by +5V whenever the console powers the cart, and
# its leakage (datasheet: 0.5 mA max at 25 C / 20 mA at 100 C, at 40 V) flows
# into VBUS -- the P-FET's gate.  The 69k VBUS sense divider alone would let a
# warm diode lift the gate past the FET's -1.3 V threshold; 4.7k keeps it under
# 2.3 V (VGS < -2.7 V) up to 500 uA of leakage (tools/audit/margins.py).
R('4.7k', 'VBUS', 'GND', desc='P-FET gate pull-down against the SS34 reverse leakage', key='R_VBPD')
C('10uF', 'CONS_5V', desc='edge 5V bulk', key='C_CONS')
C('100nF', 'CONS_5V', desc='edge 5V HF bypass', key='C_CONSHF')
# console 5 V sense for the RP (VSENSE -> GPIO27): GP27 is an ADC pin (not FT), so the divider keeps it under
# IOVDD: 3.0 V at 5.0 V, 3.15 V at 5.25 V; 100 nF makes it a ~6 ms filter
R('100k', 'CONS_5V', 'VSENSE', desc='console 5V sense divider', key='R_VSH')
R('150k', 'VSENSE', 'GND', desc='console 5V sense divider (0.6 x CONS_5V)', key='R_VSL')
C('100nF', 'VSENSE', desc='console 5V sense filter', key='C_VS')
C('22uF', '+5V', desc='buck input', key='C_BIN1')
C('22uF', '+5V', desc='buck input', key='C_BIN2')
C('100nF', '+5V', desc='buck input HF', key='C_BINHF')
add('U', 'Regulator_Switching:AP63203WU', 'AP63203WU', FP('TSOT-23-6'),
    {1: '+3V3', 2: '+5V', 3: '+5V', 4: 'GND', 5: 'BUCK_SW', 6: 'BUCK_BST'},
    mpn='AP63203WU-7', lcsc='C780769', desc='3.3V 2A buck (S3, SD, CP2102N)', key='U_BUCK')
C('100nF', 'BUCK_SW', 'BUCK_BST', desc='bootstrap', key='C_BST')
add('L', 'Device:L', '6.8uH', FP('L_Sunlord_SWPA4030S'), {1: 'BUCK_SW', 2: '+3V3'},
    mpn='SWPA4030S6R8MT', lcsc='C62684', desc='buck inductor', key='L_BUCK')
C('22uF', '+3V3', desc='buck output', key='C_BOUT1')
C('22uF', '+3V3', desc='buck output', key='C_BOUT2')
# RP rail: a fast LDO straight off the 5 V rail, so IOVDD tracks the console
# rail as it rises and the FT pads are never unpowered with 5 V on them.
add('U', 'Regulator_Linear:AP2112K-3.3', 'AP2112K-3.3', FP('SOT-23-5'),
    {1: '+5V', 2: 'GND', 3: '+5V', 4: NC, 5: RP_RAIL},
    mpn='AP2112K-3.3TRG1', lcsc='C51118', desc='RP2354A 3.3V LDO (IOVDD, VREG_VIN, VREG_AVDD), 600mA, fast start',
    key='U_LDO')
C('1uF', '+5V', desc='LDO input', key='C_LDOIN')
C('1uF', RP_RAIL, desc='LDO output', key='C_LDOOUT')

# PWR_FLAGs: nets whose drivers are passive pins (+3V3_RP is the LDO's power_out)
PWR_FLAG_NETS = ['GND', 'CONS_5V', 'VBUS', '+5V', '+3V3', 'DVDD', 'VREG_AVDD']

# ---- reference assignment (stable: declaration order) ---------------------
_count = {}
for p in PARTS:
    _count[p.prefix] = _count.get(p.prefix, 0) + 1
    p.ref = '%s%d' % (p.prefix, _count[p.prefix])

BY_REF = {p.ref: p for p in PARTS}
KEY = {p.key: p.ref for p in PARTS if p.key}
assert len(KEY) == len([p for p in PARTS if p.key]), 'duplicate part key'


def nets():
    out = {}
    for p in PARTS:
        for pad, n in p.pins.items():
            if n:
                out.setdefault(n, []).append((p.ref, pad))
    return out


if __name__ == '__main__':
    for p in PARTS:
        print(p.sheet, p.ref, p.key, p.value, p.footprint.split(':')[1], p.lcsc, 'DNP' if p.dnp else '')
    ns = nets()
    print(len(PARTS), 'parts', len(ns), 'nets')
    for n, pp in sorted(ns.items()):
        if len(pp) < 2:
            print('SINGLE-PIN NET', n, pp)
