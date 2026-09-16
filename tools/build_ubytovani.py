#!/usr/bin/env python3
"""Regenerate the per-night lodging tables in ubytovani.html and assets/ubytovani.gpx from assets/places.json.

Lodging records (id ubyt-*) carry: ll [lat, lon], bk {url, status, score, rev, rooms, canc, praise, ...},
meals, tent, contact_html. Table order per night is defined in ORDER below (explicit priority, then by score).
Run from repo root: python3 tools/build_ubytovani.py
"""
import json, re, html
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CHECKED = '16. 9. 2026'
EUR = 24.5
NIGHTS = [
    ('d18', 'Pá', 'Pá 18. 9. · Nivicë (Kurvelesh)', '2026-09-18', '2026-09-19'),
    ('d19', 'So', 'So 19. 9. · Gjirokastër', '2026-09-19', '2026-09-20'),
    ('d20', 'Ne', 'Ne 20. 9. · Përmet / Bual', '2026-09-20', '2026-09-21'),
    ('d21', 'Po', 'Po 21. 9. · Voskopojë (nebo Korçë)', '2026-09-21', '2026-09-22'),
    ('d22', 'Út', 'Út 22. 9. · Bogovë / Çorovodë', '2026-09-22', '2026-09-23'),
    ('d23', 'St', 'St 23. 9. · Berat / Roshnik', '2026-09-23', '2026-09-24'),
]
# explicit priority per night; ids not listed here but with day == night are appended by score
ORDER = {
    'Pá': ['ubyt-gh-on-canyon', 'ubyt-progon-house', 'ubyt-camp-nivica', 'ubyt-maris', 'ubyt-saffron', 'ubyt-peshtan', 'ubyt-glealb', 'ubyt-uji-ftohte'],
    'So': ['ubyt-ahmetaj', 'ubyt-life-on-farm', 'ubyt-alsara', 'ubyt-stone-city', 'ubyt-bujtina-maria', 'ubyt-musee', 'ubyt-manga', 'ubyt-amades', 'ubyt-old-town', 'ubyt-bizant', 'ubyt-babameto', 'ubyt-kalemi2', 'ubyt-barrels'],
    'Ne': ['ubyt-joan', 'ubyt-bual', 'ubyt-nako', 'ubyt-lugina', 'ubyt-stone-house', 'ubyt-kutal', 'ubyt-shtepia-me-lule', 'ubyt-albturist', 'ubyt-mulliri', 'ubyt-peshtan', 'ubyt-chri-chri', 'ubyt-alvero'],
    'Po': ['ubyt-vila-helen', 'ubyt-liana', 'ubyt-shkodrani', 'ubyt-argis', 'ubyt-vila-janko', 'ubyt-mecollari', 'ubyt-vila118', 'ubyt-vila-mata', 'ubyt-ura-e-kovacit', 'ubyt-cakuli', 'ubyt-sofra-kolonjare', 'ubyt-hani-pazarit', 'ubyt-bujtina-leon', 'ubyt-life-gallery', 'ubyt-vila-falo', 'ubyt-akademia', 'ubyt-lm-vithkuq'],
    'Út': ['ubyt-white-villa', 'ubyt-xhaferri', 'ubyt-dafinat', 'ubyt-marsi', 'ubyt-kanione', 'ubyt-luli-mucaj', 'ubyt-stylish-room', 'ubyt-zeni-zoto', 'ubyt-nuhellari', 'ubyt-village-polican', 'ubyt-farm-river', 'ubyt-kt-qato', 'ubyt-skrapari', 'ubyt-bracaj'],
    'St': ['ubyt-mangalemi', 'ubyt-mimani', 'ubyt-nurellari', 'ubyt-timos', 'ubyt-jprifti', 'ubyt-vila-harmoni', 'ubyt-koxhaku', 'ubyt-citrus-nest', 'ubyt-well-house', 'ubyt-oda-skulptorit', 'ubyt-parents-house', 'ubyt-bujtina-tomorrit', 'ubyt-alpeta', 'ubyt-klea'],
}
INACTIVE = {'ubyt-gh-on-canyon': 'zápis neaktivní (přesměrovává na vyhledávání)', 'ubyt-bujtina-tomorrit': 'zápis neaktivní'}
NO_BOOKING = {'ubyt-camp-nivica': 'není (jen vlastní web)', 'ubyt-lm-vithkuq': 'není', 'ubyt-mulliri': 'není (Facebook)', 'ubyt-life-gallery': 'není (ověřit)', 'ubyt-skrapari': 'není', 'ubyt-akademia': 'není'}

E = html.escape


def min_price(rooms):
    nums = [int(n.replace(' ', '').replace(' ', '')) for n in re.findall(r'(\d[\d  ]{2,6}) Kč', rooms or '')]
    return min(nums) if nums else None


def fmt_price(n):
    return f"{n:,}".replace(',', ' ') + ' Kč'


def map_links(p):
    if not p.get('ll'):
        return '<span class="n">–</span>'
    lat, lon = p['ll']
    note = '<br><span class="g">střed obce, ne dům</span>' if p.get('ll_approx') else ''
    return (f'<a href="https://mapy.cz/turisticka?source=coor&id={lon}%2C{lat}&x={lon}&y={lat}&z=16" target="_blank" rel="noopener">Mapy.cz</a><br>'
            f'<a href="https://www.google.com/maps/search/?api=1&query={lat},{lon}" target="_blank" rel="noopener">Google</a>' + note)


def wifi(bk):
    """WiFi note from the Booking facilities string (speed if Booking measured it)."""
    f = (bk.get('fac') or '') + ' ' + (bk.get('faq') or '')
    m = re.search(r'(\d+) Mbps', f)
    if m:
        n = int(m.group(1))
        cls = 'v' if n >= 30 else ('bad' if n < 10 else '')
        return f'<span class="{cls}">{n} Mbps</span>'
    if re.search(r'rychl\w* WiFi', f, re.I):
        return '<span class="v">rychlá (bez čísla)</span>'
    if re.search(r'základní', f, re.I):
        return '<span class="bad">základní</span>'
    if re.search(r'WiFi', f, re.I):
        return 'ano, rychlost neuvedena'
    return '<span class="n">neuvedeno</span>' if bk else '–'


def row(p, night, ci, co, tip, rid):
    bk = p.get('bk') or {}
    badge = ' <span class="pill ok">✔ rezervováno</span>' if p.get('reserved') else (' <span class="pill">záloha č. 1</span>' if tip else '')
    name = f'<a class="popup-link" href="#p={p["id"]}" title="Otevřít kartu s detaily"><b>{E(p["name"])}</b></a>' + badge
    if bk:
        rating = f'<span class="g">{bk["score"].replace(".", ",")} · {bk["rev"]} recenzí · Booking {CHECKED}</span>'
        praise = bk.get('praise') or []
        if praise:
            rating += f'<br><span class="g">„{E(praise[0][:140].rstrip("“”\"."))}…“</span>'
    else:
        rating = f'<span class="g">{E(p.get("rating", ""))}</span>'
    mp = min_price(bk.get('rooms'))
    price = f'{fmt_price(mp)}<br><span class="g">≈ {round(mp / EUR)} €</span>' if mp else '<span class="n">–</span>'
    same_night = bk.get('night') == night
    if p['id'] in INACTIVE:
        booking = f'<span class="n">není ({E(INACTIVE[p["id"]])})</span>'
    elif p['id'] in NO_BOOKING:
        booking = f'<span class="n">{E(NO_BOOKING[p["id"]])}</span>'
    elif bk:
        full = bk['status'].startswith('plné')
        url = bk['url'] if full else f"{bk['url']}?checkin={ci}&checkout={co}&group_adults=2&no_rooms=1&group_children=0"
        booking = f'<a href="{url}" target="_blank" rel="noopener">{"zápis (na naše datum plné)" if full else "otevřít s daty"}</a>'
    else:
        booking = '<span class="n">–</span>'
    canc = E(bk.get('canc') or '–') if bk else '–'
    if p.get('reserved'):
        status = f'<span class="v">✔ rezervováno</span><br><span class="g">{E(p["reserved"])}</span>'
    elif bk and same_night:
        st = bk['status']
        cls = 'bad' if st.startswith('plné') else 'v'
        status = f'<span class="{cls}">{E(st)}</span>'
        if not st.startswith('plné') and mp:
            status += f'<br><span class="g">od {fmt_price(mp)}</span>'
    elif bk:
        status = f'<span class="g">ověřeno jen pro noc {E(bk["night"])}: {E(bk["status"])}</span>'
    elif p['id'] in INACTIVE:
        status = '<span class="g">mimo Booking</span>'
    else:
        status = '<span class="g">jen přímo</span>'
    cells = [name + '<br>' + rating, price, booking, canc, status, p.get('contact_html') or '<span class="n">jen Booking</span>',
             map_links(p), E(p.get('meals', '')), wifi(bk), E(p.get('tent', ''))]
    return f'<tr id="{rid}">' + ''.join(f'<td>{c}</td>' for c in cells) + '</tr>'


BACKUP = {
    'ubyt-gh-on-canyon': 'Když se s rodinou Merjo ztratí kontakt nebo dojedete pozdě: <b>Progon House</b> v Progonatu (Booking, 682 Kč se snídaní, 20 min před Nivicë), pak Mari\'s tamtéž. Při velmi pozdním dojezdu zůstat na asfaltu: Bujtina Peshtan nebo Gle-Alb u Tepelenë.',
    'ubyt-ahmetaj': 'Alsara (200 m od bazaru, storno do 18. 9.) nebo Manga (parkování). Když jste v Gjirokastru do 15 h a chcete farmu: Life on the Farm (tel. +355 69 875 0502), jen do setmění.',
    'ubyt-joan': 'Nako (100 m od promenády, storno do 19. 9.) nebo Shtëpia me Lule. Bual (statek, večeře od Florindy) jen když je čas dojet do 18:30.',
    'ubyt-vila-helen': 'Ve Voskopojë: Vila Janko (81 Mbps, storno do 20. 9.) nebo Shkodrani. Když Frashër nevyjde a jedete přes Osumi do Çorovodë: Guest House Marsi (storno kdykoli) nebo Luli Mucaj; Helen pak propadá (nevratná).',
    'ubyt-white-villa': 'Dafinat hned vedle (storno do 18:00 v den příjezdu) nebo Xhaferri (restaurace, 4 km od Çorovodë). Když spojka Vithkuq–Osumi selže a jedete objížďkou přes Berat: spát rovnou v Beratu (J.Prifti) a kaňon Osumi vynechat.',
    'ubyt-mangalemi': 'J.Prifti (Mangalem, storno do 20. 9.) nebo Koxhaku. Kdo chce večeři v Alpetě: Mimani Stone House v Roshniku (bez platby předem), ve čtvrtek pak odjezd v 8:00.',
}


def reservations(places):
    ids = ['ubyt-gh-on-canyon', 'ubyt-ahmetaj', 'ubyt-joan', 'ubyt-vila-helen', 'ubyt-white-villa', 'ubyt-mangalemi']
    rows = []
    for pid in ids:
        p = places[pid]; r = p['res']; lat, lon = p['ll']
        maps = (f'<a href="https://mapy.cz/turisticka?source=coor&id={lon}%2C{lat}&x={lon}&y={lat}&z=16" target="_blank" rel="noopener">Mapy.cz</a> · '
                f'<a href="https://www.google.com/maps/search/?api=1&query={lat},{lon}" target="_blank" rel="noopener">Google</a>')
        tel = r['phone'].replace(' ', '')
        cells = [f'<b>{E(r["night"])}</b>', f'<a class="popup-link" href="#p={pid}"><b>{E(p["name"])}</b></a><br><span class="g">{E(r["addr"])}</span><br>{maps}',
                 f'{E(r["via"])}<br><span class="g">{"č. " + r["no"] if r["no"] != "–" else "bez čísla"}</span>', f'{E(r["checkin"])}<br><span class="g">odjezd {E(r["checkout"])}</span>',
                 E(r['room']), f'{E(r["price"])}<br><span class="g">{E(r["pay"])}</span>',
                 f'<span class="{"bad" if "NEVRATN" in r["cancel"] else "v"}">{E(r["cancel"])}</span>',
                 f'<a href="tel:{tel}">{E(r["phone"])}</a>' + (f'<br><span class="g">{E(r["note"])}</span>' if r.get('note') else ''), BACKUP[pid]]
        rows.append('<tr>' + ''.join(f'<td>{c}</td>' for c in cells) + '</tr>')
    head = ('<div class="table-scroll"><table class="cmp" style="min-width:1400px"><thead><tr><th>Noc</th><th>Ubytování</th><th>Rezervace</th><th>Check-in</th>'
            '<th>Pokoj</th><th>Cena a platba</th><th>Storno</th><th>Telefon</th><th>Záloha, kdyby to nevyšlo</th></tr></thead><tbody>\n')
    return head + '\n'.join(rows) + '\n</tbody></table></div>\n'


def build():
    data = json.loads((ROOT / 'assets/places.json').read_text(encoding='utf-8'))
    places = {p['id']: p for p in data['places']}
    head = ('<div class="table-scroll"><table class="cmp" style="min-width:1250px"><thead><tr><th>Ubytování</th><th>Cena / noc</th><th>Booking</th>'
            '<th>Storno</th><th>Obsazenost ' + CHECKED[:-5] + '</th><th>Kontakt</th><th>Mapa</th><th>Strava</th><th>WiFi</th><th>Stan</th></tr></thead><tbody>\n')
    out, seen_ids = [], set()
    for hid, night, title, ci, co in NIGHTS:
        ids = list(ORDER[night])
        extra = [p['id'] for p in data['places'] if p['id'].startswith('ubyt-') and p.get('day') == night and p['id'] not in ids]
        extra.sort(key=lambda i: -float((places[i].get('bk') or {}).get('score', 0) or 0))
        ids += extra
        out.append(f'<h3 id="{hid}">{E(title)}</h3>' + head)
        for i, pid in enumerate(ids):
            p = places[pid]
            rid = pid if pid not in seen_ids else f'{pid}-{night.lower().replace("á", "a").replace("ú", "u")}'
            seen_ids.add(pid)
            out.append(row(p, night, ci, co, i == 0, rid) + '\n')
        out.append('</tbody></table></div>\n')
    tables = ''.join(out)
    path = ROOT / 'ubytovani.html'
    src = path.read_text(encoding='utf-8')
    new = re.sub(r'(<!-- TABLES:START -->).*?(<!-- TABLES:END -->)', lambda m: m.group(1) + '\n' + tables + m.group(2), src, flags=re.S)
    new = re.sub(r'(<!-- RES:START -->).*?(<!-- RES:END -->)', lambda m: m.group(1) + '\n' + reservations(places) + m.group(2), new, flags=re.S)
    if '<!-- TABLES:START -->' not in src or '<!-- RES:START -->' not in src:
        raise SystemExit('markers TABLES:START/END not found')
    path.write_text(new, encoding='utf-8')
    # GPX waypoints
    wpts = []
    for p in data['places']:
        if not p['id'].startswith('ubyt-') or not p.get('ll'):
            continue
        lat, lon = p['ll']
        bk = p.get('bk') or {}
        desc = ' · '.join(x for x in [f"noc {p.get('day', '?')}", bk.get('status', ''), bk.get('addr', ''), bk.get('canc', '')] if x)
        link = f'<link href="{E(bk["url"])}"><text>Booking</text></link>' if bk else ''
        approx = (' (jen střed obce)' if p.get('ll_approx') else '') + (' ✔ REZERVOVÁNO' if p.get('reserved') else '')
        wpts.append(f'<wpt lat="{lat}" lon="{lon}"><name>{E(p["name"])}{approx}</name><desc>{E(desc)}</desc>{link}<sym>Lodging</sym></wpt>')
    gpx = ('<?xml version="1.0" encoding="UTF-8"?>\n<gpx version="1.1" creator="albanie build_ubytovani" xmlns="http://www.topografix.com/GPX/1/1">'
           f'<metadata><name>Albánie 4x4 – ubytování ({CHECKED})</name></metadata>\n' + '\n'.join(wpts) + '\n</gpx>\n')
    (ROOT / 'assets/ubytovani.gpx').write_text(gpx, encoding='utf-8')
    print(f'{len(seen_ids)} lodgings in tables, {len(wpts)} GPX waypoints')


if __name__ == '__main__':
    build()
