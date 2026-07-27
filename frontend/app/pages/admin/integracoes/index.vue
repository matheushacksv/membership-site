<script setup lang="ts">
import { Loader2, Plug, MessageCircle } from 'lucide-vue-next'
import type { EvolutionConfig } from '~/composables/useAdmin'

definePageMeta({ layout: 'admin', middleware: 'admin' })
useHead({ title: 'Integrações — Admin' })

const admin = useAdmin()
const toast = useToast()

const form = reactive<EvolutionConfig>({
  base_url: '',
  instance: '',
  api_key: '',
  is_active: false,
})

const saving = ref(false)

const { pending } = await useAsyncData('admin-evolution-config', async () => {
  const cfg = await admin.getEvolutionConfig()
  Object.assign(form, cfg)
  return cfg
})

const save = async () => {
  saving.value = true
  try {
    const cfg = await admin.saveEvolutionConfig({ ...form })
    Object.assign(form, cfg)
    toast.success('Configuração salva')
  } catch (e: any) {
    toast.error(e?.data?.detail || 'Falha ao salvar')
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div class="max-w-2xl">
    <div class="flex items-center gap-3 mb-1">
      <Plug class="w-5 h-5 text-orange-400" />
      <h1 class="text-2xl font-medium tracking-tight text-white">Integrações</h1>
    </div>
    <p class="text-sm text-neutral-500 mb-8">
      Conecte serviços externos à plataforma.
    </p>

    <div v-if="pending" class="flex justify-center py-12">
      <Loader2 class="w-5 h-5 text-orange-500 animate-spin" />
    </div>

    <section
      v-else
      class="bg-white/[0.02] border border-white/10 rounded-xl p-6 md:p-8"
    >
      <div class="flex items-center gap-2.5 mb-1">
        <MessageCircle class="w-4 h-4 text-emerald-400" />
        <h2 class="text-base font-medium text-white">WhatsApp — Evolution API</h2>
      </div>
      <p class="text-xs text-neutral-500 mb-6">
        Ao criar um aluno com telefone, envia uma mensagem de acesso com link de login
        automático (válido 24h), reforçando o email.
      </p>

      <form class="space-y-5" @submit.prevent="save">
        <div>
          <label class="block text-xs font-bold uppercase tracking-wider text-neutral-400 mb-1.5">URL da API</label>
          <input
            v-model="form.base_url"
            type="url"
            placeholder="https://sua-evolution.com"
            class="w-full px-4 py-2.5 bg-white/5 border border-white/10 rounded-lg text-sm text-white focus:border-orange-500/50 focus:outline-none"
          >
        </div>

        <div>
          <label class="block text-xs font-bold uppercase tracking-wider text-neutral-400 mb-1.5">Instance name</label>
          <input
            v-model="form.instance"
            type="text"
            placeholder="minha-instancia"
            class="w-full px-4 py-2.5 bg-white/5 border border-white/10 rounded-lg text-sm text-white focus:border-orange-500/50 focus:outline-none"
          >
        </div>

        <div>
          <label class="block text-xs font-bold uppercase tracking-wider text-neutral-400 mb-1.5">Instance API key</label>
          <input
            v-model="form.api_key"
            type="password"
            autocomplete="off"
            placeholder="••••••••••••"
            class="w-full px-4 py-2.5 bg-white/5 border border-white/10 rounded-lg text-sm text-white focus:border-orange-500/50 focus:outline-none"
          >
        </div>

        <label class="flex items-center gap-3 cursor-pointer select-none">
          <input v-model="form.is_active" type="checkbox" class="accent-orange-500 w-4 h-4">
          <span class="text-sm text-white">Ativo</span>
          <span class="text-xs text-neutral-500">— envia WhatsApp aos novos alunos com telefone</span>
        </label>

        <div class="flex justify-end pt-2 border-t border-white/5">
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
    </section>
  </div>
</template>
