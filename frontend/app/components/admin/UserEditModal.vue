<script setup lang="ts">
import { Loader2 } from 'lucide-vue-next'
import type { AdminUser } from '~/composables/useAdmin'

const props = defineProps<{ open: boolean; user: AdminUser | null }>()
const emit = defineEmits<{ close: []; saved: [] }>()

const admin = useAdmin()
const toast = useToast()

const form = reactive({ name: '', email: '' })
const saving = ref(false)

watch(
  () => props.user,
  (u) => {
    form.name = u?.name || ''
    form.email = u?.email || ''
  },
  { immediate: true }
)

const submit = async () => {
  if (!props.user) return
  saving.value = true
  try {
    const body: { name?: string; email?: string } = {}
    if (form.name && form.name !== props.user.name) body.name = form.name
    if (form.email && form.email !== props.user.email) body.email = form.email
    if (Object.keys(body).length === 0) {
      emit('close')
      return
    }
    await admin.updateUser(props.user.id, body)
    toast.success('Aluno atualizado')
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
  <AdminModal :open="open" title="Editar aluno" size="md" @close="emit('close')">
    <form class="space-y-4" @submit.prevent="submit">
      <div>
        <label class="block text-xs font-bold uppercase tracking-wider text-neutral-400 mb-1.5">Nome</label>
        <input
          v-model="form.name"
          type="text"
          class="w-full px-4 py-2.5 bg-white/5 border border-white/10 rounded-lg text-sm text-white focus:border-orange-500/50 focus:outline-none"
        >
      </div>

      <div>
        <label class="block text-xs font-bold uppercase tracking-wider text-neutral-400 mb-1.5">Email</label>
        <input
          v-model="form.email"
          type="email"
          class="w-full px-4 py-2.5 bg-white/5 border border-white/10 rounded-lg text-sm text-white focus:border-orange-500/50 focus:outline-none"
        >
      </div>

      <div class="flex justify-end gap-2 pt-2 border-t border-white/5">
        <button type="button" class="px-4 py-2 text-sm text-neutral-400 hover:text-white" @click="emit('close')">Cancelar</button>
        <button
          type="submit"
          :disabled="saving"
          class="inline-flex items-center gap-2 px-5 py-2 bg-orange-500 hover:bg-orange-400 disabled:opacity-50 text-black font-bold uppercase tracking-wider text-xs rounded-lg"
        >
          <Loader2 v-if="saving" class="w-3.5 h-3.5 animate-spin" />
          Salvar
        </button>
      </div>
    </form>
  </AdminModal>
</template>
