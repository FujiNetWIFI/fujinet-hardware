"""FujiNet-Astrocade Rev0 (RP2354A) -- the single source of truth.

Every part, value, footprint, MPN, LCSC code and pin->net assignment lives
here.  gen_sch.py, gen_pcb.py, check_nets.py and export_jlc.py all import it;
the KiCad files are generated output.

Circuit provenance: the INTV Rev0 cart (fujinet-hardware INTV/FujiNet-INTV-Rev0,
itself adapted from PiNTY CARD, CERN-OHL-W-2.0).  Firmware contracts:
  fujinet-firmware pico/astrocade/firmware/include/astrocade_cart.h  (RP pins)
  fujinet-firmware include/pinmap/fujiversal-astrocade.h           (S3 pins)
Edge pinout (Tilton 1-26): 1 GND, 2-9 A7..A0, 10-12 D0-D2, 13 GND,
14-18 D3-D7, 19 A11, 20 A10, 21 /CCS, 22 A12, 23 A9, 24 A8, 25 +5V, 26 GND.
"""

LIB = 'FujiNet-Astrocade'
PROJECT = 'FujiNet-Astrocade-Rev0'
NC = None  # explicit no-connect

SHEETS = [  # (file stem, title, page)
    ('cart-rp2354a', 'RP2354A cartridge bus controller + edge', 2),
    ('esp32s3-sd', 'ESP32-S3 FujiNet core, microSD, status LED', 3),
    ('usb-uart', 'USB-C, CP2102N programming bridge', 4),
    ('power', 'Power: console 5V / USB VBUS OR, 3.3V buck', 5),
]

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
        20: 'CA10', 21: 'CCS_N', 22: 'CA12', 23: 'CA9', 24: 'CA8', 25: '+5V',
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
       '100k': ('0603WAF1003T5E', 'C25803'), '150k': ('0603WAF1503T5E', 'C22807')}
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


def R(value, a, b, desc='', size='0603'):
    mpn, lcsc = RES[value] if size == '0603' else RES0402[value]
    fp = R0603 if size == '0603' else FP('RPI_R0402')
    return add('R', 'Device:R', value, fp, {1: a, 2: b}, mpn=mpn, lcsc=lcsc, desc=desc)


def C(value, a, b='GND', desc='', size=None):
    fp, mpn, lcsc = CAP[value] if size is None else CAP0402[value]
    if size is not None:
        fp = FP(size)
    return add('C', 'Device:C', value, fp, {1: a, 2: b}, mpn=mpn, lcsc=lcsc, desc=desc)


def SW(value, net, desc):
    return add('SW', 'Switch:SW_Push', value, FP('SW_SPST_TL3342'), {1: net, 2: 'GND'},
               mpn='TL3342F160QG', lcsc='C2886898', desc=desc)


def TP(net, label):
    return add('TP', 'Connector:TestPoint', label, FP('TestPoint_Pad_D1.5mm'), {1: net},
               desc='test pad', bom=False)


# =========================================================================
sheet('cart-rp2354a')
rp = {1: '+3V3', 11: '+3V3', 20: '+3V3', 30: '+3V3', 38: '+3V3', 45: '+3V3',  # IOVDD
      6: 'DVDD', 23: 'DVDD', 39: 'DVDD', 50: 'DVDD',                          # DVDD, VREG_FB
      21: 'XIN', 22: 'XOUT', 24: 'SWCLK', 25: 'SWDIO', 26: 'RUN',
      44: '+3V3',          # ADC_AVDD
      46: 'VREG_AVDD', 47: 'GND', 48: 'RP_LX', 49: '+3V3',                    # VREG
      51: 'RP_USB_DM', 52: 'RP_USB_DP', 53: '+3V3', 54: '+3V3',
      55: NC, 56: NC, 57: NC, 58: NC, 59: NC,                                  # QSPI (flash in package)
      60: 'QSPI_SS', 61: 'GND'}
for g, pin in RP_GPIO_PIN.items():
    rp[pin] = RP_GPIO_NET.get(g, NC)
add('U', 'MCU_RaspberryPi:RP2354A', 'RP2354A', FP('RPI_RP2350A_QFN60'), rp,
    mpn='RP2354A', lcsc='C41378174', desc='RP2350A + 2MB flash in package; cart bus server')
add('J', '%s:Astrocade_Cart_Edge_26' % LIB, 'Astrocade_Cart_Edge_26', FP('Astrocade_Cart_Edge_26'),
    EDGE, desc='26 contact lands on B.Cu, blade contacts from below', bom=False)
# decoupling: one 100nF per IOVDD/DVDD/QSPI/USB/ADC supply pin, bulk on 3V3
for _ in range(6):
    C('100nF', '+3V3', desc='IOVDD decoupling')
C('100nF', '+3V3', desc='QSPI_IOVDD decoupling (extra)')
C('100nF', '+3V3', desc='USB_OTP_VDD + QSPI_IOVDD decoupling', size='RPI_C0402')
C('100nF', '+3V3', desc='ADC_AVDD decoupling')
C('4.7uF', '+3V3', desc='VREG_VIN bulk', size='RPI_C0402_wide')
C('10uF', '+3V3', desc='RP 3V3 bulk')
for _ in range(3):
    C('100nF', 'DVDD', desc='DVDD decoupling')
C('4.7uF', 'DVDD', desc='core regulator output', size='RPI_C0402_wide')
R('33R', '+3V3', 'VREG_AVDD', desc='VREG_AVDD filter', size='0402')
C('4.7uF', 'VREG_AVDD', desc='VREG_AVDD filter', size='RPI_C0402')
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
# console bus support
R('10k', '+3V3', 'CCS_N', desc='/CCS idle-high when no console')
R('100k', '+5V', 'VSENSE', desc='console 5V sense (GP26/ADC0 is not 5V tolerant)')
R('150k', 'VSENSE', 'GND', desc='console 5V sense -> 3.0V')
# RP <-> S3 native USB (RP = CDC device, S3 = host)
R('27R', 'USB_DP', 'RP_USB_DP', desc='USB series', size='0402')
R('27R', 'USB_DM', 'RP_USB_DM', desc='USB series', size='0402')
# activity LED
R('1k', 'RP_LED', 'RP_LED_A', desc='LED series')
add('D', 'Device:LED', 'green', FP('LED_0603_1608Metric'), {1: 'GND', 2: 'RP_LED_A'},
    mpn='KT-0603G', lcsc='C12624', desc='RP activity LED')
TP('SWCLK', 'SWCLK')
TP('SWDIO', 'SWDIO')
TP('GND', 'GND')
TP('SELFTEST', 'SELFTEST')
TP('RP_DBG_TX', 'DBG_TX')

# =========================================================================
sheet('esp32s3-sd')
s3 = {}
for fn, pad in S3_PAD.items():
    for p in (pad if isinstance(pad, list) else [pad]):
        s3[p] = 'GND' if fn == 'GND' else '+3V3' if fn == '3V3' else S3_NET.get(fn, NC)
add('U', 'RF_Module:ESP32-S3-WROOM-1', 'ESP32-S3-WROOM-1-N16R8', FP('ESP32-S3-WROOM-1'), s3,
    mpn='ESP32-S3-WROOM-1-N16R8', lcsc='C2913202', desc='FujiNet core (fujiversal-astrocade)')
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
C('22uF', 'VIN', desc='VIN bulk')
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
PWR_FLAG_NETS = ['GND', '+5V', 'VBUS', 'VIN', '+3V3', 'DVDD', 'VREG_AVDD']

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
