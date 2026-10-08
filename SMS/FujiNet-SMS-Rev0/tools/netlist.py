"""The schematic's netlist as check_nets.py and check_glue.py read it: exported
fresh with kicad-cli (into the system temp directory), never from design.py."""
import os, re, subprocess, tempfile
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
PRJ = os.path.dirname(HERE)
SCH = os.path.join(PRJ, 'FujiNet-SMS-Rev0.kicad_sch')


def canon(n):
    """KiCad's net name -> design.py's: /NET, /sheet/NET and NET all name NET."""
    return n if n.startswith('unconnected') else n.rsplit('/', 1)[-1]


class Netlist:
    def __init__(self):
        fd, fn = tempfile.mkstemp(prefix='fujinet-sms-', suffix='.xml')
        os.close(fd)
        try:
            subprocess.run(['kicad-cli', 'sch', 'export', 'netlist', '--format', 'kicadxml', '-o', fn, SCH],
                           check=True, capture_output=True)
            t = ET.parse(fn)
        finally:
            os.remove(fn)
        self.node_net, self.func_net, self.nets, self.ptype = {}, {}, {}, {}
        full = {}
        for n in t.iter('net'):
            name = canon(n.get('name'))
            if name in full:
                raise SystemExit('netlist: %s and %s are separate nets' % (full[name], n.get('name')))
            full[name] = n.get('name')
            for nd in n.iter('node'):
                ref, pin, f = nd.get('ref'), nd.get('pin'), (nd.get('pinfunction') or '')
                f = re.sub(r'_%s$' % re.escape(pin), '', f)   # kicad-cli appends _<pin> to repeated names
                self.node_net[(ref, pin)] = name
                self.ptype[(ref, pin)] = nd.get('pintype')
                if f:
                    self.func_net[(ref, f)] = name
                self.nets.setdefault(name, []).append((ref, pin, f))
        self.parts = {c.get('ref'): (c.findtext('value'), c.findtext('footprint')) for c in t.iter('comp')}

    def by_value(self, v):
        return sorted(r for r, (val, _) in self.parts.items() if val == v)

    def one(self, v):
        return (self.by_value(v) or [None])[0]

    def net(self, ref, pin):
        return self.node_net.get((ref, str(pin)))


def unconn(n):
    return n is None or n.startswith('unconnected')


def define(path, name, default=None):
    """#define NAME value from a C header: an integer (0x.., 12u) or GPIO_NUM_n; GPIO_NUM_NC -> -1."""
    txt = open(path).read()
    m = re.search(r'#define\s+%s\s+(\S+)' % re.escape(name), txt)
    if not m:
        if default is not None:
            return default
        raise SystemExit('%s: no #define %s' % (path, name))
    v = m.group(1)
    if v == 'GPIO_NUM_NC':
        return -1
    m2 = re.match(r'GPIO_NUM_(\d+)', v)
    if m2:
        return int(m2.group(1))
    return int(v.rstrip('uUlL'), 0)
