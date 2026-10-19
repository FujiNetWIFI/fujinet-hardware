"""Minimal KiCad S-expression reader/writer used by the generator scripts.

Atoms are str; quoted strings are Q instances (a str subclass) so they are
written back quoted.  Lists are Python lists.
"""


class Q(str):
    """A quoted string atom."""


def parse(text):
    stack, cur, i, n = [], [], 0, len(text)
    while i < n:
        c = text[i]
        if c == '(':
            stack.append(cur); cur = []; i += 1
        elif c == ')':
            done = cur; cur = stack.pop(); cur.append(done); i += 1
        elif c.isspace():
            i += 1
        elif c == '"':
            j = i + 1; buf = []
            while text[j] != '"':
                if text[j] == '\\':
                    buf.append(text[j:j + 2]); j += 2
                else:
                    buf.append(text[j]); j += 1
            cur.append(Q(''.join(buf))); i = j + 1
        else:
            j = i
            while j < n and not text[j].isspace() and text[j] not in '()':
                j += 1
            cur.append(text[i:j]); i = j
    assert not stack
    return cur[0]


def q(s):
    return Q(s)


def _atom(a):
    if isinstance(a, Q):
        return '"' + a.replace('"', '\\"') + '"' if '\\' not in a else '"' + a + '"'
    if isinstance(a, float):
        s = ('%.4f' % a).rstrip('0').rstrip('.')
        return '0' if s in ('-0', '') else s
    return str(a)


def dump(e, ind=0):
    """KiCad-style: lists of only atoms on one line, others broken with tabs."""
    if not isinstance(e, list):
        return _atom(e)
    if all(not isinstance(x, list) for x in e):
        return '(' + ' '.join(_atom(x) for x in e) + ')'
    head = []
    k = 0
    while k < len(e) and not isinstance(e[k], list):
        head.append(_atom(e[k])); k += 1
    out = '(' + ' '.join(head)
    for x in e[k:]:
        out += '\n' + '\t' * (ind + 1) + dump(x, ind + 1)
    return out + '\n' + '\t' * ind + ')'


def find(e, key):
    """First child list whose head is key."""
    for x in e:
        if isinstance(x, list) and x and x[0] == key:
            return x
    return None


def findall(e, key):
    return [x for x in e if isinstance(x, list) and x and x[0] == key]
