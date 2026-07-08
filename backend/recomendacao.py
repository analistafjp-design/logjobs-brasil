"""Motor de recomendação de vagas por sobreposição de palavras-chave.

Não usa nenhuma API externa de IA (sem chave configurada no projeto) — é um
mecanismo determinístico e transparente de correspondência de termos entre o
mini-currículo do candidato e o texto da vaga, com pesos por campo. Cobre os
itens "Recomendação automática de vagas" e "Análise de compatibilidade" da
especificação do produto sem depender de infraestrutura externa.
"""
import re

STOPWORDS_PT = {
    "a", "o", "as", "os", "de", "da", "do", "das", "dos", "e", "em", "um", "uma",
    "uns", "umas", "para", "com", "sem", "por", "que", "sou", "eu", "me", "meu",
    "minha", "meus", "minhas", "tenho", "trabalho", "trabalhei", "trabalhar",
    "anos", "ano", "no", "na", "nos", "nas", "ao", "aos", "às", "sobre", "mais",
    "muito", "muita", "já", "também", "como", "ser", "está", "foi", "sua", "seu",
}


def tokenizar(texto: str) -> set:
    if not texto:
        return set()
    palavras = re.findall(r"[a-zà-ú]+", texto.lower())
    return {p for p in palavras if len(p) >= 3 and p not in STOPWORDS_PT}


def texto_vaga_por_campo(vaga) -> dict:
    return {
        "cargo": vaga.cargo or "",
        "categoria": vaga.categoria or "",
        "requisitos": vaga.requisitos or "",
        "beneficios": vaga.beneficios or "",
        "descricao": vaga.descricao or "",
    }


PESOS_CAMPO = {"cargo": 3, "categoria": 3, "requisitos": 2, "beneficios": 1, "descricao": 1}


def pontuar_vaga(tokens_usuario: set, vaga) -> tuple:
    """Retorna (pontuacao_bruta, percentual_compatibilidade)."""
    if not tokens_usuario:
        return 0, 0

    campos = texto_vaga_por_campo(vaga)
    tokens_encontrados = set()
    pontuacao = 0

    for campo, texto in campos.items():
        tokens_campo = tokenizar(texto)
        interseccao = tokens_usuario & tokens_campo
        if interseccao:
            pontuacao += len(interseccao) * PESOS_CAMPO[campo]
            tokens_encontrados |= interseccao

    percentual = round(min(1.0, len(tokens_encontrados) / len(tokens_usuario)) * 100)
    return pontuacao, percentual


def recomendar_vagas(resumo_usuario: str, vagas: list, limite: int = 6) -> list:
    tokens_usuario = tokenizar(resumo_usuario)
    if not tokens_usuario:
        return []

    pontuadas = []
    for vaga in vagas:
        pontuacao, percentual = pontuar_vaga(tokens_usuario, vaga)
        if pontuacao > 0:
            pontuadas.append((pontuacao, percentual, vaga))

    pontuadas.sort(key=lambda item: item[0], reverse=True)
    return [
        {"vaga": vaga, "compatibilidade": percentual}
        for _, percentual, vaga in pontuadas[:limite]
    ]
