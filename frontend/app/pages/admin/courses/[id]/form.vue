<script setup lang="ts">
import draggable from 'vuedraggable'
import {
  ArrowLeft,
  Plus,
  Trash2,
  GripVertical,
  Loader2,
  Download,
} from 'lucide-vue-next'
import type { AdminCourseForm, AdminFormField, FormResponseRow } from '~/composables/useAdmin'

definePageMeta({ layout: 'admin', middleware: 'admin' })

const route = useRoute()
const router = useRouter()
const admin = useAdmin()
const toast = useToast()

const courseId = Number(route.params.id)

const TYPES = [
  { value: 'text', label: 'Texto curto' },
  { value: 'textarea', label: 'Texto longo' },
  { value: 'rating', label: 'Nota (1 a 5)' },
  { value: 'choice', label: 'Escolha' },
] as const

const form = reactive<AdminCourseForm>({
  title: '',
  description: '',
  fields: [],
  every_days: 30,
  required: false,
  is_active: true,
})

const loading = ref(true)
const saving = ref(false)

const load = async () => {
  loading.value = true
  try {
    const { form: f } = await admin.getCourseForm(courseId)
    if (f) {
      form.title = f.title
      form.description = f.description
      form.every_days = f.every_days
      form.required = f.required
      form.is_active = f.is_active
      form.fields = f.fields.map((x) => ({ ...x, options: x.options || [] }))
    }
  } catch (e: any) {
    toast.error(e?.data?.detail || 'Falha ao carregar formulário')
  } finally {
    loading.value = false
  }
}
await load()

useHead({ title: 'Formulário do curso | Admin' })

const addField = () => {
  // key temp só p/ o item-key do draggable ser único; removida no save (backend atribui campo_i)
  form.fields.push({ key: `_new_${Date.now()}_${form.fields.length}`, label: '', type: 'text', required: false, options: [] })
}
const removeField = (i: number) => form.fields.splice(i, 1)

const save = async () => {
  saving.value = true
  try {
    await admin.saveCourseForm(courseId, {
      title: form.title,
      description: form.description,
      every_days: form.every_days,
      required: form.required,
      is_active: form.is_active,
      fields: form.fields.map((f) => ({
        key: f.key?.startsWith('_new_') ? '' : f.key,
        label: f.label,
        type: f.type,
        required: f.required,
        options:
          f.type === 'choice'
            ? f.options.map((o) => o.trim()).filter(Boolean)
            : [],
      })),
    })
    toast.success('Formulário salvo')
    await load()
  } catch (e: any) {
    toast.error(e?.data?.detail || 'Falha ao salvar')
  } finally {
    saving.value = false
  }
}

// Respostas
const tab = ref<'editor' | 'respostas'>('editor')
const responses = ref<FormResponseRow[]>([])
const loadingResponses = ref(false)

const loadResponses = async () => {
  loadingResponses.value = true
  try {
    responses.value = await admin.listFormResponses(courseId)
  } catch (e: any) {
    toast.error(e?.data?.detail || 'Falha ao carregar respostas')
  } finally {
    loadingResponses.value = false
  }
}
watch(tab, (t) => {
  if (t === 'respostas') loadResponses()
})

const csvCell = (v: unknown) => `"${String(v ?? '').replace(/"/g, '""')}"`

const exportCsv = () => {
  const cols = form.fields
  const header = ['Aluno', 'Email', 'Data', ...cols.map((c) => c.label)]
  const lines = responses.value.map((r) => [
    r.user_name || '',
    r.user_email,
    new Date(r.created_at).toLocaleString('pt-BR'),
    ...cols.map((c) => r.answers[c.key ?? ''] ?? ''),
  ])
  const csv = [header, ...lines].map((line) => line.map(csvCell).join(',')).join('\n')
  // BOM p/ Excel reconhecer UTF-8 (acentos)
  const blob = new Blob(['﻿' + csv], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `respostas-curso-${courseId}.csv`
  a.click()
  URL.revokeObjectURL(url)
}

const fmtAnswers = (r: FormResponseRow) =>
  form.fields
    .map((f) => `${f.label}: ${r.answers[f.key ?? ''] ?? '-'}`)
    .join('  ·  ')

const inputClass =
  'w-full px-4 py-2.5 bg-white/5 border border-white/10 rounded-lg text-sm text-white focus:border-orange-500/50 focus:outline-none'
</script>

<template>
  <div class="space-y-6 max-w-3xl">
    <header class="flex items-center gap-3">
      <button
        type="button"
        class="p-2 rounded-lg text-neutral-400 hover:text-white hover:bg-white/5"
        @click="router.back()"
      >
        <ArrowLeft class="w-4 h-4" />
      </button>
      <div class="flex-1">
        <p class="text-xs text-neutral-500 uppercase tracking-widest">Curso</p>
        <h1 class="text-2xl font-medium tracking-tight">Formulário</h1>
      </div>
    </header>

    <!-- Tabs -->
    <div class="flex gap-1 border-b border-white/5">
      <button
        type="button"
        :class="[
          'px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors',
          tab === 'editor'
            ? 'border-orange-500 text-white'
            : 'border-transparent text-neutral-500 hover:text-neutral-300',
        ]"
        @click="tab = 'editor'"
      >
        Editor
      </button>
      <button
        type="button"
        :class="[
          'px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors',
          tab === 'respostas'
            ? 'border-orange-500 text-white'
            : 'border-transparent text-neutral-500 hover:text-neutral-300',
        ]"
        @click="tab = 'respostas'"
      >
        Respostas
      </button>
    </div>

    <div v-if="loading" class="flex justify-center py-10">
      <Loader2 class="w-5 h-5 text-orange-500 animate-spin" />
    </div>

    <!-- Editor -->
    <template v-else-if="tab === 'editor'">
      <section class="space-y-5 bg-white/[0.02] border border-white/5 rounded-xl p-6">
        <div>
          <label class="block text-xs font-bold uppercase tracking-wider text-neutral-400 mb-1.5">Título</label>
          <input v-model="form.title" type="text" placeholder="Ex: Pesquisa de satisfação" :class="inputClass">
        </div>

        <div>
          <label class="block text-xs font-bold uppercase tracking-wider text-neutral-400 mb-1.5">Descrição</label>
          <textarea v-model="form.description" rows="2" placeholder="Texto opcional acima das perguntas" :class="inputClass" />
        </div>

        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="block text-xs font-bold uppercase tracking-wider text-neutral-400 mb-1.5">Repetir a cada (dias)</label>
            <input v-model.number="form.every_days" type="number" min="0" :class="inputClass">
            <p class="text-[11px] text-neutral-500 mt-1">0 = aparece só uma vez.</p>
          </div>
          <div class="flex flex-col justify-center gap-2 pt-4">
            <label class="flex items-center gap-2 text-sm text-neutral-300 cursor-pointer">
              <input v-model="form.required" type="checkbox" class="accent-orange-500">
              Obrigatório (banner volta até responder)
            </label>
            <label class="flex items-center gap-2 text-sm text-neutral-300 cursor-pointer">
              <input v-model="form.is_active" type="checkbox" class="accent-orange-500">
              Ativo
            </label>
          </div>
        </div>
      </section>

      <!-- Campos -->
      <section class="space-y-3">
        <h2 class="text-lg font-medium tracking-tight">Perguntas</h2>

        <ClientOnly>
          <draggable v-model="form.fields" handle=".field-handle" item-key="key" class="space-y-3">
            <template #item="{ element, index }">
              <div class="bg-white/[0.02] border border-white/5 rounded-xl p-4 space-y-3">
                <div class="flex items-start gap-3">
                  <button type="button" class="field-handle mt-2 cursor-grab text-neutral-600 hover:text-neutral-400">
                    <GripVertical class="w-4 h-4" />
                  </button>
                  <div class="flex-1 space-y-3">
                    <input v-model="element.label" type="text" placeholder="Pergunta" :class="inputClass">
                    <div class="flex items-center gap-3">
                      <select v-model="element.type" class="px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-sm text-white focus:outline-none [&>option]:bg-[#0a0a0a]">
                        <option v-for="t in TYPES" :key="t.value" :value="t.value">{{ t.label }}</option>
                      </select>
                      <label class="flex items-center gap-2 text-sm text-neutral-400 cursor-pointer">
                        <input v-model="element.required" type="checkbox" class="accent-orange-500">
                        Obrigatória
                      </label>
                    </div>
                    <textarea
                      v-if="element.type === 'choice'"
                      :value="element.options.join('\n')"
                      rows="3"
                      placeholder="Uma opção por linha"
                      :class="inputClass"
                      @input="element.options = ($event.target as HTMLTextAreaElement).value.split('\n')"
                    />
                  </div>
                  <button type="button" class="mt-1 p-1.5 rounded-md text-neutral-500 hover:text-red-300 hover:bg-red-500/10" @click="removeField(index)">
                    <Trash2 class="w-4 h-4" />
                  </button>
                </div>
              </div>
            </template>
          </draggable>
        </ClientOnly>

        <button
          type="button"
          class="w-full flex items-center justify-center gap-2 px-4 py-3 rounded-lg border border-dashed border-white/10 text-sm text-neutral-500 hover:text-orange-300 hover:border-orange-500/40 transition-colors"
          @click="addField"
        >
          <Plus class="w-4 h-4" />
          Nova pergunta
        </button>
      </section>

      <div class="flex justify-end">
        <button
          type="button"
          :disabled="saving"
          class="px-5 py-2.5 bg-orange-500 hover:bg-orange-400 text-white text-xs font-bold uppercase tracking-wider rounded-lg disabled:opacity-50"
          @click="save"
        >
          <Loader2 v-if="saving" class="w-4 h-4 animate-spin inline" />
          <span v-else>Salvar formulário</span>
        </button>
      </div>
    </template>

    <!-- Respostas -->
    <template v-else>
      <div class="flex items-center justify-between">
        <p class="text-sm text-neutral-400">{{ responses.length }} resposta(s)</p>
        <button
          type="button"
          :disabled="!responses.length"
          class="inline-flex items-center gap-2 px-3 py-2 bg-white/5 hover:bg-white/10 border border-white/10 rounded-lg text-xs font-bold uppercase tracking-wider text-neutral-300 disabled:opacity-40"
          @click="exportCsv"
        >
          <Download class="w-3.5 h-3.5" />
          Exportar CSV
        </button>
      </div>

      <div v-if="loadingResponses" class="flex justify-center py-10">
        <Loader2 class="w-5 h-5 text-orange-500 animate-spin" />
      </div>

      <div v-else-if="!responses.length" class="text-center py-10 text-sm text-neutral-500">
        Nenhuma resposta ainda.
      </div>

      <div v-else class="space-y-2">
        <div
          v-for="r in responses"
          :key="r.id"
          class="bg-white/[0.02] border border-white/5 rounded-lg p-4"
        >
          <div class="flex items-center justify-between gap-3">
            <p class="text-sm text-white">{{ r.user_name || r.user_email }}</p>
            <p class="text-[11px] text-neutral-500">{{ new Date(r.created_at).toLocaleString('pt-BR') }}</p>
          </div>
          <p class="text-xs text-neutral-400 mt-1.5">{{ fmtAnswers(r) }}</p>
        </div>
      </div>
    </template>
  </div>
</template>
