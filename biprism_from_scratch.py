import math
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs

WIN = 3.0                       # mm of screen we look at

# ---------- STEP 1: physics ----------
def physics(lam_nm, alpha_deg, u_cm, v_cm, mu):
    lam = lam_nm * 1e-9                  # nm -> m
    a = math.radians(alpha_deg)          # degrees -> radians
    u, v = u_cm / 100, v_cm / 100        # cm -> m
    d = 2 * u * (mu - 1) * a             # d = 2u(mu-1)alpha
    D = u + v                            # D = u + v
    beta = lam * D / d                   # beta = lambda D / d
    return d * 1000, D * 100, beta * 1000    # d in mm, D in cm, beta in mm

# ---------- STEP 2: colour ----------
def wavelength_to_rgb(nm):
    r = g = b = 0.0
    if nm < 440:   r, b = (440 - nm) / 60, 1
    elif nm < 490: g, b = (nm - 440) / 50, 1
    elif nm < 510: g, b = 1, (510 - nm) / 20
    elif nm < 580: r, g = (nm - 510) / 70, 1
    elif nm < 645: r, g = 1, (645 - nm) / 65
    else:          r = 1
    return [255 * r, 255 * g, 255 * b]

# ---------- STEP 4: fringes ----------
def intensity(x_mm, beta_mm, shift_mm=0):
    return math.cos(math.pi * (x_mm - shift_mm) / beta_mm) ** 2    # I = I0 cos^2(pi x / beta)

def fringes_svg(beta, nm, shift=0):
    r, g, b = wavelength_to_rgb(nm)
    n = 600                                # number of vertical strips
    w = 900 / n
    parts = []
    for i in range(n):
        x_mm = (i / n - 0.5) * WIN         # strip position on the screen
        I = intensity(x_mm, beta, shift)
        parts.append(f'<rect x="{i*w:.2f}" y="0" width="{w+0.6:.2f}" height="100" '
                     f'fill="rgb({int(r*I)},{int(g*I)},{int(b*I)})"/>')
    return f'<svg viewBox="0 0 900 100" width="100%">{"".join(parts)}</svg>'

# ---------- STEP 5: intensity curve ----------
def curve_svg(beta, nm, shift=0):
    r, g, b = wavelength_to_rgb(nm)
    pts = []
    for i in range(601):
        x_mm = (i / 600 - 0.5) * WIN
        y = 110 - intensity(x_mm, beta, shift) * 100
        pts.append(f"{i*1.5:.1f},{y:.1f}")
    return (f'<svg viewBox="0 0 900 120" width="100%" style="background:#111">'
            f'<polyline points="{" ".join(pts)}" fill="none" stroke="rgb({int(r)},{int(g)},{int(b)})" stroke-width="2"/></svg>')

# ---------- STEP 6: ray diagram ----------
def geometry_svg(u, v, d_mm):
    cy, h, xS = 140, 70, 70
    s = 700 / (u + v)
    xb, xs = xS + u * s, xS + (u + v) * s          # biprism and screen x-positions
    ds = min(10 + d_mm * 9, 60)                    # d is exaggerated so we can see it
    at = lambda x0, y0, x1, y1, X: y0 + (y1 - y0) * (X - x0) / (x1 - x0)
    yUp, yLo = at(xS, cy + ds, xb, cy, xs), at(xS, cy - ds, xb, cy, xs)
    out = [f'<polygon points="{xb},{cy} {xs},{yUp} {xs},{yLo}" fill="orange" fill-opacity="0.25"/>']
    for y0, yt in [(cy - ds, cy - h), (cy - ds, cy), (cy + ds, cy), (cy + ds, cy + h)]:
        out.append(f'<polyline points="{xS},{y0} {xb},{yt} {xs},{at(xS, y0, xb, yt, xs)}" '
                   f'fill="none" stroke="orange"/>')
    out.append(f'<polygon points="{xb+8},{cy-h} {xb},{cy} {xb+8},{cy+h}" fill="lightblue"/>')   # biprism
    out.append(f'<line x1="{xs}" y1="{cy-h-30}" x2="{xs}" y2="{cy+h+30}" stroke="white" stroke-width="3"/>')  # screen
    for y, name in [(cy, "S"), (cy - ds, "S1"), (cy + ds, "S2")]:
        out.append(f'<circle cx="{xS}" cy="{y}" r="5" fill="orange"/>'
                   f'<text x="{xS-28}" y="{y+4}" fill="white" font-size="13">{name}</text>')
    return f'<svg viewBox="0 0 900 280" width="100%" style="background:#111">{"".join(out)}</svg>'

# ---------- STEP 7: comparison of colours ----------
def compare_svg(D_cm, d_mm):
    rows = []
    for k, nm in enumerate([400, 450, 532, 589, 632, 700]):
        beta = nm * 1e-9 * (D_cm / 100) / (d_mm / 1000) * 1000
        r, g, b = wavelength_to_rgb(nm)
        for i in range(300):
            I = intensity((i / 300 - 0.5) * WIN, beta)
            rows.append(f'<rect x="{i*3}" y="{k*40}" width="3.6" height="34" '
                        f'fill="rgb({int(r*I)},{int(g*I)},{int(b*I)})"/>')
        rows.append(f'<text x="8" y="{k*40+22}" fill="white" font-size="13">{nm} nm: beta = {beta:.3f} mm</text>')
    return f'<svg viewBox="0 0 900 240" width="100%">{"".join(rows)}</svg>'

# ---------- STEP 3 + 8: page ----------
def get_value(query, name, default):
    try:
        return float(query.get(name, [default])[0])
    except ValueError:
        return default

def slider(name, label, lo, hi, step, value):
    return (f'<label>{label}: <b>{value:g}</b></label><br>'
            f'<input type="range" name="{name}" min="{lo}" max="{hi}" step="{step}" value="{value:g}"><br>')

def render(query):
    lam   = get_value(query, "lam", 589)
    alpha = get_value(query, "alpha", 0.5)
    u     = get_value(query, "u", 20)
    v     = get_value(query, "v", 100)
    mu    = get_value(query, "mu", 1.5)
    t     = get_value(query, "t", 0)

    d, D, beta = physics(lam, alpha, u, v, mu)
    N = (1.38 - 1) * t * 1e-6 / (lam * 1e-9)     # fringes shifted by a thin film
    shift = N * beta                              # shift in mm

    return f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<title>Fresnel Biprism Simulator</title></head>
<body style="font-family:sans-serif;background:#0e1319;color:#dde3ea;max-width:900px;margin:auto">
<h1>Fresnel Biprism Simulator</h1>
<form>
{slider("lam", "Wavelength (nm)", 380, 750, 1, lam)}
{slider("alpha", "Biprism angle (deg)", 0.1, 1, 0.01, alpha)}
{slider("u", "u (cm)", 10, 40, 1, u)}
{slider("v", "v (cm)", 30, 150, 1, v)}
{slider("mu", "Glass index", 1.4, 1.7, 0.01, mu)}
{slider("t", "Film thickness (um)", 0, 5, 0.05, t)}
<button>Update</button> <a href="/" style="color:#dde3ea">Reset</a>
</form>
<p>d = {d:.3f} mm &nbsp; D = {D:.0f} cm &nbsp; beta = {beta:.3f} mm &nbsp; film shift = {N:.2f} fringes</p>
{geometry_svg(u, v, d)}
{fringes_svg(beta, lam, shift)}
{curve_svg(beta, lam, shift)}
{compare_svg(D, d)}
</body></html>"""

# ---------- STEP 3: server ----------
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        query = parse_qs(urlparse(self.path).query)
        body = render(query).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(body)

if __name__ == "__main__":
    print("Open http://localhost:8000 in your browser (Ctrl+C to stop)")
    HTTPServer(("127.0.0.1", 8000), Handler).serve_forever()
