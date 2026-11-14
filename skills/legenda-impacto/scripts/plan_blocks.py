#!/usr/bin/env python
"""Transcricao -> blocos de legenda "impacto" (linha pequena + linha grande, branco/vermelho).

Uso:
  python -I plan_blocks.py <transcricao.json> <blocks.json> [--config regras.json]

Entrada aceita:
  - JSON exportado pelo Premiere (segments[].words[] com text/start/duration/confidence)
  - lista simples [{"text":..., "start":..., "end":...}]

Nada aqui e especifico de um video. Tudo que da para ajustar esta em RULES (ou --config).
"""
import json, re, sys, argparse, unicodedata

RULES = {
    "max_words": 6,          # maximo de palavras por bloco
    "max_dur": 3.3,          # duracao maxima de um bloco (s)
    "pause": 0.45,           # pausa (s) que forca novo bloco
    "min_single_dur": 0.4,   # bloco de 1 palavra mais curto que isso gruda no anterior
    "tail": 0.2,             # quanto o bloco fica na tela depois da ultima palavra (s)
    "close_gap": 0.35,       # se o proximo bloco comeca em ate isso, estende ate ele
    "red_max_run": 2,        # no maximo N blocos vermelhos seguidos
    "red_min_every": 4,      # se passaram N blocos sem vermelho, forca um (se tiver linha grande)
    # palavras que puxam destaque (sem acento, minusculas). Generico para qualquer tema.
    "strong": [
        "dinheiro", "lucro", "prejuizo", "perde", "perder", "perdendo", "perda", "ganha", "ganhar",
        "faturamento", "fatura", "vendas", "venda", "cliente", "erro", "errado", "errados", "nunca",
        "sempre", "problema", "sorte", "risco", "imposto", "caro", "gratis", "milhao", "milhoes",
        "mil", "zero", "tudo", "nada", "segredo", "verdade", "cuidado", "dobra", "dobrar", "quebrar",
        "quebra", "morrer", "falir", "resultado", "crescer", "cresce", "pagar", "importante",
    ],
    "stop_start": ["de", "da", "do", "das", "dos", "e", "ou", "mas", "em", "no", "na"],
    "stop_end": ["de", "da", "do", "das", "dos", "a", "o", "as", "os", "um", "uma", "e", "em", "no",
                 "na", "para", "com", "por", "se", "ou", "que", "quem", "como", "onde", "quando", "porque",
                 "esse", "essa", "esses", "essas", "aquele", "meu", "seu", "teu", "tua", "minha", "sua",
                 "nosso", "nossa", "nao", "ja", "mais", "muito", "ele", "ela", "eu", "tu", "voce", "vai",
                 "tem", "ter", "foi", "e", "era"],
    "filler": ["ne", "entao", "ai", "ta", "ne?", "ok", "ah", "ou", "mas", "e", "ai,"],
}


def norm(t):
    t = unicodedata.normalize("NFD", t.lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9$]", "", t)


def load_words(path):
    d = json.load(open(path, encoding="utf-8"))
    out = []
    if isinstance(d, dict) and "segments" in d:
        for seg in d["segments"]:
            for w in seg["words"]:
                if w.get("type", "word") != "word" or not str(w.get("text", "")).strip():
                    continue
                out.append(dict(t=w["text"], s=float(w["start"]), e=float(w["start"]) + float(w["duration"]),
                                c=float(w.get("confidence", 1))))
    else:
        for w in d:
            out.append(dict(t=w["text"], s=float(w["start"]), e=float(w["end"]), c=float(w.get("confidence", 1))))
    return out


def is_strong(w, R):
    n = norm(w["t"])
    return bool(re.search(r"\d", w["t"])) or "r$" in w["t"].lower() or n in R["strong"]


def chunk(words, R):
    blocks, cur = [], []

    def flush():
        nonlocal cur
        if cur:
            blocks.append(cur)
            cur = []

    for w in words:
        if cur and (w["s"] - cur[-1]["e"] > R["pause"] or len(cur) >= R["max_words"] or w["e"] - cur[0]["s"] > R["max_dur"]):
            flush()
        cur.append(w)
        if re.search(r"[.?!…]$", w["t"]) or (w["t"].endswith(",") and len(cur) >= 2):
            flush()
    flush()
    # nao deixa palavra solta no fim do bloco (o, de, que, esse...): ela vai para o inicio do proximo
    for i in range(len(blocks) - 1):
        b = blocks[i]
        while (len(b) > 2 and norm(b[-1]["t"]) in R["stop_end"]
               and not re.search(r"[.,?!…]$", b[-1]["t"]) and b[-1]["s"] - b[-2]["e"] < R["pause"]):
            blocks[i + 1].insert(0, b.pop())
    # gruda blocos de 1 palavra muito curtos no anterior
    merged = []
    for b in blocks:
        if (merged and len(b) == 1 and (b[0]["e"] - b[0]["s"]) < R["min_single_dur"]
                and b[0]["s"] - merged[-1][-1]["e"] < 0.3 and len(merged[-1]) < R["max_words"] + 1
                and not re.search(r"[.?!…]$", merged[-1][-1]["t"])):
            merged[-1].extend(b)
        else:
            merged.append(b)
    return merged


def split_two(ws, R):
    """Escolhe quantas palavras vao na linha grande (k) e onde cortar."""
    n = len(ws)
    base = 2 if n <= 5 else 3
    strong_idx = [i for i, w in enumerate(ws) if is_strong(w, R)]
    # primeira palavra forte -> grande em cima (1 palavra)
    if strong_idx and strong_idx[0] == 0 and n >= 4:
        return "big_above", 1
    if strong_idx and strong_idx[-1] >= n - 3:
        base = n - strong_idx[-1] if n - strong_idx[-1] >= 1 else base
        base = max(base, 1)
    for k in [base, base + 1, base - 1, base + 2]:
        if k < 1 or k > n - 1:
            continue
        small_last = norm(ws[n - k - 1]["t"])
        big_first = norm(ws[n - k]["t"])
        if small_last in R["stop_end"] or big_first in R["stop_start"]:
            continue
        return "big_below", k
    return "big_below", min(base, n - 1)


def plan(words, R):
    blocks = chunk(words, R)
    out, prev_single, run_red, since_red = [], False, 0, 0
    for idx, ws in enumerate(blocks):
        n = len(ws)
        txt = lambda arr: " ".join(w["t"] for w in arr).upper()
        strong_any = [is_strong(w, R) for w in ws]
        if n <= 2:
            if all(norm(w["t"]) in R["filler"] for w in ws):
                layout, small, big = "single_small", txt(ws), ""
            else:
                layout, small, big = "single_big", "", txt(ws)
        elif n == 3 and not prev_single:
            layout, small, big = "single_big", "", txt(ws)
        elif n == 3:
            layout, k = "big_below", 1
            small, big = txt(ws[:-k]), txt(ws[-k:])
        else:
            layout, k = split_two(ws, R)
            if layout == "big_above":
                big, small = txt(ws[:k]), txt(ws[k:])
            else:
                small, big = txt(ws[:-k]), txt(ws[-k:])
        prev_single = layout.startswith("single")
        # cor
        if layout == "single_small":
            color = "white"
        else:
            if layout == "big_above":
                big_ws = ws[:k]
            elif layout == "big_below":
                big_ws = ws[-k:]
            else:
                big_ws = ws
            want_red = any(is_strong(w, R) for w in big_ws)
            if not want_red and since_red >= R["red_min_every"] and layout != "single_small":
                want_red = True
            if want_red and run_red >= R["red_max_run"]:
                want_red = False
            color = "red" if want_red else "white"
        run_red = run_red + 1 if color == "red" else 0
        since_red = 0 if color == "red" else since_red + 1
        out.append(dict(start=round(ws[0]["s"], 3), end=round(ws[-1]["e"], 3), layout=layout,
                        small=small, big=big, color=color,
                        low_conf=[w["t"] for w in ws if w["c"] < 0.75]))
    # tempos de saida
    for i, b in enumerate(out):
        nxt = out[i + 1]["start"] if i + 1 < len(out) else None
        end = b["end"] + R["tail"]
        if nxt is not None:
            end = nxt if nxt - b["end"] <= R["close_gap"] else min(end, nxt)
        b["end"] = round(end, 3)
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("transcript")
    ap.add_argument("out")
    ap.add_argument("--config", help="JSON que sobrescreve RULES")
    a = ap.parse_args()
    R = dict(RULES)
    if a.config:
        R.update(json.load(open(a.config, encoding="utf-8")))
    blocks = plan(load_words(a.transcript), R)
    json.dump({"blocks": blocks}, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    reds = sum(b["color"] == "red" for b in blocks)
    kinds = {}
    for b in blocks:
        kinds[b["layout"]] = kinds.get(b["layout"], 0) + 1
    print(f"{len(blocks)} blocos | vermelhos: {reds} | layouts: {kinds}")
    for b in blocks:
        flag = "  [conferir: " + ", ".join(b["low_conf"]) + "]" if b["low_conf"] else ""
        print(f'{b["start"]:7.2f}-{b["end"]:6.2f} {b["layout"]:12} {b["color"]:5} | {b["small"]} / {b["big"]}{flag}')
