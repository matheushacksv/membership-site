<script setup lang="ts">
import { useEditor, EditorContent } from '@tiptap/vue-3'
import StarterKit from '@tiptap/starter-kit'
import Link from '@tiptap/extension-link'
import {
  Bold,
  Italic,
  Heading1,
  Heading2,
  List,
  ListOrdered,
  Quote,
  Link2,
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
