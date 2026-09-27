"""Генерация сезонных дизайнов сертификата (HTML/SVG → Chrome → PNG 1754×1240)."""
import math, random, sys
S = sys.argv[1]
MAPLE = "M0,-50 L8,-30 L22,-38 L18,-18 L38,-22 L30,-8 L46,2 L24,8 L28,24 L8,16 L4,42 L0,30 L-4,42 L-8,16 L-28,24 L-24,8 L-46,2 L-30,-8 L-38,-22 L-18,-18 L-22,-38 L-8,-30 Z"
LEAF = "M0,-40 C22,-26 24,10 0,40 C-24,10 -22,-26 0,-40 Z"
SEASONS = {
 "kuz":   dict(paper="#FBF6EC", accent="#B8541C", accent2="#8A3B12", muted="#7A6A58", blob="#F6E3C8", sun="#EFB54A",
              cols=["#C2410C", "#E07A2E", "#E9A23B", "#9A3412", "#7C8B3A"], title_c="#B8541C"),
 "qish":  dict(paper="#F5F8FB", accent="#2F6690", accent2="#1E4A6B", muted="#5E6C79", blob="#DDEAF4", sun="#C9DDEC",
              cols=["#2F5D50", "#3F7A66", "#1F4B40"], title_c="#2F6690"),
 "bahor": dict(paper="#FDF7F6", accent="#C0506F", accent2="#8E3450", muted="#7B6670", blob="#F8DCE3", sun="#FBE6A7",
              cols=["#F4A6B7", "#E87A99", "#F7C6D1", "#7BB661", "#5E9E4B"], title_c="#C0506F"),
 "yoz":   dict(paper="#F8FAF0", accent="#2F7D4F", accent2="#1F5A38", muted="#5F6F5E", blob="#DDF0D4", sun="#F6C343",
              cols=["#3E8E41", "#5AA84F", "#9BC53D", "#2F6B3A"], title_c="#2F7D4F"),
}

def rnd(seed): return random.Random(seed)

def panel_svg(season, c):
    r = rnd(len(season) * 7)
    g = []
    g.append(f'<path d="M140,0 C40,200 120,380 60,560 C0,760 90,960 40,1240 L574,1240 L574,0 Z" fill="{c["blob"]}"/>')
    if season == "kuz":
        g.append(f'<circle cx="300" cy="240" r="120" fill="{c["sun"]}" opacity=".9"/>')
        for i in range(26):
            x, y = r.uniform(60, 560), r.uniform(-20, 1260); s = r.uniform(.8, 2.2); rot = r.uniform(0, 360)
            col = r.choice(c["cols"]); shape = MAPLE if r.random() < .6 else LEAF
            g.append(f'<g transform="translate({x:.0f},{y:.0f}) rotate({rot:.0f}) scale({s:.2f})"><path d="{shape}" fill="{col}" opacity="{r.uniform(.75, 1):.2f}"/>'
                     f'<path d="M0,-40 L0,40" stroke="rgba(0,0,0,.18)" stroke-width="1.5"/></g>')
    elif season == "qish":
        g.append(f'<circle cx="320" cy="230" r="110" fill="#FFFFFF" opacity=".8"/>')
        g.append(f'<path d="M0,1240 C120,1060 260,1100 380,980 C470,900 530,930 574,900 L574,1240 Z" fill="#FFFFFF" opacity=".9"/>')
        for i in range(7):   # еловые ветки
            x0, y0 = r.uniform(120, 520), r.uniform(200, 1180); ang = r.uniform(-160, -20); L = r.uniform(160, 300)
            parts = [f'<line x1="0" y1="0" x2="{L:.0f}" y2="0" stroke="#4B3B2B" stroke-width="4" stroke-linecap="round"/>']
            for k in range(int(L // 10)):
                px = k * 10 + 6; ln = 26 * (1 - k * 10 / L) + 10
                col = r.choice(c["cols"])
                parts.append(f'<line x1="{px}" y1="0" x2="{px + ln * .5:.0f}" y2="{-ln:.0f}" stroke="{col}" stroke-width="3" stroke-linecap="round"/>')
                parts.append(f'<line x1="{px}" y1="0" x2="{px + ln * .5:.0f}" y2="{ln:.0f}" stroke="{col}" stroke-width="3" stroke-linecap="round"/>')
            g.append(f'<g transform="translate({x0:.0f},{y0:.0f}) rotate({ang:.0f})">{"".join(parts)}</g>')
        for i in range(34):  # снежинки
            x, y, s = r.uniform(20, 560), r.uniform(0, 1240), r.uniform(6, 22)
            arms = "".join(f'<line x1="0" y1="0" x2="{s * math.cos(math.radians(a)):.1f}" y2="{s * math.sin(math.radians(a)):.1f}"/>' for a in range(0, 360, 60))
            g.append(f'<g transform="translate({x:.0f},{y:.0f})" stroke="{c["accent"]}" stroke-width="2" opacity="{r.uniform(.35, .8):.2f}" stroke-linecap="round">{arms}</g>')
    elif season == "bahor":
        g.append(f'<circle cx="310" cy="250" r="115" fill="{c["sun"]}" opacity=".7"/>')
        for i in range(5):   # ветки
            x0, y0 = r.uniform(200, 574), r.uniform(100, 1150); ang = r.uniform(150, 220); L = r.uniform(220, 380)
            g.append(f'<g transform="translate({x0:.0f},{y0:.0f}) rotate({ang:.0f})"><path d="M0,0 C{L*.3:.0f},-30 {L*.6:.0f},30 {L:.0f},0" stroke="#6B4A3A" stroke-width="5" fill="none" stroke-linecap="round"/></g>')
        for i in range(30):  # цветы
            x, y, s = r.uniform(40, 560), r.uniform(0, 1240), r.uniform(10, 26); col = r.choice(c["cols"][:3])
            petals = "".join(f'<ellipse cx="0" cy="{-s:.0f}" rx="{s * .62:.1f}" ry="{s:.0f}" transform="rotate({a})" fill="{col}"/>' for a in range(0, 360, 72))
            g.append(f'<g transform="translate({x:.0f},{y:.0f}) rotate({r.uniform(0, 72):.0f})">{petals}<circle r="{s * .35:.1f}" fill="#F5C542"/></g>')
        for i in range(14):
            x, y, s = r.uniform(40, 560), r.uniform(0, 1240), r.uniform(.5, 1.1)
            g.append(f'<g transform="translate({x:.0f},{y:.0f}) rotate({r.uniform(0, 360):.0f}) scale({s:.2f})"><path d="{LEAF}" fill="{r.choice(c["cols"][3:])}"/></g>')
    else:  # yoz
        g.append(f'<circle cx="330" cy="250" r="135" fill="{c["sun"]}"/>')
        for k in range(12):
            a = math.radians(k * 30)
            g.append(f'<line x1="{330 + 160 * math.cos(a):.0f}" y1="{250 + 160 * math.sin(a):.0f}" x2="{330 + 205 * math.cos(a):.0f}" y2="{250 + 205 * math.sin(a):.0f}" stroke="{c["sun"]}" stroke-width="10" stroke-linecap="round"/>')
        g.append(f'<path d="M0,1240 C140,1080 300,1130 420,1020 C490,960 540,980 574,960 L574,1240 Z" fill="#BFE3B0"/>')
        for i in range(24):
            x, y, s = r.uniform(40, 574), r.uniform(420, 1260), r.uniform(1.2, 2.8)
            g.append(f'<g transform="translate({x:.0f},{y:.0f}) rotate({r.uniform(-60, 60):.0f}) scale({s:.2f})"><path d="{LEAF}" fill="{r.choice(c["cols"])}" opacity="{r.uniform(.8, 1):.2f}"/>'
                     f'<path d="M0,-38 L0,38" stroke="rgba(255,255,255,.35)" stroke-width="1.5"/></g>')
    return f'<svg width="574" height="1240" viewBox="0 0 574 1240" xmlns="http://www.w3.org/2000/svg">{"".join(g)}</svg>'

def corner_svg(season, c):
    """маленькая сезонная деталь в левом нижнем углу"""
    r = rnd(99 + len(season)); g = []
    for i in range(5):
        x, y, s = r.uniform(10, 150), r.uniform(10, 140), r.uniform(.5, 1)
        shape = MAPLE if season == "kuz" else LEAF
        col = r.choice(c["cols"])
        g.append(f'<g transform="translate({x:.0f},{y:.0f}) rotate({r.uniform(0, 360):.0f}) scale({s:.2f})"><path d="{shape}" fill="{col}" opacity=".55"/></g>')
    return f'<svg width="170" height="160" xmlns="http://www.w3.org/2000/svg">{"".join(g)}</svg>'

for season, c in SEASONS.items():
    html = f"""<!doctype html><html><head><meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Unbounded:wght@700;800&family=Manrope:wght@500;700;800&family=Playfair+Display:ital,wght@1,500&display=block" rel="stylesheet">
<style>
 * {{ margin:0; box-sizing:border-box; }}
 html,body {{ width:1754px; height:1240px; overflow:hidden; background:{c["paper"]}; }}
 .page {{ position:relative; width:1754px; height:1240px; background:{c["paper"]}; font-family:Manrope, sans-serif; }}
 .grain {{ position:absolute; inset:0; opacity:.35; mix-blend-mode:multiply;
   background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='300' height='300'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='.9' numOctaves='2' stitchTiles='stitch'/%3E%3CfeColorMatrix values='0 0 0 0 .5 0 0 0 0 .45 0 0 0 0 .35 0 0 0 .08 0'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E"); }}
 .panel {{ position:absolute; right:0; top:0; }}
 .frame {{ position:absolute; left:34px; top:34px; width:1146px; height:1172px; border:2px solid {c["accent"]}40; border-right:none; border-radius:28px 0 0 28px; }}
 .frame2 {{ position:absolute; left:48px; top:48px; width:1132px; height:1144px; border:1px solid {c["accent"]}22; border-right:none; border-radius:20px 0 0 20px; }}
 .logos {{ position:absolute; left:{575 - 250}px; top:98px; width:500px; }}
 .title {{ position:absolute; left:60px; width:1030px; top:268px; text-align:center; font:800 116px/1 Unbounded, sans-serif; letter-spacing:.06em; color:{c["title_c"]}; }}
 .sub {{ position:absolute; left:60px; width:1030px; top:408px; text-align:center; font:800 28px/1 Manrope; letter-spacing:.45em; color:{c["accent2"]}; }}
 .sub2 {{ position:absolute; left:60px; width:1030px; top:452px; text-align:center; font:700 19px/1 Manrope; letter-spacing:.34em; color:{c["muted"]}; text-transform:uppercase; }}
 .orn {{ position:absolute; left:{575 - 120}px; top:496px; width:240px; height:12px; }}
 .pres {{ position:absolute; left:60px; width:1030px; top:545px; text-align:center; font:italic 500 26px Playfair Display, serif; color:{c["muted"]}; }}
 .nameline {{ position:absolute; left:190px; width:770px; top:668px; height:2px; background:{c["accent"]}55; }}
 .dateline {{ position:absolute; left:300px; width:190px; top:1046px; height:2px; background:{c["muted"]}66; }}
 .datelbl {{ position:absolute; left:300px; width:190px; top:1060px; text-align:center; font:600 17px Manrope; color:{c["muted"]}; letter-spacing:.08em; }}
 .sign {{ position:absolute; left:{720 - 95}px; top:958px; width:190px; }}
 .corner {{ position:absolute; left:40px; bottom:30px; }}
</style></head><body><div class="page">
 <div class="panel">{panel_svg(season, c)}</div>
 <div class="frame"></div><div class="frame2"></div>
 <img class="logos" src="logos.png">
 <div class="title">CERTIFICATE</div>
 <div class="sub">OF APPRECIATION</div>
 <div class="sub2">Minnatdorchilik sertifikati</div>
 <svg class="orn" viewBox="0 0 240 12"><line x1="0" y1="6" x2="100" y2="6" stroke="{c["accent"]}" stroke-opacity=".5" stroke-width="2"/><circle cx="120" cy="6" r="5" fill="{c["accent"]}"/><line x1="140" y1="6" x2="240" y2="6" stroke="{c["accent"]}" stroke-opacity=".5" stroke-width="2"/></svg>
 <div class="pres">This certificate is proudly presented to</div>
 <div class="nameline"></div>
 <div class="dateline"></div><div class="datelbl">Date · Sana</div>
 <img class="sign" src="signature.png">
 <div class="corner">{corner_svg(season, c)}</div>
 <div class="grain"></div>
</div></body></html>"""
    open(f"{S}/cert3/{season}.html", "w").write(html)
print("ok")
