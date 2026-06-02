<script setup lang="ts">
import { Loader2, Upload, ListChecks } from 'lucide-vue-next'
import type { AdminCourse, BulkImportResult } from '~/composables/useAdmin'

const props = defineProps<{ open: boolean; courses: AdminCourse[] }>()
const emit = defineEmits<{ close: []; done: [] }>()

const admin = useAdmin()
const toast = useToast()

const tab = ref<'csv' | 'list'>('list')
const textarea = ref('')
const csvText = ref('')
const courseIds = ref<number[]>([])
const sendWelcome = ref(true)
const saving = ref(false)
const result = ref<BulkImportResult | null>(null)

const reset = () => {
  textarea.value = ''
  csvText.value = ''
  courseIds.value = []
  sendWelcome.value = true
  result.value = null
  tab.value = 'list'
}

watch(() => props.open, (v) => { if (!v) reset() })

const onCsvFile = async (e: Event) => {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (!file) return
  csvText.value = await file.text()
}

const parseList = (): { email: string; name?: string }[] => {
  return textarea.value
    .split('\n')
    .map((line) => line.trim())
    .filter((line) => line.includes('@'))
    .map((email) => ({ email, name: email.split('@')[0] }))
}

const parseCsv = (): { email: string; name?: string }[] => {
  const lines = csvText.value.split('\n').map((l) => l.trim()).filter(Boolean)
  const users: { email: string; name?: string }[] = []
  for (const line of lines) {
    const parts = line.split(',').map((p) => p.trim().replace(/^["']|["']$/g, ''))
    const email = parts.find((p) => p.includes('@'))
    if (!email) continue
    const name = parts.find((p) => p !== email && p.length > 0)
    users.push({ email, name })
  }
  // skip header row if first line had no @
  return users
}

const submit = async () => {
  const users = tab.value === 'list' ? parseList() : parseCsv()
  if (!users.length) {
    toast.error('Nenhum email válido encontrado')
    return
  }
  saving.value = true
  try {
    result.value = await admin.bulkImport({
      users,
      course_ids: courseIds.value,
      send_welcome: sendWelcome.value,
    })
    toast.success(`${result.value.created} novos, ${result.value.existing} existentes`)
    emit('done')
  } catch (e: any) {
    toast.error(e?.data?.detail || 'Falha na importação')
  } finally {
    saving.value = false
  }
}

const toggleCourse = (id: number) => {
  const i = courseIds.value.indexOf(id)
  if (i >= 0) courseIds.value.splice(i, 1)
  else courseIds.value.push(id)
}

const previewCount = computed(() =>
  tab.value === 'list' ? parseList().length : parseCsv().length
)
</script>

<template>
  <AdminModal :open="open" title="Importar em massa" size="lg" @close="emit('close')">
    <div v-if="result" class="space-y-4">
      <div class="grid grid-cols-3 gap-3">
        <div class="bg-emerald-500/10 border border-emerald-500/20 rounded-lg p-4 text-center">
          <p class="text-2xl font-medium text-emerald-300">{{ result.created }}</p>
          <p class="text-xs text-neutral-400 mt-1">Criados</p>
        </div>
        <div class="bg-white/5 border border-white/10 rounded-lg p-4 text-center">
          <p class="text-2xl font-medium text-white">{{ result.existing }}</p>
          <p class="text-xs text-neutral-400 mt-1">Já existiam</p>
        </div>
        <div class="bg-orange-500/10 border border-orange-500/20 rounded-lg p-4 text-center">
          <p class="text-2xl font-medium text-orange-300">{{ result.enrolled }}</p>
          <p class="text-xs text-neutral-400 mt-1">Matrículas</p>
        </div>
      </div>

      <div v-if="result.errors.length" class="bg-red-500/10 border border-red-500/20 rounded-lg p-3">
        <p class="text-xs font-bold uppercase tracking-wider text-red-300 mb-2">
          Erros ({{ result.errors.length }})
        </p>
        <ul class="text-xs text-red-200 space-y-1 max-h-32 overflow-y-auto">
          <li v-for="(err, i) in result.errors" :key="i">{{ err }}</li>
        </ul>
      </div>

      <div class="flex justify-end pt-3 border-t border-white/5">
        <button
          type="button"
          class="px-5 py-2 bg-orange-500 hover:bg-orange-400 text-white font-bold uppercase tracking-wider text-xs rounded-lg"
          @click="emit('close')"
        >
          Fechar
        </button>
      </div>
    </div>

    <form v-else class="space-y-4" @submit.prevent="submit">
      <!-- Tabs -->
      <div class="flex gap-1 p-1 bg-white/5 border border-white/10 rounded-lg w-fit">
        <button
          type="button"
          :class="[
            'inline-flex items-center gap-2 px-4 py-1.5 rounded-md text-xs font-bold uppercase tracking-wider transition-colors',
            tab === 'list' ? 'bg-orange-500 text-white' : 'text-neutral-400 hover:text-white',
          ]"
          @click="tab = 'list'"
        >
          <ListChecks class="w-3.5 h-3.5" />
          Lista de emails
        </button>
        <button
          type="button"
          :class="[
            'inline-flex items-center gap-2 px-4 py-1.5 rounded-md text-xs font-bold uppercase tracking-wider transition-colors',
            tab === 'csv' ? 'bg-orange-500 text-white' : 'text-neutral-400 hover:text-white',
          ]"
          @click="tab = 'csv'"
        >
          <Upload class="w-3.5 h-3.5" />
          CSV
        </button>
      </div>

      <div v-if="tab === 'list'">
        <label class="block text-xs font-bold uppercase tracking-wider text-neutral-400 mb-1.5">
          Cole os emails (um por linha)
        </label>
        <textarea
          v-model="textarea"
          rows="8"
          placeholder="joao@exemplo.com&#10;maria@exemplo.com&#10;..."
          class="w-full px-4 py-2.5 bg-white/5 border border-white/10 rounded-lg text-sm text-white font-mono focus:border-orange-500/50 focus:outline-none resize-y"
        />
      </div>

      <div v-else>
        <label class="block text-xs font-bold uppercase tracking-wider text-neutral-400 mb-1.5">
          Arquivo CSV (formato: email,nome)
        </label>
        <input
          type="file"
          accept=".csv,text/csv"
          class="block text-xs text-neutral-400 file:mr-3 file:px-3 file:py-1.5 file:rounded-md file:border-0 file:bg-white/10 file:text-white file:cursor-pointer"
          @change="onCsvFile"
        >
        <textarea
          v-if="csvText"
          v-model="csvText"
          rows="6"
          class="mt-2 w-full px-4 py-2.5 bg-white/5 border border-white/10 rounded-lg text-xs text-white font-mono"
        />
      </div>

      <p v-if="previewCount" class="text-xs text-orange-300">
        {{ previewCount }} email{{ previewCount === 1 ? '' : 's' }} detectado{{ previewCount === 1 ? '' : 's' }}
      </p>

      <div>
        <label class="block text-xs font-bold uppercase tracking-wider text-neutral-400 mb-2">Matricular em cursos</label>
        <div v-if="courses.length" class="max-h-40 overflow-y-auto border border-white/10 rounded-lg divide-y divide-white/5">
          <label
            v-for="c in courses"
            :key="c.id"
            class="flex items-center gap-2.5 px-3 py-2 hover:bg-white/5 cursor-pointer text-sm text-white"
          >
            <input
              type="checkbox"
              class="accent-orange-500"
              :checked="courseIds.includes(c.id)"
              @change="toggleCourse(c.id)"
            >
            <span class="truncate">{{ c.name }}</span>
          </label>
        </div>
      </div>

      <label class="flex items-center gap-2 text-sm text-neutral-400 cursor-pointer">
        <input v-model="sendWelcome" type="checkbox" class="accent-orange-500">
        Enviar email de acesso pra novos alunos
      </label>

      <div class="flex justify-end gap-2 pt-3 border-t border-white/5">
        <button type="button" class="px-4 py-2 text-sm text-neutral-400 hover:text-white" @click="emit('close')">Cancelar</button>
        <button
          type="submit"
          :disabled="saving || !previewCount"
          class="inline-flex items-center gap-2 px-5 py-2 bg-orange-500 hover:bg-orange-400 disabled:opacity-50 text-white font-bold uppercase tracking-wider text-xs rounded-lg"
        >
          <Loader2 v-if="saving" class="w-3.5 h-3.5 animate-spin" />
          Importar
        </button>
      </div>
    </form>
  </AdminModal>
</template>
