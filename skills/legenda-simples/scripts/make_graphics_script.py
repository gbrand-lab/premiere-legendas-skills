#!/usr/bin/env python
"""blocks.json -> scripts JS (ExtendScript) que criam a legenda "simples" como GRAFICOS editaveis no Premiere.

Cada frase vira 1 clipe de .mogrt (texto editavel) numa unica trilha.

Uso:
  python -I make_graphics_script.py blocks.json saida.js [--track 1] [--style style.json]
        [--width 1080 --height 1920] [--batch 8]
Gera saida_01.js, saida_02.js... (lotes pequenos nao travam o Premiere) e saida_clips.json.
Rode cada lote com execute_extendscript (campo "script") com a sequencia ativa.
"""
import argparse, json, os, sys
from PIL import ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from fontpath import find_font  # noqa: E402


def width_per_px(font_path, text):
    return ImageFont.truetype(find_font(font_path), 100).getlength(text) / 100.0


LINE_H = 1.25  # altura de linha / tamanho da fonte (Montserrat)


def layout_text(text, base, font_path, max_w, min_scale):
    """Garante que a frase cabe em max_w (margem segura): encolhe ate base*min_scale; se ainda nao couber, quebra em 2
    linhas (corte equilibrado) e encolhe so o necessario. Devolve (texto com CR entre linhas, tamanho, n_linhas)."""
    words = text.split()
    min_size = base * min_scale
    for nl in (1, 2):
        if nl > len(words):
            break
        if nl == 1:
            lines = [" ".join(words)]
        else:
            lines = min((
                [" ".join(words[:i]), " ".join(words[i:])] for i in range(1, len(words))
            ), key=lambda ls: max(width_per_px(font_path, l) for l in ls))
        fit_size = max_w / max(width_per_px(font_path, l) for l in lines)
        if fit_size >= min_size or nl == 2 or nl == len(words):
            return "\r".join(lines), int(min(base, fit_size)), nl  # int = para BAIXO: nunca passa da margem
    return text, int(base), 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("blocks")
    ap.add_argument("out")
    ap.add_argument("--style", default=os.path.join(HERE, "..", "style.json"))
    ap.add_argument("--mogrt", default=os.path.join(HERE, "..", "assets", "Simple_Text_WbW.mogrt"))
    ap.add_argument("--track", type=int, default=1, help="indice 0-based da trilha de video")
    ap.add_argument("--width", type=int, default=1080)
    ap.add_argument("--height", type=int, default=1920)
    ap.add_argument("--batch", type=int, default=8)
    a = ap.parse_args()
    st = json.load(open(a.style, encoding="utf-8"))
    blocks = json.load(open(a.blocks, encoding="utf-8"))["blocks"]
    # MARGEM SEGURA (title safe do Premiere = 80% x 80%): nada fora de [safe, 1-safe] em x e y.
    safe_x, safe_y = st.get("safe_margin_x", 0.10), st.get("safe_margin_y", 0.10)
    max_w = (1 - 2 * safe_x - st.get("safe_tolerance", 0.02)) * a.width
    mogrt = os.path.abspath(a.mogrt).replace("\\", "/")
    clips = []
    for b in blocks:
        text, size, nl = layout_text(b["text"], st["mogrt_size"], st["font_path"], max_w, st["min_scale"])
        h = size * 0.75 + (nl - 1) * size * LINE_H
        lo, hi = safe_y * a.height + h / 2, (1 - safe_y) * a.height - h / 2
        cy = min(max(st["y_center"] * a.height, lo), hi) if lo <= hi else a.height / 2
        clips.append(dict(s=b["start"], e=b["end"], tr=a.track, t=text, f=st["mogrt_font"],
                          z=size, y=round(cy / a.height, 5), sp=st["anim_speed"], m=mogrt, nl=nl))
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
    var sp = prop(comp, 'Anim Speed'); if (sp) sp.setValue(c.sp, true);
    var t = new Time(); t.seconds = c.e; ti.end = t;
    ti.components[1].properties[0].setValue([0.5, c.y], true);
    ti.name = 'simples ' + c.t;
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
    json.dump(clips, open(base + "_clips.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"{len(clips)} clipes em {nfiles} lotes -> {base}_NN{ext}")


if __name__ == "__main__":
    main()
