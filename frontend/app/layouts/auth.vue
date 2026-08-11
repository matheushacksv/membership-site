<script setup lang="ts">
</script>

<template>
  <div class="relative min-h-screen flex flex-col bg-[#050505] text-white">
    <!-- Background gradient layers -->
    <div class="fixed inset-0 z-0 pointer-events-none">
      <div class="absolute inset-0 bg-gradient-to-b from-[#050505]/90 via-[#050505]/60 to-[#050505]" />
      <div class="absolute inset-0 bg-[radial-gradient(ellipse_at_center,_var(--tw-gradient-stops))] from-orange-900/15 via-[#050505]/0 to-[#050505]/0" />
    </div>

    <!-- Vertical grid lines (static, no beams) -->
    <div class="fixed inset-0 z-0 pointer-events-none flex w-full max-w-7xl mx-auto border-r border-white/5 opacity-60">
      <div class="flex-1 border-l border-white/5 h-full relative">
        <span class="absolute bottom-8 left-4 text-white/10 text-xs font-mono">01</span>
      </div>
      <div class="flex-1 border-l border-white/5 h-full relative">
        <span class="absolute bottom-8 left-4 text-white/10 text-xs font-mono">02</span>
      </div>
      <div class="flex-1 border-l border-white/5 h-full flex justify-center relative">
        <div class="h-full border-r border-dashed border-orange-500/20 w-px" />
        <span class="absolute bottom-8 text-orange-500/30 text-xs font-mono">03</span>
      </div>
      <div class="flex-1 border-l border-white/5 h-full relative">
        <span class="absolute bottom-8 left-4 text-white/10 text-xs font-mono">04</span>
      </div>
      <div class="flex-1 border-l border-white/5 h-full relative">
        <span class="absolute bottom-8 left-4 text-white/10 text-xs font-mono">05</span>
      </div>
    </div>

    <!-- Header with logo -->
    <header class="relative z-10 px-6 md:px-10 py-8">
      <NuxtLink to="/" class="inline-flex">
        <AppLogo />
      </NuxtLink>
    </header>

    <!-- Content -->
    <main class="relative z-10 flex-1 flex items-center justify-center px-6 py-8">
      <slot />
    </main>

    <!-- Footer subtle -->
    <footer class="relative z-10 px-6 md:px-10 py-6 text-center text-xs text-neutral-600">
      &copy; {{ new Date().getFullYear() }} Grupo Enriquecedor
    </footer>
  </div>
</template>
