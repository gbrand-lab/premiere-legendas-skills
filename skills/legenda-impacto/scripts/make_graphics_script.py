#!/usr/bin/env python
"""blocks.json -> script JS (ExtendScript) que cria a legenda como GRAFICOS editaveis no Premiere.

Cada bloco vira 1 ou 2 clipes de .mogrt palavra-por-palavra (texto editavel no Premiere):
  linha pequena  -> trilha TRILHA_PEQ
  linha grande   -> trilha TRILHA_GRANDE (branca) ou TRILHA_VERMELHA (as vermelhas; ver SKILL.md)

Uso:
  python -I make_graphics_script.py blocks.json saida.js --mogrt <base.mogrt> [--style style.json]
        [--height 1920] [--tracks 1,2,5]   (indices 0-based: pequena, grande branca, grande vermelha)
Depois rode o conteudo de saida.js com execute_extendscript (campo "script") com a sequencia ativa.
"""
import argparse, json, os, random, glob, sys
from PIL import ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from fontpath import find_font  # noqa: E402
CAP = 0.79  # altura de maiuscula / tamanho da fonte (Impact)


def width_per_px(font_path, text):
    f = ImageFont.truetype(find_font(font_path), 100)
    return f.getlength(text) / 100.0


LINE_H = 1.2  # altura de linha / tamanho da fonte (Impact) para texto em varias linhas


def _balanced_split(words, nlines, font_path):
    """Divide as palavras em nlines linhas minimizando a linha mais larga."""
    n = len(words)
    best, best_w = None, None
    if nlines == 2:
        for i in range(1, n):
            ls = [" ".join(words[:i]), " ".join(words[i:])]
            w = max(width_per_px(font_path, l) for l in ls)
            if best_w is None or w < best_w:
                best, best_w = ls, w
    else:  # 3 linhas
        for i in range(1, n - 1):
            for j in range(i + 1, n):
                ls = [" ".join(words[:i]), " ".join(words[i:j]), " ".join(words[j:])]
                w = max(width_per_px(font_path, l) for l in ls)
                if best_w is None or w < best_w:
                    best, best_w = ls, w
    return best


def layout_text(text, base, font_path, max_w, min_scale):
    """Garante que o texto cabe em max_w (margem segura). Primeiro encolhe ate base*min_scale; se ainda nao couber,
    quebra em 2 (depois 3) linhas e encolhe so o necessario. Devolve (texto com CR entre linhas, tamanho, n_linhas).
    O tamanho final e SEMPRE tal que a linha mais larga <= max_w (nunca estoura a margem)."""
    words = text.replace("\r", " ").split()
    min_size = base * min_scale
    for nl in (1, 2, 3):
        if nl > len(words):
            break
        lines = [" ".join(words)] if nl == 1 else _balanced_split(words, nl, font_path)
        w100 = max(width_per_px(font_path, l) for l in lines)
        fit_size = max_w / w100
        if fit_size >= min_size or nl == 3 or nl == len(words):
            size = min(base, fit_size)
            return "\r".join(lines), int(size), nl  # int = arredonda para BAIXO (nunca passa da margem)
    return text, int(base), 1


def fit(text, base, font_path, max_w, min_scale):  # compatibilidade
    return layout_text(text, base, font_path, max_w, min_scale)[1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("blocks")
    ap.add_argument("out")
    ap.add_argument("--mogrt", default=None, help="forca um unico .mogrt (sem sorteio de animacao)")
    ap.add_argument("--style", default=os.path.join(HERE, "..", "style.json"))
    ap.add_argument("--width", type=int, default=1080)
    ap.add_argument("--height", type=int, default=1920)
    ap.add_argument("--tracks", default="1,2,5")
    ap.add_argument("--font-path", default="impact.ttf")
    ap.add_argument("--assets", default=os.path.join(HERE, "..", "assets"))
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--batch", type=int, default=8, help="clipes por arquivo .js (lotes pequenos nao travam o Premiere)")
    ap.add_argument("--plain-prob", type=float, default=0.4, help="chance de um bloco virar legenda reta (1 linha, tamanho padrao)")
    a = ap.parse_args()
    st = json.load(open(a.style, encoding="utf-8"))
    blocks = json.load(open(a.blocks, encoding="utf-8"))["blocks"]
    t_small, t_big, t_red = (int(x) for x in a.tracks.split(","))
    W, H = a.width, a.height
    # MARGEM SEGURA (title safe do Premiere = 80% x 80%): nada de texto fora de [safe, 1-safe] em x e y.
    safe_x = st.get("safe_margin_x", 0.10)
    safe_y = st.get("safe_margin_y", 0.10)
    tol = st.get("safe_tolerance", 0.02)             # folga extra contra diferenca de renderizacao da fonte
    max_w = (1 - 2 * safe_x - tol) * W

    def clamp_y(center, h):
        """Centro do bloco (px) ajustado para o bloco inteiro ficar dentro de [safe_y, 1-safe_y] da altura."""
        lo, hi = safe_y * H + h / 2, (1 - safe_y) * H - h / 2
        return min(max(center, lo), hi) if lo <= hi else H / 2
    s_small, s_big = st["mogrt_size_small"], st["mogrt_size_big"]
    font = st["mogrt_font"]
    rnd = random.Random(a.seed)
    anims = sorted(glob.glob(os.path.join(a.assets, "*_WbW.mogrt")))
    if a.mogrt:
        anims = [a.mogrt]
    if not anims:
        sys.exit("Nenhum .mogrt encontrado em " + os.path.abspath(a.assets) + ". Coloque la os seus *_WbW.mogrt (veja o README) ou use --mogrt <arquivo>.")
    s_plain = st.get("mogrt_size_plain", 76)
    clips, last_anim, last_mode, run = [], None, None, 0
    for b in blocks:
        anim = rnd.choice([x for x in anims if x != last_anim] or anims)
        last_anim = anim
        mode = "plain" if rnd.random() < a.plain_prob else "hier"
        if mode == last_mode and run >= 2:
            mode = "hier" if mode == "plain" else "plain"
        run = run + 1 if mode == last_mode else 1
        last_mode = mode
        if mode == "plain":
            txt = " ".join(x for x in (b["small"], b["big"]) if x) if b["layout"] != "big_above" else " ".join(x for x in (b["big"], b["small"]) if x)
            txt, size, nl = layout_text(txt, s_plain, a.font_path, max_w, 1.0)
            h = size * CAP + (nl - 1) * size * LINE_H
            cy = clamp_y(st["y_center"] * H, h)
            clips.append(dict(s=b["start"], e=b["end"], tr=t_big, t=txt, f=font, z=size, y=round(cy / H, 5), k="plain", red=False,
                              m=anim.replace("\\", "/"), nl=nl))
            continue
        ly = b["layout"]
        red = b["color"] == "red"
        items = []  # (kind, text) de cima para baixo
        if ly == "single_small":
            items = [("small", b["small"] or b["big"])]
        elif ly == "single_big":
            items = [("big", b["big"] or b["small"])]
        elif ly == "big_below":
            items = [("small", b["small"]), ("big", b["big"])]
        else:
            items = [("big", b["big"]), ("small", b["small"])]
        sized = []
        for kind, text in items:
            base = s_small if kind == "small" else s_big
            t2, size, nl = layout_text(text, base, a.font_path, max_w, st["min_scale"])
            sized.append((kind, t2, size, nl))
        gap = st["gap"] * max(sz * CAP for _, _, sz, _ in sized)
        heights = [sz * CAP + (nl - 1) * sz * LINE_H for _, _, sz, nl in sized]
        total = sum(heights) + gap * (len(sized) - 1)
        y = clamp_y(st["y_center"] * H, total) - total / 2
        for (kind, text, size, nl), h in zip(sized, heights):
            cy = y + h / 2 + st.get("mogrt_y_adjust", 0)
            track = t_small if kind == "small" else (t_red if red else t_big)
            clips.append(dict(s=b["start"], e=b["end"], tr=track, t=text, f=font, z=size,
                              y=round(cy / H, 5), k=kind, red=bool(red and kind == "big"), m=anim.replace("\\", "/"), nl=nl))
            y += h + gap
    TEMPLATE = """(function(){
var CLIPS = %s;
var TICKS = 254016000000;
var seq = app.project.activeSequence, out = [], ok = 0;
function findText(comp){ for (var i=0;i<comp.properties.numItems;i++){ var v = comp.properties[i].getValue(); if (typeof v === 'string' && v.charAt(0) === '{') return comp.properties[i]; } return null; }
function prop(comp, name){ for (var i=0;i<comp.properties.numItems;i++){ if (comp.properties[i].displayName === name) return comp.properties[i]; } return null; }
for (var i=0;i<CLIPS.length;i++){
  var c = CLIPS[i];
  try {
    var ti = seq.importMGT(c.m, String(Math.round(c.s*TICKS)), c.tr, 0);
    if (!ti) { out.push(i+':importMGT null'); continue; }
    var comp = ti.getMGTComponent();
    var tp = findText(comp);
    var j = JSON.parse(tp.getValue());
    j.textEditValue = c.t; j.fontEditValue = [c.f]; j.fontSizeEditValue = [c.z]; j.fontTextRunLength = [c.t.length];
    tp.setValue(JSON.stringify(j), true);
    var oa = prop(comp, 'Out Animation'); if (oa) oa.setValue(false, true);
    var sp = prop(comp, 'Anim Speed'); if (sp) sp.setValue(c.e - c.s < 1.0 ? 200 : 150, true);
    var t = new Time(); t.seconds = c.e; ti.end = t;
    ti.components[1].properties[0].setValue([0.5, c.y], true);
    ti.name = (c.red ? 'VERMELHO ' : (c.k === 'small' ? 'peq ' : (c.k === 'plain' ? 'reta ' : 'grande '))) + c.t.split(String.fromCharCode(13)).join(' ');
    ok++;
  } catch (e) { out.push(i + ': ' + e); }
}
return 'ok=' + ok + '/' + CLIPS.length + (out.length ? ' erros: ' + out.join(' | ') : '');
})()"""
    base, ext = os.path.splitext(a.out)
    nfiles = 0
    for n in range(0, len(clips), a.batch):
        nfiles += 1
        open(f"{base}_{nfiles:02d}{ext}", "w", encoding="utf-8").write(TEMPLATE % json.dumps(clips[n:n + a.batch], ensure_ascii=False))
    reds = sum(c["red"] for c in clips)
    plain = sum(c["k"] == "plain" for c in clips)
    print(f"{len(clips)} clipes ({reds} vermelhos, {plain} retos) em {nfiles} lotes -> {base}_NN{ext}")
    json.dump(clips, open(base + "_clips.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
