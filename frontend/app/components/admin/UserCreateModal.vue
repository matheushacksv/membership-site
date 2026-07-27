<script setup lang="ts">
import { Loader2 } from 'lucide-vue-next'
import type { AdminCourse } from '~/composables/useAdmin'

const props = defineProps<{ open: boolean; courses: AdminCourse[] }>()
const emit = defineEmits<{ close: []; created: [] }>()

const admin = useAdmin()
const toast = useToast()

const form = reactive({
  email: '',
  name: '',
  phone: '',
  course_ids: [] as number[],
})

const saving = ref(false)

const reset = () => {
  form.email = ''
  form.name = ''
  form.phone = ''
  form.course_ids = []
}

watch(() => props.open, (v) => { if (!v) reset() })

const submit = async () => {
  if (!form.email.trim()) return
  saving.value = true
  try {
    await admin.createUser({
      email: form.email,
      name: form.name || null,
      phone: form.phone || null,
      course_ids: form.course_ids,
    })
    toast.success('Aluno criado e email enviado')
    emit('created')
    emit('close')
  } catch (e: any) {
    toast.error(e?.data?.detail || 'Falha ao criar aluno')
  } finally {
    saving.value = false
  }
}

const toggleCourse = (id: number) => {
  const i = form.course_ids.indexOf(id)
  if (i >= 0) form.course_ids.splice(i, 1)
  else form.course_ids.push(id)
}
</script>

<template>
  <AdminModal :open="open" title="Novo aluno" size="md" @close="emit('close')">
    <form class="space-y-4" @submit.prevent="submit">
      <div>
        <label class="block text-xs font-bold uppercase tracking-wider text-neutral-400 mb-1.5">Email</label>
        <input
          v-model="form.email"
          type="email"
          required
          placeholder="aluno@email.com"
          class="w-full px-4 py-2.5 bg-white/5 border border-white/10 rounded-lg text-sm text-white focus:border-orange-500/50 focus:outline-none"
        >
      </div>

      <div>
        <label class="block text-xs font-bold uppercase tracking-wider text-neutral-400 mb-1.5">Nome</label>
        <input
          v-model="form.name"
          type="text"
          placeholder="Opcional"
          class="w-full px-4 py-2.5 bg-white/5 border border-white/10 rounded-lg text-sm text-white focus:border-orange-500/50 focus:outline-none"
        >
      </div>

      <div>
        <label class="block text-xs font-bold uppercase tracking-wider text-neutral-400 mb-1.5">Telefone</label>
        <input
          v-model="form.phone"
          type="tel"
          placeholder="(11) 99999-8888 — opcional, para WhatsApp"
          class="w-full px-4 py-2.5 bg-white/5 border border-white/10 rounded-lg text-sm text-white focus:border-orange-500/50 focus:outline-none"
        >
      </div>

      <div>
        <label class="block text-xs font-bold uppercase tracking-wider text-neutral-400 mb-2">
          Matricular em cursos
        </label>
        <div v-if="courses.length" class="max-h-48 overflow-y-auto border border-white/10 rounded-lg divide-y divide-white/5">
          <label
            v-for="c in courses"
            :key="c.id"
            class="flex items-center gap-2.5 px-3 py-2 hover:bg-white/5 cursor-pointer text-sm text-white"
          >
            <input
              type="checkbox"
              class="accent-orange-500"
              :checked="form.course_ids.includes(c.id)"
              @change="toggleCourse(c.id)"
            >
            <span class="truncate">{{ c.name }}</span>
            <span v-if="!c.is_active" class="ml-auto text-[10px] text-neutral-500 uppercase tracking-wider">Rascunho</span>
          </label>
        </div>
        <p v-else class="text-xs text-neutral-500">Nenhum curso criado.</p>
      </div>

      <p class="text-xs text-neutral-500 bg-white/[0.02] border border-white/5 rounded-lg p-3">
        Será enviado email com link pra definir a senha (expira em 24h).
      </p>

      <div class="flex justify-end gap-2 pt-2 border-t border-white/5">
        <button type="button" class="px-4 py-2 text-sm text-neutral-400 hover:text-white" @click="emit('close')">Cancelar</button>
        <button
          type="submit"
          :disabled="saving || !form.email.trim()"
          class="inline-flex items-center gap-2 px-5 py-2 bg-orange-500 hover:bg-orange-400 disabled:opacity-50 text-white font-bold uppercase tracking-wider text-xs rounded-lg"
        >
          <Loader2 v-if="saving" class="w-3.5 h-3.5 animate-spin" />
          Criar aluno
        </button>
      </div>
    </form>
  </AdminModal>
</template>
