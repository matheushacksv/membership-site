<script setup lang="ts">
import { CheckCircle2, Send } from 'lucide-vue-next'

definePageMeta({ layout: false })

interface FreeCourseLP {
  id: number
  name: string
  image: string | null
  lp_template: string
}
interface FreeSignupOut {
  created: boolean
  course_id: number
  access: string | null
  refresh: string | null
}

const route = useRoute()
const api = useApi()
const { setSession } = useAuth()
const slug = String(route.params.slug)

// Info pública do curso grátis (404 se não existir / não for is_free).
const { data: course } = await useAsyncData(`lp-${slug}`, () =>
  api<FreeCourseLP>(`/catalog/free/${slug}`).catch(() => null)
)

const isCloser = computed(() => course.value?.lp_template === 'closer')

useHead({ title: () => (course.value ? `${course.value.name} — Acesso gratuito` : 'Curso não encontrado') })

const name = ref('')
const email = ref('')
const phone = ref('')
const loading = ref(false)
const error = ref<string | null>(null)
const sent = ref(false) // conta já existente: acesso enviado por email/WhatsApp

const onSubmit = async () => {
  error.value = null
  loading.value = true
  try {
    const res = await api<FreeSignupOut>(`/catalog/free/${slug}/signup`, {
      method: 'POST',
      body: { name: name.value, email: email.value, phone: phone.value },
    })
    if (res.created && res.access && res.refresh) {
      setSession({ access: res.access, refresh: res.refresh })
      await navigateTo(`/courses/${res.course_id}`)
    } else {
      // Email já cadastrado: não logamos por segurança — acesso vai pelos canais dele.
      sent.value = true
    }
  } catch (e: any) {
    error.value = e?.data?.detail || 'Não foi possível concluir. Tente novamente.'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <!-- Curso não encontrado -->
  <div
    v-if="!course"
    class="min-h-screen bg-[#050505] text-white flex items-center justify-center px-6 py-10 text-center"
  >
    <div class="max-w-md">
      <h1 class="text-2xl font-medium tracking-tight mb-2">Curso não encontrado</h1>
      <p class="text-sm text-white/60">Este link pode ter expirado ou o curso não está mais disponível.</p>
      <NuxtLink to="/login" class="inline-block mt-6 text-sm text-orange-500 hover:text-orange-400 font-medium">
        Ir para o login
      </NuxtLink>
    </div>
  </div>

  <!-- Acesso enviado (conta já existia) -->
  <div
    v-else-if="sent"
    class="min-h-screen bg-[#050505] text-white flex items-center justify-center px-6 py-10 text-center"
  >
    <div class="max-w-md">
      <CheckCircle2 class="w-12 h-12 text-emerald-400 mx-auto mb-4" />
      <h1 class="text-2xl font-medium tracking-tight mb-2">Acesso liberado!</h1>
      <p class="text-sm text-white/70">
        Você já tinha conta. Enviamos o link de acesso ao <strong>{{ course.name }}</strong> por email<span v-if="phone"> e WhatsApp</span>.
      </p>
      <NuxtLink to="/login" class="inline-block mt-6 text-sm text-orange-500 hover:text-orange-400 font-medium">
        Entrar agora
      </NuxtLink>
    </div>
  </div>

  <!-- Variante SDR e Closer (Grupo Enriquecedor) -->
  <LpCloserLanding v-else-if="isCloser" :course="course">
    <template #form>
      <h2 class="text-xl font-bold tracking-tight text-white mb-1">Garanta sua vaga na próxima fase</h2>
      <p class="text-sm text-white/60 mb-6">Cadastre-se para liberar o acesso agora. O login também vai por email e WhatsApp.</p>
      <Transition name="fade">
        <div v-if="error" class="bg-red-500/10 border border-red-500/30 text-red-300 text-sm rounded-lg px-3 py-2 mb-4" role="alert">
          {{ error }}
        </div>
      </Transition>
      <form class="space-y-4" @submit.prevent="onSubmit">
        <AppInput v-model="name" type="text" placeholder="Seu nome" icon="user" autocomplete="name" label="Nome" required />
        <AppInput v-model="email" type="email" placeholder="seu@email.com" icon="mail" autocomplete="email" label="Email" required />
        <AppInput v-model="phone" type="tel" placeholder="(11) 99999-9999" autocomplete="tel" label="WhatsApp" required />
        <PrimaryButton :loading="loading">
          <Send class="w-4 h-4" />
          Quero meu acesso
        </PrimaryButton>
      </form>
    </template>
  </LpCloserLanding>

  <!-- Variante padrão (form simples) -->
  <div v-else class="min-h-screen bg-[#050505] text-white flex items-center justify-center px-6 py-10">
    <div class="w-full max-w-md mx-auto">
      <div class="inline-flex items-center gap-2 mb-6">
        <span class="flex h-2 w-2 rounded-full bg-emerald-500" />
        <span class="text-xs font-bold tracking-widest uppercase text-emerald-500/80">Acesso gratuito</span>
      </div>

      <div class="relative bg-white/5 border border-white/10 backdrop-blur-md rounded-xl p-8 md:p-10 shadow-2xl">
        <img
          v-if="course.image"
          :src="course.image"
          :alt="course.name"
          class="w-full aspect-video object-cover rounded-lg mb-6 border border-white/10"
        >
        <h1 class="text-2xl md:text-3xl font-medium tracking-tighter text-white mb-2 leading-[1.1]">
          {{ course.name }}
        </h1>
        <p class="text-sm text-white/60 mb-8">
          Preencha para liberar seu acesso na hora. O login também vai para seu email e WhatsApp.
        </p>

        <Transition name="fade">
          <div v-if="error" class="bg-red-500/10 border border-red-500/30 text-red-300 text-sm rounded-lg px-3 py-2 mb-4" role="alert">
            {{ error }}
          </div>
        </Transition>

        <form class="space-y-4" @submit.prevent="onSubmit">
          <AppInput v-model="name" type="text" placeholder="Seu nome" icon="user" autocomplete="name" label="Nome" required />
          <AppInput v-model="email" type="email" placeholder="seu@email.com" icon="mail" autocomplete="email" label="Email" required />
          <AppInput v-model="phone" type="tel" placeholder="(11) 99999-9999" autocomplete="tel" label="WhatsApp" required />
          <PrimaryButton :loading="loading">
            <Send class="w-4 h-4" />
            Quero meu acesso
          </PrimaryButton>
        </form>

        <p class="text-center text-xs text-neutral-600 mt-6">
          Já tem conta?
          <NuxtLink to="/login" class="text-orange-500 hover:text-orange-400 font-medium">Entrar</NuxtLink>
        </p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
