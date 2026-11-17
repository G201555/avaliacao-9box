// Grava ciclo_AAAA-MM.json em Firestore usando o login do Firebase CLI (firebase login):
//   ciclos/AAAA-MM            o ciclo inteiro (admin, supervisores e leitores)
//   cartas/AAAA-MM__<id>      um documento por consultor, com a média e os máximos do time,
//                             para o consultor com login próprio ver só a própria carta
//   acessos/<e-mail>          {id} de consultores_acesso.json (e-mails preenchidos)
// Uso: node publicar_ciclos.js ciclo_2026-01.json [ciclo_2026-02.json ...]
const path = require("path"), fs = require("fs");
const FT = path.join(require("child_process").execSync("npm root -g").toString().trim(), "firebase-tools", "lib");
const { requireAuth } = require(path.join(FT, "requireAuth"));
const { Client } = require(path.join(FT, "apiv2"));
const PROJETO = "seu-projeto-firebase";
const DOCS = `projects/${PROJETO}/databases/(default)/documents`;

const val = v => v === null || v === undefined ? { nullValue: null }
  : typeof v === "boolean" ? { booleanValue: v }
  : typeof v === "number" ? (Number.isInteger(v) ? { integerValue: String(v) } : { doubleValue: v })
  : typeof v === "string" ? { stringValue: v }
  : Array.isArray(v) ? { arrayValue: { values: v.map(val) } }
  : { mapValue: { fields: Object.fromEntries(Object.entries(v).map(([k, x]) => [k, val(x)])) } };
const campos = o => ({ fields: val(o).mapValue.fields });

// mesma conta da página (calc e atributos): só consultores ativos
// grupos da carta (iguais a GRUPOS da página): pontos da campanha do grupo = quantidade × peso
const GRUPOS = {
  bpr: { bolaLimpa: 1, bolaCalibrada: 1, atacador: 1, enchimento: 1 },  // boas práticas
  exe: { vitrine: 10, pontoExtra: 10, planograma: 3 },                   // execução
  eng: { compreGanhe: 20, treinamento: 3 },                              // engajamento
};
const grupo = k => d => Object.entries(GRUPOS[k]).reduce((t, [i, p]) => t + p * (d[i] || 0), 0);
const bpr = grupo("bpr"), exe = grupo("exe"), eng = grupo("eng");
function time(doc) {
  const at = doc.consultores.filter(x => !x.desligado);
  const max = f => Math.max(1, ...at.map(f));
  const med = f => at.reduce((s, x) => s + f(x), 0) / (at.length || 1);
  return {
    media: at.reduce((s, x) => s + x.pts, 0) / (at.length || 1),
    // média do time por atributo da carta (50 na escala da página)
    medias: { pts: med(x => Math.max(0, x.pts)), bpr: med(x => bpr(x.detalhe || {})), exe: med(x => exe(x.detalhe || {})), eng: med(x => eng(x.detalhe || {})) },
    maximos: { pts: max(x => Math.max(0, x.pts)), bpr: max(x => bpr(x.detalhe || {})), exe: max(x => exe(x.detalhe || {})), eng: max(x => eng(x.detalhe || {})) },
  };
}

(async () => {
  const auth = require(path.join(FT, "auth"));
  const conta = auth.getGlobalDefaultAccount();
  if (!conta) throw new Error("sem login no Firebase CLI");
  auth.setActiveAccount({}, conta);
  await requireAuth({ project: PROJETO, user: conta.user, tokens: conta.tokens });
  const c = new Client({ urlPrefix: "https://firestore.googleapis.com", apiVersion: "v1", auth: true });
  for (const f of process.argv.slice(2)) {
    const doc = JSON.parse(fs.readFileSync(f, "utf8"));
    await c.patch(`${DOCS}/ciclos/${doc.mes}`, campos(doc));
    const t = time(doc);
    for (const x of doc.consultores)
      await c.patch(`${DOCS}/cartas/${doc.mes}__${x.id}`, campos({ mes: doc.mes, rotulo: doc.rotulo, fonte: doc.fonte, id: x.id, ...t, consultor: x }));
    console.log("ok", doc.mes, doc.consultores.length, "consultores");
  }
  // fotos.json (preparar_fotos.py): {id: "data:image/jpeg;base64,..."}
  const fotos = path.join(__dirname, "fotos.json");
  if (fs.existsSync(fotos)) {
    const f = JSON.parse(fs.readFileSync(fotos, "utf8"));
    for (const [id, img] of Object.entries(f)) await c.patch(`${DOCS}/fotos/${id}`, campos({ img }));
    console.log("fotos:", Object.keys(f).length);
  }
  const arq = path.join(__dirname, "consultores_acesso.json");
  if (fs.existsSync(arq)) {
    const lista = JSON.parse(fs.readFileSync(arq, "utf8"));
    let n = 0;
    for (const [id, e] of Object.entries(lista)) {
      if (!e || !e.includes("@")) continue;
      await c.patch(`${DOCS}/acessos/${encodeURIComponent(e.trim().toLowerCase())}`, campos({ id }));
      n++;
    }
    console.log("acessos:", n, "e-mails liberados");
  }
})().catch(e => { console.error(e.message || e); process.exit(1); });
