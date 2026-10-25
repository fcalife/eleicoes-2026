"""Collect 2nd-round (pleito 3221) presidential BUs already published by TSE, sampled per municipality.
Re-runnable: cached on disk."""
import collections, hashlib, http.client, json, os, sys, threading, time
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.dirname(__file__))
import bu

HOST = 'resultados.tse.jus.br'
BASE = f'https://{HOST}/oficial/ele2026/arquivo-urna'
UFS = 'ac al am ap ba ce df es go ma mg ms mt pa pb pe pi pr rj rn ro rr rs sc se sp to zz'.split()
DATA = sys.argv[1]
AMOSTRA = 30  # max sections per municipality; the projection only needs each municipality's average swing

_local = threading.local()

def fetch(url, tries=8):  # backoff adds up to ~2 min, about how long a TSE rate-limit block lasted
    """GET with backoff when TSE rate-limits (HTTP 429/503), honoring Retry-After."""
    for n in range(tries):
        status, headers, b = _get(url)
        if status not in (429, 503): break
        time.sleep(float(headers.get('Retry-After') or 2 ** n))
    if status != 200: raise RuntimeError(f'HTTP {status} {url}')
    return b

def _get(url):
    """GET over one keep-alive HTTPS connection per thread: a TLS handshake per request made the run CPU-bound."""
    for retry in (False, True):
        conn = getattr(_local, 'conn', None) or http.client.HTTPSConnection(HOST, timeout=60)
        _local.conn = conn
        try:
            conn.request('GET', url.split(HOST, 1)[1]); r = conn.getresponse(); b = r.read()
            break
        except (http.client.HTTPException, OSError):
            conn.close(); _local.conn = None  # server dropped the idle connection: reconnect once
            if retry: raise
    return r.status, r.headers, b

def get(url, path=None):
    if path and os.path.exists(path): return open(path, 'rb').read()
    b = fetch(url)
    if path:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        open(path + '.tmp', 'wb').write(b)
        os.replace(path + '.tmp', path)  # atomic: an interrupted run never leaves a truncated file in the cache
    return b

def config(pleito, uf, cache):
    path = os.path.join(DATA, f'cs-{pleito}-{uf}.json') if cache else None
    d = json.loads(get(f'{BASE}/{pleito}/config/{uf}/{uf}-p00{pleito}-cs.json', path))
    for m in d['abr'][0]['mu']:
        for z in m['zon']:
            for s in z['sec']:
                yield uf, m['cd'], z['cd'], s

def bu_path(key):
    uf, mun, zon, sec = key
    return os.path.join(DATA, 'bu2', uf, f'{mun}-{zon}-{sec}.dat')

def one(key):
    uf, mun, zon, sec = key
    path = bu_path(key)
    if not os.path.exists(path):
        d = f'{BASE}/3221/dados/{uf}/{mun}/{zon}/{sec}'
        aux = json.loads(get(f'{d}/p003221-{uf}-m{mun}-z{zon}-s{sec}-aux.json'))
        h = aux['hashes'][-1]
        nm = next(a['nm'] for a in h['arq'] if a['tp'] == 'bu')
        get(f'{d}/{h["hash"]}/{nm}', path)
    return key, bu.presidente(path)

def amostra(publicadas, por_municipio=AMOSTRA):
    """Up to `por_municipio` published sections per municipality, in a fixed pseudo-random order so the
    sample is stable across runs. Sections already downloaded always stay in (they cost nothing)."""
    grupos = {}
    for k in publicadas: grupos.setdefault(k[:2], []).append(k)
    out = []
    for ks in grupos.values():
        cached = [k for k in ks if os.path.exists(bu_path(k))]
        resto = sorted(set(ks) - set(cached), key=lambda k: hashlib.md5('-'.join(k).encode()).hexdigest())
        out += cached + resto[:max(0, por_municipio - len(cached))]
    return out

if __name__ == '__main__':
    # 1st-round configs (static) are cached; 2nd-round configs are refetched every run
    with ThreadPoolExecutor(8) as ex:
        t1 = [x for xs in ex.map(lambda u: list(config(3220, u, True)), UFS) for x in xs]
        t2 = [x for xs in ex.map(lambda u: list(config(3221, u, False)), UFS) for x in xs]
    agg = {'t1': {f'{u}-{m}-{z}-{s["ns"]}': s.get('nsa', []) for u, m, z, s in t1},
           't2': {f'{u}-{m}-{z}-{s["ns"]}': s.get('nsa', []) for u, m, z, s in t2}}
    json.dump(agg, open(os.path.join(DATA, 'aggregations.json'), 'w'))
    publicadas = [(u, m, z, s['ns']) for u, m, z, s in t2 if 'da' in s]
    todo = amostra(publicadas)
    json.dump({'publicadas': len(publicadas)}, open(os.path.join(DATA, 't2_status.json'), 'w'))
    print(f'secoes t2: {len(t2)}  com BU publicado: {len(publicadas)}  na amostra: {len(todo)}', flush=True)
    out, errs = {}, collections.Counter()
    with ThreadPoolExecutor(16) as ex:  # 64 got HTTP 429 from TSE on election night; keep-alive makes 16 enough
        for f in [ex.submit(one, k) for k in todo]:
            try:
                k, v = f.result(); out['-'.join(k)] = v
            except Exception as e:
                errs[f'{type(e).__name__}: {e}'.split(' https')[0][:80]] += 1
    json.dump(out, open(os.path.join(DATA, 't2_results.json'), 'w'))
    print(f'parseados: {len(out)}  erros: {sum(errs.values())}', errs.most_common(3) if errs else '')
