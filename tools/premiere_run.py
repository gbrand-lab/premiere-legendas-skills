#!/usr/bin/env python
"""Executa um arquivo ExtendScript (.jsx) no Premiere Pro aberto, por um bridge de arquivos CEP, e imprime a resposta.

Uso: python tools/premiere_run.py <arquivo.jsx|codigo> [--timeout 120] [--dir PASTA_DO_BRIDGE]

Como funciona: um painel CEP dentro do Premiere (ex.: o painel "MCP Bridge" do projeto adobe-premiere-pro-mcp) vigia uma pasta
(PREMIERE_TEMP_DIR; padrao <temp>/premiere-mcp-bridge). Este script grava `command-<id>.json` = {"id", "script", "timeoutMs"}
e espera `response-<id>.json` = {"success", "result"|"error"}. `bridge-heartbeat.json` com `t` (ms) recente = painel vivo.
Veja docs/PREMIERE-BRIDGE.md.
"""
import argparse, json, os, sys, tempfile, time, uuid

ap = argparse.ArgumentParser()
ap.add_argument("script", help="caminho de um .jsx ou o proprio codigo")
ap.add_argument("--timeout", type=int, default=120)
ap.add_argument("--dir", default=os.environ.get("PREMIERE_TEMP_DIR") or os.path.join(tempfile.gettempdir(), "premiere-mcp-bridge"))
a = ap.parse_args()

src = open(a.script, encoding="utf-8").read() if os.path.isfile(a.script) else a.script
hb = os.path.join(a.dir, "bridge-heartbeat.json")
try:
    age = time.time() - json.load(open(hb))["t"] / 1000
except Exception:
    sys.exit(f"Bridge nao encontrado em {a.dir}. Abra o painel CEP no Premiere (Janela > Extensoes) ou use --dir.")
if age > 15:
    sys.exit(f"Bridge sem sinal ha {age:.0f}s. Reabra o painel CEP no Premiere.")

cid = str(uuid.uuid4())
cmd, resp = (os.path.join(a.dir, f"{p}-{cid}.json") for p in ("command", "response"))
json.dump({"id": cid, "script": src, "timeoutMs": a.timeout * 1000}, open(cmd, "w", encoding="utf-8"))
t0 = time.time()
while time.time() - t0 < a.timeout + 5:
    if os.path.exists(resp):
        time.sleep(0.1)
        print(json.dumps(json.load(open(resp, encoding="utf-8")), ensure_ascii=False))
        sys.exit(0)
    time.sleep(0.3)
try:
    os.remove(cmd)
except OSError:
    pass
sys.exit("Tempo esgotado esperando resposta do Premiere.")
