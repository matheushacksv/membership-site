<script setup lang="ts">
import { ArrowLeft, LogOut } from 'lucide-vue-next'

const { logout } = useAuth()
const { data: me } = useMe()

const initial = computed(() =>
  (me.value?.name || me.value?.email || '?').charAt(0).toUpperCase()
)
</script>

<template>
  <div class="min-h-screen flex flex-col bg-[#050505] text-white">
    <header class="flex items-center justify-between px-6 py-3 border-b border-white/5 bg-[#0a0a0a]/80 backdrop-blur-md z-30">
      <NuxtLink
        to="/"
        class="inline-flex items-center gap-2 text-sm text-neutral-400 hover:text-white"
      >
        <ArrowLeft class="w-4 h-4" />
        Voltar à home
      </NuxtLink>

      <div class="flex items-center gap-3">
        <img
          v-if="me?.avatar"
          :src="me.avatar"
          class="w-8 h-8 rounded-full object-cover border border-white/10"
        >
        <div
          v-else
          class="w-8 h-8 rounded-full bg-gradient-to-tr from-orange-500 to-amber-500 flex items-center justify-center text-xs font-semibold text-white"
        >
          {{ initial }}
        </div>
        <button
          type="button"
          aria-label="Sair"
          class="p-1.5 rounded-md text-neutral-500 hover:text-red-300 hover:bg-white/5"
          @click="logout()"
        >
          <LogOut class="w-4 h-4" />
        </button>
      </div>
    </header>

    <main class="flex-1 min-h-0">
      <slot />
    </main>
  </div>
</template>
