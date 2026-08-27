<script setup lang="ts">
import { ref, computed } from 'vue'
import { FetchError } from 'ofetch'

definePageMeta({ layout: 'auth' })
useHead({ title: 'Cadastro | Grupo Enriquecedor' })

const { register } = useAuth()
const route = useRoute()

const name = ref('')
const email = ref('')
const password = ref('')
const passwordConfirm = ref('')
const loading = ref(false)
const error = ref<string | null>(null)

const passwordError = computed(() => {
  if (!password.value) return null
  if (password.value.length < 8) return 'Mínimo 8 caracteres'
  return null
})

const confirmError = computed(() => {
  if (!passwordConfirm.value) return null
  if (password.value !== passwordConfirm.value) return 'Senhas não coincidem'
  return null
})

const onSubmit = async () => {
  error.value = null

  if (!email.value || !password.value) {
    error.value = 'Preencha email e senha'
    return
  }
  if (passwordError.value || confirmError.value) {
    error.value = passwordError.value || confirmError.value
    return
  }

  loading.value = true
  try {
    const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : '/'
    await register(email.value, password.value, name.value, redirect)
  } catch (e) {
    if (e instanceof FetchError) {
      error.value = e.data?.detail || 'Erro ao cadastrar'
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
    <div class="inline-flex items-center gap-2 mb-6">
      <span class="flex h-2 w-2 rounded-full bg-orange-500" />
      <span class="text-xs font-bold tracking-widest uppercase text-orange-500/80">Comece agora</span>
    </div>

    <div
      class="relative bg-white/5 border border-white/10 backdrop-blur-md rounded-xl p-8 md:p-10 shadow-2xl"
      style="--border-gradient: linear-gradient(180deg, rgba(255,255,255,0.12), rgba(255,255,255,0)); --border-radius-before: 12px;"
    >
      <h1 class="text-3xl md:text-4xl font-medium tracking-tighter text-white mb-2 leading-[1.05]">
        Crie sua
        <span class="text-transparent bg-clip-text bg-gradient-to-r from-white via-neutral-200 to-neutral-500">conta</span>
      </h1>
      <p class="text-sm text-white/60 mb-8">Comece sua jornada de aprendizado hoje.</p>

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
          v-model="name"
          type="text"
          placeholder="Seu nome (opcional)"
          icon="user"
          autocomplete="name"
          label="Nome"
        />
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
          placeholder="Mínimo 8 caracteres"
          icon="lock"
          autocomplete="new-password"
          label="Senha"
          :error="passwordError"
          required
        />
        <AppInput
          v-model="passwordConfirm"
          type="password"
          placeholder="Confirme a senha"
          icon="lock"
          autocomplete="new-password"
          label="Confirmar senha"
          :error="confirmError"
          required
        />

        <PrimaryButton :loading="loading">Cadastrar</PrimaryButton>
      </form>

      <div class="my-6 flex items-center gap-3">
        <div class="flex-1 h-px bg-white/5" />
        <span class="text-[10px] font-bold tracking-widest uppercase text-neutral-600">ou</span>
        <div class="flex-1 h-px bg-white/5" />
      </div>

      <p class="text-center text-sm text-neutral-500">
        Já tem conta?
        <NuxtLink to="/login" class="text-orange-500 hover:text-orange-400 font-medium transition-colors">
          Entre
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
