#!/usr/bin/env python
"""Verifica (sem abrir o Premiere) se TODAS as legendas ficam dentro da margem segura.

Uso: python -I check_margins.py <lote_clips.json> [--font-path Montserrat-Bold.ttf]
                                [--safe-x 0.10] [--safe-y 0.10] [--width 1080] [--height 1920]
Para cada clipe (campos t, z, y, nl gerados por make_graphics_script.py) mede a linha mais larga com a propria fonte
e a altura do bloco; falha (exit 1) se alguma passar de [safe, 1-safe]. Servem as duas skills de legenda
(legenda-impacto: --font-path impact.ttf; legenda-simples: Montserrat-Bold.ttf).
"""
import argparse, json, os, sys
from PIL import ImageFont
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fontpath import find_font

ap = argparse.ArgumentParser()
ap.add_argument("clips")
ap.add_argument("--font-path", default="Montserrat-Bold.ttf")
ap.add_argument("--safe-x", type=float, default=0.10)
ap.add_argument("--safe-y", type=float, default=0.10)
ap.add_argument("--width", type=int, default=1080)
ap.add_argument("--height", type=int, default=1920)
a = ap.parse_args()
f = ImageFont.truetype(find_font(a.font_path), 100)
clips = json.load(open(a.clips, encoding="utf-8"))
lim_x = (1 - 2 * a.safe_x) * a.width
bad, worst = [], 0.0
for c in clips:
    lines = c["t"].split("\r")
    w = max(f.getlength(l) for l in lines) / 100 * c["z"]
    worst = max(worst, w / a.width)
    top = c["y"] * a.height - (len(lines) * c["z"] * 1.2) / 2
    bot = c["y"] * a.height + (len(lines) * c["z"] * 1.2) / 2
    if w > lim_x + 0.5 or top < a.safe_y * a.height - 0.5 or bot > (1 - a.safe_y) * a.height + 0.5:
        bad.append((round(w / a.width, 3), round(top / a.height, 3), round(bot / a.height, 3), c["t"].replace("\r", " / ")))
print(f"{len(clips)} legendas | maior largura {worst:.1%} (limite {1 - 2 * a.safe_x:.0%}) | fora da margem: {len(bad)}")
for b in bad:
    print("  FORA:", b)
sys.exit(1 if bad else 0)
