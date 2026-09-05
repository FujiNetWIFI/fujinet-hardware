#!/usr/bin/env python3
"""Machine cross-check: FujiNet-Astrocade-Rev0 netlist vs the firmware pin
maps (fujinet-firmware pico/astrocade astrocade_cart.h, pinmap
fujiversal-astrocade.h) and the ballyalley 26-pin edge pinout.

Run after ANY schematic edit:  python3 tools/check_nets.py
Exports a fresh netlist via kicad-cli, then runs 151 checks.
"""
import re, sys


def extract_block(text, start_idx):
    """Return (block_text, end_idx) for the paren block starting at start_idx ('(')."""
    depth = 0; i = start_idx; n = len(text); in_str = False
    while i < n:
        c = text[i]
        if in_str:
            if c == '\\': i += 2; continue
            if c == '"': in_str = False
        else:
            if c == '"': in_str = True
            elif c == '(': depth += 1
            elif c == ')':
                depth -= 1
                if depth == 0: return text[start_idx:i+1], i+1
        i += 1
    raise ValueError("unbalanced")

def find_symbol_def(libtext, name):
    """Find top-level (symbol "name" ...) block in a .kicad_sym or lib_symbols body."""
    import re
    for m in re.finditer(r'\(symbol\s+"%s"' % re.escape(name), libtext):
        # ensure this is a definition start (not nested unit) by checking it parses
        blk, _ = extract_block(libtext, m.start())
        return blk
    return None

def parse_pins(symblock):
    """Return list of dicts: number, name, x, y, rot, length for all pins in a symbol block."""
    import re
    pins = []
    i = 0
    while True:
        j = symblock.find('(pin ', i)
        if j < 0: break
        blk, k = extract_block(symblock, j)
        at = re.search(r'\(at\s+(-?[\d.]+)\s+(-?[\d.]+)\s+(-?[\d.]+)\)', blk)
        ln = re.search(r'\(length\s+([\d.]+)\)', blk)
        nm = re.search(r'\(name\s+"([^"]*)"', blk)
        no = re.search(r'\(number\s+"([^"]*)"', blk)
        pins.append(dict(number=no.group(1), name=nm.group(1),
                         x=float(at.group(1)), y=float(at.group(2)),
                         rot=float(at.group(3)), length=float(ln.group(1))))
        i = k
    return pins


import os, subprocess, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
PRJ = os.path.dirname(HERE)
netf = os.path.join(tempfile.gettempdir(), "fujinet-astrocade-check.net")
subprocess.run(["kicad-cli", "sch", "export", "netlist", "--format", "kicadsexpr",
                "-o", netf, os.path.join(PRJ, "FujiNet-Astrocade-Rev0.kicad_sch")],
               check=True, capture_output=True)
NET = open(netf).read()

# parse nets -> set of (ref, pin)
nets = {}
i = 0
while True:
    j = NET.find('(net\n', i)
    if j < 0: break
    blk, i = extract_block(NET, j)
    name = re.search(r'\(name "([^"]*)"\)', blk).group(1)
    nodes = set()
    for m in re.finditer(r'\(node\s+\(ref "([^"]+)"\)\s+\(pin "([^"]+)"\)', blk):
        nodes.add((m.group(1), m.group(2)))
    nets[name] = nodes

def netof(ref, pin):
    for name, nodes in nets.items():
        if (ref, pin) in nodes: return name
    return None

ok = bad = 0
def chk(desc, cond):
    global ok, bad
    if cond: ok += 1
    else:
        bad += 1
        print("FAIL:", desc)

# --- RP2040 QFN-56 physical pin for GPIOn (from the official symbol used) ---
gpio_pin = {0:'2',1:'3',2:'4',3:'5',4:'6',5:'7',6:'8',7:'9',8:'11',9:'12',
            10:'13',11:'14',12:'15',13:'16',14:'17',15:'18',16:'27',17:'28',
            18:'29',19:'30',20:'31',21:'32',22:'34',23:'35',24:'36',25:'37',
            26:'38',27:'39',28:'40',29:'41'}

# astrocade_cart.h: GP0-12 = A0-12 (one contiguous mask), GP13 = /ENABLE,
# GP14-21 = D0-7, GP22 selftest, GP25 LED, GP26 5V sense, GP27 debug TX
for n in range(13):
    chk(f"U1 GPIO{n} on RP_A{n}", netof('U1', gpio_pin[n]) == f"RP_A{n}")
chk("U1 GPIO13 on RP_EN", netof('U1', gpio_pin[13]) == "RP_EN")
for n in range(8):
    chk(f"U1 GPIO{14+n} on RP_D{n}", netof('U1', gpio_pin[14+n]) == f"RP_D{n}")
chk("U1 GPIO22 SELFTEST", netof('U1', gpio_pin[22]) == "SELFTEST")
chk("U1 GPIO25 RP_LED",  netof('U1', gpio_pin[25]) == "RP_LED")
chk("U1 GPIO26 VSENSE",  netof('U1', gpio_pin[26]) == "VSENSE")
chk("U1 GPIO27 RP_DBG_TX", netof('U1', gpio_pin[27]) == "RP_DBG_TX")

# --- edge pinout (Tilton 1..26) ---
edge = {1:"GND",2:"CA7",3:"CA6",4:"CA5",5:"CA4",6:"CA3",7:"CA2",8:"CA1",
        9:"CA0",10:"CD0",11:"CD1",12:"CD2",13:"GND",14:"CD3",15:"CD4",
        16:"CD5",17:"CD6",18:"CD7",19:"CA11",20:"CA10",21:"CCS_N",22:"CA12",
        23:"CA9",24:"CA8",25:"+5V",26:"GND"}
for k, n in edge.items():
    chk(f"J1 pin {k} on {n}", netof('J1', str(k)) == n)

# --- level shifter continuity: every CA/CD/CCS reaches the right RP pin ---
# U8: B0..7 (18..11) = CA0..7 ; A0..7 (2..9) = RP_A0..7
for i2 in range(8):
    chk(f"U8 ch{i2} CA{i2}", netof('U8', str(18-i2)) == f"CA{i2}")
    chk(f"U8 ch{i2} RP_A{i2}", netof('U8', str(2+i2)) == f"RP_A{i2}")
# U9: B0..4=CA8..12, B5=CCS_N ; A0..4=RP_A8..12, A5=RP_EN
for i2 in range(5):
    chk(f"U9 ch{i2} CA{8+i2}", netof('U9', str(18-i2)) == f"CA{8+i2}")
    chk(f"U9 ch{i2} RP_A{8+i2}", netof('U9', str(2+i2)) == f"RP_A{8+i2}")
chk("U9 B5 CCS_N", netof('U9', '13') == "CCS_N")
chk("U9 A5 RP_EN", netof('U9', '7') == "RP_EN")
chk("U9 DIR=GND (B->A)", netof('U9', '1') == "GND")
chk("U8 DIR=GND (B->A)", netof('U8', '1') == "GND")
chk("U9 OE tied active", netof('U9', '19') == "GND")
chk("U8 OE tied active", netof('U8', '19') == "GND")
# U7 data: A=RP_D, B=CD, DIR=+3V3 (A->B), OE=/CCS
for i2 in range(8):
    chk(f"U7 ch{i2} RP_D{i2}", netof('U7', str(2+i2)) == f"RP_D{i2}")
    chk(f"U7 ch{i2} CD{i2}", netof('U7', str(18-i2)) == f"CD{i2}")
chk("U7 DIR=+3V3 (A->B)", netof('U7', '1') == "+3V3")
chk("U7 OE = CCS_N", netof('U7', '19') == "CCS_N")

# --- QSPI flash ---
for pin, net in [('1','QSPI_SS'),('2','QSPI_SD1'),('3','QSPI_SD2'),
                 ('5','QSPI_SD0'),('6','QSPI_SCLK'),('7','QSPI_SD3'),
                 ('4','GND'),('8','+3V3')]:
    chk(f"U6 pin {pin} {net}", netof('U6', pin) == net)
for pin, net in [('56','QSPI_SS'),('52','QSPI_SCLK'),('53','QSPI_SD0'),
                 ('55','QSPI_SD1'),('54','QSPI_SD2'),('51','QSPI_SD3')]:
    chk(f"U1 pin {pin} {net}", netof('U1', pin) == net)

# --- USB link RP <-> ESP32-S3 (S3 is host on GPIO19/20) ---
esp = open(os.path.join(PRJ, 'esp32s3-sd.kicad_sch')).read()
blk = find_symbol_def(esp, "RF_Module:ESP32-S3-WROOM-1")
esppins = {p['name']: p['number'] for p in parse_pins(blk)}
chk("U1 USB_DM->RP_USB_DM", netof('U1','46') == "RP_USB_DM")
chk("U1 USB_DP->RP_USB_DP", netof('U1','47') == "RP_USB_DP")
chk("R1 bridges RP_USB_DP/USB_DP",
    {netof('R1','1'), netof('R1','2')} == {"RP_USB_DP","USB_DP"})
chk("R2 bridges RP_USB_DM/USB_DM",
    {netof('R2','1'), netof('R2','2')} == {"RP_USB_DM","USB_DM"})
# module pad 13 = GPIO19 (USB D-), pad 14 = GPIO20 (USB D+) per Espressif DS
chk("S3 pad13/GPIO19 (USB D-) on USB_DM", netof('U2', '13') == "USB_DM")
chk("S3 pad14/GPIO20 (USB D+) on USB_DP", netof('U2', '14') == "USB_DP")

# --- fujiversal-astrocade.h ESP32 pins ---
for io, net in [('IO41','SD_CS'),('IO39','SD_SCK'),('IO40','SD_MISO'),
                ('IO38','SD_MOSI'),('TXD0','S3_TXD'),('RXD0','S3_RXD'),
                ('IO48','LED_STRIP'),('IO4','RUN_CTL'),('IO5','BOOTSEL_CTL')]:
    pin = esppins.get(io)
    chk(f"S3 {io} on {net}", pin is not None and netof('U2', pin) == net)

chk("WS2812 DIN driven from LED_STRIP via series R",
    any({netof(r,'1'),netof(r,'2')} == {"LED_STRIP","WS_DIN"}
        for r in ("R12","R13","R14","R15")) and
    any(netof('D2', p) == "WS_DIN" for p in ("1","2","3","4")))

# --- forcing + reset chain ---
chk("Q2 collector on RUN", netof('Q2','3') == "RUN")
chk("Q3 collector on QSPI_SS", netof('Q3','3') == "QSPI_SS")
chk("R9 RUN_CTL->Q2B", {netof('R9','1'),netof('R9','2')} == {"RUN_CTL","Q2B"})
chk("R11 BOOTSEL_CTL->Q3B", {netof('R11','1'),netof('R11','2')} == {"BOOTSEL_CTL","Q3B"})
chk("U1 RUN pin", netof('U1','26') == "RUN")
chk("D8 A1 on RUN", netof('D8','1') == "RUN")
chk("D8 A2 on S3_EN", netof('D8','2') == "S3_EN")
chk("D8 K on RST_BTN", netof('D8','3') == "RST_BTN")
chk("SW1 shorts RST_BTN to GND",
    {netof('SW1','1'),netof('SW1','2')} == {"RST_BTN","GND"})
chk("S3 EN net exists on U2", netof('U2', esppins.get('EN','?')) == "S3_EN")
chk("SW2+R20 BOOTSEL chain",
    {netof('R20','1'),netof('R20','2')} == {"QSPI_SS","BOOTSEL_BTN"} and
    {netof('SW2','1'),netof('SW2','2')} == {"BOOTSEL_BTN","GND"})

# --- power & sense ---
chk("edge +5V feeds power sheet (D6 anode)", netof('D6','2') == "+5V" or netof('D6','1') == "+5V")
chk("R7 +5V->VSENSE", {netof('R7','1'),netof('R7','2')} == {"+5V","VSENSE"})
chk("R8 VSENSE->GND", {netof('R8','1'),netof('R8','2')} == {"VSENSE","GND"})
chk("U1 IOVDD on +3V3", netof('U1','1') == "+3V3")
chk("U1 DVDD from VREG", netof('U1','23') == "DVDD" and netof('U1','45') == "DVDD")
chk("U1 TESTEN grounded", netof('U1','19') == "GND")
chk("XIN chain", netof('U1','20') == "XIN" and netof('Y1','1') == "XIN")
chk("XOUT chain", netof('U1','21') == "XOUT" and
    {netof('R4','1'),netof('R4','2')} == {"XOUT_Y","XOUT"} and netof('Y1','3') == "XOUT_Y")

print(f"\n{ok}/{ok+bad} checks passed" + ("" if bad == 0 else f"  ({bad} FAILED)"))
sys.exit(1 if bad else 0)
