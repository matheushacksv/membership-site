export interface Announcement {
  id: number
  title: string
  body: string
  image_url: string | null
  kind: string
  kind_label: string
  published_at: string | null
}

export interface AnnouncementAdmin extends Announcement {
  is_published: boolean
  email_sent_at: string | null
  created_at: string
}

// Espelha Announcement.Kind no backend (announcements/models.py).
export const ANNOUNCEMENT_KINDS = [
  { value: 'downtime', label: 'Fora do ar' },
  { value: 'change', label: 'Mudança na plataforma' },
  { value: 'feature', label: 'Nova funcionalidade' },
  { value: 'info', label: 'Informativo' },
] as const

export const useAnnouncements = () => {
  const api = useApi()
  return {
    list: () => api<Announcement[]>('/announcements'),
    unreadCount: () => api<{ count: number }>('/announcements/unread-count'),
    markRead: () => api<{ ok: boolean }>('/announcements/mark-read', { method: 'POST' }),
  }
}
