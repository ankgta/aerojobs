"""Draws the hero illustration: a double-deck airliner, nose-on, parked in a hangar.

    python -m site_builder.art.make_hero      -> site_builder/static/hero-hangar.svg

Original artwork, no airline livery or logos. Proportions follow a large
double-deck jet (about 80 m wingspan, 24 m tall) seen from the front.
"""
from pathlib import Path

W, H = 2240, 820    # a wide canvas: the page uses it as a background
CX = 1650           # aircraft centre line, set to the right so text can sit on the left
PLANE_SCALE = 0.62  # the aircraft is drawn smaller so it reads as part of the background
GROUND = 735        # where the tyres touch the floor
FLOOR_TOP = 548     # where the back wall meets the floor
CROP_TOP = 335      # the picture shows everything below this line
M = 15.5            # pixels per metre


def f(x):
    return f"{x:.1f}".rstrip("0").rstrip(".")


def poly(points, **attrs):
    pts = " ".join(f"{f(x)},{f(y)}" for x, y in points)
    a = " ".join(f'{k.replace("_", "-")}="{v}"' for k, v in attrs.items())
    return f'<polygon points="{pts}" {a}/>'


def wing_y(dx, edge):
    """Top / bottom of the wing at distance dx from the centre line (with dihedral)."""
    root_top, root_bot, tip_top, tip_bot = 652, 680, 611, 618
    t = max(0.0, min(1.0, (dx - 50) / 570))
    return (root_top + (tip_top - root_top) * t) if edge == "top" else (root_bot + (tip_bot - root_bot) * t)


def engine(x, cy, r):
    return f"""
  <g>
    <ellipse cx="{f(x)}" cy="{f(cy + r * 0.92)}" rx="{f(r * 0.9)}" ry="{f(r * 0.18)}" fill="#0E2340" opacity=".12"/>
    <circle cx="{f(x)}" cy="{f(cy)}" r="{f(r)}" fill="url(#nacelle)"/>
    <circle cx="{f(x)}" cy="{f(cy)}" r="{f(r * 0.84)}" fill="#22344E"/>
    <circle cx="{f(x)}" cy="{f(cy)}" r="{f(r * 0.76)}" fill="url(#fan)"/>
    {"".join(f'<line x1="{f(x)}" y1="{f(cy)}" x2="{f(x + r * 0.74 * c)}" y2="{f(cy + r * 0.74 * s)}" stroke="#3B5373" stroke-width="1.2"/>'
             for c, s in [(1, 0), (.81, .59), (.31, .95), (-.31, .95), (-.81, .59), (-1, 0), (-.81, -.59), (-.31, -.95), (.31, -.95), (.81, -.59)])}
    <circle cx="{f(x)}" cy="{f(cy)}" r="{f(r * 0.2)}" fill="url(#spinner)"/>
    <path d="M{f(x - r * .62)} {f(cy - r * .55)} A {f(r)} {f(r)} 0 0 1 {f(x + r * .1)} {f(cy - r * .97)}" stroke="#FFFFFF" stroke-opacity=".85" stroke-width="2.4" fill="none" stroke-linecap="round"/>
  </g>"""


def plane():
    parts = []
    # tailplane, behind the fuselage
    for side in (-1, 1):
        parts.append(poly([(CX, 586), (CX + side * 236, 571), (CX + side * 236, 576), (CX, 596)], fill="url(#skin)"))
    # fin
    fin_top = GROUND - 24.1 * M
    parts.append(poly([(CX - 10, 572), (CX - 4, fin_top), (CX + 4, fin_top), (CX + 10, 572)], fill="url(#fin)"))
    # main gear, behind
    for side in (-1, 1):
        for dx in (78, 104):
            parts.append(f'<rect x="{f(CX + side * dx - 9)}" y="{GROUND - 26}" width="18" height="26" rx="5" fill="#1B2433"/>')
        parts.append(f'<rect x="{f(CX + side * 91 - 3)}" y="{GROUND - 52}" width="6" height="30" fill="#5D6E84"/>')
    # wings
    for side in (-1, 1):
        root, tip = CX + side * 50, CX + side * 620
        parts.append(poly([(root, wing_y(50, "top")), (tip, wing_y(620, "top")), (tip, wing_y(620, "bot")),
                           (root, wing_y(50, "bot"))], fill="url(#wing)"))
        parts.append(poly([(root, wing_y(50, "bot") - 7), (tip, wing_y(620, "bot") - 2), (tip, wing_y(620, "bot")),
                           (root, wing_y(50, "bot"))], fill="#8FA4BC", opacity=".55"))
        # wingtip fence
        parts.append(poly([(tip - side * 2, wing_y(620, "top") - 20), (tip + side * 3, wing_y(620, "top") - 16),
                           (tip + side * 3, wing_y(620, "bot") + 9), (tip - side * 2, wing_y(620, "bot") + 12)],
                          fill="#E9F0F7", stroke="#B9C8D8", stroke_width="1"))
    # fuselage: an upright oval, a little wider above the middle like a double-deck body
    parts.append(f'<path d="M{CX} 559 C {CX + 44} 559 {CX + 58} 584 {CX + 57} 620 '
                 f'C {CX + 56} 660 {CX + 40} 690 {CX} 690 C {CX - 40} 690 {CX - 56} 660 {CX - 57} 620 '
                 f'C {CX - 58} 584 {CX - 44} 559 {CX} 559 Z" fill="url(#body)"/>')
    parts.append(f'<path d="M{CX - 50} 590 C {CX - 38} 566 {CX - 20} 562 {CX} 561" stroke="#FFFFFF" stroke-width="3" fill="none" stroke-linecap="round" opacity=".9"/>')
    # radome seam
    parts.append(f'<ellipse cx="{CX}" cy="646" rx="31" ry="34" fill="url(#radome)" opacity=".6"/>')
    # cockpit windows, a gentle arc of six panes
    panes = [(-46, 609, -30, 604), (-30, 604, -12, 601), (-10, 601, 10, 601), (12, 601, 30, 604), (30, 604, 46, 609)]
    for x1, y1, x2, y2 in panes:
        parts.append(poly([(CX + x1, y1), (CX + x2, y2), (CX + x2 - (2 if x2 > 0 else -2), y2 + 11),
                           (CX + x1 + (2 if x1 < 0 else -2), y1 + 11)], fill="url(#glass)"))
    parts.append(f'<path d="M{CX - 44} 610 Q {CX} 596 {CX + 44} 610" stroke="#FFFFFF" stroke-opacity=".5" stroke-width="1.5" fill="none"/>')
    # nose gear
    parts.append(f'<rect x="{CX - 3}" y="684" width="6" height="34" fill="#5D6E84"/>')
    parts.append(f'<rect x="{CX - 22}" y="{GROUND - 22}" width="16" height="22" rx="5" fill="#1B2433"/>')
    parts.append(f'<rect x="{CX + 6}" y="{GROUND - 22}" width="16" height="22" rx="5" fill="#1B2433"/>')
    # engines: inboard about 15 m, outboard about 26 m from the centre line
    for side in (-1, 1):
        parts.append(engine(CX + side * 15.2 * M, 676, 30))
        parts.append(engine(CX + side * 25.7 * M, 661, 27))
    # anti-collision light and nav lights
    # red anti-collision beacon on the crown: on for 1 second, off for 1 second
    parts.append(f'<g class="beacon"><circle cx="{CX}" cy="557" r="9" fill="#FF3B3B" opacity=".28"/><circle cx="{CX}" cy="557" r="3.6" fill="#FF3B3B"/></g>')
    parts.append(f'<circle cx="{CX - 622}" cy="{f(wing_y(620, "top") - 2)}" r="3" fill="#FF5A5A"/>')
    parts.append(f'<circle cx="{CX + 622}" cy="{f(wing_y(620, "top") - 2)}" r="3" fill="#2EE59D"/>')
    return "\n".join(parts)


def hangar():
    out = []
    # back wall with clerestory daylight
    out.append(f'<rect width="{W}" height="{FLOOR_TOP}" fill="url(#wall)"/>')
    out.append(f'<rect y="168" width="{W}" height="54" fill="url(#daylight)"/>')
    for x in range(0, W + 1, 70):
        out.append(f'<line x1="{x}" y1="168" x2="{x}" y2="222" stroke="#9FB4C9" stroke-width="3"/>')
    for x in range(35, W, 140):
        out.append(f'<line x1="{x}" y1="230" x2="{x}" y2="{FLOOR_TOP}" stroke="#A9BCCF" stroke-width="1.5" opacity=".6"/>')
    # roof truss
    out.append(f'<rect width="{W}" height="160" fill="url(#roof)"/>')
    out.append(f'<g stroke="#5E7690" stroke-width="4" fill="none">'
               f'<line x1="0" y1="34" x2="{W}" y2="34"/><line x1="0" y1="140" x2="{W}" y2="140"/>'
               + "".join(f'<polyline points="{x},140 {x + 50},34 {x + 100},140"/>' for x in range(-50, W, 100))
               + "</g>")
    # lamps hang just below the top edge of the cropped picture, clear of the tail fin
    for x in (260, 640, 1020, 1400, 1840, 2120):
        out.append(f'<ellipse cx="{x}" cy="{CROP_TOP + 90}" rx="170" ry="110" fill="url(#lampglow)"/>')
        out.append(f'<line x1="{x}" y1="{CROP_TOP}" x2="{x}" y2="{CROP_TOP + 16}" stroke="#5E7690" stroke-width="2"/>')
        out.append(poly([(x - 18, CROP_TOP + 16), (x + 18, CROP_TOP + 16), (x + 26, CROP_TOP + 30), (x - 26, CROP_TOP + 30)], fill="#3E536C"))
        out.append(f'<ellipse cx="{x}" cy="{CROP_TOP + 31}" rx="22" ry="4" fill="#FFF6D8"/>')
    # lower wall band and some equipment
    out.append(f'<rect y="{FLOOR_TOP - 70}" width="{W}" height="70" fill="#A7BBCF" opacity=".55"/>')
    # work platform with stairs, on the left
    out.append('<g stroke="#6F87A1" stroke-width="3" fill="none" transform="translate(-700 0)">'
               '<line x1="1150" y1="420" x2="1150" y2="548"/><line x1="1260" y1="420" x2="1260" y2="548"/>'
               '<line x1="1140" y1="420" x2="1270" y2="420"/><line x1="1140" y1="400" x2="1270" y2="400"/>'
               '<line x1="1150" y1="400" x2="1150" y2="420"/><line x1="1260" y1="400" x2="1260" y2="420"/>'
               + "".join(f'<line x1="{1270 + i * 12}" y1="{420 + i * 16}" x2="{1286 + i * 12}" y2="{420 + i * 16}"/>' for i in range(8))
               + '<line x1="1270" y1="420" x2="1366" y2="548"/></g>')
    # tool cabinets on the right
    for i, x in enumerate((1930, 1988, 2046)):
        out.append(f'<rect x="{x}" y="{488 - i * 6}" width="52" height="{60 + i * 6}" rx="3" fill="#7F96AF"/>')
        out.append(f'<line x1="{x + 6}" y1="{506 - i * 6}" x2="{x + 46}" y2="{506 - i * 6}" stroke="#B3C4D6" stroke-width="2"/>')
    # side columns
    for x in (0, W - 64):
        out.append(f'<rect x="{x}" y="0" width="64" height="{FLOOR_TOP}" fill="url(#column)"/>')
    # floor: polished, with perspective joints and a yellow lead-in line
    out.append(f'<rect y="{FLOOR_TOP}" width="{W}" height="{H - FLOOR_TOP}" fill="url(#floor)"/>')
    out.append(f'<line x1="0" y1="{FLOOR_TOP}" x2="{W}" y2="{FLOOR_TOP}" stroke="#7F95AD" stroke-width="2"/>')
    for i in range(-16, 10):
        out.append(f'<line x1="{CX + i * 78}" y1="{FLOOR_TOP}" x2="{CX + i * 240}" y2="{H}" stroke="#93A8BE" stroke-width="1.2" opacity=".55"/>')
    for y in (600, 668, 760):
        out.append(f'<line x1="0" y1="{y}" x2="{W}" y2="{y}" stroke="#93A8BE" stroke-width="1" opacity=".35"/>')
    out.append(poly([(CX - 2, FLOOR_TOP), (CX + 2, FLOOR_TOP), (CX + 7, H), (CX - 7, H)], fill="#F2B705", opacity=".9"))
    out.append(poly([(CX - 120, 768), (CX + 120, 768), (CX + 124, 776), (CX - 124, 776)], fill="#F2B705", opacity=".9"))
    return "\n".join(out)


def svg():
    return f"""<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 {CROP_TOP} {W} {H - CROP_TOP}" preserveAspectRatio="xMidYMax slice" role="img" aria-label="A large double-deck airliner parked nose-on in a hangar">
<style>
  .beacon {{ animation: blink 2s steps(1, end) infinite; }}
  @keyframes blink {{ 0% {{ opacity: 1; }} 50% {{ opacity: 0; }} }}
  @media (prefers-reduced-motion: reduce) {{ .beacon {{ animation: none; }} }}
</style>
<defs>
  <linearGradient id="wall" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#B7CADD"/><stop offset="1" stop-color="#D3E1EE"/></linearGradient>
  <linearGradient id="roof" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#4C6580"/><stop offset="1" stop-color="#7E96AF"/></linearGradient>
  <linearGradient id="daylight" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#F4FBFF"/><stop offset="1" stop-color="#CDE6F8"/></linearGradient>
  <linearGradient id="column" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#6E86A0"/><stop offset=".5" stop-color="#8CA2BA"/><stop offset="1" stop-color="#6E86A0"/></linearGradient>
  <linearGradient id="floor" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#B9CADB"/><stop offset="1" stop-color="#DCE7F1"/></linearGradient>
  <radialGradient id="lampglow"><stop offset="0" stop-color="#FFF8E1" stop-opacity=".75"/><stop offset="1" stop-color="#FFF8E1" stop-opacity="0"/></radialGradient>
  <linearGradient id="body" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#FFFFFF"/><stop offset=".55" stop-color="#EEF3F8"/><stop offset="1" stop-color="#B9C8D8"/></linearGradient>
  <radialGradient id="radome" cx=".4" cy=".35" r=".7"><stop offset="0" stop-color="#FFFFFF"/><stop offset="1" stop-color="#DCE5EE"/></radialGradient>
  <linearGradient id="skin" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#F7FAFD"/><stop offset="1" stop-color="#C3D0DE"/></linearGradient>
  <linearGradient id="fin" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#FFFFFF"/><stop offset="1" stop-color="#C8D5E2"/></linearGradient>
  <linearGradient id="wing" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#FFFFFF"/><stop offset="1" stop-color="#C9D6E3"/></linearGradient>
  <linearGradient id="glass" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#2B4A70"/><stop offset="1" stop-color="#0E2340"/></linearGradient>
  <radialGradient id="nacelle" cx=".4" cy=".35" r=".75"><stop offset="0" stop-color="#FFFFFF"/><stop offset=".8" stop-color="#DCE5EE"/><stop offset="1" stop-color="#AFC0D2"/></radialGradient>
  <radialGradient id="fan" cx=".5" cy=".5" r=".5"><stop offset="0" stop-color="#3A5272"/><stop offset="1" stop-color="#14243A"/></radialGradient>
  <radialGradient id="spinner" cx=".35" cy=".35" r=".7"><stop offset="0" stop-color="#FFFFFF"/><stop offset="1" stop-color="#9AAEC4"/></radialGradient>
  <radialGradient id="shadow"><stop offset="0" stop-color="#0E2340" stop-opacity=".32"/><stop offset="1" stop-color="#0E2340" stop-opacity="0"/></radialGradient>
  <linearGradient id="reflectfade" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#fff" stop-opacity=".22"/><stop offset=".5" stop-color="#fff" stop-opacity="0"/></linearGradient>
  <mask id="reflectmask" maskUnits="userSpaceOnUse" x="0" y="{GROUND}" width="{W}" height="{H - GROUND}"><rect x="0" y="{GROUND}" width="{W}" height="{H - GROUND}" fill="url(#reflectfade)"/></mask>
</defs>
{hangar()}
<g transform="translate({CX} {GROUND}) scale({PLANE_SCALE}) translate({-CX} {-GROUND})">
<ellipse cx="{CX}" cy="{GROUND + 4}" rx="600" ry="26" fill="url(#shadow)"/>
<g id="plane">
{plane()}
</g>
<g mask="url(#reflectmask)"><use href="#plane" xlink:href="#plane" transform="translate(0 {2 * GROUND}) scale(1 -1)"/></g>
</g>
</svg>
"""


if __name__ == "__main__":
    out = Path(__file__).resolve().parent.parent / "static" / "hero-hangar.svg"
    out.write_text(svg(), encoding="utf-8")
    print(f"Wrote {out} ({out.stat().st_size // 1024} KB)")
