const CACHE_NOME = "logjobs-shell-v2";

const ARQUIVOS_APP_SHELL = [
  "/",
  "/index.html",
  "/dashboard.html",
  "/ranking.html",
  "/calculadora.html",
  "/perfil.html",
  "/blog.html",
  "/artigo.html",
  "/css/style.css",
  "/css/admin.css",
  "/js/app.js",
  "/js/dashboard.js",
  "/js/ranking.js",
  "/js/calculadora.js",
  "/js/perfil.js",
  "/js/blog.js",
  "/js/artigo.js",
  "/icon.svg",
  "/manifest.json",
];

self.addEventListener("install", (evento) => {
  evento.waitUntil(
    caches.open(CACHE_NOME).then((cache) => cache.addAll(ARQUIVOS_APP_SHELL)).catch(() => {
      // Se algum arquivo falhar (ex.: rota fora do ar), não bloqueia a instalação do service worker.
    })
  );
  self.skipWaiting();
});

self.addEventListener("activate", (evento) => {
  evento.waitUntil(
    caches.keys().then((chaves) =>
      Promise.all(chaves.filter((chave) => chave !== CACHE_NOME).map((chave) => caches.delete(chave)))
    )
  );
  self.clients.claim();
});

self.addEventListener("fetch", (evento) => {
  const url = new URL(evento.request.url);

  // Nunca intercepta a API nem páginas de vaga geradas dinamicamente pelo backend —
  // essas precisam sempre de dados atualizados.
  if (
    evento.request.method !== "GET" ||
    url.pathname.startsWith("/api/") ||
    url.pathname.startsWith("/vagas/") ||
    url.pathname === "/sitemap.xml" ||
    url.pathname === "/robots.txt"
  ) {
    return;
  }

  evento.respondWith(
    caches.match(evento.request).then((respostaCache) => {
      const buscaRede = fetch(evento.request)
        .then((respostaRede) => {
          if (respostaRede && respostaRede.ok) {
            const copia = respostaRede.clone();
            caches.open(CACHE_NOME).then((cache) => cache.put(evento.request, copia));
          }
          return respostaRede;
        })
        .catch(() => respostaCache);

      return respostaCache || buscaRede;
    })
  );
});
