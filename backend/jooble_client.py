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
        vagas.append({
            "cargo": item.get("title", "")[:255],
            "empresa": item.get("company") or "Não informado",
            "cidade": cidade,
            "estado": location.split(",")[-1].strip() if "," in location else "",
            "salario": None,
            "modalidade": None,
            "veiculo": None,
            "categoria": "Importado (Jooble)",
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
