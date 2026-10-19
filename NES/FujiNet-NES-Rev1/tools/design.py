"""FujiNet-NES Rev1 (two RP2354Bs, no SRAM) -- the single source of truth.

Every part, value, footprint, MPN, LCSC code and pin->net assignment lives
here.  gen_sch.py, gen_pcb.py, check_nets.py and export.py import it; the
KiCad files are generated output.

Rev1 drops Rev0's two AS6C4008 SRAMs ($6.36 each, out of JLC stock) and the
six 74HCT glue chips that decoded them for a second RP2354B:
  RP-A (U1)  the CPU bus: PRG from its SRAM or flash through a PIO + DMA
             engine, the mailbox, WRAM, the mapper, MMC3's IRQ, the link
             to RP-B and RP-B's SWD loader.  Rev0's CPU pin map.
  RP-B (U2)  the PPU bus: CHR / CHR-RAM from its SRAM, the CIRAM lines from a
             PIO table (no '253), loaded by RP-A over SWD at every boot.
Firmware contracts (fujinet-firmware branch simplify-nes):
  pico/nes/firmware/include/nes_bus.h, nes_cart.h   RP-A pins
  pico/nes/firmware/include/nes_ppu.h               RP-B pins
  pico/nes/firmware/include/nes_link.h              the link
  include/pinmap/fujiversal-nes.h                   S3 pins
Phase 0 timing (both RPs at 266 MHz): pico/nes/bench, README "Verified facts".
Edge pinout: nesdev wiki "Cartridge connector", 72-pin NES.  Edge geometry:
nesdev "NES cartridge dimensions" (NES-EWROM-01 measured), see make_edge_fp.py.

Carried from the Rev0 audit (docs/design-review-rev0.md in Rev0): each RP on
its own fast LDO rail; the console 5 V through a P-FET; CIClone DNP.
Rev1 changes besides the RPs:
  * PWR_OK straight into both RPs: 2.2k / 3.3k = 0.6 x CONS_5V, 3.0 V at a
    5 V console -- under the 3.63 V an unpowered FT pad allows, and a 1.32k
    source for RP2350-E9 (<= 8.2k).  RP-B's ADC reads the same node.
  * The status LED on an RP-A GPIO: a red KT-0603R (Vf ~2.0 V) through 330R;
    Rev0's green (Vf 3.1 V) needed the '595's 5 V.
  * Edge pin 58 (PPU /A13) open: RP-B decodes A13 itself.
"""

LIB = 'FujiNet-NES'
PROJECT = 'FujiNet-NES-Rev1'
NC = None  # explicit no-connect

SHEETS = [  # (file stem, title, page) -- in signal-flow order, console side first
    ('edge-cic', '72-pin cart edge, CIClone', 2),
    ('rp-cpu', 'RP-A: CPU bus, PRG, link, RP-B loader', 3),
    ('rp-ppu', 'RP-B: PPU bus, CHR and CIRAM', 4),
    ('esp32s3-sd', 'ESP32-S3, microSD, status LED', 5),
    ('usb-uart', 'USB-C, CP2102N bridge', 6),
    ('power', 'Power: 5V OR, 3.3V buck, two RP LDOs', 7),
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
RP_A_RAIL = '+3V3_RP'      # RP-A: IOVDD x8, QSPI_IOVDD, USB_OTP_VDD, ADC_AVDD, VREG_VIN (Rev0's name)
RP_B_RAIL = '+3V3_RPB'     # RP-B: the same set, its own LDO
RP_IO_RAIL = RP_A_RAIL     # (Rev0 name, kept for tools that ask for "the" RP rail)

# nes_bus.h + nes_cart.h: RP-A, 44 of 48 (GP28-31 spare; 28/29 a debug UART on pads).
RP_A_GPIO_NET = {g: 'CA%d' % g for g in range(13)}                  # CA0_PIN 0
RP_A_GPIO_NET.update({13 + i: 'CD%d' % i for i in range(8)})        # CD0_PIN 13
RP_A_GPIO_NET.update({21: 'M2', 22: 'RW', 23: 'ROMSEL_N', 24: 'CA13', 25: 'CA14',
                      26: 'PWR_OK', 27: 'LED', 28: 'DBG_A_TX', 29: 'DBG_A_RX', 30: NC, 31: NC,
                      32: 'IRQ_N', 33: 'LACK'})
RP_A_GPIO_NET.update({34 + i: 'LD%d' % i for i in range(8)})        # LD0_PIN 34
RP_A_GPIO_NET.update({42: 'LCLK', 43: 'LFRM', 44: 'RPB_SWCLK', 45: 'RPB_SWDIO', 46: 'RPB_RUN',
                      47: 'PA12'})
# nes_ppu.h: RP-B, 38 of 48 (GP27, GP30-32, GP45-47 spare; 28/29 a debug UART on pads).
RP_B_GPIO_NET = {g: 'PA%d' % g for g in range(14)}                  # PA0_PIN 0
RP_B_GPIO_NET.update({14 + i: 'PD%d' % i for i in range(8)})        # PD0_PIN 14
RP_B_GPIO_NET.update({22: 'PPU_RD_N', 23: 'PPU_WR_N', 24: 'PWR_OK', 25: 'CIRAM_A10',
                      26: 'CIRAM_CE_N', 27: NC, 28: 'DBG_B_TX', 29: 'DBG_B_RX', 30: NC, 31: NC,
                      32: NC, 33: 'LFRM', 34: 'LCLK'})
RP_B_GPIO_NET.update({35 + i: 'LD%d' % (7 - i) for i in range(8)})  # LD7..LD0: mirrored, planar
RP_B_GPIO_NET.update({43: 'LACK', 44: 'PWR_OK', 45: NC, 46: NC, 47: NC})   # GP44 = ADC4: the console 5 V
for _m in (RP_A_GPIO_NET, RP_B_GPIO_NET):
    assert set(_m) == set(RP_GPIO_PIN), sorted(set(RP_GPIO_PIN) ^ set(_m))

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

# NES 72-pin edge (nesdev).  (net, symbol pin name).  EXP0-9 and SYSTEM CLK
# stay unconnected; the four CIC pins go to the (DNP) CIClone; PPU /A13
# (pin 58) is open: RP-B has PPU A13 itself.
EDGE = {1: ('GND', 'GND'), 2: ('CA11', 'CPU A11'), 3: ('CA10', 'CPU A10'), 4: ('CA9', 'CPU A9'),
        5: ('CA8', 'CPU A8'), 6: ('CA7', 'CPU A7'), 7: ('CA6', 'CPU A6'), 8: ('CA5', 'CPU A5'),
        9: ('CA4', 'CPU A4'), 10: ('CA3', 'CPU A3'), 11: ('CA2', 'CPU A2'), 12: ('CA1', 'CPU A1'),
        13: ('CA0', 'CPU A0'), 14: ('RW', 'CPU R/W'), 15: ('IRQ_N', '~{IRQ}'),
        16: (NC, 'EXP0'), 17: (NC, 'EXP1'), 18: (NC, 'EXP2'), 19: (NC, 'EXP3'), 20: (NC, 'EXP4'),
        21: ('PPU_RD_N', 'PPU ~{RD}'), 22: ('CIRAM_A10', 'CIRAM A10'),
        23: ('PA6', 'PPU A6'), 24: ('PA5', 'PPU A5'), 25: ('PA4', 'PPU A4'), 26: ('PA3', 'PPU A3'),
        27: ('PA2', 'PPU A2'), 28: ('PA1', 'PPU A1'), 29: ('PA0', 'PPU A0'),
        30: ('PD0', 'PPU D0'), 31: ('PD1', 'PPU D1'), 32: ('PD2', 'PPU D2'), 33: ('PD3', 'PPU D3'),
        34: ('CIC_TOPAK', 'CIC toPak'), 35: ('CIC_TOMB', 'CIC toMB'), 36: ('CONS_5V', '+5V'),
        37: (NC, 'SYSTEM CLK'), 38: ('M2', 'M2'), 39: ('CA12', 'CPU A12'), 40: ('CA13', 'CPU A13'),
        41: ('CA14', 'CPU A14'), 42: ('CD7', 'CPU D7'), 43: ('CD6', 'CPU D6'), 44: ('CD5', 'CPU D5'),
        45: ('CD4', 'CPU D4'), 46: ('CD3', 'CPU D3'), 47: ('CD2', 'CPU D2'), 48: ('CD1', 'CPU D1'),
        49: ('CD0', 'CPU D0'), 50: ('ROMSEL_N', '~{ROMSEL}'),
        51: (NC, 'EXP9'), 52: (NC, 'EXP8'), 53: (NC, 'EXP7'), 54: (NC, 'EXP6'), 55: (NC, 'EXP5'),
        56: ('PPU_WR_N', 'PPU ~{WR}'), 57: ('CIRAM_CE_N', 'CIRAM ~{CE}'), 58: (NC, 'PPU ~{A13}'),
        59: ('PA7', 'PPU A7'), 60: ('PA8', 'PPU A8'), 61: ('PA9', 'PPU A9'), 62: ('PA11', 'PPU A11'),
        63: ('PA10', 'PPU A10'), 64: ('PA12', 'PPU A12'), 65: ('PA13', 'PPU A13'),
        66: ('PD7', 'PPU D7'), 67: ('PD6', 'PPU D6'), 68: ('PD5', 'PPU D5'), 69: ('PD4', 'PPU D4'),
        70: ('CIC_RST', 'CIC +RST'), 71: ('CIC_CLK', 'CIC CLK'), 72: ('GND', 'GND')}

# ---- common parts: (lib_id, footprint, MPN, LCSC) --------------------------
FP = lambda n: '%s:%s' % (LIB, n)
R0603 = FP('R_0603_1608Metric')
C0603 = FP('C_0603_1608Metric')
C0805 = FP('C_0805_2012Metric')
RES = {'27R': ('0603WAF270JT5E', 'C25190'), '33R': ('0603WAF330JT5E', 'C23140'),
       '330R': ('0603WAF3300T5E', 'C23138'), '1k': ('0603WAF1001T5E', 'C21190'),
       '2.2k': ('0603WAF2201T5E', 'C4190'), '3.3k': ('0603WAF3301T5E', 'C22978'),
       '5.1k': ('0603WAF5101T5E', 'C23186'), '10k': ('0603WAF1002T5E', 'C25804'),
       '22k': ('0603WAF2202T5E', 'C31850'), '47k': ('0603WAF4702T5E', 'C25819'),
       '100k': ('0603WAF1003T5E', 'C25803'), '4.7k': ('0603WAF4701T5E', 'C23162')}
CAP = {'15pF': (C0603, 'CL10C150JB8NNNC', 'C1644'),
       '100nF': (C0603, 'CC0603KRX7R9BB104', 'C14663'),
       '1uF': (C0603, 'CL10A105KB8NNNC', 'C15849'),
       '4.7uF': (C0603, 'CL10A475KO8NNNC', 'C19666'),
       '10uF': (C0603, 'CL10A106KP8NNNC', 'C19702'),
       '22uF': (C0805, 'CL21A226MAQNNNE', 'C45783')}
RPACK = {'4x10k': ('4D03WGJ0103T5E', 'C29718')}


class Part:
    def __init__(self, prefix, lib_id, value, footprint, pins, sheet,
                 mpn='', lcsc='', desc='', bom=True, dnp=False):
        self.prefix, self.lib_id, self.value, self.footprint = prefix, lib_id, value, footprint
        self.pins = {str(k): v for k, v in pins.items()}  # pad number -> net (None = NC)
        self.sheet, self.mpn, self.lcsc, self.desc, self.bom, self.dnp = sheet, mpn, lcsc, desc, bom, dnp
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
    mpn, lcsc = RPACK[value]
    pins = {i + 1: n for i, n in enumerate(nets)}
    pins.update({8 - i: common for i in range(4)})
    return add('RN', 'Device:R_Pack04', value, FP('R_Array_Convex_4x0603'), pins, mpn=mpn, lcsc=lcsc, desc=desc)


def SW(value, net, desc):
    return add('SW', 'Switch:SW_Push', value, FP('SW_SPST_TL3342'), {1: net, 2: 'GND'},
               mpn='TL3342F160QG', lcsc='C2886898', desc=desc)


def TP(net, label):
    return add('TP', 'Connector:TestPoint', label, FP('TestPoint_Pad_D1.5mm'), {1: net},
               desc='test pad', bom=False)


# ROLE: the parts tools refer to by function, not by reference designator
# (gen_pcb, placement, fanout, check_nets): filled in as they are declared.
ROLE = {}
LDO = {}


def rp2354b(who, gpio_net, rail, n):
    """One RP2354B and everything it needs locally.  `n` maps the Rev0 local
    net names (DVDD, RP_LX, VREG_AVDD, XIN, XOUT, XOUT_Y, SWCLK, SWDIO, RUN,
    QSPI_SS, RP_USB_DM, RP_USB_DP) to this RP's."""
    rp = {30: n['XIN'], 31: n['XOUT'], 33: n['SWCLK'], 34: n['SWDIO'], 35: n['RUN'],
          59: rail,                                                          # ADC_AVDD
          61: n['VREG_AVDD'], 62: 'GND', 63: n['RP_LX'], 64: rail, 65: n['DVDD'],   # VREG: AVDD PGND LX VIN FB
          66: n['RP_USB_DM'], 67: n['RP_USB_DP'], 68: rail, 69: rail,        # USB, USB_OTP_VDD, QSPI_IOVDD
          70: NC, 71: NC, 72: NC, 73: NC, 74: NC,                           # QSPI (flash in package)
          75: n['QSPI_SS'], 81: 'GND'}
    rp.update({p: rail for p in RP_IOVDD_PINS})
    rp.update({p: n['DVDD'] for p in RP_DVDD_PINS})
    for g, pin in RP_GPIO_PIN.items():
        rp[pin] = gpio_net[g]
    u = add('U', 'MCU_RaspberryPi:RP2354B', 'RP2354B', FP('QFN-80-1EP_10x10mm_P0.4mm_EP3.4x3.4mm'), rp,
            mpn='RP2354B', lcsc='C39843328',
            desc='RP2350B + 2MB flash in package; ' + ('CPU bus, PRG engine, link, RP-B loader' if who == 'A'
                                                       else 'PPU bus, CHR, CIRAM; loaded over SWD by RP-A'))
    ROLE['rp_' + who.lower()] = u
    # decoupling: one 100nF per IOVDD/DVDD/QSPI/USB/ADC supply pin, bulk on each rail
    for _ in RP_IOVDD_PINS:
        C('100nF', rail, desc='IOVDD decoupling')
    C('100nF', rail, desc='QSPI_IOVDD decoupling')
    C('100nF', rail, desc='USB_OTP_VDD decoupling')
    C('100nF', rail, desc='ADC_AVDD decoupling')
    C('10uF', rail, desc='RP IO rail bulk (LDO output)')
    C('4.7uF', rail, desc='VREG_VIN bulk (LDO rail)')
    for _ in RP_DVDD_PINS:
        C('100nF', n['DVDD'], desc='DVDD decoupling')
    C('4.7uF', n['DVDD'], desc='core regulator output')
    R('33R', rail, n['VREG_AVDD'], desc='VREG_AVDD filter')
    C('4.7uF', n['VREG_AVDD'], desc='VREG_AVDD filter')
    ROLE['l_' + who.lower()] = add('L', 'Device:L', '3.3uH', FP('RPI_L_AOTA-B201610S3R3'),
                                   {1: n['DVDD'], 2: n['RP_LX']}, mpn='AOTA-B201610S3R3-101-T',
                                   lcsc='C42411119', desc='RP2350 core SMPS inductor')
    # 12 MHz crystal
    ROLE['y_' + who.lower()] = add('Y', 'Device:Crystal_GND24', '12MHz', FP('Crystal_SMD_3225-4Pin_3.2x2.5mm'),
                                   {1: n['XIN'], 2: 'GND', 3: n['XOUT_Y'], 4: 'GND'},
                                   mpn='ABM8-272-T3', lcsc='C20625731')
    C('15pF', n['XIN'], desc='crystal load')
    C('15pF', n['XOUT_Y'], desc='crystal load')
    R('1k', n['XOUT'], n['XOUT_Y'], desc='crystal drive limit')
    return u


NAMES_A = {k: k for k in ('DVDD', 'RP_LX', 'VREG_AVDD', 'XIN', 'XOUT', 'XOUT_Y', 'SWCLK', 'SWDIO',
                           'RUN', 'QSPI_SS', 'RP_USB_DM', 'RP_USB_DP')}
NAMES_B = {'DVDD': 'DVDD_B', 'RP_LX': 'RPB_LX', 'VREG_AVDD': 'VREG_AVDD_B', 'XIN': 'XIN_B',
           'XOUT': 'XOUT_B', 'XOUT_Y': 'XOUT_Y_B', 'SWCLK': 'RPB_SWCLK', 'SWDIO': 'RPB_SWDIO',
           'RUN': 'RPB_RUN', 'QSPI_SS': 'QSPI_SS_B', 'RP_USB_DM': NC, 'RP_USB_DP': NC}

# =========================================================================
sheet('rp-cpu')
# -- RP-A: Rev0's RP circuit (U1), on the CPU bus.
rp2354b('A', RP_A_GPIO_NET, RP_A_RAIL, NAMES_A)
sheet('edge-cic')
add('J', '%s:NES_Cart_Edge_72' % LIB, 'NES_Cart_Edge_72', FP('NES_Cart_Edge_72'),
    {k: v[0] for k, v in EDGE.items()}, desc='72-pin NES cartridge edge, 2.50 mm pitch', bom=False)
sheet('rp-cpu')
# top-face RESET resets RP-A and the S3 (RP-B follows: RP-A reloads it)
SW('RESET', 'RST_BTN', 'cart RESET: RP-A RUN + S3 EN via BAT54C')
add('D', 'Diode:BAT54C', 'BAT54C', FP('SOT-23'), {1: 'RUN', 2: 'S3_EN', 3: 'RST_BTN'},
    mpn='BAT54C,215', lcsc='C37704', desc='RESET steering, common cathode')
# RUN / BOOTSEL.  The S3 forces them exactly as fnPicoUpdater::
# forceBootselViaPins() expects: its pins idle as inputs and are driven LOW
# to assert.  3.3V rails on both chips, so a 1k series resistor is the
# whole interface (an NPN driver here would invert the firmware's polarity).
R('10k', RP_A_RAIL, 'RUN', desc='RUN pull-up')
R('10k', RP_A_RAIL, 'QSPI_SS', desc='QSPI_SS pull-up')
R('1k', 'QSPI_SS', 'BOOTSEL_BTN', desc='BOOTSEL button series')
SW('BOOTSEL', 'BOOTSEL_BTN', 'RP-A BOOTSEL (hold while pressing RESET)')
R('1k', 'RUN_CTL', 'RUN', desc='S3 IO4 -> RP-A RUN (drive low = reset)')
R('1k', 'BOOTSEL_CTL', 'QSPI_SS', desc='S3 IO5 -> RP-A QSPI_SS (low through reset = BOOTSEL)')
# RP-A <-> S3 native USB (RP-A = CDC device, S3 = host)
R('27R', 'USB_DP', 'RP_USB_DP', desc='USB series')
R('27R', 'USB_DM', 'RP_USB_DM', desc='USB series')
# status LED: KT-0603R red, Vf ~2.0 V: (3.3 - 2.0) / 330 = ~4 mA
R('330R', 'LED', 'LED_A', desc='status LED series')
ROLE['led'] = add('D', 'Device:LED', 'red', FP('LED_0603_1608Metric'), {1: 'GND', 2: 'LED_A'},
                  mpn='KT-0603R', lcsc='C2286', desc='status LED (RP-A GP27), Vf ~2.0 V')
TP('SWCLK', 'SWCLK')
TP('SWDIO', 'SWDIO')
TP('GND', 'GND')
TP('RUN', 'RUN')
TP('DBG_A_TX', 'A_TX')
TP('DBG_A_RX', 'A_RX')
sheet('edge-cic')
TP('M2', 'M2')
# -- console power sense: 2.2k / 3.3k = 0.6 x CONS_5V into both RPs (and RP-B's
# ADC): 3.0 V from a 5.0 V console, under the 3.63 V an RP2350 pad takes with
# its IOVDD off; 1.32k source impedance, inside RP2350-E9's 8.2k.
R('2.2k', 'CONS_5V', 'PWR_OK', desc='console 5V sense, top')
R('3.3k', 'PWR_OK', 'GND', desc='console 5V sense, bottom: PWR_OK = 0.6 x CONS_5V')

# =========================================================================
sheet('rp-ppu')
# -- RP-B (U2): the same RP circuit, on the PPU bus.  Its RUN, SWCLK and SWDIO
# are RP-A's (GP46, GP44, GP45); its USB is unused.
rp2354b('B', RP_B_GPIO_NET, RP_B_RAIL, NAMES_B)
R('10k', RP_B_RAIL, 'RPB_RUN', desc='RP-B RUN pull-up (RP-A drives it)')
R('10k', RP_B_RAIL, 'QSPI_SS_B', desc='RP-B QSPI_SS pull-up (it never boots its flash)')
TP('RPB_SWCLK', 'B_SWCLK')
TP('RPB_SWDIO', 'B_SWDIO')
TP('RPB_RUN', 'B_RUN')
TP('DBG_B_TX', 'B_TX')
TP('DBG_B_RX', 'B_RX')

sheet('edge-cic')
# -- CIClone: 10NES lockout clone on the four CIC fingers, DNP until its
# firmware is in hand.  Pin map = the common ATtiny13A NES CIC clone
# (avrciczz / "ciclone"): PB3 CLK, PB0 DOUT (toMB), PB1 DIN (toPak), PB2 RST;
# PB4 (LED) and /RESET open.  Powered from the console (CONS_5V) so it resets
# with it.  Programmable through the fingers + the /RESET pad.
add('U', 'MCU_Microchip_ATtiny:ATtiny13A-SS', 'ATtiny13A-SSU', FP('SOIC-8_3.9x4.9mm_P1.27mm'),
    {1: 'CIC_RESET_N', 2: 'CIC_CLK', 3: NC, 4: 'GND', 5: 'CIC_TOMB', 6: 'CIC_TOPAK', 7: 'CIC_RST', 8: 'CONS_5V'},
    mpn='ATTINY13A-SSUR', lcsc='C40382', desc='CIClone (10NES key), DNP: PB3=CLK PB0=toMB PB1=toPak PB2=+RST', dnp=True)
C('100nF', 'CONS_5V', desc='CIClone decoupling', dnp=True)
TP('CIC_RESET_N', 'CIC_RST')

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
RN('4x10k', ['SD_CS', 'SD_MISO', 'SD_DAT1', 'SD_DAT2'], '+3V3', desc='SD pull-ups')
R('10k', '+3V3', 'SD_CD', desc='card-detect pull-up')
C('10uF', '+3V3', desc='microSD supply')
# WS2812B-2020 datasheet: VDD +3.7 ~ +5.3 V, VIH min 2.7 V -- so it runs on the
# 5 V rail and the S3's 3.3 V data line drives it in spec without a shifter.
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
# CONS_5V is the edge rail, +5V the OR of it and VBUS: the buck input, the
# two RP LDOs' input and the WS2812's supply.
# Console side: a P-FET (D = CONS_5V, S = +5V).  With no USB its gate (VBUS)
# is at 0 V, so it is fully on (~30 mV drop, the HCT/SRAM rail is the
# console's 5 V).  With VBUS present the gate is at VBUS, the FET is off and
# only its body diode remains, pointing into the cart: nothing back-feeds the
# console.  With both present USB wins through the SS34 (0.35 V < 0.7 V).
# The gate is VBUS itself, held at 0 V when no cable is in by R22 below (the
# 22k/47k VBUS sense divider on the usb-uart sheet alone is not enough).
add('Q', 'Transistor_FET:AO3401A', 'AO3401A', FP('SOT-23'), {1: 'VBUS', 2: '+5V', 3: 'CONS_5V'},
    mpn='AO3401A', lcsc='C15127', desc='console 5V switch: G = VBUS, S = +5V, D = CONS_5V; body diode CONS_5V -> +5V')
add('D', 'Diode:SS34', 'SS34', FP('D_SMA'), {1: '+5V', 2: 'VBUS'}, mpn='SS34', lcsc='C8678',
    desc='USB VBUS OR-ing (no back-feed into the console)')
# The SS34 is reverse-biased by +5V whenever the console powers the cart, and
# its leakage (datasheet: 0.5 mA max at 25 C / 20 mA at 100 C, at 40 V) flows
# into VBUS -- the P-FET's gate.  The 69k VBUS sense divider alone would let a
# warm diode lift the gate past the FET's -1.3 V threshold (at >= 100 uA the FET
# is off and the console feeds the cart through the body diode, ~0.7 V down);
# 4.7k keeps VGS under -2.7 V up to 500 uA of leakage and pulls VBUS back down
# in ~4 ms after the cable is unplugged.  Costs 1.06 mA from USB.  Declared
# after every other resistor, so it is R22 and no reference moves.
R('4.7k', 'VBUS', 'GND', desc='P-FET gate pull-down against the SS34 reverse leakage')
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
# RP rails: one fast LDO per RP (AP2112K: ~20 us start-up) straight off the
# 5 V rail, so each RP's IOVDD tracks the console rail as it rises and its
# pads are never unpowered with 5 V on them.  ~60 mA each (IO drive + core
# regulator input): ~100 mW in a SOT-23-5.  One LDO would also do thermally
# (~95 mA); two keep the layout local and the rails isolated.
for rail, who in ((RP_A_RAIL, 'RP-A'), (RP_B_RAIL, 'RP-B')):
    LDO[who] = add('U', 'Regulator_Linear:AP2112K-3.3', 'AP2112K-3.3', FP('SOT-23-5'),
                   {1: '+5V', 2: 'GND', 3: '+5V', 4: NC, 5: rail},
                   mpn='AP2112K-3.3TRG1', lcsc='C51118',
                   desc='%s 3.3V LDO (IOVDD, VREG_VIN, VREG_AVDD), 600mA, fast start' % who)
    C('1uF', '+5V', desc='%s LDO input' % who)
    C('1uF', rail, desc='%s LDO output' % who)


# PWR_FLAGs: nets whose drivers are passive pins
PWR_FLAG_NETS = ['GND', 'CONS_5V', 'VBUS', '+5V', '+3V3', 'DVDD', 'VREG_AVDD', 'DVDD_B', 'VREG_AVDD_B']
# (+3V3_RP / +3V3_RPB are the LDOs' power_out)

# ---- reference assignment (stable: declaration order) ---------------------
_count = {}
for p in PARTS:
    _count[p.prefix] = _count.get(p.prefix, 0) + 1
    p.ref = '%s%d' % (p.prefix, _count[p.prefix])

BY_REF = {p.ref: p for p in PARTS}
ROLE.update({'ldo_a': LDO['RP-A'], 'ldo_b': LDO['RP-B']})
ROLE_REF = {k: v.ref for k, v in ROLE.items()}


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
    print('roles:', ROLE_REF)
    for n, pp in sorted(ns.items()):
        if len(pp) < 2:
            print('SINGLE-PIN NET', n, pp)
