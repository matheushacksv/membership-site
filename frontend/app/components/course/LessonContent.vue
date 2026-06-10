<script setup lang="ts">
import DOMPurify from 'isomorphic-dompurify'

const props = defineProps<{ content: string | null }>()

const safeHtml = computed(() =>
  props.content ? DOMPurify.sanitize(props.content) : ''
)
</script>

<template>
  <article
    v-if="safeHtml"
    class="prose prose-invert max-w-none text-sm text-neutral-300 leading-relaxed"
    v-html="safeHtml"
  />
</template>
