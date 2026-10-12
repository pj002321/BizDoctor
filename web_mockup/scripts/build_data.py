# 실제 CSV 산출물 → 목업용 JSON 추출
# 실행: 프로젝트 루트(shinhan)에서  .\.venv\Scripts\python.exe web_mockup\scripts\build_data.py
#  - 입력: seoul_panel_model_ready.csv, tableau/tableau_quarterly.csv, tableau/tableau_industry.csv
#  - 자치구 경계: data/seoul_gu.geojson (southkorea/seoul-maps, kostat 2013 simple) 필요 시 재다운로드
import json, math, os
import pandas as pd

SRC = '.'
OUT = 'web_mockup/data'
os.makedirs(f'{OUT}/cells', exist_ok=True)

GU_CODE = {'11110':'종로구','11140':'중구','11170':'용산구','11200':'성동구','11215':'광진구','11230':'동대문구',
 '11260':'중랑구','11290':'성북구','11305':'강북구','11320':'도봉구','11350':'노원구','11380':'은평구','11410':'서대문구',
 '11440':'마포구','11470':'양천구','11500':'강서구','11530':'구로구','11545':'금천구','11560':'영등포구','11590':'동작구',
 '11620':'관악구','11650':'서초구','11680':'강남구','11710':'송파구','11740':'강동구'}
GU_ENG = {}
def r(x, n=2):
    if x is None or (isinstance(x, float) and math.isnan(x)): return None
    return round(float(x), n)

def dump(name, obj):
    with open(f'{OUT}/{name}', 'w', encoding='utf-8') as f:
        json.dump(obj, f, ensure_ascii=False, separators=(',', ':'))

# ---------- 1. 자치구 지도 경로 (SVG path) ----------
geo = json.load(open('web_mockup/scripts/seoul_gu.geojson', encoding='utf-8'))
lat0 = 37.55; kx = math.cos(math.radians(lat0))
pts = []
for f in geo['features']:
    g = f['geometry']; polys = g['coordinates'] if g['type'] == 'MultiPolygon' else [g['coordinates']]
    for poly in polys:
        for ring in poly: pts += ring
xs = [p[0]*kx for p in pts]; ys = [-p[1] for p in pts]
minx, maxx, miny, maxy = min(xs), max(xs), min(ys), max(ys)
W = 600; s = W/(maxx-minx); H = round((maxy-miny)*s)
shapes = []
for f in geo['features']:
    g = f['geometry']; polys = g['coordinates'] if g['type'] == 'MultiPolygon' else [g['coordinates']]
    d = ''; area_best = 0; cen = (0, 0)
    for poly in polys:
        for ring in poly:
            P = [((x*kx-minx)*s, (-y-miny)*s) for x, y in ring]
            d += 'M' + 'L'.join(f'{a:.1f},{b:.1f}' for a, b in P) + 'Z'
            a = abs(sum(P[i][0]*P[i-1][1]-P[i-1][0]*P[i][1] for i in range(len(P))))
            if a > area_best:
                area_best = a; cen = (sum(p[0] for p in P)/len(P), sum(p[1] for p in P)/len(P))
    shapes.append({'gu': f['properties']['name'], 'eng': f['properties']['name_eng'], 'd': d, 'cx': r(cen[0], 1), 'cy': r(cen[1], 1)})
dump('seoul_gu_paths.json', {'width': W, 'height': H, 'shapes': shapes})

# ---------- 3. 패널 → 행정동 목록·셀 시계열 (F-MAP-02/03, F-DIA-02/07) ----------
p = pd.read_csv(f'{SRC}/seoul_panel_model_ready.csv', encoding='utf-8-sig')
p['gu'] = p['행정동_코드'].astype(str).str[:5].map(GU_CODE)
assert p['gu'].notna().all()
quarters = sorted(p['기준_년분기_코드'].unique())
qlabel = [f'{str(q)[:4]} Q{str(q)[4]}' for q in quarters]
qidx = {q: i for i, q in enumerate(quarters)}

dongs = p[['행정동_코드', '행정동_코드_명', 'gu']].drop_duplicates().sort_values(['gu', '행정동_코드_명'])
dump('dongs.json', [{'code': str(a), 'name': b, 'gu': c} for a, b, c in dongs.itertuples(index=False)])
inds = p[['서비스_업종_코드', '서비스_업종_코드_명', 'KOSIS_산업1']].drop_duplicates('서비스_업종_코드').sort_values('서비스_업종_코드_명')
dump('service_industries.json', [{'code': a, 'name': b, 'kosis': c} for a, b, c in inds.itertuples(index=False)])

# 셀 시계열: 자치구별 파일로 분할 (백엔드에선 사전집계 테이블이 대신함)
# 값 배열 순서: [점포수, 폐업점포수, 개업점포수, 폐업률, 개업률, 폐업개업격차, percentile, 프랜차이즈비중]
for gu, gdf in p.groupby('gu'):
    out = {}
    for (dc, sc), cdf in gdf.groupby(['행정동_코드', '서비스_업종_코드']):
        series = [None]*len(quarters)
        for x in cdf.itertuples(index=False):
            series[qidx[x.기준_년분기_코드]] = [int(x.점포_수), int(x.폐업_점포_수), int(x.개업_점포_수), r(x.폐업_률, 1), r(x.개업_율, 1), r(x.폐업개업_격차, 1),
                                          r(x.폐업률_업종내_percentile, 3), r(x.프랜차이즈_비중, 3)]
        out.setdefault(str(dc), {})[sc] = series
    dump(f'cells/{gu}.json', out)

# 업종별 최신분기 폐업률 분포 (F-DIA-07 분포 위 위치 표시)
last = p[p['기준_년분기_코드'] == quarters[-1]]
dist = {}
for sc, d in last.groupby('서비스_업종_코드'):
    pct = d['폐업률_업종내_percentile']
    hist = [int(((pct >= i/20) & (pct < (i+1)/20 if i < 19 else pct <= 1)).sum()) for i in range(20)]
    dist[sc] = {'n': int(len(d)), 'hist': hist, 'meanCloseRate': r(d['폐업_률'].mean())}
dump('industry_latest_dist.json', dist)

# ---------- 5. 분기 추이 · 업종 랭킹 (F-MAP-04/05) ----------
q = pd.read_csv(f'{SRC}/tableau/tableau_quarterly.csv', encoding='utf-8-sig')
dump('quarterly.json', [{'quarter': x.분기표기, 'industry': x.산업대분류, 'stores': int(x.점포수), 'closed': int(x.폐업점포수),
    'avgCloseRate': r(x.평균폐업률), 'avgOpenRate': r(x.평균개업률), 'realCloseRate': r(x.실질폐업률)} for x in q.itertuples()])
ind = pd.read_csv(f'{SRC}/tableau/tableau_industry.csv', encoding='utf-8-sig')
dump('industry_ranking.json', [{'name': x.업종, 'industry': x.산업대분류, 'stores': int(x.점포수), 'closed': int(x.폐업점포수),
    'avgCloseRate': r(x.평균폐업률, 3), 'obs': int(x.관측수), 'realCloseRate': r(x.실질폐업률, 3)} for x in ind.itertuples()])

dump('meta.json', {'quarters': qlabel, 'latestQuarter': qlabel[-1],
                   'source': ['seoul_panel_model_ready.csv', 'tableau_quarterly.csv', 'tableau_industry.csv']})
print('ok', len(quarters), 'quarters')
