# fresnel-biprism-simulator
PHYSICS LAB PBL
# Fresnel Biprism Interferometer Simulator

An interactive simulator of the Fresnel biprism for studying the wave nature of light, wavefront-division interference, and how optical parameters affect the virtual source separation (d) and fringe width (β).

Built with **HTML, CSS and Python only**. 

## What it does

- Shows how one monochromatic source S splits into two coherent virtual sources S₁ and S₂.
- Calculates the virtual source separation, total distance and fringe width.
- Draws the ray diagram, the coloured fringe pattern and the intensity curve.
- Compares fringes for six wavelengths (violet to red) side by side.
- Shows how a thin film in one beam shifts the fringes, which is the idea behind micro-thickness measurement.

## Technologies used

| Technology | Role |
|---|---|
| Python | All calculations, the local web server, and drawing every figure |
| HTML | Page structure, the input form (sliders) and the explanatory text |
| CSS | Layout, colours and styling of the page |

The figures are drawn as SVG, which is written inside the HTML page by Python.

## Formulas used

| Quantity | Formula |
|---|---|
| Virtual source separation | d = 2u(μ − 1)α |
| Total distance | D = u + v |
| Fringe width | β = λD / d |
| Intensity | I = I₀ cos²(πx / β) |
| Fringe shift by a thin film | N = (n_f − 1)t / λ |

Here u is the slit to biprism distance, v is the biprism to screen distance, μ is the glass refractive index, α is the biprism angle in radians and λ is the wavelength.

## Files

| File | Purpose |
|---|---|
| `server.py` | Main program. Runs the simulator in your browser. |
| `simulator.html` | A saved snapshot of the page with default values (sliders do not recalculate). |
| `biprism_from_scratch.py` | A simplified version for learning how the code is built step by step. |

## How to run

1. Install Python 3 from python.org. On Windows, tick "Add Python to PATH" during installation.
2. Download this repository (Code, then Download ZIP) and unzip it.
3. Open a terminal in the folder.
4. Run:
   ```
   python server.py
   ```
   On Mac or Linux you may need `python3 server.py`.
5. Your browser opens `http://localhost:8000`. If it doesn't, open that address yourself.
6. Stop the program with `Ctrl + C`.

No internet connection is needed, and nothing else has to be installed.

## How to use

1. Set the sliders: wavelength, biprism angle, distances u and v, glass index and film thickness.
2. Press **Update** (or a colour preset) to recalculate.
3. Read d, D and β in the result cards.
4. Check the ray diagram, the fringes and the intensity curve.
5. Change one slider at a time to see its effect.

What to expect: a larger wavelength or screen distance widens the fringes. A larger biprism angle narrows them.

## Limitations

- Assumes ideal conditions: a point-like slit, coherent monochromatic light and equal-brightness fringes.
- Does not model diffraction at the biprism edges.
- The ray diagram is schematic, with d exaggerated so it can be seen.
- The page updates when you press Update, not while dragging a slider.

## Team

SHRIYA GEORGE
YASHIKA SINGH

## License

For academic use.
