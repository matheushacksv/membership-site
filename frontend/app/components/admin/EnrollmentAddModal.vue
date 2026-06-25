<script setup lang="ts">
import { Loader2 } from 'lucide-vue-next'
import type { AdminCourse, AdminUser } from '~/composables/useAdmin'

const props = defineProps<{
  open: boolean
  user: AdminUser | null
  courses: AdminCourse[]
  excludeCourseIds?: number[]
}>()

const emit = defineEmits<{ close: []; saved: [] }>()

const admin = useAdmin()
const toast = useToast()

const selectedIds = ref<Set<number>>(new Set())

const form = reactive({
  lifetime: true,
  expires_at: '',
  is_active: true,
})

const saving = ref(false)

const reset = () => {
  selectedIds.value = new Set()
  form.lifetime = true
  form.expires_at = ''
  form.is_active = true
}

watch(() => props.open, (v) => { if (!v) reset() })

const availableCourses = computed(() =>
  props.courses.filter(
    (c) => !(props.excludeCourseIds || []).includes(c.id)
  )
)

const toggle = (id: number) => {
  const next = new Set(selectedIds.value)
  next.has(id) ? next.delete(id) : next.add(id)
  selectedIds.value = next
}

const allSelected = computed(
  () => availableCourses.value.length > 0 && selectedIds.value.size === availableCourses.value.length
)

const toggleAll = () => {
  selectedIds.value = allSelected.value
    ? new Set()
    : new Set(availableCourses.value.map((c) => c.id))
}

const submit = async () => {
  if (!props.user || !selectedIds.value.size) return

  // Endpoint é single (1 matrícula por chamada); fazemos loop sequencial pros
  // cursos marcados. Mesma config de validade/ativa pra todos.
  const expires = form.lifetime
    ? null
    : form.expires_at
      ? new Date(form.expires_at).toISOString()
      : null

  saving.value = true
  let ok = 0
  let dup = 0
  let failed = 0
  try {
    for (const courseId of [...selectedIds.value]) {
      try {
        await admin.createEnrollment({
          user_id: props.user.id,
          course_id: courseId,
          expires_at: expires,
          is_active: form.is_active,
        })
        ok++
      } catch (e: any) {
        if (e?.response?.status === 409) dup++
        else failed++
      }
    }

    if (ok && !dup && !failed) {
      toast.success(ok === 1 ? 'Matrícula criada' : `${ok} matrículas criadas`)
    } else if (ok || dup) {
      const parts = []
      if (ok) parts.push(`${ok} criada(s)`)
      if (dup) parts.push(`${dup} já existia(m)`)
      if (failed) parts.push(`${failed} com erro`)
      toast.success(parts.join(', '))
    } else {
      toast.error(failed ? `${failed} com erro` : 'Falha ao matricular')
    }

    if (ok || dup) {
      emit('saved')
      emit('close')
    }
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <AdminModal :open="open" title="Adicionar matrícula" size="md" @close="emit('close')">
    <form class="space-y-4" @submit.prevent="submit">
      <div
        v-if="user"
        class="px-4 py-3 bg-white/[0.02] border border-white/5 rounded-lg text-sm"
      >
        <p class="text-white">{{ user.name || user.email }}</p>
        <p class="text-xs text-neutral-500 mt-0.5">{{ user.email }}</p>
      </div>

      <div>
        <div class="flex items-center justify-between mb-1.5">
          <label class="block text-xs font-bold uppercase tracking-wider text-neutral-400">
            Cursos
            <span v-if="selectedIds.size" class="text-orange-300">({{ selectedIds.size }})</span>
          </label>
          <button
            v-if="availableCourses.length"
            type="button"
            class="text-[11px] font-bold uppercase tracking-wider text-orange-300 hover:text-orange-200"
            @click="toggleAll"
          >
            {{ allSelected ? 'Limpar' : 'Selecionar todos' }}
          </button>
        </div>

        <div
          v-if="availableCourses.length"
          class="max-h-56 overflow-y-auto rounded-lg border border-white/10 bg-white/5 divide-y divide-white/5"
        >
          <label
            v-for="c in availableCourses"
            :key="c.id"
            class="flex items-center gap-3 px-4 py-2.5 text-sm text-white cursor-pointer hover:bg-white/5"
          >
            <input
              type="checkbox"
              class="accent-orange-500 shrink-0"
              :checked="selectedIds.has(c.id)"
              @change="toggle(c.id)"
            >
            <span class="flex-1 break-words">
              {{ c.name }}<span v-if="!c.is_active" class="text-neutral-500"> (rascunho)</span>
            </span>
          </label>
        </div>
        <p v-else class="text-xs text-neutral-500 mt-1">
          Sem cursos disponíveis (já matriculado em todos).
        </p>
      </div>

      <div>
        <label class="flex items-center gap-2 text-sm text-neutral-400 cursor-pointer mb-2">
          <input v-model="form.lifetime" type="checkbox" class="accent-orange-500">
          Acesso vitalício
        </label>

        <template v-if="!form.lifetime">
          <label class="block text-xs font-bold uppercase tracking-wider text-neutral-400 mb-1.5">
            Expira em
          </label>
          <input
            v-model="form.expires_at"
            type="datetime-local"
            class="w-full px-4 py-2.5 bg-white/5 border border-white/10 rounded-lg text-sm text-white focus:border-orange-500/50 focus:outline-none"
          >
        </template>
      </div>

      <label class="flex items-center gap-2 text-sm text-neutral-400 cursor-pointer">
        <input v-model="form.is_active" type="checkbox" class="accent-orange-500">
        Ativa
      </label>

      <div class="flex justify-end gap-2 pt-2 border-t border-white/5">
        <button type="button" class="px-4 py-2 text-sm text-neutral-400 hover:text-white" @click="emit('close')">Cancelar</button>
        <button
          type="submit"
          :disabled="saving || !selectedIds.size"
          class="inline-flex items-center gap-2 px-5 py-2 bg-orange-500 hover:bg-orange-400 disabled:opacity-50 text-white font-bold uppercase tracking-wider text-xs rounded-lg"
        >
          <Loader2 v-if="saving" class="w-3.5 h-3.5 animate-spin" />
          Matricular{{ selectedIds.size ? ` (${selectedIds.size})` : '' }}
        </button>
      </div>
    </form>
  </AdminModal>
</template>
