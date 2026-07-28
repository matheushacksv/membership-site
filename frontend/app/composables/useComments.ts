export interface CommentAuthor {
  id: number
  name: string | null
  avatar: string | null
  is_staff: boolean
}

export interface CommentItem {
  id: number
  body: string
  created_at: string
  updated_at: string | null
  resolved_at?: string | null
  author: CommentAuthor
  replies: CommentItem[]
}

export const useComments = () => {
  const api = useApi()
  return {
    list: (lessonId: number) =>
      api<CommentItem[]>(`/catalog/lessons/${lessonId}/comments`),
    create: (lessonId: number, body: string, parent_id: number | null = null) =>
      api<CommentItem>(`/catalog/lessons/${lessonId}/comments`, {
        method: 'POST',
        body: { body, parent_id },
      }),
    update: (id: number, body: string) =>
      api<CommentItem>(`/catalog/comments/${id}`, {
        method: 'PATCH',
        body: { body },
      }),
    remove: (id: number) =>
      api(`/catalog/comments/${id}`, { method: 'DELETE' }),
  }
}
