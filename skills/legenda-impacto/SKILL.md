---
name: legenda-impacto
description: Legenda "impacto" para videos verticais 9x16 no Premiere Pro — graficos editaveis (.mogrt), animacao palavra por palavra sorteada, linha pequena + linha grande (branca ou vermelha) alternando com legenda reta, fonte condensada em maiuscula, sempre dentro da margem segura. USE quando o usuario pedir para legendar/editar um video com "legenda impacto", "o modelo de legenda" ou "o padrao de legenda". Parte so da transcricao do Premiere e funciona para qualquer video.
---

# Legenda Impacto

Modelo de legenda de alto impacto para Reels/Shorts/TikTok. Quando o usuario pedir para legendar um video com este modelo, aplique-o como descrito abaixo, sem pedir os parametros de novo.

## Pre-requisitos
- Premiere Pro (testado no 2027/27.0; usa ExtendScript) e Python 3.9+ com `pip install -r requirements.txt` (Pillow).
- Uma forma de executar ExtendScript no Premiere: um MCP do Premiere (`execute_extendscript`) **ou** o bridge de arquivos CEP — ver `docs/PREMIERE-BRIDGE.md` na raiz do repositorio.
- Fontes: **Impact** (vem no Windows e no macOS) e, opcional, Anton. Se a fonte nao for achada, defina `CAPTION_FONT_DIR`.
- **Pacote de `.mogrt` palavra por palavra (`*_WbW.mogrt`) em `assets/`** — nao vem no repositorio (veja `assets/LEIA-ME.md`). Sao modelos Essential Graphics com os controles "Anim Speed"/"Out Animation" e um campo de texto.

## Parametros (fonte da verdade: `style.json` e `scripts/plan_blocks.py`)
- Formato 9x16 (1080x1920). Texto em MAIUSCULO, centralizado, `y_center` 0,54 (um pouco abaixo do meio).
- Fonte **Impact**. Linha pequena 56 px (branca), linha grande 140 px, reta 76 px; encolhe para caber (min 60%).
- Bloco de 1 a 6 palavras, cortado por pontuacao, pausa > 0,45 s ou duracao > 3,3 s; nunca termina em palavra solta (o, de, que...).
- Tipos de bloco: `big_below` (pequena em cima + grande embaixo, padrao), `big_above` (palavra forte grande em cima), `single_big`, `single_small` e **reta** (1 linha, ou 2 se for longa, tamanho padrao, branca). Cada bloco vira reta com 40% de chance, no maximo 2 seguidos do mesmo tipo.
- Vermelho `#F2381C` na linha grande quando tem numero/dinheiro/palavra forte (lista `strong`), no maximo 2 vermelhos seguidos, forca 1 se passaram 4 blocos sem.
- Animacao: `.mogrt` palavra por palavra, sorteada por bloco entre os que existirem em `assets/`, nunca repetindo a anterior; as duas linhas do mesmo bloco usam a mesma. Saida em corte seco (Out Animation desligada). Anim Speed 150 (200 se o bloco < 1 s).
- **Margem segura (regra fixa)**: nada de texto fora do *title safe* do Premiere (80% x 80% = 10% de margem em cada lado). Implementado em `make_graphics_script.py` (`layout_text` + `clamp_y`; `safe_margin_x/y` e `safe_tolerance` no `style.json`): largura util = 1 - 2*0,10 - 0,02 = **78% da largura (842 px em 1080)**. Linha que nao cabe: 1) encolhe ate `min_scale` (60%); 2) se ainda nao couber, **quebra em 2 (ate 3) linhas** com corte equilibrado e encolhe so o necessario; o tamanho e arredondado para BAIXO, entao a linha mais larga nunca passa da margem. O bloco inteiro tambem fica entre 10% e 90% da altura.
- Entrega: **editar direto na sequencia que o usuario indicar (sem criar copia)**, a menos que ele peca copia.

## Passo a passo
1. **Conferir o projeto**: confirme com o usuario qual projeto/sequencia esta aberta e deixe a sequencia alvo ativa (o ExtendScript trabalha na sequencia ATIVA).
2. **Transcricao**: o usuario exporta o JSON do Premiere (Texto > Transcricao > menu ... > Exportar; fica em Documentos, "<sequencia>.json").
3. **Plano**: `PYTHONIOENCODING=utf-8 python -I <skill>/scripts/plan_blocks.py <transcricao.json> <pasta>/blocks.json`. Mostre o resumo e as palavras `[conferir]` (confianca < 0,75). Corrija erros no `blocks.json` (campos `small`/`big`).
4. **Trilhas**: liste as trilhas de video. V1 = video. Use V2 (indice 1) para linhas pequenas, V3 (indice 2) para grandes/retas e uma trilha NOVA acima de tudo (indice = numero atual de trilhas) para as vermelhas. Se houver clipes de legenda/titulo antigos cobrindo o quadro, desligue-os.
5. **Gerar lotes**: `python -I <skill>/scripts/make_graphics_script.py blocks.json <pasta>/lote.js --tracks 1,2,<indiceVermelha> [--seed N]` -> `lote_01.js...` (8 clipes cada) e `lote_clips.json`.
6. **Conferir a margem ANTES de rodar**: `python -I <skill>/scripts/check_margins.py <pasta>/lote_clips.json` — tem que dar `fora da margem: 0` (maior largura <= 78%).
7. **Rodar cada lote** no Premiere (ExtendScript, campo `script`, IIFE com return, so `JSON.parse/stringify`), um de cada vez, esperando `ok=8/8`. Se o bridge oscilar, verifique a conexao antes de CADA lote. Nunca mande tudo junto (dezenas de clipes de uma vez travam o Premiere).
8. **Vermelho**: liste os clipes da trilha vermelha e aplique o efeito "Equilibrio de cor (RGB)" (em ingles "RGB Color Balance") com Vermelho 242, Verde 56, Azul 28. **So uma vez por clipe** — reaplicar duplica o efeito e escurece o vermelho (se rodar de novo, apague e recrie os clipes da trilha vermelha).
9. **Conferir**: leia de volta texto/fonte/tamanho/posicao dos clipes e rode `check_margins.py` de novo; exporte 3-4 quadros (um vermelho, um reto, um de 2 linhas) se o export de frame funcionar, senao peca ao usuario para olhar com as guias de margem ligadas. Salve o projeto.
10. **Entregar**: diga o que foi feito, as palavras duvidosas e que nao viu em movimento.

## Ajustes rapidos
| Quero | Mexer em |
|---|---|
| Tamanhos/fonte/posicao | `style.json` (`mogrt_size_small/big/plain`, `mogrt_font`, `y_center`, `gap`) |
| Margem | `safe_margin_x/y`, `safe_tolerance` no `style.json` |
| Mais/menos legenda reta | `--plain-prob` (padrao 0,4) |
| Outra aleatoriedade | `--seed` |
| Mais/menos vermelho, blocos maiores/menores | `RULES` em `plan_blocks.py` ou `--config regras.json` |
| Corrigir texto | `blocks.json` e refazer os lotes |

## Alternativa: video transparente (so se o Premiere nao aceitar .mogrt)
`render_captions.py blocks.json out.mov --duration <s> --fps 30` gera ProRes 4444 com alfa (entrada "pop" de 5 quadros, vermelho nativo, nao editavel). Colocar na timeline como midia importada. Render de 45 s leva ~5 min.

## Limites conhecidos
- A animacao roda no tempo do template, nao no instante exato de cada palavra falada.
- Palavrao censurado ("P*RRA") nao e automatico (editar no `blocks.json`).
- Corte de frase pode ficar estranho; revisar a lista de blocos antes de rodar.
- A cor do `.mogrt` nao e alteravel por script (por isso o efeito de cor nos vermelhos).
