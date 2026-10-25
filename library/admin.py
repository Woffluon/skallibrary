from typing import Any
from django.contrib import admin
from django.contrib.auth.admin import GroupAdmin as BaseGroupAdmin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group, User
from django.db import transaction
from django.db.models import QuerySet
from django.http import HttpRequest
from django.utils.html import format_html
from django.utils.safestring import SafeText, mark_safe
from unfold.admin import ModelAdmin
from unfold.decorators import display
from unfold.forms import AdminPasswordChangeForm, UserChangeForm, UserCreationForm

from library.models import Book

admin.site.unregister(User)
admin.site.unregister(Group)


@admin.register(User)
class UserAdmin(BaseUserAdmin, ModelAdmin):
    form = UserChangeForm
    add_form = UserCreationForm
    change_password_form = AdminPasswordChangeForm


@admin.register(Group)
class GroupAdmin(BaseGroupAdmin, ModelAdmin):
    pass


@admin.action(description="Ödünç talebini onayla")
def approve_borrow(modeladmin: Any, request: HttpRequest, queryset: QuerySet) -> None:
    """Seçili onay bekleyen kitaplar için ödünç alma taleplerini onaylar."""
    count = 0
    with transaction.atomic():
        for book in queryset.filter(status='pending'):
            book.approve_borrow()
            book.save()
            count += 1
    modeladmin.message_user(request, f"{count} adet ödünç talebi onaylandı.")


@admin.action(description="Ödünç talebini reddet")
def deny_borrow(modeladmin: Any, request: HttpRequest, queryset: QuerySet) -> None:
    """Seçili onay bekleyen kitaplar için ödünç alma taleplerini reddeder."""
    count = 0
    with transaction.atomic():
        for book in queryset.filter(status='pending'):
            book.deny_borrow()
            book.save()
            count += 1
    modeladmin.message_user(request, f"{count} adet ödünç talebi reddedildi.")


@admin.action(description="İadeyi onayla")
def confirm_return(modeladmin: Any, request: HttpRequest, queryset: QuerySet) -> None:
    """Seçili iade onayı bekleyen kitapların iadelerini onaylar."""
    count = 0
    with transaction.atomic():
        for book in queryset.filter(status='return_pending'):
            book.confirm_return()
            book.save()
            count += 1
    modeladmin.message_user(request, f"{count} adet kitabın iadesi onaylandı.")


@admin.action(description="İade talebini reddet")
def deny_return(modeladmin: Any, request: HttpRequest, queryset: QuerySet) -> None:
    """Seçili iade onayı bekleyen kitapların iade taleplerini reddeder."""
    count = 0
    with transaction.atomic():
        for book in queryset.filter(status='return_pending'):
            book.deny_return()
            book.save()
            count += 1
    modeladmin.message_user(request, f"{count} adet kitabın iade talebi reddedildi.")


@admin.register(Book)
class BookAdmin(ModelAdmin):
    list_display = ('cover_thumbnail', 'name', 'author', 'status_badge', 'borrowed_by')
    list_filter = ('status',)
    list_filter_submit = True
    search_fields = ('name', 'author')
    search_help_text = "Kitap adı veya yazar adına göre arama yapabilirsiniz."
    list_per_page = 20
    actions = [approve_borrow, deny_borrow, confirm_return, deny_return]

    @display(description="Kapak", image=True)
    def cover_thumbnail(self, obj: Book) -> SafeText:
        """Kitabın kapak görselinin küçük önizlemesini görüntüler."""
        if obj.cover:
            return format_html(
                '<img src="{}" class="h-10 w-8 object-cover rounded shadow-xs" alt="{}">',
                obj.cover.url,
                obj.name,
            )
        return mark_safe('<span class="text-base-400 text-xs">-</span>')

    @display(
        description="Durum",
        label={
            'pending': 'warning',
            'approved': 'info',
            'return_pending': 'purple',
            'returned': 'success',
            'denied': 'danger',
        },
    )
    def status_badge(self, obj: Book) -> tuple[str, str]:
        """Kitabın ödünç ve iade durumunu renkli durum rozeti olarak görüntüler."""
        status_labels = {
            'pending': 'Onay Bekliyor',
            'approved': 'Ödünç Verildi',
            'return_pending': 'İade Onayı Bekliyor',
            'returned': 'İade Edildi',
            'denied': 'Reddedildi',
        }
        return obj.status, status_labels.get(obj.status, obj.get_status_display())
