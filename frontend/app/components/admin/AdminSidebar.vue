<script setup lang="ts">
import { computed } from 'vue'
import { BookOpen, Home, LogOut, Users } from 'lucide-vue-next'

const route = useRoute()
const { logout } = useAuth()
const { data: me } = useMe()

const items = [
  { to: '/admin/courses', label: 'Cursos', icon: BookOpen, match: '/admin/courses' },
  { to: '/admin/users', label: 'Alunos', icon: Users, match: '/admin/users' },
]

const initial = computed(
  () => (me.value?.name || me.value?.email || '?').charAt(0).toUpperCase()
)

const isActive = (match: string) => route.path.startsWith(match)
</script>

<template>
  <aside
    class="fixed left-0 top-0 bottom-0 w-60 border-r border-white/5 bg-[#0a0a0a]/80 backdrop-blur-md flex flex-col z-30"
  >
    <!-- Logo -->
    <div class="px-6 py-6 border-b border-white/5">
      <NuxtLink to="/admin" class="flex items-center gap-2">
        <AppLogo :show-label="false" />
      </NuxtLink>
      <span class="block text-[10px] font-bold tracking-widest uppercase text-orange-400/80 mt-2">
        Painel Admin
      </span>
    </div>

    <!-- Nav -->
    <nav class="flex-1 py-4 px-3 space-y-1">
      <NuxtLink
        v-for="item in items"
        :key="item.to"
        :to="item.to"
        :class="[
          'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors border-l-2',
          isActive(item.match)
            ? 'bg-orange-500/10 text-orange-300 border-orange-500'
            : 'text-neutral-400 hover:text-white hover:bg-white/5 border-transparent',
        ]"
      >
        <component :is="item.icon" class="w-4 h-4" />
        {{ item.label }}
      </NuxtLink>

      <div class="my-3 border-t border-white/5" />

      <NuxtLink
        to="/"
        class="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm text-neutral-500 hover:text-white hover:bg-white/5 transition-colors border-l-2 border-transparent"
      >
        <Home class="w-4 h-4" />
        Área do aluno
      </NuxtLink>
    </nav>

    <!-- User footer -->
    <div class="px-3 py-4 border-t border-white/5">
      <div class="flex items-center gap-3 px-2 py-2">
        <img
          v-if="me?.avatar"
          :src="me.avatar"
          alt="avatar"
          class="w-8 h-8 rounded-full object-cover border border-white/10"
        >
        <div
          v-else
          class="w-8 h-8 rounded-full bg-gradient-to-tr from-orange-500 to-amber-500 flex items-center justify-center text-xs font-semibold text-white"
        >
          {{ initial }}
        </div>
        <div class="flex-1 min-w-0">
          <p class="text-xs font-medium text-white truncate">
            {{ me?.name || me?.email }}
          </p>
          <p class="text-[10px] text-neutral-500 truncate">Staff</p>
        </div>
        <button
          type="button"
          aria-label="Sair"
          class="p-1.5 rounded-md text-neutral-500 hover:text-red-300 hover:bg-white/5 transition-colors"
          @click="logout()"
        >
          <LogOut class="w-3.5 h-3.5" />
        </button>
      </div>
    </div>
  </aside>
</template>
