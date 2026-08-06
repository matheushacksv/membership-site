from django.contrib import admin

from .models import Ticket, TicketMessage


class TicketMessageInline(admin.TabularInline):
    model = TicketMessage
    extra = 0
    readonly_fields = ('author', 'body', 'attachment', 'created_at')
    can_delete = False


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'category', 'status', 'updated_at')
    list_filter = ('status', 'category', 'created_at')
    search_fields = ('user__email', 'user__name', 'messages__body')
    readonly_fields = ('user', 'created_at', 'updated_at')
    inlines = [TicketMessageInline]
