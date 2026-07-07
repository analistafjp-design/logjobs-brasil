# 🚚 LogJobs Brasil

## Project Vision Document (PVD)

**Versão:** 1.0
**Autor:** Fábio Passos
**Status:** Documento vivo — deve ser revisado a cada novo ciclo de desenvolvimento

> Este documento é o manual oficial do projeto LogJobs Brasil. Ele orienta todas as decisões de produto, arquitetura e desenvolvimento, e serve também como material de apresentação para investidores, clientes e parceiros.

---

## 1. Visão do Projeto

O **LogJobs Brasil** será o maior portal especializado em empregos na área de logística do Brasil.

Nosso objetivo é conectar candidatos e empresas de forma rápida, inteligente e moderna, utilizando Inteligência Artificial para facilitar a busca de oportunidades.

Diferente dos portais tradicionais, o LogJobs Brasil será totalmente focado em logística, transporte e entregas. O sistema permitirá que candidatos encontrem vagas em segundos, enquanto empresas divulgam oportunidades para profissionais realmente qualificados.

---

## 2. Missão

Facilitar o acesso ao emprego na área logística utilizando tecnologia, automação e Inteligência Artificial.

---

## 3. Visão

Ser o maior portal especializado em logística da América Latina.

---

## 4. Valores

- Simplicidade
- Rapidez
- Transparência
- Tecnologia
- Inovação
- Segurança
- Inteligência Artificial
- Experiência do usuário

---

## 5. Público-Alvo

### Candidatos

- Entregadores
- Motoboys
- Motoristas
- Caminhoneiros
- Conferentes
- Auxiliares de Logística
- Estoquistas
- Operadores de Empilhadeira
- Supervisores
- Coordenadores
- Analistas
- Gestores

### Empresas

- Transportadoras
- Centros de Distribuição
- Operadores Logísticos
- E-commerce
- Supermercados
- Indústrias
- Empresas de Entrega
- Empresas de Transporte

---

## 6. Objetivo Principal

Criar um ecossistema completo de contratação para logística.

---

## 7. Diferenciais

Enquanto os concorrentes possuem vagas de todas as áreas, o LogJobs Brasil será especializado. Teremos:

- IA
- Estatísticas
- Dashboard
- Tendências
- Salários
- Empresas
- Histórico
- Alertas
- Busca Inteligente

---

## 8. Tecnologias

### Frontend

- HTML5
- CSS3
- JavaScript ES6

### Backend

- Python
- FastAPI

### Banco de Dados

- SQLite (inicial)
- PostgreSQL (posteriormente)

### IA

- Groq
- LLM

### Deploy

- GitHub Pages
- Render

### Versionamento

- GitHub

---

## 9. Arquitetura


---

## 10. Funcionalidades

### Página Inicial

- Hero moderno
- Busca
- Categorias
- Empresas
- Dashboard
- Vagas
- Footer

### Pesquisa

Pesquisar por:

- cargo
- cidade
- empresa
- estado
- salário
- modalidade
- veículo

### Empresas

Cada empresa terá:

- perfil
- vagas
- descrição
- benefícios
- localização
- avaliações (planejado)

### Página da Vaga

- Cargo
- Empresa
- Cidade
- Salário
- Descrição
- Benefícios
- Requisitos
- Botão "Candidatar-se"

### Dashboard

- Vagas
- Empresas
- Cidades
- Estados
- Salários
- Profissões
- Gráficos
- Mapa

### Login

- Candidato
- Empresa
- Administrador

### Painel Empresa

- Cadastrar vagas
- Editar vagas
- Remover vagas
- Ver candidatos

### Painel Admin

- Gerenciar usuários
- Empresas
- Vagas
- Dashboard
- Logs

---

## 11. Inteligência Artificial

A IA será responsável por:

- Classificar vagas
- Extrair salários
- Detectar benefícios
- Organizar categorias
- Criar recomendações
- Responder perguntas
- Sugerir vagas
- Gerar estatísticas

---

## 12. Busca Inteligente

Exemplo:

Usuário digita:

> "Motorista CNH D em Campinas"

A IA interpreta automaticamente:

- Cargo = Motorista
- CNH = D
- Cidade = Campinas

---

## 13. Dashboard Inteligente

Mostrar:

- Empresas contratando
- Estados em alta
- Profissões em crescimento
- Média salarial
- Novas vagas
- Tendências

---

## 14. APIs

Inicialmente:

- Jooble

Posteriormente:

- InfoJobs
- Gupy
- Catho
- LinkedIn (quando aplicável)
- Páginas "Trabalhe Conosco"

---

## 15. Banco de Dados

- Usuários
- Empresas
- Vagas
- Favoritos
- Alertas
- Logs
- Configurações

---

## 16. Segurança

- JWT
- HTTPS
- Criptografia
- Proteção contra SQL Injection
- Proteção XSS
- Rate Limit
- Validação de formulários

---

## 17. Design

Inspirado em:

- LinkedIn
- Indeed
- Stripe
- Linear
- Airbnb
- Apple

Visual: premium, responsivo, leve, elegante.

---

## 18. Padrão de Qualidade

Este capítulo define as regras que orientam **todas** as implementações futuras do projeto. Nenhuma funcionalidade deve ser considerada "pronta" se não atender a estes princípios.

### UX em primeiro lugar

Qualquer pessoa deve conseguir encontrar uma vaga em poucos cliques. Fluxos com mais de 3 passos entre a intenção do usuário e o resultado devem ser reavaliados.

### Performance

Páginas devem carregar em menos de 2 segundos. Toda nova página ou funcionalidade deve ser validada quanto a tempo de carregamento antes do deploy.

### Mobile First

A experiência em celulares deve ser projetada e validada antes da versão desktop, já que a maior parte do público (entregadores, motoristas, candidatos) acessa o portal via smartphone.

### Código modular e documentado

Cada componente deve ter uma responsabilidade clara e única. Módulos de coleta, IA, API e frontend devem ser desacoplados, permitindo evolução independente.

### Escalabilidade

A arquitetura deve suportar o crescimento de centenas para milhares de vagas sem necessidade de reescrita. Decisões de banco de dados e API devem considerar esse crescimento desde o início.

### Acessibilidade

Cores, contraste e navegação devem ser pensados para o maior número possível de usuários, seguindo boas práticas de acessibilidade web (contraste mínimo, navegação por teclado, textos alternativos).

### Critério de aceite

Toda nova funcionalidade só deve ser incorporada ao produto após verificação de alinhamento com os princípios acima. Esse checklist é o "norte" do projeto e garante consistência e aparência profissional do início ao fim.

---

## 19. Roadmap

| Sprint | Entrega |
|--------|---------|
| 1 | Landing Page Premium |
| 2 | Busca de vagas |
| 3 | Integração FastAPI |
| 4 | Banco SQLite |
| 5 | Dashboard |
| 6 | IA |
| 7 | Login |
| 8 | Empresas |
| 9 | Alertas |
| 10 | Deploy Oficial |

---

## 20. Monetização

- Plano gratuito para candidatos
- Planos para empresas
- Vagas em destaque
- Publicidade
- Cursos
- Afiliados
- Relatórios premium

---

## 21. Objetivo Final

O LogJobs Brasil não será apenas um portal de vagas. Será uma plataforma inteligente para conectar profissionais, empresas e dados do mercado logístico, oferecendo uma experiência moderna, rápida e confiável.
