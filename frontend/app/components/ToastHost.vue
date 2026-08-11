<script setup lang="ts">
import { CheckCircle2, AlertCircle, Info } from 'lucide-vue-next'
import type { ToastMessage } from '~/composables/useToast'

const { toasts, dismiss } = useToast()

const goTo = (t: ToastMessage) => {
  if (t.action) navigateTo(t.action.to)
  dismiss(t.id)
}

const styles = {
  success: 'border-emerald-500/40 text-emerald-300 bg-emerald-500/10',
  error: 'border-red-500/40 text-red-300 bg-red-500/10',
  info: 'border-white/15 text-neutral-300 bg-white/10',
}

const icons = {
  success: CheckCircle2,
  error: AlertCircle,
  info: Info,
}
</script>

<template>
  <Teleport to="body">
    <div class="fixed bottom-6 right-6 z-[100] flex flex-col gap-2 max-w-sm pointer-events-none">
      <TransitionGroup name="toast">
        <div
          v-for="t in toasts"
          :key="t.id"
          :class="[
            'pointer-events-auto flex items-start gap-2.5 px-4 py-3 rounded-lg border backdrop-blur-md text-sm',
            styles[t.type],
          ]"
        >
          <component :is="icons[t.type]" class="w-4 h-4 mt-0.5 shrink-0" />
          <div class="min-w-0">
            <span>{{ t.text }}</span>
            <button
              v-if="t.action"
              type="button"
              class="mt-1.5 block font-bold underline underline-offset-2 hover:opacity-80"
              @click="goTo(t)"
            >
              {{ t.action.label }}
            </button>
          </div>
        </div>
      </TransitionGroup>
    </div>
  </Teleport>
</template>

<style>
.toast-enter-active,
.toast-leave-active {
  transition: all 0.25s ease;
}
.toast-enter-from,
.toast-leave-to {
  opacity: 0;
  transform: translateY(10px);
}
</style>
