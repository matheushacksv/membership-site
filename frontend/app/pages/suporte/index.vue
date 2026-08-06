<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ArrowLeft, LifeBuoy, Loader2, Paperclip, Plus, Send, X } from 'lucide-vue-next'
import {
  TICKET_CATEGORIES,
  type TicketDetail,
  type TicketListItem,
} from '~/composables/useTickets'

useHead({ title: 'Suporte' })

const tickets = useTickets()
const toast = useToast()

const list = ref<TicketListItem[]>([])
const loading = ref(true)
const selected = ref<TicketDetail | null>(null)
const view = ref<'list' | 'new' | 'detail'>('list')

// --- Novo chamado ---
const form = ref({ category: '', body: '' })
const file = ref<File | null>(null)
const submitting = ref(false)

// --- Resposta na thread ---
const reply = ref('')
const replyFile = ref<File | null>(null)
const sending = ref(false)

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
    list.value = await tickets.listMine()
  } catch {
    toast.error('Falha ao carregar seus chamados')
  } finally {
    loading.value = false
  }
}
onMounted(loadList)

const openDetail = async (id: number) => {
  view.value = 'detail'
  selected.value = null
  reply.value = ''
  replyFile.value = null
  try {
    selected.value = await tickets.get(id)
  } catch {
    toast.error('Falha ao abrir o chamado')
    view.value = 'list'
  }
}

const onFile = (e: Event, target: 'new' | 'reply') => {
  const f = (e.target as HTMLInputElement).files?.[0] || null
  if (target === 'new') file.value = f
  else replyFile.value = f
}

const submitNew = async () => {
  if (!form.value.category) return toast.error('Escolha uma categoria')
  if (!form.value.body.trim()) return toast.error('Descreva o problema')
  submitting.value = true
  try {
    const fd = new FormData()
    fd.append('category', form.value.category)
    fd.append('body', form.value.body.trim())
    if (file.value) fd.append('file', file.value)
    const created = await tickets.create(fd)
    form.value = { category: '', body: '' }
    file.value = null
    await loadList()
    selected.value = created
    view.value = 'detail'
    toast.success('Chamado aberto!')
  } catch {
    toast.error('Falha ao abrir o chamado')
  } finally {
    submitting.value = false
  }
}

const submitReply = async () => {
  if (!selected.value || !reply.value.trim()) return
  sending.value = true
  try {
    const fd = new FormData()
    fd.append('body', reply.value.trim())
    if (replyFile.value) fd.append('file', replyFile.value)
    await tickets.addMessage(selected.value.id, fd)
    reply.value = ''
    replyFile.value = null
    selected.value = await tickets.get(selected.value.id)
    await loadList()
  } catch {
    toast.error('Falha ao enviar mensagem')
  } finally {
    sending.value = false
  }
}

const isResolved = computed(() => selected.value?.status === 'resolved')
</script>

<template>
  <div class="max-w-3xl mx-auto px-4 md:px-6 py-8">
    <header class="mb-6 flex items-center justify-between gap-3">
      <h1 class="text-2xl font-semibold tracking-tight flex items-center gap-2">
        <LifeBuoy class="w-6 h-6 text-orange-400" />
        Suporte
      </h1>
      <button
        v-if="view === 'list'"
        type="button"
        class="inline-flex items-center gap-1.5 px-4 py-2 bg-orange-500 hover:bg-orange-400 text-white font-bold uppercase tracking-wider text-xs rounded-lg"
        @click="view = 'new'"
      >
        <Plus class="w-4 h-4" /> Novo chamado
      </button>
      <button
        v-else
        type="button"
        class="inline-flex items-center gap-1.5 text-sm text-neutral-400 hover:text-white"
        @click="view = 'list'; selected = null"
      >
        <ArrowLeft class="w-4 h-4" /> Voltar
      </button>
    </header>

    <!-- LISTA -->
    <div v-if="view === 'list'">
      <div v-if="loading" class="flex justify-center py-20">
        <Loader2 class="w-6 h-6 text-orange-500 animate-spin" />
      </div>
      <p v-else-if="!list.length" class="text-center text-neutral-500 py-20">
        Você ainda não abriu nenhum chamado.
      </p>
      <div v-else class="space-y-2">
        <button
          v-for="t in list"
          :key="t.id"
          type="button"
          class="w-full text-left rounded-lg border border-white/10 bg-white/5 hover:bg-white/[0.07] p-4 flex items-center gap-3"
          @click="openDetail(t.id)"
        >
          <div class="flex-1 min-w-0">
            <p class="text-sm font-medium text-white truncate">{{ t.category_label }}</p>
            <p class="text-xs text-neutral-500 mt-0.5">#{{ t.id }} · atualizado {{ fmt(t.updated_at) }}</p>
          </div>
          <span
            class="shrink-0 text-[10px] uppercase tracking-wider font-bold px-2 py-1 rounded-full border"
            :class="statusClass(t.status)"
          >{{ t.status_label }}</span>
        </button>
      </div>
    </div>

    <!-- NOVO -->
    <div v-else-if="view === 'new'" class="rounded-xl border border-white/10 bg-white/5 p-5 space-y-4">
      <div>
        <label class="block text-xs font-bold uppercase tracking-wider text-neutral-400 mb-1.5">Categoria</label>
        <select
          v-model="form.category"
          class="w-full px-3 py-2.5 bg-white/5 border border-white/10 rounded-lg text-sm text-white focus:border-orange-500/50 focus:outline-none [&>option]:bg-neutral-900 [&>option]:text-white"
        >
          <option value="" disabled>Selecione...</option>
          <option v-for="c in TICKET_CATEGORIES" :key="c.value" :value="c.value">{{ c.label }}</option>
        </select>
      </div>
      <div>
        <label class="block text-xs font-bold uppercase tracking-wider text-neutral-400 mb-1.5">Descrição</label>
        <textarea
          v-model="form.body"
          rows="5"
          placeholder="Descreva o que está acontecendo com o máximo de detalhes..."
          class="w-full px-3 py-2.5 bg-white/5 border border-white/10 rounded-lg text-sm text-white placeholder:text-neutral-500 focus:border-orange-500/50 focus:outline-none resize-y"
        />
      </div>
      <div>
        <label class="inline-flex items-center gap-2 text-sm text-neutral-300 cursor-pointer hover:text-white">
          <Paperclip class="w-4 h-4" />
          <span>{{ file ? file.name : 'Anexar print (opcional)' }}</span>
          <input type="file" accept="image/*,application/pdf" class="hidden" @change="onFile($event, 'new')">
        </label>
        <button v-if="file" type="button" class="ml-2 text-neutral-500 hover:text-red-300" @click="file = null">
          <X class="w-3.5 h-3.5" />
        </button>
      </div>
      <div class="flex justify-end">
        <button
          type="button"
          :disabled="submitting"
          class="inline-flex items-center gap-2 px-5 py-2.5 bg-orange-500 hover:bg-orange-400 disabled:opacity-50 text-white font-bold uppercase tracking-wider text-xs rounded-lg"
          @click="submitNew"
        >
          <Loader2 v-if="submitting" class="w-4 h-4 animate-spin" />
          Enviar chamado
        </button>
      </div>
    </div>

    <!-- DETALHE -->
    <div v-else-if="view === 'detail'">
      <div v-if="!selected" class="flex justify-center py-20">
        <Loader2 class="w-6 h-6 text-orange-500 animate-spin" />
      </div>
      <div v-else>
        <div class="flex items-center gap-3 mb-4">
          <span class="text-sm font-medium text-white">{{ selected.category_label }}</span>
          <span
            class="text-[10px] uppercase tracking-wider font-bold px-2 py-1 rounded-full border"
            :class="statusClass(selected.status)"
          >{{ selected.status_label }}</span>
          <span class="text-xs text-neutral-500">#{{ selected.id }}</span>
        </div>

        <div class="space-y-3">
          <div
            v-for="m in selected.messages"
            :key="m.id"
            class="rounded-lg border p-3"
            :class="m.is_staff ? 'border-orange-500/20 bg-orange-500/[0.06]' : 'border-white/10 bg-white/5'"
          >
            <div class="flex items-center gap-2 flex-wrap mb-1">
              <span class="text-sm font-medium text-white">{{ m.author_name || 'Você' }}</span>
              <span
                v-if="m.is_staff"
                class="text-[10px] uppercase tracking-wider font-bold text-orange-300 bg-orange-500/10 px-1.5 py-0.5 rounded"
              >Suporte</span>
              <span class="text-[11px] text-neutral-500">{{ fmt(m.created_at) }}</span>
            </div>
            <p class="text-sm text-neutral-200 whitespace-pre-wrap break-words">{{ m.body }}</p>
            <TicketAttachmentViewer v-if="m.attachment_url" :url="m.attachment_url" />
          </div>
        </div>

        <!-- Responder -->
        <div v-if="!isResolved" class="mt-4 space-y-2">
          <textarea
            v-model="reply"
            rows="3"
            placeholder="Escreva uma mensagem..."
            class="w-full px-3 py-2.5 bg-white/5 border border-white/10 rounded-lg text-sm text-white placeholder:text-neutral-500 focus:border-orange-500/50 focus:outline-none resize-y"
          />
          <div class="flex items-center justify-between">
            <label class="inline-flex items-center gap-2 text-xs text-neutral-400 cursor-pointer hover:text-white">
              <Paperclip class="w-3.5 h-3.5" />
              <span>{{ replyFile ? replyFile.name : 'Anexar' }}</span>
              <input type="file" accept="image/*,application/pdf" class="hidden" @change="onFile($event, 'reply')">
            </label>
            <button
              type="button"
              :disabled="sending || !reply.trim()"
              class="inline-flex items-center gap-2 px-4 py-2 bg-orange-500 hover:bg-orange-400 disabled:opacity-50 text-white font-bold uppercase tracking-wider text-xs rounded-lg"
              @click="submitReply"
            >
              <Loader2 v-if="sending" class="w-4 h-4 animate-spin" />
              <Send v-else class="w-4 h-4" />
              Enviar
            </button>
          </div>
        </div>

        <!-- Finalizado: terminal, não reabre -->
        <div v-else class="mt-4 rounded-lg border border-white/10 bg-white/5 p-4 text-center">
          <p class="text-sm text-neutral-400">Este chamado foi finalizado.</p>
          <button
            type="button"
            class="mt-2 inline-flex items-center gap-1.5 px-4 py-2 bg-orange-500 hover:bg-orange-400 text-white font-bold uppercase tracking-wider text-xs rounded-lg"
            @click="view = 'new'; selected = null"
          >
            <Plus class="w-4 h-4" /> Abrir novo chamado
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
