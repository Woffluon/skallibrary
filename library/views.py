from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import Http404
from django.shortcuts import redirect, render
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
    with transaction.atomic():
        book = Book.objects.select_for_update().filter(id=book_id).first()
        if not book:
            raise Http404("Kitap bulunamadı.")

        try:
            book.request_borrow(req.user)
            book.save()
        except ValidationError:
            messages.error(req, "Bu kitap şu anda ödünç alınamaz.")
            return redirect('book_list')

    messages.success(req, f"'{book.name}' için ödünç talebiniz alındı. Yönetici onayı bekleniyor.")
    return redirect('book_list')


@login_required
@require_POST
def return_book(req, book_id):
    with transaction.atomic():
        book = Book.objects.select_for_update().filter(id=book_id).first()
        if not book:
            raise Http404("Kitap bulunamadı.")

        try:
            book.request_return(req.user)
            book.save()
        except ValidationError:
            messages.error(req, "Bu kitap için iade işlemi başlatamazsınız.")
            return redirect('book_list')

    messages.success(req, f"'{book.name}' için iade talebiniz iletildi. Yönetici onayı bekleniyor.")
    return redirect('book_list')
