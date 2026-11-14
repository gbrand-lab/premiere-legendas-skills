#!/usr/bin/env python
"""Teste de fumaca SEM Premiere: roda o pipeline das duas legendas na transcricao de exemplo e confere a margem segura.

Uso: python tests/smoke_test.py        (precisa de Pillow e das fontes Montserrat Bold e Impact instaladas)
"""
import json, os, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SK = os.path.join(ROOT, "skills")
TR = os.path.join(ROOT, "examples", "sample_transcript.json")
ENV = dict(os.environ, PYTHONIOENCODING="utf-8")


def run(*args):
    r = subprocess.run([sys.executable, "-I", *args], capture_output=True, text=True, env=ENV)
    if r.returncode:
        print(r.stdout + r.stderr)
        sys.exit(f"FALHOU: {' '.join(os.path.basename(a) for a in args[:2])}")
    return r.stdout.strip()


with tempfile.TemporaryDirectory() as tmp:
    # --- legenda simples (PNG, sem animacao)
    S = os.path.join(SK, "legenda-simples", "scripts")
    run(os.path.join(S, "plan_phrases.py"), TR, os.path.join(tmp, "simples.json"))
    blocks = json.load(open(os.path.join(tmp, "simples.json"), encoding="utf-8"))["blocks"]
    assert blocks and all(len(b["text"].split()) <= 6 for b in blocks), "frases fora do limite de palavras"
    assert all(b["end"] > b["start"] for b in blocks), "frase com duracao invalida"
    assert all(blocks[i]["end"] <= blocks[i + 1]["start"] + 1e-6 for i in range(len(blocks) - 1)), "frases sobrepostas"
    run(os.path.join(S, "make_stills.py"), os.path.join(tmp, "simples.json"), os.path.join(tmp, "png"))
    print(run(os.path.join(S, "check_margins.py"), os.path.join(tmp, "png", "stills_clips.json")))
    # --- legenda impacto (.mogrt) — usa um .mogrt "de mentira" so para gerar os scripts
    I = os.path.join(SK, "legenda-impacto", "scripts")
    fake = os.path.join(tmp, "fake.mogrt")
    open(fake, "wb").write(b"x")
    run(os.path.join(I, "plan_blocks.py"), TR, os.path.join(tmp, "impacto.json"))
    run(os.path.join(I, "make_graphics_script.py"), os.path.join(tmp, "impacto.json"), os.path.join(tmp, "lote.js"),
        "--tracks", "1,2,3", "--mogrt", fake)
    print(run(os.path.join(I, "check_margins.py"), os.path.join(tmp, "lote_clips.json")))
    # --- edicao dinamica (cortes + zoom) e script de montagem
    run(os.path.join(S, "plan_edit.py"), TR, os.path.join(tmp, "edit"))
    clips = json.load(open(os.path.join(tmp, "edit", "clips.json")))["clips"]
    assert clips and all(c["src_out"] > c["src_in"] for c in clips), "cortes invalidos"
    run(os.path.join(S, "build_cut_script.py"), os.path.join(tmp, "edit", "clips.json"), os.path.join(tmp, "edit"),
        "--item", "video.mov", "--name", "teste")
    assert os.path.getsize(os.path.join(tmp, "edit", "montar.jsx")) > 500
print("OK: pipeline das duas legendas funcionando e dentro da margem segura")
