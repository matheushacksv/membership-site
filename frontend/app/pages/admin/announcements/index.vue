<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ImagePlus, Loader2, Mail, Megaphone, Pencil, Plus, Trash2, X } from 'lucide-vue-next'
import {
  ANNOUNCEMENT_KINDS,
  type AnnouncementAdmin,
} from '~/composables/useAnnouncements'

definePageMeta({ layout: 'admin', middleware: 'admin' })
useHead({ title: 'Informativos · Admin' })

const admin = useAdmin()
const toast = useToast()

const list = ref<AnnouncementAdmin[]>([])
const loading = ref(true)

const showForm = ref(false)
const editing = ref<AnnouncementAdmin | null>(null)
const form = ref({ title: '', body: '', kind: 'info', is_published: false })
const imageFile = ref<File | null>(null)
const imagePreview = ref<string | null>(null)
const removeImage = ref(false)
const saving = ref(false)
const busyId = ref<number | null>(null)

const fmt = (iso: string | null) => (iso ? new Date(iso).toLocaleString('pt-BR') : '')
// body é HTML rico → tira as tags pro preview curto da lista.
const stripHtml = (html: string) => html.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim()

const loadList = async () => {
  loading.value = true
  try {
    list.value = await admin.announcementsList()
  } catch {
    toast.error('Falha ao carregar informativos')
  } finally {
    loading.value = false
  }
}
onMounted(loadList)

const resetImage = () => {
  imageFile.value = null
  imagePreview.value = null
  removeImage.value = false
}
const openCreate = () => {
  editing.value = null
  form.value = { title: '', body: '', kind: 'info', is_published: false }
  resetImage()
  showForm.value = true
}
const openEdit = (a: AnnouncementAdmin) => {
  editing.value = a
  form.value = { title: a.title, body: a.body, kind: a.kind, is_published: a.is_published }
  resetImage()
  imagePreview.value = a.image_url
  showForm.value = true
}

const onImage = (e: Event) => {
  const f = (e.target as HTMLInputElement).files?.[0] || null
  if (!f) return
  imageFile.value = f
  imagePreview.value = URL.createObjectURL(f)
  removeImage.value = false
}
const clearImage = () => {
  imageFile.value = null
  imagePreview.value = null
  removeImage.value = true // marca remoção da imagem já salva (ignorado no create)
}

const save = async () => {
  if (!form.value.title.trim() || !form.value.body.trim()) return toast.error('Preencha título e texto')
  saving.value = true
  try {
    const fd = new FormData()
    fd.append('title', form.value.title.trim())
    fd.append('body', form.value.body.trim())
    fd.append('kind', form.value.kind)
    fd.append('is_published', String(form.value.is_published))
    if (imageFile.value) fd.append('file', imageFile.value)
    if (editing.value && removeImage.value) fd.append('remove_image', 'true')
    if (editing.value) await admin.announcementUpdate(editing.value.id, fd)
    else await admin.announcementCreate(fd)
    showForm.value = false
    await loadList()
    toast.success('Informativo salvo')
  } catch {
    toast.error('Falha ao salvar')
  } finally {
    saving.value = false
  }
}

const sendEmail = async (a: AnnouncementAdmin) => {
  // Broadcast é irreversível (não dá pra "desenviar") — confirma antes.
  if (!confirm(`Enviar "${a.title}" por email para TODOS os alunos ativos? Isso não pode ser desfeito.`)) return
  busyId.value = a.id
  try {
    await admin.announcementSendEmail(a.id)
    await loadList()
    toast.success('Email enfileirado para envio')
  } catch (e: any) {
    toast.error(e?.data?.detail || 'Falha ao enviar email')
  } finally {
    busyId.value = null
  }
}

const remove = async (a: AnnouncementAdmin) => {
  if (!confirm(`Excluir o informativo "${a.title}"?`)) return
  busyId.value = a.id
  try {
    await admin.announcementDelete(a.id)
    await loadList()
    toast.success('Informativo excluído')
  } catch {
    toast.error('Falha ao excluir')
  } finally {
    busyId.value = null
  }
}
</script>

<template>
  <div class="max-w-4xl mx-auto px-4 py-8">
    <header class="mb-6 flex items-center justify-between gap-3">
      <div>
        <h1 class="text-2xl font-semibold tracking-tight flex items-center gap-2">
          <Megaphone class="w-6 h-6 text-orange-400" />
          Informativos
        </h1>
        <p class="text-sm text-neutral-500 mt-1">Avisos de downtime, mudanças e novidades. Aparecem no sino do aluno; opcionalmente por email.</p>
      </div>
      <button
        type="button"
        class="inline-flex items-center gap-1.5 px-4 py-2 bg-orange-500 hover:bg-orange-400 text-white font-bold uppercase tracking-wider text-xs rounded-lg shrink-0"
        @click="openCreate"
      >
        <Plus class="w-4 h-4" /> Novo
      </button>
    </header>

    <div v-if="loading" class="flex justify-center py-20">
      <Loader2 class="w-6 h-6 text-orange-500 animate-spin" />
    </div>
    <p v-else-if="!list.length" class="text-center text-neutral-500 py-20">Nenhum informativo ainda.</p>

    <div v-else class="space-y-2">
      <div
        v-for="a in list"
        :key="a.id"
        class="rounded-lg border border-white/10 bg-white/5 p-4 flex items-start gap-3"
      >
        <img v-if="a.image_url" :src="a.image_url" alt="" class="w-12 h-12 rounded-lg object-cover border border-white/10 shrink-0">
        <div class="flex-1 min-w-0">
          <div class="flex items-center gap-2 flex-wrap">
            <span class="text-sm font-medium text-white truncate">{{ a.title }}</span>
            <span class="text-[10px] uppercase tracking-wider font-bold px-2 py-0.5 rounded-full border border-white/15 text-neutral-300">{{ a.kind_label }}</span>
            <span
              v-if="a.is_published"
              class="text-[10px] uppercase tracking-wider font-bold px-2 py-0.5 rounded-full border border-emerald-500/30 bg-emerald-500/15 text-emerald-300"
            >Publicado</span>
            <span
              v-else
              class="text-[10px] uppercase tracking-wider font-bold px-2 py-0.5 rounded-full border border-amber-500/30 bg-amber-500/15 text-amber-300"
            >Rascunho</span>
            <span
              v-if="a.email_sent_at"
              class="text-[10px] uppercase tracking-wider font-bold px-2 py-0.5 rounded-full border border-sky-500/30 bg-sky-500/15 text-sky-300"
            >Email enviado</span>
          </div>
          <p class="text-xs text-neutral-500 mt-1 line-clamp-2 break-words">{{ stripHtml(a.body) }}</p>
          <p class="text-[10px] text-neutral-600 mt-1">{{ a.published_at ? `Publicado ${fmt(a.published_at)}` : `Criado ${fmt(a.created_at)}` }}</p>
        </div>

        <div class="flex items-center gap-1 shrink-0">
          <button
            type="button"
            title="Enviar email"
            :disabled="!a.is_published || !!a.email_sent_at || busyId === a.id"
            class="p-2 rounded-lg text-sky-300 hover:bg-sky-500/10 disabled:opacity-30 disabled:cursor-not-allowed"
            @click="sendEmail(a)"
          >
            <Loader2 v-if="busyId === a.id" class="w-4 h-4 animate-spin" />
            <Mail v-else class="w-4 h-4" />
          </button>
          <button
            type="button"
            title="Editar"
            class="p-2 rounded-lg text-neutral-300 hover:bg-white/10"
            @click="openEdit(a)"
          >
            <Pencil class="w-4 h-4" />
          </button>
          <button
            type="button"
            title="Excluir"
            :disabled="busyId === a.id"
            class="p-2 rounded-lg text-red-300 hover:bg-red-500/10 disabled:opacity-30"
            @click="remove(a)"
          >
            <Trash2 class="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>

    <!-- Form criar/editar -->
    <AdminModal
      :open="showForm"
      :title="editing ? 'Editar informativo' : 'Novo informativo'"
      size="lg"
      @close="showForm = false"
    >
      <div class="space-y-4">
        <div>
          <label class="block text-xs font-bold uppercase tracking-wider text-neutral-400 mb-1.5">Título</label>
          <input
            v-model="form.title"
            type="text"
            placeholder="Ex.: Manutenção programada"
            class="w-full px-3 py-2.5 bg-white/5 border border-white/10 rounded-lg text-sm text-white placeholder:text-neutral-500 focus:border-orange-500/50 focus:outline-none"
          >
        </div>
        <div>
          <label class="block text-xs font-bold uppercase tracking-wider text-neutral-400 mb-1.5">Tipo</label>
          <select
            v-model="form.kind"
            class="w-full px-3 py-2.5 bg-white/5 border border-white/10 rounded-lg text-sm text-white focus:border-orange-500/50 focus:outline-none [&>option]:bg-neutral-900 [&>option]:text-white"
          >
            <option v-for="k in ANNOUNCEMENT_KINDS" :key="k.value" :value="k.value">{{ k.label }}</option>
          </select>
        </div>
        <div>
          <label class="block text-xs font-bold uppercase tracking-wider text-neutral-400 mb-1.5">Texto</label>
          <AdminRichTextEditor v-model="form.body" enable-media :upload-image="admin.announcementUploadImage" />
          <p class="text-[11px] text-neutral-500 mt-1.5">Use a barra para inserir imagens e vídeos no meio do texto. No email o vídeo vira um link "Assistir".</p>
        </div>
        <div>
          <label class="block text-xs font-bold uppercase tracking-wider text-neutral-400 mb-1.5">Imagem (opcional)</label>
          <div v-if="imagePreview" class="relative inline-block">
            <img :src="imagePreview" alt="Prévia" class="max-h-40 rounded-lg border border-white/10">
            <button
              type="button"
              aria-label="Remover imagem"
              class="absolute -top-2 -right-2 p-1 rounded-full bg-neutral-800 border border-white/20 text-neutral-300 hover:text-red-300"
              @click="clearImage"
            >
              <X class="w-3.5 h-3.5" />
            </button>
          </div>
          <label
            v-else
            class="inline-flex items-center gap-2 text-sm text-neutral-300 cursor-pointer hover:text-white border border-dashed border-white/15 rounded-lg px-4 py-3"
          >
            <ImagePlus class="w-4 h-4" />
            <span>Anexar imagem (jpg, png, webp)</span>
            <input type="file" accept="image/jpeg,image/png,image/webp" class="hidden" @change="onImage">
          </label>
        </div>
        <label class="inline-flex items-center gap-2 text-sm text-neutral-300 cursor-pointer">
          <input v-model="form.is_published" type="checkbox" class="accent-orange-500 w-4 h-4">
          Publicar (fica visível para os alunos)
        </label>
        <div class="flex justify-end gap-2 pt-2">
          <button
            type="button"
            class="px-4 py-2 text-sm text-neutral-400 hover:text-white"
            @click="showForm = false"
          >
            Cancelar
          </button>
          <button
            type="button"
            :disabled="saving"
            class="inline-flex items-center gap-2 px-5 py-2.5 bg-orange-500 hover:bg-orange-400 disabled:opacity-50 text-white font-bold uppercase tracking-wider text-xs rounded-lg"
            @click="save"
          >
            <Loader2 v-if="saving" class="w-4 h-4 animate-spin" />
            Salvar
          </button>
        </div>
      </div>
    </AdminModal>
  </div>
</template>
