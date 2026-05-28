<script setup lang="ts">
import { X } from 'lucide-vue-next'

const props = defineProps<{
  open: boolean
  title: string
  size?: 'sm' | 'md' | 'lg' | 'xl'
}>()

const emit = defineEmits<{ close: [] }>()

const sizeClass = computed(() => {
  switch (props.size) {
    case 'sm':
      return 'max-w-md'
    case 'lg':
      return 'max-w-3xl'
    case 'xl':
      return 'max-w-5xl'
    default:
      return 'max-w-xl'
  }
})

const onEsc = (e: KeyboardEvent) => {
  if (e.key === 'Escape' && props.open) emit('close')
}

onMounted(() => window.addEventListener('keydown', onEsc))
onBeforeUnmount(() => window.removeEventListener('keydown', onEsc))
</script>

<template>
  <ClientOnly>
    <Teleport to="body">
      <Transition name="fade">
        <div
          v-if="open"
          class="fixed inset-0 z-[80] flex items-start justify-center pt-20 pb-10 px-4 overflow-y-auto bg-black/70 backdrop-blur-sm"
          @click.self="emit('close')"
        >
        <div
          :class="[
            'relative w-full bg-[#0a0a0a] border border-white/10 rounded-xl shadow-2xl',
            sizeClass,
          ]"
        >
          <div class="flex items-center justify-between px-6 py-4 border-b border-white/5">
            <h2 class="text-lg font-medium tracking-tight">{{ title }}</h2>
            <button
              type="button"
              class="p-1.5 rounded-md text-neutral-500 hover:text-white hover:bg-white/5"
              @click="emit('close')"
            >
              <X class="w-4 h-4" />
            </button>
          </div>
          <div class="p-6">
            <slot />
          </div>
        </div>
      </div>
      </Transition>
    </Teleport>
  </ClientOnly>
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
