<script setup lang="ts">
import { useEditor, EditorContent } from '@tiptap/vue-3'
import StarterKit from '@tiptap/starter-kit'
import Link from '@tiptap/extension-link'
import { TextStyle } from '@tiptap/extension-text-style'
import { Color } from '@tiptap/extension-color'
import { Highlight } from '@tiptap/extension-highlight'
import {
  Bold,
  Italic,
  Heading1,
  Heading2,
  List,
  ListOrdered,
  Quote,
  Link2,
  Highlighter,
  Baseline,
  Undo,
  Redo,
} from 'lucide-vue-next'

const props = defineProps<{ modelValue: string }>()
const emit = defineEmits<{ 'update:modelValue': [value: string] }>()

const editor = useEditor({
  content: props.modelValue,
  extensions: [
    StarterKit,
    Link.configure({
      openOnClick: false,
      HTMLAttributes: { rel: 'noopener noreferrer', target: '_blank' },
    }),
    TextStyle,
    Color,
    Highlight.configure({ multicolor: true }),
  ],
  editorProps: {
    attributes: {
      class:
        'prose prose-invert max-w-none min-h-[12rem] px-4 py-3 focus:outline-none text-sm text-neutral-200',
    },
  },
  onUpdate: ({ editor }) => {
    const html = editor.getHTML()
    emit('update:modelValue', html === '<p></p>' ? '' : html)
  },
})

watch(
  () => props.modelValue,
  (val) => {
    if (!editor.value) return
    if (editor.value.getHTML() === val) return
    editor.value.commands.setContent(val || '', { emitUpdate: false })
  }
)

onBeforeUnmount(() => editor.value?.destroy())

const setLink = () => {
  const prev = editor.value?.getAttributes('link').href as string | undefined
  const url = window.prompt('URL do link:', prev || 'https://')
  if (url === null) return
  if (url === '') {
    editor.value?.chain().focus().extendMarkRange('link').unsetLink().run()
    return
  }
  editor.value
    ?.chain()
    .focus()
    .extendMarkRange('link')
    .setLink({ href: url })
    .run()
}

// Paletas: null = remover (reset). Cores escolhidas p/ contraste no tema escuro.
const TEXT_COLORS = [
  { label: 'Padrão', value: null },
  { label: 'Laranja', value: '#fb923c' },
  { label: 'Verde', value: '#4ade80' },
  { label: 'Azul', value: '#60a5fa' },
  { label: 'Vermelho', value: '#f87171' },
  { label: 'Amarelo', value: '#facc15' },
]

const HIGHLIGHT_COLORS = [
  { label: 'Remover', value: null },
  { label: 'Amarelo', value: '#fde047' },
  { label: 'Verde', value: '#86efac' },
  { label: 'Azul', value: '#93c5fd' },
  { label: 'Rosa', value: '#f9a8d4' },
  { label: 'Laranja', value: '#fdba74' },
]

const showTextMenu = ref(false)
const showHlMenu = ref(false)

const applyColor = (value: string | null) => {
  const chain = editor.value?.chain().focus()
  if (!chain) return
  if (value) chain.setColor(value).run()
  else chain.unsetColor().run()
  showTextMenu.value = false
}

const applyHighlight = (value: string | null) => {
  const chain = editor.value?.chain().focus()
  if (!chain) return
  if (value) chain.setHighlight({ color: value }).run()
  else chain.unsetHighlight().run()
  showHlMenu.value = false
}
</script>

<template>
  <div
    class="border border-white/10 rounded-lg bg-white/5 focus-within:border-orange-500/50 overflow-hidden"
  >
    <div
      v-if="editor"
      class="flex flex-wrap items-center gap-0.5 px-2 py-1.5 border-b border-white/10 bg-white/5"
    >
      <button
        type="button"
        title="Título 1"
        class="p-1.5 rounded text-neutral-300 hover:bg-white/10"
        :class="{ 'bg-orange-500/20 text-orange-400': editor.isActive('heading', { level: 1 }) }"
        @click="editor.chain().focus().toggleHeading({ level: 1 }).run()"
      >
        <Heading1 class="w-4 h-4" />
      </button>
      <button
        type="button"
        title="Título 2"
        class="p-1.5 rounded text-neutral-300 hover:bg-white/10"
        :class="{ 'bg-orange-500/20 text-orange-400': editor.isActive('heading', { level: 2 }) }"
        @click="editor.chain().focus().toggleHeading({ level: 2 }).run()"
      >
        <Heading2 class="w-4 h-4" />
      </button>

      <span class="w-px h-5 bg-white/10 mx-1" />

      <button
        type="button"
        title="Negrito"
        class="p-1.5 rounded text-neutral-300 hover:bg-white/10"
        :class="{ 'bg-orange-500/20 text-orange-400': editor.isActive('bold') }"
        @click="editor.chain().focus().toggleBold().run()"
      >
        <Bold class="w-4 h-4" />
      </button>
      <button
        type="button"
        title="Itálico"
        class="p-1.5 rounded text-neutral-300 hover:bg-white/10"
        :class="{ 'bg-orange-500/20 text-orange-400': editor.isActive('italic') }"
        @click="editor.chain().focus().toggleItalic().run()"
      >
        <Italic class="w-4 h-4" />
      </button>
      <button
        type="button"
        title="Link"
        class="p-1.5 rounded text-neutral-300 hover:bg-white/10"
        :class="{ 'bg-orange-500/20 text-orange-400': editor.isActive('link') }"
        @click="setLink"
      >
        <Link2 class="w-4 h-4" />
      </button>

      <!-- Cor do texto -->
      <div class="relative">
        <button
          type="button"
          title="Cor do texto"
          class="p-1.5 rounded text-neutral-300 hover:bg-white/10"
          :class="{ 'bg-orange-500/20 text-orange-400': editor.isActive('textStyle') }"
          @click="showHlMenu = false; showTextMenu = !showTextMenu"
        >
          <Baseline class="w-4 h-4" />
        </button>
        <div
          v-if="showTextMenu"
          class="absolute z-20 top-full left-0 mt-1 flex gap-1 p-1.5 rounded-lg bg-neutral-900 border border-white/10 shadow-xl"
        >
          <button
            v-for="c in TEXT_COLORS"
            :key="c.label"
            type="button"
            :title="c.label"
            class="w-5 h-5 rounded-full border border-white/20 flex items-center justify-center text-[9px] font-bold text-neutral-400 hover:scale-110 transition-transform"
            :style="c.value ? { backgroundColor: c.value } : {}"
            @click="applyColor(c.value)"
          >
            <span v-if="!c.value">⌫</span>
          </button>
        </div>
      </div>

      <!-- Grifo / highlight -->
      <div class="relative">
        <button
          type="button"
          title="Grifar"
          class="p-1.5 rounded text-neutral-300 hover:bg-white/10"
          :class="{ 'bg-orange-500/20 text-orange-400': editor.isActive('highlight') }"
          @click="showTextMenu = false; showHlMenu = !showHlMenu"
        >
          <Highlighter class="w-4 h-4" />
        </button>
        <div
          v-if="showHlMenu"
          class="absolute z-20 top-full left-0 mt-1 flex gap-1 p-1.5 rounded-lg bg-neutral-900 border border-white/10 shadow-xl"
        >
          <button
            v-for="c in HIGHLIGHT_COLORS"
            :key="c.label"
            type="button"
            :title="c.label"
            class="w-5 h-5 rounded border border-white/20 flex items-center justify-center text-[9px] font-bold text-neutral-800 hover:scale-110 transition-transform"
            :style="c.value ? { backgroundColor: c.value } : {}"
            @click="applyHighlight(c.value)"
          >
            <span v-if="!c.value" class="text-neutral-400">⌫</span>
          </button>
        </div>
      </div>

      <span class="w-px h-5 bg-white/10 mx-1" />

      <button
        type="button"
        title="Lista"
        class="p-1.5 rounded text-neutral-300 hover:bg-white/10"
        :class="{ 'bg-orange-500/20 text-orange-400': editor.isActive('bulletList') }"
        @click="editor.chain().focus().toggleBulletList().run()"
      >
        <List class="w-4 h-4" />
      </button>
      <button
        type="button"
        title="Lista numerada"
        class="p-1.5 rounded text-neutral-300 hover:bg-white/10"
        :class="{ 'bg-orange-500/20 text-orange-400': editor.isActive('orderedList') }"
        @click="editor.chain().focus().toggleOrderedList().run()"
      >
        <ListOrdered class="w-4 h-4" />
      </button>
      <button
        type="button"
        title="Citação"
        class="p-1.5 rounded text-neutral-300 hover:bg-white/10"
        :class="{ 'bg-orange-500/20 text-orange-400': editor.isActive('blockquote') }"
        @click="editor.chain().focus().toggleBlockquote().run()"
      >
        <Quote class="w-4 h-4" />
      </button>

      <span class="w-px h-5 bg-white/10 mx-1" />

      <button
        type="button"
        title="Desfazer"
        class="p-1.5 rounded text-neutral-300 hover:bg-white/10 disabled:opacity-30"
        :disabled="!editor.can().undo()"
        @click="editor.chain().focus().undo().run()"
      >
        <Undo class="w-4 h-4" />
      </button>
      <button
        type="button"
        title="Refazer"
        class="p-1.5 rounded text-neutral-300 hover:bg-white/10 disabled:opacity-30"
        :disabled="!editor.can().redo()"
        @click="editor.chain().focus().redo().run()"
      >
        <Redo class="w-4 h-4" />
      </button>
    </div>

    <EditorContent :editor="editor" />
  </div>
</template>
