from django.contrib import admin

from .models import DownloadLog


@admin.register(DownloadLog)
class DownloadLogAdmin(admin.ModelAdmin):
    list_display = ('email', 'attachment', 'ip', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('email', 'ip')
    readonly_fields = ('user', 'attachment', 'email', 'ip', 'created_at')

    def has_add_permission(self, request):
        return False
