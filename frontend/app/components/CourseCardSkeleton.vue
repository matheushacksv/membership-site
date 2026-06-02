<script setup lang="ts">
// Skeleton estático que espelha CourseCard — mesma grid/aspect pra evitar layout shift.
</script>

<template>
  <div class="bg-white/5 border border-white/10 rounded-xl overflow-hidden">
    <!-- Image placeholder -->
    <div class="relative aspect-video bg-white/5 animate-pulse" />

    <!-- Body -->
    <div class="p-5 flex flex-col gap-3">
      <div class="h-5 w-3/4 rounded bg-white/5 animate-pulse" />
      <div class="h-5 w-1/2 rounded bg-white/5 animate-pulse" />

      <div class="flex items-center justify-between pt-3 border-t border-white/5">
        <div class="h-3 w-24 rounded bg-white/5 animate-pulse" />
        <div class="h-7 w-7 rounded-full bg-white/5 animate-pulse" />
      </div>
    </div>
  </div>
</template>
