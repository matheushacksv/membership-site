<script setup lang="ts">
import { Loader2, Plug, MessageCircle, Video } from 'lucide-vue-next'
import type { EvolutionConfig, PandaConfig } from '~/composables/useAdmin'

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

// Panda Video — duração automática das aulas (carga horária dos certificados)
const panda = reactive<PandaConfig>({
  base_url: 'https://api-v2.pandavideo.com.br',
  api_key: '',
  is_active: false,
})
const savingPanda = ref(false)

const { pending: pendingPanda } = await useAsyncData('admin-panda-config', async () => {
  const cfg = await admin.getPandaConfig()
  Object.assign(panda, cfg)
  return cfg
})

const savePanda = async () => {
  savingPanda.value = true
  try {
    const cfg = await admin.savePandaConfig({ ...panda })
    Object.assign(panda, cfg)
    toast.success('Configuração salva')
  } catch (e: any) {
    toast.error(e?.data?.detail || 'Falha ao salvar')
  } finally {
    savingPanda.value = false
  }
}

const backfilling = ref(false)
const runBackfill = async () => {
  if (!confirm('Rebuscar a duração de todos os vídeos Panda? Roda em segundo plano.')) return
  backfilling.value = true
  try {
    const { queued } = await admin.pandaBackfill()
    toast.success(`${queued} vídeo(s) enfileirado(s) para recálculo`)
  } catch (e: any) {
    toast.error(e?.data?.detail || 'Falha ao iniciar recálculo')
  } finally {
    backfilling.value = false
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
        automático (válido 2h), reforçando o email.
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

    <!-- Panda Video — duração automática -->
    <section
      v-if="!pendingPanda"
      class="mt-6 bg-white/[0.02] border border-white/10 rounded-xl p-6 md:p-8"
    >
      <div class="flex items-center gap-2.5 mb-1">
        <Video class="w-4 h-4 text-sky-400" />
        <h2 class="text-base font-medium text-white">Panda Video — duração automática</h2>
      </div>
      <p class="text-xs text-neutral-500 mb-6">
        Ao salvar uma aula com vídeo do Panda, busca a duração e preenche a carga horária
        sozinho — base do cálculo automático dos certificados. Sem isso, a carga horária
        precisa ser informada à mão no curso.
      </p>

      <form class="space-y-5" @submit.prevent="savePanda">
        <div>
          <label class="block text-xs font-bold uppercase tracking-wider text-neutral-400 mb-1.5">URL da API</label>
          <input
            v-model="panda.base_url"
            type="url"
            placeholder="https://api-v2.pandavideo.com.br"
            class="w-full px-4 py-2.5 bg-white/5 border border-white/10 rounded-lg text-sm text-white focus:border-orange-500/50 focus:outline-none"
          >
        </div>

        <div>
          <label class="block text-xs font-bold uppercase tracking-wider text-neutral-400 mb-1.5">API key</label>
          <input
            v-model="panda.api_key"
            type="password"
            autocomplete="off"
            placeholder="••••••••••••"
            class="w-full px-4 py-2.5 bg-white/5 border border-white/10 rounded-lg text-sm text-white focus:border-orange-500/50 focus:outline-none"
          >
        </div>

        <label class="flex items-center gap-3 cursor-pointer select-none">
          <input v-model="panda.is_active" type="checkbox" class="accent-orange-500 w-4 h-4">
          <span class="text-sm text-white">Ativo</span>
          <span class="text-xs text-neutral-500">— busca a duração dos vídeos do Panda</span>
        </label>

        <div class="flex items-center justify-between gap-3 pt-2 border-t border-white/5">
          <button
            type="button"
            :disabled="backfilling || !panda.is_active"
            title="Rebusca a duração de todas as aulas Panda já cadastradas"
            class="inline-flex items-center gap-2 px-4 py-2 bg-white/5 hover:bg-white/10 border border-white/10 disabled:opacity-40 text-neutral-200 text-xs font-bold uppercase tracking-wider rounded-lg"
            @click="runBackfill"
          >
            <Loader2 v-if="backfilling" class="w-3.5 h-3.5 animate-spin" />
            Recalcular durações
          </button>
          <button
            type="submit"
            :disabled="savingPanda"
            class="inline-flex items-center gap-2 px-5 py-2 bg-orange-500 hover:bg-orange-400 disabled:opacity-50 text-white font-bold uppercase tracking-wider text-xs rounded-lg"
          >
            <Loader2 v-if="savingPanda" class="w-3.5 h-3.5 animate-spin" />
            Salvar
          </button>
        </div>
      </form>
    </section>
  </div>
</template>
