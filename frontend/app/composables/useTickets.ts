export interface TicketMessage {
  id: number
  body: string
  attachment_url: string | null
  author_name: string | null
  is_staff: boolean
  created_at: string
}

export interface TicketListItem {
  id: number
  category: string
  category_label: string
  status: string
  status_label: string
  created_at: string
  updated_at: string
  // Só na listagem admin:
  user_name?: string | null
  user_email?: string | null
  last_message?: string | null
}

export interface TicketDetail extends TicketListItem {
  messages: TicketMessage[]
}

// Espelha Ticket.Category no backend (tickets/models.py).
export const TICKET_CATEGORIES = [
  { value: 'technical', label: 'Erro técnico' },
  { value: 'bug', label: 'Reportar Bug' },
  { value: 'access', label: 'Sem Acesso' },
  { value: 'performance', label: 'Lentidão/Performance' },
  { value: 'out', label: 'Sistema fora do ar' },
  { value: 'suggestion', label: 'Sugestão de melhoria' },
  { value: 'doubt', label: 'Dúvidas' },
] as const

export const useTickets = () => {
  const api = useApi()
  return {
    listMine: () => api<TicketListItem[]>('/tickets'),
    get: (id: number) => api<TicketDetail>(`/tickets/${id}`),
    // create/addMessage são multipart (FormData), não setar Content-Type (browser põe o boundary).
    create: (fd: FormData) =>
      api<TicketDetail>('/tickets', { method: 'POST', body: fd }),
    addMessage: (id: number, fd: FormData) =>
      api<TicketMessage>(`/tickets/${id}/messages`, { method: 'POST', body: fd }),
  }
}
