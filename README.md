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

- Cadastro e login de usuários.
- Busca de questões por ano, matéria, tópico, idioma e dificuldade.
- Registro das respostas e estatísticas de acerto.
- Trilha de tópicos, anotações e revisão de questões erradas.
- Calendário de estudos e Pomodoro, com períodos de foco e descanso.
- Metas diárias, pontos e contagem de dias seguidos de estudo.
- Relatórios de estudo e exportação em PDF.
- Notificações, com envio externo dependente de configuração.

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
- [Diagrama de classes do domínio](docs/diagrama-de-classes.md)
- [Dicionário de dados resumido](docs/dicionario-dados.md)

## Situação atual

O projeto está em desenvolvimento e as instruções acima são para uso local. A recuperação de senha ainda é uma simulação: o token aparece no terminal do servidor, sem envio de e-mail ao usuário.

As notificações externas precisam de configuração de e-mail ou de chaves para envio pelo navegador. O agendamento automático vem desativado por padrão.

Antes de publicar, é necessário definir `SECRET_KEY` e `JWT_SECRET_KEY` com valores próprios e ajustar a execução para produção. O banco ainda não possui um sistema de migrações e o repositório não inclui uma suíte de testes automatizados.

## Origem das questões

As questões de provas anteriores são obtidas pela [enem-api](https://enem.dev), que disponibiliza conteúdo das provas do ENEM/INEP. O sistema mantém a identificação da fonte nas questões importadas.
