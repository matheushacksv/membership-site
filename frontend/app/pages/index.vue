<script setup lang="ts">
import { ref, watch } from 'vue'
import { Loader2 } from 'lucide-vue-next'

definePageMeta({ layout: 'default' })
useHead({ title: 'Início — Área de Membros' })

const { data: me } = useMe()
const { myCourses, availableCourses } = useCatalog()

const category = ref('')

const {
  data: mine,
  pending: pendingMine,
  refresh: refreshMine,
} = await useAsyncData('home-mine', () => myCourses())

const {
  data: available,
  pending: pendingAvailable,
  refresh: refreshAvailable,
} = await useAsyncData(
  'home-available',
  () => availableCourses(category.value || undefined),
  { watch: [category] }
)
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
    </section>

    <!-- Continue aprendendo -->
    <section class="animate-fade-slide">
      <div class="flex items-end justify-between mb-6">
        <div>
          <h2 class="text-2xl md:text-3xl font-medium tracking-tighter">Continue aprendendo</h2>
          <p class="text-xs text-neutral-500 mt-1">Seus cursos matriculados</p>
        </div>
        <span
          v-if="mine?.length"
          class="text-xs font-bold tracking-widest uppercase text-neutral-500"
        >
          {{ mine.length }} {{ mine.length === 1 ? 'curso' : 'cursos' }}
        </span>
      </div>

      <div v-if="pendingMine" class="flex justify-center py-12">
        <Loader2 class="w-6 h-6 text-orange-500 animate-spin" />
      </div>

      <div
        v-else-if="mine?.length"
        class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6"
      >
        <CourseCard v-for="c in mine" :key="c.id" :course="c" variant="enrolled" />
      </div>

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
      v-if="available?.length || category"
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

      <div v-if="pendingAvailable" class="flex justify-center py-12">
        <Loader2 class="w-6 h-6 text-orange-500 animate-spin" />
      </div>

      <div
        v-else-if="available?.length"
        class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6"
      >
        <CourseCard v-for="c in available" :key="c.id" :course="c" variant="available" />
      </div>

      <p
        v-else
        class="text-sm text-neutral-500 text-center py-12 bg-white/[0.02] border border-white/5 rounded-xl"
      >
        Nenhum curso encontrado nesta categoria.
      </p>
    </section>
  </div>
</template>
