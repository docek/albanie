#!/usr/bin/env python3
"""Build real road geometry for the itinerary.

Routes each day leg with BRouter (OSM-based, knows Albanian gravel tracks),
writes assets/routes.json (for the Leaflet map), one GPX per route with the real
line, and prints Mapy.cz per-day links with dense waypoints so the planner
cannot pick a different road.

Usage: python3 tools/build_routes.py            # uses cache in .cache/brouter
"""
import json, math, os, sys, time, urllib.parse, urllib.request, html

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, '.cache', 'brouter'); os.makedirs(CACHE, exist_ok=True)

# name: (lat, lon) – verified against OSM (Nominatim/Overpass, 14. 9. 2026)
W = {
    'Letiště Tirana': (41.4147, 19.7206), 'Tirana': (41.3275, 19.8187), 'Lushnjë': (40.9422, 19.7060),
    'Berat': (40.7019, 19.9581), 'Roshnik': (40.7311, 20.0414), 'Bogovë': (40.5726, 20.1569),
    'Poliçan': (40.6122, 20.0990), 'Qafa e Kulmakut': (40.6216, 20.1907), 'Tomorr – türbe': (40.6363, 20.1627),
    'Çorovodë': (40.5036, 20.2283), 'Kaňon Osumi': (40.4334, 20.2710), 'Bual': (40.2600, 20.3000), 'Frashër': (40.3661, 20.4282),
    'Përmet': (40.2333, 20.3534), 'Bënja / Lengarica': (40.2519, 20.4162), 'Këlcyrë': (40.3135, 20.1923),
    'Gjirokastër': (40.0771, 20.1393), 'Libohovë': (40.0336, 20.2626), 'Selckë': (40.1089, 20.2968),
    'Poliçan (Zagoria)': (40.1298, 20.3518), 'Sheper': (40.1706, 20.3067), 'Ndëran': (40.1689, 20.2814),
    'Tepelenë': (40.2982, 20.0209), 'Progonat': (40.2155, 19.9469), 'Nivicë': (40.2403, 19.8916),
    'Fier': (40.7251, 19.5582), 'Apollonia': (40.7208, 19.4863), 'Bovilla': (41.4477, 19.8643), 'Fushë Çajupi': (40.1897, 20.1813),
    'Leskovik': (40.1524, 20.5990), 'Barmash': (40.2778, 20.6194), 'Ersekë': (40.3384, 20.6810),
    'Korçë': (40.6159, 20.7772), 'Voskopojë': (40.6332, 20.5906), 'Vithkuq': (40.5246, 20.5828),
    'Gramsh': (40.8654, 20.1864), 'Vodopád Sotira': (40.7689, 20.1943), 'Kaňon Holta': (40.9236, 20.2437),
    'Elbasan': (41.1127, 20.0821),
    'Golem': (40.17169, 19.93501), 'Kolonjë': (40.16264, 20.01280), 'Lekdush': (40.22412, 19.96379),
    'Krujë': (41.5086, 19.7931),
}

# profile per leg: 'car' = asphalt (car-fast), 'track' = gravel (trekking follows tracks)
ROUTES = {
 'D': {'color': '#24567f', 'days': [
   ('Pá', 'Letiště → Fier → Tepelenë → Nivicë', [('Letiště Tirana','Fier','car'),('Fier','Tepelenë','car'),('Tepelenë','Progonat','track'),('Progonat','Nivicë','track')], 'Nivicë'),
   ('So', 'Zkouška 1: Kurvelesh Progonat → Golem → Kolonjë → Gjirokastër', [('Nivicë','Progonat','track'),('Progonat','Golem','track'),('Golem','Kolonjë','track'),('Kolonjë','Gjirokastër','track')], 'Gjirokastër'),
   ('Ne', 'Okruh Zagoria → Përmet, Bënja a Lengarica', [('Gjirokastër','Libohovë','car'),('Libohovë','Selckë','track'),('Selckë','Poliçan (Zagoria)','track'),('Poliçan (Zagoria)','Sheper','track'),('Sheper','Ndëran','track'),('Ndëran','Fushë Çajupi','track'),('Fushë Çajupi','Gjirokastër','car'),('Gjirokastër','Këlcyrë','car'),('Këlcyrë','Përmet','car'),('Përmet','Bënja / Lengarica','car')], 'Përmet'),
   ('Po', 'Zkouška 2: Përmet → Frashër → Ersekë → Korçë → Voskopojë', [('Bënja / Lengarica','Përmet','car'),('Përmet','Frashër','track'),('Frashër','Ersekë','track'),('Ersekë','Korçë','car'),('Korçë','Voskopojë','car')], 'Voskopojë'),
   ('Út', 'Vithkuq → Osumi → Çorovodë', [('Voskopojë','Vithkuq','car'),('Vithkuq','Çorovodë','track')], 'Çorovodë'),
   ('St', 'Tomorr → Bogovë → Roshnik', [('Çorovodë','Bogovë','car'),('Bogovë','Poliçan','car'),('Poliçan','Qafa e Kulmakut','car'),('Qafa e Kulmakut','Tomorr – türbe','track'),('Tomorr – türbe','Qafa e Kulmakut','track'),('Qafa e Kulmakut','Poliçan','car'),('Poliçan','Roshnik','car')], 'Berat'),
   ('Čt', 'Roshnik → Berat → letiště', [('Roshnik','Berat','car'),('Berat','Lushnjë','car'),('Lushnjë','Letiště Tirana','car')], None),
 ]},
 'B': {'color': '#b5461f', 'days': [
   ('Pá', 'Letiště → Berat → Bogovë', [('Letiště Tirana','Lushnjë','car'),('Lushnjë','Berat','car'),('Berat','Bogovë','car'),('Bogovë','Berat','car')], 'Berat'),
   ('So', 'Tomorr → Çorovodë', [('Berat','Poliçan','car'),('Poliçan','Qafa e Kulmakut','car'),('Qafa e Kulmakut','Tomorr – türbe','track'),('Tomorr – türbe','Qafa e Kulmakut','track'),('Qafa e Kulmakut','Poliçan','car'),('Poliçan','Çorovodë','car')], 'Çorovodë'),
   ('Ne', 'Kaňon Osumi → Përmet → Bënja a Lengarica', [('Çorovodë','Kaňon Osumi','track'),('Kaňon Osumi','Bual','track'),('Bual','Përmet','car'),('Përmet','Bënja / Lengarica','car')], 'Përmet'),
   ('Po', 'Përmet → SH75 → Korçë', [('Bënja / Lengarica','Përmet','car'),('Përmet','Leskovik','car'),('Leskovik','Barmash','car'),('Barmash','Ersekë','car'),('Ersekë','Korçë','car')], 'Korçë'),
   ('Út', 'Voskopojë → Vithkuq → Osumi → Berat', [('Korçë','Voskopojë','car'),('Voskopojë','Vithkuq','car'),('Vithkuq','Çorovodë','track'),('Çorovodë','Poliçan','car'),('Poliçan','Berat','car')], 'Berat'),
   ('St', 'Berat → Gramsh → Sotira → Holta', [('Berat','Gramsh','track'),('Gramsh','Vodopád Sotira','track'),('Vodopád Sotira','Gramsh','track'),('Gramsh','Kaňon Holta','track'),('Kaňon Holta','Gramsh','track')], 'Gramsh'),
   ('Čt', 'Gramsh → letiště', [('Gramsh','Elbasan','car'),('Elbasan','Letiště Tirana','car')], None),
 ]},
 'V': {'color': '#7a847e', 'days': [
   ('Pá·B', 'Kratší pátek: letiště → Gjirokastër (a v sobotu zkouška obráceně do Nivicë)', [('Letiště Tirana','Fier','car'),('Fier','Tepelenë','car'),('Tepelenë','Gjirokastër','car')], None),
   ('Po·B', 'Frashër nevyjde: otočka a přes kaňon Osumi do Çorovodë', [('Përmet','Frashër','track'),('Frashër','Përmet','track'),('Përmet','Bual','car'),('Bual','Kaňon Osumi','track'),('Kaňon Osumi','Çorovodë','track')], None),
   ('Čt·B', 'Čtvrtek s Bovillou', [('Roshnik','Berat','car'),('Berat','Lushnjë','car'),('Lushnjë','Tirana','car'),('Tirana','Bovilla','track'),('Bovilla','Letiště Tirana','car')], None),
   ('Čt·C', 'Čtvrtek s Krujë', [('Roshnik','Berat','car'),('Berat','Lushnjë','car'),('Lushnjë','Tirana','car'),('Tirana','Krujë','car'),('Krujë','Letiště Tirana','car')], None),
 ]},
}
PROFILE = {'car': 'car-fast', 'track': 'trekking'}


def brouter(a, b, prof):
    key = f"{a[0]:.4f}_{a[1]:.4f}_{b[0]:.4f}_{b[1]:.4f}_{prof}.json"
    fp = os.path.join(CACHE, key)
    if os.path.exists(fp):
        return json.load(open(fp))
    url = ('https://brouter.de/brouter?lonlats=%f,%f|%f,%f&profile=%s&alternativeidx=0&format=geojson'
           % (a[1], a[0], b[1], b[0], PROFILE[prof]))
    for attempt in range(4):
        try:
            d = json.load(urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'albanie-plan/1.0'}), timeout=120))
            f = d['features'][0]
            out = {'km': float(f['properties']['track-length']) / 1000,
                   'up': float(f['properties'].get('filtered ascend', 0)),
                   'coords': [[round(c[1], 5), round(c[0], 5)] for c in f['geometry']['coordinates']]}
            json.dump(out, open(fp, 'w'))
            return out
        except Exception as e:
            err = e; time.sleep(5 * (attempt + 1))
    raise SystemExit(f'BRouter failed for {a}->{b}: {err}')


def hav(p, q):
    R = 6371; la1, lo1, la2, lo2 = map(math.radians, (p[0], p[1], q[0], q[1]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 2 * R * math.asin(math.sqrt(h))


def sample(coords, step_km):
    out = [coords[0]]; acc = 0
    for i in range(1, len(coords)):
        acc += hav(coords[i - 1], coords[i])
        if acc >= step_km:
            out.append(coords[i]); acc = 0
    if out[-1] != coords[-1]:
        out.append(coords[-1])
    return out


def thin(coords, tol_m=15):
    """Douglas-Peucker in a crude planar approximation (enough for a web map)."""
    if len(coords) < 3:
        return coords
    def dist(p, a, b):
        ax, ay = a[1], a[0]; bx, by = b[1], b[0]; px, py = p[1], p[0]
        dx, dy = bx - ax, by - ay
        if dx == dy == 0:
            return hav(p, a) * 1000
        t = max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
        return hav(p, (ay + t * dy, ax + t * dx)) * 1000
    imax, dmax = 0, 0
    for i in range(1, len(coords) - 1):
        d = dist(coords[i], coords[0], coords[-1])
        if d > dmax:
            imax, dmax = i, d
    if dmax > tol_m:
        return thin(coords[:imax + 1], tol_m)[:-1] + thin(coords[imax:], tol_m)
    return [coords[0], coords[-1]]


def main():
    result = {}
    links = {}
    for rk, r in ROUTES.items():
        days = []
        tot_km = tot_track = 0
        for i, (dow, title, legs, night) in enumerate(r['days'], 1):
            line = []; km = trk = up = 0
            for a, b, prof in legs:
                seg = brouter(W[a], W[b], prof)
                km += seg['km']; up += seg['up']
                if prof == 'track':
                    trk += seg['km']
                line += seg['coords'] if not line else seg['coords'][1:]
            tot_km += km; tot_track += trk
            slim = thin(line, 12)
            wps = sample(line, 6)
            mp = ('https://mapy.com/fnc/v1/route?mapset=outdoor&routeType=bike_mountain&start=%s&end=%s&waypoints=%s'
                  % ('%.4f,%.4f' % (wps[0][1], wps[0][0]), '%.4f,%.4f' % (wps[-1][1], wps[-1][0]),
                     ';'.join('%.4f,%.4f' % (p[1], p[0]) for p in wps[1:-1])))
            days.append({'n': i, 'dow': dow, 'title': title, 'km': round(km), 'track_km': round(trk), 'up': round(up),
                         'night': night, 'line': slim, 'mapy': mp,
                         'stops': [(a, W[a]) for a, _, _ in legs] + [(legs[-1][1], W[legs[-1][1]])]})
            links.setdefault(rk, []).append((i, dow, title, round(km), round(trk), mp))
            print(f'{rk} {i} {dow} {title}: {km:.0f} km, track {trk:.0f} km, +{up:.0f} m, {len(slim)} pts', file=sys.stderr)
        result[rk] = {'color': r['color'], 'km': round(tot_km), 'track_km': round(tot_track), 'days': days}
        # GPX with real geometry
        fn = {'D': 'Doporucena-trasa-D.gpx', 'B': 'Alternativa-B.gpx', 'V': 'Varianty-D.gpx'}[rk]
        g = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<gpx version="1.1" creator="albanie-4x4-plan (BRouter/OSM)" xmlns="http://www.topografix.com/GPX/1/1">',
             f'  <metadata><name>Albánie 4x4 – trasa {rk} – 18.–24. 9. 2026 (reálný průjezd po cestách z OSM)</name></metadata>']
        seen = set()
        for d in days:
            for name, (la, lo) in d['stops']:
                if name in seen:
                    continue
                seen.add(name)
                g.append(f'  <wpt lat="{la}" lon="{lo}"><name>{html.escape(name)}</name></wpt>')
        for d in days:
            g.append(f'  <trk><name>{d["n"]} {d["dow"]} – {html.escape(d["title"])}</name><trkseg>')
            g += [f'    <trkpt lat="{p[0]}" lon="{p[1]}"/>' for p in d['line']]
            g.append('  </trkseg></trk>')
        g += ['</gpx>', '']
        open(os.path.join(ROOT, fn), 'w').write('\n'.join(g))
    json.dump(result, open(os.path.join(ROOT, 'assets', 'routes.json'), 'w'), ensure_ascii=False, separators=(',', ':'))
    json.dump(links, open(os.path.join(ROOT, '.cache', 'mapy_links.json'), 'w'), ensure_ascii=False, indent=1)
    print('routes.json written', file=sys.stderr)


if __name__ == '__main__':
    main()
