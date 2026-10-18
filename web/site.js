// Maps for the public site: the statewide utility territory map and the pilot communities map.
// Map data comes from saved copies in data.js (window.SNAPSHOTS), built by run.py from
// data/snapshots/, which scripts/fetch_data.py downloads and refreshes weekly. The queries,
// filters (e.g. leaving out wholesale suppliers WAPA and Deseret) and simplification live there.

// ---- Map 1: statewide electric and gas service territories ----
// Colorado's border is (almost exactly) a box of latitude and longitude lines.
const COLORADO_BBOX = [-109.0603, 36.9924, -102.0415, 41.0034];  // west, south, east, north

// A saved dataset, as a promise so a missing one is handled like a failed download.
const snapshot = name => (window.SNAPSHOTS && window.SNAPSHOTS[name])
  ? Promise.resolve(window.SNAPSHOTS[name])
  : Promise.reject(new Error(`Map data "${name}" is missing`));

// Cut every shape at the Colorado border. Clipping leaves empty rings for parts that were
// fully outside, so those are removed, and shapes with nothing left are dropped.
function clipToColorado(fc) {
  if (!window.turf) return fc;
  const cleanPolygon = rings => {
    const kept = rings.filter(r => r.length >= 4);
    return kept.length && rings[0].length >= 4 ? kept : null;
  };
  const features = fc.features.map(f => {
    const g = turf.bboxClip(f, COLORADO_BBOX).geometry;
    const polygons = (g.type === 'Polygon' ? [g.coordinates] : g.coordinates)
      .map(cleanPolygon).filter(Boolean);
    if (!polygons.length) return null;
    const clipped = turf.multiPolygon(polygons, f.properties);
    return turf.area(clipped) > 1 ? clipped : null;
  }).filter(Boolean);
  return turf.featureCollection(features);
}

// One color per ownership type, used on every layer: fills use the lighter step, gas outlines the
// darker step. Validated as a set for color-blind readers (any two side by side) and the darker
// steps all clear 3:1 contrast on the basemap. Gas also differs by dash pattern, so color is
// never the only cue.
const INK = '#3d3d3a';
const OWNERSHIP = {
  iou:     {label: 'Investor-owned', fill: '#2a78d6', ink: '#1c5cab', dash: '8 4'},
  muni:    {label: 'Municipal',      fill: '#1baf7a', ink: '#0f7a55', dash: '3 3'},
  coop:    {label: 'Cooperative',    fill: '#d9e4bf'},
  // Private is a deliberate neutral (near-black, dotted): a 4th hue would fail the color-blind checks.
  private: {label: 'Private',        ink: '#2b2b29', dash: '1 4'}
};
// Electric utilities by ownership. A few out-of-state public power districts and the Navajo Tribal
// Utility Authority cross the border in small slivers; they're grey and not in the legend.
// Fills are 80% opaque: see-through fills wash toward the gray basemap until blue and teal become
// hard to tell apart. Co-ops, the largest category, get a pale sage so they recede and investor-owned
// and municipal territories stand out. Checked as rendered over the basemap.
const ELECTRIC_TYPES = {
  iou: {label: OWNERSHIP.iou.label, color: OWNERSHIP.iou.fill, opacity: 0.8},
  muni: {label: OWNERSHIP.muni.label, color: OWNERSHIP.muni.fill, opacity: 0.8},
  coop: {label: OWNERSHIP.coop.label, color: OWNERSHIP.coop.fill, opacity: 0.8}
};
const OTHER_ELECTRIC = {label: 'Other public power (border area)', color: '#b4b2a9', opacity: 0.4};
// About half the Colorado records have TYPE 'NOT AVAILABLE', so fall back to the utility's name.
function electricType(p) {
  const t = (p.TYPE || '').toUpperCase(), name = (p.NAME || '').toUpperCase();
  if (t === 'INVESTOR OWNED') return 'iou';
  if (t === 'MUNICIPAL' || /^(CITY|TOWN) OF/.test(name)) return 'muni';
  // Carbon Power & Light is a Wyoming co-op whose name doesn't say so.
  if (t === 'COOPERATIVE' || /COOP|ELEC ASSN|ELECTRIC ASSN|CARBON POWER/.test(name)) return 'coop';
  return 'other';
}
const electricStyle = p => ELECTRIC_TYPES[electricType(p)] || OTHER_ELECTRIC;
// Keys that identify the same company in both datasets, whose names are spelled differently
// (e.g. electric "CITY OF TRINIDAD - (CO)" vs gas "TRINIDAD, CITY OF").
function electricCompanyKey(p) {
  const name = (p.NAME || '').toUpperCase();
  if (/XCEL/.test(p.HOLDING_CO || '')) return 'XCEL';
  if (/^BLACK HILLS COLORADO ELECTRIC/.test(name)) return 'BLACK HILLS';
  const muni = name.match(/^(?:CITY|TOWN) OF ([A-Z .]+?)(?:\s*-?\s*\(CO\))?$/);
  return muni ? 'MUNI ' + muni[1].trim() : null;
}
function gasCompanyKey(p) {
  const name = (p.NAME || '').toUpperCase();
  if (/PUBLIC SERVICE CO OF COLORADO/.test(name) || /XCEL/.test(p.HOLDINGCO || '')) return 'XCEL';
  if (/BLACK HILLS/.test(name)) return 'BLACK HILLS';
  if (name === 'COLORADO SPRINGS UTILITIES') return 'MUNI COLORADO SPRINGS';
  const muni = name.match(/^(.+), (?:CITY|TOWN) OF$/) || name.match(/^(.+) MUNICIPAL GAS SYSTEM$/);
  return muni ? 'MUNI ' + muni[1].trim() : null;
}
// Black Hills Colorado Electric and Black Hills Energy (gas) are both owned by Black Hills Corporation.
// Black Hills Colorado Electric and Black Hills Energy (gas) are separate companies with one parent.
const COMPANY_LABELS = {'XCEL': 'Xcel Energy', 'BLACK HILLS': 'Black Hills Corporation'};
// Overlapping service areas are hatched in dark ink so the electric color shows through.
// Hatch direction tells the utilities apart (patterns are defined in the <svg> at the top of <body>).
const OVERLAP_PATTERNS = {
  XCEL: {label: 'Xcel Energy', pattern: 'hatch-45'},
  'BLACK HILLS': {label: 'Black Hills (separate electric and gas companies, same parent)', pattern: 'hatch-135'},
  MUNI: {label: 'Municipal utilities', pattern: 'hatch-cross'}
};
const overlapPattern = key => (key.startsWith('MUNI ') ? OVERLAP_PATTERNS.MUNI : OVERLAP_PATTERNS[key]).pattern;
const companyLabel = key => COMPANY_LABELS[key] || 'City of ' + titleCase(key.replace(/^MUNI /, ''));

const SQ_METERS_PER_SQ_MI = 2589988.11;
const bboxesTouch = (a, b) => a[0] <= b[2] && b[0] <= a[2] && a[1] <= b[3] && b[1] <= a[3];
const polygonsOf = f => (f.geometry.type === 'Polygon' ? [f.geometry.coordinates] : f.geometry.coordinates)
  .map(rings => turf.polygon(rings));

// Intersect each electric territory with each gas territory run by the same company. Where the
// data also puts another electric or gas utility over that area (e.g. Holy Cross and Xcel both
// claim Silt), the area is split off and marked contested, because we can't tell who serves it.
// City-owned utilities are exempt: they serve their own city, and the source data draws co-op and
// other territories straight over towns without cutting them out.
function sameUtilityAreas(electric, gas) {
  const out = [];
  const others = [
    ...electric.features.map(f => ({f, service: 'electric', key: electricCompanyKey(f.properties)})),
    ...gas.features.map(f => ({f, service: 'gas', key: gasCompanyKey(f.properties)}))
  ].map(o => Object.assign(o, {bb: turf.bbox(o.f), name: titleCase(o.f.properties.NAME)}));

  electric.features.forEach(e => {
    const key = electricCompanyKey(e.properties);
    if (!key) return;
    gas.features.filter(g => gasCompanyKey(g.properties) === key).forEach(g => {
      try {
        const overlap = turf.intersect(turf.featureCollection([e, g]));
        if (!overlap) return;
        const bb = turf.bbox(overlap);
        if (key.startsWith('MUNI ')) {
          overlap.properties = {key, contested: false, sqmi: turf.area(overlap) / SQ_METERS_PER_SQ_MI};
          out.push(overlap);
          return;
        }
        const claims = others
          .filter(o => o.key !== key && bboxesTouch(bb, o.bb))
          .map(o => Object.assign({}, o, {piece: turf.intersect(turf.featureCollection([overlap, o.f]))}))
          .filter(o => o.piece && turf.area(o.piece) > 1);
        const contested = claims.length > 1
          ? turf.union(turf.featureCollection(claims.map(c => c.piece)))
          : (claims[0] || {}).piece;
        const clear = contested ? turf.difference(turf.featureCollection([overlap, contested])) : overlap;
        if (clear) {
          clear.properties = {key, contested: false, sqmi: turf.area(clear) / SQ_METERS_PER_SQ_MI};
          out.push(clear);
        }
        if (contested) {
          // Label each separate contested patch with the utilities that cover a real share of it
          // (at least 10% of the patch, or 1 sq mi), not every one that grazes its edge.
          polygonsOf(contested).forEach(patch => {
            const pb = turf.bbox(patch), patchArea = turf.area(patch);
            const shares = claims
              .filter(c => bboxesTouch(pb, turf.bbox(c.piece)))
              .map(c => {
                const shared = turf.intersect(turf.featureCollection([patch, c.piece]));
                return {c, a: shared ? turf.area(shared) : 0};
              })
              .filter(x => x.a > 0)
              .sort((x, y) => y.a - x.a);
            const big = shares.filter(x => x.a >= 0.1 * patchArea || x.a >= SQ_METERS_PER_SQ_MI);
            patch.properties = {
              key, contested: true, sqmi: patchArea / SQ_METERS_PER_SQ_MI,
              claims: [...new Set((big.length ? big : shares.slice(0, 1)).map(x => `${x.c.name} (${x.c.service})`))]
            };
            if (patch.properties.sqmi > 0.01) out.push(patch);
          });
        }
      } catch (err) {
        console.warn('Could not intersect', key, err);
      }
    });
  });
  return turf.featureCollection(out);
}

const titleCase = s => (s || '').toLowerCase().replace(/\b\w/g, c => c.toUpperCase());
// Names and types come from third-party map services; escape them before putting them into the page.
const esc = s => String(s == null ? '' : s).replace(/[&<>"']/g,
  c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));
// Gas utilities by ownership: investor-owned and private utilities are regulated by the Colorado PUC;
// municipal ones are run by their city.
const GAS_TYPES = {
  'INVESTOR-OWNED': {label: OWNERSHIP.iou.label, color: OWNERSHIP.iou.ink, dash: OWNERSHIP.iou.dash},
  'MUNICIPAL': {label: OWNERSHIP.muni.label, color: OWNERSHIP.muni.ink, dash: OWNERSHIP.muni.dash},
  'PRIVATE': {label: OWNERSHIP.private.label, color: OWNERSHIP.private.ink, dash: OWNERSHIP.private.dash}
};
// Fine gas lines; the dotted private line is a little heavier so its dots stay visible.
const gasLineWidth = t => t.dash === OWNERSHIP.private.dash ? 2 : 1.25;
const gasType = p => GAS_TYPES[(p.TYPE || '').toUpperCase()] || {label: titleCase(p.TYPE) || 'Not reported', color: INK, dash: '2 4'};
const fmt = n => (n == null ? 'n/a' : Number(n).toLocaleString());

// Background drawn from public-domain U.S. Census Bureau data instead of a tile provider: no API key,
// no third-party tile terms. It shows state outlines (Colorado lighter), and optionally faint
// interstates and a short list of city names.
const BACKGROUND_CREDIT = 'Background: U.S. Census Bureau';
function addCensusBackground(m, {interstates = false, cities = false} = {}) {
  m.attributionControl.addAttribution(BACKGROUND_CREDIT);
  // Panes: states under everything; interstates just above the utility fills; city names on top.
  m.createPane('base').style.zIndex = 300;

  snapshot('states').then(states => L.geoJSON(states, {
    pane: 'base', interactive: false,
    style: f => f.properties.STUSAB === 'CO'
      ? {color: '#9c9a93', weight: 1.2, fillColor: '#f6f6f3', fillOpacity: 1}
      : {color: '#c9c7c0', weight: 0.8, fillColor: '#ebeae6', fillOpacity: 1}
  }).addTo(m)).catch(() => {});  // without it the map still works on its plain background

  if (interstates) {
    m.createPane('interstates').style.zIndex = 430;
    m.getPane('interstates').style.pointerEvents = 'none';
    snapshot('interstates').then(roads => L.geoJSON(roads, {
      pane: 'interstates', interactive: false, style: {color: '#ffffff', weight: 1.2, opacity: 0.55}
    }).addTo(m)).catch(() => {});
  }

  if (cities) {
    m.createPane('cityLabels').style.zIndex = 660;
    m.getPane('cityLabels').style.pointerEvents = 'none';
    snapshot('cities').then(places => places.features.forEach(f => {
      const at = turf.centerOfMass(f).geometry.coordinates;
      L.marker([at[1], at[0]], {
        pane: 'cityLabels', interactive: false, keyboard: false,
        icon: L.divIcon({className: 'city-label', iconSize: [0, 0], html: `<span>${esc(f.properties.BASENAME)}</span>`})
      }).addTo(m);
    })).catch(() => {});
  }
}

const COLORADO_BOUNDS = [[COLORADO_BBOX[1], COLORADO_BBOX[0]], [COLORADO_BBOX[3], COLORADO_BBOX[2]]];
// Scroll-wheel zoom is off so scrolling the page doesn't get caught by the map;
// the +/- buttons, double-click and pinch still zoom.
const stateMap = L.map('statemap', {scrollWheelZoom: false}).fitBounds(COLORADO_BOUNDS);
addCensusBackground(stateMap, {interstates: true, cities: true});
// County lines sit in their own pane: above the utility layers so the 80% fills don't hide them,
// below the basemap's place names, and never catching clicks meant for the territories.
stateMap.createPane('counties');
stateMap.getPane('counties').style.zIndex = 450;
stateMap.getPane('counties').style.pointerEvents = 'none';
const COUNTY_LINE = '#4a4a46';
const countyLayer = L.geoJSON(null, {
  pane: 'counties', interactive: false,
  style: {color: COUNTY_LINE, weight: 0.9, opacity: 0.75, fill: false}
});
// County names appear once zoomed in far enough to read them without clutter.
const COUNTY_LABEL_MIN_ZOOM = 8;
const countyLabels = L.layerGroup();
function updateCountyLabels() {
  const show = stateMap.hasLayer(countyLayer) && stateMap.getZoom() >= COUNTY_LABEL_MIN_ZOOM;
  if (show) countyLabels.addTo(stateMap); else stateMap.removeLayer(countyLabels);
}
stateMap.on('zoomend', updateCountyLabels);

const electricLayer = L.geoJSON(null, {
  // Thin white borders keep neighboring territories from blending together.
  style: f => ({
    color: '#ffffff', weight: 1, opacity: 0.9,
    fillColor: electricStyle(f.properties).color,
    fillOpacity: electricStyle(f.properties).opacity
  }),
  onEachFeature: (f, layer) => {
    const p = f.properties;
    layer.bindPopup(`<div class="popup"><h3>${esc(titleCase(p.NAME))}</h3><table>
      <tr><td>Service</td><td>Electric</td></tr>
      <tr><td>Ownership</td><td>${esc(electricStyle(p).label)}</td></tr>
      <tr><td>Utility-wide customers (2023)</td><td>${p.CUSTOMERS > 0 ? fmt(p.CUSTOMERS) : 'not reported'}</td></tr></table></div>`);
  }
});
const gasLayer = L.geoJSON(null, {
  style: f => {
    const t = gasType(f.properties);
    // Transparent fill keeps the inside clickable without tinting the electric colors.
    return {color: t.color, weight: gasLineWidth(t), dashArray: t.dash,
            lineCap: 'round', fillColor: t.color, fillOpacity: 0};
  },
  onEachFeature: (f, layer) => {
    const p = f.properties;
    layer.bindPopup(`<div class="popup"><h3>${esc(titleCase(p.NAME))}</h3><table>
      <tr><td>Service</td><td>Gas</td></tr>
      <tr><td>Ownership</td><td>${esc(gasType(p).label)}</td></tr>
      <tr><td>Utility-wide customers</td><td>${p.TOTAL_CUST ? fmt(p.TOTAL_CUST) : 'not reported'}</td></tr></table></div>`);
  }
});

// A white halo under each gas line keeps the dashes readable over any electric fill.
const gasHalo = L.geoJSON(null, {
  interactive: false,
  style: f => ({color: '#ffffff', weight: gasLineWidth(gasType(f.properties)) + 2,
                opacity: 0.9, lineCap: 'round', fill: false})
});

const sameUtilityLayer = L.geoJSON(null, {
  style: f => {
    return f.properties.contested
      ? {color: INK, weight: 1.5, dashArray: '4 3', fillColor: INK, fillOpacity: 0}
      : {color: INK, weight: 1.5, fillColor: `url(#${overlapPattern(f.properties.key)})`, fillOpacity: 1};
  },
  onEachFeature: (f, layer) => {
    const p = f.properties;
    const area = Math.round(p.sqmi) ? fmt(Math.round(p.sqmi)) + ' sq mi' : 'under 1 sq mi';
    layer.bindPopup(p.contested
      ? `<div class="popup"><h3>${esc(companyLabel(p.key))}?</h3><table>
          <tr><td>Status</td><td>Uncertain: the data also lists ${p.claims.map(esc).join(', ')} here</td></tr>
          <tr><td>Area</td><td>${area}</td></tr></table>
          <p style="margin:6px 0 0;color:var(--muted)">Check the utilities' own maps or the Colorado PUC to see who serves this area.</p></div>`
      : `<div class="popup"><h3>${esc(companyLabel(p.key))}</h3><table>
          <tr><td>Service</td><td>${p.key === 'BLACK HILLS'
            ? 'Electric and gas from two companies with the same parent'
            : 'Electric and gas from the same utility'}</td></tr>
          <tr><td>Area</td><td>${area}</td></tr></table></div>`);
  }
});

const status = document.getElementById('state-status');
snapshot('counties')
  .then(counties => {
    countyLayer.addData(counties);
    counties.features.forEach(f => {
      const at = window.turf ? turf.pointOnFeature(f).geometry.coordinates : null;
      if (at) L.marker([at[1], at[0]], {
        pane: 'counties', interactive: false, keyboard: false,
        icon: L.divIcon({className: 'county-label', html: `<span>${esc(f.properties.BASENAME)}</span>`, iconSize: [0, 0]})
      }).addTo(countyLabels);
    });
    showIfChecked('counties');
  })
  .catch(() => setLayerAvailable('counties', false));
Promise.all([snapshot('electric'), snapshot('gas')]).then(([electricRaw, gasRaw]) => {
  const electric = clipToColorado(electricRaw), gas = clipToColorado(gasRaw);
  electricLayer.addData(electric);
  gasLayer.addData(gas);
  gasHalo.addData(gas);
  if (window.turf) {
    const sameAreas = sameUtilityAreas(electric, gas);
    sameUtilityLayer.addData(sameAreas);
    addPilotContext(sameAreas);
    writeOverlapSummary(sameAreas);
  } else {
    status.textContent = 'Could not load the overlap tool, so the same-utility layer is hidden.';
    setLayerAvailable('same', false);
  }
  // Add layers in drawing order (electric fill, gas outlines, same-utility on top), honoring the checkboxes.
  ['electric', 'gas', 'same'].forEach(showIfChecked);
}).catch(() => {
  status.textContent = 'Could not load the utility map data. Reload to try again.';
});

// Fill in each source's last-edit date and the date its copy was saved, from the snapshot manifest.
const longDate = iso => new Date(iso + 'T00:00:00Z')
  .toLocaleDateString('en-US', {year: 'numeric', month: 'long', day: 'numeric', timeZone: 'UTC'});
const manifest = (window.SNAPSHOTS && window.SNAPSHOTS.manifest) || {};
document.querySelectorAll('[data-edited]').forEach(el => {
  const info = manifest[el.dataset.edited];
  if (info && info.source_last_edited) el.textContent = longDate(info.source_last_edited);
});
document.querySelectorAll('[data-saved]').forEach(el => {
  const info = manifest[el.dataset.saved];
  if (info && info.saved_on) el.textContent = longDate(info.saved_on);
});

// Text alternative for the statewide map: overlap area per utility, confirmed and uncertain.
function writeOverlapSummary(sameAreas) {
  const totals = {};
  sameAreas.features.forEach(f => {
    const label = companyLabel(f.properties.key);
    totals[label] = totals[label] || {clear: 0, uncertain: 0};
    totals[label][f.properties.contested ? 'uncertain' : 'clear'] += f.properties.sqmi;
  });
  const sq = n => Math.round(n) >= 1 ? fmt(Math.round(n)) : 'under 1';
  document.getElementById('overlap-summary').innerHTML = Object.entries(totals)
    .sort((a, b) => (b[1].clear + b[1].uncertain) - (a[1].clear + a[1].uncertain))
    .map(([label, t]) => `<li>${esc(label)}: ${sq(t.clear)} sq mi` +
      (t.uncertain >= 0.5 ? `, plus ${sq(t.uncertain)} sq mi uncertain` : '') + '</li>')
    .join('');
}

// The legend doubles as the layer switcher: each section heading has a checkbox.
const STATE_LAYERS = {electric: electricLayer, gas: gasLayer, same: sameUtilityLayer, counties: countyLayer};
const layerToggle = name => document.querySelector(`.legend input[data-layer="${name}"]`);
const HALOS = {gas: gasHalo};
function showIfChecked(name) {
  const box = layerToggle(name), layer = STATE_LAYERS[name], halo = HALOS[name];
  const on = box && box.checked && !box.disabled;
  if (on && layer.getLayers().length) {
    if (halo) halo.addTo(stateMap);
    layer.addTo(stateMap);
  } else {
    stateMap.removeLayer(layer);
    if (halo) stateMap.removeLayer(halo);
  }
  restackLayers();
  updateCountyLabels();
  if (box) box.closest('.group').classList.toggle('off', !on);
}
// Whatever order the checkboxes are clicked in, draw electric fills at the bottom, then the gas
// halo and lines, then the overlapping service areas on top.
function restackLayers() {
  [gasHalo, gasLayer, sameUtilityLayer].forEach(l => { if (stateMap.hasLayer(l)) l.bringToFront(); });
}
function setLayerAvailable(name, available) {
  const box = layerToggle(name);
  if (box) { box.disabled = !available; showIfChecked(name); }
}

// On phone-sized screens the basemap credit wraps onto two lines along the bottom, so the legend goes top right.
const PHONE = window.matchMedia('(max-width: 600px)').matches;
const stateLegend = L.control({position: PHONE ? 'topright' : 'bottomleft'});
stateLegend.onAdd = () => {
  const el = L.DomUtil.create('div', 'legend');
  L.DomEvent.disableClickPropagation(el);
  L.DomEvent.disableScrollPropagation(el);
  // Swatches are tiny SVGs so the legend shows the real fills, dash patterns and hatching.
  const svg = body => `<svg class="swatch" width="24" height="14" viewBox="0 0 24 14" aria-hidden="true">${body}</svg>`;
  const fillSwatch = (color, opacity) =>
    svg(`<rect x="1" y="1" width="22" height="12" rx="2" fill="${color}" fill-opacity="${opacity}" stroke="#fff"/>`);
  const lineSwatch = (color, dash, width) =>
    svg(`<line x1="2" y1="7" x2="22" y2="7" stroke="${color}" stroke-width="${width}" stroke-dasharray="${dash}" stroke-linecap="round"/>`);
  const hatchSwatch = pattern =>
    svg(`<rect x="1" y="1" width="22" height="12" rx="2" fill="url(#${pattern})" stroke="${INK}" stroke-width="1.2"/>`);
  const group = (name, title, rows, checked = true) => `<div class="group">
    <label class="toggle"><input type="checkbox" data-layer="${name}" autocomplete="off"${checked ? ' checked' : ''}><span>${title}</span></label>${rows}</div>`;
  el.innerHTML =
    `<div class="legend-head"><span class="legend-title">Legend</span>
       <button type="button" class="legend-toggle" aria-expanded="true" aria-controls="state-legend-body">Hide legend</button></div>` +
    `<div class="legend-body" id="state-legend-body">` +
    group('electric', 'Electric Utilities',
      Object.values(ELECTRIC_TYPES).map(t =>
        `<div class="row">${fillSwatch(t.color, t.opacity)}${t.label}</div>`).join('')) +
    group('gas', 'Gas Utilities',
      Object.values(GAS_TYPES).map(t =>
        `<div class="row">${lineSwatch(t.color, t.dash, gasLineWidth(t))}${t.label}</div>`).join('')) +
    group('same', 'Overlapping Service Areas',
      Object.values(OVERLAP_PATTERNS).map(o =>
        `<div class="row">${hatchSwatch(o.pattern)}${o.label}</div>`).join('') +
      `<div class="row">${svg(`<rect x="1" y="1" width="22" height="12" rx="2" fill="none" stroke="${INK}" stroke-width="1.2" stroke-dasharray="4 3"/>`)}Uncertain, overlapping utility boundaries</div>`) +
    group('counties', 'County Boundaries',
      `<div class="row">${lineSwatch(COUNTY_LINE, 'none', 1.2)}County line (names show when zoomed in)</div>`, false) +
    `</div>`;
  el.querySelectorAll('input[data-layer]').forEach(box =>
    box.addEventListener('change', () => showIfChecked(box.dataset.layer)));
  // Show/hide button: collapsing keeps the layer checkboxes as they are, it only frees up the map.
  const toggle = el.querySelector('.legend-toggle');
  const setCollapsed = collapsed => {
    el.classList.toggle('collapsed', collapsed);
    toggle.setAttribute('aria-expanded', String(!collapsed));
    toggle.textContent = collapsed ? 'Show legend' : 'Hide legend';
  };
  toggle.addEventListener('click', () => setCollapsed(!el.classList.contains('collapsed')));
  // On phone-sized screens the open legend covers most of the map, so start it collapsed there.
  if (PHONE) setCollapsed(true);
  return el;
};
stateLegend.addTo(stateMap);

// ---- Pilot map: Gas Planning Pilot Program communities (static view) ----
// The five communities the PUC approved in Decision C25-0482. All partner with Xcel; Winter Park's
// electricity comes from Mountain Parks Electric, so only its gas is Xcel's.
const PILOT_COMMUNITIES = {
  'Boulder': 'Front Range', 'Denver': 'Front Range', 'Golden': 'Front Range',
  'Winter Park': 'Mountain', 'Breckenridge': 'Mountain'
};
const PILOT_COLOR = '#6250d6';
// A fixed frame around the five communities: no dragging, zooming or scroll capture.
const pilotMap = L.map('pilotmap', {
  zoomControl: false, dragging: false, scrollWheelZoom: false, doubleClickZoom: false,
  boxZoom: false, keyboard: false, touchZoom: false, attributionControl: true
}).fitBounds([[39.40, -106.20], [40.10, -104.60]]);
// No city names here: the map labels the five communities itself (and draws its own roads below).
addCensusBackground(pilotMap);

// Context: where Xcel provides both electricity and gas (the overlap computed for the statewide map).
const pilotContext = L.geoJSON(null, {
  interactive: false,
  style: {color: '#ffffff', weight: 0.5, fillColor: '#9ec5f4', fillOpacity: 0.55}
}).addTo(pilotMap);
function addPilotContext(sameAreas) {
  pilotContext.addData(sameAreas.features.filter(f => f.properties.key === 'XCEL'));
  pilotContext.bringToBack();
}

// Faint road outlines from the Census Bureau (no names): interstates plus state and US highways.
// They sit above the blue context area and below the pilot communities.
pilotMap.createPane('roads').style.zIndex = 410;
pilotMap.createPane('pilots').style.zIndex = 420;
[{name: 'pilot_roads_primary', weight: 1.6}, {name: 'pilot_roads_secondary', weight: 0.8}].forEach(({name, weight}) => {
  snapshot(name)
    .then(roads => L.geoJSON(roads, {
      pane: 'roads', interactive: false,
      style: {color: '#a3a19a', weight, opacity: 0.4, lineCap: 'round', lineJoin: 'round'}
    }).addTo(pilotMap))
    .catch(() => {});  // roads are decoration; the map still works without them
});

const pilotLayer = L.geoJSON(null, {
  pane: 'pilots', interactive: false,
  style: {color: '#ffffff', weight: 1.5, fillColor: PILOT_COLOR, fillOpacity: 0.85}
}).addTo(pilotMap);
snapshot('pilot_places')
  .then(places => {
    pilotLayer.addData(places);
    places.features.forEach(f => {
      const name = f.properties.BASENAME;
      const c = turf.centerOfMass(f).geometry.coordinates;
      L.marker([c[1], c[0]], {
        interactive: false, keyboard: false,
        icon: L.divIcon({className: 'pilot-label', iconSize: [0, 0],
          html: `<span style="margin-top:16px">${esc(name)}<small>${esc(PILOT_COMMUNITIES[name])}</small></span>`})
      }).addTo(pilotMap);
    });
  })
  .catch(() => {
    document.getElementById('pilot-status').textContent = 'Could not load the pilot community boundaries. Reload to try again.';
  });

const pilotLegend = L.control({position: 'topright'});
pilotLegend.onAdd = () => {
  const el = L.DomUtil.create('div', 'legend');
  el.innerHTML =
    `<div class="row"><svg class="swatch" width="24" height="14" aria-hidden="true"><rect x="1" y="1" width="22" height="12" rx="2" fill="${PILOT_COLOR}" fill-opacity=".85"/></svg>Pilot community (city limits)</div>` +
    `<div class="row"><svg class="swatch" width="24" height="14" aria-hidden="true"><rect x="1" y="1" width="22" height="12" rx="2" fill="#9ec5f4" fill-opacity=".55"/></svg>Xcel provides both gas and electricity</div>`;
  return el;
};
pilotLegend.addTo(pilotMap);

