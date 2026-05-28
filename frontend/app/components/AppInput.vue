<script setup lang="ts">
import { ref, computed } from 'vue'
import { Mail, Lock, User, Eye, EyeOff, type LucideIcon } from 'lucide-vue-next'

type IconName = 'mail' | 'lock' | 'user'

const props = withDefaults(
  defineProps<{
    type?: string
    placeholder?: string
    icon?: IconName
    error?: string | null
    autocomplete?: string
    required?: boolean
    label?: string
  }>(),
  {
    type: 'text',
    placeholder: '',
    icon: undefined,
    error: null,
    autocomplete: undefined,
    required: false,
    label: undefined,
  }
)

const model = defineModel<string>({ default: '' })

const iconMap: Record<IconName, LucideIcon> = {
  mail: Mail,
  lock: Lock,
  user: User,
}

const IconComp = computed(() => (props.icon ? iconMap[props.icon] : null))

const showPassword = ref(false)
const isPassword = computed(() => props.type === 'password')
const inputType = computed(() => {
  if (!isPassword.value) return props.type
  return showPassword.value ? 'text' : 'password'
})
</script>

<template>
  <label class="block">
    <span v-if="label" class="block text-xs font-medium tracking-wider uppercase text-neutral-400 mb-2">
      {{ label }}
    </span>
    <div class="relative">
      <component
        :is="IconComp"
        v-if="IconComp"
        class="absolute left-3 top-1/2 -translate-y-1/2 text-neutral-500 w-4 h-4 pointer-events-none"
      />
      <input
        v-model="model"
        :type="inputType"
        :placeholder="placeholder"
        :autocomplete="autocomplete"
        :required="required"
        :class="[
          'w-full bg-white/5 border rounded-lg py-3 text-sm text-white placeholder:text-neutral-500',
          'focus:outline-none focus:ring-1 transition-colors',
          IconComp ? 'pl-10' : 'pl-4',
          isPassword ? 'pr-10' : 'pr-4',
          error
            ? 'border-red-500/50 focus:border-red-500/70 focus:ring-red-500/30'
            : 'border-white/10 focus:border-orange-500/50 focus:ring-orange-500/30',
        ]"
      >
      <button
        v-if="isPassword"
        type="button"
        class="absolute right-3 top-1/2 -translate-y-1/2 text-neutral-500 hover:text-white transition-colors"
        :aria-label="showPassword ? 'Ocultar senha' : 'Mostrar senha'"
        @click="showPassword = !showPassword"
      >
        <Eye v-if="!showPassword" class="w-4 h-4" />
        <EyeOff v-else class="w-4 h-4" />
      </button>
    </div>
    <p v-if="error" class="mt-1 text-xs text-red-400">{{ error }}</p>
  </label>
</template>
