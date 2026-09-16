// Shared place popups + glossary (index.html, ubytovani.html)
// ---------- place popups and glossary ----------
(async function(){
  const ON_UBYT = /ubytovani\.html$/.test(location.pathname);
  const modal = document.getElementById('modal'), box = modal.querySelector('.box'), content = document.getElementById('modal-content');
  const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
  function open(html, small) { content.innerHTML = html; modal.classList.toggle('small', !!small); modal.classList.add('on'); modal.setAttribute('aria-hidden','false'); box.scrollTop = 0; document.body.style.overflow = 'hidden'; }
  window.openModal = open;
  function close() { modal.classList.remove('on'); modal.setAttribute('aria-hidden','true'); document.body.style.overflow = ''; }
  modal.addEventListener('click', e => { if (e.target === modal || e.target.closest('.x')) close(); });
  document.addEventListener('keydown', e => { if (e.key === 'Escape') close(); });

  let data;
  try { data = await (await fetch('assets/places.json')).json(); } catch (e) { console.error('places.json', e); return; }
  const places = Object.fromEntries(data.places.map(p => [p.id, p]));
  const terms = data.terms;

  function placeHtml(p) {
    let img = '';
    if (p.img && p.img.file) {
      const fn = p.img.file.replace(/ /g, '_');
      const src = 'https://commons.wikimedia.org/wiki/Special:FilePath/' + encodeURIComponent(fn) + '?width=900';
      img = `<img src="${src}" alt="${esc(p.name)}" loading="lazy"><div class="credit">Foto: ${esc(p.img.author)}, ${esc(p.img.license)}, <a href="https://commons.wikimedia.org/wiki/File:${encodeURIComponent(fn)}" target="_blank" rel="noopener">Wikimedia Commons</a></div>`;
    }
    const sec = (t, v) => v ? `<h4>${t}</h4><p>${esc(v)}</p>` : '';
    const links = (p.links || []).map(l => `<a href="${esc(l.url)}" target="_blank" rel="noopener">${esc(l.label)} ↗</a>`).join('');
    const gal = (p.gallery || []).map(g => { const fn = g.file.replace(/ /g, '_'); const enc = encodeURIComponent(fn);
      return `<a class="th" href="https://commons.wikimedia.org/wiki/File:${enc}" target="_blank" rel="noopener" title="${esc(g.author)}, ${esc(g.license)}"><img src="https://commons.wikimedia.org/wiki/Special:FilePath/${enc}?width=480" alt="" loading="lazy"><span>${esc(g.author)} · ${esc(g.license)}</span></a>`; }).join('');
    const galHtml = gal ? `<h4>Další fotky (Wikimedia Commons)</h4><div class="gallery">${gal}</div>` : '';
    const facts = (p.facts || []).map(f => { const i = f.indexOf(':'); return i > 0 ? `<div><b>${esc(f.slice(0, i))}</b>${esc(f.slice(i + 1).trim())}</div>` : `<div>${esc(f)}</div>`; }).join('');
    const factsHtml = facts ? `<div class="facts">${facts}</div>` : '';
    const call = (cls, t, v) => v ? `<div class="pcall ${cls}"><b>${t}</b>${esc(v)}</div>` : '';
    let extra = '';
    if (p.kind === 'ubytování') {
      const bk = p.bk || {};
      const praise = (bk.praise || []).length ? `<h4>Co hosté chválí (Booking)</h4><ul>${bk.praise.map(q => `<li>„${esc(q.replace(/^[“"]+|[”".]+$/g, ''))}“</li>`).join('')}</ul>` : '';
      const faq = bk.faq ? sec('Z FAQ a vybavení na Bookingu', bk.faq + (bk.fac ? ' Vybavení: ' + bk.fac + '.' : '')) : '';
      let where = '';
      if (p.ll) {
        const [lat, lon] = p.ll;
        where = `<h4>Kde to je</h4><p>${bk.addr ? esc(bk.addr) + ' · ' : ''}${p.ll_approx ? 'souřadnice jsou střed obce, ne dům · ' : ''}${lat.toFixed(4)}, ${lon.toFixed(4)} · <a href="https://mapy.cz/turisticka?source=coor&id=${lon}%2C${lat}&x=${lon}&y=${lat}&z=16" target="_blank" rel="noopener">Mapy.cz ↗</a> · <a href="https://www.google.com/maps/search/?api=1&query=${lat},${lon}" target="_blank" rel="noopener">Google Maps ↗</a></p>`;
      }
      extra = sec('Dostupnost a storno', p.booking) + sec('Kontakt', p.contact) + sec('Hodnocení', p.rating) + praise + faq + where + `<p style="margin-top:10px"><a href="${ON_UBYT ? '' : 'ubytovani.html'}#${esc(p.id)}">Tabulka noclehů: cena, Booking s daty, storno, kontakty →</a></p>`;
    }
    const city = p.city_route ? `<div class="city"><h4>Průvodce městem</h4>${sec('Parkování', p.city_parking)}${sec('Okruh na náš čas', p.city_route)}${sec('Co vidět', p.city_see)}${sec('Kde jíst', p.city_eat)}${sec('Nákupy, bankomat, pumpa', p.city_shop)}${sec('Místní zvyky', p.city_local)}</div>` : '';
    const meta = [p.day ? 'den ' + p.day : '', p.detour || '', p.time ? 'na místě ' + p.time : ''].filter(Boolean).join(' · ');
    return `${img}<div class="in"><h3>${esc(p.name)}</h3><div class="kind">${esc(p.kind)}${meta ? ' · ' + esc(meta) : ''}</div>${factsHtml}${call('warn', 'Varování', p.warning)}${sec('Co to je', p.what)}${sec('Proč tam', p.why)}${sec('Co zažijeme', p.experience)}${sec('Jak se tam dostat', p.access)}${sec('Tipy', p.tips)}${extra}${city}${call('note', 'Poznámka', p.note)}${call('fun', 'Kuriozita', p.fun)}<div class="links">${links}</div>${galHtml}</div>`;
  }
  document.addEventListener('click', e => {
    const t = e.target.closest('.pl'); if (!t) return;
    const p = places[t.dataset.pl]; if (p) { e.preventDefault(); open(placeHtml(p)); }
  });
  document.addEventListener('keydown', e => { if (e.key === 'Enter' && e.target.classList && e.target.classList.contains('pl')) e.target.click(); });
  // deep link: index.html#p=<place id> opens the card (used by the lodging tables)
  const openFromHash = () => { const m = location.hash.match(/^#p=([\w-]+)/); if (m && places[m[1]]) open(placeHtml(places[m[1]])); };
  openFromHash(); window.addEventListener('hashchange', openFromHash);

  // glossary list
  const dl = document.getElementById('gloss-list');
  if (dl) Object.entries(terms).sort((a, b) => a[1].localeCompare(b[1], 'cs')).forEach(([k, v]) => {
    const head = v.split(':')[0]; const rest = v.slice(head.length + 1).trim();
    dl.insertAdjacentHTML('beforeend', `<dt>${esc(head)}</dt><dd>${esc(rest)}</dd>`);
  });

  // annotate terms in text: first occurrence per block
  const EXACT = new Set(['AKT','TAP','han','ura','lek','UNESCO','CASCO','SH7']);
  const keys = Object.keys(terms).sort((a, b) => b.length - a.length);
  const escRx = s => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const alts = [];
  for (const k of keys) {
    if (EXACT.has(k)) { alts.push(k === 'lek' ? 'lek(?:y|ů|ech)?(?!\\p{L})' : (k === 'SH7' ? 'SH7\\d' : escRx(k) + '(?!\\p{L})')); }
    else { const cap = k[0].toUpperCase() + k.slice(1); alts.push('(?:' + escRx(k) + '|' + escRx(cap) + ')\\p{L}*'); }
  }
  const rx = new RegExp('(^|[^\\p{L}])(' + alts.join('|') + ')', 'u');
  const keyOf = w => keys.find(k => EXACT.has(k) ? (k === 'SH7' ? w.startsWith('SH7') : w === k || (k === 'lek' && /^lek/.test(w))) : w.toLowerCase().startsWith(k.toLowerCase()));
  const SKIP = new Set(['A','BUTTON','SCRIPT','STYLE','H1','H2','H3','SUP','INPUT','SELECT','TEXTAREA','DT','DD']);
  const blocks = document.querySelectorAll('#zkratka .card, #trasy .day .body, #trasy .route-head, #trasy .card, #trasy table, #baleni li, #rizeni p, #rizeni li, #pozor .risk, #proc .in');
  for (const b of blocks) {
    const seen = new Set();
    const walker = document.createTreeWalker(b, NodeFilter.SHOW_TEXT, { acceptNode: n => {
      let el = n.parentElement; while (el && el !== b) { if (SKIP.has(el.tagName) || el.classList.contains('pl') || el.classList.contains('gl')) return NodeFilter.FILTER_REJECT; el = el.parentElement; }
      return NodeFilter.FILTER_ACCEPT; } });
    const nodes = []; while (walker.nextNode()) nodes.push(walker.currentNode);
    for (const n of nodes) {
      let text = n.nodeValue, frag = null, last = 0, m, guard = 0;
      const out = document.createDocumentFragment();
      while ((m = rx.exec(text.slice(last))) && guard++ < 20) {
        const key = keyOf(m[2]); if (!key) { last = last + m.index + m[1].length + m[2].length; continue; }
        const start = last + m.index + m[1].length, end = start + m[2].length;
        if (seen.has(key)) { out.appendChild(document.createTextNode(text.slice(last, end))); last = end; continue; }
        seen.add(key);
        out.appendChild(document.createTextNode(text.slice(last, start)));
        const s = document.createElement('span'); s.className = 'gl'; s.dataset.gl = key; s.tabIndex = 0; s.textContent = text.slice(start, end); out.appendChild(s);
        last = end; frag = out;
      }
      if (frag) { out.appendChild(document.createTextNode(text.slice(last))); n.parentNode.replaceChild(out, n); }
    }
  }
  document.addEventListener('click', e => {
    const t = e.target.closest('.gl'); if (!t) return;
    const v = terms[t.dataset.gl]; if (!v) return;
    const head = v.split(':')[0]; open(`<div class="in"><h3>${esc(head)}</h3><p>${esc(v.slice(head.length + 1).trim())}</p><div class="links"><a href="${ON_UBYT ? 'index.html' : ''}#slovnicek">celý slovníček</a></div></div>`, true);
  });
})();
