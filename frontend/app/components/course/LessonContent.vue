<script setup lang="ts">
defineProps<{ content: string | null }>()
</script>

<template>
  <article
    v-if="content"
    class="prose prose-invert max-w-none text-sm text-neutral-300 whitespace-pre-wrap leading-relaxed"
  >{{ content }}</article>
</template>
