<template>
  <div class="hd-page">
    <div class="crumbs">
      <span>
        <router-link to="/tickets" style="color:var(--c-muted);text-decoration:none">Tickets</router-link>
        / <span>T-{{ ticket?.id }}</span>
      </span>
      <span v-if="ticket" class="crumb-actions">
        <button class="mark-unread" type="button" title="Volta a aparecer a negrito em Os meus tickets" @click="markUnread">
          <span class="material-icons">mark_email_unread</span> Marcar como não lido
        </button>
        <button v-if="auth.isAdmin" class="mark-unread danger" type="button" title="Apagar definitivamente este ticket" @click="deleteTicket">
          <span class="material-icons">delete</span> Apagar ticket
        </button>
      </span>
    </div>

    <div v-if="!ticket && loadError" class="load-error">
      <span class="material-icons">error_outline</span>
      <div>{{ loadError }}</div>
      <button class="hd-btn hd-btn-outline" type="button" @click="retryLoad">Tentar novamente</button>
    </div>
    <div v-else-if="!ticket" style="padding:80px;text-align:center;color:var(--c-muted)">A carregar...</div>

    <template v-else>
      <div class="ticket-header">
        <!-- Title row -->
        <div class="ticket-title-row">
          <h1 v-if="!editingContent" class="ticket-title">{{ ticket.title }}</h1>
          <input v-else class="hd-input" v-model="editTitle" style="font-size:18px;font-weight:600;width:100%" />
        </div>
        <!-- Badges + actions row -->
        <div class="ticket-badges-row">
          <template v-if="!editingContent">
            <button v-if="auth.isAdmin" class="hd-icon-btn" title="Editar assunto e descrição" @click="startEditContent">
              <span class="material-icons" style="font-size:18px">edit</span>
            </button>
            <!-- Force-send to support company (staff only) -->
            <button
              v-if="auth.isStaff && !isDeescalated"
              class="hd-btn hd-btn-outline"
              style="font-size:12px;padding:3px 10px"
              :disabled="escalating"
              @click="onEscalateTicket"
            >
              <span class="material-icons" style="font-size:13px">{{ isEscalated ? 'forward_to_inbox' : 'outgoing_mail' }}</span>
              {{ escalating ? '...' : (isEscalated ? 'Reenviar à empresa de apoio' : 'Enviar para empresa de apoio') }}
            </button>
            <span class="hd-status" :class="ticket.status">{{ statusLabel(ticket.status) }}</span>
            <PriorityBadge :priority="ticket.priority" />
            <span v-if="ticket.school" class="school-badge" :title="ticket.school.name">
              <span class="material-icons">school</span>
              {{ ticket.school.name }}
            </span>
            <span v-if="isEscalated && !isDeescalated" class="escalated-badge" title="Ticket reportado à empresa de apoio">
              <span class="material-icons" style="font-size:13px;vertical-align:middle">open_in_new</span>
              Empresa de apoio
            </span>
            <button
              v-if="isEscalated && !isDeescalated && auth.isStaff"
              class="hd-btn hd-btn-outline"
              style="font-size:12px;padding:3px 10px"
              :disabled="deescalating"
              title="Marcar como resolvido pela empresa de apoio"
              @click="onDeescalate"
            >
              <span class="material-icons" style="font-size:13px">check_circle</span>
              {{ deescalating ? '...' : 'Empresa de apoio resolveu' }}
            </button>
            <span v-if="isDeescalated" class="deescalated-badge">
              <span class="material-icons" style="font-size:13px;vertical-align:middle">check_circle</span>
              Resolvido pela empresa de apoio
            </span>
            <button
              v-if="isDeescalated && auth.isStaff"
              class="hd-btn hd-btn-outline"
              style="font-size:12px;padding:3px 10px"
              :disabled="escalating"
              title="Reverter — empresa de apoio ainda não resolveu"
              @click="onEscalateTicket"
            >
              <span class="material-icons" style="font-size:13px">undo</span>
              {{ escalating ? '...' : 'Reverter' }}
            </button>
          </template>
          <template v-else>
            <button class="hd-btn hd-btn-outline" @click="cancelEditContent">Cancelar</button>
            <button class="hd-btn hd-btn-primary" :disabled="savingContent" @click="saveContent">
              {{ savingContent ? 'A guardar...' : 'Guardar' }}
            </button>
          </template>
        </div>
        <div v-if="otherViewers.length" class="live-viewers" title="Pessoas com este ticket aberto agora">
          <span class="live-dot"></span>
          <span class="live-avatars">
            <span v-for="v in otherViewers" :key="v.id" class="live-avatar" :title="v.name">{{ shortName(v.name).split(' ').map(w => w[0]).join('').slice(0, 2) }}</span>
          </span>
          {{ otherViewers.length === 1 ? shortName(otherViewers[0].name) + ' também está a ver este ticket' : otherViewers.length + ' pessoas também estão a ver este ticket' }}
        </div>
        <div class="ticket-meta">
          Aberto por <strong class="meta-person"><PersonName :name="ticket.creator.display_name" /></strong> · {{ formatDate(ticket.created_at) }}
        </div>
      </div>

      <div class="ticket-detail-grid">
        <!-- Left: conversation -->
        <div>
          <!-- Description message -->
          <div class="hd-msg" style="margin-bottom:12px">
            <AvatarCircle :name="shortName(ticket.creator.display_name)" size="36" />
            <div class="hd-msg-body">
              <div class="hd-msg-header">
                <PersonName class="hd-msg-author" :name="ticket.creator.display_name" />
                <span class="hd-msg-time">{{ formatDate(ticket.created_at) }}</span>
              </div>
              <div v-if="!editingContent" class="hd-msg-bubble" v-html="renderText(ticket.description)"></div>
              <ReactionBar v-if="!editingContent" target-type="ticket" :target-id="ticket.id" :reactions="ticketReactions" @update="(r) => (ticketReactions = r)" />
              <textarea v-else class="hd-textarea" v-model="editDescription" rows="6" style="margin-top:4px"></textarea>
              <div v-if="contentError" style="color:#DC2626;font-size:12px;margin-top:6px">{{ contentError }}</div>
              <div v-if="ticketLevelAttachments.length" style="margin-top:10px">
                <!-- image thumbnails -->
                <div v-if="imageAttachments.length" style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:8px">
                  <button
                    v-for="a in imageAttachments"
                    :key="a.id"
                    type="button"
                    class="attach-thumb"
                    :title="a.original_name"
                    @click="openLightbox(a)"
                  >
                    <img v-if="attachBlobUrls[a.id]" :src="attachBlobUrls[a.id]" :alt="a.original_name" style="width:100%;height:100%;object-fit:cover" />
                    <span v-else class="material-icons" style="color:var(--c-muted);font-size:28px">image</span>
                  </button>
                </div>
                <!-- pdf / other files -->
                <div v-for="a in fileAttachments" :key="a.id" style="margin-bottom:4px">
                  <button
                    type="button"
                    class="hd-row"
                    style="gap:6px;color:var(--c-primary);font-size:12.5px;background:none;border:none;cursor:pointer;padding:0;text-align:left"
                    @click="openFile(a)"
                  >
                    <span class="material-icons" style="font-size:15px">picture_as_pdf</span>
                    {{ a.original_name }} · {{ formatSize(a.size) }}
                  </button>
                </div>
              </div>
            </div>
          </div>

          <!-- Comments (consecutive private messages between the same people are grouped in one block) -->
          <div v-for="b in commentBlocks" :key="b.key" :class="{ 'private-thread': b.others }">
          <div v-if="b.others" class="private-thread-head" title="Só as pessoas desta conversa a veem">
            <span class="material-icons">lock</span>
            <span>Conversa privada · {{ namesList(b.others, true) }}</span>
          </div>
          <div
            v-for="c in b.items"
            :key="c.id"
            class="hd-msg"
            :class="{ 'hd-msg-internal': c.is_internal, 'hd-msg-private': !!c.private_to }"
            style="margin-bottom:12px"
          >
            <AvatarCircle :name="shortName(c.author.display_name)" size="36" />
            <div class="hd-msg-body">
              <div class="hd-msg-header">
                <PersonName class="hd-msg-author" :name="c.author.display_name" />
                <span v-if="c.is_internal" class="hd-internal-tag">NOTA INTERNA</span>
                <span v-if="c.remind_at" class="reminder-tag" :class="{ sent: !!c.reminder_sent_at }" :title="c.reminder_sent_at ? 'Lembrete já enviado' : 'Vai receber um lembrete por email e notificação'">
                  <span class="material-icons">{{ c.reminder_sent_at ? 'notifications_off' : 'alarm' }}</span>
                  {{ c.reminder_sent_at ? 'Lembrete enviado' : 'Lembrete ' + formatReminder(c.remind_at) }}
                </span>
                <span class="hd-msg-time">{{ formatDate(c.created_at) }}</span>
                <button v-if="canEditComment(c)" class="msg-action" @click="startEditComment(c)">Editar</button>
                <button v-if="canEditComment(c)" class="msg-action danger" @click="onDeleteComment(c)">Apagar</button>
                <button
                  v-if="auth.isStaff && isEscalated && !c.is_internal && !c.private_to"
                  class="msg-action"
                  :disabled="sendingCommentId === c.id"
                  :title="'Reenviar esta resposta à empresa de apoio'"
                  @click="forwardCommentToProvider(c)"
                >
                  {{ sendingCommentId === c.id ? '...' : 'Enviar para empresa de apoio' }}
                </button>
              </div>
              <div v-if="editingCommentId === c.id" class="comment-edit-box">
                <textarea class="hd-textarea" v-model="editingCommentBody" rows="3"></textarea>
                <div class="hd-row" style="justify-content:flex-end;gap:8px;margin-top:8px">
                  <button class="hd-btn hd-btn-outline" @click="cancelEditComment">Cancelar</button>
                  <button class="hd-btn hd-btn-primary" @click="saveEditedComment(c)">Guardar</button>
                </div>
              </div>
              <div v-else class="hd-msg-bubble" v-html="renderText(c.body)"></div>
              <div v-if="attachmentsByComment[c.id]?.length" class="msg-files">
                <template v-for="a in attachmentsByComment[c.id]" :key="a.id">
                  <button v-if="isImage(a)" type="button" class="attach-thumb" :title="a.original_name" @click="openLightbox(a)">
                    <img v-if="attachBlobUrls[a.id]" :src="attachBlobUrls[a.id]" :alt="a.original_name" style="width:100%;height:100%;object-fit:cover" />
                    <span v-else class="material-icons" style="color:var(--c-muted);font-size:28px">image</span>
                  </button>
                  <button v-else type="button" class="msg-file" @click="openFile(a)">
                    <span class="material-icons">description</span>
                    {{ a.original_name }} · {{ formatSize(a.size) }}
                  </button>
                </template>
              </div>
              <ReactionBar v-if="editingCommentId !== c.id" target-type="comment" :target-id="c.id" :reactions="reactions[c.id] ?? []" @update="(r) => (reactions[c.id] = r)" />
            </div>
          </div>
          <!-- Answer this private conversation right here (goes to everyone in it) -->
          <div v-if="b.others && b.lastOfGroup && threadFiles[b.group]" class="reply-file-preview thread-file">
            <span class="material-icons" style="font-size:15px;color:var(--c-primary)">attach_file</span>
            <span style="font-size:12px;flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">{{ threadFiles[b.group]?.name }}</span>
            <button type="button" class="hd-icon-btn" style="padding:2px" title="Remover" @click="threadFiles[b.group] = null">
              <span class="material-icons" style="font-size:14px">close</span>
            </button>
          </div>
          <div v-if="b.others && b.lastOfGroup" class="thread-reply">
            <textarea
              v-model="threadDrafts[b.group]"
              class="hd-textarea"
              rows="1"
              :placeholder="`Responder em privado a ${namesList(b.others)}… (pode colar imagens)`"
              @input="autoGrow($event.target as HTMLTextAreaElement)"
              @paste="onPasteThreadImage($event, b.group)"
              @keydown.ctrl.enter.prevent="sendThreadReply(b)"
              @keydown.meta.enter.prevent="sendThreadReply(b)"
            ></textarea>
            <label class="hd-icon-btn thread-attach" title="Anexar imagem ou ficheiro (só as pessoas desta conversa o veem)">
              <span class="material-icons">attach_file</span>
              <input type="file" style="display:none" :accept="ATTACH_ACCEPT"
                     @change="threadFiles[b.group] = ($event.target as HTMLInputElement).files?.[0] ?? null; ($event.target as HTMLInputElement).value = ''" />
            </label>
            <button
              class="hd-btn hd-btn-primary thread-send"
              type="button"
              :disabled="(!threadDrafts[b.group]?.trim() && !threadFiles[b.group]) || threadSending === b.group"
              :title="'Enviar só para ' + namesList(b.others, true)"
              @click="sendThreadReply(b)"
            >
              <span class="material-icons">{{ threadSending === b.group ? 'hourglass_empty' : 'lock' }}</span>
              {{ threadSending === b.group ? 'A enviar…' : 'Enviar' }}
            </button>
          </div>
          </div>

          <!-- The requester rates the help once the ticket is finished -->
          <div v-if="canRate" id="avaliar" class="hd-card rate-card" :class="{ highlight: rateHighlight }">
            <div class="rate-title">{{ ticket.rating ? 'A sua avaliação' : 'Como correu o atendimento?' }}</div>
            <div class="rate-stars" role="radiogroup" aria-label="Avaliação de 1 a 5 estrelas">
              <button v-for="n in 5" :key="n" type="button" class="rate-star" :class="{ on: n <= (rateHover || rateStars) }"
                      role="radio" :aria-checked="rateStars === n" :aria-label="`${n} estrela${n > 1 ? 's' : ''}`"
                      @mouseenter="rateHover = n" @mouseleave="rateHover = 0" @click="rateStars = n">
                <span class="material-icons">{{ n <= (rateHover || rateStars) ? 'star' : 'star_border' }}</span>
              </button>
              <span class="rate-hint">{{ ['', 'Muito mau', 'Mau', 'Razoável', 'Bom', 'Excelente'][rateHover || rateStars] }}</span>
            </div>
            <textarea v-model="rateComment" class="hd-textarea" rows="2" placeholder="Comentário (opcional)"></textarea>
            <div class="rate-actions">
              <span v-if="rateSaved" class="rate-saved"><span class="material-icons">check_circle</span> Obrigado pela sua avaliação!</span>
              <button type="button" class="hd-btn hd-btn-primary" :disabled="!rateStars || rateSaving" @click="saveRating">
                {{ rateSaving ? 'A guardar…' : ticket.rating ? 'Atualizar avaliação' : 'Enviar avaliação' }}
              </button>
            </div>
          </div>

          <div v-if="!canReply && !privateOnly" class="hd-card read-only-note">
            <span class="material-icons">visibility</span>
            Está a consultar este ticket em modo de leitura — o seu papel permite ver todos os tickets, mas não responder nem alterá-los.
          </div>
          <!-- Reply box -->
          <div v-else class="hd-card" style="padding:20px">
            <div style="font-weight:600;font-size:14px;margin-bottom:12px">Responder</div>
            <div v-if="privateTargets.length" class="private-box" :class="{ off: !privateOn }">
              <div class="private-title">
                <div v-if="!privateOnly" class="hd-toggle-wrap" @click="togglePrivate" role="switch" tabindex="0" :aria-checked="!!(privateOn)" @keydown.enter.prevent="togglePrivate" @keydown.space.prevent="togglePrivate">
                  <div class="hd-toggle-track" :class="{ on: privateOn }">
                    <div class="hd-toggle-thumb"></div>
                  </div>
                </div>
                <span class="material-icons">lock</span>
                Mensagem privada
              </div>
              <template v-if="privateOn">
                <div class="private-people">
                  <span v-for="u in privateChosen" :key="u.id" class="private-chip">
                    {{ shortName(u.display_name) }}<small v-if="u.tag">{{ u.tag }}</small>
                    <button type="button" :title="'Retirar ' + shortName(u.display_name)" @click="removePrivateTarget(u.id)"><span class="material-icons">close</span></button>
                  </span>
                  <select v-if="privateAvailableGroups.length" class="hd-input private-select" value="" @change="addPrivateTarget($event.target as HTMLSelectElement)">
                    <option value="" disabled>{{ privateChosen.length ? '+ Adicionar pessoa' : 'Escolher destinatário…' }}</option>
                    <optgroup v-for="g in privateAvailableGroups" :key="g.label" :label="g.label">
                      <option v-for="u in g.people" :key="u.id" :value="u.id">{{ shortName(u.display_name) }}{{ u.tag ? ' (' + u.tag + ')' : '' }}</option>
                    </optgroup>
                  </select>
                </div>
                <div class="private-hint">
                  <template v-if="privateChosen.length">
                    Só {{ namesList(privateChosen, true) }} veem esta mensagem. Mais ninguém a vê — nem os outros técnicos, nem os administradores.
                  </template>
                  <template v-else>Escolha uma ou mais pessoas.</template>
                  <template v-if="privateOnly"> O seu papel permite responder apenas em privado.</template>
                </div>
              </template>
            </div>
            <div v-if="auth.isStaff && !privateOn" class="quick-replies">
              <button
                v-for="reply in quickReplies"
                :key="reply.label"
                class="quick-reply"
                :class="{ 'quick-reply-active': reply.status && replyStatus === reply.status }"
                type="button"
                :title="reply.status ? 'Também muda o estado para ' + statusLabel(reply.status) : ''"
                @click="newComment = reply.body; if (reply.status) replyStatus = reply.status"
              >
                {{ reply.label }}
              </button>
            </div>
            <textarea
              class="hd-textarea"
              ref="replyBox"
              v-model="newComment"
              rows="4"
              :placeholder="privateOn ? 'Escreva a mensagem privada...' : 'Escreva a sua resposta... (@ para mencionar alguém; pode colar imagens)'"
              @input="onReplyTyping(); onMentionInput()"
              @keydown="onMentionKey"
              @paste="onPasteImage"
              @blur="closeMentionsSoon"
            ></textarea>
            <div v-if="mentionOpen && mentionMatches.length" class="mention-menu" role="listbox">
              <button v-for="(u, i) in mentionMatches" :key="u.id" type="button" class="mention-item" :class="{ active: i === mentionIndex }"
                      role="option" :aria-selected="i === mentionIndex" @mousedown.prevent="pickMention(u)">
                <AvatarCircle :name="shortName(u.display_name)" size="22" />
                <span>{{ shortName(u.display_name) }}</span><small v-if="u.tag">{{ u.tag }}</small>
              </button>
            </div>
            <div v-if="typingNames.length" class="live-typing"><span class="live-dots"><i></i><i></i><i></i></span>{{ typingNames.join(', ') }} {{ typingNames.length > 1 ? 'estão' : 'está' }} a escrever…</div>
            <!-- Hidden file input -->
            <input
              ref="commentFileInput"
              type="file"
              style="display:none"
              :accept="ATTACH_ACCEPT"
              @change="commentFile = ($event.target as HTMLInputElement).files?.[0] ?? null"
            />
            <!-- Selected file preview -->
            <div v-if="commentFile" class="reply-file-preview">
              <span class="material-icons" style="font-size:15px;color:var(--c-primary)">attach_file</span>
              <span style="font-size:12px;flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">{{ commentFile.name }}</span>
              <button type="button" class="hd-icon-btn" style="padding:2px" title="Remover" @click="commentFile = null; if (commentFileInput) commentFileInput.value = ''">
                <span class="material-icons" style="font-size:14px">close</span>
              </button>
            </div>
            <div v-if="canRemind" class="reminder-box" :class="{ off: !reminderOn }">
              <div class="reminder-title">
                <div class="hd-toggle-wrap" @click="toggleReminder" role="switch" tabindex="0" :aria-checked="!!(reminderOn)" @keydown.enter.prevent="toggleReminder" @keydown.space.prevent="toggleReminder">
                  <div class="hd-toggle-track" :class="{ on: reminderOn }">
                    <div class="hd-toggle-thumb"></div>
                  </div>
                </div>
                <span class="material-icons">alarm</span>
                Lembrar-me deste ticket <span class="reminder-opt">(só para si)</span>
              </div>
              <div v-if="replyReminders.length" class="reminder-saved">
                <div v-for="r in replyReminders" :key="r.id" class="reminder-saved-item">
                  <span class="material-icons">alarm_on</span>
                  <span>Lembrete marcado para <strong>{{ reminderLabel(r.remind_at) }}</strong><template v-if="r.note"> — {{ r.note }}</template></span>
                  <button type="button" class="reminder-cancel" @click="cancelReminder(r.id)">Cancelar</button>
                </div>
              </div>
              <template v-if="reminderOn">
                <div class="reminder-row">
                  <input class="hd-input reminder-date" type="date" v-model="remindDate" :min="todayIso" />
                  <input class="hd-input reminder-time" type="time" v-model="remindTime" />
                  <button v-for="q in reminderQuick" :key="q.label" type="button" class="reminder-chip" @click="setReminderIn(q.days)">{{ q.label }}</button>
                </div>
                <div class="reminder-status" :class="reminderState">
                  <template v-if="reminderState === 'saving'"><span class="material-icons spin">sync</span> A guardar…</template>
                  <template v-else-if="reminderState === 'saved'"><span class="material-icons">check_circle</span> Guardado — recebe um email e uma notificação a {{ reminderPreview }}.</template>
                  <template v-else-if="reminderState === 'error'"><span class="material-icons">error</span> {{ reminderError }}</template>
                  <template v-else-if="!remindDate">Escolha o dia em que quer ser lembrado.</template>
                </div>
              </template>
            </div>
            <div class="hd-row" style="justify-content:space-between;margin-top:12px">
              <div class="hd-row" style="gap:8px">
                <label v-if="auth.isStaff && !privateOn" class="hd-row" style="gap:8px;cursor:pointer;font-size:13px;color:var(--c-muted)">
                  <div class="hd-toggle-wrap" @click="isInternal = !isInternal" role="switch" tabindex="0" :aria-checked="!!(isInternal)" @keydown.enter.prevent="isInternal = !isInternal" @keydown.space.prevent="isInternal = !isInternal">
                    <div class="hd-toggle-track" :class="{ on: isInternal }">
                      <div class="hd-toggle-thumb"></div>
                    </div>
                  </div>
                  Nota interna
                </label>
                <button
                  type="button"
                  class="hd-btn hd-btn-outline"
                  style="font-size:12px;padding:5px 10px"
                  :title="privateOn ? 'Anexar ficheiro (só os destinatários da mensagem privada o veem)' : isInternal ? 'Anexar ficheiro (só a equipa o vê)' : 'Anexar ficheiro'"
                  @click="commentFileInput?.click()"
                >
                  <span class="material-icons" style="font-size:15px">attach_file</span>
                  Anexar
                </button>
                <button v-if="isTouch" type="button" class="hd-btn hd-btn-outline" style="font-size:12px;padding:5px 10px" title="Tirar fotografia" @click="cameraInput?.click()">
                  <span class="material-icons" style="font-size:15px">photo_camera</span>
                  Foto
                </button>
                <input ref="cameraInput" type="file" accept="image/*" capture="environment" style="display:none"
                       @change="commentFile = ($event.target as HTMLInputElement).files?.[0] ?? null" />
              </div>
              <div class="hd-row send-group">
              <label v-if="auth.isStaff" class="reply-status" :class="{ changed: !!replyStatus }" :title="'Estado atual: ' + statusLabel(ticket.status) + '. Pode alterá-lo ao enviar a resposta.'">
                <span class="material-icons">sync_alt</span>
                <select v-model="replyStatus">
                  <option value="">Manter estado</option>
                  <option v-for="o in statusOpts.filter(o => o.v !== ticket.status)" :key="o.v" :value="o.v">{{ o.l }}</option>
                </select>
              </label>
              <button
                class="hd-btn hd-btn-primary"
                :disabled="(!newComment.trim() && !commentFile) || commenting"
                @click="onAddComment"
              >
                <span class="material-icons" style="font-size:16px">send</span>
                {{ commenting ? 'A enviar...' : sendLabel }}
              </button>
              </div>
            </div>
            <div v-if="commentError" style="color:#DC2626;font-size:13px;margin-top:8px">{{ commentError }}</div>
          </div>
        </div>

        <!-- Right: details + timeline -->
        <div class="ticket-side-panel">
          <!-- Details card -->
          <div class="hd-card" style="padding:20px">
            <div style="font-weight:600;font-size:14px;margin-bottom:16px">Detalhes</div>

            <div class="hd-detail-row">
              <div class="hd-detail-label">Solicitante</div>
              <div class="hd-row" style="gap:6px">
                <AvatarCircle :name="shortName(ticket.creator.display_name)" size="22" />
                <PersonName style="font-size:13px" :name="ticket.creator.display_name" />
              </div>
            </div>

            <div v-if="canManageEmailNotifications" class="email-notification-panel">
              <div>
                <strong>Atualizações por email</strong>
                <span>{{ ticket.creator_email_notifications ? 'Ativas para o autor' : 'Desativadas para o autor' }}</span>
              </div>
              <button
                class="email-toggle-btn"
                :class="{ active: ticket.creator_email_notifications }"
                :disabled="savingEmailPreference"
                @click="toggleEmailNotifications"
              >
                <span class="material-icons">{{ ticket.creator_email_notifications ? 'notifications_active' : 'notifications_off' }}</span>
                {{ ticket.creator_email_notifications ? 'Desativar emails' : 'Ativar emails' }}
              </button>
            </div>

            <div class="hd-detail-row" style="flex-direction:column;align-items:flex-start;gap:8px">
              <div class="hd-detail-label">Em conhecimento</div>
              <div v-if="ticket.watchers?.length" class="watcher-list" style="width:100%">
                <div v-for="user in ticket.watchers" :key="user.id" class="watcher-mini">
                  <AvatarCircle :name="shortName(user.display_name)" size="22" />
                  <PersonName :name="user.display_name" />
                  <button
                    v-if="canEditWatchers"
                    class="watcher-remove-btn"
                    @click="onRemoveWatcher(user.id)"
                    title="Remover"
                  >
                    <span class="material-icons" style="font-size:14px">close</span>
                  </button>
                </div>
              </div>
              <span v-else style="font-size:13px;color:var(--c-muted)">Nenhuma pessoa adicionada.</span>
              <div v-if="canEditWatchers" class="watcher-add-row">
                <div class="person-search">
                  <input
                    class="hd-input"
                    v-model="watcherSearch"
                    placeholder="Pesquisar por nome ou email..."
                    autocomplete="off"
                  />
                  <div v-if="watcherSearch.trim().length >= 2 && (watcherLoading || filteredWatcherUsers.length)" class="person-search-menu">
                    <div v-if="watcherLoading" class="person-search-empty">A pesquisar...</div>
                    <button v-for="u in filteredWatcherUsers" :key="u.id" type="button" @mousedown.prevent="addWatcherCandidate(u)">
                      <AvatarCircle :name="shortName(u.display_name)" size="22" />
                      <span>
                        <strong class="pn-block"><PersonName :name="u.display_name" /></strong>
                        <small>{{ u.email }}</small>
                      </span>
                    </button>
                  </div>
                </div>
                <button
                  class="hd-btn hd-btn-primary"
                  style="padding:5px 12px;font-size:12px;white-space:nowrap"
                  :disabled="!resolvedWatcherId || addingWatcher"
                  @click="onAddWatcher"
                >
                  Adicionar
                </button>
              </div>
            </div>

            <div class="hd-detail-row">
              <div class="hd-detail-label">Atribuído a</div>
              <div v-if="auth.isStaff" class="assignee-editor">
                <div v-if="assignedTechnicians.length" class="assignee-chip-list">
                  <span v-for="user in assignedTechnicians" :key="user.id" class="assignee-chip">
                    <AvatarCircle :name="shortName(user.display_name)" size="20" />
                    <PersonName :name="user.display_name" />
                    <button type="button" title="Remover técnico" @click="removeAssignee(user.id)">
                      <span class="material-icons">close</span>
                    </button>
                  </span>
                </div>
                <span v-else class="muted-mini">— Nenhum técnico atribuído</span>
                <div class="person-search">
                  <input
                    class="hd-input"
                    v-model="assigneeSearch"
                    placeholder="Adicionar técnico..."
                    autocomplete="off"
                    @focus="assigneeSearchOpen = true"
                    @click="assigneeSearchOpen = true"
                    @keydown.escape="assigneeSearchOpen = false"
                  />
                  <div v-if="assigneeSearchOpen && filteredAssigneeUsers.length" class="person-search-menu">
                    <button v-for="u in filteredAssigneeUsers" :key="u.id" type="button" @mousedown.prevent="addAssignee(u)">
                      <AvatarCircle :name="shortName(u.display_name)" size="22" />
                      <span>
                        <strong class="pn-block"><PersonName :name="u.display_name" /></strong>
                        <small>{{ u.email }}</small>
                      </span>
                    </button>
                  </div>
                </div>
              </div>
              <div v-else style="font-size:13px">
                {{ assignedTechnicianNames || '—' }}
              </div>
            </div>

            <div class="hd-detail-row">
              <div class="hd-detail-label">Grupo</div>
              <div v-if="auth.isStaff">
                <select class="hd-select" style="font-size:12px;padding:4px 8px" v-model="groupId" @change="onGroupChange">
                  <option :value="''">— Sem grupo</option>
                  <option v-for="g in groups" :key="g.id" :value="String(g.id)">{{ g.name }}</option>
                </select>
              </div>
              <div v-else style="font-size:13px">{{ ticket.group?.name || '—' }}</div>
            </div>

            <div class="hd-detail-row">
              <div class="hd-detail-label">Estado</div>
              <div v-if="auth.isStaff">
                <select class="hd-select" style="font-size:12px;padding:4px 8px" v-model="ticketStatus" @change="onStatusChange">
                  <option v-for="o in statusOpts" :key="o.v" :value="o.v">{{ o.l }}</option>
                </select>
              </div>
              <span v-else class="hd-status" :class="ticket.status">{{ statusLabel(ticket.status) }}</span>
            </div>

            <div class="hd-detail-row">
              <div class="hd-detail-label">Prioridade</div>
              <PriorityBadge :priority="ticket.priority" />
            </div>

            <div class="hd-detail-row">
              <div class="hd-detail-label">Categoria</div>
              <div class="hd-row" style="gap:6px">
                <span class="material-icons" :style="{ color: ticket.category.color, fontSize: '14px' }">{{ ticket.category.icon }}</span>
                <span style="font-size:13px">{{ ticket.category.name }}</span>
              </div>
            </div>

            <div v-if="ticket.school" class="hd-detail-row">
              <div class="hd-detail-label">Escola</div>
              <span style="font-size:13px">{{ ticket.school.name }}</span>
            </div>

            <div class="hd-detail-row">
              <div class="hd-detail-label">Aberto</div>
              <span style="font-size:13px">{{ formatDate(ticket.created_at) }}</span>
            </div>

            <div class="hd-detail-row" :style="ticket.rating && !canRate ? '' : 'border-bottom:none'">
              <div class="hd-detail-label">Tempo de resposta</div>
              <span style="font-size:13px">{{ ticket.category.sla_hours }}h</span>
            </div>
            <div v-if="ticket.rating && !canRate" class="hd-detail-row rating-row" style="border-bottom:none" :title="ticket.rating.comment || ''">
              <div class="hd-detail-label">Avaliação</div>
              <span class="rating-stars">{{ '★'.repeat(ticket.rating.stars) }}<span class="rating-off">{{ '★'.repeat(5 - ticket.rating.stars) }}</span></span>
            </div>
            <div v-if="ticket.rating?.comment && !canRate" class="rating-comment">“{{ ticket.rating.comment }}”</div>

            <div v-if="auth.isStaff && escalationMessage" class="provider-escalation">
              <p :class="{ error: escalationError }">{{ escalationMessage }}</p>
            </div>
          </div>

          <!-- Timeline -->
          <div class="hd-card" style="padding:20px">
            <div style="font-weight:600;font-size:14px;margin-bottom:16px">Histórico</div>
            <div v-if="ticket.events?.length" class="event-list">
              <div v-for="event in ticket.events" :key="event.id" class="event-item">
                <div class="event-dot"></div>
                <div>
                  <div class="event-message">{{ event.message }}</div>
                  <div class="event-meta">
                    {{ formatDate(event.created_at) }}
                    <span v-if="event.actor"> · {{ shortName(event.actor.display_name) }}</span>
                  </div>
                </div>
              </div>
            </div>
            <div class="hd-timeline">
              <div v-for="(step, idx) in timeline" :key="step.status" class="hd-tl-item">
                <div class="hd-tl-spine">
                  <div class="hd-tl-dot" :class="{ done: isStatusDone(step.status), active: ticket.status === step.status }"></div>
                  <div v-if="idx < timeline.length - 1" class="hd-tl-line"></div>
                </div>
                <div class="hd-tl-label" :class="{ done: isStatusDone(step.status) }">{{ step.label }}</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </template>
  </div>

  <!-- Lightbox -->
  <Teleport to="body">
    <div v-if="lightboxSrc" class="hd-lightbox" @click="lightboxSrc = null">
      <button class="hd-lightbox-close" @click="lightboxSrc = null">
        <span class="material-icons">close</span>
      </button>
      <img :src="lightboxSrc" class="hd-lightbox-img" @click.stop />
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { statusLabel as labelFor } from '../utils/ticketStatus'
import { computed, nextTick, ref, onMounted, onUnmounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getTicket, markTicketUnread, adminBulkActionTickets, getMyReminders, setMyReminder, clearMyReminder, deleteReminder, addComment, adminUpdateTicket, updateTicket, updateComment, deleteComment, escalateTicket, deescalateTicket, escalateComment, addWatcher, removeWatcher, downloadAttachment, fetchAttachmentBlob, uploadTicketAttachment } from '../api/tickets'
import { getGroups, getUsers, searchUsers } from '../api/users'
import { useAuthStore } from '../stores/auth'
import AvatarCircle from '../components/AvatarCircle.vue'
import PriorityBadge from '../components/PriorityBadge.vue'
import { formatDateTime } from '../utils/dates'
import { shortName } from '../utils/names'
import { forgetSticky, onRealtime, sendRealtime } from '../services/realtime'
import ReactionBar from '../components/ReactionBar.vue'
import { getReactions, type ReactionSummary } from '../api/reactions'
import PersonName from '../components/PersonName.vue'
import { api } from '../boot/axios'
import { confirmDialog, errorMessage, notifyError } from '../utils/feedback'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()
const ticket = ref<any>(null)
const newComment = ref('')
const isInternal = ref(false)
const reminderOn = ref(false)
const remindDate = ref('')
const remindTime = ref('09:00')
const todayIso = computed(() => toIsoDate(new Date()))
const canRemind = computed(() => {
  const me = auth.user?.id
  const t: any = ticket.value
  if (!me || !t) return false
  return auth.isStaff || t.assignee?.id === me || (t.assignees ?? []).some((a: any) => a.id === me)
})

// Private messages: to one or more people (someone in the ticket, a technician/admin or the Direção), or back to
// everyone in a private conversation with me
const privateOn = ref(false)
const privateToIds = ref<number[]>([])
function privatePeople(c: any): any[] {
  const list = [c.author, ...(c.private_recipients?.length ? c.private_recipients : c.private_to ? [c.private_to] : [])]
  const seen = new Set<number>()
  return list.filter((u: any) => u && !seen.has(u.id) && seen.add(u.id))
}
// Each private conversation (same people) is ONE box with all its messages in order, shown where its latest
// message is; public replies and notes stay in the normal flow around it
const commentBlocks = computed(() => {
  const me = auth.user?.id
  // In "Ver como docente" internal notes are hidden, as the server does for docentes
  const all = (ticket.value?.comments ?? []).filter((x: any) => !(auth.inPreview && x.is_internal)) as any[]
  const groups = new Map<string, { others: any[]; items: any[] }>()
  const groupOf = new Map<number, string>()
  for (const c of all) {
    if (!c.private_to) continue
    const others = privatePeople(c).filter((u: any) => u.id !== me)
      .sort((a: any, b: any) => String(a.display_name).localeCompare(String(b.display_name), 'pt'))
    const key = others.map((u: any) => u.id).sort((a: number, b: number) => a - b).join(',')
    if (!groups.has(key)) groups.set(key, { others, items: [] })
    groups.get(key)!.items.push(c)
    groupOf.set(c.id, key)
  }
  const blocks: { key: string; others: any[] | null; group: string; items: any[]; lastOfGroup?: boolean }[] = []
  for (const c of all) {
    const key = groupOf.get(c.id)
    if (key === undefined) {
      blocks.push({ key: `c${c.id}`, others: null, group: '', items: [c] })
      continue
    }
    const g = groups.get(key)!
    if (g.items[g.items.length - 1].id === c.id) {
      blocks.push({ key: `p${key}`, others: g.others, group: key, items: g.items, lastOfGroup: true })
    }
  }
  return blocks
})
// "Rui Técnico, Diana Diretora e você"
function namesList(people: any[], withMe = false) {
  const names = [...people.map((u: any) => shortName(u.display_name)), ...(withMe ? ['você'] : [])]
  return names.length > 1 ? `${names.slice(0, -1).join(', ')} e ${names[names.length - 1]}` : names[0] ?? ''
}
// Supervisors (tickets.view_all without tickets.manage) can open any ticket but only reply to their own
const canReply = computed(() => {
  const me = auth.user?.id
  const t: any = ticket.value
  if (!me || !t) return false
  return auth.isStaff || t.creator?.id === me || t.assignee?.id === me
    || [...(t.assignees ?? []), ...(t.watchers ?? [])].some((u: any) => u.id === me)
})
const staffPeople = ref<any[]>([])
// The Direção (sees every ticket without managing them) writes in private only
const isSupervisor = computed(() => auth.can('tickets.view_all') && !auth.isStaff)
const canWritePrivate = computed(() => {
  const me = auth.user?.id
  const t: any = ticket.value
  if (!me || !t) return false
  return auth.isStaff || isSupervisor.value || t.assignee?.id === me || (t.assignees ?? []).some((a: any) => a.id === me)
})
const privateOnly = computed(() => !canReply.value && canWritePrivate.value)
watch(privateOnly, (v) => { if (v) privateOn.value = true }, { immediate: true })
function isStaffUser(u: any) {
  return u.role === 'admin' || u.role === 'technician' || u.is_technician
}
// Grouped recipients: people in this ticket first, then the Direção and every technician/admin
const privateGroups = computed(() => {
  const me = auth.user?.id
  const t: any = ticket.value
  if (!me || !t) return []
  const inTicket = new Map<number, any>()
  const add = (u: any, tag: string) => { if (u && u.id !== me && !inTicket.has(u.id)) inTicket.set(u.id, { ...u, tag }) }
  if (canWritePrivate.value) {
    ;[...(t.assignees ?? []), ...(t.assignee ? [t.assignee] : [])].forEach((u: any) => add(u, 'responsável'))
    add(t.creator, 'solicitante')
    ;(t.watchers ?? []).forEach((u: any) => add(u, 'seguidor'))
  }
  ;(t.comments ?? []).forEach((c: any) => {
    if (c.private_to && privatePeople(c).some((u: any) => u.id === me)) privatePeople(c).forEach((u: any) => add(u, 'conversa privada'))
  })
  const groups = [{ label: 'Neste ticket', people: [...inTicket.values()] }]
  if (canWritePrivate.value) {
    const rest = staffPeople.value.filter((u: any) => u.id !== me && !inTicket.has(u.id))
    groups.push({ label: 'Direção', people: rest.filter((u: any) => !isStaffUser(u)).map((u: any) => ({ ...u, tag: u.role_label || 'Direção' })) })
    groups.push({ label: 'Técnicos e administradores', people: rest.filter(isStaffUser)
      .map((u: any) => ({ ...u, tag: u.role_label || (u.role === 'admin' ? 'Administrador' : 'Técnico') })) })
  }
  return groups.filter((g) => g.people.length)
})
const privateTargets = computed(() => privateGroups.value.flatMap((g) => g.people))
const privateChosen = computed(() => privateToIds.value.map((id) => privateTargets.value.find((u: any) => u.id === id)).filter(Boolean) as any[])
const privateAvailableGroups = computed(() => privateGroups.value
  .map((g) => ({ ...g, people: g.people.filter((u: any) => !privateToIds.value.includes(u.id)) }))
  .filter((g) => g.people.length))
function addPrivateTarget(select: HTMLSelectElement) {
  const id = Number(select.value)
  if (id && !privateToIds.value.includes(id)) privateToIds.value = [...privateToIds.value, id]
  select.value = ''
}
function removePrivateTarget(id: number) {
  privateToIds.value = privateToIds.value.filter((x) => x !== id)
}
async function loadStaffPeople() {
  if (staffPeople.value.length || !canWritePrivate.value) return
  try { staffPeople.value = await searchUsers('', { private_targets: true, limit: 100 }) } catch { staffPeople.value = [] }
}
watch(canWritePrivate, (v) => { if (v) loadStaffPeople() }, { immediate: true })
function togglePrivate() {
  privateOn.value = !privateOn.value
  if (privateOn.value) {
    isInternal.value = false
    privateToIds.value = privateToIds.value.filter((id) => privateTargets.value.some((u: any) => u.id === id))
  }
}
// Quick replies inside a private conversation block, one draft per conversation
const threadDrafts = ref<Record<string, string>>({})
const threadFiles = ref<Record<string, File | null>>({})
const threadSending = ref('')
const ATTACH_ACCEPT = '.png,.jpg,.jpeg,.gif,.webp,.heic,.pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.odt,.ods,.txt,.csv,.zip'
function onPasteThreadImage(e: ClipboardEvent, group: string) {
  const file = pastedImage(e)
  if (file) threadFiles.value[group] = file
}
function autoGrow(el: HTMLTextAreaElement) {
  el.style.height = 'auto'
  el.style.height = Math.min(el.scrollHeight, 220) + 'px'
}
async function sendThreadReply(b: { group: string; others: any[] | null }) {
  const text = (threadDrafts.value[b.group] ?? '').trim()
  const file = threadFiles.value[b.group] ?? null
  if ((!text && !file) || !b.others || threadSending.value || !ticket.value) return
  threadSending.value = b.group
  try {
    const c = await addComment(ticket.value.id, text || '📎 Ficheiro anexado.', false, null, b.others.map((u: any) => u.id))
    threadDrafts.value[b.group] = ''
    if (file) {
      threadFiles.value[b.group] = null
      await uploadTicketAttachment(ticket.value.id, file, c.id)
    }
    await load({ live: true })
    loadReactions()
  } catch (e) {
    notifyError(e, 'Não foi possível enviar a mensagem privada.')
  } finally {
    threadSending.value = ''
  }
}


// Reminders saved on their own (without writing a reply)
const myReminders = ref<{ id: string; remind_at: string; note: string | null; source: string }[]>([])
const reminderError = ref('')

async function loadReminders() {
  if (!ticket.value || !canRemind.value) return
  try { myReminders.value = await getMyReminders(ticket.value.id) } catch { myReminders.value = [] }
  applySavedReminder()
}

function reminderLabel(iso: string) {
  const d = new Date(iso)
  return d.toLocaleDateString('pt-PT', { weekday: 'long', day: 'numeric', month: 'long' }) + ' às ' + d.toLocaleTimeString('pt-PT', { hour: '2-digit', minute: '2-digit' })
}

// "Lembrar-me deste ticket" saves by itself: switching on, changing the day/time, switching off
const reminderState = ref<'' | 'saving' | 'saved' | 'error'>('')
const mineReminder = computed(() => myReminders.value.find((r) => r.source === 'lembrete'))
const replyReminders = computed(() => myReminders.value.filter((r) => r.source !== 'lembrete'))
let reminderTimer: ReturnType<typeof setTimeout> | null = null
let applyingSaved = false

function applySavedReminder() {
  const r = mineReminder.value
  applyingSaved = true
  if (r) {
    const d = new Date(r.remind_at)
    reminderOn.value = true
    remindDate.value = toIsoDate(d)
    remindTime.value = d.toTimeString().slice(0, 5)
    reminderState.value = 'saved'
  } else {
    reminderOn.value = false
    reminderState.value = ''
  }
  setTimeout(() => { applyingSaved = false })
}

async function persistReminder() {
  if (!ticket.value) return
  try {
    if (!reminderOn.value) {
      if (mineReminder.value) myReminders.value = await clearMyReminder(ticket.value.id)
      reminderState.value = ''
      return
    }
    if (!remindDate.value) return
    reminderState.value = 'saving'
    const at = new Date(`${remindDate.value}T${remindTime.value || '09:00'}`).toISOString()
    myReminders.value = await setMyReminder(ticket.value.id, at)
    reminderState.value = 'saved'
  } catch (e: any) {
    reminderState.value = 'error'
    reminderError.value = errorMessage(e, 'Não foi possível guardar o lembrete.')
  }
}

watch([reminderOn, remindDate, remindTime], () => {
  if (applyingSaved) return
  if (reminderTimer) clearTimeout(reminderTimer)
  reminderTimer = setTimeout(persistReminder, reminderOn.value ? 500 : 0)
})

async function cancelReminder(id: string) {
  if (!ticket.value) return
  myReminders.value = await deleteReminder(ticket.value.id, id)
}

function toggleReminder() {
  reminderOn.value = !reminderOn.value
  if (reminderOn.value && !remindDate.value) setReminderIn(1)
  if (!reminderOn.value) remindDate.value = ''
}
const reminderQuick = [
  { label: 'Amanhã', days: 1 },
  { label: 'Daqui a 3 dias', days: 3 },
  { label: 'Próxima segunda', days: 7 },
]
const reminderPreview = computed(() => {
  if (!remindDate.value) return ''
  const d = new Date(`${remindDate.value}T${remindTime.value || '09:00'}`)
  return d.toLocaleDateString('pt-PT', { weekday: 'long', day: 'numeric', month: 'long' }) + ' às ' + (remindTime.value || '09:00')
})
const commenting = ref(false)
const commentError = ref('')
const staffUsers = ref<any[]>([])
const groups = ref<any[]>([])
const assigneeSearch = ref('')
const assigneeSearchOpen = ref(false)
const groupId = ref('')
const ticketStatus = ref('')
const editingCommentId = ref<number | null>(null)
const editingCommentBody = ref('')
const sendingCommentId = ref<number | null>(null)
const escalating = ref(false)
const escalationMessage = ref('')
const escalationError = ref(false)
const savingEmailPreference = ref(false)
const watcherSearch = ref('')
const watcherResults = ref<any[]>([])
const watcherLoading = ref(false)
const addingWatcher = ref(false)
let watcherSearchTimer: ReturnType<typeof setTimeout> | null = null
const attachBlobUrls = ref<Record<number, string>>({})
const lightboxSrc = ref<string | null>(null)
// Status to apply together with the reply ('' keeps the current one)
const replyStatus = ref('')
const commentFile = ref<File | null>(null)
const commentFileInput = ref<HTMLInputElement | null>(null)
const editingContent = ref(false)
const editTitle = ref('')
const editDescription = ref('')
const savingContent = ref(false)
const contentError = ref('')

const isImage = (a: any) => (a.content_type as string).startsWith('image/')
// Files of the ticket itself (shown with the description); files sent with a reply are shown under that reply
const ticketLevelAttachments = computed(() => (ticket.value?.attachments ?? []).filter((a: any) => !a.comment_id))
const imageAttachments = computed(() => ticketLevelAttachments.value.filter(isImage))
const fileAttachments = computed(() => ticketLevelAttachments.value.filter((a: any) => !isImage(a)))
const attachmentsByComment = computed(() => {
  const out: Record<number, any[]> = {}
  for (const a of ticket.value?.attachments ?? []) {
    if (a.comment_id) (out[a.comment_id] ??= []).push(a)
  }
  return out
})

const isEscalated = computed(() => !!ticket.value?.is_escalated)
const isDeescalated = computed(() => {
  const events: any[] = ticket.value?.events ?? []
  const hadEscalated = events.some((e: any) => e.event_type === 'escalated')
  return hadEscalated && !ticket.value?.is_escalated
})
const deescalating = ref(false)

const canManageEmailNotifications = computed(() => {
  if (!ticket.value || !auth.user) return false
  return auth.isAdmin || ticket.value.creator?.id === auth.user.id
})

const canEditWatchers = computed(() => {
  if (!ticket.value || !auth.user) return false
  return auth.isStaff || ticket.value.creator?.id === auth.user.id
})

const filteredWatcherUsers = computed(() => {
  const addedIds = new Set((ticket.value?.watchers ?? []).map((w: any) => w.id))
  return watcherResults.value.filter(u => !addedIds.has(u.id) && u.id !== ticket.value?.creator?.id).slice(0, 8)
})

const resolvedWatcherId = computed(() => {
  const term = watcherSearch.value.trim().toLowerCase()
  const exactMatch = filteredWatcherUsers.value.find(u =>
    String(u.email || '').toLowerCase() === term || String(u.username || '').toLowerCase() === term
  )
  if (exactMatch) return exactMatch.id
  if (filteredWatcherUsers.value.length === 1) return filteredWatcherUsers.value[0].id
  return null
})

const assignedTechnicians = computed(() => {
  const assignees = ticket.value?.assignees?.length ? ticket.value.assignees : (ticket.value?.assignee ? [ticket.value.assignee] : [])
  const seen = new Set<number>()
  return assignees.filter((user: any) => {
    if (!user?.id || seen.has(user.id)) return false
    seen.add(user.id)
    return true
  })
})

const assignedTechnicianNames = computed(() =>
  assignedTechnicians.value.map((user: any) => user.display_name).join(', ')
)

const filteredAssigneeUsers = computed(() => {
  const term = assigneeSearch.value.trim().toLowerCase()
  const assignedIds = new Set(assignedTechnicians.value.map((user: any) => user.id))
  return staffUsers.value
    .filter((user: any) => !assignedIds.has(user.id))
    .filter((user: any) => !term || userSearchText(user).includes(term))
    .slice(0, 12)
})

const statusOpts = [
  { v: 'open', l: 'Aberto' }, { v: 'assigned', l: 'Atribuído' },
  { v: 'in_progress', l: 'Em Curso' }, { v: 'waiting_user', l: 'A aguardar utilizador' },
  { v: 'resolved', l: 'Resolvido' }, { v: 'closed', l: 'Fechado' },
]

const timeline = [
  { status: 'open', label: 'Aberto' },
  { status: 'assigned', label: 'Atribuído' },
  { status: 'in_progress', label: 'Em Curso' },
  { status: 'waiting_user', label: 'A aguardar utilizador' },
  { status: 'resolved', label: 'Resolvido' },
  { status: 'closed', label: 'Fechado' },
]

const statusOrder = ['open', 'assigned', 'in_progress', 'waiting_user', 'resolved', 'closed']
// Ready-made replies (Configurações → Respostas-modelo)
const quickReplies = ref<{ label: string; body: string; status: string }[]>([])
async function loadQuickReplies() {
  if (!auth.isStaff) return
  try { quickReplies.value = (await api.get('/api/v1/settings/quick-replies')).data.replies ?? [] } catch { quickReplies.value = [] }
}

// Rating by the requester, once the ticket is resolved or closed
const rateStars = ref(0)
const rateHover = ref(0)
const rateComment = ref('')
const rateSaving = ref(false)
const rateSaved = ref(false)
const rateHighlight = ref(false)
const canRate = computed(() => !!ticket.value && ticket.value.creator?.id === auth.user?.id
  && ['resolved', 'closed'].includes(ticket.value.status) && !auth.inPreview)
watch(() => ticket.value?.rating, (r: any) => {
  if (r) { rateStars.value = r.stars; rateComment.value = r.comment ?? '' }
}, { immediate: true })
async function saveRating() {
  if (!ticket.value || !rateStars.value) return
  rateSaving.value = true
  try {
    const { data } = await api.put(`/api/v1/tickets/${ticket.value.id}/rating`, { stars: rateStars.value, comment: rateComment.value })
    ticket.value.rating = data
    rateSaved.value = true
  } catch (e) {
    notifyError(e, 'Não foi possível guardar a avaliação.')
  } finally {
    rateSaving.value = false
  }
}

// Paste a screenshot straight into the reply; take a photo on phones/tablets
const cameraInput = ref<HTMLInputElement | null>(null)
const isTouch = typeof window !== 'undefined' && window.matchMedia?.('(pointer: coarse)').matches
function pastedImage(e: ClipboardEvent): File | null {
  const item = Array.from(e.clipboardData?.items ?? []).find((i) => i.kind === 'file' && i.type.startsWith('image/'))
  const file = item?.getAsFile()
  if (!file) return null
  e.preventDefault()
  const ext = file.type.split('/')[1]?.replace('jpeg', 'jpg') || 'png'
  const stamp = new Date().toLocaleString('pt-PT').replace(/[/:, ]+/g, '-')
  return new File([file], `captura-${stamp}.${ext}`, { type: file.type })
}
function onPasteImage(e: ClipboardEvent) {
  const file = pastedImage(e)
  if (file) commentFile.value = file
}

// @mentions: pick someone from the list; they get a notification when the reply is sent
const replyBox = ref<HTMLTextAreaElement | null>(null)
const mentionOpen = ref(false)
const mentionQuery = ref('')
const mentionIndex = ref(0)
const mentioned = new Map<string, number>()  // "@Nome Apelido" -> user id
const mentionCandidates = computed(() => {
  const me = auth.user?.id
  const t: any = ticket.value
  if (!t) return []
  const people = new Map<number, any>()
  const add = (u: any, tag = '') => { if (u && u.id !== me && !people.has(u.id)) people.set(u.id, { ...u, tag }) }
  if (privateOn.value) {
    privateChosen.value.forEach((u: any) => add(u))
  } else {
    if (!isInternal.value) {
      add(t.creator, 'solicitante')
      ;(t.watchers ?? []).forEach((u: any) => add(u, 'seguidor'))
    }
    ;[...(t.assignees ?? []), ...(t.assignee ? [t.assignee] : [])].forEach((u: any) => add(u, 'responsável'))
    staffPeople.value.filter((u: any) => !isInternal.value || isStaffUser(u)).forEach((u: any) => add(u, u.role_label || ''))
  }
  return [...people.values()]
})
const mentionMatches = computed(() => {
  const q = mentionQuery.value.toLowerCase()
  return mentionCandidates.value.filter((u: any) => !q || String(u.display_name).toLowerCase().includes(q)).slice(0, 6)
})
function onMentionInput() {
  const el = replyBox.value
  if (!el) return
  const before = newComment.value.slice(0, el.selectionStart ?? newComment.value.length)
  const m = before.match(/(?:^|\s)@([\p{L}]*)$/u)
  mentionOpen.value = !!m
  mentionQuery.value = m ? m[1] : ''
  mentionIndex.value = 0
  if (m) loadStaffPeople()
}
function pickMention(u: any) {
  const el = replyBox.value
  const caret = el?.selectionStart ?? newComment.value.length
  const before = newComment.value.slice(0, caret).replace(/@([\p{L}]*)$/u, '')
  const label = `@${shortName(u.display_name)}`
  newComment.value = `${before}${label} ${newComment.value.slice(caret)}`
  mentioned.set(label, u.id)
  mentionOpen.value = false
  nextTick(() => { el?.focus(); const pos = before.length + label.length + 1; el?.setSelectionRange(pos, pos) })
}
function onMentionKey(e: KeyboardEvent) {
  if (!mentionOpen.value || !mentionMatches.value.length) return
  if (e.key === 'ArrowDown') { e.preventDefault(); mentionIndex.value = (mentionIndex.value + 1) % mentionMatches.value.length }
  else if (e.key === 'ArrowUp') { e.preventDefault(); mentionIndex.value = (mentionIndex.value - 1 + mentionMatches.value.length) % mentionMatches.value.length }
  else if (e.key === 'Enter' || e.key === 'Tab') { e.preventDefault(); pickMention(mentionMatches.value[mentionIndex.value]) }
  else if (e.key === 'Escape') mentionOpen.value = false
}
function closeMentionsSoon() { setTimeout(() => { mentionOpen.value = false }, 150) }
function mentionIdsIn(text: string) {
  return [...mentioned.entries()].filter(([label]) => text.includes(label)).map(([, id]) => id)
}

function renderText(text: string): string {
  if (!text) return ''
  const escaped = text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    // @Nome Apelido → highlighted (text already escaped, so this only adds our own tag)
    .replace(/(^|\s)(@[\p{Lu}][\p{L}]+(?: [\p{Lu}][\p{L}]+)?)/gu, '$1<span class="mention">$2</span>')
  // Collapse 3+ consecutive newlines to 2, then convert to <br>
  return escaped.replace(/\n{3,}/g, '\n\n').replace(/\n/g, '<br>')
}

function isStatusDone(status: string) {
  const current = statusOrder.indexOf(ticket.value?.status)
  return statusOrder.indexOf(status) <= current
}

// ── Live updates (see services/realtime.ts) ─────────────────────────────
const viewers = ref<{ id: number; name: string }[]>([])
const otherViewers = computed(() => viewers.value.filter((v) => v.id !== auth.user?.id))
const typers = ref<Record<number, { name: string; timer: ReturnType<typeof setTimeout> }>>({})
const typingNames = computed(() => Object.values(typers.value).map((t) => shortName(t.name)))
const realtimeOffs: Array<() => void> = []
let viewTimer: ReturnType<typeof setInterval> | null = null
let lastTypingSent = 0
let liveTicketId = 0

function startLive(id: number) {
  liveTicketId = id
  sendRealtime({ type: 'view', ticket_id: id }, 'ticket-view')
  if (viewTimer) clearInterval(viewTimer)
  viewTimer = setInterval(() => sendRealtime({ type: 'view', ticket_id: id }), 20000)
}

function stopLive() {
  if (viewTimer) clearInterval(viewTimer)
  if (liveTicketId) sendRealtime({ type: 'leave', ticket_id: liveTicketId })
  forgetSticky('ticket-view')
  liveTicketId = 0
  viewers.value = []
}

async function deleteTicket() {
  if (!ticket.value) return
  const ok = await confirmDialog(
    `Apagar definitivamente o ticket T-${ticket.value.id} ("${ticket.value.title}")?\n\nApaga também as respostas e os anexos. Não é possível desfazer.`,
    { ok: 'Apagar ticket', danger: true },
  )
  if (!ok) return
  try {
    await adminBulkActionTickets({ ids: [ticket.value.id], action: 'delete' })
    router.push('/tickets')
  } catch (e: any) {
    notifyError(e, 'Não foi possível apagar o ticket.')
  }
}

// Emoji reactions on the replies
const reactions = ref<Record<number, ReactionSummary[]>>({})
const ticketReactions = ref<ReactionSummary[]>([])
async function loadReactions() {
  if (!ticket.value) return
  const ids = ((ticket.value.comments ?? []) as any[]).map((c) => c.id)
  try {
    const [data, own] = await Promise.all([getReactions('comment', ids), getReactions('ticket', [ticket.value.id])])
    reactions.value = Object.fromEntries(Object.entries(data).map(([k, v]) => [Number(k), v]))
    ticketReactions.value = own[String(ticket.value.id)] ?? []
  } catch { /* ignore */ }
}

async function markUnread() {
  if (!ticket.value) return
  try {
    await markTicketUnread(ticket.value.id)
    router.push('/tickets')
  } catch (e) {
    notifyError(e, 'Não foi possível marcar como não lido.')
  }
}

function onReplyTyping() {
  if (!ticket.value) return
  const now = Date.now()
  if (now - lastTypingSent < 3000) return
  lastTypingSent = now
  sendRealtime({ type: 'typing', ticket_id: ticket.value.id, private_to_ids: privateOn.value ? privateToIds.value : [], internal: isInternal.value })
}

realtimeOffs.push(
  onRealtime('ticket.changed', (e) => { if (e.ticket_id === liveTicketId) reloadLiveSoon() }),
  // Back online after a break (e.g. the server was updated): something may have changed meanwhile
  onRealtime('realtime.connected', (e) => {
    if (e.resumed && liveTicketId) reloadLiveSoon()
    // Opened while the server was unreachable: try again now that it answers
    else if (!ticket.value && loadError.value) retryLoad()
  }),
  onRealtime('reaction.changed', (e) => {
    if ((e.target_type === 'comment' || e.target_type === 'ticket') && e.ticket_id === liveTicketId) loadReactions()
  }),
  onRealtime('ticket.viewers', (e) => { if (e.ticket_id === liveTicketId) viewers.value = e.viewers }),
  onRealtime('ticket.typing', (e) => {
    if (e.ticket_id !== liveTicketId || e.user.id === auth.user?.id) return
    const prev = typers.value[e.user.id]
    if (prev) clearTimeout(prev.timer)
    typers.value[e.user.id] = { name: e.user.name, timer: setTimeout(() => { delete typers.value[e.user.id] }, 5000) }
  }),
)

// Someone else changed the ticket: reload it, at most once every half second, without undoing what this person
// is in the middle of (e.g. searching for a technician)
let liveReloadTimer: ReturnType<typeof setTimeout> | null = null
function reloadLiveSoon() {
  if (liveReloadTimer) clearTimeout(liveReloadTimer)
  liveReloadTimer = setTimeout(async () => {
    try {
      await load({ live: true })
      loadImageBlobs()
      loadReactions()
    } catch { /* the next event or reconnection tries again */ }
  }, 500)
}

const loadError = ref('')
async function retryLoad() {
  loadError.value = ''
  await init()
}

async function firstLoad() {
  try {
    await load()
  } catch (e: any) {
    loadError.value = e?.response?.status === 404
      ? 'Este ticket não existe ou foi apagado.'
      : e?.response?.status === 403
        ? 'Não tem acesso a este ticket.'
        : errorMessage(e, 'Não foi possível abrir o ticket.')
    return false
  }
  return true
}

onMounted(() => init())

async function init() {
  if (!(await firstLoad())) return
  loadQuickReplies()
  if (route.query.avaliar && canRate.value) {
    rateHighlight.value = true
    nextTick(() => document.getElementById('avaliar')?.scrollIntoView({ behavior: 'smooth', block: 'center' }))
  }
  loadReactions()
  loadReminders()
  if (ticket.value) startLive(ticket.value.id)
  loadImageBlobs()
  if (auth.isStaff) {
    try {
      const [users, grps] = await Promise.all([getUsers(), getGroups()])
      staffUsers.value = users.filter(isAssignableTechnician)
      groups.value = grps
    } catch (e) {
      notifyError(e, 'Não foi possível carregar a lista de técnicos e grupos.')
    }
  }
}

onUnmounted(() => {
  if (liveReloadTimer) clearTimeout(liveReloadTimer)
  stopLive()
  realtimeOffs.forEach((off) => off())
  if (watcherSearchTimer) clearTimeout(watcherSearchTimer)
  Object.values(attachBlobUrls.value).forEach(url => URL.revokeObjectURL(url))
})

watch(watcherSearch, value => {
  if (watcherSearchTimer) clearTimeout(watcherSearchTimer)
  const term = value.trim()
  if (term.length < 2) {
    watcherResults.value = []
    watcherLoading.value = false
    return
  }
  watcherLoading.value = true
  watcherSearchTimer = setTimeout(async () => {
    try {
      const results = await searchUsers(term, { limit: 8 })
      if (watcherSearch.value.trim() === term) watcherResults.value = results
    } finally {
      if (watcherSearch.value.trim() === term) watcherLoading.value = false
    }
  }, 250)
})

async function load(opts: { live?: boolean } = {}) {
  const t = await getTicket(Number(route.params.id))
  ticket.value = t
  // A live reload keeps a technician search that is being typed
  if (!opts.live) assigneeSearch.value = ''
  groupId.value = t.group?.id ? String(t.group.id) : ''
  ticketStatus.value = t.status
}

function loadImageBlobs() {
  const attachments: any[] = ticket.value?.attachments ?? []
  for (const a of attachments) {
    if ((a.content_type as string).startsWith('image/') && !attachBlobUrls.value[a.id]) {
      fetchAttachmentBlob(ticket.value.id, a.id)
        .then(url => { attachBlobUrls.value[a.id] = url })
        .catch(() => {})
    }
  }
}

async function openLightbox(a: { id: number; content_type: string }) {
  let url = attachBlobUrls.value[a.id]
  if (!url) {
    url = await fetchAttachmentBlob(ticket.value.id, a.id)
    attachBlobUrls.value[a.id] = url
  }
  lightboxSrc.value = url
}

async function openFile(a: { id: number; original_name: string }) {
  const url = await fetchAttachmentBlob(ticket.value.id, a.id)
  window.open(url, '_blank')
  setTimeout(() => URL.revokeObjectURL(url), 30000)
}

function startEditContent() {
  editTitle.value = ticket.value.title
  editDescription.value = ticket.value.description
  contentError.value = ''
  editingContent.value = true
}

function cancelEditContent() {
  editingContent.value = false
  contentError.value = ''
}

async function saveContent() {
  if (!editTitle.value.trim() || !editDescription.value.trim()) {
    contentError.value = 'O assunto e a descrição não podem estar vazios.'
    return
  }
  savingContent.value = true
  contentError.value = ''
  try {
    ticket.value = await adminUpdateTicket(ticket.value.id, {
      title: editTitle.value.trim(),
      description: editDescription.value.trim(),
    })
    editingContent.value = false
  } catch (e: any) {
    contentError.value = errorMessage(e, 'Erro ao guardar as alterações.')
  } finally {
    savingContent.value = false
  }
}

async function onAddComment() {
  if (!newComment.value.trim() && !commentFile.value) return
  if (privateOn.value && !privateToIds.value.length) {
    commentError.value = 'Escolha a quem enviar a mensagem privada.'
    return
  }
  commenting.value = true
  commentError.value = ''
  const newStatus = auth.isStaff && replyStatus.value && replyStatus.value !== ticket.value.status ? replyStatus.value : ''
  try {
    const privateIds = privateOn.value ? privateToIds.value : []
    const internal = isInternal.value && !privateIds.length
    // A public reply carries the new state itself: the requester gets one email with both
    const statusWithReply = newStatus && !internal && !privateIds.length ? newStatus : null
    const created = await addComment(ticket.value.id, newComment.value || '📎 Ficheiro anexado.', internal, null, privateIds, statusWithReply, mentionIdsIn(newComment.value))
    mentioned.clear()
    newComment.value = ''
    isInternal.value = false
    privateOn.value = privateOnly.value
    privateToIds.value = privateOnly.value ? privateIds : []
    if (commentFile.value) {
      await uploadTicketAttachment(ticket.value.id, commentFile.value, created.id)
      commentFile.value = null
      if (commentFileInput.value) commentFileInput.value.value = ''
    }
    if (newStatus && !statusWithReply) {
      await adminUpdateTicket(ticket.value.id, { status: newStatus })
    }
    replyStatus.value = ''
    await load()
    loadReminders()
  } catch (e: any) {
    commentError.value = errorMessage(e, 'Erro ao enviar resposta')
  } finally {
    commenting.value = false
  }
}

function toIsoDate(d: Date) {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

function setReminderIn(days: number) {
  const d = new Date()
  if (days === 7) {
    // "Próxima segunda": the first Monday after today (tomorrow, if today is Sunday)
    d.setDate(d.getDate() + (((8 - d.getDay()) % 7) || 7))
  } else {
    d.setDate(d.getDate() + days)
    while (d.getDay() === 0 || d.getDay() === 6) d.setDate(d.getDate() + 1)
  }
  remindDate.value = toIsoDate(d)
  if (!remindTime.value) remindTime.value = '09:00'
}

function formatReminder(iso?: string | null) {
  if (!iso) return ''
  const d = new Date(iso.endsWith('Z') || iso.includes('+') ? iso : iso + 'Z')
  return d.toLocaleDateString('pt-PT', { day: '2-digit', month: '2-digit' }) + ' às ' + d.toLocaleTimeString('pt-PT', { hour: '2-digit', minute: '2-digit' })
}

const sendLabel = computed(() => {
  const base = privateOn.value ? 'Enviar em privado' : 'Enviar'
  const target = statusOpts.find((o) => o.v === replyStatus.value)
  return target ? `${base} e marcar ${target.l}` : base
})

async function onStatusChange() {
  try {
    await adminUpdateTicket(ticket.value.id, { status: ticketStatus.value })
    await load()
  } catch (e) {
    ticketStatus.value = ticket.value.status
    notifyError(e, 'Não foi possível alterar o estado.')
  }
}

async function saveAssignees(ids: number[]) {
  try {
    ticket.value = await adminUpdateTicket(ticket.value.id, { assignee_ids: ids })
    assigneeSearch.value = ''
    assigneeSearchOpen.value = false
    await load()
  } catch (e) {
    assigneeSearch.value = ''
    assigneeSearchOpen.value = false
    notifyError(e, 'Não foi possível alterar os técnicos atribuídos.')
  }
}

async function addAssignee(user: any) {
  const ids = Array.from(new Set([...assignedTechnicians.value.map((u: any) => u.id), user.id]))
  await saveAssignees(ids)
}

async function removeAssignee(userId: number) {
  await saveAssignees(assignedTechnicians.value.map((u: any) => u.id).filter((id: number) => id !== userId))
}

async function onGroupChange() {
  try {
    await adminUpdateTicket(ticket.value.id, { group_id: groupId.value ? Number(groupId.value) : null })
    await load()
  } catch (e) {
    groupId.value = ticket.value.group?.id ? String(ticket.value.group.id) : ''
    notifyError(e, 'Não foi possível alterar o grupo.')
  }
}

async function toggleEmailNotifications() {
  if (!ticket.value || savingEmailPreference.value) return
  savingEmailPreference.value = true
  try {
    const payload = { creator_email_notifications: !ticket.value.creator_email_notifications }
    ticket.value = auth.isAdmin
      ? await adminUpdateTicket(ticket.value.id, payload)
      : await updateTicket(ticket.value.id, payload)
  } catch (e) {
    notifyError(e, 'Não foi possível alterar as notificações por email.')
  } finally {
    savingEmailPreference.value = false
  }
}

function canEditComment(comment: any) {
  if (comment.private_to) return comment.author?.id === auth.user?.id
  return auth.isStaff || comment.author?.id === auth.user?.id
}

function startEditComment(comment: any) {
  editingCommentId.value = comment.id
  editingCommentBody.value = comment.body
}

function cancelEditComment() {
  editingCommentId.value = null
  editingCommentBody.value = ''
}

async function saveEditedComment(comment: any) {
  if (!editingCommentBody.value.trim()) return
  try {
    await updateComment(ticket.value.id, comment.id, editingCommentBody.value)
    cancelEditComment()
    await load()
  } catch (e) {
    notifyError(e, 'Não foi possível guardar a alteração.')
  }
}

async function onDeleteComment(comment: any) {
  if (!(await confirmDialog('Apagar esta resposta?', { ok: 'Apagar', danger: true }))) return
  try {
    await deleteComment(ticket.value.id, comment.id)
    await load()
  } catch (e) {
    notifyError(e, 'Não foi possível apagar a resposta.')
  }
}

async function onAddWatcher() {
  if (!resolvedWatcherId.value || addingWatcher.value) return
  addingWatcher.value = true
  try {
    ticket.value = await addWatcher(ticket.value.id, resolvedWatcherId.value)
    watcherSearch.value = ''
  } catch (e) {
    notifyError(e, 'Não foi possível adicionar o seguidor.')
  } finally {
    addingWatcher.value = false
  }
}

async function addWatcherCandidate(user: any) {
  if (!user?.id || addingWatcher.value) return
  addingWatcher.value = true
  try {
    ticket.value = await addWatcher(ticket.value.id, user.id)
    watcherSearch.value = ''
  } catch (e) {
    notifyError(e, 'Não foi possível adicionar o seguidor.')
  } finally {
    addingWatcher.value = false
  }
}

async function onRemoveWatcher(userId: number) {
  try {
    ticket.value = await removeWatcher(ticket.value.id, userId)
  } catch (e) {
    notifyError(e, 'Não foi possível remover o seguidor.')
  }
}

async function onEscalateTicket() {
  const alreadyEscalated = isEscalated.value
  const msg = alreadyEscalated
    ? 'Reenviar este ticket à empresa de apoio (enviará novamente o email de escalamento)?'
    : 'Reportar este ticket à empresa de apoio informático configurada?'
  if (!(await confirmDialog(msg, { ok: alreadyEscalated ? 'Reenviar' : 'Reportar' }))) return
  escalating.value = true
  escalationMessage.value = ''
  escalationError.value = false
  try {
    ticket.value = await escalateTicket(ticket.value.id)
    escalationMessage.value = alreadyEscalated
      ? 'Email reenviado à empresa de apoio.'
      : 'Ticket reportado e email enviado à empresa de apoio.'
  } catch (error: any) {
    escalationError.value = true
    escalationMessage.value = errorMessage(error, 'Não foi possível reportar o ticket. Verifica o email da empresa de apoio nas configurações.')
  } finally {
    escalating.value = false
  }
}

async function onDeescalate() {
  if (!ticket.value) return
  deescalating.value = true
  try {
    ticket.value = await deescalateTicket(ticket.value.id)
  } catch (e) {
    notifyError(e, 'Não foi possível retirar o reporte.')
  } finally {
    deescalating.value = false
  }
}

async function forwardCommentToProvider(comment: any) {
  if (!(await confirmDialog('Reenviar esta resposta à empresa de apoio?', { ok: 'Reenviar' }))) return
  sendingCommentId.value = comment.id
  escalationMessage.value = ''
  escalationError.value = false
  try {
    await escalateComment(ticket.value.id, comment.id)
    escalationMessage.value = 'Resposta enviada à empresa de apoio.'
  } catch (error: any) {
    escalationError.value = true
    escalationMessage.value = errorMessage(error, 'Não foi possível reenviar. Verifique as configurações de email.')
  } finally {
    sendingCommentId.value = null
  }
}

function userSearchText(u: any) {
  const emailPrefix = String(u.email || '').split('@')[0]
  return `${u.display_name} ${u.email} ${emailPrefix} ${u.username}`.toLowerCase()
}

function isAssignableTechnician(u: any) {
  return u?.is_active && (u.role === 'technician' || u.is_technician)
}

function statusLabel(s: string) {
  return labelFor(s)
}

function formatDate(d: string) {
  return formatDateTime(d)
}

async function onDownloadAttachment(a: { id: number; original_name: string }) {
  await downloadAttachment(ticket.value.id, a.id, a.original_name)
}

function formatSize(size: number) {
  return size >= 1024 * 1024 ? `${(size / 1024 / 1024).toFixed(1)} MB` : `${Math.round(size / 1024)} KB`
}
</script>

<style scoped>
.rate-card { padding: 18px 20px; margin-bottom: 16px; border-color: #FDE68A; }
.rate-card.highlight { box-shadow: 0 0 0 3px rgba(245, 158, 11, .35); }
.rate-title { font-weight: 700; font-size: 14px; margin-bottom: 8px; }
.rate-stars { display: flex; align-items: center; gap: 2px; margin-bottom: 10px; }
.rate-star { border: 0; background: transparent; cursor: pointer; padding: 2px; color: #D1D5DB; line-height: 0; }
.rate-star.on { color: #F59E0B; }
.rate-star .material-icons { font-size: 30px; }
.rate-hint { margin-left: 8px; font-size: 13px; color: var(--c-muted); font-weight: 600; }
.rate-actions { display: flex; justify-content: flex-end; align-items: center; gap: 12px; margin-top: 10px; }
.rate-saved { color: #16A34A; font-size: 13px; font-weight: 700; display: inline-flex; align-items: center; gap: 4px; }
.rate-saved .material-icons { font-size: 17px; }
.rating-stars { color: #F59E0B; letter-spacing: 1px; font-size: 15px; }
.rating-off { color: #D1D5DB; }
.rating-comment { font-size: 12.5px; color: var(--c-muted); font-style: italic; padding: 0 0 10px; }
.mention-menu { position: relative; z-index: 20; margin-top: 4px; border: 1px solid var(--c-border); border-radius: 10px; background: var(--c-surface); box-shadow: var(--shadow-md); padding: 4px; max-width: 360px; }
.mention-item { display: flex; align-items: center; gap: 8px; width: 100%; border: 0; background: transparent; padding: 6px 8px; border-radius: 8px; cursor: pointer; color: var(--c-text); font-size: 13px; text-align: left; }
.mention-item small { color: var(--c-muted); margin-left: auto; }
.mention-item.active, .mention-item:hover { background: var(--c-primary-soft); }
:deep(.mention) { color: var(--c-primary); font-weight: 700; background: var(--c-primary-soft); border-radius: 5px; padding: 0 3px; }
.load-error { padding: 64px 16px; text-align: center; color: var(--c-muted); display: flex; flex-direction: column; align-items: center; gap: 12px; }
.load-error .material-icons { font-size: 40px; color: #DC2626; }
.escalated-badge {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: .4px;
  background: #FFF7ED;
  color: #C2410C;
  border: 1px solid #FED7AA;
  border-radius: 5px;
  padding: 3px 8px;
  white-space: nowrap;
}
:root.dark .escalated-badge {
  background: #431407;
  color: #FB923C;
  border-color: #7C2D12;
}
.deescalated-badge {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: .4px;
  background: #DCFCE7;
  color: #166534;
  border: 1px solid #BBF7D0;
  border-radius: 5px;
  padding: 3px 8px;
  white-space: nowrap;
}
:root.dark .deescalated-badge {
  background: #14532D;
  color: #86EFAC;
  border-color: #166534;
}

/* ── Ticket header ── */
.ticket-header {
  margin-bottom: 24px;
}

.ticket-title-row {
  margin-bottom: 8px;
}

.ticket-title {
  font-size: 20px;
  font-weight: 700;
  line-height: 1.35;
  margin: 0;
  word-break: break-word;
}

.ticket-badges-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 6px;
}

.ticket-meta {
  font-size: 13px;
  color: var(--c-muted);
}

/* ── Ticket detail grid ── */
.ticket-detail-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 320px;
  gap: 20px;
  align-items: start;
}

.ticket-side-panel {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.msg-action {
  border: 0;
  background: transparent;
  color: var(--c-primary);
  cursor: pointer;
  font-size: 12px;
  font-weight: 700;
  padding: 2px 4px;
}

.msg-action.danger {
  color: #dc2626;
}

.comment-edit-box {
  margin-top: 8px;
}

.quick-replies {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 12px;
}

.quick-reply {
  border: 1px solid var(--c-border);
  background: var(--c-surface);
  color: var(--c-text);
  border-radius: 6px;
  cursor: pointer;
  font-size: 12px;
  font-weight: 700;
  padding: 6px 9px;
}

.quick-reply:hover {
  border-color: var(--c-primary);
  color: var(--c-primary);
}

.quick-reply-active {
  background: #22C55E;
  border-color: #16A34A;
  color: #fff;
}

.quick-reply-active:hover {
  background: #16A34A;
  border-color: #15803D;
  color: #fff;
}

.reply-file-preview {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 8px;
  padding: 6px 10px;
  background: var(--c-bg);
  border: 1px solid var(--c-border);
  border-radius: 8px;
  min-width: 0;
}

.watcher-list {
  display: flex;
  flex-direction: column;
  gap: 7px;
  min-width: 0;
}

.watcher-mini {
  align-items: center;
  display: grid;
  gap: 6px;
  grid-template-columns: 22px minmax(0, 1fr) auto;
}

.watcher-mini span {
  font-size: 13px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.watcher-remove-btn {
  background: none;
  border: none;
  cursor: pointer;
  color: var(--c-muted);
  padding: 2px;
  border-radius: 4px;
  display: flex;
  align-items: center;
  line-height: 1;
  transition: background .15s, color .15s;
}

.watcher-remove-btn:hover {
  background: #FEE2E2;
  color: #DC2626;
}

.watcher-add-row {
  display: flex;
  gap: 8px;
  align-items: center;
  width: 100%;
}

.person-search {
  flex: 1;
  min-width: 0;
  position: relative;
  width: 100%;
}

.person-search .hd-input {
  font-size: 12px;
  padding: 6px 9px;
  width: 100%;
}

.person-search-menu {
  background: var(--c-surface);
  border: 1px solid var(--c-border);
  border-radius: 10px;
  box-shadow: 0 12px 26px rgba(15, 23, 42, 0.16);
  left: 0;
  max-height: 250px;
  overflow-y: auto;
  padding: 4px;
  position: absolute;
  right: 0;
  top: calc(100% + 6px);
  z-index: 30;
}

.person-search-menu button {
  align-items: center;
  background: transparent;
  border: 0;
  border-radius: 8px;
  color: var(--c-text);
  cursor: pointer;
  display: grid;
  gap: 8px;
  grid-template-columns: 22px minmax(0, 1fr);
  padding: 8px;
  text-align: left;
  width: 100%;
}

.person-search-menu button:hover {
  background: var(--c-surface-soft);
}

.person-search-menu strong,
.person-search-menu small {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.person-search-menu strong {
  font-size: 12px;
}

.person-search-menu small {
  color: var(--c-muted);
  font-size: 11px;
  margin-top: 1px;
}

.person-search-empty {
  color: var(--c-muted);
  font-size: 12px;
  padding: 8px;
}

.assignee-editor {
  display: grid;
  gap: 8px;
  min-width: 0;
  width: 100%;
  flex: 1 1 0;
}
.assignee-chip-list { min-width: 0; }
.assignee-chip, .watcher-mini { max-width: 100%; min-width: 0; }

.assignee-chip-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.assignee-chip {
  align-items: center;
  background: rgba(61, 82, 213, 0.10);
  border: 1px solid rgba(61, 82, 213, 0.18);
  border-radius: 999px;
  color: var(--c-text);
  display: inline-flex;
  font-size: 12px;
  font-weight: 700;
  gap: 6px;
  max-width: 100%;
  padding: 4px 7px 4px 4px;
}

.assignee-chip button {
  align-items: center;
  background: transparent;
  border: 0;
  color: var(--c-muted);
  cursor: pointer;
  display: inline-flex;
  padding: 0;
}

.assignee-chip .material-icons {
  font-size: 14px;
}

.muted-mini {
  color: var(--c-muted);
  font-size: 13px;
}

.provider-escalation {
  border-top: 1px solid var(--c-border);
  margin-top: 4px;
  padding-top: 16px;
}

.email-notification-panel {
  align-items: center;
  background: rgba(61, 82, 213, 0.06);
  border: 1px solid rgba(61, 82, 213, 0.18);
  border-radius: 9px;
  display: grid;
  gap: 10px;
  margin: 0 0 14px;
  padding: 12px;
}

.email-notification-panel strong,
.email-notification-panel span {
  display: block;
}

.email-notification-panel strong {
  font-size: 13px;
}

.email-notification-panel span {
  color: var(--c-muted);
  font-size: 12px;
  margin-top: 2px;
}

.email-toggle-btn {
  align-items: center;
  background: var(--c-surface);
  border: 1px solid var(--c-border);
  border-radius: 8px;
  color: var(--c-muted);
  cursor: pointer;
  display: inline-flex;
  font-size: 12px;
  font-weight: 800;
  gap: 7px;
  justify-content: center;
  padding: 9px 10px;
  width: 100%;
}

.email-toggle-btn.active {
  background: rgba(22, 163, 74, 0.1);
  border-color: rgba(22, 163, 74, 0.24);
  color: #15803D;
}

.email-toggle-btn .material-icons {
  font-size: 16px;
}

.provider-escalation p {
  color: #16A34A;
  font-size: 12px;
  margin: 8px 0 0;
}

.provider-escalation p.error {
  color: #DC2626;
}

.event-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 18px;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--c-border);
}

.event-item {
  display: grid;
  grid-template-columns: 10px minmax(0, 1fr);
  gap: 10px;
  align-items: start;
}

.event-dot {
  width: 8px;
  height: 8px;
  margin-top: 7px;
  border-radius: 50%;
  background: var(--c-primary);
}

.event-message {
  font-size: 13px;
  font-weight: 700;
}

.event-meta {
  color: var(--c-muted);
  font-size: 12px;
}

@media (max-width: 900px) {
  .ticket-detail-grid {
    grid-template-columns: minmax(0, 1fr);
  }

  .ticket-side-panel {
    order: -1;
  }

  :deep(.hd-msg) {
    grid-template-columns: 32px minmax(0, 1fr);
  }

  :deep(.hd-msg-header) {
    align-items: flex-start;
    flex-wrap: wrap;
    gap: 6px;
  }
}

.attach-thumb {
  width: 80px;
  height: 80px;
  border: 1px solid var(--c-border);
  border-radius: 8px;
  overflow: hidden;
  cursor: pointer;
  background: var(--c-surface);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0;
  transition: opacity .15s;
}

.attach-thumb:hover {
  opacity: .85;
}

</style>

<style>
.hd-lightbox {
  position: fixed;
  inset: 0;
  z-index: 9999;
  background: rgba(0, 0, 0, .88);
  display: flex;
  align-items: center;
  justify-content: center;
}

.hd-lightbox-img {
  max-width: 90vw;
  max-height: 90vh;
  border-radius: 6px;
  box-shadow: 0 8px 40px rgba(0, 0, 0, .5);
  object-fit: contain;
}

.hd-lightbox-close {
  position: absolute;
  top: 16px;
  right: 16px;
  background: rgba(255, 255, 255, .15);
  border: none;
  border-radius: 50%;
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  color: #fff;
  transition: background .15s;
}

.hd-lightbox-close:hover {
  background: rgba(255, 255, 255, .25);
}
.send-group { gap: 8px; flex-wrap: wrap; justify-content: flex-end; }
.reply-status {
  display: inline-flex; align-items: center; gap: 4px; padding: 0 4px 0 10px; height: 36px;
  border: 1px solid var(--c-border); border-radius: 8px; background: var(--c-surface); color: var(--c-muted); cursor: pointer;
}
.reply-status .material-icons { font-size: 16px; }
.reply-status select { max-width: 190px; border: 0; background: transparent; color: var(--c-text); font-size: 13px; font-weight: 600; padding: 6px 4px; cursor: pointer; outline: none; }
.reply-status.changed { border-color: var(--c-primary); background: var(--c-primary-soft); color: var(--c-primary); }
.reply-status.changed select { color: var(--c-primary); }
.dark .reply-status select option { background: #111827; color: #F9FAFB; }
.group-tag {
  display: inline-block; font-size: 10.5px; font-weight: 700; color: var(--c-muted);
  border: 1px solid var(--c-border); border-radius: 6px; padding: 0 6px; line-height: 17px;
}
.crumbs { display: flex; align-items: center; justify-content: space-between; gap: 10px; font-size: 12px; color: var(--c-muted); margin-bottom: 6px; }
.mark-unread { display: inline-flex; align-items: center; gap: 4px; border: 0; background: transparent; color: var(--c-muted); font-size: 12px; font-weight: 600; cursor: pointer; padding: 2px 4px; border-radius: 6px; }
.mark-unread:hover { color: var(--c-primary); background: var(--c-primary-soft); }
.mark-unread .material-icons { font-size: 15px; }
.mark-unread.danger:hover { color: #DC2626; background: rgba(220, 38, 38, .1); }
.crumb-actions { display: inline-flex; gap: 4px; flex-wrap: wrap; }
.live-viewers { display: inline-flex; align-items: center; gap: 8px; font-size: 12.5px; color: var(--c-muted); margin: 2px 0 6px; }
.live-dot { width: 8px; height: 8px; border-radius: 50%; background: #22C55E; box-shadow: 0 0 0 3px rgba(34, 197, 94, .2); }
.live-avatars { display: inline-flex; }
.live-avatar { width: 22px; height: 22px; border-radius: 50%; display: grid; place-items: center; font-size: 9.5px; font-weight: 800; color: #fff; background: linear-gradient(135deg, #2563EB, #0891B2); border: 2px solid var(--c-bg); margin-left: -6px; }
.live-avatar:first-child { margin-left: 0; }
.live-typing { display: flex; align-items: center; gap: 8px; font-size: 12.5px; color: var(--c-muted); margin-top: 6px; font-style: italic; }
.live-dots { display: inline-flex; gap: 3px; }
.live-dots i { width: 5px; height: 5px; border-radius: 50%; background: var(--c-muted); animation: live-bounce 1.2s infinite ease-in-out; }
.live-dots i:nth-child(2) { animation-delay: .15s; }
.live-dots i:nth-child(3) { animation-delay: .3s; }
@keyframes live-bounce { 0%, 80%, 100% { transform: translateY(0); opacity: .4; } 40% { transform: translateY(-3px); opacity: 1; } }
.read-only-note { display: flex; align-items: center; gap: 10px; padding: 14px 18px; font-size: 13px; color: var(--c-muted); }
.read-only-note .material-icons { font-size: 18px; color: var(--c-primary); }
.school-badge {
  display: inline-flex; align-items: center; gap: 5px; max-width: 100%;
  font-size: 13px; font-weight: 700; color: #0E7490; background: #CFFAFE;
  border: 1px solid #A5F3FC; border-radius: 999px; padding: 3px 12px 3px 9px;
}
.school-badge .material-icons { font-size: 16px; }
.send-group { gap: 8px; flex-wrap: wrap; justify-content: flex-end; }
.reply-status {
  display: inline-flex; align-items: center; gap: 4px; padding: 0 4px 0 10px; height: 36px;
  border: 1px solid var(--c-border); border-radius: 8px; background: var(--c-surface); color: var(--c-muted); cursor: pointer;
}
.reply-status .material-icons { font-size: 16px; }
.reply-status select { max-width: 190px; border: 0; background: transparent; color: var(--c-text); font-size: 13px; font-weight: 600; padding: 6px 4px; cursor: pointer; outline: none; }
.reply-status.changed { border-color: var(--c-primary); background: var(--c-primary-soft); color: var(--c-primary); }
.reply-status.changed select { color: var(--c-primary); }
.dark .reply-status select option { background: #111827; color: #F9FAFB; }
.dark .school-badge { color: #A5F3FC; background: rgba(8, 145, 178, .2); border-color: rgba(34, 211, 238, .35); }
/* Private messages: grouped in one indented block with its own colour */
.private-thread {
  margin: 0 0 14px 56px; padding: 12px 14px 2px;
  background: #F3EEFF; border: 1px solid #DDD1FB; border-left: 4px solid #7C3AED; border-radius: 12px;
}
.dark .private-thread { background: rgba(124, 58, 237, .14); border-color: rgba(167, 139, 250, .30); border-left-color: #A78BFA; }
@media (max-width: 600px) { .private-thread { margin-left: 16px; } }
.private-thread-head {
  display: flex; flex-wrap: wrap; align-items: center; gap: 8px; margin-bottom: 12px;
  font-size: 12.5px; font-weight: 700; color: #6D28D9;
}
.private-thread-head .material-icons { font-size: 16px; }
.msg-files { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 8px; align-items: center; }
.msg-file { display: inline-flex; align-items: center; gap: 5px; color: var(--c-primary); font-size: 12.5px; background: none; border: none; cursor: pointer; padding: 0; text-align: left; }
.msg-file .material-icons { font-size: 15px; }
.thread-attach { cursor: pointer; flex-shrink: 0; align-self: center; }
.thread-file { margin-top: 4px; }
.thread-reply { display: flex; align-items: flex-end; gap: 8px; margin-top: 4px; }
.thread-reply .hd-textarea { flex: 1; min-width: 0; min-height: 40px; resize: none; padding: 9px 12px; font-size: 13.5px; line-height: 1.4; }
.thread-send { flex-shrink: 0; padding: 8px 14px; font-size: 13px; }
.thread-send .material-icons { font-size: 15px; }
.dark .private-thread-head { color: #DDD6FE; }
.hd-msg-private .hd-msg-bubble { background: rgba(255, 255, 255, .75); border: 1px solid #E9E1FD; }
.dark .hd-msg-private .hd-msg-bubble { background: rgba(255, 255, 255, .05); border-color: rgba(167, 139, 250, .18); }
.private-box { border: 1px solid #DDD1FB; background: rgba(124, 58, 237, .06); border-radius: 10px; padding: 10px 12px; margin-bottom: 12px; }
.private-box.off { border-color: var(--c-border); background: transparent; padding: 8px 12px; }
.private-box.off .private-title { color: var(--c-muted); font-weight: 600; }
.private-box.off .private-title .material-icons { color: var(--c-muted); }
.private-title { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; font-size: 13px; font-weight: 700; color: var(--c-text); }
.private-title .material-icons { font-size: 17px; color: #7C3AED; }
.private-select { width: auto; max-width: 340px; padding: 5px 10px; font-size: 13px; }
.private-people { display: flex; flex-wrap: wrap; align-items: center; gap: 6px; margin-top: 8px; }
.private-chip { display: inline-flex; align-items: center; gap: 5px; padding: 3px 4px 3px 10px; border-radius: 999px; background: rgba(124, 58, 237, .12); color: #5B21B6; font-size: 12.5px; font-weight: 700; }
.private-chip small { font-weight: 500; opacity: .75; }
.private-chip button { display: inline-flex; border: 0; background: transparent; color: inherit; cursor: pointer; border-radius: 50%; padding: 2px; }
.private-chip button:hover { background: rgba(124, 58, 237, .18); }
.private-chip .material-icons { font-size: 14px; }
.dark .private-chip { background: rgba(167, 139, 250, .2); color: #DDD6FE; }
.private-hint { font-size: 12px; color: var(--c-muted); margin-top: 8px; }
.reminder-tag {
  display: inline-flex; align-items: center; gap: 3px;
  font-size: 10.5px; font-weight: 700;
  padding: 2px 7px; border-radius: 999px;
  color: #B45309; background: #FEF3C7;
}
.reminder-tag .material-icons { font-size: 12px; }
.reminder-tag.sent { color: var(--c-muted); background: var(--c-surface-soft, rgba(0,0,0,.05)); }
.dark .reminder-tag:not(.sent) { color: #FCD34D; background: rgba(245, 158, 11, .16); }
.reminder-box {
  margin-top: 10px; padding: 10px 12px;
  border: 1px dashed #F59E0B; border-radius: 10px;
  background: rgba(245, 158, 11, .06);
}
.reminder-box.off { border-color: var(--c-border); background: transparent; padding: 8px 12px; }
.reminder-box.off .reminder-title { margin-bottom: 0; color: var(--c-muted); font-weight: 600; }
.reminder-box.off .reminder-title .material-icons { color: var(--c-muted); }
.reminder-title { display: flex; align-items: center; gap: 8px; font-size: 13px; font-weight: 700; color: var(--c-text); margin-bottom: 8px; }
.reminder-title .material-icons { font-size: 17px; color: #D97706; }
.reminder-opt { font-weight: 400; font-size: 12px; color: var(--c-muted); }
.reminder-row { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; }
.reminder-date { width: auto; max-width: 170px; padding: 6px 10px; }
.reminder-time { width: auto; max-width: 110px; padding: 6px 10px; }
.reminder-chip {
  border: 1px solid var(--c-border); background: var(--c-surface); color: var(--c-text);
  border-radius: 999px; padding: 5px 10px; font: 600 12px var(--font-sans); cursor: pointer;
}
.reminder-chip:hover { border-color: #F59E0B; color: #B45309; }
.reminder-chip.clear { color: var(--c-muted); }
.reminder-saved { display: flex; flex-direction: column; gap: 6px; margin: 4px 0 8px; }
.reminder-saved-item { display: flex; align-items: center; gap: 8px; font-size: 13px; padding: 7px 10px; border-radius: 10px; background: rgba(245, 158, 11, .1); border: 1px solid rgba(245, 158, 11, .3); }
.reminder-saved-item .material-icons { font-size: 17px; color: #D97706; }
.reminder-saved-item > span:nth-child(2) { flex: 1; min-width: 0; }
.reminder-cancel { border: 0; background: transparent; color: #DC2626; font-weight: 700; font-size: 12px; cursor: pointer; }
.reminder-ok { display: flex; align-items: center; gap: 6px; font-size: 13px; color: #16A34A; margin: 2px 0 8px; }
.reminder-ok .material-icons { font-size: 17px; }
.reminder-status { display: flex; align-items: center; gap: 6px; font-size: 12.5px; color: var(--c-muted); margin-top: 8px; min-height: 18px; }
.reminder-status .material-icons { font-size: 16px; }
.reminder-status.saved { color: #16A34A; }
.reminder-status.error { color: #DC2626; }
.reminder-status .spin { animation: rem-spin 1s linear infinite; }
@keyframes rem-spin { to { transform: rotate(360deg); } }
.reminder-actions { display: flex; align-items: center; justify-content: space-between; gap: 10px; margin-top: 10px; flex-wrap: wrap; }
.reminder-save { font-size: 13px; padding: 7px 14px; }
.reminder-save .material-icons { font-size: 17px; }
.reminder-err { color: #DC2626; font-size: 12.5px; margin-top: 6px; }
.dark .reminder-saved-item { background: rgba(245, 158, 11, .12); }
.reminder-hint { font-size: 12px; color: var(--c-muted); margin-top: 8px; }
</style>
