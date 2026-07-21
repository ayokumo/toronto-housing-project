"""
Toronto Shelter System — Interactive Geographic Map (Enhanced)
"""

from pathlib import Path
import json
import math
import duckdb
import pandas as pd

DB_PATH = Path("data/toronto_housing.duckdb")
OUT_DIR = Path("analysis/outputs")
OUT_DIR.mkdir(parents=True, exist_ok=True)

FSA_COORDS = {
    "M1B": (43.793, -79.251), "M1C": (43.784, -79.236),
    "M1E": (43.765, -79.249), "M1G": (43.771, -79.218),
    "M1H": (43.773, -79.239), "M1J": (43.744, -79.231),
    "M1K": (43.728, -79.261), "M1L": (43.712, -79.285),
    "M1M": (43.716, -79.234), "M1N": (43.693, -79.260),
    "M1P": (43.757, -79.273), "M1R": (43.751, -79.299),
    "M1S": (43.794, -79.263), "M1T": (43.786, -79.284),
    "M1V": (43.816, -79.252), "M1W": (43.796, -79.270),
    "M1X": (43.836, -79.205), "M2H": (43.803, -79.363),
    "M2J": (43.778, -79.349), "M2K": (43.786, -79.385),
    "M2L": (43.757, -79.374), "M2M": (43.789, -79.408),
    "M2N": (43.770, -79.413), "M2P": (43.752, -79.389),
    "M2R": (43.782, -79.442), "M3A": (43.753, -79.329),
    "M3B": (43.745, -79.352), "M3C": (43.725, -79.340),
    "M3H": (43.754, -79.442), "M3J": (43.767, -79.488),
    "M3K": (43.737, -79.465), "M3L": (43.739, -79.507),
    "M3M": (43.728, -79.495), "M3N": (43.761, -79.521),
    "M4A": (43.726, -79.314), "M4B": (43.706, -79.309),
    "M4C": (43.695, -79.318), "M4E": (43.677, -79.296),
    "M4G": (43.707, -79.363), "M4H": (43.697, -79.357),
    "M4J": (43.685, -79.337), "M4K": (43.680, -79.352),
    "M4L": (43.669, -79.316), "M4M": (43.659, -79.340),
    "M4N": (43.728, -79.390), "M4P": (43.712, -79.392),
    "M4R": (43.720, -79.407), "M4S": (43.704, -79.398),
    "M4T": (43.690, -79.383), "M4V": (43.686, -79.400),
    "M4W": (43.679, -79.376), "M4X": (43.668, -79.362),
    "M4Y": (43.666, -79.383), "M5A": (43.655, -79.354),
    "M5B": (43.657, -79.378), "M5C": (43.651, -79.375),
    "M5E": (43.644, -79.373), "M5G": (43.657, -79.387),
    "M5H": (43.649, -79.383), "M5J": (43.641, -79.381),
    "M5K": (43.648, -79.382), "M5L": (43.648, -79.378),
    "M5M": (43.733, -79.419), "M5N": (43.711, -79.419),
    "M5P": (43.696, -79.411), "M5R": (43.672, -79.408),
    "M5S": (43.662, -79.400), "M5T": (43.653, -79.400),
    "M5V": (43.643, -79.396), "M5X": (43.648, -79.381),
    "M6A": (43.718, -79.444), "M6B": (43.709, -79.444),
    "M6C": (43.693, -79.430), "M6E": (43.689, -79.453),
    "M6G": (43.669, -79.422), "M6H": (43.660, -79.436),
    "M6J": (43.648, -79.420), "M6K": (43.637, -79.420),
    "M6L": (43.714, -79.487), "M6M": (43.691, -79.480),
    "M6N": (43.673, -79.494), "M6P": (43.661, -79.464),
    "M6R": (43.648, -79.456), "M6S": (43.651, -79.484),
    "M7A": (43.662, -79.389), "M8V": (43.607, -79.496),
    "M8W": (43.602, -79.544), "M8X": (43.653, -79.511),
    "M8Y": (43.636, -79.498), "M8Z": (43.622, -79.523),
    "M9A": (43.665, -79.532), "M9B": (43.651, -79.556),
    "M9C": (43.643, -79.579), "M9L": (43.757, -79.551),
    "M9M": (43.724, -79.537), "M9N": (43.706, -79.518),
    "M9P": (43.697, -79.541), "M9R": (43.689, -79.566),
    "M9V": (43.740, -79.587), "M9W": (43.707, -79.591),
}

def get_shelter_data():
    con = duckdb.connect(str(DB_PATH))
    df = con.execute("""
        SELECT
            f.location_name, f.location_address, f.location_postal_code,
            f.sector, f.organization_name,
            ROUND(AVG(f.occupancy_rate), 1) AS avg_occupancy_rate,
            ROUND(AVG(f.occupancy), 0) AS avg_daily_occupied,
            ROUND(AVG(f.capacity_actual), 0) AS avg_capacity,
            COUNT(*) FILTER (WHERE f.is_effectively_full) AS days_full,
            COUNT(*) AS total_days,
            ROUND(COUNT(*) FILTER (WHERE f.is_effectively_full)::FLOAT
                / NULLIF(COUNT(*), 0) * 100, 1) AS pct_days_full
        FROM main_marts.fact_shelter_daily f
        WHERE f.year_number >= 2023
            AND f.occupancy_rate IS NOT NULL
            AND f.location_address IS NOT NULL
        GROUP BY f.location_name, f.location_address,
            f.location_postal_code, f.sector, f.organization_name
        HAVING COUNT(*) > 30
        ORDER BY avg_occupancy_rate DESC
    """).df()
    con.close()
    return df

def resolve_coords(postal):
    fsa = str(postal).strip().upper()[:3] if postal else ""
    return FSA_COORDS.get(fsa, (43.6532, -79.3832))

def stress_color(rate):
    if rate >= 98: return "#e63946"
    if rate >= 95: return "#f4a261"
    if rate >= 85: return "#e9c46a"
    return "#2a9d8f"

def bubble_radius(capacity):
    if not capacity or capacity <= 0: return 7
    return max(6, min(22, 6 + math.sqrt(float(capacity) / 5)))

def build_html(df):
    shelters = []
    for _, r in df.iterrows():
        lat, lon = resolve_coords(r["location_postal_code"])
        shelters.append({
            "name": r["location_name"],
            "org": r["organization_name"],
            "address": r["location_address"],
            "sector": str(r["sector"]).strip().upper() if r["sector"] else "OTHER",
            "occ_rate": float(r["avg_occupancy_rate"] or 0),
            "avg_occupied": int(r["avg_daily_occupied"] or 0),
            "avg_capacity": int(r["avg_capacity"] or 0),
            "pct_full": float(r["pct_days_full"] or 0),
            "lat": lat, "lon": lon,
            "color": stress_color(float(r["avg_occupancy_rate"] or 0)),
            "radius": bubble_radius(float(r["avg_capacity"] or 0)),
        })

    total   = len(df)
    at_95   = int((df["avg_occupancy_rate"] >= 95).sum())
    sys_avg = round(df["avg_occupancy_rate"].mean(), 1)
    sj      = json.dumps(shelters)

    return f"""<!DOCTYPE html>
<html lang="en"><head>
<meta charset="UTF-8"/>
<title>Toronto Shelter Occupancy Map</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:'Segoe UI',Arial,sans-serif;background:#0f1117;color:#e0e0e0;display:flex;height:100vh;overflow:hidden}}
#sidebar{{width:310px;min-width:280px;background:#16181f;display:flex;flex-direction:column;z-index:1000;border-right:1px solid #2a2d3a}}
#sidebar-header{{padding:16px;border-bottom:1px solid #2a2d3a}}
#sidebar-header h1{{font-size:14px;font-weight:700;color:#fff;line-height:1.4}}
#sidebar-header p{{font-size:11px;color:#666;margin-top:3px}}
#sys-stats{{padding:12px 16px;border-bottom:1px solid #2a2d3a;display:grid;grid-template-columns:1fr 1fr;gap:8px}}
.stat-box{{background:#1e2130;border-radius:6px;padding:10px 12px}}
.stat-box .val{{font-size:20px;font-weight:700;color:#fff;line-height:1}}
.stat-box .lbl{{font-size:10px;color:#666;margin-top:3px;text-transform:uppercase;letter-spacing:.05em}}
.stat-box.red .val{{color:#e63946}}
.stat-box.amber .val{{color:#e9c46a}}
#filters{{padding:10px 16px;border-bottom:1px solid #2a2d3a}}
#filters p{{font-size:10px;color:#666;text-transform:uppercase;letter-spacing:.05em;margin-bottom:6px}}
.filter-row{{display:flex;flex-wrap:wrap;gap:4px}}
.fbtn{{padding:3px 9px;border-radius:20px;border:1px solid #3a3d4a;background:#1e2130;color:#888;font-size:11px;cursor:pointer;transition:all .15s}}
.fbtn.active{{background:#2c7bb6;border-color:#2c7bb6;color:#fff}}
#legend{{padding:10px 16px;border-bottom:1px solid #2a2d3a}}
#legend p{{font-size:10px;color:#666;text-transform:uppercase;letter-spacing:.05em;margin-bottom:6px}}
.leg-row{{display:flex;align-items:center;gap:8px;margin-bottom:4px;font-size:11px;color:#aaa}}
.leg-dot{{width:11px;height:11px;border-radius:50%;flex-shrink:0}}
#detail{{flex:1;padding:12px 16px;overflow-y:auto}}
#detail-placeholder{{color:#444;font-size:12px;line-height:1.6;margin-top:6px}}
#detail-content{{display:none}}
#detail-content h2{{font-size:13px;font-weight:700;color:#fff;margin-bottom:3px;line-height:1.3}}
#detail-content .org{{font-size:11px;color:#666;margin-bottom:10px}}
.dstat{{display:flex;justify-content:space-between;align-items:center;padding:6px 0;border-bottom:1px solid #2a2d3a;font-size:12px}}
.dstat .dl{{color:#666}}.dstat .dv{{color:#fff;font-weight:600}}
.occ-wrap{{margin-top:10px}}
.occ-labels{{display:flex;justify-content:space-between;font-size:10px;color:#555;margin-bottom:3px}}
.occ-bar{{height:7px;background:#2a2d3a;border-radius:4px;overflow:hidden}}
.occ-fill{{height:100%;border-radius:4px;transition:width .4s}}
#map{{flex:1}}
</style></head><body>
<div id="sidebar">
  <div id="sidebar-header">
    <h1>Toronto Shelter System<br>Occupancy Stress Map</h1>
    <p>2023–2026 &middot; avg occupancy by program</p>
  </div>
  <div id="sys-stats">
    <div class="stat-box red"><div class="val">{sys_avg}%</div><div class="lbl">System avg occupancy</div></div>
    <div class="stat-box amber"><div class="val">{at_95}/{total}</div><div class="lbl">Programs &ge;95% full</div></div>
  </div>
  <div id="filters">
    <p>Filter by sector</p>
    <div class="filter-row">
      <button class="fbtn active" onclick="filterSector('ALL')">All</button>
      <button class="fbtn" onclick="filterSector('MEN')">Men</button>
      <button class="fbtn" onclick="filterSector('WOMEN')">Women</button>
      <button class="fbtn" onclick="filterSector('YOUTH')">Youth</button>
      <button class="fbtn" onclick="filterSector('FAMILIES')">Families</button>
      <button class="fbtn" onclick="filterSector('MIXED ADULT')">Mixed</button>
      <button class="fbtn" onclick="filterSector('CO-ED')">Co-ed</button>
    </div>
  </div>
  <div id="legend">
    <p>Avg occupancy rate</p>
    <div class="leg-row"><div class="leg-dot" style="background:#e63946"></div>&ge;98% Critical</div>
    <div class="leg-row"><div class="leg-dot" style="background:#f4a261"></div>95–98% Effectively full</div>
    <div class="leg-row"><div class="leg-dot" style="background:#e9c46a"></div>85–95% High</div>
    <div class="leg-row"><div class="leg-dot" style="background:#2a9d8f"></div>&lt;85% Moderate</div>
    <div class="leg-row" style="color:#444;font-size:10px;margin-top:4px">Bubble size &prop; shelter capacity</div>
  </div>
  <div id="detail">
    <div id="detail-placeholder">&larr; Click any bubble to see shelter details</div>
    <div id="detail-content">
      <h2 id="d-name"></h2>
      <div class="org" id="d-org"></div>
      <div class="dstat"><span class="dl">Sector</span><span class="dv" id="d-sector"></span></div>
      <div class="dstat"><span class="dl">Avg occupancy</span><span class="dv" id="d-rate"></span></div>
      <div class="dstat"><span class="dl">Avg daily occupied</span><span class="dv" id="d-occ"></span></div>
      <div class="dstat"><span class="dl">Avg capacity</span><span class="dv" id="d-cap"></span></div>
      <div class="dstat"><span class="dl">Days at &ge;95%</span><span class="dv" id="d-pct"></span></div>
      <div class="dstat" style="border:none"><span class="dl">Address</span><span class="dv" id="d-addr" style="font-size:10px;text-align:right;max-width:60%"></span></div>
      <div class="occ-wrap">
        <div class="occ-labels"><span>0%</span><span>100%</span></div>
        <div class="occ-bar"><div class="occ-fill" id="d-bar" style="width:0%"></div></div>
      </div>
    </div>
  </div>
</div>
<div id="map"></div>
<script>
const SHELTERS={sj};
const map=L.map('map',{{center:[43.686,-79.383],zoom:13}});
L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{{z}}/{{y}}/{{x}}',{{attribution:'Tiles &copy; Esri',maxZoom:19}}).addTo(map);
L.tileLayer('https://{{s}}.basemaps.cartocdn.com/dark_only_labels/{{z}}/{{x}}/{{y}}{{r}}.png',{{attribution:'&copy; CARTO',subdomains:'abcd',maxZoom:19,opacity:1.0}}).addTo(map);
let markers=[];
function drawMarkers(sector){{
  markers.forEach(m=>map.removeLayer(m));markers=[];
  SHELTERS.forEach(s=>{{
    if(sector!=='ALL'&&s.sector!==sector)return;
    const m=L.circleMarker([s.lat,s.lon],{{radius:s.radius,color:s.color,fillColor:s.color,fillOpacity:0.82,weight:1.5}}).addTo(map);
    m.bindTooltip('<b>'+s.name+'</b><br>'+s.occ_rate+'% avg occupancy',{{direction:'top',className:'dtip'}});
    m.on('click',()=>showDetail(s));
    markers.push(m);
  }});
}}
function filterSector(sector){{
  document.querySelectorAll('.fbtn').forEach(b=>b.classList.remove('active'));
  event.target.classList.add('active');
  drawMarkers(sector);
}}
function showDetail(s){{
  document.getElementById('detail-placeholder').style.display='none';
  document.getElementById('detail-content').style.display='block';
  document.getElementById('d-name').textContent=s.name;
  document.getElementById('d-org').textContent=s.org;
  document.getElementById('d-sector').textContent=s.sector.charAt(0)+s.sector.slice(1).toLowerCase();
  document.getElementById('d-rate').textContent=s.occ_rate+'%';
  document.getElementById('d-occ').textContent=s.avg_occupied+' beds/rooms';
  document.getElementById('d-cap').textContent=s.avg_capacity+' beds/rooms';
  document.getElementById('d-pct').textContent=s.pct_full+'% of days';
  document.getElementById('d-addr').textContent=s.address;
  const bar=document.getElementById('d-bar');
  bar.style.width=Math.min(s.occ_rate,100)+'%';
  bar.style.background=s.color;
}}
drawMarkers('ALL');
const st=document.createElement('style');
st.textContent='.dtip{{background:#1e2130;border:1px solid #3a3d4a;color:#eee;font-size:12px;padding:5px 9px;border-radius:4px}}.dtip::before{{display:none}}';
document.head.appendChild(st);
</script></body></html>"""

def main():
    print("Loading shelter data...")
    df = get_shelter_data()
    print(f"  {len(df)} programs, {(df['avg_occupancy_rate']>=95).sum()} at 95%+")
    print("Building map...")
    html = build_html(df)
    out = OUT_DIR / "shelter_map.html"
    out.write_text(html, encoding="utf-8")
    print(f"Saved: {out}")

if __name__ == "__main__":
    main()
