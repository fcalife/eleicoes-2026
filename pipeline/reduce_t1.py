"""Reduce TSE votacao_secao CSV (1st round, presidente) to {uf-mun-zona-secao: {13, 22, outros, branco, nulo}}."""
import csv, json, sys
out, cargos = {}, set()
with open(sys.argv[1], encoding='latin-1', newline='') as f:
    for r in csv.DictReader(f, delimiter=';'):
        cargos.add(r['CD_CARGO'])
        if r['CD_CARGO'] != '1': continue
        k = f"{r['SG_UF'].lower()}-{int(r['CD_MUNICIPIO']):05d}-{int(r['NR_ZONA']):04d}-{int(r['NR_SECAO']):04d}"
        n = int(r['NR_VOTAVEL'])
        c = {13: '13', 22: '22', 95: 'branco', 96: 'nulo'}.get(n, 'outros')
        d = out.setdefault(k, {})
        d[c] = d.get(c, 0) + int(r['QT_VOTOS'])
json.dump(out, open(sys.argv[2], 'w'))
print('cargos', cargos, 'secoes', len(out))
