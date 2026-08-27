<script setup lang="ts">
import { Loader2, Paperclip, Upload, Trash2, FileText, FolderOpen, Video, ListChecks, BarChart3 } from 'lucide-vue-next'
import type { AdminQuizQuestion, AttachmentItem, LessonItem } from '~/composables/useAdmin'

const props = defineProps<{ open: boolean; lessonId: number | null }>()
const emit = defineEmits<{ close: []; saved: [lesson: LessonItem] }>()

const admin = useAdmin()
const toast = useToast()

const loading = ref(false)
const saving = ref(false)
const attachments = ref<AttachmentItem[]>([])
const uploading = ref(false)
const fileInput = ref<HTMLInputElement | null>(null)
const pickerOpen = ref(false)
const linking = ref(false)
const questions = ref<AdminQuizQuestion[]>([])
const responsesOpen = ref(false)

const form = reactive({
  name: '',
  kind: 'video' as 'video' | 'quiz',
  description: '',
  video_provider: '' as string | null,
  video_id: '',
  content: '',
  allow_retake: true,
  time_limit_min: 0, // exercício: tempo em minutos (0 = sem tempo); vira segundos no save
  duration_min: 0, // vídeo: duração em minutos (Panda preenche sozinho; editável); vira segundos no save
  is_published: true,
})

const loadAttachments = async (id: number) => {
  try {
    attachments.value = await admin.listAttachments(id)
  } catch {
    attachments.value = []
  }
}

watch(
  () => props.lessonId,
  async (id) => {
    if (!id || !props.open) return
    loading.value = true
    try {
      const l = await admin.getLesson(id)
      form.name = l.name
      form.kind = l.kind === 'quiz' ? 'quiz' : 'video'
      form.description = l.description || ''
      form.video_provider = l.video_provider || ''
      form.video_id = l.video_id || ''
      form.content = l.content || ''
      form.allow_retake = l.allow_retake ?? true
      form.time_limit_min = Math.round((l.time_limit_seconds || 0) / 60)
      form.duration_min = Math.round((l.duration_seconds || 0) / 60)
      form.is_published = l.is_published
      questions.value = form.kind === 'quiz' ? await admin.getLessonQuiz(id) : []
      await loadAttachments(id)
    } catch (e: any) {
      toast.error(e?.data?.detail || 'Falha ao carregar')
    } finally {
      loading.value = false
    }
  },
  { immediate: true }
)

const onPickFile = async (e: Event) => {
  const picked = Array.from((e.target as HTMLInputElement).files ?? [])
  if (!picked.length || !props.lessonId) return

  // Upload sequencial: o endpoint calcula `order` via Max() a cada chamada;
  // paralelo poderia gerar `order` duplicado. Mantém a ordem de seleção.
  uploading.value = true
  let ok = 0
  let failed = 0
  try {
    for (const file of picked) {
      if (file.size > 50 * 1024 * 1024) {
        toast.error(`${file.name}: máximo 50MB`)
        failed++
        continue
      }
      try {
        const att = await admin.uploadAttachment(props.lessonId, file)
        attachments.value = [...attachments.value, att]
        ok++
      } catch (err: any) {
        toast.error(`${file.name}: ${err?.data?.detail || 'falha no upload'}`)
        failed++
      }
    }
    if (ok && !failed) toast.success(ok === 1 ? 'Anexo enviado' : `${ok} anexos enviados`)
    else if (ok) toast.success(`${ok} enviado(s), ${failed} com erro`)
  } finally {
    uploading.value = false
    if (fileInput.value) fileInput.value.value = ''
  }
}

const onPickExisting = async (ids: number[]) => {
  if (!ids.length || !props.lessonId) return

  // Sequencial pelo mesmo motivo do upload: o endpoint calcula `order` via Max().
  linking.value = true
  let ok = 0
  let failed = 0
  try {
    for (const id of ids) {
      try {
        const att = await admin.linkAttachment(props.lessonId, id)
        attachments.value = [...attachments.value, att]
        ok++
      } catch (err: any) {
        toast.error(err?.data?.detail || 'Falha ao adicionar anexo')
        failed++
      }
    }
    if (ok && !failed) toast.success(ok === 1 ? 'Anexo adicionado' : `${ok} anexos adicionados`)
    else if (ok) toast.success(`${ok} adicionado(s), ${failed} com erro`)
  } finally {
    linking.value = false
  }
}

const removeAttachment = async (id: number) => {
  if (!confirm('Deletar anexo?')) return
  const prev = attachments.value
  attachments.value = attachments.value.filter((a) => a.id !== id)
  try {
    await admin.deleteAttachment(id)
    toast.success('Anexo deletado')
  } catch {
    attachments.value = prev
    toast.error('Falha ao deletar')
  }
}

const fmtSize = (b: number) => {
  if (b < 1024) return `${b} B`
  if (b < 1024 * 1024) return `${(b / 1024).toFixed(1)} KB`
  return `${(b / 1024 / 1024).toFixed(1)} MB`
}

const save = async () => {
  if (!props.lessonId) return
  saving.value = true
  try {
    const updated = await admin.updateLesson(props.lessonId, {
      name: form.name,
      kind: form.kind,
      description: form.description || null,
      video_provider: form.video_provider || null,
      video_id: form.video_id || null,
      content: form.content || null,
      allow_retake: form.allow_retake,
      time_limit_seconds: Math.max(0, Math.round(form.time_limit_min || 0)) * 60,
      duration_seconds: Math.max(0, Math.round(form.duration_min || 0)) * 60,
      is_published: form.is_published,
    })
    // Perguntas vão num PUT separado; o backend valida (≥2 opções, gabarito no range)
    // e devolve 422 → cai no catch e vira toast.
    if (form.kind === 'quiz') await admin.saveLessonQuiz(props.lessonId, questions.value)
    toast.success('Aula salva')
    emit('saved', updated)
    emit('close')
  } catch (e: any) {
    toast.error(e?.data?.detail || 'Falha ao salvar')
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <AdminModal :open="open" title="Editar aula" size="lg" @close="emit('close')">
    <div v-if="loading" class="flex justify-center py-10">
      <Loader2 class="w-6 h-6 text-orange-500 animate-spin" />
    </div>
    <form v-else class="space-y-4" @submit.prevent="save">
      <div>
        <label class="block text-xs font-bold uppercase tracking-wider text-neutral-400 mb-1.5">Nome</label>
        <input
          v-model="form.name"
          type="text"
          required
          class="w-full px-4 py-2.5 bg-white/5 border border-white/10 rounded-lg text-sm text-white focus:border-orange-500/50 focus:outline-none"
        >
      </div>

      <div>
        <label class="block text-xs font-bold uppercase tracking-wider text-neutral-400 mb-1.5">Descrição</label>
        <input
          v-model="form.description"
          type="text"
          class="w-full px-4 py-2.5 bg-white/5 border border-white/10 rounded-lg text-sm text-white focus:border-orange-500/50 focus:outline-none"
        >
      </div>

      <div>
        <label class="block text-xs font-bold uppercase tracking-wider text-neutral-400 mb-1.5">Tipo de aula</label>
        <div class="inline-flex rounded-lg border border-white/10 overflow-hidden">
          <button
            type="button"
            class="inline-flex items-center gap-1.5 px-4 py-2 text-xs font-bold uppercase tracking-wider"
            :class="form.kind === 'video' ? 'bg-orange-500 text-white' : 'text-neutral-400 hover:text-white'"
            @click="form.kind = 'video'"
          >
            <Video class="w-3.5 h-3.5" />
            Vídeo
          </button>
          <button
            type="button"
            class="inline-flex items-center gap-1.5 px-4 py-2 text-xs font-bold uppercase tracking-wider"
            :class="form.kind === 'quiz' ? 'bg-orange-500 text-white' : 'text-neutral-400 hover:text-white'"
            @click="form.kind = 'quiz'"
          >
            <ListChecks class="w-3.5 h-3.5" />
            Exercício
          </button>
        </div>
      </div>

      <div v-if="form.kind === 'video'" class="space-y-4">
      <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
        <div>
          <label class="block text-xs font-bold uppercase tracking-wider text-neutral-400 mb-1.5">Provedor de vídeo</label>
          <select
            v-model="form.video_provider"
            class="w-full px-4 py-2.5 bg-white/5 border border-white/10 rounded-lg text-sm text-white focus:border-orange-500/50 focus:outline-none"
          >
            <option value="" class="bg-black">sem vídeo</option>
            <option value="youtube" class="bg-black">YouTube</option>
            <option value="vimeo" class="bg-black">Vimeo</option>
            <option value="panda" class="bg-black">Panda Video</option>
          </select>
        </div>
        <div>
          <label class="block text-xs font-bold uppercase tracking-wider text-neutral-400 mb-1.5">ID do vídeo</label>
          <input
            v-model="form.video_id"
            type="text"
            placeholder="Ex: dQw4w9WgXcQ"
            class="w-full px-4 py-2.5 bg-white/5 border border-white/10 rounded-lg text-sm text-white focus:border-orange-500/50 focus:outline-none"
          >
        </div>
      </div>

      <div>
        <label class="block text-xs font-bold uppercase tracking-wider text-neutral-400 mb-1.5">Duração (min)</label>
        <input
          v-model.number="form.duration_min"
          type="number"
          min="0"
          class="w-32 px-4 py-2.5 bg-white/5 border border-white/10 rounded-lg text-sm text-white focus:border-orange-500/50 focus:outline-none"
        >
        <p class="text-[11px] text-neutral-500 mt-1">
          Vídeo do Panda preenche sozinho ao salvar. Edite para ajustar manualmente. Base da carga horária do certificado.
        </p>
      </div>

      <div>
        <label class="block text-xs font-bold uppercase tracking-wider text-neutral-400 mb-1.5">Conteúdo (texto)</label>
        <AdminRichTextEditor v-model="form.content" />
      </div>
      </div>

      <div v-else class="space-y-2">
        <div class="flex items-center justify-between">
          <label class="text-xs font-bold uppercase tracking-wider text-neutral-400">Perguntas</label>
          <button
            type="button"
            class="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-bold uppercase tracking-wider text-neutral-300 hover:text-white hover:bg-white/5 border border-white/15 rounded-md"
            @click="responsesOpen = true"
          >
            <BarChart3 class="w-3 h-3" />
            Ver respostas
          </button>
        </div>
        <label class="flex items-center gap-2 text-sm text-neutral-400">
          <input v-model="form.allow_retake" type="checkbox" class="accent-orange-500">
          Permitir refazer <span class="text-neutral-600">(desligado = 1 tentativa)</span>
        </label>
        <label class="flex items-center gap-2 text-sm text-neutral-400">
          <span>Tempo limite</span>
          <input
            v-model.number="form.time_limit_min"
            type="number"
            min="0"
            class="w-20 px-2 py-1 bg-white/5 border border-white/10 rounded-md text-sm text-white focus:border-orange-500/50 focus:outline-none"
          >
          <span class="text-neutral-600">min (0 = sem tempo; ao esgotar vira tentativa falha)</span>
        </label>
        <AdminQuizEditor v-model="questions" />
      </div>

      <div class="pt-2 border-t border-white/5">
        <div class="flex items-center justify-between mb-2">
          <label class="inline-flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-neutral-400">
            <Paperclip class="w-3.5 h-3.5" />
            Anexos
          </label>
          <div class="flex items-center gap-2">
            <button
              type="button"
              :disabled="linking"
              class="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-bold uppercase tracking-wider text-neutral-300 hover:text-white hover:bg-white/5 border border-white/15 rounded-md disabled:opacity-50"
              @click="pickerOpen = true"
            >
              <Loader2 v-if="linking" class="w-3 h-3 animate-spin" />
              <FolderOpen v-else class="w-3 h-3" />
              Escolher
            </button>
            <button
              type="button"
              :disabled="uploading"
              class="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-bold uppercase tracking-wider text-orange-300 hover:text-orange-200 hover:bg-orange-500/10 border border-orange-500/30 rounded-md disabled:opacity-50"
              @click="fileInput?.click()"
            >
              <Loader2 v-if="uploading" class="w-3 h-3 animate-spin" />
              <Upload v-else class="w-3 h-3" />
              Enviar
            </button>
          </div>
          <input
            ref="fileInput"
            type="file"
            multiple
            class="hidden"
            @change="onPickFile"
          >
        </div>
        <div v-if="attachments.length" class="space-y-1.5">
          <div
            v-for="a in attachments"
            :key="a.id"
            class="flex items-center gap-2 px-3 py-2 bg-white/[0.02] border border-white/5 rounded-md text-sm"
          >
            <FileText class="w-3.5 h-3.5 text-neutral-500 shrink-0" />
            <a
              :href="a.file_url"
              target="_blank"
              rel="noopener noreferrer"
              class="flex-1 text-white hover:text-orange-300 truncate"
            >
              {{ a.title }}
            </a>
            <span class="text-[10px] text-neutral-500 shrink-0">{{ fmtSize(a.size_bytes) }}</span>
            <button
              type="button"
              class="p-1 rounded text-neutral-500 hover:text-red-400"
              @click="removeAttachment(a.id)"
            >
              <Trash2 class="w-3 h-3" />
            </button>
          </div>
        </div>
        <p v-else class="text-xs text-neutral-600 italic">Nenhum anexo</p>
      </div>

      <label class="flex items-center gap-2 text-sm text-neutral-400">
        <input v-model="form.is_published" type="checkbox" class="accent-orange-500">
        Publicada
      </label>

      <div class="flex justify-end gap-2 pt-4 border-t border-white/5">
        <button type="button" class="px-4 py-2 text-sm text-neutral-400 hover:text-white" @click="emit('close')">Cancelar</button>
        <button
          type="submit"
          :disabled="saving"
          class="inline-flex items-center gap-2 px-5 py-2 bg-orange-500 hover:bg-orange-400 disabled:opacity-50 text-white font-bold uppercase tracking-wider text-xs rounded-lg"
        >
          <Loader2 v-if="saving" class="w-3.5 h-3.5 animate-spin" />
          Salvar
        </button>
      </div>
    </form>

    <AdminAttachmentPickerModal
      :open="pickerOpen"
      @close="pickerOpen = false"
      @pick="onPickExisting"
    />

    <AdminQuizResponsesModal
      :open="responsesOpen"
      :lesson-id="lessonId"
      @close="responsesOpen = false"
    />
  </AdminModal>
</template>
