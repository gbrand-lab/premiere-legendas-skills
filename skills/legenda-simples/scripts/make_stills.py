#!/usr/bin/env python
"""blocks.json -> legendas SEM animacao de entrada: um PNG transparente 1080x1920 por frase (texto branco + sombra
suave, ja posicionado e dentro da margem segura) + scripts JSX que importam os PNGs e colocam cada um na trilha, no
tempo exato da fala. A frase aparece inteira no 1o quadro e some em corte seco.

Por que PNG e nao .mogrt: o .mogrt (Simple_Text_WbW) tem a entrada palavra por palavra EMBUTIDA (so existe o controle
"Out Animation" e "Anim Speed" 50-500; nao existe "In Animation"). Com Anim Speed 500 ainda ha uma entrada. PNG = zero
animacao, sombra real e o que voce ve no PNG e exatamente o que aparece no video (da pra conferir sem o Premiere).
Contrapartida: o texto nao e editavel no Premiere (para corrigir, edite blocks.json e gere de novo).

Uso: python -I make_stills.py blocks.json <pasta_de_saida> [--track 1] [--bin "legenda_simples"] [--batch 20]
Gera: <pasta>/ls_001.png..., stills_clips.json (para check_margins.py), stills_import.jsx, stills_01.jsx... (colocacao).
Rode primeiro stills_import.jsx e depois os stills_NN.jsx, um por vez, com a sequencia ativa.
"""
import argparse, json, os, sys

from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from fontpath import find_font
from make_graphics_script import layout_text, LINE_H  # mesma regra de margem segura da legenda-impacto

CAP = 0.70  # altura da maiuscula / tamanho da fonte (Montserrat)


def render(lines, size, cy, st, W, H, font_path):
    font = ImageFont.truetype(find_font(font_path), size)
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d, ds = ImageDraw.Draw(img), ImageDraw.Draw(shadow)
    lh = size * LINE_H
    block = (len(lines) - 1) * lh + size * CAP
    base = cy - block / 2 + size * CAP  # baseline da 1a linha
    dy = st.get("shadow_dy", 4)
    for i, line in enumerate(lines):
        y = base + i * lh
        ds.text((W / 2, y + dy), line, font=font, fill=(0, 0, 0, int(255 * st.get("shadow_alpha", 0.55))), anchor="ms")
        d.text((W / 2, y), line, font=font, fill=(255, 255, 255, 255), anchor="ms")
    shadow = shadow.filter(ImageFilter.GaussianBlur(st.get("shadow_blur", 6)))
    return Image.alpha_composite(shadow, img)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("blocks")
    ap.add_argument("out")
    ap.add_argument("--style", default=os.path.join(HERE, "..", "style.json"))
    ap.add_argument("--track", type=int, default=1, help="indice 0-based da trilha de video")
    ap.add_argument("--bin", default="legenda_simples")
    ap.add_argument("--width", type=int, default=1080)
    ap.add_argument("--height", type=int, default=1920)
    ap.add_argument("--batch", type=int, default=20)
    ap.add_argument("--fps", type=float, default=30.0, help="fps da sequencia: tempos viram multiplos de 1 quadro")
    a = ap.parse_args()
    st = json.load(open(a.style, encoding="utf-8"))
    blocks = json.load(open(a.blocks, encoding="utf-8"))["blocks"]
    W, H = a.width, a.height
    safe_x, safe_y = st.get("safe_margin_x", 0.10), st.get("safe_margin_y", 0.10)
    max_w = (1 - 2 * safe_x - st.get("safe_tolerance", 0.02)) * W
    os.makedirs(a.out, exist_ok=True)
    clips = []
    for i, b in enumerate(blocks, 1):
        text, size, nl = layout_text(b["text"], st["mogrt_size"], st["font_path"], max_w, st["min_scale"])
        h = size * CAP + (nl - 1) * size * LINE_H
        lo, hi = safe_y * H + h / 2, (1 - safe_y) * H - h / 2
        cy = min(max(st["y_center"] * H, lo), hi) if lo <= hi else H / 2
        name = f"ls_{i:03d}.png"
        render(text.split("\r"), size, cy, st, W, H, st["font_path"]).save(os.path.join(a.out, name))
        # tempos no quadro exato: o Premiere ajusta o inicio do clipe ao quadro, entao a busca/aparo precisa da mesma grade
        fs, fe = round(b["start"] * a.fps) / a.fps, round(b["end"] * a.fps) / a.fps
        if fe <= fs:
            fe = fs + 1 / a.fps
        clips.append(dict(s=round(fs, 5), e=round(fe, 5), tr=a.track, t=text, z=size, y=round(cy / H, 5), nl=nl, png=name))
    json.dump(clips, open(os.path.join(a.out, "stills_clips.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    folder = os.path.abspath(a.out).replace("\\", "/")
    IMPORT = """(function(){
var p = app.project, bin = null;
for (var k=0;k<p.rootItem.children.numItems;k++){ var it = p.rootItem.children[k]; if (it.type === 2 && it.name === %s) bin = it; }
if (!bin) bin = p.rootItem.createBin(%s);
var files = %s, paths = [];
for (var i=0;i<files.length;i++) paths.push(new File(%s + '/' + files[i]).fsName);
var ok = p.importFiles(paths, true, bin, false);
return 'importados: ' + bin.children.numItems + ' de ' + files.length;
})()"""
    open(os.path.join(a.out, "stills_import.jsx"), "w", encoding="utf-8").write(
        IMPORT % (json.dumps(a.bin), json.dumps(a.bin), json.dumps([c["png"] for c in clips]), json.dumps(folder)))
    PLACE = """(function(){
var CLIPS = %s, p = app.project, seq = p.activeSequence, bin = null, ok = 0, out = [];
for (var k=0;k<p.rootItem.children.numItems;k++){ var it = p.rootItem.children[k]; if (it.type === 2 && it.name === %s) bin = it; }
if (!bin) return 'bin nao encontrado (rode stills_import.jsx antes)';
function find(name){ for (var i=0;i<bin.children.numItems;i++){ if (bin.children[i].name === name) return bin.children[i]; } return null; }
for (var i=0;i<CLIPS.length;i++){
  var c = CLIPS[i];
  try {
    var item = find(c.png); if (!item) { out.push(i + ': png nao importado'); continue; }
    var tr = seq.videoTracks[c.tr], t0 = new Time(); t0.seconds = c.s;
    tr.overwriteClip(item, t0);
    var clip = null;
    var bestD = 1e9;
    for (var j=0;j<tr.clips.numItems;j++){ var dd = Math.abs(tr.clips[j].start.seconds - c.s); if (dd < bestD) { bestD = dd; clip = tr.clips[j]; } }
    if (!clip || bestD > 0.05) { out.push(i + ': clipe nao achado (dist ' + bestD + ')'); continue; }
    var t1 = new Time(); t1.seconds = c.e; clip.end = t1;
    clip.name = 'simples ' + c.t.split(String.fromCharCode(13)).join(' ');
    ok++;
  } catch (e) { out.push(i + ': ' + e); }
}
return 'ok=' + ok + '/' + CLIPS.length + (out.length ? ' erros: ' + out.join(' | ') : '');
})()"""
    n = 0
    for s in range(0, len(clips), a.batch):
        n += 1
        open(os.path.join(a.out, f"stills_{n:02d}.jsx"), "w", encoding="utf-8").write(
            PLACE % (json.dumps(clips[s:s + a.batch], ensure_ascii=False), json.dumps(a.bin)))
    print(f"{len(clips)} PNGs + stills_import.jsx + {n} lotes em {a.out}")


if __name__ == "__main__":
    main()
