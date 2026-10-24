from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from library.models import Book


def book_list(req):
    books = Book.objects.all()
    return render(req, "library/books.html", {
        "books": books
    })


@login_required
@require_POST
def borrow_book(req, book_id):
    book = get_object_or_404(Book, id=book_id)

    if book.status in ['pending', 'approved', 'return_pending'] or book.borrowed_by is not None:
        messages.error(req, "Bu kitap şu anda ödünç alınamaz.")
        return redirect('book_list')

    book.status = 'pending'
    book.borrowed_by = req.user
    book.save()

    admin_email = getattr(settings, 'ADMIN_EMAIL', 'admin@example.com')
    send_mail(
        subject=f"Yeni Ödünç Talebi: {book.name}",
        message=f"{req.user.username} adlı öğrenci '{book.name}' ({book.author}) kitabı için ödünç alma talebinde bulundu.",
        from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', None),
        recipient_list=[admin_email],
        fail_silently=True,
    )
    messages.success(req, f"'{book.name}' için ödünç talebiniz alındı. Yönetici onayı bekleniyor.")
    return redirect('book_list')


@login_required
@require_POST
def return_book(req, book_id):
    book = get_object_or_404(Book, id=book_id)

    if book.borrowed_by != req.user or book.status != 'approved':
        messages.error(req, "Bu kitap için iade işlemi başlatamazsınız.")
        return redirect('book_list')

    book.status = 'return_pending'
    book.save()

    messages.success(req, f"'{book.name}' için iade talebiniz iletildi. Yönetici onayı bekleniyor.")
    return redirect('book_list')


def landing(req):
    return render(req, "library/landing.html")
