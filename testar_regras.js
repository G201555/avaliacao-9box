// Testa firestore.rules na API de regras do Firebase (sem gravar nada), com o login do Firebase CLI.
// Uso: node testar_regras.js
const path = require("path"), fs = require("fs");
const FT = path.join(require("child_process").execSync("npm root -g").toString().trim(), "firebase-tools", "lib");
const { requireAuth } = require(path.join(FT, "requireAuth"));
const { Client } = require(path.join(FT, "apiv2"));
const PROJETO = "seu-projeto-firebase";
const D = "/databases/(default)/documents";

const CONS = "usuario@exemplo.com", ID = "ana-teste";
const tok = e => ({ auth: { uid: "u-" + e, token: { email: e } } });
// acessos/{CONS} existe com {id: ID}; nenhum outro e-mail tem acesso
const mocks = [
  { function: "exists", args: [{ exactValue: `${D}/acessos/${CONS}` }], result: { value: true } },
  { function: "exists", args: [{ anyValue: {} }], result: { value: false } },
  { function: "get", args: [{ exactValue: `${D}/acessos/${CONS}` }], result: { value: { data: { id: ID } } } },
];
const caso = (nome, esperado, email, metodo, doc, dados) => ({
  nome, testCase: {
    expectation: esperado, functionMocks: mocks,
    request: { ...tok(email), method: metodo, path: `${D}/${doc}` },
    ...(dados ? { resource: { data: dados } } : {}),
  },
});
const CASOS = [
  caso("consultor lê a própria carta", "ALLOW", CONS, "get", `cartas/2026-10__${ID}`, { id: ID }),
  caso("consultor NÃO lê a carta de outro", "DENY", CONS, "get", "cartas/2026-10__outro", { id: "outro" }),
  caso("consultor NÃO lê o ciclo do time", "DENY", CONS, "get", "ciclos/2026-10", { mes: "2026-10" }),
  caso("consultor lê a própria avaliação", "ALLOW", CONS, "get", `avaliacoes/2026-10__${ID}`, { consultor: ID }),
  caso("consultor NÃO lê avaliação de outro", "DENY", CONS, "get", "avaliacoes/2026-10__outro", { consultor: "outro" }),
  caso("consultor lê o próprio acesso", "ALLOW", CONS, "get", `acessos/${CONS}`, { id: ID }),
  caso("consultor NÃO lê acesso de outro", "DENY", CONS, "get", "acessos/usuario@exemplo.com", { id: "outro" }),
  caso("consultor NÃO grava a carta", "DENY", CONS, "update", `cartas/2026-10__${ID}`, { id: ID }),
  caso("leitora lê qualquer carta", "ALLOW", "usuario@exemplo.com", "get", "cartas/2026-10__outro", { id: "outro" }),
  caso("e-mail sem acesso NÃO lê carta", "DENY", "usuario@exemplo.com", "get", `cartas/2026-10__${ID}`, { id: ID }),
  caso("consultor vê a própria foto", "ALLOW", CONS, "get", `fotos/${ID}`, { img: "x" }),
  caso("consultor NÃO vê foto de outro", "DENY", CONS, "get", "fotos/outro", { img: "x" }),
  caso("leitora vê fotos", "ALLOW", "usuario@exemplo.com", "get", "fotos/outro", { img: "x" }),
  caso("e-mail sem acesso NÃO vê foto", "DENY", "usuario@exemplo.com", "get", `fotos/${ID}`, { img: "x" }),
  caso("consultor NÃO grava foto", "DENY", CONS, "update", `fotos/${ID}`, { img: "x" }),
];

(async () => {
  const auth = require(path.join(FT, "auth"));
  const conta = auth.getGlobalDefaultAccount();
  auth.setActiveAccount({}, conta);
  await requireAuth({ project: PROJETO, user: conta.user, tokens: conta.tokens });
  const c = new Client({ urlPrefix: "https://firebaserules.googleapis.com", apiVersion: "v1", auth: true });
  const regras = fs.readFileSync(path.join(__dirname, "firestore.rules"), "utf8");
  const r = await c.post(`projects/${PROJETO}:test`, {
    source: { files: [{ name: "firestore.rules", content: regras }] },
    testSuite: { testCases: CASOS.map(x => x.testCase) },
  });
  let falhas = 0;
  (r.body.testResults || []).forEach((t, i) => {
    const ok = t.state === "SUCCESS"; if (!ok) falhas++;
    console.log(ok ? "ok  " : "FALHOU", CASOS[i].nome, ok ? "" : JSON.stringify(t.debugMessages || t.errorPosition || t));
  });
  if (r.body.issues) console.log(JSON.stringify(r.body.issues));
  console.log(falhas ? `${falhas} falha(s)` : "todos os casos passaram");
  process.exit(falhas ? 1 : 0);
})().catch(e => { console.error(e.message || e); process.exit(1); });
