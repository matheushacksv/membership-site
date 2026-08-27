<script setup lang="ts">
import { Loader2, Search, Layers } from 'lucide-vue-next'
import type { ModuleLibraryItem } from '~/composables/useAdmin'

const props = defineProps<{ open: boolean; excludeCourseId: number }>()
const emit = defineEmits<{ close: []; pick: [moduleId: number] }>()

const admin = useAdmin()

const items = ref<ModuleLibraryItem[]>([])
const loading = ref(false)
const q = ref('')
const selectedId = ref<number | null>(null)

const load = async () => {
  loading.value = true
  try {
    items.value = await admin.listModuleLibrary(q.value.trim(), props.excludeCourseId)
  } catch {
    items.value = []
  } finally {
    loading.value = false
  }
}

// Busca no servidor (nome do módulo ou do curso) com debounce, lista pode ser grande.
let timer: ReturnType<typeof setTimeout> | null = null
watch(q, () => {
  if (timer) clearTimeout(timer)
  timer = setTimeout(load, 300)
})

watch(
  () => props.open,
  (v) => {
    if (!v) {
      selectedId.value = null
      q.value = ''
      return
    }
    load()
  }
)

const submit = () => {
  if (selectedId.value == null) return
  emit('pick', selectedId.value)
  emit('close')
}
</script>

<template>
  <AdminModal :open="open" title="Importar módulo de outro curso" size="md" @close="emit('close')">
    <div class="space-y-4">
      <p class="text-xs text-neutral-500">
        Copia o módulo (aulas + anexos) pra este curso. Cópia independente, editar o original depois não altera aqui. Entra despublicado.
      </p>

      <div class="relative">
        <Search class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-500" />
        <input
          v-model="q"
          type="search"
          placeholder="Buscar por módulo ou curso..."
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
          v-for="m in items"
          :key="m.id"
          class="flex items-center gap-3 px-4 py-2.5 text-sm text-white cursor-pointer hover:bg-white/5"
        >
          <input
            type="radio"
            name="module-pick"
            class="accent-orange-500 shrink-0"
            :checked="selectedId === m.id"
            @change="selectedId = m.id"
          >
          <Layers class="w-3.5 h-3.5 text-neutral-500 shrink-0" />
          <span class="flex-1 min-w-0">
            <span class="block truncate">{{ m.name }}</span>
            <span class="block text-[11px] text-neutral-500 truncate">{{ m.course_name }}</span>
          </span>
          <span class="text-[10px] text-neutral-500 shrink-0">{{ m.lesson_count }} aula(s)</span>
        </label>
      </div>

      <p v-else class="text-xs text-neutral-500 text-center py-10">
        {{ q ? `Nenhum módulo encontrado para "${q}".` : 'Nenhum módulo disponível.' }}
      </p>

      <div class="flex justify-end gap-2 pt-2 border-t border-white/5">
        <button type="button" class="px-4 py-2 text-sm text-neutral-400 hover:text-white" @click="emit('close')">
          Cancelar
        </button>
        <button
          type="button"
          :disabled="selectedId == null"
          class="inline-flex items-center gap-2 px-5 py-2 bg-orange-500 hover:bg-orange-400 disabled:opacity-50 text-white font-bold uppercase tracking-wider text-xs rounded-lg"
          @click="submit"
        >
          Importar
        </button>
      </div>
    </div>
  </AdminModal>
</template>
