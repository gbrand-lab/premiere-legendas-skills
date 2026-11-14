"""Acha um arquivo de fonte em qualquer computador (Windows, macOS, Linux).

find_font("Montserrat-Bold.ttf") -> caminho absoluto. Aceita caminho completo, ou so o nome do arquivo.
Procura, nesta ordem: a pasta da variavel de ambiente CAPTION_FONT_DIR, a pasta fonts/ da skill, e as pastas de fontes
do sistema e do usuario. Se nao achar, para com uma mensagem dizendo onde baixar/instalar.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def _dirs():
    home = os.path.expanduser("~")
    local = os.environ.get("LOCALAPPDATA", "")
    out = [os.environ.get("CAPTION_FONT_DIR", ""), os.path.join(HERE, "..", "fonts"),
           os.path.join(os.environ.get("WINDIR", "C:/Windows"), "Fonts"),
           os.path.join(local, "Microsoft", "Windows", "Fonts") if local else "",
           "/Library/Fonts", "/System/Library/Fonts", os.path.join(home, "Library", "Fonts"),
           "/usr/share/fonts", "/usr/local/share/fonts", os.path.join(home, ".fonts"),
           os.path.join(home, ".local", "share", "fonts")]
    return [d for d in out if d and os.path.isdir(d)]


def find_font(name_or_path):
    if os.path.isfile(name_or_path):
        return name_or_path
    base = os.path.basename(name_or_path).lower()
    for d in _dirs():
        for root, _dirs_, files in os.walk(d):
            for f in files:
                if f.lower() == base:
                    return os.path.join(root, f)
    sys.exit(f"Fonte '{os.path.basename(name_or_path)}' nao encontrada. Instale a fonte (Montserrat e Anton: fonts.google.com; "
             "Impact ja vem no Windows e no macOS) ou aponte a pasta com a variavel CAPTION_FONT_DIR.")
