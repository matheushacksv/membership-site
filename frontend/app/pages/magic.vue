<script setup lang="ts">
import { ref } from 'vue'
import { AlertCircle, Loader2 } from 'lucide-vue-next'

definePageMeta({ layout: 'auth' })
useHead({ title: 'Entrando | Grupo Enriquecedor' })

const route = useRoute()
const api = useApi()
const { access, refresh } = useAuth()

const token = String(route.query.token || '')
const error = ref<string | null>(null)

// Consome o link, grava os tokens nos cookies e entra. Feito no onMounted (client)
// pra escrita de cookie + navegação rodarem no browser, não no SSR.
onMounted(async () => {
  if (!token) {
    error.value = 'Link inválido, token ausente.'
    return
  }
  try {
    const data = await api<{
      access: string
      refresh: string
      reset_uid: string
      reset_token: string
    }>('/auth/magic/login', {
      method: 'POST',
      body: { token },
    })
    access.value = data.access
    refresh.value = data.refresh
    // Já entra logado, mas cai direto na tela de nova senha: o link prova posse do
    // canal, então o par uid/token que vem no response substitui a senha antiga.
    // Quem não quiser trocar agora tem o "continuar sem trocar" na própria tela.
    await navigateTo(
      `/reset-password?uid=${data.reset_uid}&token=${data.reset_token}&magic=1`
    )
  } catch (e: any) {
    error.value = e?.data?.detail || 'Link inválido ou expirado.'
  }
})
</script>

<template>
  <div class="w-full max-w-md mx-auto animate-fade-slide">
    <div class="inline-flex items-center gap-2 mb-6">
      <span class="flex h-2 w-2 rounded-full bg-orange-500" />
      <span class="text-xs font-bold tracking-widest uppercase text-orange-500/80">
        Acesso rápido
      </span>
    </div>

    <div
      class="relative bg-white/5 border border-white/10 backdrop-blur-md rounded-xl p-8 md:p-10 shadow-2xl"
      style="--border-gradient: linear-gradient(180deg, rgba(255,255,255,0.12), rgba(255,255,255,0)); --border-radius-before: 12px;"
    >
      <!-- Erro -->
      <template v-if="error">
        <div class="flex items-center gap-3 mb-4">
          <div class="w-10 h-10 rounded-full bg-red-500/20 border border-red-500/40 flex items-center justify-center">
            <AlertCircle class="w-5 h-5 text-red-400" />
          </div>
          <h1 class="text-2xl md:text-3xl font-medium tracking-tighter text-white leading-[1.1]">
            Link inválido
          </h1>
        </div>
        <p class="text-sm text-white/60 mb-6">
          {{ error }}
        </p>
        <p class="text-xs text-neutral-500 mb-6">
          O link de acesso pode ter expirado (válido por 2h). Peça um novo ou entre com email e senha.
        </p>
        <NuxtLink
          to="/login"
          class="block w-full text-center py-2 text-sm text-orange-500 hover:text-orange-400 font-medium transition-colors"
        >
          Ir para o login
        </NuxtLink>
      </template>

      <!-- Entrando -->
      <div v-else class="flex flex-col items-center justify-center py-8">
        <Loader2 class="w-8 h-8 text-orange-500 animate-spin mb-4" />
        <p class="text-sm text-white/60">Entrando...</p>
      </div>
    </div>
  </div>
</template>
