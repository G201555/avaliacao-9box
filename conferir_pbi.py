# -*- coding: utf-8 -*-
"""
Confere os ciclo_AAAA-MM.json contra o Power BI: roda as queries extraídas dos .pbix
(news-penalty-trimestral/pbi_sql) e aplica as mesmas medidas DAX, por consultor.

Uso: python conferir_pbi.py AAAA-MM [AAAA-MM ...]
Só imprime o que diverge.
"""
import sys, json, pathlib
import pandas as pd
from gerar_ciclo import AQUI, norm, query_pbi, PESO, META_EFET, PENALIDADE

PBI = pathlib.Path("C:/dev/news-penalty-trimestral/pbi_sql")
num = lambda s: pd.to_numeric(s, errors="coerce").fillna(0)


def q(nome):
    df = query_pbi(PBI / nome)
    df["m"] = pd.to_datetime(df["DATA" if "DATA" in df.columns else "data"]).dt.strftime("%Y-%m")
    return df


def col(df, *trechos):
    return next(c for c in df.columns if all(t in c for t in trechos))


def carregar():
    pes = query_pbi(PBI / "Execução_Bola__d_pessoa.sql")
    cod = {r.COD_PESSOA: norm(r.NOM_PESSOA) for r in pes.itertuples()}
    T = {"bola": q("Execução_Bola__f_bola.sql"), "cal": q("Execução_Calçados__f_calcados.sql"),
         "vit": q("Execução_Vitrine__f_excucaovitrine.sql"), "pe": q("Espaço_Loja__f_ponto_extra.sql"),
         "cg": q("Compre_e_Ganhe__f_compreeganhe.sql"), "tr": q("Treinamento__f_treinamento.sql"),
         "ef": q("Efetividade_(TEMPO_EM_LOJA)__fEfetividade.sql")}
    for k in ("bola", "cal", "cg", "tr"):
        T[k]["n"] = T[k].PROMOTOR.map(norm)
    for k in ("vit", "pe"):
        T[k]["n"] = T[k].COD_PESSOA.map(cod)
    T["ef"]["n"] = T["ef"].NOM_PESSOA.map(norm)
    return T


def medidas(T, m):
    g = {k: v[v.m == m] for k, v in T.items()}
    b, c, v, p, k, t, e = (g[x] for x in ("bola", "cal", "vit", "pe", "cg", "tr", "ef"))
    soma = lambda df, cl: df.groupby("n")[cl].apply(lambda s: num(s).sum())
    plan = col(c, "PLANOGRAMA")
    ativ = col(k, "ATIVADO")
    ef = e.assign(pl=num(e.planejado), re=num(e.realizado)).groupby("n").agg(pl=("pl", "sum"), re=("re", "sum"), lj=("cod_loja", "nunique"))
    return {
        "bolaLimpa": soma(b, "QUANTAS BOLAS FORAM LIMPAS NO ATENDIMENTO:"),
        "bolaCalibrada": soma(b, "INFORME A QTD DE BOLAS CALIBRADAS:"),
        "atacador": soma(c, col(c, "QTD", "CARDA")),
        "enchimento": soma(c, col(c, "QTD", "ENCHIMENTO")),
        "vitrine": soma(v, "EXECUCAO_UNICA"),
        "pontoExtra": p[num(p.FL_EXISTE) == 1].groupby("n").bi_id_loja.nunique(),
        "planograma": c[c[plan].astype(str).str.upper() == "SIM"].groupby("n").bi_id_loja.nunique(),
        "compreGanhe": k[k[ativ].astype(str).str.strip().str.upper() == "SIM"].groupby("n").BI_ID_LOJA.nunique(),
        "treinamento": soma(t, "QTD PESSOAS TREINADAS"),
    }, ef


def main():
    T = carregar()
    for m in sys.argv[1:]:
        d = json.loads((AQUI / f"ciclo_{m}.json").read_text(encoding="utf-8"))
        P, ef = medidas(T, m)
        difs = 0
        for x in d["consultores"]:
            n = norm(x["nome"]); dif = []
            for k, s in P.items():
                a, b = x["detalhe"][k], int(round(s.get(n, 0)))
                if a != b: dif.append(f"{k} {a} vs PBI {b}")
            if n in ef.index:
                r = ef.loc[n]; e = round(r.re / r.pl, 4) if r.pl else None
                if e != x["efetividade"]: dif.append(f"efetividade {x['efetividade']} vs PBI {e}")
                if int(r.lj) != x["lojas"]: dif.append(f"lojas {x['lojas']} vs PBI {int(r.lj)}")
                pen = PENALIDADE if (e is not None and e < META_EFET) else 0
                pts = sum(int(round(P[k].get(n, 0))) * PESO[k] for k in PESO) - pen
                if pts != x["pts"]: dif.append(f"pontos {x['pts']} vs PBI {pts}")
            if dif:
                difs += 1; print(f"  {m} {x['nome'][:30]:30} " + "; ".join(dif))
        fora = set().union(*[set(s.index) for s in P.values()]) - {norm(x["nome"]) for x in d["consultores"]} - {None, ""}
        print(f"{m}: {len(d['consultores'])} consultores, {difs} com diferença" + (f"; só no PBI: {sorted(fora)}" if fora else ""))


if __name__ == "__main__":
    main()
