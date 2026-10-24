from django.contrib import admin
from library.models import Book


@admin.action(description="Seçili kitapların ödünç taleplerini onayla")
def approve_borrow(modeladmin, request, queryset):
    count = queryset.filter(status='pending').update(status='approved')
    modeladmin.message_user(request, f"{count} adet ödünç talebi onaylandı.")


@admin.action(description="Seçili kitapların ödünç taleplerini reddet")
def deny_borrow(modeladmin, request, queryset):
    count = queryset.filter(status='pending').update(status='denied', borrowed_by=None)
    modeladmin.message_user(request, f"{count} adet ödünç talebi reddedildi.")


@admin.action(description="Seçili kitapların iadelerini onayla")
def confirm_return(modeladmin, request, queryset):
    count = queryset.filter(status='return_pending').update(status='returned', borrowed_by=None)
    modeladmin.message_user(request, f"{count} adet kitabın iadesi onaylandı.")


class BookAdmin(admin.ModelAdmin):
    list_display = ('name', 'author', 'status', 'borrowed_by', 'cover')
    list_filter = ('status',)
    search_fields = ('name', 'author')
    actions = [approve_borrow, deny_borrow, confirm_return]


admin.site.register(Book, BookAdmin)
