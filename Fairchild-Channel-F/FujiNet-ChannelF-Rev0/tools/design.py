"""FujiNet-ChannelF Rev0 (RP2040 + ESP32-S3) -- the single source of truth.

Every part, value, footprint, MPN, LCSC code and pin->net assignment lives
here.  gen_sch.py, check_nets.py and export.py import it; the KiCad files are
generated output.  Parts are addressed by `key` (the drawing, the audits).

One sheet per block, console side first: the schematic reads from the cartridge
slot outward, signals flowing left to right (tools/sch_layout.py).  The edge,
the two translators and the whole RP2040 (one symbol) share the cart-rp sheet,
so the bus is wired from the slot straight into the MCU.

Firmware contract (unchanged by this board -- the RP2040 runs it as-is):
  fujinet-firmware pico/channelf/firmware/include/channelf_cart.h   D0-D7 GP0-7 through a '245,
      ROMC0-4 GP8-12, WRITE GP13, PHI GP14, DIR GP15 (1 = console -> cart, 0 = cart drives),
      /INTREQ GP16 (declared, never driven)
  pico/channelf/firmware/boards/fujichannelf.{h,cmake}  stock Pico: RP2040, 2 MB flash, LED GP25
  include/pinmap/fujiversal-channelf.h (branch fujiversal-channelf-board)  S3: SD 38-41, UART0
      43/44, WS2812 48; RUN / BOOTSEL forcing IO4 / IO5 as on the Astrocade board
Edge pinout (channelf.se veswiki 'Pinouts'): 1-2 GND, 3 D0, 4 D1, 5 /INTREQ, 6-8 ROMC0-2, 9 D2,
10 ROMC3, 11 D3, 12 ROMC4, 13 PHI, 14 D4, 15 WRITE, 16 D5, 17 D6, 18 D7, 19-20 +5V, 21 NC, 22 +12V.

Level translation: two SN74LVC4245A, A port = the console at 5 V (VCCA = CONS_5V, straight off
edge pins 19/20, ahead of the OR diode), B port = the RP2040 at 3.3 V.  The F3850's data bus wants
VIH 2.9 V min (F3850 datasheet Table 7) -- a 3.3 V driver has no margin -- and the RP2040's pads
are not 5 V tolerant (VPIN max IOVDD + 0.5 V).  The '4245A's A port has TTL inputs (VIH 2.0 V)
and drives 5 V levels; DIR high = A -> B, which is the firmware's polarity (DIR = 1 idles the
data buffer console -> cart).  With the console off, VCCA < 100 mV puts every '4245A output in
high-Z (SCAS375K 7.5), so a USB-powered cart cannot back-power the console through the bus.

Rails: CONS_5V is edge pins 19/20; +5V is the diode-OR of CONS_5V and USB VBUS; +3V3 (AP63203
buck) feeds the S3, CP2102N and microSD; +3V3_RP (AP2112K LDO) feeds the RP2040, its flash and
both translators' B ports; DVDD is the RP2040's own 1.1 V core regulator output.
"""

LIB = 'FujiNet-ChannelF'
PROJECT = 'FujiNet-ChannelF-Rev0'
NC = None  # explicit no-connect

SHEETS = [  # (file stem, title, page): console side first
    ('cart-rp', 'Cart bus -> RP2040', 2),
    ('fujinet', 'FujiNet (ESP32-S3)', 3),
    ('usb', 'USB-C + CP2102N', 4),
    ('power', 'Power', 5),
]
SHEET_ORDER = [s[0] for s in SHEETS]

# ---- RP2040 (QFN-56) GPIO -> package pin (RP2040 datasheet 1.4.2, Table 2) --------------
RP_GPIO_PIN = {g: 2 + g for g in range(8)}
RP_GPIO_PIN.update({g: 3 + g for g in range(8, 16)})
RP_GPIO_PIN.update({g: 11 + g for g in range(16, 22)})
RP_GPIO_PIN.update({g: 12 + g for g in range(22, 30)})

# channelf_cart.h: D0_PIN 0 (D0-D7 = GP0-7), ROMC0_PIN 8 (GP8-12), WRITE_PIN 13, PHI_PIN 14,
# DIR_PIN 15, INTREQ_PIN 16; boards/pico.h PICO_DEFAULT_LED_PIN 25.  GP17 is a spare broken out
# to a pad for scope triggers (the WRITE-edge timing is PROVISIONAL in channelf_cart.c).
RP_GPIO_NET = {g: 'RP_D%d' % g for g in range(8)}
RP_GPIO_NET.update({8 + i: 'RP_ROMC%d' % i for i in range(5)})
RP_GPIO_NET.update({13: 'RP_WRITE', 14: 'RP_PHI', 15: 'RP_DIR', 16: 'RP_INTREQ', 17: 'RP_GP17', 25: 'RP_LED'})
RP_RAIL = '+3V3_RP'
RP_IOVDD_PINS = [1, 10, 22, 33, 42, 49]
RP_DVDD_PINS = [23, 50]

# ESP32-S3-WROOM-1 module pad -> function (pads per the KiCad symbol)
S3_PAD = {'GND': [1, 40, 41], '3V3': 2, 'EN': 3, 'IO4': 4, 'IO5': 5, 'IO6': 6,
          'IO7': 7, 'IO15': 8, 'IO16': 9, 'IO17': 10, 'IO18': 11, 'IO8': 12,
          'IO19': 13, 'IO20': 14, 'IO3': 15, 'IO46': 16, 'IO9': 17, 'IO10': 18,
          'IO11': 19, 'IO12': 20, 'IO13': 21, 'IO14': 22, 'IO21': 23,
          'IO47': 24, 'IO48': 25, 'IO45': 26, 'IO0': 27, 'IO35': 28,
          'IO36': 29, 'IO37': 30, 'IO38': 31, 'IO39': 32, 'IO40': 33,
          'IO41': 34, 'IO42': 35, 'RXD0': 36, 'TXD0': 37, 'IO2': 38, 'IO1': 39}
# fujiversal-channelf.h (SD, UART0, LED strip) + the Astrocade board's RUN/BOOTSEL forcing pins
S3_NET = {'EN': 'S3_EN', 'IO0': 'S3_IO0', 'IO4': 'RUN_CTL', 'IO5': 'BOOTSEL_CTL',
          'IO19': 'USB_DM', 'IO20': 'USB_DP', 'IO38': 'SD_MOSI', 'IO39': 'SD_SCK',
          'IO40': 'SD_MISO', 'IO41': 'SD_CS', 'IO42': 'SD_CD', 'IO48': 'LED_STRIP',
          'RXD0': 'S3_RXD', 'TXD0': 'S3_TXD'}

# the 22-pin Videocart edge (console side of the translators: the F8 bus signal names)
EDGE = {1: 'GND', 2: 'GND', 3: 'D0', 4: 'D1', 5: 'INTREQ_N', 6: 'ROMC0', 7: 'ROMC1', 8: 'ROMC2',
        9: 'D2', 10: 'ROMC3', 11: 'D3', 12: 'ROMC4', 13: 'PHI', 14: 'D4', 15: 'WRITE', 16: 'D5',
        17: 'D6', 18: 'D7', 19: 'CONS_5V', 20: 'CONS_5V', 21: NC, 22: NC}   # 22 = +12V, unused

# ---- the two translators: channel -> (console net, RP net); A1-A8 = pins 3-10, B1-B8 = 21-14 ----
DATA_CH = [('D%d' % i, 'RP_D%d' % i) for i in range(8)]
# control: WRITE first and PHI last, so each has a free side for its scope pad
CTRL_CH = [('WRITE', 'RP_WRITE')] + [('ROMC%d' % i, 'RP_ROMC%d' % i) for i in range(5)] + \
          [('PHI', 'RP_PHI'), ('CBUF_A8', NC)]                 # A8 unused: pulled low, B8 open
A_PIN = {k: 2 + k for k in range(1, 9)}                         # A1 -> 3 ... A8 -> 10
B_PIN = {k: 22 - k for k in range(1, 9)}                        # B1 -> 21 ... B8 -> 14

# ---- common parts: (lib_id, footprint, MPN, LCSC) --------------------------
FP = lambda n: '%s:%s' % (LIB, n)
R0603 = FP('R_0603_1608Metric')
C0603 = FP('C_0603_1608Metric')
C0805 = FP('C_0805_2012Metric')
RES = {'27R': ('0603WAF270JT5E', 'C25190'), '330R': ('0603WAF3300T5E', 'C23138'),
       '1k': ('0603WAF1001T5E', 'C21190'), '4.7k': ('0603WAF4701T5E', 'C23162'),
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
                 mpn='', lcsc='', desc='', bom=True, dnp=False, ds='', key=None):
        self.prefix, self.lib_id, self.value, self.footprint = prefix, lib_id, value, footprint
        self.pins = {str(k): v for k, v in pins.items()}  # pad number -> net (None = NC)
        self.sheet, self.mpn, self.lcsc, self.desc, self.bom, self.dnp = sheet, mpn, lcsc, desc, bom, dnp
        self.mfr = ''
        self.ds = ds                                       # datasheet URL when the stock symbol's is another part's
        self.key = key      # stable name the drawing scripts use
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


def R(value, a, b, desc='', key=None):
    mpn, lcsc = RES[value]
    return add('R', 'Device:R', value, R0603, {1: a, 2: b}, mpn=mpn, lcsc=lcsc, desc=desc, key=key)


def C(value, a, b='GND', desc='', key=None):
    fp, mpn, lcsc = CAP[value]
    return add('C', 'Device:C', value, fp, {1: a, 2: b}, mpn=mpn, lcsc=lcsc, desc=desc, key=key)


def SW(value, net, desc, key=None):
    return add('SW', 'Switch:SW_Push', value, FP('SW_SPST_TL3342'), {1: net, 2: 'GND'},
               mpn='TL3342F160QG', lcsc='C2886898', desc=desc, key=key)


def TP(net, label, key=None):
    return add('TP', 'Connector:TestPoint', label, FP('TestPoint_Pad_D1.5mm'), {1: net},
               desc='test pad', bom=False, key=key)


def LVC4245(key, ch, dir_net, desc):
    """An SN74LVC4245A: A port (VCCA, pin 1) on the console's 5 V, B port (VCCB, 23/24) on the
    RP's 3.3 V, /OE (22) tied low; ch = [(A net, B net)] for channels 1-8."""
    pins = {1: 'CONS_5V', 2: dir_net, 11: 'GND', 12: 'GND', 13: 'GND', 22: 'GND',
            23: RP_RAIL, 24: RP_RAIL}
    for k, (a, b) in enumerate(ch, 1):
        pins[A_PIN[k]] = a
        pins[B_PIN[k]] = b
    return add('U', '%s:SN74LVC4245A' % LIB, 'SN74LVC4245APWR', FP('TSSOP-24_4.4x7.8mm_P0.65mm'), pins,
               mpn='SN74LVC4245APWR', lcsc='C7859', desc=desc, key=key,
               ds='https://www.ti.com/lit/ds/symlink/sn74lvc4245a.pdf')


# =========================================================================
# cart-rp: the edge, the two translators, the RP2040 and its own circuit
sheet('cart-rp')
rp = {p: RP_RAIL for p in RP_IOVDD_PINS}                                     # IOVDD
rp.update({p: 'DVDD' for p in RP_DVDD_PINS})
rp.update({19: 'GND',                                                        # TESTEN
           20: 'XIN', 21: 'XOUT', 24: 'SWCLK', 25: 'SWDIO', 26: 'RUN',
           43: RP_RAIL,                                                      # ADC_AVDD
           44: RP_RAIL, 45: 'DVDD',                                          # VREG_VIN, VREG_VOUT
           46: 'RP_USB_DM', 47: 'RP_USB_DP', 48: RP_RAIL,                    # USB_VDD
           51: 'QSPI_SD3', 52: 'QSPI_SCLK', 53: 'QSPI_SD0', 54: 'QSPI_SD2', 55: 'QSPI_SD1',
           56: 'QSPI_SS', 57: 'GND'})
for g, pin in RP_GPIO_PIN.items():
    rp[pin] = RP_GPIO_NET.get(g, NC)
U_RP = add('U', '%s:RP2040_Fn' % LIB, 'RP2040', FP('QFN-56-1EP_7x7mm_P0.4mm_EP3.2x3.2mm'), rp,
           mpn='RP2040', lcsc='C2040', desc='F8 bus memory device: ROMC state machine on core1 (fujichannelf)',
           key='U_RP', ds='https://datasheets.raspberrypi.com/rp2040/rp2040-datasheet.pdf')
# one symbol, pins by function (gen_sch.rp_symbol): the bus on the left, row for row with the
# translators, the flash and crystal under it; supplies top and bottom; USB / SWD / RUN on the right
# no footprint yet: the Videocart edge's contact geometry (faces, pitch, pin 1) is to be measured from a
# real cartridge before layout -- not guessed (README, open items)
add('J', '%s:ChannelF_Cart_Edge_22' % LIB, 'ChannelF_Cart_Edge_22', '',
    EDGE, desc='Fairchild Channel F Videocart edge, 22 contacts (footprint: measure a real Videocart first)',
    bom=False, key='J_EDGE')
LVC4245('U_DBUF', DATA_CH, 'RP_DIR', 'F8 data bus D0-D7: A = console 5 V, B = RP2040; DIR = GP15')
C('100nF', 'CONS_5V', desc='data translator VCCA', key='C_DBUFA')
C('100nF', RP_RAIL, desc='data translator VCCB', key='C_DBUFB')
# GP15 floats with the RP2040's 50-80 kOhm pad pull-down through reset and boot (datasheet 5.5.3):
# 4.7k holds DIR >= 3.0 V (VIH 2.0 V), i.e. console -> cart, until the firmware owns the pin
R('4.7k', RP_RAIL, 'RP_DIR', desc='DIR pull-up: console -> cart through RP reset / boot', key='R_DIR')
TP('RP_DIR', 'DIR', key='TP_DIR')
LVC4245('U_CBUF', CTRL_CH, 'CONS_5V', 'F8 ROMC0-4, WRITE, PHI: console -> RP2040 only (DIR high)')
C('100nF', 'CONS_5V', desc='control translator VCCA', key='C_CBUFA')
# SCAS375K 5.4 note 1: unused inputs held at VCC or GND -- through 10k, not straight onto the GND plane net
R('10k', 'CBUF_A8', 'GND', desc='control translator spare input A8 held low', key='R_A8')
C('100nF', RP_RAIL, desc='control translator VCCB', key='C_CBUFB')
TP('RP_WRITE', 'WRITE', key='TP_WRITE')
TP('RP_PHI', 'PHI', key='TP_PHI')
# /INTREQ: open drain, as the F3850 wants it (internal pull-up to VDD); GP16 is never driven, the
# gate pull-down keeps the FET off through reset and with no firmware at all
add('Q', 'Transistor_FET:2N7002', '2N7002', FP('SOT-23'), {1: 'RP_INTREQ', 2: 'GND', 3: 'INTREQ_N'},
    mpn='2N7002', lcsc='C8545', desc='/INTREQ open-drain driver (GP16, unused by the firmware)', key='Q_INT')
R('100k', 'RP_INTREQ', 'GND', desc='/INTREQ FET gate pull-down', key='R_INTPD')
# activity LED (boards/pico.h PICO_DEFAULT_LED_PIN 25; main.c lights it at boot)
R('330R', 'RP_LED', 'RP_LED_A', desc='LED series (KT-0603G VF ~2.6-2.85 V: 1.5-2 mA from 3.3 V)', key='R_LED')
add('D', 'Device:LED', 'green', FP('LED_0603_1608Metric'), {1: 'GND', 2: 'RP_LED_A'},
    mpn='KT-0603G', lcsc='C12624', desc='RP activity LED', key='D_LED')
TP('RP_GP17', 'GP17', key='TP_GP17')

# ---- the RP2040's own circuit: supplies and decoupling, core regulator, QSPI flash, crystal,
# RUN / BOOTSEL / RESET, SWD, the USB link to the S3 (Hardware design with RP2040, ch. 2)
for pin in RP_IOVDD_PINS:
    C('100nF', RP_RAIL, desc='IOVDD decoupling', key='C_IOV%d' % pin)
C('100nF', RP_RAIL, desc='USB_VDD decoupling', key='C_USBV')
C('100nF', RP_RAIL, desc='ADC_AVDD decoupling', key='C_ADC')
C('1uF', RP_RAIL, desc='VREG_VIN (design guide 2.1.3: 1 uF close to the input)', key='C_VREGIN')
C('10uF', RP_RAIL, desc='RP 3V3 bulk', key='C_IOBULK')
C('1uF', 'DVDD', desc='VREG_VOUT (design guide 2.1.3: 1 uF close to the output)', key='C_VREGOUT')
for pin in RP_DVDD_PINS:
    C('100nF', 'DVDD', desc='DVDD decoupling', key='C_DV%d' % pin)
# QSPI flash: 2 MB (boards/fujichannelf.cmake PICO_FLASH_SIZE_BYTES), W25Q080-compatible boot2
add('U', 'Memory_Flash:W25Q16JVSS', 'W25Q16JVSSIQ', FP('SOIC-8_5.3x5.3mm_P1.27mm'),
    {1: 'QSPI_SS', 2: 'QSPI_SD1', 3: 'QSPI_SD2', 4: 'GND', 5: 'QSPI_SD0', 6: 'QSPI_SCLK',
     7: 'QSPI_SD3', 8: RP_RAIL}, mpn='W25Q16JVSSIQ', lcsc='C82317', desc='2 MB QSPI boot flash',
    key='U_FLASH')
C('100nF', RP_RAIL, desc='flash VCC decoupling', key='C_FLASH')
# 12 MHz crystal (design guide 2.3: ABM8-272-T3, 15 pF each side, 1k series on XOUT)
add('Y', 'Device:Crystal_GND24', '12MHz', FP('Crystal_SMD_3225-4Pin_3.2x2.5mm'),
    {1: 'XIN', 2: 'GND', 3: 'XOUT_Y', 4: 'GND'}, mpn='ABM8-272-T3', lcsc='C20625731', key='Y_RP')
C('15pF', 'XIN', desc='crystal load', key='C_XIN')
C('15pF', 'XOUT_Y', desc='crystal load', key='C_XOUT')
R('1k', 'XOUT', 'XOUT_Y', desc='crystal drive limit', key='R_XOUT')
# RUN / BOOTSEL.  The S3 forces them as fnPicoUpdater::forceBootselViaPins() expects: its pins idle
# as inputs and are driven LOW to assert.  Same 3.3 V rail on both chips: a 1k series resistor is
# the whole interface.
R('10k', RP_RAIL, 'QSPI_SS', desc='QSPI_SS pull-up (design guide 2.2: flash /CS high at power-up)', key='R_SS')
R('1k', 'QSPI_SS', 'BOOTSEL_BTN', desc='BOOTSEL button series (design guide 2.2)', key='R_BSEL')
SW('BOOTSEL', 'BOOTSEL_BTN', 'RP2040 BOOTSEL (hold while pressing RESET)', key='SW_BOOTSEL')
R('1k', 'BOOTSEL_CTL', 'QSPI_SS', desc='S3 IO5 -> RP QSPI_SS (low through reset = BOOTSEL)', key='R_BSELCTL')
R('10k', RP_RAIL, 'RUN', desc='RUN pull-up', key='R_RUN')
R('1k', 'RUN_CTL', 'RUN', desc='S3 IO4 -> RP RUN (drive low = reset)', key='R_RUNCTL')
# RESET resets both MCUs: the button pulls RP RUN and S3 EN low through a common-cathode pair, so
# neither chip's reset drives the other's.  It is also the way back to CONFIG after a booted
# Videocart: there is no reset pin on the cart edge (main.c).
SW('RESET', 'RST_BTN', 'cart RESET: RP RUN + S3 EN via BAT54C', key='SW_RESET')
add('D', 'Diode:BAT54C', 'BAT54C', FP('SOT-23'), {1: 'RUN', 2: 'S3_EN', 3: 'RST_BTN'},
    mpn='BAT54C,215', lcsc='C37704', desc='RESET steering, common cathode', key='D_RST')
# RP <-> S3 native USB (RP = CDC device, S3 = host): design guide 2.4, 27R series at the chip
R('27R', 'USB_DP', 'RP_USB_DP', desc='USB series', key='R_USBP')
R('27R', 'USB_DM', 'RP_USB_DM', desc='USB series', key='R_USBM')
# the RP has no PC-facing USB: first flash over SWD (Debug Probe), or PICOBOOT from the S3
TP('SWCLK', 'SWCLK', key='TP_SWCLK')
TP('SWDIO', 'SWDIO', key='TP_SWDIO')
TP('GND', 'GND', key='TP_GND')
TP('RUN', 'RUN', key='TP_RUN')
TP('QSPI_SS', 'BOOTSEL', key='TP_BOOTSEL')

# =========================================================================
# fujinet: the ESP32-S3, microSD, the WS2812 status LED
sheet('fujinet')
s3 = {}
for fn, pad in S3_PAD.items():
    for p in (pad if isinstance(pad, list) else [pad]):
        s3[p] = 'GND' if fn == 'GND' else '+3V3' if fn == '3V3' else S3_NET.get(fn, NC)
add('U', '%s:ESP32-S3-WROOM-1_Fn' % LIB, 'ESP32-S3-WROOM-1-N16R8', FP('ESP32-S3-WROOM-1'), s3,
    mpn='ESP32-S3-WROOM-1-N16R8', lcsc='C2913202', desc='FujiNet core (fujiversal-channelf)', key='U_S3')
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
# TF-015 card-detect: open with no card, closed to the shell (GND) with a card in
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
# Diode OR: no back-feed from USB into an unpowered console, nor from the console into the USB
# host.  SS34 VF ~0.35 V at the cart's ~0.4 A: +5V is 4.4-4.9 V on a 4.75-5.25 V console rail --
# above the AP63203's 3.8 V and the AP2112K's 3.3 V + 0.25 V dropout.  The only 5 V logic is the
# translators' A ports, and they sit on CONS_5V itself, ahead of this diode.
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
# RP rail: AP2112K-3.3 straight off +5V.  In dropout it follows the console rail as it rises,
# instead of waiting out the buck's UVLO + 4 ms soft-start, so the RP2040 and its flash come up
# with the console bus.
add('U', 'Regulator_Linear:AP2112K-3.3', 'AP2112K-3.3', FP('SOT-23-5'),
    {1: '+5V', 2: 'GND', 3: '+5V', 4: NC, 5: RP_RAIL},
    mpn='AP2112K-3.3TRG1', lcsc='C51118', desc='RP2040 + flash + translator B ports 3.3V LDO, fast start',
    key='U_LDO')
C('1uF', '+5V', desc='LDO input', key='C_LDOIN')
C('1uF', RP_RAIL, desc='LDO output', key='C_LDOOUT')
TP('+5V', '+5V', key='TP_5V')
TP('+3V3', '+3V3', key='TP_3V3')
TP(RP_RAIL, '+3V3_RP', key='TP_3V3RP')

# PWR_FLAGs: nets whose drivers are passive pins (+3V3_RP: LDO power_out; DVDD: VREG_VOUT power_out)
PWR_FLAG_NETS = ['GND', 'CONS_5V', 'VBUS', '+5V', '+3V3']
# nets drawn as power symbols (global, never prefixed)
RAIL_NETS = ['GND', 'CONS_5V', 'VBUS', '+5V', '+3V3', '+3V3_RP', 'DVDD']

# ---- references: by sheet order, U / J / ... numbered as declared (no routed board to freeze yet;
# tools/refs.lock, if present, pins key -> reference as on the sibling carts)
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
        print(p.sheet, p.ref, p.key, p.value, (p.footprint.split(':')[-1] or '-'), p.lcsc, 'DNP' if p.dnp else '')
    ns = nets()
    print(len(PARTS), 'parts', len(ns), 'nets')
    for n, pp in sorted(ns.items()):
        if len(pp) < 2:
            print('SINGLE-PIN NET', n, pp)
