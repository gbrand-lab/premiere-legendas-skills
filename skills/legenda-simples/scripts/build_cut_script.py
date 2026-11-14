#!/usr/bin/env python
"""clips.json (de plan_edit.py) -> JSX que monta a sequencia cortada no Premiere e aplica o zoom alternado.

Uso: python -I build_cut_script.py clips.json <pasta> --item video.mov --name "meu-video editado 9x16"
Gera <pasta>/montar.jsx: cria a sequencia a partir do item, limpa, insere os clipes e aplica a Escala.
Rode com execute_extendscript (ou pelo bridge CEP por arquivo). Depois gere as legendas com
make_graphics_script.py --track 1 (a sequencia nova fica ativa).
"""
import argparse, json, os

ap = argparse.ArgumentParser()
ap.add_argument("clips")
ap.add_argument("out")
ap.add_argument("--item", required=True, help="nome do item de midia no projeto (ex.: video.mov)")
ap.add_argument("--name", required=True, help="nome da sequencia nova")
a = ap.parse_args()
clips = json.load(open(a.clips, encoding="utf-8"))["clips"]

TPL = """(function(){
var CL = %s, Z = %s, p = app.project, item = null;
for (var k=0;k<p.rootItem.children.numItems;k++){ if (p.rootItem.children[k].name === %s) item = p.rootItem.children[k]; }
if (!item) return 'item nao encontrado';
var NAME = %s, s = null;
for (var i=0;i<p.sequences.numSequences;i++){ if (p.sequences[i].name===NAME) s = p.sequences[i]; }
if (!s) {
  p.createNewSequenceFromClips(NAME, [item], p.rootItem);
  for (var i=0;i<p.sequences.numSequences;i++){ if (p.sequences[i].name===NAME) s = p.sequences[i]; }
  p.openSequence(s.sequenceID);
  for (var t=0;t<s.videoTracks.numTracks;t++){ var tr=s.videoTracks[t]; for (var c=tr.clips.numItems-1;c>=0;c--) tr.clips[c].remove(false,false); }
  for (var t=0;t<s.audioTracks.numTracks;t++){ var tr=s.audioTracks[t]; for (var c=tr.clips.numItems-1;c>=0;c--) tr.clips[c].remove(false,false); }
}
for (var n=0;n<CL.length;n++){
  var c = CL[n]; item.setInPoint(c.src_in, 4); item.setOutPoint(c.src_out, 4);
  var tm = new Time(); tm.seconds = c.new_in; s.videoTracks[0].overwriteClip(item, tm);
}
item.clearInPoint(4); item.clearOutPoint(4);
var tr0 = s.videoTracks[0], done = 0;
for (var i=0;i<tr0.clips.numItems;i++){
  var comp = tr0.clips[i].components[1];
  for (var j=0;j<comp.properties.numItems;j++){ var nm = comp.properties[j].displayName; if (nm==='Scale' || nm==='Escala'){ comp.properties[j].setValue(Z[i], true); done++; } }
}
return JSON.stringify({seq:s.name, v:tr0.clips.numItems, a:s.audioTracks[0].clips.numItems, zoom:done});
})()"""
os.makedirs(a.out, exist_ok=True)
open(os.path.join(a.out, "montar.jsx"), "w", encoding="utf-8").write(
    TPL % (json.dumps(clips), json.dumps([c["zoom"] for c in clips]), json.dumps(a.item), json.dumps(a.name)))
print(len(clips), "clipes -> montar.jsx")
