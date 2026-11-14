#!/usr/bin/env python
"""blocks.json -> video transparente (ProRes 4444 com alfa) para colocar na trilha de cima.

Uso:
  python -I render_captions.py blocks.json saida.mov --duration 44.93 [--size 1080x1920] [--fps 30] [--style style.json]
  python -I render_captions.py blocks.json --still 12.5 quadro.png      # so um quadro (previa rapida, fundo cinza)
Requer: Pillow e ffmpeg no PATH.
"""
import json, sys, os, subprocess, argparse
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))


def load_style(path):
    st = json.load(open(path, encoding="utf-8"))
    return st


def font(st, key, size):
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from fontpath import find_font
    last = None
    for p in (st[key], st["font_fallback"]):
        try:
            return ImageFont.truetype(find_font(p), int(size))
        except SystemExit as e:
            last = e
    raise last


def hexrgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def wrap(draw, text, f, max_w):
    words, lines, cur = text.split(" "), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if draw.textlength(t, font=f) <= max_w or not cur:
            cur = t
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def make_item(draw, text, key, base_size, color, st, W, scale):
    """Ajusta o tamanho para caber na largura; se ainda nao couber, quebra em linhas."""
    max_w = st["max_width"] * W
    size = base_size * scale
    f = font(st, key, size)
    if draw.textlength(text, font=f) > max_w:
        k = max_w / draw.textlength(text, font=f)
        if k >= st["min_scale"]:
            size *= k
            f = font(st, key, size)
    lines = wrap(draw, text, f, max_w)
    cap = f.getbbox("H")[3] - f.getbbox("H")[1]
    return dict(lines=lines, font=f, cap=cap, color=color, lh=cap * st["line_height"])


def render_block(b, st, W, H):
    scale = W / 1080.0
    white, red = hexrgb(st["color_white"]), hexrgb(st["color_red"])
    big_color = red if b["color"] == "red" else white
    probe = ImageDraw.Draw(Image.new("L", (8, 8)))
    ly = b["layout"]
    items = []
    if ly == "single_small":
        items = [make_item(probe, b["small"] or b["big"], "font_small", st["size_small"], white, st, W, scale)]
    elif ly == "single_big":
        items = [make_item(probe, b["big"] or b["small"], "font_big", st["size_big"], big_color, st, W, scale)]
    else:
        s = make_item(probe, b["small"], "font_small", st["size_small"], white, st, W, scale)
        g = make_item(probe, b["big"], "font_big", st["size_big"], big_color, st, W, scale)
        items = [s, g] if ly == "big_below" else [g, s]
    gap = st["gap"] * (items[-1]["cap"] if len(items) == 1 else max(i["cap"] for i in items))
    heights = [i["cap"] + (len(i["lines"]) - 1) * i["lh"] for i in items]
    total = sum(heights) + gap * (len(items) - 1)
    top = st["y_center"] * H - total / 2
    text_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    mask = Image.new("L", (W, H), 0)
    d, dm = ImageDraw.Draw(text_layer), ImageDraw.Draw(mask)
    y = top
    for it, h in zip(items, heights):
        base = y + it["cap"]
        for line in it["lines"]:
            d.text((W / 2, base), line, font=it["font"], fill=it["color"] + (255,), anchor="ms")
            dm.text((W / 2, base), line, font=it["font"], fill=255, anchor="ms")
            base += it["lh"]
        y += h + gap
    sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    blur = mask.filter(ImageFilter.GaussianBlur(st["shadow_blur"] * scale))
    blur = blur.point(lambda v: int(v * st["shadow_alpha"]))
    sh.putalpha(blur)
    sh = sh.transform(sh.size, Image.AFFINE, (1, 0, 0, 0, 1, -st["shadow_dy"] * scale))
    return Image.alpha_composite(sh, text_layer)


def animate(img, t, st):
    """Pop de entrada: escala sobe de anim_from_scale a 1 com fade, em anim_frames quadros."""
    bbox = img.getbbox()
    if not bbox or t >= 1:
        return img
    e = 1 - (1 - t) ** 3
    s = st["anim_from_scale"] + (1 - st["anim_from_scale"]) * e
    crop = img.crop(bbox)
    w, h = max(1, int(crop.width * s)), max(1, int(crop.height * s))
    crop = crop.resize((w, h), Image.LANCZOS)
    a = crop.getchannel("A").point(lambda v: int(v * (0.25 + 0.75 * e)))
    crop.putalpha(a)
    out = Image.new("RGBA", img.size, (0, 0, 0, 0))
    cx, cy = (bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2
    out.paste(crop, (int(cx - w / 2), int(cy - h / 2)), crop)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("blocks")
    ap.add_argument("out", nargs="?")
    ap.add_argument("--duration", type=float)
    ap.add_argument("--size", default="1080x1920")
    ap.add_argument("--fps", type=float, default=30)
    ap.add_argument("--style", default=os.path.join(HERE, "..", "style.json"))
    ap.add_argument("--still", type=float, help="exporta so o quadro neste tempo (s) em PNG com fundo cinza")
    a = ap.parse_args()
    W, H = (int(x) for x in a.size.lower().split("x"))
    st = load_style(a.style)
    blocks = json.load(open(a.blocks, encoding="utf-8"))["blocks"]

    if a.still is not None:
        t = a.still
        b = next((b for b in blocks if b["start"] <= t < b["end"]), None)
        bg = Image.new("RGBA", (W, H), (40, 44, 52, 255))
        if b:
            bg = Image.alpha_composite(bg, render_block(b, st, W, H))
        bg.convert("RGB").save(a.out)
        print("ok", a.out, "bloco:", b)
        return

    dur = a.duration or (blocks[-1]["end"] + 0.5)
    total = int(round(dur * a.fps))
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{W}x{H}",
           "-r", str(a.fps), "-i", "-", "-c:v", "prores_ks", "-profile:v", "4444", "-pix_fmt", "yuva444p10le",
           "-vendor", "apl0", a.out]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    empty = bytes(W * H * 4)
    cache, cur_i, cur_bytes = {}, None, empty
    for f in range(total):
        t = f / a.fps
        bi = next((i for i, b in enumerate(blocks) if b["start"] <= t < b["end"]), None)
        if bi is None:
            data = empty
        else:
            if bi not in cache:
                cache = {bi: render_block(blocks[bi], st, W, H)}
            img = cache[bi]
            k = (f - int(round(blocks[bi]["start"] * a.fps))) / max(1, st["anim_frames"])
            data = (animate(img, k, st) if k < 1 else img).tobytes()
        p.stdin.write(data)
    p.stdin.close()
    p.wait()
    print("ok", a.out, f"{total} quadros")


if __name__ == "__main__":
    main()
