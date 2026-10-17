"""Write the ranked results as a CSV table and an interactive map (HTML + Leaflet)."""

import csv
import json
from pathlib import Path
from typing import List

from gasplan.score import ScoredNeighborhood


def write_rankings_csv(scored: List[ScoredNeighborhood], path: Path) -> None:
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "rank", "neighborhood", "priority", "readiness", "equity_flag",
            "infrastructure_age", "momentum", "grid_readiness", "equity_need",
            "gas_replacement_cost", "electrification_cost", "avoided_cost_ratio",
        ])
        for rank, s in enumerate(scored, start=1):
            writer.writerow([
                rank, s.neighborhood.name, round(s.priority, 3), round(s.readiness, 3),
                s.equity_flag,
                *(round(s.factors[k], 3) for k in
                  ("infrastructure_age", "momentum", "grid_readiness", "equity_need")),
                round(s.gas_replacement_cost), round(s.electrification_cost),
                round(s.avoided_cost_ratio, 2),
            ])


def write_map_html(scored: List[ScoredNeighborhood], path: Path, sample_data: bool) -> None:
    rows = [
        {
            "rank": rank,
            "name": s.neighborhood.name,
            "lat": s.neighborhood.lat,
            "lon": s.neighborhood.lon,
            "units": s.neighborhood.housing_units,
            "priority": round(s.priority, 3),
            "readiness": round(s.readiness, 3),
            "equity": s.equity_flag,
            "factors": {k: round(v, 2) for k, v in s.factors.items()},
            "gasCost": s.gas_replacement_cost,
            "elecCost": s.electrification_cost,
            "ratio": round(s.avoided_cost_ratio, 2),
        }
        for rank, s in enumerate(scored, start=1)
    ]
    banner = (
        '<div class="banner">Sample data for demonstration only. '
        "Not real Denver figures.</div>" if sample_data else ""
    )
    html = TEMPLATE.replace("__BANNER__", banner).replace("__DATA__", json.dumps(rows))
    path.write_text(html)


TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Gas Decommissioning Priorities</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script src="https://cdn.jsdelivr.net/npm/@turf/turf@7.1.0/turf.min.js"></script>
<style>
  :root { --ink:#1d2433; --muted:#5b6475; --line:#e3e6ec; --bg:#fafbfc; --accent:#b4441f; }
  * { box-sizing: border-box; }
  body { margin:0; font:14px/1.45 -apple-system, system-ui, sans-serif; color:var(--ink); background:var(--bg); }
  header { padding:16px 20px 8px; }
  h1 { margin:0; font-size:20px; }
  header p { margin:4px 0 0; color:var(--muted); }
  .banner { margin:8px 20px 0; padding:8px 12px; background:#fff4d6; border:1px solid #f0d58a; border-radius:6px; }
  main { display:grid; grid-template-columns: 1fr 420px; gap:16px; padding:16px 20px 20px; }
  #map { height:calc(100vh - 140px); min-height:420px; border-radius:8px; border:1px solid var(--line); }
  .panel { background:#fff; border:1px solid var(--line); border-radius:8px; overflow:auto; max-height:calc(100vh - 140px); }
  table { width:100%; border-collapse:collapse; }
  th, td { padding:7px 10px; border-bottom:1px solid var(--line); text-align:left; }
  th { position:sticky; top:0; background:#fff; font-weight:600; color:var(--muted); font-size:12px; }
  td.num { text-align:right; font-variant-numeric:tabular-nums; }
  tr { cursor:pointer; } tr:hover td { background:#f4f6f9; }
  .tag { display:inline-block; padding:1px 6px; border-radius:10px; background:#fde4da; color:var(--accent); font-size:11px; font-weight:600; }
  .legend { background:#fff; padding:8px 10px; border-radius:6px; border:1px solid var(--line); font-size:12px; }
  .legend .bar { width:160px; height:10px; border-radius:3px; background:linear-gradient(90deg,#fde0c5,#f59e62,#c2410c,#7c2d12); }
  .legend .ends { display:flex; justify-content:space-between; color:var(--muted); }
  .popup h3 { margin:0 0 4px; font-size:15px; }
  .popup table td { padding:2px 6px 2px 0; border:none; }
  .note { margin:4px 20px 0; color:var(--muted); font-size:12px; }
  .note a { color:inherit; }
  #state-status { color:var(--accent); }
  section.state { padding:12px 20px 8px; }
  #statemap { height:560px; border-radius:8px; border:1px solid var(--line); }
  .legend .swatch { display:inline-block; width:14px; height:10px; margin-right:6px; vertical-align:middle; border-radius:2px; }
  .legend .row { margin-top:3px; }
  @media (max-width: 860px) {
    main { grid-template-columns: 1fr; padding:16px; }
    #map { height:60vh; }
    #statemap { height:60vh; }
    section.state { padding:12px 16px 8px; }
    header, .note, .banner { margin-left:16px; margin-right:16px; }
    header { padding-left:0; padding-right:0; }
  }
</style>
</head>
<body>
<header>
  <h1>Colorado utility service territories</h1>
  <p>Where Xcel Energy (Public Service Co. of Colorado) provides electricity, gas, or both.
     Orange and yellow areas get electricity and gas from the same utility. Pale, dashed areas are
     uncertain because the data also lists another utility there.
     Click a territory for details, and use the layer control to switch layers on or off.</p>
</header>
<div class="note">Loaded live. Electric:
  <a href="https://www.arcgis.com/home/item.html?id=597555ce8e4a4892a030784a7c657fdd" target="_blank" rel="noopener">Electric Retail Service Territories</a>
  (federal HIFLD data from Oak Ridge National Laboratory, 2023; public use). Gas:
  <a href="https://geodata.colorado.gov/datasets/47935f56eddd4d1781328c60c8517c96_0/explore" target="_blank" rel="noopener">Gas Utility Service Territories</a>
  (Colorado GeoData).
  <span id="state-status"></span></div>
<section class="state"><div id="statemap"></div></section>

<header>
  <h1>Where to plan neighborhood-scale electrification first</h1>
  <p>Circles show each neighborhood's priority (darker = higher). Circle size shows the number of homes.
     <span class="tag">Equity</span> marks neighborhoods with high renter and low-income shares.</p>
</header>
__BANNER__
<main>
  <div id="map"></div>
  <div class="panel">
    <table>
      <thead><tr><th>#</th><th>Neighborhood</th><th class="num">Priority</th><th class="num">Avoided $ per $1</th></tr></thead>
      <tbody id="rows"></tbody>
    </table>
  </div>
</main>
<script>
// ---- Map 1: statewide electric and gas service territories ----
// Electric: federal HIFLD retail service territories (public use), as kept by the National
// Broadband Availability Map after HIFLD Open shut down. Gas: Colorado GeoData.
const ELECTRIC_URL = 'https://services3.arcgis.com/OYP7N6mAJJCyH6hd/arcgis/rest/services/Electric_Retail_Service_Territories_HIFLD/FeatureServer/0/query';
const GAS_URL = 'https://services3.arcgis.com/DgjqnJA1rgO92Soi/arcgis/rest/services/Gas_Utility_Service_Territories/FeatureServer/0/query';
// Shapes are simplified to about 50 m (0.0005 degrees) so neighboring borders still line up.
const geojsonQuery = (url, fields, extra) => url + '?' + new URLSearchParams(Object.assign({
  where: '1=1', outFields: fields, outSR: '4326', geometryPrecision: '5',
  maxAllowableOffset: '0.0005', f: 'geojson'
}, extra));
// Colorado's border is (almost exactly) a box of latitude and longitude lines.
const COLORADO_BBOX = [-109.0603, 36.9924, -102.0415, 41.0034];  // west, south, east, north
// The national electric layer is filtered to territories that touch Colorado, not to STATE='CO':
// some Colorado providers (e.g. Black Hills Colorado Electric) are listed under out-of-state addresses.
// WAPA and Deseret are left out: they sell wholesale power to utilities, not to homes, and their
// territories are drawn across most of the state underneath the retail utilities.
const ELECTRIC_QUERY = {
  where: "NAME NOT LIKE 'WAPA%' AND NAME NOT LIKE 'DESERET%'",
  geometry: COLORADO_BBOX.join(','), geometryType: 'esriGeometryEnvelope', inSR: '4326',
  spatialRel: 'esriSpatialRelIntersects'
};

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

const ELECTRIC_COLORS = {xcel: '#2563eb', iou: '#93c5fd', muni: '#5eead4', coop: '#d9f99d'};
const ELECTRIC_LABELS = {iou: 'Other investor-owned', muni: 'Municipal', coop: 'Cooperative'};
const isXcelElectric = p => /XCEL/i.test(p.HOLDING_CO || '');
// About half the Colorado records have TYPE 'NOT AVAILABLE', so fall back to the utility's name.
function electricType(p) {
  const t = (p.TYPE || '').toUpperCase(), name = (p.NAME || '').toUpperCase();
  if (t === 'INVESTOR OWNED') return 'iou';
  if (t === 'MUNICIPAL' || /^(CITY|TOWN) OF/.test(name)) return 'muni';
  if (t === 'COOPERATIVE' || /COOP|ELEC ASSN|ELECTRIC ASSN/.test(name)) return 'coop';
  return 'other';
}
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
const COMPANY_LABELS = {'XCEL': 'Xcel Energy', 'BLACK HILLS': 'Black Hills Energy (same parent company)'};
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

const titleCase = s => (s || '').toLowerCase().replace(/\\b\\w/g, c => c.toUpperCase());
const isXcelGas = p => /PUBLIC SERVICE CO/i.test(p.NAME || '') || /XCEL/i.test(p.HOLDINGCO || '');
const fmt = n => (n == null ? 'n/a' : Number(n).toLocaleString());

// Esri basemap tiles work when the page is opened straight from a file
// (OpenStreetMap's servers block those requests). Labels go in their own pane above the data.
const ESRI_TILES = 'https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/';
function addBasemap(m, extraAttribution) {
  L.tileLayer(ESRI_TILES + 'World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}', {
    attribution: 'Tiles &copy; Esri' + (extraAttribution ? ' | ' + extraAttribution : ''), maxZoom: 16
  }).addTo(m);
  m.createPane('labels');
  m.getPane('labels').style.zIndex = 650;
  m.getPane('labels').style.pointerEvents = 'none';
  L.tileLayer(ESRI_TILES + 'World_Light_Gray_Reference/MapServer/tile/{z}/{y}/{x}', {
    pane: 'labels', maxZoom: 16
  }).addTo(m);
}

const COLORADO_BOUNDS = [[COLORADO_BBOX[1], COLORADO_BBOX[0]], [COLORADO_BBOX[3], COLORADO_BBOX[2]]];
const stateMap = L.map('statemap').fitBounds(COLORADO_BOUNDS);
addBasemap(stateMap, 'Electric: HIFLD/ORNL | Gas: Colorado GeoData');
const layerControl = L.control.layers(null, null, {collapsed: false}).addTo(stateMap);

const electricLayer = L.geoJSON(null, {
  style: f => ({
    color: '#475569', weight: 0.6,
    fillColor: isXcelElectric(f.properties) ? ELECTRIC_COLORS.xcel : (ELECTRIC_COLORS[electricType(f.properties)] || '#e2e8f0'),
    fillOpacity: isXcelElectric(f.properties) ? 0.35 : 0.45
  }),
  onEachFeature: (f, layer) => {
    const p = f.properties;
    layer.bindPopup(`<div class="popup"><h3>${titleCase(p.NAME)}</h3><table>
      <tr><td>Service</td><td>Electric</td></tr>
      <tr><td>Type</td><td>${isXcelElectric(p) ? 'Investor-owned (Xcel Energy)' : (ELECTRIC_LABELS[electricType(p)] || 'Not reported')}</td></tr>
      <tr><td>Customers</td><td>${p.CUSTOMERS > 0 ? fmt(p.CUSTOMERS) : 'not reported'}</td></tr></table></div>`);
  }
});
const gasLayer = L.geoJSON(null, {
  style: f => isXcelGas(f.properties)
    ? {color: '#7c3aed', weight: 2.5, dashArray: '6 4', fillColor: '#7c3aed', fillOpacity: 0.12}
    : {color: '#6b7280', weight: 1.5, dashArray: '4 4', fillColor: '#6b7280', fillOpacity: 0.08},
  onEachFeature: (f, layer) => {
    const p = f.properties;
    layer.bindPopup(`<div class="popup"><h3>${p.NAME}</h3><table>
      <tr><td>Service</td><td>Gas</td></tr>
      <tr><td>Type</td><td>${p.TYPE}${isXcelGas(p) ? ' (Xcel Energy)' : ''}</td></tr>
      <tr><td>Total customers</td><td>${p.TOTAL_CUST ? fmt(p.TOTAL_CUST) : 'not reported'}</td></tr></table></div>`);
  }
});

const sameUtilityLayer = L.geoJSON(null, {
  style: f => {
    const fill = f.properties.key === 'XCEL' ? '#f97316' : '#facc15';
    return f.properties.contested
      ? {color: '#9a3412', weight: 1.5, dashArray: '3 3', fillColor: fill, fillOpacity: 0.2}
      : {color: '#9a3412', weight: 1.5, fillColor: fill, fillOpacity: 0.65};
  },
  onEachFeature: (f, layer) => {
    const p = f.properties;
    const area = Math.round(p.sqmi) ? fmt(Math.round(p.sqmi)) + ' sq mi' : 'under 1 sq mi';
    layer.bindPopup(p.contested
      ? `<div class="popup"><h3>${companyLabel(p.key)}?</h3><table>
          <tr><td>Status</td><td>Uncertain: the data also lists ${p.claims.join(', ')} here</td></tr>
          <tr><td>Area</td><td>${area}</td></tr></table>
          <p style="margin:6px 0 0;color:var(--muted)">Check the utilities' own maps or the Colorado PUC to see who serves this area.</p></div>`
      : `<div class="popup"><h3>${companyLabel(p.key)}</h3><table>
          <tr><td>Service</td><td>Electric and gas from the same utility</td></tr>
          <tr><td>Area</td><td>${area}</td></tr></table></div>`);
  }
});

const status = document.getElementById('state-status');
Promise.all([
  fetch(geojsonQuery(ELECTRIC_URL, 'NAME,TYPE,CUSTOMERS,HOLDING_CO', ELECTRIC_QUERY)).then(r => r.json()),
  fetch(geojsonQuery(GAS_URL, 'NAME,HOLDINGCO,TYPE,TOTAL_CUST')).then(r => r.json())
]).then(([electricRaw, gasRaw]) => {
  const electric = clipToColorado(electricRaw), gas = clipToColorado(gasRaw);
  electricLayer.addData(electric).addTo(stateMap);
  gasLayer.addData(gas).addTo(stateMap);
  layerControl.addOverlay(electricLayer, 'Electric utilities (fill)');
  layerControl.addOverlay(gasLayer, 'Gas utilities (dashed outline)');
  if (window.turf) {
    sameUtilityLayer.addData(sameUtilityAreas(electric, gas)).addTo(stateMap);
    layerControl.addOverlay(sameUtilityLayer, 'Same electric &amp; gas utility');
  } else {
    status.textContent = 'Could not load the overlap tool, so the same-utility layer is hidden.';
  }
}).catch(() => {
  status.textContent = 'Could not load the utility layers. Check your internet connection and reload.';
});

const stateLegend = L.control({position: 'bottomleft'});
stateLegend.onAdd = () => {
  const el = L.DomUtil.create('div', 'legend');
  const sw = (c, extra) => `<span class="swatch" style="background:${c};${extra || ''}"></span>`;
  el.innerHTML = '<b>Electric</b>' +
    `<div class="row">${sw(ELECTRIC_COLORS.xcel, 'opacity:.6')}Xcel Energy</div>` +
    Object.entries(ELECTRIC_LABELS).map(([k, v]) => `<div class="row">${sw(ELECTRIC_COLORS[k])}${v}</div>`).join('') +
    '<b style="display:block;margin-top:6px">Gas</b>' +
    `<div class="row">${sw('transparent', 'border:2px dashed #7c3aed')}Xcel Energy</div>` +
    `<div class="row">${sw('transparent', 'border:2px dashed #6b7280')}Other gas utility</div>` +
    '<b style="display:block;margin-top:6px">Same utility for both</b>' +
    `<div class="row">${sw('#f97316')}Xcel Energy</div>` +
    `<div class="row">${sw('#facc15')}Other utility</div>` +
    `<div class="row">${sw('rgba(249,115,22,.2)', 'border:1.5px dashed #9a3412')}Uncertain, overlapping utility boundaries</div>`;
  return el;
};
stateLegend.addTo(stateMap);

// ---- Map 2: neighborhood priorities ----
const DATA = __DATA__;
const money = v => '$' + (v / 1e6).toFixed(1) + 'M';
const ramp = ['#fde0c5', '#f59e62', '#c2410c', '#7c2d12'];
const max = Math.max(...DATA.map(d => d.priority)), min = Math.min(...DATA.map(d => d.priority));
const color = p => ramp[Math.min(3, Math.floor(((p - min) / ((max - min) || 1)) * 4))];

const map = L.map('map').setView([39.73, -104.95], 11);
addBasemap(map);

const labels = {infrastructure_age: 'Infrastructure age', momentum: 'Electrification momentum',
                grid_readiness: 'Grid readiness', equity_need: 'Equity need'};
const markers = {};
DATA.forEach(d => {
  const factors = Object.entries(d.factors)
    .map(([k, v]) => `<tr><td>${labels[k]}</td><td>${v.toFixed(2)}</td></tr>`).join('');
  const popup = `<div class="popup"><h3>#${d.rank} ${d.name} ${d.equity ? '<span class="tag">Equity</span>' : ''}</h3>
    <table>${factors}
      <tr><td><b>Priority score</b></td><td><b>${d.priority.toFixed(2)}</b></td></tr>
      <tr><td>Gas main replacement</td><td>${money(d.gasCost)}</td></tr>
      <tr><td>Electrify all ${d.units.toLocaleString()} homes</td><td>${money(d.elecCost)}</td></tr>
    </table></div>`;
  markers[d.name] = L.circleMarker([d.lat, d.lon], {
    radius: 6 + Math.sqrt(d.units) / 8, color: d.equity ? '#1d2433' : '#fff',
    weight: d.equity ? 2.5 : 1, fillColor: color(d.priority), fillOpacity: 0.85
  }).bindPopup(popup).bindTooltip(d.name).addTo(map);

  const tr = document.createElement('tr');
  tr.innerHTML = `<td>${d.rank}</td><td>${d.name} ${d.equity ? '<span class="tag">Equity</span>' : ''}</td>
    <td class="num">${d.priority.toFixed(2)}</td><td class="num">$${d.ratio.toFixed(2)}</td>`;
  tr.onclick = () => { map.setView([d.lat, d.lon], 13); markers[d.name].openPopup(); };
  document.getElementById('rows').appendChild(tr);
});

const legend = L.control({position: 'bottomleft'});
legend.onAdd = () => {
  const el = L.DomUtil.create('div', 'legend');
  el.innerHTML = '<b>Priority</b><div class="bar"></div><div class="ends"><span>Lower</span><span>Higher</span></div>';
  return el;
};
legend.addTo(map);
</script>
</body>
</html>
"""
