<script setup lang="ts">
import { Loader2, Search, FileText } from 'lucide-vue-next'
import type { AttachmentLibraryItem } from '~/composables/useAdmin'

const props = defineProps<{ open: boolean }>()
const emit = defineEmits<{ close: []; pick: [ids: number[]] }>()

const admin = useAdmin()

const items = ref<AttachmentLibraryItem[]>([])
const loading = ref(false)
const q = ref('')
const selectedIds = ref<Set<number>>(new Set())

const load = async () => {
  loading.value = true
  try {
    items.value = await admin.listAttachmentLibrary(q.value.trim())
  } catch {
    items.value = []
  } finally {
    loading.value = false
  }
}

// Busca no servidor (`title__icontains`) com debounce — a lista pode ter centenas
// de anexos, não dá pra filtrar tudo no cliente.
let timer: ReturnType<typeof setTimeout> | null = null
watch(q, () => {
  if (timer) clearTimeout(timer)
  timer = setTimeout(load, 300)
})

watch(
  () => props.open,
  (v) => {
    if (!v) {
      selectedIds.value = new Set()
      q.value = ''
      return
    }
    load()
  }
)

const toggle = (id: number) => {
  const next = new Set(selectedIds.value)
  next.has(id) ? next.delete(id) : next.add(id)
  selectedIds.value = next
}

const fmtSize = (b: number) => {
  if (b < 1024) return `${b} B`
  if (b < 1024 * 1024) return `${(b / 1024).toFixed(1)} KB`
  return `${(b / 1024 / 1024).toFixed(1)} MB`
}

const submit = () => {
  if (!selectedIds.value.size) return
  emit('pick', [...selectedIds.value])
  emit('close')
}
</script>

<template>
  <AdminModal :open="open" title="Escolher anexo existente" size="md" @close="emit('close')">
    <div class="space-y-4">
      <div class="relative">
        <Search class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-500" />
        <input
          v-model="q"
          type="search"
          placeholder="Buscar por nome do arquivo..."
          class="w-full pl-10 pr-4 py-2.5 bg-white/5 border border-white/10 rounded-lg text-sm text-white placeholder:text-neutral-500 focus:border-orange-500/50 focus:outline-none"
        >
      </div>

      <div v-if="loading" class="flex justify-center py-10">
        <Loader2 class="w-5 h-5 text-orange-500 animate-spin" />
      </div>

      <div
        v-else-if="items.length"
        class="max-h-72 overflow-y-auto rounded-lg border border-white/10 bg-white/5 divide-y divide-white/5"
      >
        <label
          v-for="a in items"
          :key="a.id"
          class="flex items-center gap-3 px-4 py-2.5 text-sm text-white cursor-pointer hover:bg-white/5"
        >
          <input
            type="checkbox"
            class="accent-orange-500 shrink-0"
            :checked="selectedIds.has(a.id)"
            @change="toggle(a.id)"
          >
          <FileText class="w-3.5 h-3.5 text-neutral-500 shrink-0" />
          <span class="flex-1 min-w-0">
            <span class="block truncate">{{ a.title }}</span>
            <span class="block text-[11px] text-neutral-500 truncate">
              {{ a.course_name }} › {{ a.lesson_name }}
            </span>
          </span>
          <span class="text-[10px] text-neutral-500 shrink-0">{{ fmtSize(a.size_bytes) }}</span>
        </label>
      </div>

      <p v-else class="text-xs text-neutral-500 text-center py-10">
        {{ q ? `Nenhum anexo encontrado para "${q}".` : 'Nenhum anexo enviado ainda.' }}
      </p>

      <div class="flex justify-end gap-2 pt-2 border-t border-white/5">
        <button type="button" class="px-4 py-2 text-sm text-neutral-400 hover:text-white" @click="emit('close')">
          Cancelar
        </button>
        <button
          type="button"
          :disabled="!selectedIds.size"
          class="inline-flex items-center gap-2 px-5 py-2 bg-orange-500 hover:bg-orange-400 disabled:opacity-50 text-white font-bold uppercase tracking-wider text-xs rounded-lg"
          @click="submit"
        >
          Adicionar{{ selectedIds.size ? ` (${selectedIds.size})` : '' }}
        </button>
      </div>
    </div>
  </AdminModal>
</template>
