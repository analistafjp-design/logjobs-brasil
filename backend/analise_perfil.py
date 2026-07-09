"""Análise de currículo, sugestões de melhoria e geração de currículo formatado.

Determinístico e baseado em regras — mesma filosofia de recomendacao.py:
sem depender de nenhuma chave de LLM externa, já que o projeto não tem uma
configurada. "IA sob demanda" aqui significa automação que só roda quando o
candidato pede (abre a tela de análise/gera o currículo), nunca em segundo
plano.
"""
import json
from typing import Optional


def _lista_json(texto: Optional[str]) -> list:
    if not texto:
        return []
    try:
        return json.loads(texto)
    except (json.JSONDecodeError, TypeError):
        return []


def _contar_palavras(texto: Optional[str]) -> int:
    return len((texto or "").split())


def analisar_perfil(usuario) -> dict:
    """Retorna pontos fortes, lacunas e sugestões de melhoria do perfil do candidato."""
    experiencias = _lista_json(usuario.experiencias_json)
    formacoes = _lista_json(usuario.formacoes_json)
    idiomas = _lista_json(usuario.idiomas_json)
    cursos = _lista_json(usuario.cursos_json)
    certificados = _lista_json(usuario.certificados_json)

    pontos_fortes = []
    sugestoes = []

    if usuario.resumo and _contar_palavras(usuario.resumo) >= 30:
        pontos_fortes.append("Mini-currículo bem detalhado")
    elif usuario.resumo:
        sugestoes.append("Seu mini-currículo está curto — detalhe um pouco mais sua experiência e objetivos.")
    else:
        sugestoes.append("Você ainda não escreveu um mini-currículo. Ele é o que mais pesa nas recomendações de vagas.")

    if usuario.habilidades:
        total_habilidades = len([h for h in usuario.habilidades.split(",") if h.strip()])
        if total_habilidades >= 3:
            pontos_fortes.append(f"{total_habilidades} habilidades cadastradas")
        else:
            sugestoes.append("Cadastre mais habilidades separadas por vírgula (ex.: \"Direção defensiva, CNH E\").")
    else:
        sugestoes.append("Nenhuma habilidade cadastrada ainda — isso ajuda muito no motor de recomendação de vagas.")

    if experiencias:
        pontos_fortes.append(f"{len(experiencias)} experiência(s) profissional(is) cadastrada(s)")
        sem_descricao = sum(1 for e in experiencias if not (e.get("descricao") or "").strip())
        if sem_descricao:
            sugestoes.append(f"{sem_descricao} experiência(s) sem descrição — descreva suas responsabilidades e conquistas.")
    else:
        sugestoes.append("Cadastre pelo menos uma experiência profissional no seu perfil.")

    if formacoes:
        pontos_fortes.append(f"{len(formacoes)} formação/formações cadastrada(s)")
    else:
        sugestoes.append("Cadastre sua formação acadêmica ou técnica, mesmo que incompleta.")

    if usuario.possui_cnh:
        pontos_fortes.append(f"CNH categoria {usuario.possui_cnh}")
    else:
        sugestoes.append("Informe sua categoria de CNH, se tiver — é um dos filtros mais usados em vagas de logística.")

    if not idiomas:
        sugestoes.append("Cadastre idiomas, mesmo que seja só \"Português — Nativo\".")
    if not cursos and not certificados:
        sugestoes.append("Cursos e certificados (mesmo online e gratuitos) aumentam sua compatibilidade com vagas técnicas.")

    if usuario.linkedin_url or usuario.portfolio_url or usuario.github_url:
        pontos_fortes.append("Tem link de LinkedIn/portfólio cadastrado")
    else:
        sugestoes.append("Adicione seu LinkedIn ou portfólio, se tiver — passa mais confiança para a empresa.")

    if usuario.disponibilidade:
        pontos_fortes.append(f"Disponibilidade informada: {usuario.disponibilidade}")
    else:
        sugestoes.append("Informe sua disponibilidade para começar (Imediata, 15 dias, 30 dias...).")

    campos_preenchidos = [
        bool(usuario.telefone), bool(usuario.cidade), bool(usuario.resumo), bool(usuario.habilidades),
        bool(usuario.pretensao_salarial), bool(usuario.disponibilidade), bool(experiencias), bool(formacoes),
        bool(idiomas), bool(usuario.linkedin_url or usuario.portfolio_url or usuario.github_url),
    ]
    completude = round(100 * sum(campos_preenchidos) / len(campos_preenchidos))

    return {
        "completude": completude,
        "pontos_fortes": pontos_fortes,
        "sugestoes": sugestoes,
    }


def gerar_curriculo_texto(usuario) -> str:
    """Monta um currículo em texto plano formatado, pronto para copiar ou imprimir
    (Ctrl+P / "Salvar como PDF" do navegador) — não depende de nenhuma biblioteca
    de geração de PDF no cliente."""
    experiencias = _lista_json(usuario.experiencias_json)
    formacoes = _lista_json(usuario.formacoes_json)
    cursos = _lista_json(usuario.cursos_json)
    certificados = _lista_json(usuario.certificados_json)
    idiomas = _lista_json(usuario.idiomas_json)

    linhas = [usuario.nome.upper(), "=" * len(usuario.nome)]

    contato = [p for p in [usuario.email, usuario.telefone, usuario.cidade] if p]
    if contato:
        linhas.append(" | ".join(contato))
    links = [p for p in [usuario.linkedin_url, usuario.github_url, usuario.portfolio_url] if p]
    if links:
        linhas.append(" | ".join(links))
    linhas.append("")

    if usuario.resumo:
        linhas += ["RESUMO PROFISSIONAL", usuario.resumo, ""]

    dados_rapidos = []
    if usuario.possui_cnh:
        dados_rapidos.append(f"CNH: {usuario.possui_cnh}")
    if usuario.veiculo_proprio == "sim":
        dados_rapidos.append("Possui veículo próprio")
    if usuario.disponibilidade:
        dados_rapidos.append(f"Disponibilidade: {usuario.disponibilidade}")
    if usuario.pretensao_salarial:
        dados_rapidos.append(f"Pretensão salarial: R$ {usuario.pretensao_salarial:,.2f}")
    if dados_rapidos:
        linhas += ["DADOS COMPLEMENTARES", *dados_rapidos, ""]

    if usuario.habilidades:
        linhas += ["HABILIDADES", usuario.habilidades, ""]

    if experiencias:
        linhas.append("EXPERIÊNCIA PROFISSIONAL")
        for e in experiencias:
            periodo = f"{e.get('inicio') or '?'} – {e.get('fim') or 'atual'}"
            linhas.append(f"- {e.get('cargo', '')} | {e.get('empresa', '')} ({periodo})")
            if e.get("descricao"):
                linhas.append(f"  {e['descricao']}")
        linhas.append("")

    if formacoes:
        linhas.append("FORMAÇÃO ACADÊMICA")
        for f in formacoes:
            status = f" — {f.get('status')}" if f.get("status") else ""
            linhas.append(f"- {f.get('curso', '')} | {f.get('instituicao', '')}{status}")
        linhas.append("")

    if cursos:
        linhas.append("CURSOS")
        for c in cursos:
            ano = f" ({c.get('ano')})" if c.get("ano") else ""
            linhas.append(f"- {c.get('nome', '')}{ano}")
        linhas.append("")

    if certificados:
        linhas.append("CERTIFICADOS")
        for c in certificados:
            ano = f" ({c.get('ano')})" if c.get("ano") else ""
            linhas.append(f"- {c.get('nome', '')}{ano}")
        linhas.append("")

    if idiomas:
        linhas.append("IDIOMAS")
        for i in idiomas:
            nivel = f" — {i.get('nivel')}" if i.get("nivel") else ""
            linhas.append(f"- {i.get('idioma', '')}{nivel}")
        linhas.append("")

    return "\n".join(linhas).strip() + "\n"
