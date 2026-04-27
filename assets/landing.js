// Tiny sparkline renderer + table builder for landing pages.
function miniSpark(series) {
  const w = 120, h = 28;
  if (!series || !series.length) return "";
  const max = Math.max(1, ...series);
  let path = "";
  for (let i = 0; i < series.length; i++) {
    const x = (i / Math.max(1, series.length - 1)) * w;
    const y = h - (series[i] / max) * (h - 2) - 1;
    path += (i === 0 ? "M" : "L") + x.toFixed(1) + "," + y.toFixed(1);
  }
  return `<svg viewBox="0 0 ${w} ${h}" preserveAspectRatio="none" class="spark"><path class="line" d="${path}"/></svg>`;
}

async function renderLandingTable(kind, target) {
  const r = await fetch(`${NameVitals.BASE}data/landing/${kind}.json`);
  const { yM, rows } = await r.json();
  const fmt = NameVitals.fmt;

  const headers = {
    extinct: `<tr><th>Name</th><th class="num">Peak year</th><th class="num">Peak</th><th class="num">Last year on record</th><th>Trajectory</th><th></th></tr>`,
    endangered: `<tr><th>Name</th><th class="num">Peak year</th><th class="num">Peak</th><th class="num">${yM}</th><th class="num">Decline</th><th>Trajectory</th><th></th></tr>`,
    rising: `<tr><th>Name</th><th class="num">${yM}</th><th class="num">Prev decade</th><th class="num">This decade</th><th class="num">Growth</th><th>Trajectory</th><th></th></tr>`,
  }[kind];

  const row = (r) => {
    const linkTo = `${NameVitals.BASE}?name=${encodeURIComponent(r.name)}&sex=${r.sex}`;
    const spark = `<td class="sparkcell">${miniSpark(r.series)}</td>`;
    const cta = `<td><a href="${linkTo}">Details →</a></td>`;
    if (kind === "extinct") {
      return `<tr>
        <td><a href="${linkTo}">${r.name}</a> <span class="meta">${r.sex}</span></td>
        <td class="num">${r.peakYear}</td>
        <td class="num">${fmt(r.peakCount)}</td>
        <td class="num">${r.lastYearSeen}</td>
        ${spark}${cta}
      </tr>`;
    }
    if (kind === "endangered") {
      return `<tr>
        <td><a href="${linkTo}">${r.name}</a> <span class="meta">${r.sex}</span></td>
        <td class="num">${r.peakYear}</td>
        <td class="num">${fmt(r.peakCount)}</td>
        <td class="num">${fmt(r.latestCount)}</td>
        <td class="num">−${r.declinePct}%</td>
        ${spark}${cta}
      </tr>`;
    }
    return `<tr>
      <td><a href="${linkTo}">${r.name}</a> <span class="meta">${r.sex}</span></td>
      <td class="num">${fmt(r.latestCount)}</td>
      <td class="num">${fmt(r.prevDecadeTotal)}</td>
      <td class="num">${fmt(r.currDecadeTotal)}</td>
      <td class="num">${r.growthX ? r.growthX + "×" : "—"}</td>
      ${spark}${cta}
    </tr>`;
  };

  target.innerHTML = `<table class="table"><thead>${headers}</thead><tbody>${rows.map(row).join("")}</tbody></table>`;
}

window.renderLandingTable = renderLandingTable;
