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

const form = reactive({
  course_id: null as number | null,
  lifetime: true,
  expires_at: '',
  is_active: true,
})

const saving = ref(false)

const reset = () => {
  form.course_id = null
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

const submit = async () => {
  if (!props.user || !form.course_id) return
  saving.value = true
  try {
    await admin.createEnrollment({
      user_id: props.user.id,
      course_id: form.course_id,
      expires_at: form.lifetime
        ? null
        : form.expires_at
          ? new Date(form.expires_at).toISOString()
          : null,
      is_active: form.is_active,
    })
    toast.success('Matrícula criada')
    emit('saved')
    emit('close')
  } catch (e: any) {
    if (e?.response?.status === 409) {
      toast.error('Aluno já matriculado neste curso')
    } else {
      toast.error(e?.data?.detail || 'Falha ao matricular')
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
        <label class="block text-xs font-bold uppercase tracking-wider text-neutral-400 mb-1.5">Curso</label>
        <select
          v-model="form.course_id"
          required
          class="w-full px-4 py-2.5 bg-white/5 border border-white/10 rounded-lg text-sm text-white focus:border-orange-500/50 focus:outline-none"
        >
          <option :value="null" disabled class="bg-black">Selecione...</option>
          <option
            v-for="c in availableCourses"
            :key="c.id"
            :value="c.id"
            class="bg-black"
          >
            {{ c.name }}{{ !c.is_active ? ' (rascunho)' : '' }}
          </option>
        </select>
        <p v-if="!availableCourses.length" class="text-xs text-neutral-500 mt-1">
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
          :disabled="saving || !form.course_id"
          class="inline-flex items-center gap-2 px-5 py-2 bg-orange-500 hover:bg-orange-400 disabled:opacity-50 text-black font-bold uppercase tracking-wider text-xs rounded-lg"
        >
          <Loader2 v-if="saving" class="w-3.5 h-3.5 animate-spin" />
          Matricular
        </button>
      </div>
    </form>
  </AdminModal>
</template>
