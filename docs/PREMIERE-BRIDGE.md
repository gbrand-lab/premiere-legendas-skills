# Como rodar ExtendScript no Premiere

As skills geram arquivos `.jsx` (ExtendScript) que precisam ser executados **dentro** do Premiere, na sequencia ativa. Duas formas:

## Opcao 1 — MCP do Premiere
Qualquer MCP que exponha uma ferramenta de executar ExtendScript (por exemplo `execute_extendscript`, `set_active_sequence`,
`verify_premiere_connection`). O Claude chama a ferramenta com o conteudo de cada `.jsx` no campo `script`.

## Opcao 2 — bridge de arquivos CEP (sem MCP): `tools/premiere_run.py`
Um painel CEP dentro do Premiere (por exemplo o painel "MCP Bridge" do projeto
[adobe-premiere-pro-mcp](https://www.npmjs.com/package/adobe-premiere-pro-mcp)) vigia uma pasta e executa o que aparecer nela:

- Pasta: variavel de ambiente `PREMIERE_TEMP_DIR`, ou `<pasta temporaria do sistema>/premiere-mcp-bridge`.
- Comando: `command-<id>.json` = `{"id": "<id>", "script": "<ExtendScript>", "timeoutMs": 120000}`.
- Resposta: `response-<id>.json` = `{"success": true, "result": "..."}` ou `{"success": false, "error": "..."}`.
- Saude: `bridge-heartbeat.json` = `{"t": <ms epoch>, ...}` atualizado a cada poucos segundos; mais de ~15 s parado = painel fechado.

Uso:
```bash
python tools/premiere_run.py caminho/lote_01.jsx
python tools/premiere_run.py "(function(){ return app.project.name; })()"
```
Abra o painel no Premiere (Janela > Extensoes) antes. O script avisa se o bridge nao responder.

## Regras de ouro (aprendidas na pratica)
- O ExtendScript trabalha na **sequencia ativa**: confirme qual esta ativa antes de rodar qualquer lote.
- **Um lote por vez** (8-20 clipes); lotes grandes travam o Premiere. Espere `ok=N/N` antes do proximo.
- Escreva o `.jsx` como uma funcao imediata que **retorna** uma string (`(function(){ ... return "ok"; })()`); use `JSON.parse/stringify`.
- Caminhos: use `new File(caminho).fsName` ao importar arquivos.
- Nunca reaplique um efeito de cor num clipe que ja o tem (duplica). Se precisar refazer, apague e recrie os clipes.
- Premiere trava arquivos importados: ao regerar PNGs, grave numa **pasta nova**.
