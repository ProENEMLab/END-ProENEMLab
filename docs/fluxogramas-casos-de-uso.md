# Fluxogramas dos casos de uso

Estes fluxogramas mostram como o sistema consulta e salva anotações de um tópico, ações do caso de uso UC05. O aluno precisa estar conectado à sua conta.

As etapas seguem o código do projeto: o Controller recebe o pedido, o Service organiza a operação e aplica as regras, e o Repository acessa o banco usando os Models e o SQLAlchemy.

## Recuperação de dados — Consultar anotações

```mermaid
flowchart TD
    inicio([Aluno abre as anotações de um tópico])
    pedido[Frontend envia GET para a API]
    controller[NoteController recebe o tópico e identifica o aluno]
    service[NotesService solicita a consulta do tópico]
    topicoRepo[TopicRepository busca o tópico pelo identificador]
    topicoBanco[(SQLite: consulta do tópico)]
    existe{Service recebe o resultado: tópico existe?}
    erro[API devolve erro 404 e frontend informa o problema]
    notasRepo[Service chama NoteRepository para filtrar por aluno e tópico]
    notasBanco[(SQLite: consulta das anotações)]
    retorno[Repository retorna as anotações ao Service]
    resposta[Service retorna ao Controller, que formata a resposta JSON]
    tela[Frontend mostra as anotações ou uma lista vazia]
    fim([Fim])

    inicio --> pedido --> controller --> service --> topicoRepo --> topicoBanco --> existe
    existe -->|Não| erro --> fim
    existe -->|Sim| notasRepo --> notasBanco --> retorno --> resposta --> tela --> fim
```

A consulta usa `GET /api/topics/{topic_id}/notes`. O método `NoteRepository.list_for_topic` busca somente as anotações daquele aluno e tópico, ordenadas da atualização mais recente para a mais antiga.

## Entrada de dados — Criar uma anotação

```mermaid
flowchart TD
    inicio([Aluno escreve uma anotação e solicita salvar])
    pedido[Frontend envia POST com o conteúdo para a API]
    controller[NoteController recebe o pedido e valida o conteúdo com NoteCreateSchema]
    valido{Conteúdo válido?}
    erroDados[API devolve erro de validação e frontend informa o problema]
    service[NotesService solicita a consulta do tópico]
    topicoRepo[TopicRepository busca o tópico pelo identificador]
    topicoBanco[(SQLite: consulta do tópico)]
    existe{Service recebe o resultado: tópico existe?}
    erroTopico[API devolve erro 404 e frontend informa o problema]
    model[Service cria o Model Note com aluno, tópico, conteúdo e datas]
    notasRepo[NoteRepository adiciona a anotação e confirma a gravação]
    notasBanco[(SQLite: gravação da anotação)]
    retorno[Service retorna a anotação ao Controller]
    resposta[Controller formata a resposta JSON com status 201]
    tela[Frontend apresenta a anotação salva]
    fim([Fim])

    inicio --> pedido --> controller --> valido
    valido -->|Não| erroDados --> fim
    valido -->|Sim| service --> topicoRepo --> topicoBanco --> existe
    existe -->|Não| erroTopico --> fim
    existe -->|Sim| model --> notasRepo --> notasBanco --> retorno --> resposta --> tela --> fim
```

A criação usa `POST /api/topics/{topic_id}/notes`. O conteúdo deve ser um texto com pelo menos um caractere. Os métodos `add` e `commit`, usados por `NoteRepository`, são herdados de `BaseRepository`.

Os diagramas mostram o caminho principal e as verificações de conteúdo e tópico. As verificações de autenticação acontecem antes de executar as ações do Controller.
