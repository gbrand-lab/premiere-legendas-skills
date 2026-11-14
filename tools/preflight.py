#!/usr/bin/env python
"""Checagem rapida do computador ANTES de legendar: Python/Pillow, fontes INSTALADAS no sistema, bridge do Premiere e
tamanho da sequencia ativa. Existe porque a causa mais comum de "a legenda saiu da margem" em outro PC e: fonte nao
instalada (o Premiere troca por outra mais larga) ou sequencia que nao e 1080x1920.

Uso: python tools/preflight.py
"""
import json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "skills", "legenda-simples", "scripts"))
ok_all = True


def say(ok, msg):
    global ok_all
    ok_all = ok_all and ok
    print(("[OK]    " if ok else "[FALTA] ") + msg)


try:
    import PIL
    say(True, f"Pillow {PIL.__version__}")
except ImportError:
    say(False, "Pillow nao instalado: pip install -r requirements.txt")

# fontes instaladas NO SISTEMA (ignora as copias dentro do repositorio: o Premiere nao le essas)
import fontpath
sysdirs = [d for d in fontpath._dirs() if os.path.abspath(d).find(os.path.abspath(ROOT)) != 0]
for font, quem in (("Montserrat-Bold.ttf", "legenda-simples"), ("impact.ttf", "legenda-impacto"), ("Anton-Regular.ttf", "legenda-impacto (opcional)")):
    found = None
    for d in sysdirs:
        for root, _x, files in os.walk(d):
            if any(f.lower() == font.lower() for f in files):
                found = os.path.join(root, font)
                break
        if found:
            break
    if found:
        say(True, f"fonte {font} instalada ({quem})")
    elif "opcional" in quem:
        print(f"[aviso] fonte {font} nao instalada ({quem}); o arquivo esta em skills/legenda-impacto/fonts/")
    else:
        say(False, f"fonte {font} NAO instalada ({quem}). Instale (clique direito > Instalar para todos os usuarios) e reinicie o Premiere.")

# bridge + sequencia ativa
jsx = ("(function(){var s=app.project.activeSequence; if(!s) return JSON.stringify({err:'nenhuma sequencia ativa'});"
       "return JSON.stringify({name:s.name,w:s.frameSizeHorizontal,h:s.frameSizeVertical,v:s.videoTracks.numTracks,ver:app.version});})()")
r = subprocess.run([sys.executable, os.path.join(HERE, "premiere_run.py"), jsx, "--timeout", "20"], capture_output=True, text=True)
if r.returncode:
    say(False, "bridge do Premiere: " + (r.stderr.strip() or r.stdout.strip()))
else:
    try:
        res = json.loads(r.stdout)["result"]
        info = json.loads(res) if isinstance(res, str) else res
        if "err" in info:
            say(False, "Premiere: " + info["err"])
        else:
            say(True, f"Premiere {info['ver']} | sequencia ativa \"{info['name']}\" {info['w']}x{info['h']}")
            if (info["w"], info["h"]) != (1080, 1920):
                say(False, f"a sequencia e {info['w']}x{info['h']}, nao 1080x1920: passe --width {info['w']} --height {info['h']} "
                           "aos geradores (make_graphics_script.py / make_stills.py) ou use uma sequencia 1080x1920")
    except Exception as e:
        say(False, f"resposta inesperada do bridge: {e}: {r.stdout[:200]}")

print("\nTudo certo." if ok_all else "\nCorrija os itens [FALTA] antes de legendar.")
sys.exit(0 if ok_all else 1)
