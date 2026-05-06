export const APP_VERSION = '1.7.2'
export const APP_VERSION_DATE = '2026-05-06'

export const RELEASE_NOTES = [
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
