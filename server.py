"""Fresnel Biprism Simulator - HTML + Python only (no JavaScript, no installs).

Run:     python server.py          -> opens http://localhost:8000 in your browser
Export:  python server.py export   -> writes a standalone simulator.html (default values)

Python does all the physics and draws every picture (SVG).
The HTML page is a form: move the sliders, then press "Update".
"""
import math, sys, webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs

WIN = 3.0                      # screen window shown, in mm
LIMITS = {                     # name: (min, max, default, step, label)
    "lam":   (380, 750, 589, 1,    "Wavelength λ (nm)"),
    "alpha": (0.1, 1.0, 0.5, 0.01, "Biprism angle α (degrees)"),
    "u":     (10, 40, 20, 1,       "Slit to biprism u (cm)"),
    "v":     (30, 150, 100, 1,     "Biprism to screen v (cm)"),
    "mu":    (1.4, 1.7, 1.5, 0.01, "Glass index μ"),
    "t":     (0, 5, 0, 0.05,       "Thin film thickness t (µm)"),
}
FILM_N = 1.38                  # refractive index of the biological film


# ---------------------------------------------------------------- physics
def wavelength_to_rgb(nm):
    r = g = b = 0.0
    if nm < 440:   r, b = (440 - nm) / 60, 1
    elif nm < 490: g, b = (nm - 440) / 50, 1
    elif nm < 510: g, b = 1, (510 - nm) / 20
    elif nm < 580: r, g = (nm - 510) / 70, 1
    elif nm < 645: r, g = 1, (645 - nm) / 65
    else:          r = 1
    f = 0.3 + 0.7 * (nm - 380) / 40 if nm < 420 else 0.3 + 0.7 * (750 - nm) / 50 if nm > 700 else 1
    return [255 * (c * f) ** 0.8 for c in (r, g, b)]


def physics(p):
    lam = p["lam"] * 1e-9
    a = math.radians(p["alpha"])          # degrees -> radians
    u, v = p["u"] / 100, p["v"] / 100     # cm -> m
    d = 2 * u * (p["mu"] - 1) * a         # d = 2u(mu-1)alpha
    D = u + v                             # D = u + v
    beta = lam * D / d                    # beta = lambda D / d
    N = (FILM_N - 1) * p["t"] * 1e-6 / lam    # fringe shift from a thin film
    return dict(d=d * 1e3, D=D * 100, beta=beta * 1e3, N=N, shift=N * beta * 1e3)


def intensity(x_mm, beta_mm, shift_mm):
    return math.cos(math.pi * (x_mm - shift_mm) / beta_mm) ** 2   # I = I0 cos^2(pi x / beta)


# ---------------------------------------------------------------- drawings
def fringe_strip(beta, shift, nm, n=600, width=900, height=100, y=0):
    col = wavelength_to_rgb(nm)
    w = width / n
    out = []
    for i in range(n):
        I = sum(intensity(((i + k / 4) / n - 0.5) * WIN, beta, shift) for k in range(4)) / 4
        c = ",".join(str(int(v * I)) for v in col)
        out.append(f'<rect x="{i*w:.2f}" y="{y}" width="{w+0.6:.2f}" height="{height}" fill="rgb({c})"/>')
    return "".join(out)


def fringes_svg(P, ph):
    col = wavelength_to_rgb(P["lam"])
    color = "rgb(%d,%d,%d)" % tuple(col)
    pts = " ".join(
        f"{i*1.5:.1f},{225 - intensity(((i / 600) - 0.5) * WIN, ph['beta'], ph['shift']) * 90:.1f}"
        for i in range(601))
    ticks = "".join(
        f'<text x="{450 + m*300 - 14}" y="246" fill="#8d9aab" font-size="12">{m} mm</text>' for m in (-1, 0, 1))
    return (f'<svg viewBox="0 0 900 250" class="fig">'
            f'{fringe_strip(ph["beta"], ph["shift"], P["lam"])}'
            f'<line x1="0" y1="225" x2="900" y2="225" stroke="#2a3441"/>'
            f'<polyline points="{pts}" fill="none" stroke="{color}" stroke-width="1.8"/>'
            f'{ticks}<text x="6" y="130" fill="#8d9aab" font-size="12">I / I₀</text></svg>')


def compare_svg(P, ph):
    names = [(400, "400 nm violet"), (450, "450 nm blue"), (532, "532 nm green"),
             (589, "589 nm yellow"), (632, "632 nm red"), (700, "700 nm deep red")]
    rows = []
    for k, (nm, label) in enumerate(names):
        y = k * 46
        beta = nm * 1e-9 * (ph["D"] / 100) / (ph["d"] / 1e3) * 1e3
        rows.append(fringe_strip(beta, 0, nm, n=300, height=34, y=y))
        rows.append(f'<text x="8" y="{y+22}" fill="#fff" font-size="13" stroke="#000" stroke-width="0.4">'
                    f'{label}: β = {beta:.3f} mm</text>')
    return f'<svg viewBox="0 0 900 276" class="fig">{"".join(rows)}</svg>'


def geometry_svg(P, ph):
    W, H, cy, h = 900, 280, 140, 70
    col = "rgb(%d,%d,%d)" % tuple(wavelength_to_rgb(P["lam"]))
    xS = 70
    s = 700 / (P["u"] + P["v"])
    xb, xs = xS + P["u"] * s, xS + (P["u"] + P["v"]) * s
    ds = min(10 + ph["d"] * 9, 60)                 # d is exaggerated so it can be seen
    at = lambda x0, y0, x1, y1, X: y0 + (y1 - y0) * (X - x0) / (x1 - x0)
    yUp, yLo = at(xS, cy + ds, xb, cy, xs), at(xS, cy - ds, xb, cy, xs)
    o = [f'<defs><clipPath id="c"><rect width="{W}" height="{H}"/></clipPath></defs>',
         f'<line x1="30" y1="{cy}" x2="{W-20}" y2="{cy}" stroke="#3a4757" stroke-dasharray="4 5"/>',
         f'<g clip-path="url(#c)"><polygon points="{xb},{cy} {xs},{yUp} {xs},{yLo}" fill="{col}" fill-opacity="0.22"/>']
    for y0, yt in [(cy - ds, cy - h), (cy - ds, cy), (cy + ds, cy), (cy + ds, cy + h)]:
        o.append(f'<polyline points="{xS},{y0} {xb},{yt} {xs},{at(xS, y0, xb, yt, xs)}" fill="none" stroke="{col}"/>')
    o.append('</g>')
    o.append(f'<polyline points="{xS},{cy} {xb},{cy-h}" stroke="#fff" stroke-opacity="0.35" fill="none"/>'
             f'<polyline points="{xS},{cy} {xb},{cy+h}" stroke="#fff" stroke-opacity="0.35" fill="none"/>')
    o.append(f'<polygon points="{xb+8},{cy-h} {xb},{cy} {xb+8},{cy+h}" fill="#8cc8ff" fill-opacity="0.35" stroke="#8cc8ff" stroke-width="1.5"/>')
    o.append(f'<line x1="{xs}" y1="{cy-h-35}" x2="{xs}" y2="{cy+h+35}" stroke="#dde3ea" stroke-width="3"/>')
    o.append(f'<circle cx="{xS}" cy="{cy}" r="5" fill="{col}"/>'
             f'<circle cx="{xS}" cy="{cy-ds}" r="5" fill="none" stroke="{col}" stroke-width="1.5"/>'
             f'<circle cx="{xS}" cy="{cy+ds}" r="5" fill="none" stroke="{col}" stroke-width="1.5"/>')
    t = lambda x, y, s: f'<text x="{x:.0f}" y="{y:.0f}" fill="#dde3ea" font-size="13">{s}</text>'
    o += [t(xS-20, cy+4, "S"), t(xS-26, cy-ds+4, "S₁"), t(xS-26, cy+ds+4, "S₂"),
          t(xb-22, cy-h-10, "Biprism"), t(xs-20, cy-h-42, "Screen"),
          f'<text x="{(xS+xb)/2-30:.0f}" y="{H-10}" fill="#8d9aab" font-size="13">u = {P["u"]:g} cm</text>',
          f'<text x="{(xb+xs)/2-30:.0f}" y="{H-10}" fill="#8d9aab" font-size="13">v = {P["v"]:g} cm</text>',
          f'<line x1="{xS}" y1="{H-28}" x2="{xs}" y2="{H-28}" stroke="#4a586a"/>']
    return f'<svg viewBox="0 0 {W} {H}" class="fig">{"".join(o)}</svg>'


# ---------------------------------------------------------------- page
CSS = """
:root{--bg:#0e1319;--panel:#171e27;--line:#2a3441;--tx:#dde3ea;--mute:#8d9aab;--c:@@COL@@}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--tx);font:15px/1.5 system-ui,Segoe UI,sans-serif}
.wrap{max-width:1080px;margin:0 auto;padding:20px 16px 40px}
h1{font:600 26px Georgia,serif;margin:0 0 4px}.sub{color:var(--mute);margin:0 0 18px}
.grid{display:grid;grid-template-columns:300px 1fr;gap:16px}@media(max-width:820px){.grid{grid-template-columns:1fr}}
.panel{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:14px 16px;margin-bottom:16px}
h2{font:600 16px Georgia,serif;margin:0 0 10px}
label{display:flex;justify-content:space-between;font-size:14px}label b{color:var(--c)}
input[type=range]{width:100%;accent-color:var(--c);margin-bottom:10px}
button,a.btn{background:var(--c);color:#111;border:0;border-radius:6px;padding:8px 12px;font-weight:600;cursor:pointer;margin:0 6px 6px 0;text-decoration:none;display:inline-block;font-size:14px}
button.alt,a.alt{background:transparent;color:var(--tx);border:1px solid var(--line)}
.out{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-bottom:12px}
.out div{border-left:3px solid var(--c);padding:2px 10px}.out span{display:block;color:var(--mute);font-size:12px}
.out strong{font:600 19px Georgia,serif}.fig{width:100%;display:block;background:#0a0e13;border-radius:6px}
.note{color:var(--mute);font-size:13px;margin:8px 0 0}ul{padding-left:18px;margin:0}li{margin-bottom:6px;font-size:14px}
"""

BODY = """<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Fresnel Biprism Interferometer Simulator</title><style>@@CSS@@</style></head><body><div class="wrap">
<h1>Fresnel Biprism Interferometer Simulator</h1>
<p class="sub">Wavefront-division interference. Python calculates and draws everything; set the sliders and press Update.</p>
<div class="grid"><div>
<form class="panel" method="get" action="/"><h2>Optical parameters</h2>@@SLIDERS@@
<button type="submit">Update</button><a class="btn alt" href="/">Reset</a>
<h2 style="margin-top:12px">Colour presets</h2>@@PRESETS@@</form>
<div class="panel"><h2>Formula sheet</h2><ul>
<li>Virtual source gap: d = 2u(μ − 1)α</li><li>Total distance: D = u + v</li>
<li>Fringe width: β = λD / d</li><li>Intensity: I = I₀ cos²(πx / β)</li>
<li>Bright: Δx = nλ &nbsp; Dark: Δx = (2n + 1)λ/2</li></ul></div></div>
<div><div class="panel"><div class="out">
<div><span>Virtual separation d</span><strong>@@D@@ mm</strong></div>
<div><span>Total distance D</span><strong>@@BIGD@@ cm</strong></div>
<div><span>Fringe width β</span><strong>@@BETA@@ mm</strong></div>
<div><span>Fringes in 3 mm</span><strong>@@NF@@</strong></div></div>
@@GEO@@<p class="note">Schematic: d is exaggerated so S₁ and S₂ are visible. The shaded wedge is where both wavefronts overlap.</p></div>
<div class="panel"><h2>Screen pattern and intensity profile</h2>@@FR@@<p class="note">@@SHIFT@@</p></div>
<div class="panel"><h2>Same setup, different colours</h2>@@CMP@@
<p class="note">Longer wavelength gives wider fringes: red is widest, violet is narrowest.</p></div>
<div class="panel"><h2>Link to biotechnology</h2>
<p>Interferometry turns tiny optical path differences into visible fringe shifts. A transparent film of thickness t and index n<sub>f</sub> placed in one beam shifts the pattern by N = (n<sub>f</sub> − 1)t / λ fringes, so very small thicknesses can be read from the shift. The slider uses n<sub>f</sub> = 1.38, typical of biological material.</p>
<p>The same principle drives optical coherence tomography (OCT), which images retinal and tissue layers by interfering light reflected from different depths, and label-free biosensors and phase microscopy.</p></div>
</div></div></div></body></html>"""


def get_params(query):
    P = {}
    for k, (lo, hi, dflt, step, _) in LIMITS.items():
        try:
            val = float(query.get(k, [dflt])[0])
        except ValueError:
            val = dflt
        P[k] = min(max(val, lo), hi)
    if "preset" in query:                      # colour preset buttons override lambda
        try:
            P["lam"] = min(max(float(query["preset"][0]), 380), 750)
        except ValueError:
            pass
    return P


def render(query):
    P = get_params(query)
    ph = physics(P)
    col = "rgb(%d,%d,%d)" % tuple(wavelength_to_rgb(P["lam"]))
    sliders = "".join(
        f'<label for="{k}">{lab}<b>{P[k]:g}</b></label>'
        f'<input id="{k}" name="{k}" type="range" min="{lo}" max="{hi}" step="{st}" value="{P[k]:g}">'
        for k, (lo, hi, _, st, lab) in LIMITS.items())
    presets = "".join(f'<button class="alt" name="preset" value="{nm}">{n}</button>'
                      for nm, n in [(420, "Violet"), (470, "Blue"), (532, "Green"), (589, "Yellow"), (632, "Red")])
    shift = (f"Film shifts the pattern by N = {ph['N']:.2f} fringes ({ph['shift']:.3f} mm)." if P["t"] > 0
             else "Set a film thickness above 0 and press Update to see the fringe shift used for thickness measurement.")
    page = BODY
    for key, val in {"CSS": CSS.replace("@@COL@@", col), "SLIDERS": sliders, "PRESETS": presets,
                     "D": f"{ph['d']:.3f}", "BIGD": f"{ph['D']:.0f}", "BETA": f"{ph['beta']:.3f}",
                     "NF": f"{WIN/ph['beta']:.1f}", "GEO": geometry_svg(P, ph),
                     "FR": fringes_svg(P, ph), "CMP": compare_svg(P, ph), "SHIFT": shift}.items():
        page = page.replace(f"@@{key}@@", val)
    return page


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        url = urlparse(self.path)
        if url.path != "/":
            self.send_error(404); return
        body = render(parse_qs(url.query)).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "export":
        with open("simulator.html", "w", encoding="utf-8") as f:
            f.write(render({}))
        print("Wrote simulator.html")
    else:
        server = HTTPServer(("127.0.0.1", 8000), Handler)
        print("Simulator running at http://localhost:8000  (press Ctrl+C to stop)")
        webbrowser.open("http://localhost:8000")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("Stopped.")
