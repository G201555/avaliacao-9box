# -*- coding: utf-8 -*-
"""
Prepara as fotos dos consultores para as cartas do 9-box.

Uso: python preparar_fotos.py <pasta com as fotos>
  - cada arquivo (.jpg/.jpeg/.png/.webp) com o nome do consultor, ex.: "Maria Silva.jpg"
    ou só nome e sobrenome ("Maria Silva.png"); acentos e maiúsculas não importam
  - recorta o centro em quadrado, reduz para 240×240 e grava fotos.json ({id: data URI})
Depois: node publicar_ciclos.js  (grava fotos/{id} no Firestore; só a equipe e o próprio consultor leem)
"""
import sys, json, glob, io, base64, pathlib
from PIL import Image, ImageOps
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from gerar_ciclo import norm  # noqa: E402

AQUI = pathlib.Path(__file__).parent
LADO = 240


def consultores():
    """id e nome de todos os consultores dos ciclos gerados (o mais recente vence)."""
    out = {}
    for f in sorted(AQUI.glob("ciclo_*.json")):
        for x in json.loads(f.read_text(encoding="utf-8"))["consultores"]:
            out[x["id"]] = x["nome"]
    return out


def achar(stem, cons):
    p = norm(stem).replace("_", " ").replace("-", " ").split()
    p = [w for w in p if w not in ("THUMBNAIL", "FOTO", "IMG")]
    exatos = [i for i, n in cons.items() if norm(n).split() == p or i == "-".join(p).lower()]
    if exatos:
        return exatos
    return [i for i, n in cons.items() if all(w in norm(n).split() for w in p)]


# recorte manual quando o rosto é pequeno ou fora do centro: id → (centro x, centro y, lado), frações da largura/altura
AJUSTE = {
    "afonso-mendonca-neto": (0.30, 0.20, 0.42),
    "edson-raimundo-de-sousa": (0.56, 0.47, 0.80),
}


def miniatura(arq, id_=None):
    im = ImageOps.exif_transpose(Image.open(arq)).convert("RGB")
    if id_ in AJUSTE:
        cx, cy, lado = AJUSTE[id_]
        w, h = im.size; s = lado * w
        x0, y0 = max(0, cx * w - s / 2), max(0, cy * h - s / 2)
        im = im.crop((int(x0), int(y0), int(min(w, x0 + s)), int(min(h, y0 + s))))
    im = ImageOps.fit(im, (LADO, LADO), Image.LANCZOS, centering=(0.5, 0.3))  # acima do centro: rosto
    b = io.BytesIO()
    im.save(b, "JPEG", quality=82, optimize=True)
    return "data:image/jpeg;base64," + base64.b64encode(b.getvalue()).decode()


def main():
    pasta = pathlib.Path(sys.argv[1])
    cons = consultores()
    out, sem = {}, []
    for arq in sorted(pasta.iterdir()):
        if arq.suffix.lower() not in (".jpg", ".jpeg", ".png", ".webp"):
            continue
        ids = achar(arq.stem, cons)
        if len(ids) != 1:
            sem.append(f"{arq.name}: {'nenhum consultor' if not ids else 'vários: ' + ', '.join(cons[i] for i in ids)}")
            continue
        out[ids[0]] = miniatura(arq, ids[0])
        print(f"  {arq.name:40} → {cons[ids[0]]}")
    (AQUI / "fotos.json").write_text(json.dumps(out), encoding="utf-8")
    print(len(out), "fotos em fotos.json")
    for t in sem:
        print("  NÃO USADA", t)
    faltam = [n for i, n in cons.items() if i not in out]
    if faltam:
        print("  sem foto:", ", ".join(sorted(faltam)))


if __name__ == "__main__":
    main()
