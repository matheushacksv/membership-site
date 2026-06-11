<script setup lang="ts">
import DOMPurify from 'isomorphic-dompurify'

const props = defineProps<{ content: string | null }>()

// Permite explicitamente <mark> (grifo) e style inline (cor) do editor.
// DOMPurify sanitiza o CSS — só props seguras como color/background-color passam.
const safeHtml = computed(() =>
  props.content
    ? DOMPurify.sanitize(props.content, {
        ADD_TAGS: ['mark'],
        ADD_ATTR: ['style'],
      })
    : ''
)
</script>

<template>
  <article
    v-if="safeHtml"
    class="prose prose-invert max-w-none text-sm text-neutral-300 leading-relaxed"
    v-html="safeHtml"
  />
</template>
