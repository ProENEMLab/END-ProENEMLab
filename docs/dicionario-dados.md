# Dicionário de dados resumido

Este documento detalha as principais tabelas de cadastro, questões e estudo. As tabelas auxiliares estão resumidas ao final. A definição completa fica em `backend/models`.

Os tipos seguem os modelos do SQLAlchemy. PK identifica um registro e FK aponta para outra tabela. Campos opcionais aceitam valor nulo. Booleano significa verdadeiro ou falso. As regras abaixo mostram as restrições de cada coluna; não incluem todos os índices e regras que envolvem várias colunas.

## `users`

Cadastro, senha protegida por hash, recuperação de acesso e pontos do aluno.

| Campo | Tipo | Regra | Descrição |
| --- | --- | --- | --- |
| id | Inteiro | PK | Identificador do registro. |
| name | Texto (120) | Obrigatório | Nome. |
| email | Texto (255) | Único | E-mail de acesso. |
| password_hash | Texto (255) | Obrigatório | Hash da senha, sem guardar a senha original. |
| reset_token | Texto (255) | Opcional | Token de recuperação de senha. |
| reset_token_expires_at | Data/hora | Opcional | Validade do token. |
| total_points | Inteiro | Obrigatório | Total de pontos. |
| created_at | Data/hora | Obrigatório | Criação do registro. |

## `questions`

Enunciados, gabaritos, origem e dificuldade das questões.

| Campo | Tipo | Regra | Descrição |
| --- | --- | --- | --- |
| id | Inteiro | PK | Identificador do registro. |
| year | Inteiro | Obrigatório | Ano da prova. |
| subject | Texto (80) | Obrigatório | Matéria ou área, armazenada como texto. |
| topic_id | Inteiro | FK: topics.id, Opcional | Tópico relacionado. |
| statement | Texto | Obrigatório | Enunciado. |
| image_url | Texto (255) | Opcional | Endereço da imagem. |
| correct_option | Texto (1) | Obrigatório | Letra da resposta correta. |
| explanation_text | Texto | Obrigatório | Explicação ou referência ao gabarito. |
| explanation_image_url | Texto (255) | Opcional | Imagem da explicação. |
| explanation_video_url | Texto (255) | Opcional | Vídeo da explicação. |
| enem_index | Inteiro | Opcional | Número da questão na prova de origem. |
| language | Texto (32) | Obrigatório | Idioma; pode estar vazio. |
| discipline | Texto (40) | Opcional | Disciplina informada na importação. |
| context | Texto | Opcional | Texto de apoio. |
| files_json | Texto | Opcional | Lista de arquivos em JSON. |
| alternatives_introduction | Texto | Opcional | Introdução das alternativas. |
| enem_title | Texto (255) | Opcional | Título na origem. |
| source | Texto (32) | Obrigatório | Origem, como seed ou enem-api. |
| inep_item_code | Texto (64) | Opcional | Código do item do INEP. |
| difficulty | Texto (16) | Opcional | Classificação: easy, medium ou hard. |
| enem_correct_rate | Decimal | Opcional | Taxa de acerto de referência. |
| difficulty_source | Texto (16) | Opcional | Fonte da classificação. |
| difficulty_value | Decimal | Opcional | Valor usado na classificação. |
| difficulty_updated_at | Data/hora | Opcional | Atualização da dificuldade. |

## `question_options`

Alternativas de cada questão.

| Campo | Tipo | Regra | Descrição |
| --- | --- | --- | --- |
| id | Inteiro | PK | Identificador do registro. |
| question_id | Inteiro | FK: questions.id | Questão relacionada. |
| letter | Texto (1) | Obrigatório | Letra da alternativa. |
| text | Texto | Obrigatório | Texto da alternativa. |
| file_url | Texto | Opcional | Endereço de arquivo ou imagem. |

## `attempts`

Respostas enviadas pelos alunos.

| Campo | Tipo | Regra | Descrição |
| --- | --- | --- | --- |
| id | Inteiro | PK | Identificador do registro. |
| user_id | Inteiro | FK: users.id | Aluno relacionado. |
| question_id | Inteiro | FK: questions.id | Questão relacionada. |
| selected_option | Texto (1) | Obrigatório | Alternativa escolhida. |
| is_correct | Booleano | Obrigatório | Indica acerto. |
| error_type | Texto (32) | Opcional | Tipo de erro: conceito ou atencao. |
| answered_at | Data/hora | Obrigatório | Momento da resposta. |

## `topics`

Conteúdos organizados na trilha de estudo.

| Campo | Tipo | Regra | Descrição |
| --- | --- | --- | --- |
| id | Inteiro | PK | Identificador do registro. |
| name | Texto (150) | Obrigatório | Nome. |
| subject | Texto (80) | Obrigatório | Matéria ou área, armazenada como texto. |
| order_index | Inteiro | Único | Posição na trilha. |
| description | Texto | Opcional | Descrição. |
| inep_incidence | Decimal | Opcional | Valor de incidência usado pelo sistema. |

## `user_topic_progress`

Situação de cada tópico para cada aluno.

| Campo | Tipo | Regra | Descrição |
| --- | --- | --- | --- |
| id | Inteiro | PK | Identificador do registro. |
| user_id | Inteiro | FK: users.id | Aluno relacionado. |
| topic_id | Inteiro | FK: topics.id | Tópico relacionado. |
| status | Texto (32) | Obrigatório | Situação do registro. |
| updated_at | Data/hora | Obrigatório | Última atualização. |

## `notes`

Anotações dos alunos.

| Campo | Tipo | Regra | Descrição |
| --- | --- | --- | --- |
| id | Inteiro | PK | Identificador do registro. |
| user_id | Inteiro | FK: users.id | Aluno relacionado. |
| topic_id | Inteiro | FK: topics.id | Tópico relacionado. |
| content | Texto | Obrigatório | Texto da anotação. |
| created_at | Data/hora | Obrigatório | Criação do registro. |
| updated_at | Data/hora | Obrigatório | Última atualização. |

## `daily_goals`

Metas diárias.

| Campo | Tipo | Regra | Descrição |
| --- | --- | --- | --- |
| id | Inteiro | PK | Identificador do registro. |
| user_id | Inteiro | FK: users.id | Aluno relacionado. |
| description | Texto (255) | Obrigatório | Descrição. |
| target_date | Data | Obrigatório | Dia previsto para a meta. |
| is_completed | Booleano | Obrigatório | Indica conclusão. |
| completed_at | Data/hora | Opcional | Momento da conclusão. |
| created_at | Data/hora | Obrigatório | Criação do registro. |

## `subjects`

Disciplinas usadas no calendário.

| Campo | Tipo | Regra | Descrição |
| --- | --- | --- | --- |
| id | Inteiro | PK | Identificador do registro. |
| name | Texto (80) | Único | Nome. |
| slug | Texto (80) | Único | Nome simplificado para identificação. |
| area | Texto (2) | Opcional | Sigla da área. |
| color | Texto (7) | Obrigatório | Cor usada na interface. |

## `study_blocks`

Horários planejados para estudo.

| Campo | Tipo | Regra | Descrição |
| --- | --- | --- | --- |
| id | Inteiro | PK | Identificador do registro. |
| user_id | Inteiro | FK: users.id | Aluno relacionado. |
| subject_id | Inteiro | FK: subjects.id | Disciplina relacionada. |
| week_start | Data | Obrigatório | Início da semana. |
| day_of_week | Inteiro | Obrigatório | Dia da semana. |
| start_minute | Inteiro | Obrigatório | Início em minutos desde meia-noite. |
| duration_minutes | Inteiro | Obrigatório | Duração em minutos. |
| created_at | Data/hora | Obrigatório | Criação do registro. |
| updated_at | Data/hora | Obrigatório | Última atualização. |

## `study_sessions`

Sessões de estudo realizadas.

| Campo | Tipo | Regra | Descrição |
| --- | --- | --- | --- |
| id | Inteiro | PK | Identificador do registro. |
| user_id | Inteiro | FK: users.id | Aluno relacionado. |
| subject_id | Inteiro | FK: subjects.id | Disciplina relacionada. |
| block_id | Inteiro | FK: study_blocks.id, Opcional | Bloco de estudo de origem. |
| status | Texto (16) | Obrigatório | Situação do registro. |
| planned_cycles | Inteiro | Obrigatório | Quantidade de ciclos planejados. |
| completed_cycles | Inteiro | Obrigatório | Quantidade de ciclos concluídos. |
| started_at | Data/hora | Obrigatório | Início. |
| ended_at | Data/hora | Opcional | Encerramento. |
| focused_seconds | Inteiro | Obrigatório | Tempo de foco em segundos. |

## `review_cycles`

Ciclos de revisão de questões.

| Campo | Tipo | Regra | Descrição |
| --- | --- | --- | --- |
| id | Inteiro | PK | Identificador do registro. |
| user_id | Inteiro | FK: users.id | Aluno relacionado. |
| question_id | Inteiro | FK: questions.id | Questão relacionada. |
| status | Texto (16) | Obrigatório | Situação do registro. |
| anchor_date | Data | Obrigatório | Data de referência do ciclo. |
| current_stage | Inteiro | Obrigatório | Etapa atual. |
| due_date | Data | Obrigatório | Data prevista da próxima revisão. |
| restart_count | Inteiro | Obrigatório | Quantidade de reinícios. |
| created_at | Data/hora | Obrigatório | Criação do registro. |
| updated_at | Data/hora | Obrigatório | Última atualização. |
| completed_at | Data/hora | Opcional | Momento da conclusão. |

## Tabelas auxiliares

| Tabela | Dados armazenados |
| --- | --- |
| focus_interruptions | Interrupções de uma sessão. |
| focus_intervals | Intervalos de foco de uma sessão. |
| inep_difficulty_cutoffs | Limites de dificuldade por área. |
| inep_item_params | Identificação e parâmetros dos itens do INEP. |
| inep_refreshes | Controle de atualização da incidência. |
| notification_log | Histórico de envio e falhas. |
| notification_messages | Mensagens e indicação de leitura. |
| notification_preferences | Canais, tipos e horários de silêncio. |
| points_transactions | Histórico de pontos e motivos. |
| pomodoro_settings | Configurações de foco e pausas. |
| push_subscriptions | Inscrições dos navegadores para notificações. |
| review_events | Eventos das etapas de revisão. |
| review_items | Revisões com data, etapa e situação. |
| roadmap_version_topics | Ordem e incidência dos tópicos por versão. |
| roadmap_versions | Versões da trilha e referências de provas. |
| saved_filter_sets | Filtros de questões salvos. |
| streak_records | Sequências de dias de estudo. |
| testimonials | Depoimentos, consentimento e publicação. |
| topic_progressions | Progressão por aluno e tópico. |
| user_notices | Avisos para os alunos. |
| user_topic_levels | Dificuldade liberada por aluno e tópico. |
| weekly_reports | Relatórios semanais em JSON. |

## Principais relacionamentos

- Um usuário pode ter várias tentativas, anotações, metas e sessões de estudo.
- Um tópico pode ter várias questões e anotações.
- Uma questão pode ter várias alternativas e tentativas.
- Uma disciplina pode estar ligada a vários blocos e sessões de estudo.
- Um ciclo de revisão liga um usuário a uma questão e pode ter vários eventos.

Há no máximo um registro de `user_topic_progress` para cada combinação de aluno e tópico. As colunas `subject` de `topics` e `questions` são textos, sem chave estrangeira para `subjects`. Os blocos e as sessões usam `subject_id` para fazer essa ligação.
