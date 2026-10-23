# ProENEM Lab

O ProENEM Lab é um projeto escolar de uma plataforma de estudos para o ENEM. A ideia é reunir questões de provas anteriores e ferramentas para organizar a rotina de estudo e acompanhar o desempenho.

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

É necessário ter Python 3.11 ou mais recente. Execute os comandos a partir da pasta do projeto.

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

Abra http://127.0.0.1:5000 no navegador. O próprio Flask serve as páginas; não é necessário iniciar outro servidor para o frontend.

O banco é criado automaticamente em `backend/proenem.db`. Para encerrar o servidor, pressione `Ctrl+C` no terminal.

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
- [Dicionário de dados resumido](docs/dicionario-dados.md)

## Situação atual

O projeto está em desenvolvimento e as instruções acima são para uso local. A recuperação de senha ainda é uma simulação: o token aparece no terminal do servidor, sem envio de e-mail ao usuário.

As notificações externas precisam de configuração de e-mail ou de chaves para envio pelo navegador. O agendamento automático vem desativado por padrão.

Antes de publicar, é necessário definir `SECRET_KEY` e `JWT_SECRET_KEY` com valores próprios e ajustar a execução para produção. O banco ainda não possui um sistema de migrações e o repositório não inclui uma suíte de testes automatizados.

## Origem das questões

As questões de provas anteriores são obtidas pela [enem-api](https://enem.dev), que disponibiliza conteúdo das provas do ENEM/INEP. O sistema mantém a identificação da fonte nas questões importadas.
