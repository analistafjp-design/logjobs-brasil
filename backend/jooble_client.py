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
    (re.compile(r"entregador|delivery", re.I), "Entregador"),
    (re.compile(r"caminhoneiro|carreteiro|caminh[aã]o", re.I), "Caminhoneiro"),
    (re.compile(r"motorista", re.I), "Motorista"),
    (re.compile(r"estoquista|estoque", re.I), "Estoquista"),
    (re.compile(r"conferente", re.I), "Conferente"),
    (re.compile(r"auxiliar", re.I), "Auxiliar Logístico"),
    (re.compile(r"supervisor", re.I), "Supervisor"),
    (re.compile(r"coordenador", re.I), "Coordenador"),
    (re.compile(r"analista", re.I), "Analista"),
    (re.compile(r"gestor|gerente", re.I), "Gestor"),
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


PALAVRAS_CHAVE = "logistica entregador motorista estoquista conferente operador de empilhadeira"

REGIOES = [
    "São Paulo, SP", "Rio de Janeiro, RJ", "Belo Horizonte, MG", "Curitiba, PR",
    "Porto Alegre, RS", "Salvador, BA", "Recife, PE", "Fortaleza, CE",
    "Brasília, DF", "Manaus, AM", "Goiânia, GO", "Florianópolis, SC",
    "Vitória, ES", "Belém, PA", "Campo Grande, MS", "Cuiabá, MT",
]


def _buscar_uma_regiao(keywords: str, location: str):
    response = requests.post(
        JOOBLE_URL.format(key=JOOBLE_API_KEY),
        json={"keywords": keywords, "location": location},
        timeout=10,
    )
    response.raise_for_status()
    dados = response.json()

    vagas = []
    for item in dados.get("jobs", []):
        cidade = item.get("location", "").split(",")[0].strip() or "Não informado"
        cargo = item.get("title", "")[:255]
        vagas.append({
            "cargo": cargo,
            "empresa": item.get("company") or "Não informado",
            "cidade": cidade,
            "estado": location.split(",")[-1].strip() if "," in location else "",
            "salario": None,
            "modalidade": None,
            "veiculo": None,
            "categoria": classificar_categoria(cargo),
            "descricao": _limpar_html(item.get("snippet", "")),
            "beneficios": None,
            "requisitos": None,
            "link": item.get("link"),
            "fonte": "jooble",
        })
    return vagas


def buscar_vagas_jooble(keywords: str = PALAVRAS_CHAVE, location: str = "Brasil"):
    """Busca vagas na API do Jooble para uma única região. Retorna lista vazia se JOOBLE_API_KEY não estiver configurada."""
    if not JOOBLE_API_KEY:
        return []

    return _buscar_uma_regiao(keywords, location)


def buscar_vagas_todas_regioes():
    """Busca vagas na API do Jooble em várias capitais brasileiras para maximizar a cobertura regional.
    Retorna lista vazia se JOOBLE_API_KEY não estiver configurada."""
    if not JOOBLE_API_KEY:
        return []

    vagas = []
    for regiao in REGIOES:
        try:
            vagas.extend(_buscar_uma_regiao(PALAVRAS_CHAVE, regiao))
        except requests.RequestException:
            continue
    return vagas
