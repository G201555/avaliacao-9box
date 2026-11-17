# -*- coding: utf-8 -*-
"""
Gera o ciclo do 9-box direto do bi_cliente (SQL Server SEU_SERVIDOR_SQL, da empresa).

Uso: python gerar_ciclo.py AAAA-MM [--comparar "<Campanha de Incentivo ... .xlsx>"]

Pontos: mesma mecânica da Campanha de Incentivo (news-penalty-trimestral/apur_calc.py):
  bola limpa + bola calibrada + atacador + enchimento (1 pt por unidade)
  + 10 × vitrine (loja-dia com foto de vitrine, regra do Execução Vitrine.pbix)
  + 10 × ponto extra (lojas) + 3 × planograma (lojas) + 20 × C&G (lojas ativas, query do Compre e Ganhe.pbix)
  + 3 × pessoas treinadas
  − 10 se a efetividade ficar abaixo de 89%.
Efetividade: query do Efetividade.pbix (sql/efetividade_pbi.sql), realizado ÷ planejado.
Lojas = lojas distintas da base de efetividade no mês (Qtd Lojas do PBI); dias trabalhados = dias com visita realizada (mesma base).
Ano = soma de janeiro até o mês do ciclo (pontos, dias trabalhados, pontos por dia).
Saída: ciclo_AAAA-MM.json no mesmo formato do importar.py.
"""
import sys, json, re, datetime, unicodedata, pathlib
import pyodbc
import pandas as pd

AQUI = pathlib.Path(__file__).parent
MESES = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho",
         "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
PESO = {"bolaLimpa": 1, "bolaCalibrada": 1, "atacador": 1, "enchimento": 1, "vitrine": 10,
        "pontoExtra": 10, "planograma": 3, "compreGanhe": 20, "treinamento": 3}
META_EFET, PENALIDADE = 0.89, 10
# fora do quadro de consultores (supervisor). Desligados vêm do cadastro (bi_d_pessoa.DTA_DEMISSAO):
# aparecem marcados só no mês da demissão, fora do 9-box, do ranking e da média.
FORA_DO_QUADRO = {"consultor DE SOUZA"}


def conectar():
    return pyodbc.connect("DRIVER={ODBC Driver 18 for SQL Server};SERVER=SEU_SERVIDOR_SQL;DATABASE=bi_cliente;"
                          "Trusted_Connection=yes;TrustServerCertificate=yes", timeout=30)


def norm(s):
    return unicodedata.normalize("NFKD", str(s or "").strip()).encode("ascii", "ignore").decode().upper()


def slug(nome):
    return re.sub(r"[^a-z0-9]+", "-", norm(nome).lower()).strip("-")


def contagens(c, a, b):
    """Quantidades por consultor no mês (cada item da campanha, antes do peso)."""
    def by(sql):
        return {norm(r[0]): float(r[1] or 0) for r in c.execute(sql).fetchall()}
    JP = ("JOIN bi_d_pessoa p ON p.bi_id_pessoa=f.bi_id_pessoa "
          "LEFT JOIN bi_d_formulario_alternativas a ON a.bi_id_formulario_alternativas=f.bi_id_formulario_alternativas")
    W = f"f.DATA>='{a}' AND f.DATA<'{b}'"
    F = lambda fo, pg, agg="SUM(f.DES_RESPOSTA_QTD)", extra="": by(
        f"SELECT p.NOM_PESSOA,{agg} FROM bi_f_formulario f {JP} WHERE {W} AND f.COD_FORMULARIO={fo} "
        f"AND f.COD_PERGUNTA={pg} {extra} GROUP BY p.NOM_PESSOA")
    return {
        "bolaLimpa": F(3, 70), "bolaCalibrada": F(3, 23), "atacador": F(14, 26), "enchimento": F(14, 30),
        "vitrine": by(f"""SELECT p.NOM_PESSOA, COUNT(DISTINCT CONCAT(r.COD_LOJA,'-',CAST(f.DATA AS DATE)))
            FROM bi_d_foto_execucao f JOIN bi_f_efetividade r ON f.COD_ROTEIRO=r.COD_ROTEIRO
            JOIN bi_d_pessoa p ON p.COD_PESSOA=r.COD_PESSOA AND p.date_to>'2100-01-01'
            WHERE f.COD_TIPO_EXECUCAO=3 AND {W} GROUP BY p.NOM_PESSOA"""),
        "pontoExtra": by(f"""SELECT p.NOM_PESSOA, COUNT(DISTINCT f.COD_LOJA) FROM bi_f_ponto_extra f
            JOIN bi_d_pessoa p ON p.bi_id_pessoa=f.bi_id_pessoa WHERE {W} AND f.FL_EXISTE=1 GROUP BY p.NOM_PESSOA"""),
        "planograma": F(14, 33, "COUNT(DISTINCT f.COD_LOJA)", "AND a.DES_ALTERNATIVA='SIM'"),
        # pessoas treinadas (bate exatamente com a planilha)
        "treinamento": F(2, 4),
    }


def query_pbi(arquivo):
    """Roda uma query extraída de um .pbix (sql/) e devolve o último result set."""
    sql = (AQUI / "sql" / arquivo).read_text(encoding="utf-8-sig")
    sql = "SET NOCOUNT ON;\n" + re.sub(r"^\s*use\s+bi_cliente\s*$", "", sql, flags=re.I | re.M)
    cn = conectar()  # conexão própria: as queries do PBI reaproveitam nomes de tabela temporária
    cur = cn.cursor(); cur.execute(sql)
    while cur.description is None and cur.nextset():
        pass
    df = pd.DataFrame.from_records(cur.fetchall(), columns=[d[0] for d in cur.description])
    cn.close()
    return df


def base_efetividade():
    """Base do Efetividade.pbix inteira (uma linha por loja planejada/visitada por dia)."""
    df = query_pbi("efetividade_pbi.sql")
    df["d"] = pd.to_datetime(df["data"])
    for k in ("planejado", "realizado"):
        df[k] = pd.to_numeric(df[k])
    df["NOM_PESSOA"] = df["NOM_PESSOA"].map(norm)
    # UF da loja (estado onde o consultor atua)
    cn = conectar()
    uf = {int(r[0]): r[1] for r in cn.cursor().execute(
        "SELECT COD_LOJA, DES_UF FROM bi_d_loja WHERE date_to>'2100-01-01'").fetchall()}
    cn.close()
    df["uf"] = pd.to_numeric(df["cod_loja"]).map(uf)
    return df


def base_compre_ganhe():
    """Compre e Ganhe.pbix (f_compreeganhe), com a exclusão de UF que a própria query faz."""
    df = query_pbi("compre_ganhe_pbi.sql")
    df["d"] = pd.to_datetime(df["DATA"])
    df["NOM_PESSOA"] = df["PROMOTOR"].map(norm)
    ativ = [c for c in df.columns if "ATIVADO" in c][0]
    return df[df[ativ].astype(str).str.strip().str.upper() == "SIM"]


def compre_ganhe(cg, a, b):
    """Lojas ativas no mês, como a medida compre_Lojas Ativas do PBI."""
    df = cg[(cg.d >= a) & (cg.d < b)]
    return df.groupby("NOM_PESSOA").BI_ID_LOJA.nunique().astype(float).to_dict()


def rota(base, a, b):
    """Por consultor no mês: efetividade (realizado ÷ planejado), lojas da carteira, dias com visita realizada
    e UFs onde atua (lojas distintas por UF, da maior para a menor)."""
    df = base[(base.d >= a) & (base.d < b)]
    g = df.groupby("NOM_PESSOA")[["planejado", "realizado"]].sum()
    g = g[g.planejado > 0]
    lojas = df.groupby("NOM_PESSOA").cod_loja.nunique()  # medida Qtd Lojas do Efetividade.pbix
    dias = df[df.realizado > 0].groupby("NOM_PESSOA").d.nunique()
    ufs = {}
    for n, d in df.dropna(subset=["uf"]).groupby("NOM_PESSOA"):
        ufs[n] = list(d.groupby("uf").cod_loja.nunique().sort_values(ascending=False).index)
    return (g.realizado / g.planejado).to_dict(), lojas.to_dict(), dias.to_dict(), ufs


def pontos_mes(mes, base, cg, dem):
    a = mes + "-01"; b = str(pd.Period(mes) + 1) + "-01"
    cn = conectar(); col = contagens(cn.cursor(), a, b); cn.close()
    col["compreGanhe"] = compre_ganhe(cg, a, b)
    efp, lojas, dias, ufs = rota(base, a, b)
    nomes = sorted(set().union(*[set(v) for v in col.values()]) | set(efp))
    out = {}
    for n in nomes:
        det = {k: int(round(col[k].get(n, 0))) for k in PESO}  # quantidades, como na planilha
        if n in FORA_DO_QUADRO or (not any(det.values()) and n not in efp):
            continue
        e = efp.get(n)
        pen = PENALIDADE if (e is not None and e < META_EFET) else 0
        out[n] = {"id": slug(n), "nome": " ".join(w.capitalize() for w in n.lower().split()),
                  "pts": sum(det[k] * PESO[k] for k in PESO) - pen, "efetividade": round(e, 4) if e is not None else None,
                  "penalidadeEfetividade": pen, "lojas": int(lojas.get(n, 0)), "diasTrabalhados": int(dias.get(n, 0)),
                  "uf": (ufs.get(n) or [None])[0], "ufs": ufs.get(n, []), "detalhe": det}
        if n in dem and dem[n] < b:  # demitido neste mês (ou antes, se ainda sobrou registro)
            out[n]["desligado"] = True
            out[n]["demissao"] = dem[n]
    return out


def cadastro():
    """Admissão e demissão por consultor (bi_d_pessoa, versão atual): tempo de casa e mês do desligamento."""
    cn = conectar()
    rows = cn.cursor().execute("SELECT NOM_PESSOA, MIN(DTA_ADMISSAO), MAX(DTA_DEMISSAO) FROM bi_d_pessoa "
                               "WHERE date_to>'2100-01-01' GROUP BY NOM_PESSOA").fetchall()
    cn.close()
    adm = {norm(n): a.date().isoformat() for n, a, _ in rows if a}
    dem = {norm(n): d.date().isoformat() for n, _, d in rows if d}
    return adm, dem


def gerar(mes):
    base, cg = base_efetividade(), base_compre_ganhe()
    adm, dem = cadastro()
    p = pd.Period(mes)
    # campanha anual: soma de janeiro até o mês do ciclo
    meses = [str(pd.Period(f"{p.year}-{m:02d}")) for m in range(1, p.month + 1)]
    por_mes = {m: pontos_mes(m, base, cg, dem) for m in meses}
    # demitido num mês em que já não teve atividade (ex.: saiu no dia 2): entra no mês da demissão,
    # marcado como desligado e zerado, para aparecer no mês certo
    for i, m in enumerate(meses):
        b = str(pd.Period(m) + 1) + "-01"
        for n, d in dem.items():
            if not (m + "-01" <= d < b) or n in por_mes[m]:
                continue
            ant = [por_mes[k][n] for k in meses[:i] if n in por_mes[k]]
            if not ant:
                continue
            u = ant[-1]
            por_mes[m][n] = {"id": u["id"], "nome": u["nome"], "pts": 0, "efetividade": None, "penalidadeEfetividade": 0,
                             "lojas": 0, "diasTrabalhados": 0, "uf": u["uf"], "ufs": u["ufs"],
                             "detalhe": {k: 0 for k in PESO}, "desligado": True, "demissao": d, "semAtividade": True}
    # efetividade e lojas do ano inteiro (realizado ÷ planejado de janeiro até o fim do mês), para o filtro "Ano · geral"
    ef_ano, lojas_ano, _, _ = rota(base, f"{p.year}-01-01", str(p + 1) + "-01")
    out = []
    for n, x in por_mes[mes].items():
        hist = [por_mes[m][n] for m in meses if n in por_mes[m] and not por_mes[m][n].get("semAtividade")]
        pts, dias = sum(h["pts"] for h in hist), sum(h["diasTrabalhados"] for h in hist)
        x["ano"] = {"pts": pts, "diasTrabalhados": dias, "meses": len(hist),
                    "ptsPorDia": round(pts / dias, 1) if dias else None,
                    "efetividade": round(ef_ano[n], 4) if n in ef_ano else None, "lojas": int(lojas_ano.get(n, 0))}
        if n in adm:
            x["admissao"] = adm[n]
        out.append(x)
    out.sort(key=lambda x: -x["pts"])
    return out


def main():
    mes = sys.argv[1]
    cons = gerar(mes)
    ano, m = map(int, mes.split("-"))
    doc = {"mes": mes, "rotulo": f"{MESES[m - 1]} {ano}", "fonte": "bi_cliente (Campanha de Incentivo)",
           "importadoEm": datetime.date.today().isoformat(), "consultores": cons}
    saida = AQUI / f"ciclo_{mes}.json"
    saida.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    print(saida.name, len(cons), "consultores")
    if "--comparar" in sys.argv:
        sys.path.insert(0, str(AQUI)); from importar import ler
        plan = {x["id"]: x for x in ler(sys.argv[sys.argv.index("--comparar") + 1])}
        for x in cons:
            p = plan.get(x["id"])
            if not p:
                print(f"  {x['nome'][:32]:32} {x['pts']:>6}  (não está na planilha)"); continue
            dif = {k: (x["detalhe"].get(k, 0), p["detalhe"].get(k, 0)) for k in PESO if x["detalhe"].get(k, 0) != p["detalhe"].get(k, 0)}
            ef = f"efet {x['efetividade']} vs {p['efetividade']}"
            print(f"  {x['nome'][:32]:32} BI {x['pts']:>6}  planilha {p['pts']:>6}  {ef}  {dif if dif else 'itens iguais'}")
        for k, p in plan.items():
            if k not in {x['id'] for x in cons}:
                print(f"  {p['nome'][:32]:32} só na planilha ({p['pts']})")
    else:
        for x in cons:
            print(f"  {x['nome'][:34]:34} {x['pts']:>6}  efet={x['efetividade']}")


if __name__ == "__main__":
    main()
