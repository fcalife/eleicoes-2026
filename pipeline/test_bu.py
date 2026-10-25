"""Self-check: BU parser against a real 1st/2nd-round pair (Damasco, zona 1, seção 727)."""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
import bu
d = os.path.join(os.path.dirname(__file__), 'testdata')
assert bu.presidente(os.path.join(d, 'zz-29637-0001-0727-t1.dat')) == {13: 97, 22: 7, 27: 1, 55: 2, 70: 1, 'branco': 1, 'nulo': 9}
assert bu.presidente(os.path.join(d, 'zz-29637-0001-0727-t2.dat')) == {13: 106, 22: 11, 'nulo': 2}
print('test_bu ok')
