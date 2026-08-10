<script setup lang="ts">
import { computed, ref, onMounted, onBeforeUnmount } from 'vue'
import { LogOut, Shield, ChevronDown, LifeBuoy, User as UserIcon } from 'lucide-vue-next'

const { logout } = useAuth()
const { data: me } = useMe()

const initial = computed(() => {
  const source = me.value?.name || me.value?.email || ''
  return source.charAt(0).toUpperCase() || '?'
})

const open = ref(false)
const menuRef = ref<HTMLElement | null>(null)

const onDocClick = (e: MouseEvent) => {
  if (!open.value) return
  if (menuRef.value && !menuRef.value.contains(e.target as Node)) {
    open.value = false
  }
}

const onKey = (e: KeyboardEvent) => {
  if (e.key === 'Escape') open.value = false
}

onMounted(() => {
  document.addEventListener('click', onDocClick)
  document.addEventListener('keydown', onKey)
})

onBeforeUnmount(() => {
  document.removeEventListener('click', onDocClick)
  document.removeEventListener('keydown', onKey)
})

const handleLogout = () => {
  open.value = false
  logout()
}
</script>

<template>
  <header
    class="sticky top-0 z-40 backdrop-blur-md bg-[#050505]/70 border-b border-white/5"
  >
    <div class="max-w-7xl mx-auto flex items-center justify-between px-6 md:px-10 py-5">
      <NuxtLink to="/">
        <AppLogo />
      </NuxtLink>

      <div class="flex items-center gap-3">
        <NuxtLink
          v-if="me?.is_staff"
          to="/admin"
          class="inline-flex items-center gap-1.5 text-xs font-bold tracking-wider uppercase text-orange-300 hover:text-orange-200 transition-colors border border-orange-500/30 hover:border-orange-500/50 bg-orange-500/10 rounded-full px-3 py-2"
        >
          <Shield class="w-3.5 h-3.5" />
          <span class="hidden md:inline">Admin</span>
        </NuxtLink>

        <NotificationBell v-if="me" />

        <div ref="menuRef" class="relative">
          <button
            type="button"
            class="inline-flex items-center gap-2 pl-1 pr-3 py-1 rounded-full border border-white/10 hover:border-white/20 bg-white/5 hover:bg-white/10 transition-colors"
            :aria-expanded="open"
            aria-haspopup="menu"
            @click="open = !open"
          >
            <img
              v-if="me?.avatar"
              :src="me.avatar"
              alt="Avatar"
              class="w-8 h-8 rounded-full object-cover"
            >
            <div
              v-else
              class="w-8 h-8 rounded-full bg-gradient-to-tr from-orange-500 to-amber-500 flex items-center justify-center text-sm font-semibold text-white"
            >
              {{ initial }}
            </div>
            <span class="hidden md:inline text-sm font-medium text-white max-w-[140px] truncate">
              {{ me?.name || me?.email }}
            </span>
            <ChevronDown
              class="w-3.5 h-3.5 text-neutral-400 transition-transform"
              :class="{ 'rotate-180': open }"
            />
          </button>

          <Transition
            enter-active-class="transition duration-150 ease-out"
            enter-from-class="opacity-0 -translate-y-1"
            enter-to-class="opacity-100 translate-y-0"
            leave-active-class="transition duration-100 ease-in"
            leave-from-class="opacity-100 translate-y-0"
            leave-to-class="opacity-0 -translate-y-1"
          >
            <div
              v-if="open"
              role="menu"
              class="absolute right-0 mt-2 w-60 rounded-xl border border-white/10 bg-[#0a0a0a]/95 backdrop-blur-md shadow-xl shadow-black/40 overflow-hidden"
            >
              <div class="px-4 py-3 border-b border-white/5">
                <p class="text-sm font-medium text-white truncate">
                  {{ me?.name || 'Usuário' }}
                </p>
                <p class="text-xs text-neutral-500 truncate">{{ me?.email }}</p>
              </div>
              <NuxtLink
                to="/profile"
                role="menuitem"
                class="flex items-center gap-2 px-4 py-2.5 text-sm text-neutral-200 hover:bg-white/5 hover:text-white transition-colors"
                @click="open = false"
              >
                <UserIcon class="w-4 h-4" />
                Perfil
              </NuxtLink>
              <NuxtLink
                to="/suporte"
                role="menuitem"
                class="flex items-center gap-2 px-4 py-2.5 text-sm text-neutral-200 hover:bg-white/5 hover:text-white transition-colors"
                @click="open = false"
              >
                <LifeBuoy class="w-4 h-4" />
                Suporte
              </NuxtLink>
              <button
                type="button"
                role="menuitem"
                class="w-full flex items-center gap-2 px-4 py-2.5 text-sm text-neutral-200 hover:bg-white/5 hover:text-white transition-colors text-left"
                @click="handleLogout"
              >
                <LogOut class="w-4 h-4" />
                Sair
              </button>
            </div>
          </Transition>
        </div>
      </div>
    </div>
  </header>
</template>
