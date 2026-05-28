<script setup lang="ts">
const CATEGORIES: { value: string; label: string }[] = [
  { value: '', label: 'Todos' },
  { value: 'sales', label: 'Vendas' },
  { value: 'marketing', label: 'Marketing' },
  { value: 'strategy', label: 'Estratégia' },
  { value: 'tool', label: 'Ferramentas' },
  { value: 'customer', label: 'Customer Success' },
  { value: 'lifestyle', label: 'Estilo de Vida' },
  { value: 'development', label: 'Desenvolvimento' },
]

const model = defineModel<string>({ default: '' })
</script>

<template>
  <div class="flex flex-wrap gap-2">
    <button
      v-for="c in CATEGORIES"
      :key="c.value || 'all'"
      type="button"
      :class="[
        'rounded-full px-4 py-1.5 text-xs font-medium tracking-wide uppercase transition-colors border',
        model === c.value
          ? 'bg-orange-500/15 border-orange-500/40 text-orange-300'
          : 'bg-white/5 border-white/10 text-neutral-400 hover:text-white hover:border-white/20',
      ]"
      @click="model = c.value"
    >
      {{ c.label }}
    </button>
  </div>
</template>
