# DECISIONS

Este documento registra as decisões de arquitetura, tecnologia e produto da USM Platform.

O objetivo é preservar a lógica das decisões tomadas durante o desenvolvimento, permitindo evolução consistente da plataforma.

---

# D001 — Criação da plataforma

**Data:** 16/07/2026

## Decisão

Criar a USM Platform como um ecossistema de ferramentas voltadas para a gestão e automação da operação jurídica.

## Motivo

Evitar o desenvolvimento de aplicações isoladas para cada necessidade do escritório.

A plataforma permitirá concentrar diversos módulos em um único ambiente.

---

# D002 — Nome da plataforma

**Data:** 16/07/2026

## Decisão

Adotar o nome **USM Platform**.

## Motivo

O nome utiliza as iniciais da idealizadora do projeto, sem limitar a plataforma a uma única funcionalidade.

A marca permite expansão para novos módulos sem necessidade de alteração da identidade.

---

# D003 — Tecnologia

**Data:** 16/07/2026

## Decisão

Utilizar Python como linguagem principal.

Framework escolhido:

- Streamlit

Bibliotecas iniciais:

- Pandas
- OpenPyXL

## Motivo

Ferramentas gratuitas.

Alta produtividade.

Excelente capacidade para manipulação de grandes bases de dados.

Facilidade de evolução.

---

# D004 — Arquitetura

**Data:** 16/07/2026

## Decisão

Separar a aplicação em módulos independentes.

Estrutura inicial:

- app.py
- modules
- services
- assets
- uploads
- outputs

## Motivo

Facilitar manutenção.

Permitir expansão da plataforma.

Evitar concentração de toda a lógica em um único arquivo.

---

# D005 — Primeiro módulo

**Data:** 16/07/2026

## Decisão

O primeiro módulo da plataforma será a Conferência de Audiências.

## Motivo

Trata-se de uma atividade operacional repetitiva, com elevado potencial de automação e impacto direto na redução de falhas.

O módulo servirá como base arquitetural para os demais.

---

# D006 — Metodologia

**Data:** 16/07/2026

## Decisão

O desenvolvimento ocorrerá por Sprints.

Cada Sprint deverá possuir:

- objetivo definido;
- critérios de aceite;
- testes;
- atualização do CHANGELOG.

## Motivo

Permitir evolução incremental da plataforma, garantindo estabilidade e rastreabilidade.

---

# D007 — Filosofia do projeto

**Data:** 16/07/2026

## Decisão

Desenvolver a USM Platform como um software profissional desde a primeira versão.

## Princípios

- simplicidade para o usuário;
- arquitetura organizada;
- escalabilidade;
- documentação contínua;
- foco na experiência do usuário;
- automação de tarefas repetitivas.


---

# D008 — Princípio da Automação

**Data:** 16/07/2026

## Decisão

Toda funcionalidade implementada deverá reduzir tempo operacional, minimizar erros humanos ou aumentar a confiabilidade da informação.

## Motivo

A USM Platform não será desenvolvida para substituir o trabalho intelectual dos profissionais.

Seu propósito é automatizar tarefas repetitivas, reduzir riscos operacionais e permitir que a equipe concentre esforços em atividades estratégicas e de maior valor agregado.