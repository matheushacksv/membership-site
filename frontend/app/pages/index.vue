<script setup lang="ts">
import { computed, ref } from 'vue'
import { Search, RefreshCw, AlertCircle } from 'lucide-vue-next'
import type { CourseListItem } from '~/composables/useCatalog'

definePageMeta({ layout: 'default' })
useHead({ title: 'Início — Grupo Enriquecedor' })

const { data: me } = useMe()
const { myCourses, availableCourses, banners } = useCatalog()

const { data: bannerList } = await useAsyncData('home-banners', () => banners())

const category = ref('')
const search = ref('')

const {
  data: mine,
  pending: pendingMine,
  error: errorMine,
  refresh: refreshMine,
} = await useAsyncData('home-mine', () => myCourses())

const {
  data: available,
  pending: pendingAvailable,
  error: errorAvailable,
  refresh: refreshAvailable,
} = await useAsyncData(
  'home-available',
  () => availableCourses(category.value || undefined),
  { watch: [category] }
)

const matches = (c: CourseListItem, term: string) =>
  c.name.toLowerCase().includes(term)

const filteredMine = computed<CourseListItem[]>(() => {
  const term = search.value.trim().toLowerCase()
  if (!term) return mine.value || []
  return (mine.value || []).filter((c) => matches(c, term))
})

const filteredAvailable = computed<CourseListItem[]>(() => {
  const term = search.value.trim().toLowerCase()
  if (!term) return available.value || []
  return (available.value || []).filter((c) => matches(c, term))
})
</script>

<template>
  <div class="space-y-10 md:space-y-14">
    <!-- Hero -->
    <section class="animate-fade-slide">
      <div class="inline-flex items-center gap-2 mb-4">
        <span class="flex h-2 w-2 rounded-full bg-orange-500" />
        <span class="text-xs font-bold tracking-widest uppercase text-orange-500/80">Sua área</span>
      </div>
      <h1 class="text-4xl md:text-6xl font-medium tracking-tighter leading-[0.95]">
        Olá,
        <span class="text-transparent bg-clip-text bg-gradient-to-r from-white via-neutral-200 to-neutral-500">
          {{ me?.name || 'aluno' }}
        </span>
      </h1>
      <p class="text-base text-white/60 mt-4 max-w-xl">
        Continue de onde parou ou descubra novos conteúdos.
      </p>

      <!-- Banners (destaques do staff) -->
      <BannerCarousel v-if="bannerList?.length" :banners="bannerList" class="mt-8" />

      <!-- Busca -->
      <div class="relative mt-6 max-w-md">
        <Search class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-500" />
        <input
          v-model="search"
          type="search"
          placeholder="Buscar curso..."
          class="w-full pl-10 pr-4 py-2.5 bg-white/5 border border-white/10 rounded-lg text-sm text-white placeholder:text-neutral-500 focus:outline-none focus:border-orange-500/40 focus:bg-white/[0.07] transition-colors"
        >
      </div>
    </section>

    <!-- Continue aprendendo -->
    <section class="animate-fade-slide">
      <div class="flex items-end justify-between mb-6">
        <div>
          <h2 class="text-2xl md:text-3xl font-medium tracking-tighter">Continue aprendendo</h2>
          <p class="text-xs text-neutral-500 mt-1">Seus cursos matriculados</p>
        </div>
        <span
          v-if="mine?.length && !search"
          class="text-xs font-bold tracking-widest uppercase text-neutral-500"
        >
          {{ mine.length }} {{ mine.length === 1 ? 'curso' : 'cursos' }}
        </span>
      </div>

      <!-- Loading -->
      <div
        v-if="pendingMine"
        class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6"
      >
        <CourseCardSkeleton v-for="n in 3" :key="n" />
      </div>

      <!-- Erro -->
      <div
        v-else-if="errorMine"
        class="bg-white/5 border border-red-500/20 rounded-xl p-8 text-center"
      >
        <AlertCircle class="w-6 h-6 text-red-400 mx-auto mb-3" />
        <p class="text-sm text-white/70">Não foi possível carregar seus cursos.</p>
        <button
          type="button"
          class="mt-4 inline-flex items-center gap-2 px-4 py-2 bg-white/5 hover:bg-white/10 border border-white/10 rounded-lg text-xs font-bold uppercase tracking-wider text-neutral-300 transition-colors"
          @click="refreshMine()"
        >
          <RefreshCw class="w-3.5 h-3.5" />
          Tentar novamente
        </button>
      </div>

      <!-- Lista -->
      <div
        v-else-if="filteredMine.length"
        class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6"
      >
        <CourseCard v-for="c in filteredMine" :key="c.id" :course="c" variant="enrolled" />
      </div>

      <!-- Vazio por busca -->
      <p
        v-else-if="search"
        class="text-sm text-neutral-500 text-center py-12 bg-white/[0.02] border border-white/5 rounded-xl"
      >
        Nenhum curso encontrado para "{{ search }}".
      </p>

      <!-- Vazio sem cursos -->
      <div
        v-else
        class="bg-white/5 border border-white/10 rounded-xl p-10 text-center"
      >
        <p class="text-sm text-white/60">
          Você ainda não tem cursos. Explore o catálogo abaixo.
        </p>
      </div>
    </section>

    <!-- Disponíveis -->
    <section
      v-if="available?.length || category || search"
      class="animate-fade-slide"
    >
      <div class="flex items-end justify-between mb-4">
        <div>
          <h2 class="text-2xl md:text-3xl font-medium tracking-tighter">
            Disponíveis pra você
          </h2>
          <p class="text-xs text-neutral-500 mt-1">Explore novos conteúdos</p>
        </div>
      </div>

      <CategoryChips v-model="category" class="mb-6" />

      <!-- Loading -->
      <div
        v-if="pendingAvailable"
        class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6"
      >
        <CourseCardSkeleton v-for="n in 3" :key="n" />
      </div>

      <!-- Erro -->
      <div
        v-else-if="errorAvailable"
        class="bg-white/5 border border-red-500/20 rounded-xl p-8 text-center"
      >
        <AlertCircle class="w-6 h-6 text-red-400 mx-auto mb-3" />
        <p class="text-sm text-white/70">Não foi possível carregar o catálogo.</p>
        <button
          type="button"
          class="mt-4 inline-flex items-center gap-2 px-4 py-2 bg-white/5 hover:bg-white/10 border border-white/10 rounded-lg text-xs font-bold uppercase tracking-wider text-neutral-300 transition-colors"
          @click="refreshAvailable()"
        >
          <RefreshCw class="w-3.5 h-3.5" />
          Tentar novamente
        </button>
      </div>

      <!-- Lista -->
      <div
        v-else-if="filteredAvailable.length"
        class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6"
      >
        <CourseCard v-for="c in filteredAvailable" :key="c.id" :course="c" variant="available" />
      </div>

      <!-- Vazio -->
      <p
        v-else
        class="text-sm text-neutral-500 text-center py-12 bg-white/[0.02] border border-white/5 rounded-xl"
      >
        {{ search ? `Nenhum curso encontrado para "${search}".` : 'Nenhum curso encontrado nesta categoria.' }}
      </p>
    </section>
  </div>
</template>
