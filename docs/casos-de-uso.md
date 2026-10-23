# Casos de uso simplificados

Um caso de uso descreve como uma pessoa usa o sistema para realizar uma tarefa. Este documento apresenta os principais usos do ProENEM Lab, com passos simples e o resultado esperado.

## Quem usa o sistema?

- **Aluno:** pessoa que usa a plataforma para estudar para o ENEM.
- **Responsável pela importação:** integrante do grupo que executa a importação das provas. Esse papel não representa uma conta de administrador ou uma tela administrativa.

Para os casos de estudo abaixo, o aluno precisa estar cadastrado e conectado à sua conta. A busca e a resolução de questões também dependem de haver questões no banco.

## UC01 — Criar uma conta

**Quem participa:** aluno que ainda não tem conta.

1. O aluno abre a página de cadastro.
2. Informa nome, e-mail e senha.
3. O sistema verifica os dados e cria a conta.

**Resultado:** o aluno pode usar os dados cadastrados para entrar na plataforma.

**Se houver um problema:** dados inválidos ou um e-mail já cadastrado impedem o cadastro e geram uma mensagem de erro.

## UC02 — Entrar na plataforma

**Quem participa:** aluno com conta cadastrada.

1. O aluno abre a página de login.
2. Informa e-mail e senha.
3. O sistema verifica os dados e libera o acesso.

**Resultado:** o aluno acessa suas informações e ferramentas de estudo.

**Se houver um problema:** se os dados estiverem incorretos, o sistema informa o erro e o aluno pode tentar novamente.

## UC03 — Buscar e responder questões

**Quem participa:** aluno.

1. O aluno abre a página de questões.
2. Escolhe filtros, como ano, matéria, tópico, idioma ou dificuldade.
3. O sistema apresenta as questões encontradas.
4. O aluno abre uma questão, lê o enunciado e escolhe uma alternativa.
5. Envia a resposta e recebe a correção.

**Resultado:** o sistema registra a tentativa e informa se o aluno acertou ou errou.

**Se houver um problema:** se nenhuma questão atender aos filtros, o aluno pode alterar a busca.

## UC04 — Revisar questões erradas

**Quem participa:** aluno com revisões disponíveis.

1. O aluno abre a página de revisões.
2. Consulta as revisões disponíveis para o dia e inicia uma sessão.
3. Responde novamente às questões apresentadas.
4. O sistema mostra a correção e atualiza os registros de revisão.

**Resultado:** o aluno pratica conteúdos em que teve dificuldade.

**Se não houver revisões:** o aluno pode continuar praticando na página de questões.

## UC05 — Acompanhar a trilha e fazer anotações

**Quem participa:** aluno.

1. O aluno consulta a trilha de tópicos de estudo.
2. Escolhe um tópico e acompanha seu andamento.
3. Registra uma anotação sobre o conteúdo.
4. Pode consultar, editar ou excluir suas anotações depois.

**Resultado:** o aluno mantém seus conteúdos e anotações organizados por tópico.

## UC06 — Organizar o calendário de estudos

**Quem participa:** aluno.

1. O aluno abre o calendário e escolhe a semana.
2. Adiciona um bloco de estudo com matéria e horário.
3. O sistema salva o bloco e o apresenta no calendário.
4. O aluno pode alterar ou excluir o bloco quando precisar.

**Resultado:** a programação de estudos fica salva para consulta.

## UC07 — Estudar com o Pomodoro

**Quem participa:** aluno.

1. O aluno configura os períodos de foco e descanso.
2. Inicia uma sessão de estudo.
3. Acompanha o tempo e faz as pausas entre os períodos de foco.
4. Finaliza a sessão ao terminar de estudar.

**Resultado:** o sistema registra a sessão para acompanhar o tempo de estudo.

## UC08 — Criar e concluir metas

**Quem participa:** aluno.

1. O aluno cria uma meta e informa a data desejada.
2. O sistema salva a meta.
3. Depois de realizar a atividade, o aluno marca a meta como concluída.

**Resultado:** o aluno acompanha as atividades que planejou e as que já concluiu.

O aluno também pode consultar seus pontos e a contagem de dias seguidos de estudo para acompanhar sua participação.

## UC09 — Consultar o desempenho e exportar um relatório

**Quem participa:** aluno com atividades registradas.

1. O aluno acessa as estatísticas ou os relatórios.
2. O sistema apresenta informações sobre as respostas e os estudos registrados.
3. O aluno consulta os resultados para identificar o que precisa praticar.
4. Se desejar, solicita a exportação do relatório de estudo em PDF.

**Resultado:** o aluno acompanha seu desempenho e pode guardar um relatório em arquivo.

## UC10 — Configurar notificações

**Quem participa:** aluno.

1. O aluno abre a página de notificações.
2. Escolhe suas preferências de lembretes e canais disponíveis.
3. Salva as configurações.

**Resultado:** as preferências ficam registradas para orientar os lembretes.

**Limitação atual:** o envio por e-mail ou pelo navegador depende de configuração do projeto. As notificações do navegador também precisam de permissão do aluno. O agendamento automático vem desativado por padrão.

## UC11 — Recuperar a senha (simulação)

**Quem participa:** aluno que esqueceu a senha, com apoio de quem executa o projeto.

1. O aluno acessa a opção de recuperação de senha e informa seu e-mail.
2. Se a conta existir, o sistema gera um código de recuperação (token), exibido no terminal do servidor.
3. Em uma demonstração local, o responsável consulta esse código para permitir testar a redefinição.
4. O aluno informa o código e uma nova senha na página de redefinição.

**Resultado:** com um código válido, a senha é atualizada e o aluno pode entrar novamente.

**Limitação atual:** o sistema ainda não envia o código por e-mail. Esse fluxo serve para demonstração local.

## UC12 — Importar questões do ENEM

**Quem participa:** responsável pela importação. A enem-api fornece as questões.

**Antes de começar:** o ambiente do projeto precisa estar preparado e conectado à internet.

1. O responsável escolhe o ano da prova.
2. Executa o comando de importação descrito no README.
3. O sistema busca as questões na enem-api e as salva no banco local.

**Resultado:** as questões importadas ficam disponíveis para os alunos buscarem e responderem.

**Se houver um problema:** se a conexão ou a fonte de questões estiver indisponível, o responsável verifica o erro e tenta novamente depois.

## Fora do escopo atual

Os planos Pro e Elite são propostas futuras. A contratação de assinaturas e os pagamentos não fazem parte dos casos de uso atuais.
