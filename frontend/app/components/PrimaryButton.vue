<script setup lang="ts">
import { Loader2, ArrowRight } from 'lucide-vue-next'

withDefaults(
  defineProps<{
    loading?: boolean
    disabled?: boolean
    type?: 'submit' | 'button' | 'reset'
    showArrow?: boolean
  }>(),
  {
    loading: false,
    disabled: false,
    type: 'submit',
    showArrow: true,
  }
)
</script>

<template>
  <button
    :type="type"
    :disabled="loading || disabled"
    class="button-custom w-full"
  >
    <div class="points_wrapper">
      <i class="point" />
      <i class="point" />
      <i class="point" />
      <i class="point" />
      <i class="point" />
      <i class="point" />
      <i class="point" />
    </div>
    <span class="inner">
      <Loader2 v-if="loading" class="w-4 h-4 animate-spin" />
      <template v-else>
        <slot />
        <ArrowRight v-if="showArrow" class="w-4 h-4 ml-1 transition-transform group-hover:translate-x-0.5" />
      </template>
    </span>
  </button>
</template>
