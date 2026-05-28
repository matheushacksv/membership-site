<script setup lang="ts">
import { Plus, Loader2, ImageOff, Eye, EyeOff } from 'lucide-vue-next'
import type { AdminCourse, CourseInput } from '~/composables/useAdmin'

definePageMeta({ layout: 'admin', middleware: 'admin' })
useHead({ title: 'Cursos — Admin' })

const admin = useAdmin()
const toast = useToast()

const { data: courses, pending, refresh } = await useAsyncData(
  'admin-courses',
  () => admin.listCourses()
)

const showCreate = ref(false)
const creating = ref(false)
const form = reactive<CourseInput>({
  name: '',
  category: 'sales',
  sales_page: '',
  checkout_link: '',
  is_active: true,
})

const CATEGORIES = [
  { value: 'sales', label: 'Vendas' },
  { value: 'marketing', label: 'Marketing' },
  { value: 'strategy', label: 'Estratégia' },
  { value: 'tool', label: 'Ferramentas' },
  { value: 'customer', label: 'Customer Success' },
  { value: 'lifestyle', label: 'Estilo de Vida' },
  { value: 'development', label: 'Desenvolvimento' },
]

const resetForm = () => {
  form.name = ''
  form.category = 'sales'
  form.sales_page = ''
  form.checkout_link = ''
  form.is_active = true
}

const submit = async () => {
  if (!form.name.trim()) return
  creating.value = true
  try {
    const c = await admin.createCourse({
      name: form.name,
      category: form.category,
      sales_page: form.sales_page || null,
      checkout_link: form.checkout_link || null,
      is_active: form.is_active,
    })
    toast.success('Curso criado')
    showCreate.value = false
    resetForm()
    await navigateTo(`/admin/courses/${c.id}/edit`)
  } catch (e: any) {
    toast.error(e?.data?.detail || 'Falha ao criar curso')
  } finally {
    creating.value = false
  }
}
</script>

<template>
  <div class="space-y-8">
    <header class="flex items-end justify-between">
      <div>
        <h1 class="text-3xl font-medium tracking-tight">Cursos</h1>
        <p class="text-sm text-neutral-500 mt-1">Crie e gerencie o catálogo</p>
      </div>
      <button
        type="button"
        class="inline-flex items-center gap-2 px-4 py-2.5 bg-orange-500 hover:bg-orange-400 text-black font-bold uppercase tracking-wider text-xs rounded-lg transition-colors"
        @click="showCreate = true"
      >
        <Plus class="w-4 h-4" />
        Novo curso
      </button>
    </header>

    <div v-if="pending" class="flex justify-center py-16">
      <Loader2 class="w-6 h-6 text-orange-500 animate-spin" />
    </div>

    <div
      v-else-if="courses?.length"
      class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5"
    >
      <NuxtLink
        v-for="c in courses"
        :key="c.id"
        :to="`/admin/courses/${c.id}/edit`"
        class="group block bg-white/[0.03] border border-white/10 rounded-xl overflow-hidden hover:border-orange-500/40 hover:-translate-y-0.5 transition-all"
      >
        <div class="relative aspect-video bg-gradient-to-br from-orange-500/10 via-neutral-900 to-neutral-950">
          <img
            v-if="c.image"
            :src="c.image"
            :alt="c.name"
            class="absolute inset-0 w-full h-full object-cover"
          >
          <div v-else class="absolute inset-0 flex items-center justify-center">
            <ImageOff class="w-8 h-8 text-neutral-700" />
          </div>
          <span
            v-if="!c.is_active"
            class="absolute top-3 left-3 text-[10px] font-bold uppercase tracking-widest px-2 py-1 rounded-full bg-black/70 text-neutral-400 border border-white/10 inline-flex items-center gap-1"
          >
            <EyeOff class="w-3 h-3" />
            Rascunho
          </span>
          <span
            v-else
            class="absolute top-3 left-3 text-[10px] font-bold uppercase tracking-widest px-2 py-1 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 inline-flex items-center gap-1"
          >
            <Eye class="w-3 h-3" />
            Publicado
          </span>
        </div>
        <div class="p-4">
          <h3 class="font-medium text-white truncate">{{ c.name }}</h3>
          <p class="text-xs text-neutral-500 uppercase tracking-wider mt-1">
            {{ c.category }}
          </p>
        </div>
      </NuxtLink>
    </div>

    <div
      v-else
      class="bg-white/[0.02] border border-white/5 rounded-xl py-16 text-center"
    >
      <p class="text-sm text-neutral-500">
        Nenhum curso ainda. Clique em <strong>Novo curso</strong> pra começar.
      </p>
    </div>

    <!-- Modal: Novo curso -->
    <AdminModal :open="showCreate" title="Novo curso" @close="showCreate = false">
      <form class="space-y-4" @submit.prevent="submit">
        <div>
          <label class="block text-xs font-bold uppercase tracking-wider text-neutral-400 mb-1.5">Nome</label>
          <input
            v-model="form.name"
            type="text"
            required
            placeholder="Ex: Vendas High Ticket"
            class="w-full px-4 py-2.5 bg-white/5 border border-white/10 rounded-lg text-sm text-white focus:border-orange-500/50 focus:outline-none transition-colors"
          >
        </div>

        <div>
          <label class="block text-xs font-bold uppercase tracking-wider text-neutral-400 mb-1.5">Categoria</label>
          <select
            v-model="form.category"
            class="w-full px-4 py-2.5 bg-white/5 border border-white/10 rounded-lg text-sm text-white focus:border-orange-500/50 focus:outline-none"
          >
            <option v-for="c in CATEGORIES" :key="c.value" :value="c.value" class="bg-black">
              {{ c.label }}
            </option>
          </select>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
          <div>
            <label class="block text-xs font-bold uppercase tracking-wider text-neutral-400 mb-1.5">Página de vendas</label>
            <input
              v-model="form.sales_page"
              type="url"
              placeholder="https://..."
              class="w-full px-4 py-2.5 bg-white/5 border border-white/10 rounded-lg text-sm text-white focus:border-orange-500/50 focus:outline-none"
            >
          </div>
          <div>
            <label class="block text-xs font-bold uppercase tracking-wider text-neutral-400 mb-1.5">Checkout</label>
            <input
              v-model="form.checkout_link"
              type="url"
              placeholder="https://..."
              class="w-full px-4 py-2.5 bg-white/5 border border-white/10 rounded-lg text-sm text-white focus:border-orange-500/50 focus:outline-none"
            >
          </div>
        </div>

        <label class="flex items-center gap-2 text-sm text-neutral-400 cursor-pointer">
          <input v-model="form.is_active" type="checkbox" class="accent-orange-500">
          Publicar agora
        </label>

        <div class="flex justify-end gap-2 pt-4 border-t border-white/5">
          <button
            type="button"
            class="px-4 py-2 text-sm text-neutral-400 hover:text-white"
            @click="showCreate = false"
          >
            Cancelar
          </button>
          <button
            type="submit"
            :disabled="creating || !form.name.trim()"
            class="inline-flex items-center gap-2 px-5 py-2 bg-orange-500 hover:bg-orange-400 disabled:opacity-50 text-black font-bold uppercase tracking-wider text-xs rounded-lg"
          >
            <Loader2 v-if="creating" class="w-3.5 h-3.5 animate-spin" />
            Criar e editar
          </button>
        </div>
      </form>
    </AdminModal>
  </div>
</template>
