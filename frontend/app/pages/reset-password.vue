<script setup lang="ts">
import { ref, computed } from 'vue'
import { FetchError } from 'ofetch'
import { CheckCircle2, AlertCircle, Loader2, Mail } from 'lucide-vue-next'

definePageMeta({ layout: 'auth' })
useHead({ title: 'Redefinir senha — Grupo Enriquecedor' })

const route = useRoute()
const api = useApi()

const uid = computed(() => String(route.query.uid || ''))
const token = computed(() => String(route.query.token || ''))
// Vindo do /magic o usuário JÁ está logado: o destino final é a plataforma, não o
// login, e trocar a senha agora é opcional (dá pra seguir e trocar depois no perfil).
const fromMagic = computed(() => route.query.magic === '1')

const password = ref('')
const repeatPassword = ref('')
const loading = ref(false)
const error = ref<string | null>(null)
const success = ref(false)

const validating = ref(true)
const linkValid = ref(false)
const linkError = ref<string | null>(null)

const resending = ref(false)
const resent = ref(false)
const resendError = ref<string | null>(null)

const passwordError = computed(() => {
  if (!password.value) return null
  if (password.value.length < 8) return 'Mínimo 8 caracteres'
  return null
})

const confirmError = computed(() => {
  if (!repeatPassword.value) return null
  if (password.value !== repeatPassword.value) return 'Senhas não coincidem'
  return null
})

const validateLink = async () => {
  if (!uid.value || !token.value) {
    linkValid.value = false
    linkError.value = 'Link inválido — parâmetros ausentes.'
    validating.value = false
    return
  }
  try {
    await api('/auth/reset-password/validate', {
      method: 'GET',
      query: { uid: uid.value, token: token.value },
    })
    linkValid.value = true
  } catch (e) {
    linkValid.value = false
    if (e instanceof FetchError) {
      linkError.value = e.data?.detail || 'Link inválido ou expirado.'
    } else {
      linkError.value = 'Erro ao validar link.'
    }
  } finally {
    validating.value = false
  }
}

await validateLink()

const resendLink = async () => {
  resendError.value = null
  resending.value = true
  try {
    await api('/auth/reset-password/resend', {
      method: 'POST',
      body: { uid: uid.value },
    })
    resent.value = true
  } catch (e) {
    if (e instanceof FetchError) {
      resendError.value = e.data?.detail || 'Erro ao reenviar o link'
    } else {
      resendError.value = 'Erro inesperado'
    }
  } finally {
    resending.value = false
  }
}

const onSubmit = async () => {
  error.value = null

  if (passwordError.value || confirmError.value) {
    error.value = passwordError.value || confirmError.value
    return
  }
  if (!password.value || !repeatPassword.value) {
    error.value = 'Preencha ambos os campos'
    return
  }

  loading.value = true
  try {
    await api('/auth/reset-password', {
      method: 'POST',
      body: {
        uid: uid.value,
        token: token.value,
        password: password.value,
        repeat_password: repeatPassword.value,
      },
    })
    success.value = true
    setTimeout(() => navigateTo(fromMagic.value ? '/' : '/login'), 2500)
  } catch (e) {
    if (e instanceof FetchError) {
      error.value = e.data?.detail || 'Erro ao redefinir senha'
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
        Nova senha
      </span>
    </div>

    <div
      class="relative bg-white/5 border border-white/10 backdrop-blur-md rounded-xl p-8 md:p-10 shadow-2xl"
      style="--border-gradient: linear-gradient(180deg, rgba(255,255,255,0.12), rgba(255,255,255,0)); --border-radius-before: 12px;"
    >
      <!-- Validating -->
      <div v-if="validating" class="flex flex-col items-center justify-center py-8">
        <Loader2 class="w-8 h-8 text-orange-500 animate-spin mb-4" />
        <p class="text-sm text-white/60">Validando link...</p>
      </div>

      <!-- Resent confirmation -->
      <template v-else-if="resent">
        <div class="flex items-center gap-3 mb-4">
          <div class="w-10 h-10 rounded-full bg-orange-500/20 border border-orange-500/40 flex items-center justify-center">
            <Mail class="w-5 h-5 text-orange-400" />
          </div>
          <h1 class="text-2xl md:text-3xl font-medium tracking-tighter text-white leading-[1.1]">
            Novo link enviado
          </h1>
        </div>
        <p class="text-sm text-white/60 mb-6">
          Enviamos um novo link para o seu email. Abra-o para definir sua senha — ele vale por 24h.
        </p>
        <p class="text-xs text-neutral-500 mb-6">
          Não chegou? Confira a caixa de spam ou aguarde alguns minutos.
        </p>
      </template>

      <!-- Invalid link -->
      <template v-else-if="!linkValid">
        <div class="flex items-center gap-3 mb-4">
          <div class="w-10 h-10 rounded-full bg-red-500/20 border border-red-500/40 flex items-center justify-center">
            <AlertCircle class="w-5 h-5 text-red-400" />
          </div>
          <h1 class="text-2xl md:text-3xl font-medium tracking-tighter text-white leading-[1.1]">
            Link inválido
          </h1>
        </div>
        <p class="text-sm text-white/60 mb-6">
          {{ linkError }}
        </p>
        <p class="text-xs text-neutral-500 mb-6">
          O link pode ter expirado (válido por 24h) ou já ter sido usado.
        </p>

        <Transition name="fade">
          <div
            v-if="resendError"
            class="bg-red-500/10 border border-red-500/30 text-red-300 text-sm rounded-lg px-3 py-2 mb-4"
            role="alert"
          >
            {{ resendError }}
          </div>
        </Transition>

        <template v-if="uid">
          <PrimaryButton type="button" :loading="resending" :show-arrow="false" @click="resendLink">
            Receber novo link
          </PrimaryButton>
          <NuxtLink
            to="/forgot-password"
            class="block w-full text-center py-2 mt-2 text-xs text-neutral-500 hover:text-neutral-300 transition-colors"
          >
            Usar outro email
          </NuxtLink>
        </template>
        <NuxtLink
          v-else
          to="/forgot-password"
          class="block w-full text-center py-2 text-sm text-orange-500 hover:text-orange-400 transition-colors"
        >
          Solicitar novo link
        </NuxtLink>
      </template>

      <!-- Success -->
      <template v-else-if="success">
        <div class="flex items-center gap-3 mb-4">
          <div class="w-10 h-10 rounded-full bg-green-500/20 border border-green-500/40 flex items-center justify-center">
            <CheckCircle2 class="w-5 h-5 text-green-400" />
          </div>
          <h1 class="text-2xl md:text-3xl font-medium tracking-tighter text-white leading-[1.1]">
            Senha redefinida
          </h1>
        </div>
        <p class="text-sm text-white/60 mb-6">
          Sua senha foi atualizada com sucesso.
          {{ fromMagic ? 'Levando você para a plataforma...' : 'Redirecionando para o login...' }}
        </p>
        <NuxtLink
          :to="fromMagic ? '/' : '/login'"
          class="block w-full text-center py-2 text-sm text-orange-500 hover:text-orange-400 transition-colors"
        >
          {{ fromMagic ? 'Ir para a plataforma agora' : 'Ir para login agora' }}
        </NuxtLink>
      </template>

      <!-- Form -->
      <template v-else>
        <h1 class="text-3xl md:text-4xl font-medium tracking-tighter text-white mb-2 leading-[1.05]">
          Defina sua
          <span class="text-transparent bg-clip-text bg-gradient-to-r from-white via-neutral-200 to-neutral-500">nova senha</span>
        </h1>
        <p class="text-sm text-white/60 mb-8">
          {{
            fromMagic
              ? 'Você já está dentro. Crie uma senha agora para entrar sozinho da próxima vez, sem precisar de link.'
              : 'Escolha uma senha forte com pelo menos 8 caracteres.'
          }}
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
            v-model="password"
            type="password"
            placeholder="Mínimo 8 caracteres"
            icon="lock"
            autocomplete="new-password"
            label="Nova senha"
            :error="passwordError"
            required
          />
          <AppInput
            v-model="repeatPassword"
            type="password"
            placeholder="Confirme a nova senha"
            icon="lock"
            autocomplete="new-password"
            label="Confirmar senha"
            :error="confirmError"
            required
          />
          <PrimaryButton :loading="loading">Redefinir senha</PrimaryButton>
        </form>
      </template>

      <div v-if="!validating" class="my-6 flex items-center gap-3">
        <div class="flex-1 h-px bg-white/5" />
        <span class="text-[10px] font-bold tracking-widest uppercase text-neutral-600">ou</span>
        <div class="flex-1 h-px bg-white/5" />
      </div>

      <p v-if="!validating" class="text-center text-sm text-neutral-500">
        <NuxtLink
          :to="fromMagic ? '/' : '/login'"
          class="text-orange-500 hover:text-orange-400 font-medium transition-colors"
        >
          {{ fromMagic ? 'Continuar sem trocar a senha' : 'Voltar ao login' }}
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
