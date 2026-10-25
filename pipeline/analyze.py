"""Section-by-section 1st->2nd round comparison (Lula=13, Flavio=22) and extrapolation to unreported sections.

Unit of comparison = group of sections linked by aggregation in either round (union-find), so that
1st-round and 2nd-round votes always cover the same voters.
Projection: for each unreported unit, L2 = L1 * rL and F2 = F1 * rF, where rX = sum(X2)/sum(X1) over
reported units in the finest stratum with >= MIN reported units: municipality -> UF -> region -> Brazil.
Hybrid: a municipality 100% totalized enters whole, from TSE's consolidated result, instead of its sections.
Section-level statistics (swing per section, charts) still come from the section BUs.
"""
import json, os, sys, statistics
DATA = sys.argv[1]
MIN = 10
MIN_UF_LOCAL = 200  # a UF-level extrapolation only counts as "local" (reliability badge) with this many sampled units
REGIAO = {**dict.fromkeys('ac am ap pa ro rr to'.split(), 'N'), **dict.fromkeys('al ba ce ma pb pe pi rn se'.split(), 'NE'),
          **dict.fromkeys('df go ms mt'.split(), 'CO'), **dict.fromkeys('es mg rj sp'.split(), 'SE'),
          **dict.fromkeys('pr rs sc'.split(), 'S'), 'zz': 'EXT'}

t1 = json.load(open(os.path.join(DATA, 't1_secoes.json')))
t2 = json.load(open(os.path.join(DATA, 't2_results.json')))
agg = json.load(open(os.path.join(DATA, 'aggregations.json')))

parent = {}
def find(x):
    parent.setdefault(x, x)
    while parent[x] != x: parent[x] = parent[parent[x]]; x = parent[x]
    return x
for k in list(t1) + list(agg['t1']) + list(agg['t2']): find(k)
for rnd in ('t1', 't2'):
    for k, nsa in agg[rnd].items():
        pre = k.rsplit('-', 1)[0]
        for s in nsa: parent[find(f'{pre}-{s}')] = find(k)

aggregated2 = {f"{k.rsplit('-', 1)[0]}-{s}" for k, nsa in agg['t2'].items() for s in nsa}
units = {}
for k in parent:
    u = units.setdefault(find(k), {'L1': 0, 'F1': 0, 'V1': 0, 'L2': 0, 'F2': 0, 'V2': 0, 'pend': 0})
    v = t1.get(k, {})
    u['L1'] += v.get('13', 0); u['F1'] += v.get('22', 0); u['V1'] += sum(v.values())
    if k in agg['t2'] and k not in aggregated2:          # 2nd-round principal section (has its own BU)
        r = t2.get(k)
        if r is None: u['pend'] += 1
        else:
            u['L2'] += r.get(13, r.get('13', 0)); u['F2'] += r.get(22, r.get('22', 0)); u['V2'] += sum(r.values())
mun2_path = os.path.join(DATA, 't2_municipios.json')
mun2 = json.load(open(mun2_path)) if os.path.exists(mun2_path) else {}
fechados = {k for k, r in mun2.items() if r['ts'] and r['st'] == r['ts']}
mun_units = {}  # closed municipality -> one unit holding all its sections
for root, u in units.items():
    uf, mun = root.split('-')[:2]
    u['strata'] = (f'{uf}-{mun}', uf, REGIAO[uf], 'BR')
    u['rep'] = u['pend'] == 0 and u['V2'] > 0
    u['fechado'] = u['strata'][0] in fechados
    if u['fechado']:
        m = mun_units.setdefault(u['strata'][0], {'L1': 0, 'F1': 0, 'V1': 0, 'n': 0, 'strata': u['strata']})
        m['L1'] += u['L1']; m['F1'] += u['F1']; m['V1'] += u['V1']; m['n'] += 1
for k, m in mun_units.items():
    m['L2'], m['F2'] = mun2[k]['13'], mun2[k]['22']
# what the projection counts as known: closed municipalities whole, plus reported sections elsewhere
cobertas = list(mun_units.values()) + [dict(u, n=1) for u in units.values() if u['rep'] and not u['fechado']]

# ratios per stratum, from known units (a[4] counts sections, so MIN means the same for both kinds)
S = {}
for u in cobertas:
    for s in u['strata']:
        a = S.setdefault(s, [0, 0, 0, 0, 0]); a[0] += u['L1']; a[1] += u['F1']; a[2] += u['L2']; a[3] += u['F2']; a[4] += u['n']

proj, level_votes, local_votes = {}, [0, 0, 0, 0], 0
def add(uf, L, F, L1, F1, rep, n=1):
    for key in (uf, 'BR'):
        p = proj.setdefault(key, {'L': 0, 'F': 0, 'L1r': 0, 'F1r': 0, 'L2r': 0, 'F2r': 0, 'n': 0, 'nrep': 0})
        p['L'] += L; p['F'] += F; p['n'] += n
        if rep: p['L1r'] += L1; p['F1r'] += F1; p['L2r'] += L; p['F2r'] += F; p['nrep'] += n
for u in cobertas: add(u['strata'][1], u['L2'], u['F2'], u['L1'], u['F1'], True, u['n'])
for u in units.values():
    if u['fechado'] or u['rep']: continue
    uf = u['strata'][1]
    for i, s in enumerate(u['strata']):
        a = S.get(s)
        if a and a[4] >= MIN and a[0] and a[1]: break
    else: a, i = None, 3
    u['nivel'] = i
    level_votes[i] += u['V1']
    if i == 0 or (i == 1 and a[4] >= MIN_UF_LOCAL): local_votes += u['V1']
    if a: add(uf, u['L1'] * a[2] / a[0], u['F1'] * a[3] / a[1], 0, 0, False)
    else: add(uf, 0, 0, 0, 0, False)

pct = lambda a, b: 100 * a / (a + b) if a + b else float('nan')
rep = [u for u in units.values() if u['rep']]  # sections with their own BU: section-level statistics only
V1tot = sum(u['V1'] for u in units.values()); V1rep = sum(u['V1'] for u in cobertas)
n_cobertas = sum(u['n'] for u in cobertas)
print(f'Unidades (secoes/agregacoes): {len(units)}  com dados no 2T: {n_cobertas}  ({100*V1rep/V1tot:.2f}% dos votos do 1T)'
      f'  municipios fechados: {len(mun_units)}  secoes com BU: {len(rep)}')
print('Nivel usado p/ extrapolar (% dos votos 1T nao apurados): ' + ', '.join(
    f'{n}={100*v/max(1,sum(level_votes)):.1f}%' for n, v in zip(('municipio', 'UF', 'regiao', 'Brasil'), level_votes)))
if rep:
    d = [pct(u['L2'], u['F2']) - pct(u['L1'], u['F1']) for u in rep if u['L1'] + u['F1'] and u['L2'] + u['F2']]
    print(f"\nSecao a secao (apuradas): delta share Lula (L/(L+F)) 1T->2T: media {statistics.mean(d):+.2f}pp, "
          f"mediana {statistics.median(d):+.2f}pp; Lula ganhou share em {100*sum(x>0 for x in d)/len(d):.0f}% das secoes")
    L1, F1, L2, F2 = (sum(u[k] for u in cobertas) for k in ('L1', 'F1', 'L2', 'F2'))
    print(f'Nas secoes com dados: Lula {L1}->{L2} ({100*(L2/L1-1):+.1f}%), Flavio {F1}->{F2} ({100*(F2/F1-1):+.1f}%)')
print(f"\n{'UF':4}{'apur':>8}{'tot':>8}  {'Lula 1T->2T':>12}{'Flav 1T->2T':>12}  {'Lula% 1T':>9}{'proj 2T':>9}")
t1uf = {}
for u in units.values():
    a = t1uf.setdefault(u['strata'][1], [0, 0]); a[0] += u['L1']; a[1] += u['F1']
for k in sorted(proj, key=lambda k: (k == 'BR', k)):
    p = proj[k]; a = t1uf.get(k) or [sum(x[0] for x in t1uf.values()), sum(x[1] for x in t1uf.values())]
    gl = f"{100*(p['L2r']/p['L1r']-1):+.1f}%" if p['L1r'] else '-'
    gf = f"{100*(p['F2r']/p['F1r']-1):+.1f}%" if p['F1r'] else '-'
    print(f"{k:4}{p['nrep']:>8}{p['n']:>8}  {gl:>12}{gf:>12}  {pct(*a):>8.2f}%{pct(p['L'], p['F']):>8.2f}%")
b = proj['BR']
print(f"\nPROJECAO 2T (votos validos): Lula {pct(b['L'], b['F']):.2f}%  x  Flavio {pct(b['F'], b['L']):.2f}%   "
      f"(Lula {b['L']:,.0f} / Flavio {b['F']:,.0f})")

# ---- dashboard export (JSON row files) ----
import datetime, glob, random
OUT = os.path.join(DATA, 'dash'); os.makedirs(OUT, exist_ok=True)
dump = lambda name, rows: json.dump(rows, open(os.path.join(OUT, f'{name}.json'), 'w', encoding='utf-8'), ensure_ascii=False)
nomes = {}
for f in glob.glob(os.path.join(DATA, 'cs-3220-*.json')):
    for m in json.load(open(f, encoding='utf-8'))['abr'][0]['mu']:
        nomes[f"{os.path.basename(f)[8:10]}-{m['cd']}"] = m['nm']
lv = dict(zip(('municipio', 'uf', 'regiao', 'brasil'), (round(100 * v / max(1, sum(level_votes)), 2) for v in level_votes)))
r1 = lambda x: round(x, 2)
L1, F1, L2, F2 = (sum(u[k] for u in cobertas) for k in ('L1', 'F1', 'L2', 'F2'))
d = d if rep else [0]
dump('resumo', [{
    'atualizado': datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds'),
    'secoes_total': len(units), 'secoes_apuradas': n_cobertas, 'pct_votos_1t_apurados': round(100 * V1rep / V1tot, 3),
    'secoes_com_bu': len(rep), 'municipios_fechados': len(mun_units), 'municipios_total': len({u['strata'][0] for u in units.values()}),
    'secoes_publicadas': json.load(open(os.path.join(DATA, 't2_status.json')))['publicadas'],
    'nivel_municipio': lv['municipio'], 'nivel_uf': lv['uf'], 'nivel_regiao': lv['regiao'], 'nivel_brasil': lv['brasil'],
    'nivel_local': round(100 * local_votes / max(1, sum(level_votes)), 2),
    'delta_media_pp': r1(statistics.mean(d)), 'delta_mediana_pp': r1(statistics.median(d)),
    'pct_secoes_lula_ganhou': r1(100 * sum(x > 0 for x in d) / len(d)),
    'lula_1t_apuradas': L1, 'flavio_1t_apuradas': F1, 'lula_2t_apuradas': L2, 'flavio_2t_apuradas': F2,
    'lula_2t_apuradas_pct': r1(pct(L2, F2)), 'lula_1t_apuradas_pct': r1(pct(L1, F1)),
    'lula_1t_pct': r1(pct(*[sum(x[0] for x in t1uf.values()), sum(x[1] for x in t1uf.values())])),
    'lula_proj': round(b['L']), 'flavio_proj': round(b['F']),
    'lula_proj_pct': r1(pct(b['L'], b['F'])), 'flavio_proj_pct': r1(pct(b['F'], b['L'])),
}])
uflevel = {}
for u in units.values():
    if 'nivel' not in u: continue
    c = uflevel.setdefault(u['strata'][1], [0, 0, 0, 0]); c[u['nivel']] += u['V1']
NIV = ('município', 'UF', 'região', 'Brasil')
dump('por_uf', [{
    'uf': k.upper(), 'regiao': REGIAO[k], 'secoes_total': p['n'], 'secoes_apuradas': p['nrep'],
    'lula_var_pct': r1(100 * (p['L2r'] / p['L1r'] - 1)) if p['L1r'] else None,
    'flavio_var_pct': r1(100 * (p['F2r'] / p['F1r'] - 1)) if p['F1r'] else None,
    'lula_1t_pct': r1(pct(*t1uf[k])), 'lula_proj_pct': r1(pct(p['L'], p['F'])),
    'nivel_extrapolacao': NIV[max(range(4), key=lambda i: uflevel.get(k, [1, 0, 0, 0])[i])] if k in uflevel else 'apurada',
} for k, p in sorted(proj.items()) if k != 'BR'])
hist = {}
for x in d: hist[max(-20, min(20, round(x)))] = hist.get(max(-20, min(20, round(x))), 0) + 1
dump('delta_hist', [{'delta_pp': k, 'secoes': hist.get(k, 0)} for k in range(-20, 21)])
amostra = random.Random(1).sample(rep, min(3000, len(rep)))
roots = {id(u): r for r, u in units.items()}
dump('secoes', [{
    'secao': roots[id(u)], 'uf': roots[id(u)][:2].upper(), 'municipio': nomes.get(roots[id(u)][:8], ''),
    'lula_1t': u['L1'], 'flavio_1t': u['F1'], 'lula_2t': u['L2'], 'flavio_2t': u['F2'],
    'lula_share_1t': r1(pct(u['L1'], u['F1'])), 'lula_share_2t': r1(pct(u['L2'], u['F2'])),
} for u in amostra if u['L1'] + u['F1'] and u['L2'] + u['F2']])
print('dashboard JSON em', OUT)
