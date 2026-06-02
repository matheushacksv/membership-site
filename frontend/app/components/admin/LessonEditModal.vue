<script setup lang="ts">
import { Loader2, Paperclip, Upload, Trash2, FileText } from 'lucide-vue-next'
import type { AttachmentItem, LessonItem } from '~/composables/useAdmin'

const props = defineProps<{ open: boolean; lessonId: number | null }>()
const emit = defineEmits<{ close: []; saved: [lesson: LessonItem] }>()

const admin = useAdmin()
const toast = useToast()

const loading = ref(false)
const saving = ref(false)
const attachments = ref<AttachmentItem[]>([])
const uploading = ref(false)
const fileInput = ref<HTMLInputElement | null>(null)

const form = reactive({
  name: '',
  description: '',
  video_provider: '' as string | null,
  video_id: '',
  content: '',
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
      form.description = l.description || ''
      form.video_provider = l.video_provider || ''
      form.video_id = l.video_id || ''
      form.content = l.content || ''
      form.is_published = l.is_published
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
  const file = (e.target as HTMLInputElement).files?.[0]
  if (!file || !props.lessonId) return
  if (file.size > 50 * 1024 * 1024) {
    toast.error('Máximo 50MB')
    return
  }
  uploading.value = true
  try {
    const att = await admin.uploadAttachment(props.lessonId, file)
    attachments.value = [...attachments.value, att]
    toast.success('Anexo enviado')
  } catch (e: any) {
    toast.error(e?.data?.detail || 'Falha no upload')
  } finally {
    uploading.value = false
    if (fileInput.value) fileInput.value.value = ''
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
      description: form.description || null,
      video_provider: form.video_provider || null,
      video_id: form.video_id || null,
      content: form.content || null,
      is_published: form.is_published,
    })
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

      <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
        <div>
          <label class="block text-xs font-bold uppercase tracking-wider text-neutral-400 mb-1.5">Provedor de vídeo</label>
          <select
            v-model="form.video_provider"
            class="w-full px-4 py-2.5 bg-white/5 border border-white/10 rounded-lg text-sm text-white focus:border-orange-500/50 focus:outline-none"
          >
            <option value="" class="bg-black">— sem vídeo —</option>
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
        <label class="block text-xs font-bold uppercase tracking-wider text-neutral-400 mb-1.5">Conteúdo (texto)</label>
        <textarea
          v-model="form.content"
          rows="6"
          class="w-full px-4 py-2.5 bg-white/5 border border-white/10 rounded-lg text-sm text-white focus:border-orange-500/50 focus:outline-none resize-y"
        />
      </div>

      <div class="pt-2 border-t border-white/5">
        <div class="flex items-center justify-between mb-2">
          <label class="inline-flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-neutral-400">
            <Paperclip class="w-3.5 h-3.5" />
            Anexos
          </label>
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
          <input
            ref="fileInput"
            type="file"
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
  </AdminModal>
</template>
