"""FujiNet-O2 Rev0 (RP2354B + ESP32-S3) -- the single source of truth.

Every part, value, footprint, MPN, LCSC code and pin->net assignment lives
here.  gen_sch.py, gen_pcb.py and export.py import it; the KiCad files are
generated output.  check_nets.py does NOT import it: it reads the netlist and
the firmware sources and checks one against the other.

Firmware contract (fujinet-firmware master, pico/o2):
  pico/o2/firmware/picopac_cart.c   A0_PIN..A11_PIN = GP0-11, P11_PIN 12, P10_PIN 13, D0_PIN..D7_PIN =
                                    GP14-21, PSEN_PIN 22, WR_PIN 23, CS_PIN 24 (P14), LED_PIN 25,
                                    NOTCS_PIN 26 (edge pin E), TD_PIN 27 (T0)
  pico/o2/firmware/CMakeLists.txt   (a plain RP2040 PicoPAC today: README "Firmware changes")
  include/pinmap/fujiversal-o2.h    S3 pins (SD, LED strip, UART0)
The RP2354B (QFN-80) keeps that map exactly: GPIO0-39 are 5 V tolerant on the QFN-80 (RP2350
datasheet Table 1674: "Digital IO (FT)"); its ADC pins are GPIO40-47.  The RP2354A could not: its
GPIO26-29 are the ADC pins, and the O2 needs 27 bus lines.
Edge pinout: Dan Boris, Odyssey 2 Technical Specs v1.1, checked against three built carts
(tools/edge_geom.py has the sources; tools/audit/edge_orientation.py the cross-check).

Circuit provenance:
  * the cart side is FujiNet-Arcadia Rev0's: the 5 V bus straight into the RP's 5 V-tolerant pads
    through 330R in every line (limits the current into a pad while IOVDD is still rising, and a
    contention or back-drive current to < 10 mA), the VSENSE divider (10k / 15k, under RP2350-E9's
    8.2 kOhm);
  * the RP2354B core, its regulator corner (Raspberry Pi's minimal design, MIT, moved onto the
    QFN-80) and the rp-core drawing are FujiNet-StudioII Rev0's;
  * the ESP32-S3 half, the USB-C (USBLC6-2SC6, CP2102N with the datasheet's 1k RSTb pull-up) and
    the power mux (TPS2116: USB first, the console second) are FujiNet-StudioII / Arcadia Rev0's.
"""

LIB = 'FujiNet-O2'
PROJECT = 'FujiNet-O2-Rev0'
NC = None  # explicit no-connect

SHEETS = [  # (file stem, title, page) -- in signal-flow order, console side first
    ('cart-bus', 'Cart bus: edge, 330R, RP2354B GPIO', 2),
    ('rp-core', 'RP2354B core, crystal, RUN, SWD', 3),
    ('fujinet', 'FujiNet (ESP32-S3), microSD', 4),
    ('usb', 'USB-C + CP2102N', 5),
    ('power', 'Power: mux, S3 buck, RP LDO', 6),
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
RP_RAIL = '+3V3_RP'   # IOVDD x8, QSPI_IOVDD, USB_OTP_VDD, ADC_AVDD, VREG_VIN, (VREG_AVDD through 33R)
RP_IO_RAIL = RP_CORE_RAIL = RP_RAIL     # (FujiNet-StudioII Rev0's names for it, in the ported core)
S3_RAIL = '+3V3'      # the AP63203 buck: ESP32-S3, CP2102N, microSD

# The console's lines, in GPIO order: (edge-side net, RP-side net, GPIO, series resistor).  The
# PicoPAC map (picopac_cart.c), plus the Videopac+ pin B on GP28 (README "Pin B").
BUS = ([('CA%d' % i, 'RP_A%d' % i, i, '330R') for i in range(12)] +
       [('CP11', 'RP_P11', 12, '330R'), ('CP10', 'RP_P10', 13, '330R')] +
       [('CD%d' % i, 'RP_D%d' % i, 14 + i, '330R') for i in range(8)] +
       [('PSEN_N', 'RP_PSEN', 22, '330R'), ('WR_N', 'RP_WR', 23, '330R'), ('CP14', 'RP_P14', 24, '330R'),
        ('EXTRAM', 'RP_EXTRAM', 26, '330R'), ('T0', 'RP_T0', 27, '330R'), ('VPB', 'RP_VPB', 28, '1k')])
RP_GPIO_NET = {g: NC for g in RP_GPIO_PIN}
RP_GPIO_NET.update({g: rn for _cn, rn, g, _r in BUS})
RP_GPIO_NET.update({25: 'RP_LED', 29: 'SELFTEST', 40: 'VSENSE', 44: 'DBG_TX', 45: 'DBG_RX'})
assert len(RP_GPIO_NET) == 48 and set(RP_GPIO_NET) == set(RP_GPIO_PIN)
# Only the FT pins may meet the 5 V bus: GPIO40-47 are the ADC pins (VPIN max IOVDD + 0.5 V)
assert all(g < 40 for _cn, _rn, g, _r in BUS)

# ESP32-S3-WROOM-1 module pad -> function (pads per the KiCad symbol)
S3_PAD = {'GND': [1, 40, 41], '3V3': 2, 'EN': 3, 'IO4': 4, 'IO5': 5, 'IO6': 6,
          'IO7': 7, 'IO15': 8, 'IO16': 9, 'IO17': 10, 'IO18': 11, 'IO8': 12,
          'IO19': 13, 'IO20': 14, 'IO3': 15, 'IO46': 16, 'IO9': 17, 'IO10': 18,
          'IO11': 19, 'IO12': 20, 'IO13': 21, 'IO14': 22, 'IO21': 23,
          'IO47': 24, 'IO48': 25, 'IO45': 26, 'IO0': 27, 'IO35': 28,
          'IO36': 29, 'IO37': 30, 'IO38': 31, 'IO39': 32, 'IO40': 33,
          'IO41': 34, 'IO42': 35, 'RXD0': 36, 'TXD0': 37, 'IO2': 38, 'IO1': 39}
# include/pinmap/fujiversal-o2.h (SD 38-41, UART0 43/44, LED strip 48; the RP link is the S3's own
# USB, IO19 / IO20) + the fujiversal RUN / BOOTSEL forcing pins (IO4 / IO5) and SD card detect on
# IO42, as every on-cart S3 board (README "Firmware changes": the pin map lacks them)
S3_NET = {'EN': 'S3_EN', 'IO0': 'S3_IO0', 'IO4': 'RUN_CTL', 'IO5': 'BOOTSEL_CTL',
          'IO19': 'USB_DM', 'IO20': 'USB_DP', 'IO38': 'SD_MOSI', 'IO39': 'SD_SCK',
          'IO40': 'SD_MISO', 'IO41': 'SD_CS', 'IO42': 'SD_CD', 'IO48': 'LED_STRIP',
          'RXD0': 'S3_RXD', 'TXD0': 'S3_TXD'}

# Odyssey 2 / Videopac cartridge port: pin -> (net, symbol pin name).  Dan Boris, Odyssey 2 Technical
# Specs v1.1 section 2.0; 1..15 on the parts face (F.Cu), A..R behind them (B.Cu).  N = A7 and P = A6
# (Boris, and the nets of bwack's, wilco2009's and PicoPAC's built carts; MAME slot.h's comment has
# them swapped).  B is GND on a G7000 (Boris) but an input on the Videopac+ G7400 (MAME: the 8245's
# graphics show everywhere while it is low) -- here a 10k pull-down and 1k from GP28.
EDGE = {'1': ('T0', 'T0'), '10': ('CA10', 'A10'), '11': ('CP14', 'P14'), '12': ('CP11', 'P11'),
        '13': ('CP10', 'P10'), '14': ('CA11', 'A11'), '15': ('CA9', 'A9'),
        'A': ('WR_N', '~{WR}'), 'B': ('VPB', 'B'), 'C': ('GND', 'GND'), 'D': ('CONS_5V', '+5V'),
        'E': ('EXTRAM', 'E'), 'F': ('PSEN_N', '~{PSEN}'), 'G': ('CA0', 'A0'), 'H': ('CA1', 'A1'),
        'J': ('CA2', 'A2'), 'K': ('CA3', 'A3'), 'L': ('CA4', 'A4'), 'M': ('CA5', 'A5'),
        'N': ('CA7', 'A7'), 'P': ('CA6', 'A6'), 'R': ('CA8', 'A8')}
EDGE.update({str(2 + i): ('CD%d' % i, 'DB%d' % i) for i in range(8)})      # 2 DB0 ... 9 DB7
assert sorted(EDGE) == sorted([str(i) for i in range(1, 16)] + list('ABCDEFGHJKLMNPR'))

# ---- common parts: footprint, (MPN, LCSC) ----------------------------------
FP = lambda n: '%s:%s' % (LIB, n)
R0603 = FP('R_0603_1608Metric')
R0402 = FP('RPI_R0402')
C0603 = FP('C_0603_1608Metric')
C0805 = FP('C_0805_2012Metric')
RES = {'27R': ('0603WAF270JT5E', 'C25190'), '330R': ('0603WAF3300T5E', 'C23138'),
       '680R': ('0603WAF6800T5E', 'C23228'), '1k': ('0603WAF1001T5E', 'C21190'),
       '5.1k': ('0603WAF5101T5E', 'C23186'), '10k': ('0603WAF1002T5E', 'C25804'),
       '15k': ('0603WAF1502T5E', 'C22809'), '22k': ('0603WAF2202T5E', 'C31850'),
       '33k': ('0603WAF3302T5E', 'C4216'), '47k': ('0603WAF4702T5E', 'C25819')}
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

# MPN -> manufacturer (names from LCSC's / JLCPCB's pages)
MFR = {'RP2354B': 'Raspberry Pi', 'CC0603KRX7R9BB104': 'YAGEO', 'CL10A106KP8NNNC': 'Samsung Electro-Mechanics',
       'CL10A475KO8NNNC': 'Samsung Electro-Mechanics', 'CL10C150JB8NNNC': 'Samsung Electro-Mechanics',
       'CL10A105KB8NNNC': 'Samsung Electro-Mechanics', 'CL21A226MAQNNNE': 'Samsung Electro-Mechanics',
       'CL05B104KO5NNNC': 'Samsung Electro-Mechanics', 'CL05A475MP5NRNC': 'Samsung Electro-Mechanics',
       'AOTA-B201610S3R3-101-T': 'Abracon', 'ABM8-272-T3': 'Abracon', 'TS-1187A-B-A-B': 'XKB Connection',
       'KT-0603R': 'Hubei KENTO Elec', 'TYPE-C-31-M-12': 'Korean Hroparts Elec',
       'AP2112K-3.3TRG1': 'Diodes Incorporated', 'AP63203WU-7': 'Diodes Incorporated',
       'ESP32-S3-WROOM-1-N16R8': 'Espressif', 'TF-015': 'SOFNG', 'WS2812B-2020-V6': 'Worldsemi',
       '4D03WGJ0103T5E': 'UNI-ROYAL', 'CP2102N-A02-GQFN28R': 'Silicon Labs', 'UMH3N': 'Jiangsu Changjing (JSCJ)',
       'USBLC6-2SC6': 'STMicroelectronics', 'BAT54C,215': 'Nexperia', 'TPS2116DRLR': 'Texas Instruments',
       'SWPA4030S6R8MT': 'Sunlord'}
for _v in list(RES.values()) + list(RES0402.values()):
    MFR.setdefault(_v[0], 'UNI-ROYAL')


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
    drawn on its line: nets[0..3] on pins 1-4, common on 5-8."""
    mpn, lcsc = RPACK[value]
    pins = {i + 1: n for i, n in enumerate(nets)}
    pins.update({8 - i: common for i in range(4)})
    return add('RN', 'Device:R_Pack04_Split', value, FP('R_Array_Convex_4x0603'), pins, mpn=mpn, lcsc=lcsc,
               desc=desc, **k)


def SW(value, net, desc, **k):
    # XKB TS-1187A-B-A-B (JLCPCB basic C318884), as FujiNet-StudioII / 5200 / 7800 / SMS Rev0
    return add('SW', 'Switch:SW_Push', value, FP('SW_SPST_TS-1187A'), {1: net, 2: 'GND'},
               mpn='TS-1187A-B-A-B', lcsc='C318884', desc=desc, **k)


def TP(net, label, desc='test pad', **k):
    return add('TP', 'Connector:TestPoint', label, FP('TestPoint_Pad_D1.5mm'), {1: net},
               desc=desc, bom=False, **k)


# =========================================================================
sheet('cart-bus')
add('J', '%s:Videopac_Cart_Edge_30' % LIB, 'Videopac_Cart_Edge_30', FP('Videopac_Cart_Edge_30'),
    {k: v[0] for k, v in EDGE.items()}, desc='Odyssey 2 / Videopac cartridge edge, 2x15 gold fingers, 3.9286 mm '
    'pitch; 1-15 on the parts face, A-R behind them', bom=False, key='J_EDGE')
# -- the console's bus into the RP: every line through 330R.  It limits the current into a 5 V-tolerant
# pad while IOVDD is still rising, a back-drive into a console that is off, and the overlap while the
# firmware lets go of D0-D7 after /PSEN rises (no buffer: the 8048's ~2.8 us machine cycle leaves
# room; 330R x ~10 pF of pad and trace is 3 ns).  Pin B is driven through 1k (a console that grounds
# it sees 3.3 mA) and pulled down by 10k, so it reads low (normal graphics) unless the firmware
# raises it.
for cn, rn, g, rv in BUS:
    R(rv, cn, rn, desc='%s series (GPIO%d)' % (cn, g), key='R_' + rn[3:])
R('10k', 'VPB', 'GND', desc='pin B pull-down: low = the 8245 shows everywhere on a Videopac+', key='R_VPBPD')
# -- the RP2354B (two units: GPIO here, the core on rp-core).  Every RP supply pin on +3V3_RP, the LDO
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
           mpn='RP2354B', lcsc='C39843328', desc='RP2350B + 2MB flash in package; serves the Odyssey 2 cart bus',
           key='U_RP', ds='https://datasheets.raspberrypi.com/rp2350/rp2350-datasheet.pdf')
# drawn in two units: A = the 48 GPIOs on the cart-bus sheet, B = supplies, core regulator,
# crystal, RUN, SWD, USB and QSPI on rp-core (gen_sch.rp_split_symbol)
U_RP.unit_sheets = {1: 'cart-bus', 2: 'rp-core'}
U_RP.pin_unit = {str(pad): 1 if pad in RP_GPIO_PIN.values() else 2 for pad in rp}
# activity LED on GP25 (picopac_cart.c LED_PIN); red, so a 3.3 V pin lights it (~2 mA)
R('680R', 'RP_LED', 'RP_LED_A', desc='LED series (~2 mA)', key='R_LED')
add('D', 'Device:LED', 'red', FP('LED_0603_1608Metric'), {1: 'GND', 2: 'RP_LED_A'},
    mpn='KT-0603R', lcsc='C2286', desc='RP activity LED (GP25)', key='D_LED')
# console 5 V sense (GP40, ADC0, not 5 V tolerant): 10k / 15k = 0.6 x CONS_5V, 3.0 V at 5.0 V, 3.15 V
# at 5.25 V; 6 kOhm source, under RP2350-E9's 8.2 kOhm (Astrocade Rev0); 100 nF ~0.6 ms filter.  It
# is taken at the edge, ahead of the mux: a cart on USB in a console that is off reads 0.
R('10k', 'CONS_5V', 'VSENSE', desc='console 5V sense divider', key='R_VSH')
R('15k', 'VSENSE', 'GND', desc='console 5V sense divider (0.6 x CONS_5V)', key='R_VSL')
C('100nF', 'VSENSE', desc='console 5V sense filter', key='C_VS')
TP('SELFTEST', 'SELFTEST', desc='test pad: GP29, a self-test trigger for bring-up', key='TP_SELFTEST')
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
# neither chip's reset drives the other's.  The edge has no reset line: RESET is the way back to the
# FujiNet's CONFIG screen.
SW('RESET', 'RST_BTN', 'cart RESET: RP RUN + S3 EN through the BAT54C', key='SW_RESET')
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
    mpn='ESP32-S3-WROOM-1-N16R8', lcsc='C2913202', desc='FujiNet core (fujiversal-o2)', key='U_S3')
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
# it runs on +5V (the mux's output) and takes the S3's 3.3 V data directly
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
# +5V (the RP's LDO, the S3's buck, the WS2812) is the TPS2116 power mux's output:
#   VIN1  USB VBUS -- the priority input: MODE on VIN1, PR1 from a 33k / 10k divider, so VBUS above
#         VREF x 4.3 (3.96-4.64 V) runs the cart and the console's supply delivers nothing
#   VIN2  CONS_5V, edge pin D, the console's 5 V (its regulator and spare current are not published:
#         README "Power") -- whenever VBUS is absent
# 37-60 mOhm either way; reverse current blocking: neither source can back-feed the other, so the
# cart on USB never powers a console that is off.  ST (open drain, low on VIN2) is not used.
add('U', 'Power_Management:TPS2116DRL', 'TPS2116', FP('SOT-583-8'),
    {1: 'GND', 2: '+5V', 3: 'VBUS', 4: 'VBUS_PR', 5: 'VBUS', 6: 'CONS_5V', 7: '+5V', 8: NC},
    mpn='TPS2116DRLR', lcsc='C3235557', desc='power mux: VBUS first, console 5V second', key='U_MUX')
R('33k', 'VBUS', 'VBUS_PR', desc='mux priority threshold (VBUS > 4.3 V)', key='R_PRH')
R('10k', 'VBUS_PR', 'GND', desc='mux priority threshold', key='R_PRL')
C('1uF', 'VBUS', desc='mux VIN1 (datasheet: 1 uF at the input)', key='C_MUXV1')
C('10uF', 'CONS_5V', desc='edge 5V bulk, mux VIN2', key='C_CONS')
C('100nF', 'CONS_5V', desc='edge 5V HF bypass', key='C_CONSHF')
C('22uF', '+5V', desc='+5V bulk (mux output; buck input)', key='C_5VBULK')
# the S3 side's 3.3 V: AP63203, 2 A synchronous buck; WiFi bursts ~400 mA
C('22uF', '+5V', desc='buck input', key='C_BIN')
C('100nF', '+5V', desc='buck input HF', key='C_BINHF')
add('U', 'Regulator_Switching:AP63203WU', 'AP63203WU', FP('TSOT-23-6'),
    {1: '+3V3', 2: '+5V', 3: '+5V', 4: 'GND', 5: 'BUCK_SW', 6: 'BUCK_BST'},
    mpn='AP63203WU-7', lcsc='C780769', desc='3.3V 2A buck (S3, SD, CP2102N)', key='U_BUCK')
C('100nF', 'BUCK_SW', 'BUCK_BST', desc='bootstrap', key='C_BST')
add('L', 'Device:L', '6.8uH', FP('L_Sunlord_SWPA4030S'), {1: 'BUCK_SW', 2: '+3V3'},
    mpn='SWPA4030S6R8MT', lcsc='C62684', desc='buck inductor', key='L_BUCK')
C('22uF', '+3V3', desc='buck output', key='C_BOUT1')
C('22uF', '+3V3', desc='buck output', key='C_BOUT2')
# RP rail: a fast LDO (AP2112K: ~20 us start-up) straight off +5V, so IOVDD tracks the console rail
# as it rises and the FT pads are never unpowered with 5 V on them (the buck waits out UVLO + 4 ms
# soft start: Astrocade Rev0's lesson).
add('U', 'Regulator_Linear:AP2112K-3.3', 'AP2112K-3.3', FP('SOT-23-5'),
    {1: '+5V', 2: 'GND', 3: '+5V', 4: NC, 5: RP_RAIL},
    mpn='AP2112K-3.3TRG1', lcsc='C51118', desc='RP2354B 3.3V LDO (IOVDD, VREG_VIN, VREG_AVDD), 600mA, fast start',
    key='U_LDO')
C('1uF', '+5V', desc='LDO input', key='C_LDOIN')
C('1uF', RP_RAIL, desc='LDO output', key='C_LDOOUT')
TP('CONS_5V', 'CONS_5V', desc='bring-up pad: console 5V (edge pin D)', key='TP_CONS5V')
TP('VBUS', 'VBUS', desc='bring-up pad: USB VBUS', key='TP_VBUS')
TP('+5V', '+5V', desc='bring-up pad: +5V (mux output)', key='TP_5V')
TP(RP_RAIL, '+3V3_RP', desc='bring-up pad: +3V3_RP (RP LDO)', key='TP_3V3')
TP('+3V3', '+3V3', desc='bring-up pad: +3V3 (buck: S3 side)', key='TP_3V3S3')

# PWR_FLAGs: nets whose drivers are passive pins (+5V is the mux's VOUT, +3V3_RP the LDO's)
PWR_FLAG_NETS = ['GND', 'CONS_5V', 'VBUS', '+3V3', 'DVDD', 'VREG_AVDD']
# nets drawn as power symbols (global, never prefixed)
RAIL_NETS = ['GND', 'CONS_5V', 'VBUS', '+5V', '+3V3', RP_RAIL, 'DVDD']

# ---- reference assignment (stable: declaration order) ---------------------
_count = {}
for p in PARTS:
    _count[p.prefix] = _count.get(p.prefix, 0) + 1
    p.ref = '%s%d' % (p.prefix, _count[p.prefix])

BY_REF = {p.ref: p for p in PARTS}
KEY = {p.key: p.ref for p in PARTS if p.key}
BY_KEY = {p.key: p for p in PARTS if p.key}
assert len(KEY) == len([p for p in PARTS if p.key]), 'duplicate part key'


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
