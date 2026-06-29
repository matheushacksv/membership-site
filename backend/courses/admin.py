from django.contrib import admin

from .models import Banner, DownloadLog


@admin.register(DownloadLog)
class DownloadLogAdmin(admin.ModelAdmin):
    list_display = ('email', 'attachment', 'ip', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('email', 'ip')
    readonly_fields = ('user', 'attachment', 'email', 'ip', 'created_at')

    def has_add_permission(self, request):
        return False


@admin.register(Banner)
class BannerAdmin(admin.ModelAdmin):
    list_display = ('title', 'url', 'is_active', 'created_at')
    list_editable = ('is_active',)
    list_filter = ('is_active',)
    search_fields = ('title', 'url')
