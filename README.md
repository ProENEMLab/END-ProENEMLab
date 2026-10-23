# ProENEM Lab

O ProENEM Lab é um projeto escolar de uma plataforma de estudos para o ENEM. A ideia é reunir questões de provas anteriores e ferramentas para organizar a rotina de estudo e acompanhar o desempenho.
## Integrantes:
- Analice Carvalho
- Bernardo Magalhães
- Caio Luciano
- Davi Fontana
- Isabela Brasil
- Lucas Gabriel

## Funcionalidades

O resumo abaixo segue a ordem dos 20 requisitos e descreve o funcionamento atual, incluindo as partes que ainda dependem de dados ou configuração.

1. **Cadastro e acesso:** cadastro e login por e-mail e senha, com senha protegida por hash e autenticação por token. A recuperação de senha é uma simulação local, sem envio de e-mail. O login por redes sociais ainda não está implementado.

2. **Dashboard principal:** apresenta o próximo tópico da trilha, a meta do dia e a sequência atual de dias de estudo (streak).

3. **Roadmap linear:** organiza os tópicos em uma sequência e acompanha o progresso individual do aluno. A ordem pode usar a incidência dos conteúdos e os pré-requisitos cadastrados; a sequência não é gerada individualmente para cada usuário.

4. **Anotações por tópico:** permite criar, consultar, editar e excluir anotações vinculadas diretamente aos tópicos da trilha, sem organizar pastas ou tags.

5. **Correção de questões:** apresenta a resposta correta após o envio e exibe explicação em texto, imagem ou vídeo quando disponível. As questões importadas podem trazer apenas a referência ao gabarito oficial, sem comentário pedagógico detalhado.

6. **Banco de questões:** permite importar provas pela enem-api e buscar questões por ano, matéria, tópico, idioma e dificuldade. A cobertura depende das edições disponíveis na fonte e já importadas; o projeto não vem com todas as provas desde 2009.

7. **Estatísticas de desempenho:** mostra percentuais de acerto por tópico e matéria, os três tópicos com pior rendimento e a distribuição dos erros. O aluno pode classificar respostas erradas como falta de conceito ou erro de atenção.

8. **Pomodoro integrado:** oferece períodos de foco e descanso ligados às disciplinas e aos blocos do calendário semanal, com registro das sessões de estudo.

9. **Dificuldade das questões:** apresenta os níveis fácil, médio e difícil. A classificação usa parâmetros de dificuldade do INEP quando importados e vinculados, ou estatísticas da própria plataforma quando há dados suficientes. Sem esses dados, a questão fica sem classificação.

10. **Avanço de dificuldade:** libera o próximo nível por tópico ao atingir pelo menos 80% de acertos na janela de avaliação. Por padrão, considera até dez primeiras respostas a questões distintas do nível e exige dez questões, ou a quantidade disponível quando menor.

11. **Sequência de estudos:** acompanha o streak atual e o maior streak registrado. Medalhas por conquistas e rankings mensais entre usuários ainda não estão implementados.

12. **Pontos por atividade:** registra +5 pontos por questão respondida, +10 por Pomodoro concluído, +15 por meta concluída e +20 a cada marco de sete dias consecutivos de estudo.

13. **Metas diárias:** permite cadastrar uma descrição e uma data, marcar a conclusão e excluir metas. O aluno pode escrever metas específicas e mensuráveis, mas o sistema não valida automaticamente os critérios SMART nem mede seu cumprimento pelo texto.

14. **Planejamento semanal:** permite criar, mover e redimensionar blocos de disciplinas arrastando no calendário. Cada bloco pode iniciar seu Pomodoro; o início automático no horário previsto depende da configuração escolhida.

15. **Foco Total:** integra as sessões Pomodoro a uma interface de foco com fundo escuro e opção de tela cheia. A tela cheia depende das permissões e da interação exigida pelo navegador; o site não bloqueia notificações externas do sistema operacional.

16. **Revisão de erros:** programa revisões espaçadas das questões erradas para 1, 3 e 7 dias a partir da data de referência do ciclo, apresenta as revisões pendentes e registra novas respostas. Os avisos externos dependem da configuração de notificações.

17. **Relatório semanal:** compara o desempenho por tópico, indica evolução ou regressão quando há respostas suficientes e apresenta o tempo líquido de estudo registrado nas sessões.

18. **Atualização do roadmap:** gera versões da trilha usando arquivos de referência do edital, mapeamentos de conteúdos e incidência nas cinco edições definidas no catálogo. Há agendamento anual para gerar um rascunho, mas os arquivos e as provas precisam ser atualizados e a nova versão precisa ser ativada pelo responsável.

19. **Exportação em PDF:** reúne anotações por tópico e questões erradas com respostas corretas e explicações disponíveis. A exportação aceita filtros e possui limites configuráveis de quantidade de anotações e questões.

20. **Notificações e lembretes:** permite configurar avisos de metas pendentes, revisões e manutenção do streak por e-mail ou push. O envio exige configuração dos canais, permissão do navegador para push e ativação do agendador para os disparos automáticos.

Os planos Pro e Elite aparecem como propostas futuras. Ainda não há cobrança ou assinatura.

## Tecnologias

| Parte | Tecnologias |
| --- | --- |
| Interface | HTML, CSS e JavaScript |
| Servidor e API | Python e Flask |
| Banco local | SQLite e Flask-SQLAlchemy |
| Autenticação | Flask-JWT-Extended e Werkzeug |
| Validação de dados | Marshmallow |
| Geração de PDF | ReportLab |

## Como executar

É necessário ter Python 3.11 ou mais recente. O frontend e a API executam em servidores separados. Use dois terminais, começando na pasta do projeto.

No primeiro terminal, prepare o ambiente e inicie a API:

### Windows (Prompt de Comando)

```bat
py -3 -m venv venv
venv\Scripts\activate
python -m pip install -r backend\requirements.txt
cd backend
python run.py
```

### Linux ou macOS

```bash
python3 -m venv venv
source venv/bin/activate
python -m pip install -r backend/requirements.txt
cd backend
python run.py
```

### Frontend (segundo terminal)

Na pasta do projeto, execute:

Windows:

```bat
py -3 -m http.server 8000 --bind 127.0.0.1 --directory frontend/public
```

Linux ou macOS:

```bash
python3 -m http.server 8000 --bind 127.0.0.1 --directory frontend/public
```

Abra http://localhost:8000 no navegador. Mantenha os dois terminais abertos:

- O servidor da porta 8000 entrega as páginas, os estilos e os scripts.
- A API Flask atende em `http://localhost:5000/api` e acessa o banco.
- O JavaScript das páginas envia as requisições para a API. O CORS do backend já permite a origem `http://localhost:8000`.

O banco é criado automaticamente em `backend/proenem.db`. Para encerrar, pressione `Ctrl+C` em cada terminal.

Se alterar o endereço da API, ajuste `frontend/public/assets/js/config.js`. Se alterar o endereço do frontend, ajuste também a variável de ambiente `CORS_ORIGINS` do backend.

Para configurar notificações externas, `FRONTEND_BASE_URL` indica o endereço das páginas e `PUBLIC_BASE_URL` indica o endereço da API usado no cancelamento dos lembretes.

### Dados de exemplo

Com o ambiente virtual ativado, dentro de `backend`, execute:

```bash
python -m flask --app app_factory:create_app seed
```

Esse comando limpa parte dos dados existentes e cria dados de demonstração. Use apenas em um banco de testes, sem informações que queira manter.

Conta de demonstração:

- E-mail: `demo@proenem.lab`
- Senha: `password123`

### Importar questões do ENEM

Para buscar as questões de uma edição, também dentro de `backend`:

```bash
python -m flask --app app_factory:create_app sync-enem --year 2023
```

A importação precisa de internet. As questões são obtidas pela enem-api e ficam armazenadas no banco local. Os dados de demonstração do comando `seed` são separados das questões importadas.

## Organização do projeto

```text
backend/
  controllers/    Rotas da API e comandos de terminal
  services/       Regras de funcionamento do sistema
  repositories/   Consultas e gravações no banco
  models/         Definição das tabelas e relacionamentos
  views/          Validação e formatação dos dados da API
  app_factory.py  Criação da aplicação
  config.py       Configurações de ambiente
  run.py          Inicialização do servidor
frontend/public/
  assets/         Estilos, scripts e imagens
  pages/          Páginas das funcionalidades
  index.html      Página inicial
```

## Documentação

- [Arquitetura e fluxo de dados](docs/arquitetura.md)
- [Casos de uso simplificados](docs/casos-de-uso.md)
- [Fluxogramas dos casos de uso](docs/fluxogramas-casos-de-uso.md)
- [Diagrama de classes do domínio](docs/diagrama-de-classes.md)
- [Dicionário de dados resumido](docs/dicionario-dados.md)

## Situação atual

O projeto está em desenvolvimento e as instruções acima são para uso local. A recuperação de senha ainda é uma simulação: o token aparece no terminal do servidor, sem envio de e-mail ao usuário.

As notificações externas precisam de configuração de e-mail ou de chaves para envio pelo navegador. O agendamento automático vem desativado por padrão.

Antes de publicar, é necessário definir `SECRET_KEY` e `JWT_SECRET_KEY` com valores próprios e ajustar a execução para produção. O banco ainda não possui um sistema de migrações e o repositório não inclui uma suíte de testes automatizados.

## Origem das questões

As questões de provas anteriores são obtidas pela [enem-api](https://enem.dev), que disponibiliza conteúdo das provas do ENEM/INEP. O sistema mantém a identificação da fonte nas questões importadas.
