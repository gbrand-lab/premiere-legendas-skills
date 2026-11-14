#!/usr/bin/env python
"""Transcricao -> frases curtas (ate 4 palavras) para a legenda "simples".

Uso:
  python -I plan_phrases.py <transcricao.json> <blocks.json> [--config regras.json]

Entrada aceita (igual a legenda-impacto):
  - JSON exportado pelo Premiere (segments[].words[] com text/start/duration/confidence)
  - lista simples [{"text":..., "start":..., "end":...}]

Regras: no maximo 4 palavras por frase, quebra em pontuacao e pausas, frases longas
sao divididas de forma equilibrada (5 -> 3+2, 7 -> 4+3, nunca 4+1), nunca termina em
palavra solta (o, de, que...). Texto mantido como transcrito (maiuscula inicial), sem
ponto/virgula no fim; "?" e "!" ficam.
"""
import argparse, json, math, re, sys, unicodedata

RULES = {
    "max_words": 4,
    "max_words_fast": 5,    # em trecho rapido (frase < fast_dur de fala) pode juntar ate N palavras para nao piscar
    "fast_dur": 0.9,        # duracao da fala (s) abaixo da qual a frase e considerada rapida demais para ler
    "min_words": 3,         # frase com menos palavras que isso tenta juntar na vizinha (se couber em max_words)
    "schedule_mode": "sync",  # "sync" = legenda NASCE e MORRE junto com a fala (padrao); "lag" = tempo de leitura, atrasa a fala
    "min_dur": 0.80,        # tempo minimo na tela (s); no modo sync so estende para dentro do silencio, nunca atrasa a proxima frase
    "min_hold": 0.50,       # sync: frase com < min_hold s no total e colada na vizinha (nao pisca)
    "floor_dur": 0.7,       # piso quando o atraso ja passou de max_lag (a frase nao some antes disso)
    "max_lag": 0.9,         # atraso maximo (s) da legenda em relacao a fala, ate recuperar numa pausa
    "comma_min_words": 3,   # virgula so corta a frase se ja houver ao menos N palavras (evita "Entao" sozinho)
    "pause": 0.55,          # pausa (s) que forca nova frase
    "tail": 0.30,           # quanto a frase fica na tela depois da ultima palavra (s)
    "close_gap": 0.60,      # se a proxima comeca em ate isso, estende ate ela (sem piscar)
    "stop_end": ["de", "da", "do", "das", "dos", "a", "o", "as", "os", "um", "uma", "e", "em", "no",
                 "na", "para", "com", "por", "se", "ou", "que", "quem", "como", "onde", "quando",
                 "porque", "esse", "essa", "esses", "essas", "aquele", "meu", "seu", "teu", "tua",
                 "minha", "sua", "nosso", "nossa", "nao", "ja", "mais", "muito", "ele", "ela", "eu",
                 "tu", "voce", "vai", "tem", "ter", "foi", "era"],
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


def segments(words, R):
    """Corta em pontuacao forte, virgula e pausa."""
    segs, cur = [], []
    for w in words:
        if cur and w["s"] - cur[-1]["e"] > R["pause"]:
            segs.append(cur)
            cur = []
        cur.append(w)
        if re.search(r"[.?!…]$", w["t"]) or (re.search(r"[,;:]$", w["t"]) and len(cur) >= R["comma_min_words"]):
            segs.append(cur)
            cur = []
    if cur:
        segs.append(cur)
    return segs


def split_even(seg, R):
    """Divide um segmento em frases de 3-4 palavras (programacao dinamica): evita frase de 1-2 palavras,
    evita terminar em palavra solta (o, de, que...) e prefere cortar onde ha virgula ou pausa."""
    n, m = len(seg), R["max_words"]
    if n <= m:
        return [seg]
    SIZE_COST = {1: 6.0, 2: 3.0, 3: 0.0, 4: 0.4}
    INF = float("inf")
    best = [INF] * (n + 1)
    prev = [0] * (n + 1)
    best[0] = 0.0
    for k in range(1, n + 1):
        for size in range(1, min(m, k) + 1):
            j = k - size
            if best[j] == INF:
                continue
            last = seg[k - 1]
            cost = SIZE_COST.get(size, 9.0)
            if k < n and norm(last["t"]) in R["stop_end"]:
                cost += 3.0                      # nao termina em palavra solta
            if k < n and re.search(r"[,;:]$", last["t"]):
                cost -= 1.0                      # corte natural na virgula
            if k < n and seg[k]["s"] - last["e"] > 0.25:
                cost -= 0.6                      # ou numa pausa
            if best[j] + cost < best[k]:
                best[k] = best[j] + cost
                prev[k] = j
    cuts, k = [], n
    while k > 0:
        cuts.append((prev[k], k))
        k = prev[k]
    return [seg[a:b] for a, b in reversed(cuts)]


def clean(text):
    # tira ponto/virgula/;/: do fim; "?" e "!" ficam
    return re.sub(r"[.,;:…]+$", "", text.strip())


def plan(words, R):
    phrases = []
    for seg in segments(words, R):
        phrases.extend(split_even(seg, R))
    # segmento de 1 palavra sem pontuacao forte gruda na frase vizinha se couber
    merged = []
    for p in phrases:
        if (merged and len(p) == 1 and len(merged[-1]) < R["max_words"]
                and p[0]["s"] - merged[-1][-1]["e"] < R["pause"]
                and not re.search(r"[.?!…]$", merged[-1][-1]["t"])):
            merged[-1].extend(p)
        else:
            merged.append(p)
    # frase curta demais (< min_words) gruda na vizinha quando o total cabe em max_words
    changed = True
    while changed:
        changed = False
        for i, p in enumerate(merged):
            if len(p) >= R["min_words"]:
                continue
            for j in (i + 1, i - 1):
                if 0 <= j < len(merged) and len(p) + len(merged[j]) <= R["max_words"]:
                    a, b = (i, j) if i < j else (j, i)
                    if abs(merged[b][0]["s"] - merged[a][-1]["e"]) < 1.0:
                        merged[a:b + 1] = [merged[a] + merged[b]]
                        changed = True
                        break
            if changed:
                break
    # trecho rapido: frase que a fala atravessa em menos de fast_dur junta com a vizinha (ate max_words_fast)
    changed = True
    while changed:
        changed = False
        for i, p in enumerate(merged):
            if p[-1]["e"] - p[0]["s"] >= R["fast_dur"]:
                continue
            cands = [j for j in (i - 1, i + 1) if 0 <= j < len(merged)
                     and len(p) + len(merged[j]) <= R["max_words_fast"]
                     and abs(merged[max(i, j)][0]["s"] - merged[min(i, j)][-1]["e"]) < 0.6
                     and not re.search(r"[.?!…]$", merged[min(i, j)][-1]["t"])]
            if cands:
                j = min(cands, key=lambda j: len(merged[j]))
                a, b = min(i, j), max(i, j)
                merged[a:b + 1] = [merged[a] + merged[b]]
                changed = True
                break
    out = []
    for ws in merged:
        words = [clean(w["t"]) if i == len(ws) - 1 else w["t"] for i, w in enumerate(ws)]
        out.append(dict(start=round(ws[0]["s"], 3), end=round(ws[-1]["e"], 3), text=" ".join(words),
                        low_conf=[w["t"] for w in ws if w["c"] < 0.75]))
    for i, b in enumerate(out):
        nxt = out[i + 1]["start"] if i + 1 < len(out) else None
        end = b["end"] + R["tail"]
        if nxt is not None:
            end = nxt if nxt - b["end"] <= R["close_gap"] else min(end, nxt)
        b["end"] = round(end, 3)
    return schedule(out, R) if R.get("auto_schedule", True) else out


def _schedule_sync(blocks, R):
    """Legenda sincronizada com a fala: START = inicio da 1a palavra, sem atraso nenhum. END = fim da ultima palavra
    + tail, estendido ate min_dur SO se houver silencio depois (nunca invade a proxima frase). Frase que ficaria com
    menos de min_hold s (fala muito rapida) e colada na anterior em vez de piscar."""
    for i, b in enumerate(blocks):
        nxt = blocks[i + 1]["start"] if i + 1 < len(blocks) else None
        end = max(b["end"], b["start"] + R["min_dur"])
        if nxt is not None:
            end = min(end, nxt)
        b["end"] = round(end, 3)
    out = []
    for b in blocks:
        # so cola se couber em max_words_fast e a anterior nao fechou uma frase (. ? !) - nunca estoura o limite de palavras
        if (out and b["end"] - b["start"] < R["min_hold"]
                and len(out[-1]["text"].split()) + len(b["text"].split()) <= R["max_words_fast"]
                and not re.search(r"[.?!…]$", out[-1]["text"])):
            out[-1]["text"] += " " + b["text"]
            out[-1]["end"] = max(out[-1]["end"], b["end"])
        else:
            out.append(b)
    blocks[:] = out
    return blocks


def schedule(blocks, R):
    """Tempo de leitura: cada frase fica ao menos min_dur na tela. Quando a fala e mais rapida que a leitura,
    a frase seguinte entra um pouco depois (atraso), e o atraso se recupera nas pausas. O atraso nunca passa de
    max_lag: nesse caso a frase anterior e encurtada (ate floor_dur, ou menos so se nao houver jeito)."""
    if R.get("schedule_mode", "sync") == "sync":
        return _schedule_sync(blocks, R)
    prev = None
    for b in blocks:
        ns, ne = b["start"], b["end"]
        start = prev["end"] if prev else ns
        start = max(ns, start)
        if start - ns > R["max_lag"]:
            start = ns + R["max_lag"]
            prev["end"] = round(max(start, prev["start"] + 0.4), 3)
            start = max(start, prev["end"])
        dur = max(ne - ns, R["min_dur"])
        b["start"], b["end"] = round(start, 3), round(start + dur, 3)
        prev = b
    # frase que sobrou com menos de 0.35 s (fim apertado do video) e colada na anterior: nunca pisca na tela
    out = []
    for b in blocks:
        if out and b["end"] - b["start"] < 0.35:
            out[-1]["text"] += " " + b["text"]
            out[-1]["end"] = max(out[-1]["end"], b["end"])
        else:
            out.append(b)
    blocks[:] = out
    return blocks


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
    print(f"{len(blocks)} frases")
    for b in blocks:
        flag = "  [conferir: " + ", ".join(b["low_conf"]) + "]" if b["low_conf"] else ""
        print(f'{b["start"]:7.2f}-{b["end"]:6.2f} | {b["text"]}{flag}')
