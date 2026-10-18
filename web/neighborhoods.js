// Draft only, never published: the neighborhood priority map. Built into output/neighborhoods.html,
// with the scored neighborhoods in neighborhood-data.js (const DATA). Uses helpers from site.js.
// ---- Map 2: neighborhood priorities ----
const money = v => '$' + (v / 1e6).toFixed(1) + 'M';
// Ordinal steps of the sequential blue ramp: the lightest step still clears 2:1 on the gray basemap.
const ramp = ['#6da7ec', '#3987e5', '#1c5cab', '#0d366b'];
const max = Math.max(...DATA.map(d => d.priority)), min = Math.min(...DATA.map(d => d.priority));
const color = p => ramp[Math.min(3, Math.floor(((p - min) / ((max - min) || 1)) * 4))];

const map = L.map('map').setView([39.73, -104.95], 11);
addCensusBackground(map, {interstates: true});

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
    radius: 6 + Math.sqrt(d.units) / 8, color: d.equity ? '#0b0b0b' : '#fff',
    weight: d.equity ? 3 : 1.5, fillColor: color(d.priority), fillOpacity: 0.9
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
