# -*- coding: utf-8 -*-
"""
Gera public/brasil-uf.json (contorno dos estados em SVG) a partir da malha do IBGE.

Fonte: https://servicodados.ibge.gov.br/api/v3/malhas/paises/BR?formato=application/vnd.geo%2Bjson&intrarregiao=UF&qualidade=minima
Uso: python gerar_mapa.py <br_uf.json baixado do IBGE>
Saída: {"viewBox": "0 0 L A", "uf": {"SP": "M..Z", ...}, "centro": {"SP": [x, y], ...}}
"""
import sys, json, math, pathlib

# código IBGE da UF → sigla
SIGLA = {11: "RO", 12: "AC", 13: "AM", 14: "RR", 15: "PA", 16: "AP", 17: "TO", 21: "MA", 22: "PI", 23: "CE",
         24: "RN", 25: "PB", 26: "PE", 27: "AL", 28: "SE", 29: "BA", 31: "MG", 32: "ES", 33: "RJ", 35: "SP",
         41: "PR", 42: "SC", 43: "RS", 50: "MS", 51: "MT", 52: "GO", 53: "DF"}
LARG = 600          # largura do SVG
TOL = 0.6           # tolerância da simplificação, em px


def projetar(lon, lat, lat0):
    return lon * math.cos(math.radians(lat0)), -lat


def simplificar(pts, tol):
    """Douglas-Peucker."""
    if len(pts) < 4:
        return pts
    (x1, y1), (x2, y2) = pts[0], pts[-1]
    dx, dy = x2 - x1, y2 - y1
    n = math.hypot(dx, dy) or 1e-9
    dmax, imax = 0, 0
    for i in range(1, len(pts) - 1):
        d = abs(dy * pts[i][0] - dx * pts[i][1] + x2 * y1 - y2 * x1) / n
        if d > dmax:
            dmax, imax = d, i
    if dmax <= tol:
        return [pts[0], pts[-1]]
    return simplificar(pts[:imax + 1], tol)[:-1] + simplificar(pts[imax:], tol)


def aneis(geom):
    cs = geom["coordinates"]
    polys = cs if geom["type"] == "MultiPolygon" else [cs]
    return [anel for poly in polys for anel in poly]


def main():
    g = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
    feats = g["features"]
    todos = [p for f in feats for a in aneis(f["geometry"]) for p in a]
    lat0 = sum(p[1] for p in todos) / len(todos)
    xy = [projetar(*p, lat0) for p in todos]
    minx, maxx = min(p[0] for p in xy), max(p[0] for p in xy)
    miny, maxy = min(p[1] for p in xy), max(p[1] for p in xy)
    esc = LARG / (maxx - minx)
    alt = round((maxy - miny) * esc)
    tela = lambda p: ((p[0] - minx) * esc, (p[1] - miny) * esc)
    out, centro = {}, {}
    for f in feats:
        pr = f["properties"]
        uf = pr.get("sigla") or SIGLA[int(pr.get("codarea") or pr.get("codigo_ibg"))]
        partes, area_max, c = [], 0, (0, 0)
        for anel in aneis(f["geometry"]):
            pts = [tela(projetar(*p, lat0)) for p in anel]
            # anel fechado (1º ponto = último): simplifica em duas metades
            if pts[0] == pts[-1]:
                pts = pts[:-1]
            m = len(pts) // 2
            pts = simplificar(pts[:m + 1], TOL)[:-1] + simplificar(pts[m:] + pts[:1], TOL)[:-1]
            if len(pts) < 3:
                continue
            partes.append("M" + "L".join(f"{x:.1f},{y:.1f}" for x, y in pts) + "Z")
            # centroide do maior anel, para o rótulo
            a = cx = cy = 0
            for (x1, y1), (x2, y2) in zip(pts, pts[1:] + pts[:1]):
                k = x1 * y2 - x2 * y1; a += k; cx += (x1 + x2) * k; cy += (y1 + y2) * k
            if abs(a) > area_max and a:
                area_max, c = abs(a), (cx / (3 * a), cy / (3 * a))
        out[uf] = "".join(partes)
        centro[uf] = [round(c[0], 1), round(c[1], 1)]
    dest = pathlib.Path(__file__).parent / "public" / "brasil-uf.json"
    dest.write_text(json.dumps({"viewBox": f"0 0 {LARG} {alt}", "uf": out, "centro": centro}, separators=(",", ":")), encoding="utf-8")
    print(dest, len(out), "UFs", dest.stat().st_size, "bytes")


if __name__ == "__main__":
    main()
