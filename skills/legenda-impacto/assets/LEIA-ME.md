# Pasta `assets/` — pacote de .mogrt

Coloque aqui os seus modelos `*_WbW.mogrt` (Essential Graphics do Premiere, animacao palavra por palavra). O gerador sorteia
entre todos os `*_WbW.mogrt` desta pasta. **Eles nao vem no repositorio** porque a origem/licenca de pacotes de templates e de
quem os criou.

Requisitos de cada `.mogrt`: um campo de texto (Source Text), o controle **Anim Speed** (50-500) e o interruptor **Out Animation**.
Para testar sem pacote: `make_graphics_script.py ... --mogrt caminho/do/seu.mogrt`.
