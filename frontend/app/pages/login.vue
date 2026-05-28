<script setup lang="ts">
import { ref } from 'vue'
import { FetchError } from 'ofetch'

definePageMeta({ layout: 'auth' })
useHead({ title: 'Entrar — Área de Membros' })

const { login } = useAuth()
const route = useRoute()

const email = ref('')
const password = ref('')
const loading = ref(false)
const error = ref<string | null>(null)

const onSubmit = async () => {
  error.value = null
  if (!email.value || !password.value) {
    error.value = 'Preencha email e senha'
    return
  }
  loading.value = true
  try {
    const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : '/'
    await login(email.value, password.value, redirect)
  } catch (e) {
    if (e instanceof FetchError) {
      error.value = e.data?.detail || 'Erro ao entrar'
    } else {
      error.value = 'Erro inesperado'
    }
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="w-full max-w-md mx-auto animate-fade-slide">
    <!-- Status pill -->
    <div class="inline-flex items-center gap-2 mb-6">
      <span class="flex h-2 w-2 rounded-full bg-orange-500" />
      <span class="text-xs font-bold tracking-widest uppercase text-orange-500/80">Acesso restrito</span>
    </div>

    <!-- Glass card -->
    <div
      class="relative bg-white/5 border border-white/10 backdrop-blur-md rounded-xl p-8 md:p-10 shadow-2xl"
      style="--border-gradient: linear-gradient(180deg, rgba(255,255,255,0.12), rgba(255,255,255,0)); --border-radius-before: 12px;"
    >
      <h1 class="text-3xl md:text-4xl font-medium tracking-tighter text-white mb-2 leading-[1.05]">
        Entre na sua
        <span class="text-transparent bg-clip-text bg-gradient-to-r from-white via-neutral-200 to-neutral-500">conta</span>
      </h1>
      <p class="text-sm text-white/60 mb-8">Acesse seus cursos e conteúdos exclusivos.</p>

      <Transition name="fade">
        <div
          v-if="error"
          class="bg-red-500/10 border border-red-500/30 text-red-300 text-sm rounded-lg px-3 py-2 mb-4"
          role="alert"
        >
          {{ error }}
        </div>
      </Transition>

      <form class="space-y-4" @submit.prevent="onSubmit">
        <AppInput
          v-model="email"
          type="email"
          placeholder="seu@email.com"
          icon="mail"
          autocomplete="email"
          label="Email"
          required
        />
        <AppInput
          v-model="password"
          type="password"
          placeholder="••••••••"
          icon="lock"
          autocomplete="current-password"
          label="Senha"
          required
        />

        <div class="flex justify-end -mt-1">
          <NuxtLink
            to="/forgot-password"
            class="text-xs text-neutral-400 hover:text-orange-400 transition-colors"
          >
            Esqueceu a senha?
          </NuxtLink>
        </div>

        <PrimaryButton :loading="loading">Entrar</PrimaryButton>
      </form>

      <div class="my-6 flex items-center gap-3">
        <div class="flex-1 h-px bg-white/5" />
        <span class="text-[10px] font-bold tracking-widest uppercase text-neutral-600">ou</span>
        <div class="flex-1 h-px bg-white/5" />
      </div>

      <p class="text-center text-sm text-neutral-500">
        Não tem conta?
        <NuxtLink to="/register" class="text-orange-500 hover:text-orange-400 font-medium transition-colors">
          Cadastre-se
        </NuxtLink>
      </p>
    </div>
  </div>
</template>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
