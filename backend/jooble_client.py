import os
import re

import requests

JOOBLE_API_KEY = os.getenv("JOOBLE_API_KEY")
JOOBLE_URL = "https://jooble.org/api/{key}"

_TAG_HTML = re.compile(r"<[^>]+>")
_ESPACOS = re.compile(r"\s+")


def _limpar_html(texto):
    """Remove tags HTML (o Jooble costuma destacar palavras-chave com <b> no snippet)
    e normaliza espaços, deixando a descrição legível como texto puro."""
    if not texto:
        return texto
    sem_tags = _TAG_HTML.sub("", texto)
    return _ESPACOS.sub(" ", sem_tags).strip()


# Ordem importa: padrões mais específicos primeiro (ex.: "empilhadeira" antes de
# "operador" genérico), para classificar corretamente o cargo em uma das
# categorias usadas pelos filtros do site.
_PADROES_CATEGORIA = [
    (re.compile(r"empilhadeira", re.I), "Operador"),
    (re.compile(r"motoboy", re.I), "Motoboy"),
    (re.compile(r"entregador|entrega\b|delivery", re.I), "Entregador"),
    (re.compile(r"caminhoneiro|carreteiro|caminh[aã]o", re.I), "Caminhoneiro"),
    (re.compile(r"motorista|condutor", re.I), "Motorista"),
    (re.compile(r"estoquista|estoque|almoxarife", re.I), "Estoquista"),
    (re.compile(r"conferente|confer[eê]ncia", re.I), "Conferente"),
    (re.compile(r"auxiliar|ajudante|separador|expedi[cç][aã]o|embalador", re.I), "Auxiliar Logístico"),
    (re.compile(r"supervisor", re.I), "Supervisor"),
    (re.compile(r"coordenador", re.I), "Coordenador"),
    (re.compile(r"analista", re.I), "Analista"),
    (re.compile(r"gestor|gerente|diretor", re.I), "Gestor"),
    (re.compile(r"operador", re.I), "Operador"),
]


def classificar_categoria(cargo: str) -> str:
    """Classifica o cargo em uma das categorias usadas pelos filtros do site,
    a partir de palavras-chave no título da vaga. Sem correspondência, cai
    numa categoria genérica que ainda aparece normalmente na busca."""
    for padrao, categoria in _PADROES_CATEGORIA:
        if padrao.search(cargo or ""):
            return categoria
    return "Logística"


# (cidade, sigla do estado). A sigla NÃO é enviada para o Jooble como parte da
# busca — várias siglas de estado brasileiro colidem com códigos postais dos
# EUA (MT=Montana, PA=Pennsylvania, MS=Mississippi, SC=South Carolina,
# AL=Alabama), o que fazia o Jooble devolver vagas americanas (ex.: vagas de
# "Maquinista" na Montana, EUA) em vez de brasileiras. Por isso a busca usa
# sempre "Cidade, Brasil", e a sigla do estado é só para exibição no site.
REGIOES = [
    ("São Paulo", "SP"), ("Rio de Janeiro", "RJ"), ("Belo Horizonte", "MG"), ("Curitiba", "PR"),
    ("Porto Alegre", "RS"), ("Salvador", "BA"), ("Recife", "PE"), ("Fortaleza", "CE"),
    ("Brasília", "DF"), ("Manaus", "AM"), ("Goiânia", "GO"), ("Florianópolis", "SC"),
    ("Vitória", "ES"), ("Belém", "PA"), ("Campo Grande", "MS"), ("Cuiabá", "MT"),
]

# Buscar com uma palavra-chave combinada ("logistica entregador motorista...")
# faz o Jooble devolver majoritariamente vagas genéricas de "Logística", sem
# as palavras específicas no título. Por isso a busca é feita termo a termo,
# marcando a categoria diretamente pelo termo buscado (mais confiável do que
# só adivinhar pela classificação de texto depois).
TERMOS_CATEGORIA = [
    ("entregador", "Entregador"),
    ("motorista entregas", "Motorista"),
    ("motorista caminhoneiro carreteiro", "Caminhoneiro"),
    ("estoquista almoxarife", "Estoquista"),
    ("conferente de cargas", "Conferente"),
    ("auxiliar logistica expedicao", "Auxiliar Logístico"),
    ("operador de empilhadeira", "Operador"),
    ("motoboy", "Motoboy"),
]


# Nomes de estados americanos cujas siglas colidem com as brasileiras — se
# aparecerem no local retornado pelo Jooble, é sinal de que a vaga é dos EUA,
# não do Brasil, e deve ser descartada.
_ESTADOS_EUA_COLIDENTES = re.compile(
    r"\b(Montana|Pennsylvania|Mississippi|South Carolina|Alabama)\b", re.I
)


def _buscar_uma_regiao(keywords: str, cidade_busca: str, estado: str):
    location = f"{cidade_busca}, Brasil"
    response = requests.post(
        JOOBLE_URL.format(key=JOOBLE_API_KEY),
        json={"keywords": keywords, "location": location},
        timeout=10,
    )
    response.raise_for_status()
    dados = response.json()

    vagas = []
    for item in dados.get("jobs", []):
        local_bruto = item.get("location", "")
        if _ESTADOS_EUA_COLIDENTES.search(local_bruto):
            continue

        cidade = local_bruto.split(",")[0].strip() or cidade_busca
        cargo = item.get("title", "")[:255]
        vagas.append({
            "cargo": cargo,
            "empresa": item.get("company") or "Não informado",
            "cidade": cidade,
            "estado": estado,
            "salario": None,
            "modalidade": None,
            "veiculo": None,
            "categoria": cargo,  # substituído pelo chamador com a categoria correta
            "descricao": _limpar_html(item.get("snippet", "")),
            "beneficios": None,
            "requisitos": None,
            "link": item.get("link"),
            "fonte": "jooble",
        })
    return vagas


def _categoria_final(cargo, categoria_da_busca):
    """Usa a classificação por título quando ela reconhece algo específico no
    cargo; caso contrário, confia na categoria do termo que foi buscado."""
    detectada = classificar_categoria(cargo)
    return detectada if detectada != "Logística" else categoria_da_busca


def buscar_vagas_por_termo(termo: str, categoria: str):
    """Busca vagas na API do Jooble em todas as regiões para um único termo,
    já marcando a categoria correta. Retorna lista vazia sem JOOBLE_API_KEY."""
    if not JOOBLE_API_KEY:
        return []

    vagas = []
    for cidade, estado in REGIOES:
        try:
            encontradas = _buscar_uma_regiao(termo, cidade, estado)
        except requests.RequestException:
            continue
        for vaga in encontradas:
            vaga["categoria"] = _categoria_final(vaga["cargo"], categoria)
        vagas.extend(encontradas)
    return vagas


def buscar_vagas_todas_categorias():
    """Busca vagas para todos os termos/categorias, em todas as regiões. Usado
    apenas na primeira população do banco (custa bem mais chamadas de API)."""
    if not JOOBLE_API_KEY:
        return []

    vagas = []
    for termo, categoria in TERMOS_CATEGORIA:
        vagas.extend(buscar_vagas_por_termo(termo, categoria))
    return vagas


def buscar_vagas_proxima_categoria(indice: int):
    """Busca vagas para um único termo/categoria da rotação (mesmo custo de
    API que antes: uma chamada por região). `indice` deve avançar a cada
    execução do agendador para percorrer todas as categorias com o tempo."""
    if not JOOBLE_API_KEY:
        return []

    termo, categoria = TERMOS_CATEGORIA[indice % len(TERMOS_CATEGORIA)]
    return buscar_vagas_por_termo(termo, categoria)
