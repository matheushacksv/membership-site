<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { LifeBuoy, Loader2, Paperclip, Send } from 'lucide-vue-next'
import {
  TICKET_CATEGORIES,
  type TicketDetail,
  type TicketListItem,
} from '~/composables/useTickets'

definePageMeta({ layout: 'admin', middleware: 'admin' })
useHead({ title: 'Suporte · Admin' })

const admin = useAdmin()
const toast = useToast()

const list = ref<TicketListItem[]>([])
const loading = ref(true)
const filters = ref({ status: '', category: '' })

const active = ref<TicketDetail | null>(null)
const detailLoading = ref(false)
const reply = ref('')
const replyFile = ref<File | null>(null)
const sending = ref(false)
const updatingStatus = ref(false)

const STATUS_CLASS: Record<string, string> = {
  open: 'bg-amber-500/15 text-amber-300 border-amber-500/30',
  in_progress: 'bg-sky-500/15 text-sky-300 border-sky-500/30',
  resolved: 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30',
}
const statusClass = (s: string) => STATUS_CLASS[s] || 'bg-white/10 text-neutral-300 border-white/20'
const fmt = (iso: string) => new Date(iso).toLocaleString('pt-BR')

const loadList = async () => {
  loading.value = true
  try {
    list.value = await admin.ticketsList({
      status: filters.value.status || undefined,
      category: filters.value.category || undefined,
    })
  } catch {
    toast.error('Falha ao carregar chamados')
  } finally {
    loading.value = false
  }
}
onMounted(loadList)

const openTicket = async (id: number) => {
  detailLoading.value = true
  active.value = null
  reply.value = ''
  replyFile.value = null
  try {
    active.value = await admin.ticket(id)
  } catch {
    toast.error('Falha ao abrir o chamado')
  } finally {
    detailLoading.value = false
  }
}

const onReplyFile = (e: Event) => {
  replyFile.value = (e.target as HTMLInputElement).files?.[0] || null
}

const submitReply = async () => {
  if (!active.value || !reply.value.trim()) return
  sending.value = true
  try {
    const fd = new FormData()
    fd.append('body', reply.value.trim())
    if (replyFile.value) fd.append('file', replyFile.value)
    await admin.ticketReply(active.value.id, fd)
    reply.value = ''
    replyFile.value = null
    active.value = await admin.ticket(active.value.id)
    await loadList()
    toast.success('Resposta enviada')
  } catch {
    toast.error('Falha ao responder')
  } finally {
    sending.value = false
  }
}

const setStatus = async (status: string) => {
  if (!active.value) return
  updatingStatus.value = true
  try {
    await admin.ticketSetStatus(active.value.id, status)
    active.value.status = status
    active.value.status_label = { open: 'Aberto', in_progress: 'Em andamento', resolved: 'Resolvido' }[status] || status
    await loadList()
    toast.success('Status atualizado')
  } catch {
    toast.error('Falha ao atualizar status')
  } finally {
    updatingStatus.value = false
  }
}
</script>

<template>
  <div class="max-w-4xl mx-auto px-4 py-8">
    <header class="mb-6">
      <h1 class="text-2xl font-semibold tracking-tight flex items-center gap-2">
        <LifeBuoy class="w-6 h-6 text-orange-400" />
        Suporte
      </h1>
      <p class="text-sm text-neutral-500 mt-1">Chamados dos alunos. Responder um aberto o move para "em andamento".</p>
    </header>

    <!-- Filtros -->
    <div class="flex flex-wrap gap-3 mb-4">
      <select
        v-model="filters.status"
        class="px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-sm text-white focus:border-orange-500/50 focus:outline-none [&>option]:bg-neutral-900 [&>option]:text-white"
        @change="loadList"
      >
        <option value="">Todos os status</option>
        <option value="open">Aberto</option>
        <option value="in_progress">Em andamento</option>
        <option value="resolved">Resolvido</option>
      </select>
      <select
        v-model="filters.category"
        class="px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-sm text-white focus:border-orange-500/50 focus:outline-none [&>option]:bg-neutral-900 [&>option]:text-white"
        @change="loadList"
      >
        <option value="">Todas as categorias</option>
        <option v-for="c in TICKET_CATEGORIES" :key="c.value" :value="c.value">{{ c.label }}</option>
      </select>
    </div>

    <div v-if="loading" class="flex justify-center py-20">
      <Loader2 class="w-6 h-6 text-orange-500 animate-spin" />
    </div>
    <p v-else-if="!list.length" class="text-center text-neutral-500 py-20">Nenhum chamado.</p>

    <div v-else class="space-y-2">
      <button
        v-for="t in list"
        :key="t.id"
        type="button"
        class="w-full text-left rounded-lg border border-white/10 bg-white/5 hover:bg-white/[0.07] p-4 flex items-center gap-3"
        @click="openTicket(t.id)"
      >
        <div class="flex-1 min-w-0">
          <div class="flex items-center gap-2">
            <span class="text-sm font-medium text-white truncate">{{ t.category_label }}</span>
            <span class="text-xs text-neutral-500 shrink-0">#{{ t.id }}</span>
          </div>
          <p class="text-xs text-neutral-500 mt-0.5 truncate">
            {{ t.user_name || t.user_email }} · {{ t.last_message }}
          </p>
        </div>
        <span
          class="shrink-0 text-[10px] uppercase tracking-wider font-bold px-2 py-1 rounded-full border"
          :class="statusClass(t.status)"
        >{{ t.status_label }}</span>
      </button>
    </div>

    <!-- Modal: thread -->
    <AdminModal
      :open="!!active || detailLoading"
      :title="active ? `#${active.id} · ${active.category_label}` : 'Chamado'"
      size="lg"
      @close="active = null"
    >
      <div v-if="detailLoading" class="flex justify-center py-10">
        <Loader2 class="w-5 h-5 text-orange-500 animate-spin" />
      </div>

      <div v-else-if="active">
        <div class="flex items-center gap-2 mb-4 flex-wrap">
          <span class="text-xs text-neutral-400">{{ active.user_name || active.user_email }}</span>
          <span
            class="text-[10px] uppercase tracking-wider font-bold px-2 py-0.5 rounded-full border"
            :class="statusClass(active.status)"
          >{{ active.status_label }}</span>
          <span class="flex-1" />
          <button
            type="button"
            :disabled="updatingStatus || active.status === 'in_progress' || active.status === 'resolved'"
            class="px-3 py-1.5 text-xs font-bold uppercase tracking-wider rounded-lg border border-sky-500/30 text-sky-300 hover:bg-sky-500/10 disabled:opacity-40"
            @click="setStatus('in_progress')"
          >
            Em andamento
          </button>
          <button
            type="button"
            :disabled="updatingStatus || active.status === 'resolved'"
            class="px-3 py-1.5 text-xs font-bold uppercase tracking-wider rounded-lg border border-emerald-500/30 text-emerald-300 hover:bg-emerald-500/10 disabled:opacity-40"
            @click="setStatus('resolved')"
          >
            Resolver
          </button>
        </div>

        <div class="space-y-3 max-h-[45vh] overflow-y-auto pr-1">
          <div
            v-for="m in active.messages"
            :key="m.id"
            class="rounded-lg border p-3"
            :class="m.is_staff ? 'border-orange-500/20 bg-orange-500/[0.06]' : 'border-white/10 bg-white/5'"
          >
            <div class="flex items-center gap-2 flex-wrap mb-1">
              <span class="text-sm font-medium text-white">{{ m.author_name }}</span>
              <span
                v-if="m.is_staff"
                class="text-[10px] uppercase tracking-wider font-bold text-orange-300 bg-orange-500/10 px-1.5 py-0.5 rounded"
              >Staff</span>
              <span class="text-[11px] text-neutral-500">{{ fmt(m.created_at) }}</span>
            </div>
            <p class="text-sm text-neutral-200 whitespace-pre-wrap break-words">{{ m.body }}</p>
            <TicketAttachmentViewer v-if="m.attachment_url" :url="m.attachment_url" />
          </div>
        </div>

        <!-- Responder (bloqueado quando finalizado) -->
        <div v-if="active.status !== 'resolved'" class="mt-4 space-y-2">
          <textarea
            v-model="reply"
            rows="3"
            placeholder="Responder ao aluno..."
            class="w-full px-3 py-2.5 bg-white/5 border border-white/10 rounded-lg text-sm text-white placeholder:text-neutral-500 focus:border-orange-500/50 focus:outline-none resize-y"
          />
          <div class="flex items-center justify-between gap-2 flex-wrap">
            <label class="inline-flex items-center gap-2 text-xs text-neutral-400 cursor-pointer hover:text-white">
              <Paperclip class="w-3.5 h-3.5" />
              <span>{{ replyFile ? replyFile.name : 'Anexar' }}</span>
              <input type="file" accept="image/*,application/pdf" class="hidden" @change="onReplyFile">
            </label>
            <button
              type="button"
              :disabled="sending || !reply.trim()"
              class="inline-flex items-center gap-2 px-4 py-2 bg-orange-500 hover:bg-orange-400 disabled:opacity-50 text-white font-bold uppercase tracking-wider text-xs rounded-lg"
              @click="submitReply"
            >
              <Loader2 v-if="sending" class="w-4 h-4 animate-spin" />
              <Send v-else class="w-4 h-4" />
              Responder
            </button>
          </div>
        </div>
        <p v-else class="mt-4 text-center text-xs text-neutral-500">
          Chamado finalizado, não aceita novas mensagens.
        </p>
      </div>
    </AdminModal>
  </div>
</template>
