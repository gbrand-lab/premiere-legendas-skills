# premiere-legendas-skills

Duas **skills do Claude Code** que legendam (e, opcionalmente, editam) videos verticais 9x16 no **Adobe Premiere Pro** a partir da transcricao do proprio Premiere. Tudo roda por scripts Python + ExtendScript; o Claude conduz o passo a passo.

| Skill | Estilo | Animacao | Edita o texto no Premiere? |
|---|---|---|---|
| [`legenda-impacto`](skills/legenda-impacto/SKILL.md) | Maiuscula Impact, linha pequena + linha grande (branca/vermelha) alternando com legenda reta | palavra por palavra, sorteada | sim (`.mogrt`) |
| [`legenda-simples`](skills/legenda-simples/SKILL.md) | Frases de 3-4 palavras, Montserrat Bold branca com sombra suave, minuscula com inicial maiuscula | **nenhuma** (aparece inteira, corte seco) | nao (PNG por frase) |

Regras comuns:
- **Margem segura**: nada de texto fora do *title safe* do Premiere (80% x 80%); largura util 78%. Linha que nao cabe encolhe e, se preciso, quebra em 2-3 linhas. Cada skill tem um verificador (`check_margins.py`).
- A `legenda-simples` **nasce e morre junto com a fala** (sincronizada com a 1a/ultima palavra) e traz um pipeline opcional de **edicao dinamica**: corta pausas/respiros, faz sub-cortes e alterna zoom 100%/116%.

> Escrito em portugues (BR). / Portuguese (BR) docs: two Claude Code skills that caption vertical videos in Premiere Pro from Premiere's own transcript.

## Requisitos
- **Adobe Premiere Pro** com Transcricao (testado no 2027 / 27.0, Windows).
- **Python 3.9+** e `pip install -r requirements.txt` (so Pillow).
- **Fontes** instaladas: [Montserrat](https://fonts.google.com/specimen/Montserrat) (legenda-simples) e **Impact** (ja vem no Windows/macOS; legenda-impacto). Fonte fora do lugar padrao: defina `CAPTION_FONT_DIR`.
- **Uma forma de rodar ExtendScript no Premiere** (ver [docs/PREMIERE-BRIDGE.md](docs/PREMIERE-BRIDGE.md)): um MCP do Premiere com `execute_extendscript`, ou o bridge de arquivos CEP + [`tools/premiere_run.py`](tools/premiere_run.py).
- [Claude Code](https://claude.com/claude-code) para usar como skill (os scripts tambem funcionam sozinhos, pela linha de comando).
- Apenas a `legenda-impacto`: seu pacote de `.mogrt` palavra por palavra em `skills/legenda-impacto/assets/` (**nao incluido**, ver o `LEIA-ME.md` da pasta).

## Instalar (como skill do Claude Code)
```bash
git clone https://github.com/gbrand-lab/premiere-legendas-skills.git
cp -r premiere-legendas-skills/skills/legenda-simples ~/.claude/skills/
cp -r premiere-legendas-skills/skills/legenda-impacto ~/.claude/skills/
pip install -r premiere-legendas-skills/requirements.txt
```
No Windows, a pasta de skills e `%USERPROFILE%\.claude\skills`. Depois, peca ao Claude: *"legenda esse video com a legenda simples"* ou *"aplica a legenda impacto nessa sequencia"* (exporte antes a transcricao: **Texto > Transcricao > ... > Exportar**).

## Usar sem o Claude (linha de comando)
```bash
# legenda simples: frases -> PNGs sem animacao + scripts para o Premiere
python -I skills/legenda-simples/scripts/plan_phrases.py transcricao.json saida/blocks.json
python -I skills/legenda-simples/scripts/make_stills.py saida/blocks.json saida/png --track 1
python -I skills/legenda-simples/scripts/check_margins.py saida/png/stills_clips.json
python tools/premiere_run.py saida/png/stills_import.jsx      # importa os PNGs
python tools/premiere_run.py saida/png/stills_01.jsx          # ...um lote por vez

# edicao dinamica completa (cortes + zoom + legenda): ver skills/legenda-simples/SKILL.md, Opcao B
```

## Testar sem o Premiere
```bash
python tests/smoke_test.py
```
Roda o pipeline das duas legendas numa transcricao de exemplo (`examples/sample_transcript.json`, texto inventado) e confere a margem segura. Se passar, o ambiente (Python, Pillow e fontes) esta certo.

## Como funciona (resumo)
1. A transcricao exportada do Premiere (palavras com tempo) vira **blocos/frases** com regras de corte (pontuacao, pausas, palavras soltas).
2. Os blocos viram **gráficos** posicionados dentro da margem segura (`.mogrt` na impacto; PNG na simples) e **scripts ExtendScript** em lotes pequenos (lote grande trava o Premiere).
3. Os lotes sao executados no Premiere aberto, um por vez; o projeto e conferido lendo de volta o que foi criado.

## Limitacoes conhecidas
- Testado so no Premiere 27 / Windows; a API (ExtendScript/QE) muda entre versoes.
- Exportar quadro via QE (`exportFramePNG`) falhou nos testes; a conferencia e por leitura de dados e pelos PNGs/guias de margem.
- A cor do `.mogrt` nao e alteravel por script (por isso os vermelhos usam o efeito "Equilibrio de cor (RGB)").
- A transcricao do Premiere pode errar palavras; revise o `blocks.json` antes de aplicar.

## Licenca
[MIT](LICENSE). Fontes, `.mogrt` e marcas citadas sao de seus respectivos donos e nao fazem parte deste repositorio.
