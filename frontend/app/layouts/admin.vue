<template>
  <div class="relative min-h-screen bg-[#050505] text-white">
    <AdminSidebar />

    <!-- Background subtle -->
    <div class="fixed inset-0 z-0 pointer-events-none">
      <div class="absolute inset-0 bg-gradient-to-b from-[#050505]/90 via-[#050505]/60 to-[#050505]" />
      <div class="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,_var(--tw-gradient-stops))] from-orange-900/10 via-transparent to-transparent" />
    </div>

    <main class="relative z-10 ml-60 min-h-screen px-8 py-8">
      <slot />
    </main>
  </div>
</template>
