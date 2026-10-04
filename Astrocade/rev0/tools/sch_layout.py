"""FujiNet-Astrocade Rev0 schematic drawing: where every symbol sits and which
pins are drawn joined.  design.py stays the only source of parts and nets;
gen_sch.py refuses any wire that would join two different nets.

Per sheet:
  place    REF -> (x, y[, rot[, mirror]])   symbol origin, mm, 1.27 grid
           or {'units': {1: (x, y), 2: (x, y)}, 'rot': r} for multi-unit parts
  wires    polylines; an entry is 'REF.pin' (its tip), (x, y), or ('REF.pin', dx, dy);
           '|' makes the next corner vertical-first.  Geometry decides what is
           connected: a wire end on another wire or on a pin tip joins them.
  anchor   'REF.pin' -> direction of the rail symbol / net label placed at that
           pin, or 'none'.  Every wired group (or lone pin) is named exactly once:
           at its anchor pin, else at its first pin.
  stub     'REF.pin' -> (length, direction): a lead before that symbol/label
  labels   (net, point, direction): a name on a wire point
  rails    (net, point, direction): a rail symbol on a wire point
  flags    (net, x, y): a free-standing rail symbol carrying a PWR_FLAG
  pwr_flags points that get a PWR_FLAG
  fields   REF -> ((dx, dy, justify), (dx, dy, justify)): Reference / Value
           positions relative to the symbol origin
  text     (x, y, text[, size])
"""

# ---------------------------------------------------------------------------
# power: console 5V / USB VBUS diode-OR, 3.3 V buck, RP 3.3 V LDO
POWER = {
    'paper': 'A4', 'shift': (-25.4, -5.08),
    'place': {
        'C28': (45.72, 64.77),
        'D7': (60.96, 60.96, 180), 'D8': (60.96, 76.2, 180),
        'C29': (78.74, 64.77), 'C30': (88.9, 64.77), 'C31': (99.06, 64.77), 'C32': (109.22, 64.77),
        'TP8': (119.38, 60.96),
        'U5': (139.7, 66.04),
        'C33': (166.37, 66.04, 270), 'L2': (180.34, 63.5, 90),
        'C34': (193.04, 67.31), 'C35': (203.2, 67.31), 'TP9': (213.36, 63.5),
        'C36': (121.92, 102.87), 'U6': (139.7, 101.6), 'C37': (157.48, 102.87), 'TP10': (167.64, 99.06),
    },
    'wires': [
        ['C28.1', 'D7.2'],
        ['D7.1', 'D8.1'],
        ['D7.1', 'C29.1', 'C30.1', 'C31.1', 'C32.1', 'TP8.1', (129.54, 60.96), 'U5.3'],
        ['U5.3', 'U5.2'],
        ['C29.2', 'C30.2', 'C31.2', 'C32.2'],
        ['U5.6', 'C33.2'],
        ['U5.5', 'L2.1'],
        ['C33.1', (170.18, 63.5)],
        ['L2.2', 'C34.1', 'C35.1', 'TP9.1'],
        ['U5.1', (151.13, 68.58), (151.13, 76.2), (187.96, 76.2), (187.96, 63.5)],
        ['C34.2', 'C35.2'],
        ['C36.1', 'U6.1'], ['U6.1', 'U6.3'],
        ['U6.5', 'C37.1', 'TP10.1'],
    ],
    'anchor': {'C28.1': 'U', 'C32.1': 'U', 'C29.2': 'D', 'C35.1': 'U', 'C34.2': 'D', 'C36.1': 'U',
               'C37.1': 'U', 'D8.2': 'U'},
    'stub': {'D8.2': (5.08, 'L')},
    'labels': [('BUCK_SW', (151.13, 63.5), 'R'), ('BUCK_BST', (151.13, 66.04), 'R')],
    'flags': [('GND', 40.64, 139.7), ('CONS_5V', 58.42, 139.7), ('VBUS', 76.2, 139.7),
              ('+5V', 93.98, 139.7), ('+3V3', 111.76, 139.7)],
    'text': [
        (40.64, 30.48, 'POWER', 3.0),
        (40.64, 38.1, 'Console +5V (edge land 25, CONS_5V) and USB VBUS are diode-ORed into +5V: neither source can\n'
                      'back-feed the other (an unpowered console, or the USB host).  SS34 VF ~0.35 V at the cart\'s ~0.4 A,\n'
                      'so +5V is 4.4-4.9 V; there is no 5 V logic on this board.', 1.524),
        (40.64, 86.36, 'AP63203 3.3 V / 2 A buck: ESP32-S3 (WiFi bursts ~400 mA), CP2102N, microSD.  4 ms soft-start (tSS).', 1.524),
        (40.64, 116.84, 'AP2112K-3.3 LDO -> +3V3_RP: the WHOLE RP2354A (IOVDD, QSPI/USB/ADC supplies, VREG_VIN + VREG_AVDD).\n'
                        'In dropout it follows +5V as the console rail rises (1 V/ms into 21 uF = 21 mA, under the 50 mA\n'
                        'fold-back limit), so the 5 V-tolerant pads are never unpowered with the console bus driving them\n'
                        '(RP2350 datasheet: FT pads tolerate 5.5 V "provided IOVDD is powered to 3.3 V").\n'
                        'The buck instead waits for UVLO, then soft-starts over 4 ms.  VREG_VIN and VREG_AVDD rise together (p.402).', 1.524),
        (40.64, 152.4, 'PWR_FLAGs: the rails above are driven through diodes / inductors (passive pins).', 1.27),
    ],
}

# ---------------------------------------------------------------------------
# USB-C, CP2102N bridge, esptool auto-program
UART = {
    'paper': 'A4', 'shift': (-25.4, -5.08),
    'place': {
        'J3': (50.8, 99.06),
        'R17': (76.2, 88.9, 90), 'R18': (86.36, 91.44, 90),
        'D6': (81.28, 74.93, 270), 'C24': (101.6, 74.93), 'C25': (111.76, 74.93),
        'R19': (127.0, 74.93), 'R20': (127.0, 82.55),
        'D5': (78.74, 109.22, 270), 'D4': (96.52, 109.22, 270),
        'U3': (170.18, 111.76),
        'R21': (144.78, 80.01),
        'C26': (187.96, 72.39), 'C27': (198.12, 72.39),
        'U4': {'units': {1: (215.9, 99.06), 2: (215.9, 119.38)}, 'rot': 0},
    },
    'wires': [
        ['J3.A4', (71.12, 83.82), (71.12, 71.12), 'D6.1', 'C24.1', 'C25.1', 'R19.1'],
        ['J3.A5', 'R17.1'], ['J3.B5', 'R18.1'], ['R17.2', (93.98, 88.9), (93.98, 91.44), 'R18.2'],
        ['J3.A7', 'J3.B7'], ['J3.A6', 'J3.B6'],
        ['J3.B7', 'U3.5'], ['J3.A6', 'U3.4'],
        ['D5.1', (78.74, 99.06)], ['D4.1', (96.52, 101.6)],
        ['U3.7', 'U3.6'],
        ['R21.2', 'U3.9'],
    ],
    'rails': [('GND', (93.98, 91.44), 'D')],
    'anchor': {'C24.1': 'U', 'J3.B7': 'none', 'J3.A6': 'none', 'R19.2': 'L',
               'U3.6': 'U', 'U3.9': 'none', 'U3.23': 'D',
               'U4.2': 'L', 'U4.1': 'D', 'U4.5': 'L', 'U4.4': 'D', 'U4.6': 'R', 'U4.3': 'R'},
    'stub': {'U4.6': (5.08, 'U'), 'U4.3': (5.08, 'U'), 'U3.24': (12.7, 'R'), 'U3.28': (12.7, 'R'), 'U3.23': (7.62, 'R')},
    'labels': [('UBRG_DM', (104.14, 99.06), 'R'), ('UBRG_DP', (104.14, 101.6), 'R'),
               ('CP_RST', (146.05, 83.82), 'R')],
    'fields': {'U3': ((-10.16, 38.1, 'left'), (-10.16, 40.64, 'left')),
               'U4': ((5.08, -1.27, 'left'), (5.08, 1.27, 'left')),
               'J3': ((-10.16, -24.13, 'left'), (-10.16, -21.59, 'left'))},
    'text': [
        (40.64, 30.48, 'USB-C: POWER + ESP32-S3 PROGRAMMING BRIDGE', 3.0),
        (40.64, 38.1, 'UFP (5.1k Rd on CC1/CC2).  ESD5Z5.0 on D+, D-, VBUS at the connector.  CP2102N is self-powered from +3V3\n'
                      '(VDD = VREGIN, regulator bypassed); its VBUS pin only senses the cable through 22k/47k (3.4 V at 5 V).\n'
                      'UMH3N = the ESP32-S3-DevKitC-1 auto-program pair: esptool drives DTR/RTS to pulse EN and hold IO0.', 1.524),
    ],
}

# ---------------------------------------------------------------------------
# ESP32-S3 module, EN/BOOT/RESET, microSD, status LED
ESP = {
    'paper': 'A4',
    'place': {
        'U2': (139.7, 111.76),
        'C19': (165.1, 76.2), 'C20': (175.26, 76.2),
        'D2': (35.56, 66.04), 'SW4': (35.56, 76.2, 270),
        'SW2': (53.34, 71.12, 270), 'C21': (68.58, 69.85), 'R14': (78.74, 62.23),
        'SW3': (53.34, 99.06, 270),
        'J2': (254.0, 116.84),
        'RN1': (210.82, 93.98), 'R15': (222.25, 93.98), 'C22': (232.41, 93.98),
        'R16': (190.5, 147.32, 90), 'D3': (215.9, 147.32), 'C23': (233.68, 147.32),
    },
    'wires': [
        ['D2.2', 'SW2.1', 'C21.1', 'R14.2', (91.44, 66.04)],
        ['SW3.1', (63.5, 93.98)],
        ['RN1.8', 'RN1.7', 'RN1.6', 'RN1.5'],
        ['J2.10', 'J2.11', 'J2.12', 'J2.13'],
        ['R16.2', 'D3.3'],
    ],
    'anchor': {'D2.2': 'none', 'SW3.1': 'none', 'D2.3': 'L', 'RN1.8': 'U', 'J2.10': 'none',
               'R16.2': 'none', 'J2.11': 'D', 'J2.4': 'U', 'J2.6': 'D'},
    'stub': {'J2.4': (12.7, 'L'), 'J2.6': (12.7, 'L')},
    'labels': [('S3_EN', (91.44, 66.04), 'R'), ('S3_IO0', (63.5, 93.98), 'R'),
               ('WS_DIN', (195.58, 147.32), 'R')],
    'fields': {'U2': ((-12.7, 33.02, 'left'), (-12.7, 35.56, 'left')),
               'J2': ((-8.89, -17.78, 'left'), (-8.89, -15.24, 'left')),
               'D2': ((-3.81, -3.81, 'left'), (3.81, -3.81, 'left')),
               'D3': ((7.62, -6.35, 'left'), (7.62, -3.81, 'left')),
               'RN1': ((-7.62, -1.27, 'right'), (-7.62, 1.27, 'right'))},
    'text': [
        (15.24, 17.78, 'ESP32-S3 FUJINET CORE', 3.0),
        (15.24, 25.4, 'ESP32-S3-WROOM-1-N16R8 runs fujinet-firmware (build fujiversal-astrocade, include/pinmap/fujiversal-astrocade.h).\n'
                      'It is the USB HOST of the RP2354A (IO19/IO20, native USB) and re-flashes it over PICOBOOT: IO4 -> RP RUN,\n'
                      'IO5 -> RP QSPI_SS (1k series each, on the RP sheet), driven LOW to assert, inputs when idle.\n'
                      'IO26-IO37 belong to the module\'s flash/PSRAM (N16R8) and stay unconnected.', 1.524),
        (15.24, 48.26, 'RESET (top face) pulls RP RUN and S3 EN low through a common-cathode BAT54C:\n'
                       'neither reset line can drive the other.  EN: 10k / 1 uF power-on delay.', 1.27),
        (15.24, 88.9, 'S3 BOOT (IO0)', 1.27),
        (198.12, 73.66, 'microSD (SPI).  CD closes to the shell with a card in:\nSD_CD reads LOW = card present.', 1.27),
        (167.64, 129.54, 'Status LED: WS2812B-2020 on +5V (datasheet VDD 3.7-5.3 V;\nVIH 2.7 V takes the S3\'s 3.3 V data without a level shifter).', 1.27),
    ],
}

# ---------------------------------------------------------------------------
# cartridge edge + RP2354A
_U1 = (203.2, 152.4)
CART = {
    'place': {
        'J1': (76.2, 144.78, 0, 'y'),
        'U1': (_U1[0], _U1[1], 0, 'y'),
        # decoupling row
        'C1': (76.2, 68.58), 'C2': (88.9, 68.58), 'C3': (101.6, 68.58), 'C4': (114.3, 68.58),
        'C5': (127.0, 68.58), 'C6': (139.7, 68.58), 'C7': (152.4, 68.58), 'C8': (165.1, 68.58),
        'C9': (177.8, 68.58), 'C10': (190.5, 68.58), 'C11': (203.2, 68.58),
        'C12': (228.6, 68.58), 'C13': (241.3, 68.58), 'C14': (254.0, 68.58), 'C15': (266.7, 68.58),
        # core regulator corner (top pins, mirrored symbol)
        'R1': (220.98, 102.87), 'C16': (238.76, 110.49), 'L1': (194.31, 93.98, 90),
        # crystal
        'Y1': (248.92, 171.45, 270), 'C17': (269.24, 171.45), 'R2': (238.76, 177.8, 90), 'C18': (264.16, 181.61),
        # SWD
        'TP1': (238.76, 185.42), 'TP2': (251.46, 187.96),
        # bus support in the gap
        'R8': (157.48, 143.51),
        'R9': (139.7, 175.26), 'R10': (139.7, 182.88),
        'TP4': (165.1, 170.18), 'TP5': (165.1, 185.42),
        'R13': (127.0, 208.28, 90), 'D1': (148.59, 208.28, 180),
        # USB link
        'R12': (304.8, 116.84, 270), 'R11': (304.8, 124.46, 270),
        # RUN
        'R3': (299.72, 143.51), 'TP6': (307.34, 147.32), 'R6': (317.5, 147.32, 270),
        # BOOTSEL / QSPI_SS
        'R4': (299.72, 168.91), 'TP7': (307.34, 172.72), 'R7': (317.5, 172.72, 270),
        'R5': (294.64, 176.53), 'SW1': (294.64, 187.96, 270),
        'TP3': (213.36, 210.82),
    },
    'wires': [
        # +3V3_RP supply pins share one bar
        ['U1.53', '|', (215.9, 101.6), (200.66, 101.6), 'U1.49'],
        ['U1.44', (213.36, 101.6)], ['U1.54', (208.28, 101.6)], ['U1.1', (205.74, 101.6)],
        # VREG_AVDD RC
        ['U1.46', 'C16.1'],
        # core SMPS: LX -> L1 -> DVDD, FB on DVDD
        ['U1.48', 'L1.2'], ['L1.1', 'U1.6'], ['U1.50', (195.58, 99.06), (190.5, 99.06)],
        ['U1.47', 'U1.61'],
        # crystal
        ['U1.21', 'Y1.1', 'C17.1'],
        ['U1.22', 'R2.1'],
        ['R2.2', 'C18.1'], ['Y1.3', (248.92, 177.8)],
        # SWD pads
        ['U1.24', 'TP1.1'], ['U1.25', 'TP2.1'],
        # bus support
        [(149.86, 147.32), 'R8.2', 'U1.17'],
        ['U1.34', 'TP4.1'], ['U1.41', 'TP5.1'],
        ['R13.2', 'D1.2'],
        # RUN cluster
        [(292.1, 147.32), 'R3.2', 'TP6.1', 'R6.2'],
        # BOOTSEL cluster
        [(287.02, 172.72), 'R5.1', 'R4.2', 'TP7.1', 'R7.2'], ['R5.2', 'SW1.1'],
    ],
    'anchor': {
        'U1.53': 'none', 'U1.46': 'none', 'L1.1': 'U', 'U1.48': 'none', 'U1.47': 'none', 'U1.61': 'D',
        'U1.21': 'none', 'U1.22': 'none', 'R2.2': 'none', 'U1.24': 'none', 'U1.25': 'none',
        'TP4.1': 'L', 'TP5.1': 'L', 'R13.2': 'none',
        'R9.2': 'L', 'D1.1': 'D', 'Y1.2': 'D', 'SW1.1': 'R',
        'R3.2': 'none', 'R5.1': 'none',
        'J1.1': 'D', 'J1.13': 'D', 'J1.26': 'D', 'J1.25': 'U',
    },
    'stub': {'D1.1': (2.54, 'R'), 'J1.1': (10.16, 'R'), 'J1.13': (10.16, 'R'), 'J1.26': (10.16, 'R'),
             'J1.25': (10.16, 'R')},
    'rails': [('+3V3_RP', (208.28, 101.6), 'U')],
    'pwr_flags': [(238.76, 106.68)],
    'flags': [('DVDD', 167.64, 96.52)],
    'labels': [('VREG_AVDD', (223.52, 106.68), 'R'), ('CCS_N', (149.86, 147.32), 'L'), ('RP_LX', (198.12, 104.14), 'U'), ('XIN', (231.14, 167.64), 'R'),
               ('XOUT', (229.87, 177.8), 'R'), ('XOUT_Y', (250.19, 177.8), 'R'),
               ('SWCLK', (231.14, 185.42), 'R'), ('SWDIO', (231.14, 187.96), 'R'),
               ('RP_LED_A', (132.08, 208.28), 'R'),
               ('RUN', (292.1, 147.32), 'L'), ('QSPI_SS', (287.02, 172.72), 'L')],
    'fields': {'U1': ((10.16, 48.26, 'left'), (10.16, 50.8, 'left')),
               'Y1': ((3.81, -1.27, 'left'), (3.81, 1.27, 'left')),
               'R5': ((-1.27, -1.27, 'right'), (-1.27, 1.27, 'right')),
               'L1': ((5.08, -1.27, 'left'), (5.08, 1.27, 'left')),
               'R1': ((-1.27, -1.27, 'right'), (-1.27, 1.27, 'right')),
               'C18': ((-2.54, -1.27, 'right'), (-2.54, 1.27, 'right')),
               'J1': ((-7.62, -38.1, 'left'), (-7.62, -35.56, 'left'))},
    'text': [
        (40.64, 30.48, 'CARTRIDGE PORT + RP2354A BUS SERVER', 3.0),
        (40.64, 38.1, 'Bally Astrocade cassette port, 26 contacts on the PCB UNDERSIDE (the console blade presses up), Tilton 1-26.\n'
                      'The RP2354A (RP2350A + 2 MB flash in package) serves the 8K cart window straight off the 5 V bus: A0-A12 = GP0-12,\n'
                      '/CCS = GP13, D0-D7 = GP14-21 (astrocade_cart.h).  No buffers: the RP2350 fault-tolerant pads take 5.5 V while\n'
                      'IOVDD is up, and +3V3_RP (power sheet, LDO) follows the console rail as it rises.  The firmware drives D0-D7\n'
                      'only while /CCS is low AND VSENSE is high, so a USB-powered cart never drives a dead console.', 1.524),
        (76.2, 80.01, 'Decoupling: one 100 nF at each IOVDD / QSPI_IOVDD / USB_OTP_VDD / ADC_AVDD pin, 4.7 uF at VREG_VIN, 10 uF bulk;\n'
                      'DVDD 3 x 100 nF + 4.7 uF at the core regulator output.  Regulator corner per the Raspberry Pi RP2350A minimal design.', 1.27),
        (106.68, 193.04, 'VSENSE: console +5V x 0.6 (3.0 V; 3.15 V at 5.25 V).\nGP26 is an ADC pad, not 5 V tolerant.', 1.27),
        (106.68, 218.44, 'Activity LED (GP25)', 1.27),
        (279.4, 109.22, 'RP <-> S3 native USB (S3 = host)', 1.27),
        (279.4, 129.54, 'RUN: pulled up; S3 IO4 (1k) and the RESET\nbutton (S3 sheet) pull it low', 1.27),
        (279.4, 154.94, 'BOOTSEL: QSPI_SS low through reset = USB boot;\nS3 IO5 (1k) or SW1 (pinhole)', 1.27),
        (236.22, 200.66, 'SWD + test pads', 1.27),
    ],
}

SHEETS = {'power': POWER, 'usb-uart': UART, 'esp32s3-sd': ESP, 'cart-rp2354a': CART}

# hierarchical label shapes, per sheet
HIER_SHAPE = {
    ('usb-uart', 'S3_TXD'): 'input', ('usb-uart', 'S3_RXD'): 'output',
    ('usb-uart', 'S3_EN'): 'output', ('usb-uart', 'S3_IO0'): 'output',
    ('esp32s3-sd', 'S3_TXD'): 'output', ('esp32s3-sd', 'S3_RXD'): 'input',
    ('esp32s3-sd', 'S3_EN'): 'input', ('esp32s3-sd', 'S3_IO0'): 'input',
    ('esp32s3-sd', 'RUN_CTL'): 'output', ('esp32s3-sd', 'BOOTSEL_CTL'): 'output',
    ('esp32s3-sd', 'RUN'): 'output',
    ('cart-rp2354a', 'RUN_CTL'): 'input', ('cart-rp2354a', 'BOOTSEL_CTL'): 'input',
    ('cart-rp2354a', 'RUN'): 'input',
}

# root: block diagram, signal flow left to right
_P = [83.82, 88.9, 93.98, 99.06, 104.14]
ROOT = {
    # short sheet names: KiCad prefixes every net local to a sheet with its path (/cart/CA0)
    'names': {'cart-rp2354a': 'cart', 'esp32s3-sd': 'esp32', 'usb-uart': 'usb', 'power': 'power'},
    'blocks': {   # stem -> (x, y, w, h)
        'usb-uart': (45.72, 76.2, 63.5, 38.1),
        'esp32s3-sd': (165.1, 76.2, 63.5, 38.1),
        'cart-rp2354a': (284.48, 76.2, 81.28, 38.1),
        'power': (45.72, 157.48, 63.5, 25.4),
    },
    'pins': {
        'usb-uart': {'R': [('S3_EN', _P[0]), ('S3_IO0', _P[1]), ('S3_RXD', _P[2]), ('S3_TXD', _P[3])]},
        'esp32s3-sd': {'L': [('S3_EN', _P[0]), ('S3_IO0', _P[1]), ('S3_RXD', _P[2]), ('S3_TXD', _P[3])],
                       'R': [('USB_DP', _P[0]), ('USB_DM', _P[1]), ('RUN_CTL', _P[2]), ('BOOTSEL_CTL', _P[3]),
                             ('RUN', _P[4])]},
        'cart-rp2354a': {'L': [('USB_DP', _P[0]), ('USB_DM', _P[1]), ('RUN_CTL', _P[2]), ('BOOTSEL_CTL', _P[3]),
                               ('RUN', _P[4])]},
    },
    'wires': [('usb-uart', 'esp32s3-sd', n, []) for n in ('S3_EN', 'S3_IO0', 'S3_RXD', 'S3_TXD')] +
             [('esp32s3-sd', 'cart-rp2354a', n, []) for n in ('USB_DP', 'USB_DM', 'RUN_CTL', 'BOOTSEL_CTL', 'RUN')],
    'text': [
        (45.72, 30.48, 'FujiNet for the Bally Astrocade - Rev0', 4.0),
        (45.72, 40.64, 'One cassette-shell cartridge carrying both halves of the Astrocade FujiNet stack.  Signal flow left to right:\n'
                       'PC / power  ->  USB-C + CP2102N  ->  ESP32-S3 (FujiNet, WiFi, microSD)  ->  native USB  ->  RP2354A  ->  console bus.', 1.8),
        (45.72, 125.73, 'UART + auto-program: esptool resets the S3 into\nits ROM loader over DTR/RTS.', 1.27),
        (165.1, 125.73, 'USB host of the RP (CDC device, VID 0xCafe); embeds the RP\nfirmware and re-flashes it over PICOBOOT when it changes:\nIO4 pulses RUN while IO5 holds QSPI_SS low.', 1.27),
        (284.48, 125.73, 'Serves the 8K cart window and the FujiNet mailbox straight\noff the 5 V bus (5 V-tolerant pads, no level shifters).\nEdge: A0-A12, D0-D7, /CCS (pre-decoded enable), +5V, 3 x GND.\nThe console only ever reads the cart.', 1.27),
        (45.72, 190.5, 'Rails (power symbols, global):\n'
                       '  CONS_5V  console +5V, edge land 25\n'
                       '  VBUS     USB-C\n'
                       '  +5V      CONS_5V / VBUS diode-OR -> buck, LDO, WS2812\n'
                       '  +3V3     AP63203 buck -> ESP32-S3, CP2102N, microSD\n'
                       '  +3V3_RP  AP2112K LDO -> RP2354A (all supplies)\n'
                       '  DVDD     RP2350 on-chip core SMPS (1.1 V)', 1.27),
        (165.1, 157.48, 'Not verifiable in CAD (bring-up checklist, README):\n'
                        ' - console cold start: +3V3_RP vs CA*/CCS_N rise (scope)\n'
                        ' - /CCS-to-data timing against the Z80 read cycle\n'
                        ' - console 5 V headroom under WiFi bursts\n'
                        ' - blade reach vs the land escape holes (17.4 mm)', 1.27),
        (165.1, 210.82, 'License CERN-OHL-W-2.0.  Circuit blocks from FujiNet-INTV-Rev0 (PiNTY CARD) and the ESP32-S3-DevKitC-1;\n'
                        'RP2350 regulator corner from the Raspberry Pi RP2350A minimal design (MIT).', 1.27),
    ],
}
