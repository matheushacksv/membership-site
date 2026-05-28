<script setup lang="ts">
import { ref } from 'vue'
import { FetchError } from 'ofetch'
import { Mail } from 'lucide-vue-next'

definePageMeta({ layout: 'auth' })
useHead({ title: 'Recuperar senha — Área de Membros' })

const api = useApi()

const email = ref('')
const loading = ref(false)
const error = ref<string | null>(null)
const sent = ref(false)

const onSubmit = async () => {
  error.value = null
  if (!email.value) {
    error.value = 'Informe seu email'
    return
  }

  loading.value = true
  try {
    await api('/auth/forgot-password', {
      method: 'POST',
      body: { email: email.value },
    })
    sent.value = true
  } catch (e) {
    if (e instanceof FetchError) {
      error.value = e.data?.detail || 'Erro ao solicitar redefinição'
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
      <span class="text-xs font-bold tracking-widest uppercase text-orange-500/80">
        Recuperar acesso
      </span>
    </div>

    <div
      class="relative bg-white/5 border border-white/10 backdrop-blur-md rounded-xl p-8 md:p-10 shadow-2xl"
      style="--border-gradient: linear-gradient(180deg, rgba(255,255,255,0.12), rgba(255,255,255,0)); --border-radius-before: 12px;"
    >
      <template v-if="!sent">
        <h1 class="text-3xl md:text-4xl font-medium tracking-tighter text-white mb-2 leading-[1.05]">
          Esqueceu sua
          <span class="text-transparent bg-clip-text bg-gradient-to-r from-white via-neutral-200 to-neutral-500">senha?</span>
        </h1>
        <p class="text-sm text-white/60 mb-8">
          Informe o email da conta e enviaremos um link para redefinir.
        </p>

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
          <PrimaryButton :loading="loading">Enviar link</PrimaryButton>
        </form>
      </template>

      <template v-else>
        <div class="flex items-center gap-3 mb-4">
          <div class="w-10 h-10 rounded-full bg-orange-500/20 border border-orange-500/40 flex items-center justify-center">
            <Mail class="w-5 h-5 text-orange-400" />
          </div>
          <h1 class="text-2xl md:text-3xl font-medium tracking-tighter text-white leading-[1.1]">
            Verifique seu email
          </h1>
        </div>
        <p class="text-sm text-white/60 mb-6">
          Se uma conta existir com <span class="text-white">{{ email }}</span>, você receberá um link para redefinir sua senha em alguns instantes.
        </p>
        <p class="text-xs text-neutral-500 mb-6">
          Não chegou? Confira a caixa de spam ou aguarde alguns minutos.
        </p>

        <button
          type="button"
          class="w-full text-sm text-neutral-400 hover:text-white transition-colors py-2"
          @click="sent = false"
        >
          Tentar com outro email
        </button>
      </template>

      <div class="my-6 flex items-center gap-3">
        <div class="flex-1 h-px bg-white/5" />
        <span class="text-[10px] font-bold tracking-widest uppercase text-neutral-600">ou</span>
        <div class="flex-1 h-px bg-white/5" />
      </div>

      <p class="text-center text-sm text-neutral-500">
        Lembrou a senha?
        <NuxtLink to="/login" class="text-orange-500 hover:text-orange-400 font-medium transition-colors">
          Voltar ao login
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
