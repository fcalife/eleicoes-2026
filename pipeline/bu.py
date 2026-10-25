"""Minimal DER reader for TSE boletim de urna (bu.dat): extracts presidential votes."""
import sys
from der import tlv

def children(b, s, e):
    out = []
    while s < e:
        h, cs, ce = tlv(b, s)
        out.append((h, cs, ce)); s = ce
    return out

def num(b, s, e): return int.from_bytes(b[s:e], 'big', signed=True)

def find_cargos(b, s, e, acc):
    """TotalVotosCargo = SEQ{[1] codigoCargo, INT ordem, SEQ OF votavel}; votavel = SEQ{[1] tipo, [2] qtd, [3] {partido, numero}?}"""
    try: kids = children(b, s, e)
    except Exception: return
    if len(kids) >= 3 and kids[0][0] == (2, False, 1) and kids[1][0] == (0, False, 2) and kids[2][0] == (0, True, 16):
        votos = {}
        for v in children(b, kids[2][1], kids[2][2]):
            vk = {h[2]: (cs, ce, h) for h, cs, ce in children(b, v[1], v[2]) if h[0] == 2}
            tipo, qtd = num(b, *vk[1][:2]), num(b, *vk[2][:2])
            key = {2: 'branco', 3: 'nulo'}.get(tipo, tipo)
            if tipo == 1 and 3 in vk:
                key = num(b, *children(b, vk[3][0], vk[3][1])[1][1:])
            votos[key] = votos.get(key, 0) + qtd
        acc.setdefault(num(b, kids[0][1], kids[0][2]), votos)
        return
    for h, cs, ce in kids:
        if h[1]: find_cargos(b, cs, ce, acc)
        elif h == (0, False, 4): find_cargos(b, cs, ce, acc)  # envelope: BU lives in an OCTET STRING

def presidente(path):
    b = open(path, 'rb').read(); acc = {}
    find_cargos(b, 0, len(b), acc)
    return acc.get(1)

if __name__ == '__main__':
    for p in sys.argv[1:]: print(p, presidente(p))
