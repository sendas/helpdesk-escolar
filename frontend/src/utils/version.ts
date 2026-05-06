export const APP_VERSION = '1.7.13'
export const APP_VERSION_DATE = '2026-05-06'

export const RELEASE_NOTES = [
  {
    version: '1.7.13',
    date: '2026-05-06',
    title: 'Pré-visualização de imagens e PDFs nos tickets',
    changes: [
      'Imagens anexadas aparecem como miniaturas diretamente no ticket — clicar abre a imagem em popup a ecrã inteiro.',
      'PDFs e outros ficheiros abrem num novo separador do browser ao clicar.',
      'As miniaturas são carregadas automaticamente quando o ticket é aberto.',
    ],
  },
  {
    version: '1.7.12',
    date: '2026-05-06',
    title: 'Correções de upload e download de anexos',
    changes: [
      'O backend passa a aceitar qualquer formato de imagem (incluindo HEIC e WebP de dispositivos iOS/Android) além de PDF.',
      'A opção de anexar ficheiro no formulário de novo ticket passa a abrir a galeria completa do dispositivo móvel.',
      'Se um anexo falhar no upload, o ticket é criado na mesma e o utilizador é avisado do ficheiro que falhou.',
      'O download de anexos ficou mais fiável: o link temporário permanece válido durante 10 segundos para compatibilidade com todos os browsers.',
    ],
  },
  {
    version: '1.7.11',
    date: '2026-05-06',
    title: 'Correções de anexos, mobile e branding do login',
    changes: [
      'Clicar num anexo já não devolve "Not authenticated" — o download é agora feito com o token de sessão.',
      'O botão "Submeter ticket" deixou de ficar bloqueado após escolher um ficheiro da galeria no telemóvel.',
      'A opção de receber atualizações por email fica ativa por defeito ao criar um ticket.',
      'Ficheiros da galeria iOS (HEIC e outros formatos móveis) passam a ser aceites como anexos.',
      'Página de login: título alterado para "Centro de Apoio Digital do Agrupamento".',
      'Painel lateral do login mostra agora o nome do agrupamento e o endereço www.queiroz.pt de forma destacada.',
      'Cada funcionalidade destacada no login tem agora uma cor e ícone distintos.',
      'Pesquisa de pessoas em conhecimento no detalhe do ticket passa a filtrar por endereço de email.',
    ],
  },
  {
    version: '1.7.10',
    date: '2026-05-06',
    title: 'Diagnóstico das respostas por email',
    changes: [
      'Os emails enviados passam a definir explicitamente o Reply-To para a caixa configurada em MAIL_FROM.',
      'A sincronização IMAP passa a registar nos logs se encontrou emails não lidos, se ignorou mensagens sem marcador de ticket e se importou respostas com sucesso.',
      'Erros de ligação, autenticação ou seleção da pasta IMAP passam a ficar visíveis nos logs do backend.',
    ],
  },
  {
    version: '1.7.9',
    date: '2026-05-06',
    title: 'Respostas por email atualizam o ticket',
    changes: [
      'Quando a caixa IMAP de respostas está configurada, respostas a emails com o assunto [Ticket #ID] passam a ser importadas automaticamente como comentários públicos no ticket.',
      'Cada resposta recebida por email atualiza a data do ticket, cria um registo no histórico e evita duplicados através do Message-ID.',
      'Os restantes participantes do ticket são notificados quando chega uma nova resposta por email.',
    ],
  },
  {
    version: '1.7.8',
    date: '2026-05-06',
    title: 'Correção da pesquisa em conhecimento por utilizador',
    changes: [
      'No detalhe do ticket, o campo Em conhecimento passa a filtrar sugestões pelo nome, email, prefixo do email e nome de utilizador.',
      'Ao escrever diretamente um utilizador como pedropereira, o botão Adicionar passa a identificar esse utilizador quando a correspondência é exata ou única.',
    ],
  },
  {
    version: '1.7.7',
    date: '2026-05-06',
    title: 'Pesquisa por utilizador nas pessoas em conhecimento',
    changes: [
      'A gestão de membros dos grupos internos passa a permitir pesquisar utilizadores por nome, email ou nome de utilizador.',
      'Ao criar um novo ticket, o campo Dar conhecimento a mostra também o nome de utilizador nos resultados.',
      'Na página de detalhe do ticket, a secção Em conhecimento passa a aceitar seleção por nome, email ou nome de utilizador.',
    ],
  },
  {
    version: '1.7.6',
    date: '2026-05-06',
    title: 'Gestão de pessoas em conhecimento no ticket',
    changes: [
      'O autor do ticket e qualquer técnico ou administrador podem agora adicionar e remover pessoas em conhecimento diretamente na página de detalhe, sem ser necessário recriar o ticket.',
      'Campo de pesquisa por nome substitui a lista fixa: basta escrever parte do nome para filtrar os utilizadores disponíveis.',
      'Cada adição ou remoção fica registada no histórico do ticket com o nome da pessoa e quem fez a alteração.',
    ],
  },
  {
    version: '1.7.5',
    date: '2026-05-06',
    title: 'Correção do modo escuro no login',
    changes: [
      'Quando o modo escuro é ativado no ecrã de login, toda a área de entrada passa a usar fundo, cartões, bordas e texto escuros coerentes.',
      'Melhorado o contraste dos textos no login escuro para evitar letras cinzentas sobre fundo claro.',
    ],
  },
  {
    version: '1.7.4',
    date: '2026-05-06',
    title: 'Escolha de tema no login',
    changes: [
      'Página de login continua a abrir em modo claro por defeito.',
      'Adicionada opção visível Modo escuro com escolha Sim / Não no ecrã de entrada.',
      'A escolha de modo escuro no login deixa de prender o ecrã de entrada em escuro nas visitas seguintes.',
    ],
  },
  {
    version: '1.7.3',
    date: '2026-05-06',
    title: 'Criação de tickets e login claro',
    changes: [
      'Administradores podem atribuir logo um novo ticket a pessoas em conhecimento e a equipas internas.',
      'Ao escolher equipas internas na criação do ticket, os membros passam a acompanhar o pedido e recebem notificações.',
      'A sincronização Entra passa a correr automaticamente durante a noite por defeito.',
      'A página de login abre sempre em modo claro, independentemente da preferência usada dentro da aplicação.',
      'Ecrã de entrada mais compacto, com menos espaço vazio no topo e logotipo do agrupamento maior.',
      'Botão principal de entrada renomeado para email ou conta da escola e login local escondido numa opção secundária.',
      'Referências a Active Directory removidas da área visível do login.',
    ],
  },
  {
    version: '1.7.2',
    date: '2026-05-06',
    title: 'Categorias, técnicos ativos e tema',
    changes: [
      'Categorias padrão atualizadas para Inovar, Mail e Teams, Internet e Wi-Fi, Computadores, Impressoras, Projetores, Passwords e Outros.',
      'Cada categoria padrão recebe um ícone simples e uma cor distinta.',
      'A categoria genérica Apoio Técnico deixa de ser criada por defeito e é removida automaticamente quando não tem tickets associados.',
      'O campo Atribuído a passa a mostrar apenas técnicos ativos; administradores, direção e docentes deixam de aparecer como responsáveis diretos.',
      'Regras de encaminhamento automático só aceitam responsáveis que sejam técnicos ativos.',
      'Opção de manter o modo escuro no login tornada visível no ecrã de entrada e no topo da aplicação.',
    ],
  },
  {
    version: '1.7.1',
    date: '2026-05-06',
    title: 'Utilizadores manuais e emails institucionais',
    changes: [
      'Adição manual de utilizadores com nome, email, papel, departamento, estado e palavra-passe definida pelo administrador.',
      'Autenticação local para utilizadores que não existam no Entra ID.',
      'Sincronização Entra passa a preferir aliases institucionais @queiroz.pt em vez de endereços @onmicrosoft.com.',
      'Botões de cancelar e guardar da sincronização Entra colocados também no topo da janela.',
      'Página de entrada com instruções de login e aviso sobre modo escuro.',
      'Ao ativar modo escuro, a aplicação pergunta se deve manter esse modo no ecrã de login.',
      'Regra de manutenção: cada atualização enviada para GitHub deve acrescentar versão e alterações nesta página.',
    ],
  },
  {
    version: '1.7.0',
    date: '2026-05-05',
    title: 'Participantes, notificações e sincronização Entra',
    changes: [
      'Opção para dar conhecimento a pessoas ao criar um ticket.',
      'Participantes podem acompanhar, responder e anexar informação ao ticket.',
      'Opção explícita para o autor receber ou não atualizações por email.',
      'Sincronização Entra com seleção de OUs e exclusão de alunos.',
      'Campo Departamento / OU editável na gestão de utilizadores.',
      'Página de versão e histórico de atualizações.',
    ],
  },
  {
    version: '1.6.0',
    date: '2026-05-05',
    title: 'Escalação e gestão em lote',
    changes: [
      'Escalação de tickets para fornecedor externo configurável.',
      'Ações em lote para arquivar ou apagar tickets selecionados.',
      'Modo demo escondido até ser solicitado no ecrã de login.',
    ],
  },
  {
    version: '1.5.0',
    date: '2026-05-04',
    title: 'Administração escolar',
    changes: [
      'Gestão de escolas, categorias e grupos internos.',
      'Sincronização de utilizadores com Microsoft Entra ID.',
      'Permissões por papel com bloqueio manual de administradores e técnicos.',
      'Configuração de logotipo e favicon do agrupamento.',
    ],
  },
]

export function versionLabel() {
  return `v${APP_VERSION} · ${APP_VERSION_DATE}`
}
