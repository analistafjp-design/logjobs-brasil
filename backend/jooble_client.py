import os
import requests

JOOBLE_API_KEY = os.getenv("JOOBLE_API_KEY")
JOOBLE_URL = "https://jooble.org/api/{key}"


def buscar_vagas_jooble(keywords: str = "logistica entregador motorista", location: str = "Brasil"):
    """Busca vagas na API do Jooble. Retorna lista vazia se JOOBLE_API_KEY não estiver configurada."""
    if not JOOBLE_API_KEY:
        return []

    response = requests.post(
        JOOBLE_URL.format(key=JOOBLE_API_KEY),
        json={"keywords": keywords, "location": location},
        timeout=10,
    )
    response.raise_for_status()
    dados = response.json()

    vagas = []
    for item in dados.get("jobs", []):
        vagas.append({
            "cargo": item.get("title", ""),
            "empresa": item.get("company") or "Não informado",
            "cidade": item.get("location", "").split(",")[0].strip() or "Não informado",
            "estado": "",
            "salario": None,
            "modalidade": None,
            "veiculo": None,
            "categoria": "Importado (Jooble)",
            "descricao": item.get("snippet", ""),
            "beneficios": None,
            "requisitos": None,
            "fonte": "jooble",
        })
    return vagas
