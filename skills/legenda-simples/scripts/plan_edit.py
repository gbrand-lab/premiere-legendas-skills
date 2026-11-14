#!/usr/bin/env python
"""Transcricao do Premiere -> cortes dinamicos (sem pausas/respiros, zoom alternado) + frases da legenda
ja no tempo da sequencia CORTADA.

Uso: python -I plan_edit.py <transcricao.json do Premiere> <pasta_de_saida> [regras.json]
Gera na pasta: segs.json, clips.json (cortes + zoom), blocks.json (legenda, no tempo da sequencia cortada).
Depois: build_cut_script.py (monta a sequencia) e make_graphics_script.py (legendas).
"""
import json, os, re, sys, importlib.util

TR, D = sys.argv[1], sys.argv[2]
os.makedirs(D, exist_ok=True)
spec = importlib.util.spec_from_file_location(
    "pp", os.path.join(os.path.dirname(os.path.abspath(__file__)), "plan_phrases.py"))
pp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pp)

# --- parametros do corte (ajuste aqui)
GAP = 0.30          # pausa/respiro acima disso e cortada
PRE, POST = 0.05, 0.10   # folga antes/depois da fala em cada trecho mantido
ZOOM_ALT = 116      # zoom (%) dos clipes pares; os outros ficam em 100
SUB_MIN, SUB_MAX = 2.6, 4.8  # sub-corte (troca de zoom) em pontuacao apos SUB_MIN s, ou forcado em SUB_MAX s

raw = json.load(open(TR, encoding="utf-8"))
allw = []
for seg in raw["segments"]:
    for w in seg["words"]:
        allw.append(dict(t=w["text"].strip(), s=float(w["start"]),
                         e=float(w["start"]) + float(w["duration"]), c=float(w["confidence"])))
words = [w for w in allw if w["t"]]  # tira disfluencias (texto vazio = "ããh", respiro)

runs, cur = [], [words[0]]
for a, b in zip(words, words[1:]):
    if b["s"] - a["e"] > GAP:  # token vazio dentro do intervalo conta como corte
        runs.append(cur)
        cur = []
    cur.append(b)
runs.append(cur)

segs, t_new = [], 0.0
for r in runs:
    si, so = max(0.0, r[0]["s"] - PRE), r[-1]["e"] + POST
    if segs and si < segs[-1]["out"]:
        si = segs[-1]["out"]
    segs.append(dict(src_in=round(si, 3), out=round(so, 3), new_in=round(t_new, 3)))
    t_new += so - si
for s in segs:
    s["src_out"] = s.pop("out")


def seg_of(t):
    for s in segs:
        if s["src_in"] - 1e-6 <= t <= s["src_out"] + 1e-6:
            return s
    return min(segs, key=lambda s: min(abs(t - s["src_in"]), abs(t - s["src_out"])))


# --- legenda: frases no tempo original -> tempo cortado, depois ritmo de leitura
R = dict(pp.RULES)
R["auto_schedule"] = False
if len(sys.argv) > 3:  # 3o argumento opcional: JSON que sobrescreve RULES (ex.: {"max_words": 3})
    R.update(json.load(open(sys.argv[3], encoding="utf-8")))
phr = pp.plan(words, R)
out = []
for p in phr:
    a = seg_of(p["start"])
    b = seg_of(p["end"] - 0.15 - 1e-3 if p["end"] - 0.15 > p["start"] else p["start"])
    ns = a["new_in"] + max(p["start"], a["src_in"]) - a["src_in"]
    ne = b["new_in"] + min(p["end"], b["src_out"]) - b["src_in"]
    out.append(dict(start=round(ns, 3), end=round(max(ne, ns + 0.3), 3), text=p["text"], low_conf=p["low_conf"]))
for i in range(len(out) - 1):
    if out[i]["end"] > out[i + 1]["start"]:
        out[i]["end"] = out[i + 1]["start"]
out = pp.schedule(out, R)
for b in out:
    b["end"] = round(min(b["end"], t_new), 3)
fix = []
for b in out:  # sobra apertada no fim do video: cola na frase anterior
    if fix and b["end"] - b["start"] < 0.35:
        fix[-1]["text"] += " " + b["text"]
        fix[-1]["end"] = b["end"]
    else:
        fix.append(b)
out = fix
json.dump(dict(segs=segs, total=round(t_new, 3)), open(os.path.join(D, "segs.json"), "w"), indent=1)
json.dump(dict(blocks=out), open(os.path.join(D, "blocks.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("segmentos", len(segs), "duracao nova", round(t_new, 1), "de", round(words[-1]["e"], 1), "| frases", len(out))

# --- sub-cortes com troca de zoom dentro dos trechos longos (dinamismo), sem remover conteudo
clips = []
for s in segs:
    ws = [w for w in words if s["src_in"] - 1e-6 <= w["s"] and w["e"] <= s["src_out"] + 1e-6]
    start = s["src_in"]
    for i, w in enumerate(ws):
        last = i == len(ws) - 1
        el = w["e"] - start
        punct = bool(re.search(r"[.,?!;:]$", w["t"]))
        if not last and ((punct and el >= SUB_MIN) or el >= SUB_MAX):
            nxt = ws[i + 1]
            cut = round((w["e"] + nxt["s"]) / 2 if nxt["s"] > w["e"] else w["e"], 3)
            clips.append(dict(src_in=round(start, 3), src_out=cut))
            start = cut
    clips.append(dict(src_in=round(start, 3), src_out=s["src_out"]))
t = 0.0
for i, c in enumerate(clips):
    c["new_in"] = round(t, 3)
    t += c["src_out"] - c["src_in"]
    c["zoom"] = 100 if i % 2 == 0 else ZOOM_ALT
json.dump(dict(clips=clips, total=round(t, 3)), open(os.path.join(D, "clips.json"), "w"), indent=1)
print("clips", len(clips), "total", round(t, 2))
