import sys
def tlv(b, i):
    t = b[i]; i += 1
    if t & 0x1f == 0x1f:
        n = 0
        while True:
            x = b[i]; i += 1; n = n << 7 | (x & 0x7f)
            if not x & 0x80: break
        tag = n
    else: tag = t & 0x1f
    l = b[i]; i += 1
    if l & 0x80:
        k = l & 0x7f; l = int.from_bytes(b[i:i+k], 'big'); i += k
    return (t >> 6, bool(t & 0x20), tag), i, i + l

def walk(b, i=0, end=None, d=0, out=print):
    end = len(b) if end is None else end
    while i < end:
        (cls, cons, tag), s, e = tlv(b, i)
        v = b[s:e]
        if cons:
            out(f"{'  '*d}[{cls}:{tag}] {{")
            walk(b, s, e, d+1, out)
        else:
            show = int.from_bytes(v, 'big', signed=True) if len(v) <= 8 else v[:40]
            out(f"{'  '*d}[{cls}:{tag}] {show!r}")
            if len(v) > 8:
                try: walk(v, 0, None, d+1, out)
                except Exception: pass
        i = e
if __name__ == '__main__':
    walk(open(sys.argv[1], 'rb').read())
