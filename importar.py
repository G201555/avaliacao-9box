# -*- coding: utf-8 -*-
"""
Le a planilha "Campanha de Incentivo 2026 - Apuracao <Mes>.xlsx" e gera o JSON
do ciclo do 9-box (doc ciclos/AAAA-MM no banco do Artifact).

Uso: python importar.py <apuracao.xlsx> <AAAA-MM> [saida.json]

Mesma leitura do news-penalty/tools/importar_apuracao.py: aba com as colunas
"Consultores" e "Pts"; efetividade na coluna "%". As demais colunas viram o
detalhe de produtividade (abertas separadamente, como pedido).
"""
import sys, json, re, unicodedata, datetime
from openpyxl import load_workbook

MESES = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho",
         "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]

# header normalizado -> chave no JSON
DETALHE = {
    "bola limpa": "bolaLimpa", "bola calibrada": "bolaCalibrada", "atacador": "atacador",
    "enchimento": "enchimento", "vitrine": "vitrine", "ponto extra": "pontoExtra",
    "planograma": "planograma", "c&g": "compreGanhe", "treinamento": "treinamento",
    "extra treinamento": "extraTreinamento",
}


def norm(s):
    if s is None:
        return ""
    s = unicodedata.normalize("NFKD", str(s).strip()).encode("ascii", "ignore").decode()
    return s.lower()


def slug(nome):
    return re.sub(r"[^a-z0-9]+", "-", norm(nome)).strip("-")


def num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def ler(path):
    wb = load_workbook(path, data_only=True)
    for ws in wb.worksheets:
        for r in range(1, min(ws.max_row, 30) + 1):
            hdr = [norm(ws.cell(r, c).value) for c in range(1, ws.max_column + 1)]
            if "consultores" in hdr and "pts" in hdr:
                break
        else:
            continue
        ci = {h: i + 1 for i, h in reversed(list(enumerate(hdr))) if h}
        # "efetividade" aparece duas vezes: em "%" (taxa) e na penalidade (pontos)
        c_pen = max(i + 1 for i, h in enumerate(hdr) if h == "efetividade")
        out = []
        for rr in range(r + 1, ws.max_row + 1):
            nome = ws.cell(rr, ci["consultores"]).value
            if not nome or norm(nome) in ("pendente", "total"):
                continue
            pts = ws.cell(rr, ci["pts"]).value
            if pts is None:
                continue
            det = {k: int(num(ws.cell(rr, ci[h]).value)) for h, k in DETALHE.items() if h in ci}
            efet = ws.cell(rr, ci["%"]).value
            out.append({
                "id": slug(nome),
                "nome": " ".join(w.capitalize() for w in str(nome).split()),
                "pts": int(round(num(pts))),
                "efetividade": round(num(efet), 4) if efet is not None else None,
                "penalidadeEfetividade": int(num(ws.cell(rr, c_pen).value)),
                "detalhe": det,
            })
        return out
    raise SystemExit("Nao achei a aba com Consultores/Pts")


def main():
    path, mes = sys.argv[1], sys.argv[2]
    saida = sys.argv[3] if len(sys.argv) > 3 else f"ciclo_{mes}.json"
    a, m = map(int, mes.split("-"))
    doc = {
        "mes": mes,
        "rotulo": f"{MESES[m - 1]} {a}",
        "fonte": path.replace("\\", "/").split("/")[-1],
        "importadoEm": datetime.date.today().isoformat(),
        "consultores": ler(path),
    }
    with open(saida, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)
    print(saida, len(doc["consultores"]), "consultores")
    for c in doc["consultores"]:
        print(f"  {c['nome'][:34]:34} {c['pts']:>6}  efet={c['efetividade']}")


if __name__ == "__main__":
    main()
