# Builds public/geo/regions.json (and relief.jpg) for the briefing map from Natural Earth
# (public domain). Usage, with the downloads in one folder NE:
#
#   curl -L -o NE/countries50.geojson https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_50m_admin_0_countries.geojson
#   curl -L -o NE/states10.geojson    https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_10m_admin_1_states_provinces.geojson
#   curl -L -o NE/land50.geojson      https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_50m_land.geojson
#   python3 scripts/geo/build.py NE public/geo/regions.json
#
#   curl -L -o NE/SR_50M.zip https://naciscdn.org/naturalearth/50m/raster/SR_50M.zip && unzip NE/SR_50M.zip -d NE
#   ffmpeg -i NE/SR_50M.tif -vf "scale=8192:4096:flags=lanczos,format=gray" -q:v 4 public/geo/relief.jpg
#
# States are only kept for the countries in STATE_COUNTRIES (ids like US-NV, DE-BY).
import json, sys, math
ne, out = sys.argv[1], sys.argv[2]

def dp(points, tol):
    # Douglas-Peucker on [(x, y)]
    if len(points) < 4:
        return points
    keep = [False] * len(points)
    keep[0] = keep[-1] = True
    stack = [(0, len(points) - 1)]
    while stack:
        a, b = stack.pop()
        ax, ay = points[a]; bx, by = points[b]
        dx, dy = bx - ax, by - ay
        norm = math.hypot(dx, dy) or 1e-12
        best, idx = -1, -1
        for i in range(a + 1, b):
            px, py = points[i]
            d = abs(dy * (px - ax) - dx * (py - ay)) / norm if (dx or dy) else math.hypot(px - ax, py - ay)
            if d > best:
                best, idx = d, i
        if best > tol:
            keep[idx] = True
            stack += [(a, idx), (idx, b)]
    return [p for p, k in zip(points, keep) if k]

def rings_of(geom, tol, min_points=4):
    polys = [geom['coordinates']] if geom['type'] == 'Polygon' else geom['coordinates']
    rings = []
    for poly in polys:
        for ring in poly[:1]:
            pts = dp([(p[0], p[1]) for p in ring], tol)
            if len(pts) >= min_points:
                rings.append([v for p in pts for v in (round(p[0], 3), round(p[1], 3))])
    return rings

countries = []
for f in json.load(open(f'{ne}/countries50.geojson'))['features']:
    p = f['properties']
    rings = rings_of(f['geometry'], 0.02)
    if rings:
        countries.append({'id': p['ADM0_A3'], 'name': p.get('NAME_DE') or p['NAME'], 'rings': rings})

STATE_COUNTRIES = {'USA', 'DEU'}
states = []
for f in json.load(open(f'{ne}/states10.geojson'))['features']:
    p = f['properties']
    if p.get('adm0_a3') not in STATE_COUNTRIES:
        continue
    rings = rings_of(f['geometry'], 0.012)
    if rings:
        states.append({'id': p['iso_3166_2'], 'country': p['adm0_a3'], 'name': p.get('name_de') or p['name'], 'rings': rings})

land = []
for f in json.load(open(f'{ne}/land50.geojson'))['features']:
    land += rings_of(f['geometry'], 0.02)

json.dump({
    'source': 'Natural Earth (public domain): admin 0 countries 1:50m, admin 1 states 1:10m (USA, DEU), land 1:50m; simplified, rings as [lon, lat, ...]',
    'land': land, 'countries': countries, 'states': states,
}, open(out, 'w'), separators=(',', ':'), ensure_ascii=False)
print(len(land), len(countries), len(states))
