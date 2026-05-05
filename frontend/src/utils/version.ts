export const APP_VERSION = '1.7.0'
export const APP_VERSION_DATE = '2026-05-05'

export const RELEASE_NOTES = [
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
