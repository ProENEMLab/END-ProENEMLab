# Arquitetura e fluxo de dados

O sistema tem três partes principais: as páginas que o aluno usa no navegador, o servidor que processa as ações e o banco que guarda os dados. Na execução local, o Flask entrega tanto as páginas quanto a API.

## Diagrama de arquitetura

```mermaid
flowchart TD
    aluno[Aluno] --> interface[Interface: HTML, CSS e JavaScript]
    interface <-->|HTTP| servidor[Servidor Flask]
    servidor --> controllers[Controllers: recebem as requisições]
    controllers --> views[Views: validam entradas e formatam respostas]
    controllers --> services[Services: regras do sistema]
    services --> repositories[Repositories: acesso aos dados]
    repositories --> models[Models e SQLAlchemy]
    models <-->|Leitura e gravação| banco[(SQLite)]
    services <-->|Importação de provas| fonte[enem-api]
    services -->|Quando configurado| canais[E-mail e notificações do navegador]
```

Os nomes das camadas correspondem às pastas do backend. A pasta `views` contém validações e formatos de resposta da API; as telas ficam em `frontend/public`.

A consulta à enem-api acontece na importação das provas. Depois disso, as questões são consultadas no banco local.

## Diagrama de fluxo de dados (DFD simplificado)

Este diagrama mostra os principais dados que entram e saem do sistema. Os processos e depósitos foram agrupados para facilitar a leitura; não representam todas as rotas ou tabelas.

```mermaid
flowchart LR
    aluno[Aluno]
    operador[Responsável pela importação]
    fonte[enem-api]
    acesso([1. Gerenciar acesso])
    pratica([2. Resolver questões])
    estudo([3. Organizar estudos])
    relatorios([4. Consultar desempenho])
    importar([5. Importar provas])
    usuarios[(D1: Usuários)]
    questoes[(D2: Questões e alternativas)]
    registros[(D3: Respostas e dados de estudo)]

    aluno -->|Cadastro e credenciais| acesso
    acesso -->|Cadastro| usuarios
    usuarios -->|Dados para autenticação| acesso
    acesso -->|Token de acesso e dados da conta| aluno
    aluno -->|Filtros e alternativa escolhida| pratica
    questoes -->|Enunciados, alternativas e gabaritos| pratica
    pratica -->|Tentativas e resultados| registros
    pratica -->|Questão e correção| aluno
    aluno -->|Horários, metas e anotações| estudo
    registros -->|Planejamento e revisões salvos| estudo
    estudo -->|Planejamento, sessões e revisões| registros
    estudo -->|Agenda e revisões pendentes| aluno
    aluno -->|Pedido de consulta ou exportação| relatorios
    registros -->|Histórico de estudo| relatorios
    relatorios -->|Estatísticas e PDF| aluno
    operador -->|Ano da prova| importar
    importar -->|Pedido das provas| fonte
    fonte -->|Questões e gabaritos| importar
    importar -->|Provas importadas| questoes
```

Por exemplo, ao responder uma questão, o aluno envia a alternativa escolhida. O servidor consulta o gabarito, registra a tentativa e devolve o resultado. Esse histórico também é usado nas estatísticas e nas revisões.
