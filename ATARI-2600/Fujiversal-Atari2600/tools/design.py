"""Fujiversal-Atari2600 Rev0 (RP2040) -- the single source of truth.

Every part, value, footprint, MPN, LCSC code and pin->net assignment lives
here.  gen_sch.py, gen_pcb.py and export.py import it; the KiCad files are
generated output.  check_nets.py deliberately does NOT: it re-derives the
contract from the firmware headers.

Circuit provenance: FujiNet-Astrocade Rev0 / FujiNet-INTV-Rev0 (the ESP32-S3,
USB-UART and power blocks; CERN-OHL-W-2.0, itself from PiNTY CARD).  Firmware
contracts (fujinet-firmware, branch 2600-experiment):
  pico/atari-2600/firmware/include/vcs_pins.h    A0-A12 GP2-14, D0-D7 GP15-22, DIR GP26
  pico/atari-2600/firmware/boards/fujivcs.cmake  RP2040, 2 MB flash, LED GP25 (boards/pico.h)
  include/pinmap/fujiversal-atari2600.h          S3 SD/LED/UART/RUN/BOOTSEL pins
Edge pinout (Atari 2600, 1-24): 1-8 A7..A0, 9-11 D0-D2, 12 GND, 13-17 D3-D7,
18 A12, 19 A10, 20 A11, 21 A9, 22 A8, 23 +5V, 24 GND.  Pins 1-12 are on the
face toward the console FRONT (label side, B.Cu here), 13-24 on the face
toward the console REAR (component side, F.Cu); pin 1 is opposite pin 24.
Taken from the working FujiPlusCart prototype's gerbers.
"""

LIB = 'Fujiversal-Atari2600'
PROJECT = 'Fujiversal-Atari2600-Rev0'
NC = None  # explicit no-connect

SHEETS = [  # (file stem, title, page)
    ('cart-rp2040', 'RP2040, flash, crystal', 2),
    ('bus-buffers', 'Edge + 74LVC245A buffers', 3),
    ('esp32s3-sd', 'ESP32-S3, microSD, status LED', 4),
    ('usb-uart', 'USB-C, CP2102N programming bridge', 5),
    ('power', 'Power: 5V OR, 3.3V buck', 6),
]

# ---- RP2040 (QFN-56) GPIO -> package pin ----------------------------------
RP_GPIO_PIN = {0: 2, 1: 3, 2: 4, 3: 5, 4: 6, 5: 7, 6: 8, 7: 9, 8: 11, 9: 12,
               10: 13, 11: 14, 12: 15, 13: 16, 14: 17, 15: 18, 16: 27, 17: 28,
               18: 29, 19: 30, 20: 31, 21: 32, 22: 34, 23: 35, 24: 36, 25: 37,
               26: 38, 27: 39, 28: 40, 29: 41}

# vcs_pins.h: ADDR_PIN 2 (A0-A12 = GP2-14), D0_PIN 15 (D0-D7 = GP15-22),
# DIR_PIN 26; boards/pico.h: PICO_DEFAULT_LED_PIN 25.  GP0/GP1 = UART0 pads.
RP_GPIO_NET = {2 + a: 'RA%d' % a for a in range(13)}
RP_GPIO_NET.update({15 + d: 'RD%d' % d for d in range(8)})
RP_GPIO_NET.update({0: 'RP_TX', 1: 'RP_RX', 25: 'RP_LED', 26: 'BUF_DIR'})

# ESP32-S3-WROOM-1 module pad -> function (pads per the KiCad symbol)
S3_PAD = {'GND': [1, 40, 41], '3V3': 2, 'EN': 3, 'IO4': 4, 'IO5': 5, 'IO6': 6,
          'IO7': 7, 'IO15': 8, 'IO16': 9, 'IO17': 10, 'IO18': 11, 'IO8': 12,
          'IO19': 13, 'IO20': 14, 'IO3': 15, 'IO46': 16, 'IO9': 17, 'IO10': 18,
          'IO11': 19, 'IO12': 20, 'IO13': 21, 'IO14': 22, 'IO21': 23,
          'IO47': 24, 'IO48': 25, 'IO45': 26, 'IO0': 27, 'IO35': 28,
          'IO36': 29, 'IO37': 30, 'IO38': 31, 'IO39': 32, 'IO40': 33,
          'IO41': 34, 'IO42': 35, 'RXD0': 36, 'TXD0': 37, 'IO2': 38, 'IO1': 39}
# fujiversal-atari2600.h (+ the RUN/BOOTSEL forcing contract shared with
# fujiversal-intv / -astrocade)
S3_NET = {'EN': 'S3_EN', 'IO0': 'S3_IO0', 'IO4': 'RUN_CTL', 'IO5': 'BOOTSEL_CTL',
          'IO19': 'USB_DM', 'IO20': 'USB_DP', 'IO38': 'SD_MOSI', 'IO39': 'SD_SCK',
          'IO40': 'SD_MISO', 'IO41': 'SD_CS', 'IO42': 'SD_CD', 'IO48': 'LED_STRIP',
          'RXD0': 'S3_RXD', 'TXD0': 'S3_TXD'}

# console-side (5V) nets on the edge
EDGE = {1: 'CA7', 2: 'CA6', 3: 'CA5', 4: 'CA4', 5: 'CA3', 6: 'CA2', 7: 'CA1', 8: 'CA0',
        9: 'CD0', 10: 'CD1', 11: 'CD2', 12: 'GND', 13: 'CD3', 14: 'CD4', 15: 'CD5',
        16: 'CD6', 17: 'CD7', 18: 'CA12', 19: 'CA10', 20: 'CA11', 21: 'CA9', 22: 'CA8',
        23: '+5V', 24: 'GND'}

# ---- 74LVC245A channel assignment ------------------------------------------
# A side = console edge (5V-tolerant inputs), B side = RP2040.  Channels are
# interchangeable, so each buffer's order follows the geometry (see
# placement.py): U3 sits under the RP2040's south row (A0-A9), U4 south-east
# (A10-A12 on the RP's east face, A8/A9), U5 serves the data byte.
#   buffer -> [channel 0..7] = bit name or None (unused: A input tied to GND)
BUF_ADDR_LO = ['A0', 'A1', 'A2', 'A3', 'A4', 'A5', 'A6', 'A7']
BUF_ADDR_HI = ['A8', 'A9', 'A10', 'A11', 'A12', None, None, None]
BUF_DATA = ['D0', 'D1', 'D2', 'D3', 'D4', 'D5', 'D6', 'D7']

# ---- common parts: (lib_id, footprint, MPN, LCSC) --------------------------
FP = lambda n: '%s:%s' % (LIB, n)
R0603 = FP('R_0603_1608Metric')
C0603 = FP('C_0603_1608Metric')
C0805 = FP('C_0805_2012Metric')
RES = {'27R': ('0603WAF270JT5E', 'C25190'), '33R': ('0603WAF330JT5E', 'C23140'),
       '330R': ('0603WAF3300T5E', 'C23138'), '1k': ('0603WAF1001T5E', 'C21190'),
       '5.1k': ('0603WAF5101T5E', 'C23186'), '10k': ('0603WAF1002T5E', 'C25804'),
       '22k': ('0603WAF2202T5E', 'C31850'), '47k': ('0603WAF4702T5E', 'C25819'),
       '100k': ('0603WAF1003T5E', 'C25803')}
CAP = {'15pF': (C0603, 'CL10C150JB8NNNC', 'C1644'),
       '100nF': (C0603, 'CC0603KRX7R9BB104', 'C14663'),
       '1uF': (C0603, 'CL10A105KB8NNNC', 'C15849'),
       '4.7uF': (C0603, 'CL10A475KO8NNNC', 'C19666'),
       '10uF': (C0603, 'CL10A106KP8NNNC', 'C19702'),
       '22uF': (C0805, 'CL21A226MAQNNNE', 'C45783')}


class Part:
    def __init__(self, prefix, lib_id, value, footprint, pins, sheet,
                 mpn='', lcsc='', desc='', unit_pins=None, bom=True):
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


def buffer(chans, dir_net, desc):
    """74LVC245A: pin 1 DIR (H = A->B), 2-9 A0-A7, 10 GND, 11-18 B7-B0,
    19 /OE, 20 VCC.  A = console edge, B = RP2040."""
    pins = {1: dir_net, 10: 'GND', 19: 'GND', 20: '+3V3'}
    for k, bit in enumerate(chans):
        pins[2 + k] = ('C' + bit) if bit else 'GND'
        pins[18 - k] = ('R' + bit) if bit else NC
    return add('U', '74xx:74LS245', '74LVC245A', FP('TSSOP-20_4.4x6.5mm_P0.65mm'), pins,
               mpn='74LVC245APW,118', lcsc='C6082', desc=desc)


# =========================================================================
sheet('cart-rp2040')
rp = {1: '+3V3', 10: '+3V3', 22: '+3V3', 33: '+3V3', 42: '+3V3', 49: '+3V3',  # IOVDD
      19: 'GND',                                        # TESTEN
      20: 'XIN', 21: 'XOUT', 23: 'DVDD', 50: 'DVDD',
      24: 'SWCLK', 25: 'SWDIO', 26: 'RUN',
      43: '+3V3', 44: '+3V3', 45: 'DVDD',               # ADC_AVDD, VREG_VIN, VREG_VOUT
      46: 'RP_USB_DM', 47: 'RP_USB_DP', 48: '+3V3',     # USB_VDD
      51: 'QSPI_SD3', 52: 'QSPI_SCLK', 53: 'QSPI_SD0', 54: 'QSPI_SD2', 55: 'QSPI_SD1',
      56: 'QSPI_SS', 57: 'GND'}
for g, pin in RP_GPIO_PIN.items():
    rp[pin] = RP_GPIO_NET.get(g, NC)
add('U', 'MCU_RaspberryPi:RP2040', 'RP2040', FP('QFN-56-1EP_7x7mm_P0.4mm_EP3.2x3.2mm'), rp,
    mpn='RP2040', lcsc='C2040', desc='cartridge bus server (fujivcs)')
add('U', 'Memory_Flash:W25Q32JVSS', 'W25Q16JVSSIQ', FP('SOIC-8_5.3x5.3mm_P1.27mm'),
    {1: 'QSPI_SS', 2: 'QSPI_SD1', 3: 'QSPI_SD2', 4: 'GND', 5: 'QSPI_SD0', 6: 'QSPI_SCLK',
     7: 'QSPI_SD3', 8: '+3V3'},
    mpn='W25Q16JVSSIQ', lcsc='C131025', desc='2 MB QSPI flash (PICO_FLASH_SIZE_BYTES 2097152)')
C('100nF', '+3V3', desc='flash VCC')
# decoupling: one 100nF per IOVDD pin + USB_VDD + ADC_AVDD, 1uF on VREG_VIN/VOUT
for _ in range(6):
    C('100nF', '+3V3', desc='IOVDD decoupling')
C('100nF', '+3V3', desc='USB_VDD decoupling')
C('100nF', '+3V3', desc='ADC_AVDD decoupling')
C('1uF', '+3V3', desc='VREG_VIN')
C('1uF', 'DVDD', desc='VREG_VOUT (core 1.1V)')
C('100nF', 'DVDD', desc='DVDD decoupling')
C('100nF', 'DVDD', desc='DVDD decoupling')
C('10uF', '+3V3', desc='RP 3V3 bulk')
# 12 MHz crystal (Raspberry Pi minimal design values)
add('Y', 'Device:Crystal_GND24', '12MHz', FP('Crystal_SMD_3225-4Pin_3.2x2.5mm'),
    {1: 'XIN', 2: 'GND', 3: 'XOUT_Y', 4: 'GND'}, mpn='ABM8-272-T3', lcsc='C20625731')
C('15pF', 'XIN', desc='crystal load')
C('15pF', 'XOUT_Y', desc='crystal load')
R('1k', 'XOUT', 'XOUT_Y', desc='crystal drive limit')
# RESET resets both MCUs: the way back to the browser after launching a game
# (vcs main.c: "getting back to the browser ... an item for the PCB")
SW('RESET', 'RST_BTN', 'cart RESET: RP RUN + S3 EN via BAT54C')
add('D', 'Diode:BAT54C', 'BAT54C', FP('SOT-23'), {1: 'RUN', 2: 'S3_EN', 3: 'RST_BTN'},
    mpn='BAT54C,215', lcsc='C37704', desc='RESET steering, common cathode')
# RUN / BOOTSEL.  The S3 forces them exactly as fnPicoUpdater expects: its
# pins idle as inputs and are driven LOW to assert.  Same 3.3V rail on both
# chips, so a 1k series resistor is the whole interface (no inverting NPN).
R('10k', '+3V3', 'RUN', desc='RUN pull-up')
R('10k', '+3V3', 'QSPI_SS', desc='QSPI_SS pull-up')
R('1k', 'QSPI_SS', 'BOOTSEL_BTN', desc='BOOTSEL button series')
SW('BOOTSEL', 'BOOTSEL_BTN', 'RP2040 BOOTSEL (hold while pressing RESET)')
R('1k', 'RUN_CTL', 'RUN', desc='S3 IO4 -> RP RUN (drive low = reset)')
R('1k', 'BOOTSEL_CTL', 'QSPI_SS', desc='S3 IO5 -> RP QSPI_SS (low through reset = BOOTSEL)')
# RP <-> S3 native USB (RP = CDC device, S3 = host)
R('27R', 'USB_DP', 'RP_USB_DP', desc='USB series')
R('27R', 'USB_DM', 'RP_USB_DM', desc='USB series')
# activity LED (PICO_DEFAULT_LED_PIN)
R('1k', 'RP_LED', 'RP_LED_A', desc='LED series')
add('D', 'Device:LED', 'green', FP('LED_0603_1608Metric'), {1: 'GND', 2: 'RP_LED_A'},
    mpn='KT-0603G', lcsc='C12624', desc='RP activity LED (GP25)')
TP('SWCLK', 'SWCLK')
TP('SWDIO', 'SWDIO')
TP('GND', 'GND')
TP('RP_TX', 'RP_TX')
TP('RP_RX', 'RP_RX')

# =========================================================================
sheet('bus-buffers')
add('J', '%s:Atari2600_Cart_Edge_24' % LIB, 'Atari2600_Cart_Edge_24', FP('Atari2600_Cart_Edge_24'),
    EDGE, desc='24 gold fingers, 12 per face, 2.54 mm pitch', bom=False)
buffer(BUF_ADDR_LO, '+3V3', 'A0-A7 console -> RP (DIR high: A->B always)')
buffer(BUF_ADDR_HI, '+3V3', 'A8-A12 console -> RP (DIR high: A->B always)')
buffer(BUF_DATA, 'BUF_DIR', 'D0-D7; DIR = GP26, low = cart drives the console')
# DIR idles high (console -> RP) while the RP is in reset / BOOTSEL / unpowered
# firmware, matching main.c's boot default: the cart never drives the bus
# until the firmware says so.
R('10k', '+3V3', 'BUF_DIR', desc='DIR pull-up: not driving the console by default')
for _ in range(3):
    C('100nF', '+3V3', desc="'245 VCC decoupling")
C('10uF', '+5V', desc='edge 5V bulk at the connector')

# =========================================================================
sheet('esp32s3-sd')
s3 = {}
for fn, pad in S3_PAD.items():
    for p in (pad if isinstance(pad, list) else [pad]):
        s3[p] = 'GND' if fn == 'GND' else '+3V3' if fn == '3V3' else S3_NET.get(fn, NC)
add('U', 'RF_Module:ESP32-S3-WROOM-1', 'ESP32-S3-WROOM-1-N16R8', FP('ESP32-S3-WROOM-1'), s3,
    mpn='ESP32-S3-WROOM-1-N16R8', lcsc='C2913202', desc='FujiNet core (fujiversal-atari2600)')
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
add('D', 'Diode:SS34', 'SS34', FP('D_SMA'), {1: 'VIN', 2: '+5V'}, mpn='SS34', lcsc='C8678',
    desc='console 5V OR-ing')
add('D', 'Diode:SS34', 'SS34', FP('D_SMA'), {1: 'VIN', 2: 'VBUS'}, mpn='SS34', lcsc='C8678',
    desc='USB VBUS OR-ing (no back-feed into the console)')
C('100nF', '+5V', desc='edge 5V HF bypass')
C('22uF', 'VIN', desc='buck input')
C('22uF', 'VIN', desc='buck input')
C('100nF', 'VIN', desc='buck input HF')
add('U', 'Regulator_Switching:AP63203WU', 'AP63203WU', FP('TSOT-23-6'),
    {1: '+3V3', 2: 'VIN', 3: 'VIN', 4: 'GND', 5: 'BUCK_SW', 6: 'BUCK_BST'},
    mpn='AP63203WU-7', lcsc='C780769', desc='3.3V 2A buck')
C('100nF', 'BUCK_SW', 'BUCK_BST', desc='bootstrap')
add('L', 'Device:L', '6.8uH', FP('L_Sunlord_SWPA4030S'), {1: 'BUCK_SW', 2: '+3V3'},
    mpn='SWPA4030S6R8MT', lcsc='C62684', desc='buck inductor')
C('22uF', '+3V3', desc='buck output')
C('22uF', '+3V3', desc='buck output')

# PWR_FLAGs: nets whose drivers are passive pins
PWR_FLAG_NETS = ['GND', '+5V', 'VBUS', 'VIN', '+3V3']   # DVDD: driven by VREG_VOUT

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
        print(p.sheet, p.ref, p.value, p.footprint.split(':')[1], p.lcsc, p.desc)
    ns = nets()
    print(len(PARTS), 'parts', len(ns), 'nets')
    for n, pp in sorted(ns.items()):
        if len(pp) < 2:
            print('SINGLE-PIN NET', n, pp)
