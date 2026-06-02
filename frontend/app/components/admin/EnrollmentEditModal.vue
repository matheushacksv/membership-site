<script setup lang="ts">
import { Loader2 } from 'lucide-vue-next'
import type { EnrollmentItem } from '~/composables/useAdmin'

const props = defineProps<{
  open: boolean
  enrollment: EnrollmentItem | null
  userLabel?: string
  courseName?: string
}>()
const emit = defineEmits<{ close: []; saved: [] }>()

const admin = useAdmin()
const toast = useToast()

const form = reactive({
  expires_at: '' as string,
  is_active: true,
  lifetime: true,
})

const saving = ref(false)

const toLocalDatetime = (iso: string | null): string => {
  if (!iso) return ''
  const d = new Date(iso)
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
}

watch(
  () => props.enrollment,
  (e) => {
    form.is_active = e?.is_active ?? true
    if (e?.expires_at) {
      form.lifetime = false
      form.expires_at = toLocalDatetime(e.expires_at)
    } else {
      form.lifetime = true
      form.expires_at = ''
    }
  },
  { immediate: true }
)

const submit = async () => {
  if (!props.enrollment) return
  saving.value = true
  try {
    const body: { expires_at?: string | null; is_active?: boolean } = {
      is_active: form.is_active,
      expires_at: form.lifetime
        ? null
        : form.expires_at
          ? new Date(form.expires_at).toISOString()
          : null,
    }
    await admin.updateEnrollment(props.enrollment.id, body)
    toast.success('Matrícula atualizada')
    emit('saved')
    emit('close')
  } catch (e: any) {
    toast.error(e?.data?.detail || 'Falha ao salvar')
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <AdminModal :open="open" title="Editar matrícula" size="md" @close="emit('close')">
    <form class="space-y-4" @submit.prevent="submit">
      <div
        v-if="userLabel || courseName"
        class="px-4 py-3 bg-white/[0.02] border border-white/5 rounded-lg text-sm"
      >
        <p v-if="userLabel" class="text-white">{{ userLabel }}</p>
        <p v-if="courseName" class="text-xs text-neutral-500 mt-0.5">{{ courseName }}</p>
      </div>

      <div>
        <label class="flex items-center gap-2 text-sm text-neutral-400 cursor-pointer mb-2">
          <input v-model="form.lifetime" type="checkbox" class="accent-orange-500">
          Acesso vitalício
        </label>

        <label v-if="!form.lifetime" class="block text-xs font-bold uppercase tracking-wider text-neutral-400 mb-1.5">
          Expira em
        </label>
        <input
          v-if="!form.lifetime"
          v-model="form.expires_at"
          type="datetime-local"
          class="w-full px-4 py-2.5 bg-white/5 border border-white/10 rounded-lg text-sm text-white focus:border-orange-500/50 focus:outline-none"
        >
      </div>

      <label class="flex items-center gap-2 text-sm text-neutral-400 cursor-pointer">
        <input v-model="form.is_active" type="checkbox" class="accent-orange-500">
        Matrícula ativa
      </label>

      <div class="flex justify-end gap-2 pt-2 border-t border-white/5">
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
