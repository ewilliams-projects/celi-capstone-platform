// National map: where gas and electric utility territories overlap across the U.S., and who runs them.
// Uses helpers from site.js (snapshot, esc, fmt, titleCase). The shapes are computed ahead of time by
// scripts/build_national_overlap.py, because overlaying the whole country takes too long in a browser.

// One color per relationship. Blues mean one company or parent could move savings between gas and electric;
// orange means two unrelated companies. Uncertain also gets a dashed outline, so color is never the only cue.
const US_CLASSES = {
  same: {label: 'Same utility', color: '#1c5cab',
         about: 'One company provides both gas and electricity'},
  parent: {label: 'Same parent company', color: '#6da7ec',
           about: 'Separate gas and electric companies with one parent'},
  uncertain: {label: 'Uncertain', color: '#c0beb6', dash: '3 3',
              about: 'One of the above, but the data also lists another utility'},
  different: {label: 'Different companies', color: '#eb6834',
              about: 'Gas and electricity come from unrelated companies'},
  no_electric: {label: 'No electric utility listed', color: '#6f6d66',
                about: 'The data lists gas territory here but no retail electric utility'}
};
const US_VIEWS = {
  'Lower 48': [[24.4, -125], [49.5, -66.8]],
  'Alaska': [[58, -170], [71.5, -140]],
  'Hawaii': [[18.8, -160.4], [22.4, -154.6]]
};

const usMap = L.map('usmap', {scrollWheelZoom: false, preferCanvas: true});
usMap.fitBounds(US_VIEWS['Lower 48']);
usMap.attributionControl.addAttribution('Background: Natural Earth');
// Drawing order: land under everything; then the territories (Leaflet's overlay pane, 400); then water, roads
// and state lines on top so they stay visible through the fills; then place names. None of the panes above the
// territories catch clicks.
usMap.createPane('usLand').style.zIndex = 300;
[['usWater', 420], ['usRoads', 430], ['usLines', 440], ['usLabels', 660]].forEach(([name, z]) => {
  const pane = usMap.createPane(name);
  pane.style.zIndex = z;
  pane.style.pointerEvents = 'none';
});

const usNames = names => names.length ? names.map(n => esc(titleCase(n))).join(', ') : 'none listed';
const usLayer = L.geoJSON(null, {
  style: f => {
    const t = US_CLASSES[f.properties.c];
    return {fillColor: t.color, fillOpacity: 0.9, color: t.dash ? '#6b6a64' : '#ffffff',
            weight: t.dash ? 0.5 : 0.3, dashArray: t.dash || null};
  },
  onEachFeature: (f, layer) => {
    const p = f.properties, t = US_CLASSES[p.c];
    layer.bindPopup(`<div class="popup"><h3>${esc(t.label)}${p.by ? ': ' + esc(p.by) : ''}</h3>
      <p style="margin:0 0 4px;color:var(--muted)">${esc(t.about)}.</p><table>
      <tr><td>Gas</td><td>${usNames(p.g)}</td></tr>
      <tr><td>Electric</td><td>${usNames(p.e)}</td></tr></table></div>`);
  }
}).addTo(usMap);

const US_WATER = '#c5d6e2', US_LAND = '#f6f6f3';
// Place names appear as you zoom in. Natural Earth's scalerank says how prominent each city is.
const usCityMinZoom = rank => (rank <= 1 ? 0 : rank <= 3 ? 5 : rank <= 4 ? 6 : rank <= 6 ? 7 : 8);
const US_ROADS_MIN_ZOOM = 6, US_STATE_LABELS_MAX_ZOOM = 6;
const usRoads = L.layerGroup(), usLabels = L.layerGroup(), usLabelList = [];
// Each label's on-screen box: city names start beside their dot, state codes are centered on their point.
function usLabelBox(label, zoom) {
  const p = usMap.project(label.at, zoom), width = label.name.length * 6.5;
  return label.city ? [p.x - 4, p.y - 8, p.x + 8 + width, p.y + 8]
                    : [p.x - width / 2 - 2, p.y - 7, p.x + width / 2 + 2, p.y + 7];
}
const usBoxesTouch = (a, b) => a[0] < b[2] && b[0] < a[2] && a[1] < b[3] && b[1] < a[3];
// Show the most prominent labels first (the list is sorted that way), skipping any that would overlap one
// already shown. Positions only change relative to each other with zoom, so this reruns on zoom alone.
function updateUsBasemap() {
  const zoom = usMap.getZoom(), taken = [];
  usLayerToggle(usRoads, zoom >= US_ROADS_MIN_ZOOM);
  usLabels.clearLayers();
  usLabelList.forEach(label => {
    if (label.city ? zoom < usCityMinZoom(label.rank) : zoom > US_STATE_LABELS_MAX_ZOOM) return;
    const box = usLabelBox(label, zoom);
    if (taken.some(other => usBoxesTouch(box, other))) return;
    taken.push(box);
    usLabels.addLayer(label.marker);
  });
}
const usLayerToggle = (layer, show) => { if (show) layer.addTo(usMap); else usMap.removeLayer(layer); };
function addUsBasemap(basemap) {
  const of = (...kinds) => basemap.features.filter(f => kinds.includes(f.properties.k));
  const add = (kinds, options) => L.geoJSON({type: 'FeatureCollection', features: of(...kinds)},
    Object.assign({interactive: false}, options));
  add(['land'], {pane: 'usLand', style: {color: '#cfcdc6', weight: 0.6, fillColor: '#ebe9e3', fillOpacity: 1}}).addTo(usMap);
  add(['state'], {pane: 'usLand', style: {stroke: false, fillColor: US_LAND, fillOpacity: 1}}).addTo(usMap);
  add(['lake'], {pane: 'usWater', style: {stroke: false, fillColor: US_WATER, fillOpacity: 1}}).addTo(usMap);
  add(['river'], {pane: 'usWater', style: {color: '#8fb0c7', weight: 1, opacity: 0.9}}).addTo(usMap);
  add(['road'], {pane: 'usRoads', style: {color: '#ffffff', weight: 1, opacity: 0.8}}).addTo(usRoads);
  add(['road'], {pane: 'usRoads', style: {color: '#7a7870', weight: 0.5, opacity: 0.8}}).addTo(usRoads);
  add(['state'], {pane: 'usLines', style: {color: '#3d3d3a', weight: 0.8, opacity: 0.7, fill: false}}).addTo(usMap);
  const addLabel = (f, html, className, extra) => {
    const at = [f.geometry.coordinates[1], f.geometry.coordinates[0]];
    usLabelList.push(Object.assign({at, name: f.properties.n, marker: L.marker(at, {
      pane: 'usLabels', interactive: false, keyboard: false, icon: L.divIcon({className, iconSize: [0, 0], html})
    })}, extra));
  };
  of('city').sort((a, b) => a.properties.r - b.properties.r).forEach(f =>
    addLabel(f, `<i></i><span>${esc(f.properties.n)}</span>`, 'us-city-label', {city: true, rank: f.properties.r}));
  of('state_label').forEach(f => addLabel(f, `<span>${esc(f.properties.n)}</span>`, 'us-state-label', {city: false}));
  usLabels.addTo(usMap);
  usMap.on('zoomend', updateUsBasemap);
  updateUsBasemap();
}

// These shapes and the background are several megabytes, so they load only when the map is about to scroll into view.
const usStatus = document.getElementById('us-status');
function loadUsOverlap() {
  usStatus.textContent = 'Loading the national map data\u2026';
  const script = document.createElement('script');
  script.src = 'us-overlap.js';
  script.onload = () => {
    addUsBasemap(window.SNAPSHOTS.us_basemap);
    usLayer.addData(window.SNAPSHOTS.us_overlap);
    usStatus.textContent = '';
  };
  script.onerror = () => { usStatus.textContent = 'Could not load the national map data. Reload to try again.'; };
  document.body.appendChild(script);
}
if (window.IntersectionObserver) {
  const usWatcher = new IntersectionObserver(entries => {
    if (entries.some(e => e.isIntersecting)) {
      usWatcher.disconnect();
      loadUsOverlap();
    }
  }, {rootMargin: '600px'});
  usWatcher.observe(document.getElementById('usmap'));
} else {
  loadUsOverlap();
}

// The key sits above the map rather than on it: at this scale a legend would cover several states.
const usSwatch = t => `<svg class="swatch" width="24" height="14" viewBox="0 0 24 14" aria-hidden="true"><rect x="1" y="1" width="22" height="12" rx="2" fill="${t.color}" stroke="${t.dash ? '#6b6a64' : t.edge || 'none'}"${t.dash ? ` stroke-dasharray="${t.dash}"` : ''}/></svg>`;
document.getElementById('us-key').innerHTML =
  Object.values(US_CLASSES).map(t => `<span class="row">${usSwatch(t)}${esc(t.label)}</span>`).join('') +
  `<span class="row">${usSwatch({color: US_LAND, edge: '#9c9a93'})}No gas territory listed</span>`;

// Buttons above the map jump to Alaska and Hawaii, which sit far outside the main view.
const usViews = document.getElementById('us-views');
Object.keys(US_VIEWS).forEach(name => {
  const button = document.createElement('button');
  button.type = 'button';
  button.textContent = name;
  button.addEventListener('click', () => usMap.fitBounds(US_VIEWS[name]));
  usViews.appendChild(button);
});

// Text alternative: the share of each state's gas territory in each class, from the manifest.
const usInfo = (window.SNAPSHOTS && window.SNAPSHOTS.manifest && window.SNAPSHOTS.manifest.us_overlap) || null;
if (usInfo) {
  const order = Object.keys(US_CLASSES);
  const shown = order.filter(k => k !== 'no_electric');
  const share = (row, key) => {
    const total = order.reduce((sum, k) => sum + (row[k] || 0), 0);
    return total ? `${Math.round(100 * (row[key] || 0) / total)}%` : 'n/a';
  };
  const stateNames = {};
  ((window.SNAPSHOTS.us_states || {}).features || []).forEach(f => { stateNames[f.properties.STUSAB] = f.properties.NAME; });
  const row = (label, values) => `<tr><th scope="row">${esc(label)}</th>` +
    shown.map(k => `<td class="num">${share(values, k)}</td>`).join('') +
    `<td class="num">${fmt(order.reduce((sum, k) => sum + (values[k] || 0), 0))}</td></tr>`;
  document.getElementById('us-table-rows').innerHTML =
    row('United States', usInfo.sq_mi_by_class) +
    Object.entries(usInfo.sq_mi_by_state)
      .sort((a, b) => (stateNames[a[0]] || a[0]).localeCompare(stateNames[b[0]] || b[0]))
      .map(([code, values]) => row(stateNames[code] || code, values)).join('');
}
