---
name: legenda-simples
description: Legenda "simples" para videos verticais 9x16 no Premiere Pro — frases curtas (3-4 palavras, ate 5 em trecho rapido), uma linha, branca com sombra suave, Montserrat Bold, maiuscula so no inicio da frase, SEM animacao de entrada (aparece inteira e some em corte seco), sincronizada com a fala e dentro da margem segura. Inclui o pipeline de edicao dinamica (corta pausas/respiros e alterna zoom). Estilo de cortes de podcast. USE quando o usuario pedir "legenda simples", "legenda de podcast", "legenda por frase", "o modelo simples" ou "edita esse video com a legenda simples". Para o estilo grande/vermelho/palavra por palavra use a legenda-impacto.
---

# Legenda Simples — frases curtas, sem animacao, no tempo da fala

Uma frase por vez, texto branco em negrito, **minuscula com inicial maiuscula** (como transcrito), sem fundo, sombra suave, no terco de baixo, sem vermelho e **sem animacao de entrada**. Ex.: "O problema é que" / "sem prática".

## Pre-requisitos
- Premiere Pro (testado no 2027/27.0; ExtendScript) e Python 3.9+ com `pip install -r requirements.txt` (Pillow).
- Uma forma de executar ExtendScript no Premiere (MCP com `execute_extendscript` ou o bridge CEP por arquivo) — ver `docs/PREMIERE-BRIDGE.md` na raiz do repositorio.
- Fonte **Montserrat Bold INSTALADA no sistema** (o Premiere precisa dela; o `.ttf` esta em `fonts/` — clique direito > Instalar para todos os usuarios e reinicie o Premiere). Se um script nao achar a fonte, defina `CAPTION_FONT_DIR`.
- O modo padrao (PNG) **nao precisa de `.mogrt`**. A alternativa `.mogrt` usa `assets/Simple_Text_WbW.mogrt` (incluido; uso interno).

## Parametros (fonte da verdade: `style.json` e `RULES` em `scripts/plan_phrases.py`)
- 9x16 (1080x1920). Montserrat Bold 66 px, branco, sombra suave (blur 6, dy 4, 55%). `y_center` 0,70.
- **Sem animacao de entrada**: cada frase e um **PNG transparente 1080x1920** (`make_stills.py`) que aparece inteiro no 1o quadro e some em corte seco. O `.mogrt` palavra por palavra nao serve: a entrada e embutida (so existem "Out Animation" e "Anim Speed" 50-500, nao "In Animation"). Contrapartida do PNG: o texto nao e editavel no Premiere — para corrigir, edite `blocks.json` e gere de novo (segundos).
- Frase de **3-4 palavras**, por programacao dinamica: evita 1-2 palavras soltas, nao termina em "o/de/que...", prefere cortar em virgula ou pausa; virgula so corta com ao menos 3 palavras. Em fala rapida (frase atravessada em < 0,9 s) junta ate **5 palavras**, sem atravessar fim de frase (. ? !).
- **Margem segura**: nada fora do title safe do Premiere (80% x 80%); largura util 78% (842 px em 1080), bloco dentro de 10%-90% da altura. O texto encolhe ate `min_scale` e, se nao couber, quebra em 2 linhas; tamanho arredondado para BAIXO. Conferir com `check_margins.py` (deve dar `fora da margem: 0`).
- Entrega: **editar direto na sequencia indicada (sem copia)**, a menos que o usuario peca copia.

## Tempo na tela = tempo da fala (modo `sync`, padrao)
- A frase **nasce no inicio da 1a palavra falada** (atraso zero) e **morre no fim da ultima + `tail` 0,3 s**, estendida ate `min_dur` 0,8 s **so se houver silencio depois** (nunca invade a proxima frase). Frase que ficaria < 0,5 s cola na anterior somente se couber em 5 palavras e a anterior nao fechou uma frase.
- **Nota de projeto**: existe tambem o modo `schedule_mode: "lag"` (tempo de leitura: cada frase fica ao menos ~0,9 s e, se a fala for mais rapida, a seguinte entra depois, ate 0,9 s). Ele descola a legenda da voz (inicio e fim deixam de coincidir e a duracao varia sem relacao com o que e falado), por isso o padrao e `sync`. Use `lag` so se o usuario pedir leitura mais lenta (`--config` com `{"schedule_mode":"lag"}`).
- Limite honesto: fala muito densa (~3,6 palavras/s, picos de 6/s) faz algumas frases ficarem curtas (0,36-0,8 s). E a fala, nao a legenda.

## Opcao A — so legenda numa sequencia ja editada
1. Confirmar o projeto/sequencia com o usuario e deixa-la ativa.
2. Transcricao: JSON exportado do Premiere (Texto > Transcricao > ... > Exportar; fica em Documentos "<sequencia>.json").
3. `PYTHONIOENCODING=utf-8 python -I <skill>/scripts/plan_phrases.py <transcricao.json> <pasta>/blocks.json`; mostre a lista e as palavras `[conferir]`.
4. `python -I <skill>/scripts/make_stills.py <pasta>/blocks.json <pasta>/png --track 1` (gera PNGs + JSX; use uma pasta NOVA a cada geracao — o Premiere trava os PNGs ja importados) e `python -I <skill>/scripts/check_margins.py <pasta>/png/stills_clips.json`.
5. No Premiere, com a sequencia ativa: rodar `stills_import.jsx` (importa os PNGs num bin) e em seguida `stills_01.jsx...` um por vez (`ok=20/20`). Os tempos ja saem na grade de quadros (`--fps`, padrao 30).

## Opcao B — edicao dinamica completa (cortes + zoom + legenda)
1. Importar o video no projeto e ter a transcricao do Premiere.
2. `python -I <skill>/scripts/plan_edit.py <transcricao.json> <pasta>`: tira pausas/respiros > 0,3 s e as hesitacoes (texto vazio), faz sub-cortes de ~3 s em pontuacao, alterna zoom 100%/116% e escreve `clips.json` + `blocks.json` ja no tempo cortado. Ajustes no topo do script (`GAP`, `ZOOM_ALT`, `SUB_MIN/MAX`).
3. `python -I <skill>/scripts/build_cut_script.py <pasta>/clips.json <pasta> --item <nome do arquivo no projeto> --name "<nome> editado 9x16"` -> `montar.jsx`; rode no Premiere (a sequencia original nao e tocada).
4. Legendas: passos 4 e 5 da Opcao A com o `blocks.json` desta pasta.
5. Salvar o projeto e entregar listando: cortes, zoom, palavras duvidosas e o que nao foi visto.

## Alternativa .mogrt (texto editavel, COM entrada palavra por palavra)
`python -I <skill>/scripts/make_graphics_script.py <pasta>/blocks.json <pasta>/lote.js --track 1` (usa `assets/Simple_Text_WbW.mogrt`; Anim Speed em `style.json`) e rodar os lotes `lote_NN.js`. Use so se o usuario aceitar a animacao.

## Dicas de Premiere (descobertas na pratica)
- `importFiles` precisa de caminho absoluto (`new File(...).fsName`); `createNewSequenceFromClips` herda 1080x1920 de um video vertical.
- **Render**: `app.encoder.encodeSequence(...)` + `startBatch()` pode nao entrar na fila do Media Encoder. O que funcionou: `seq.exportAsMediaDirect(saida, preset, app.encoder.ENCODE_ENTIRE)` (renderiza dentro do Premiere, ~5 min para 90 s). Preset: `<pasta do Premiere>/MediaIO/systempresets/.../H264 Match Source - High bitrate.epr` (procure com glob; fica dentro da instalacao). O preset "MooV" gera audio PCM em .mov/.mp4; se for postar, re-empacote com `ffmpeg -c:v copy -c:a aac`.
- **Exportar frame** (`exportFramePNG` via QE) pode falhar; os PNGs da legenda dispensam isso: o que se ve no PNG e o que vai pro video.

## Ajustes rapidos
| Quero | Mexer em |
|---|---|
| Fonte/tamanho/posicao/sombra | `style.json` (`font_path`, `mogrt_font`, `mogrt_size`, `y_center`, `shadow_*`) |
| Mais tempo na tela | `min_dur`, `tail` em `RULES` (no `sync` so estende para o silencio) |
| 3 palavras em vez de 4 | `{"max_words": 3}` via `--config` |
| Mais/menos cortes e zoom | `GAP`, `ZOOM_ALT`, `SUB_MIN/SUB_MAX` em `plan_edit.py` |

## Limites conhecidos
- PNG nao e texto editavel (corrigir = editar `blocks.json` e regerar).
- A transcricao do Premiere pode errar; revisar o `blocks.json` antes de aplicar.
- A fonte de referencia parece Proxima Nova Bold (mais estreita); usa-se Montserrat Bold (livre).
