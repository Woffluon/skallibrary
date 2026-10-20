from django.contrib.auth import authenticate,login
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render, redirect
from django.views.decorators.http import require_POST

from library.models import Book

# Create your views here.

def book_list(req):
    books = Book.objects.all()
    return render(req, "library/books.html", {
        "books": books
    })

@login_required
@require_POST
def borrow_book(req, book_id):
    book = get_object_or_404(Book, id=book_id)

    if not book.borrowed:
        book.borrowed = True
        book.save(update_fields=["borrowed"])

    return redirect('book_list')

def signup(req):
    if req.user.is_authenticated:
        return redirect('book_list')

    if req.method == 'POST':
        form = UserCreationForm(req.POST)

        if form.is_valid():
            user = form.save()
            login(req, user)
            return redirect('book_list')
    else:
        form = UserCreationForm()

    return render(
        req,
        "registiration/signup.html",
        {"form":form}
    )

def landing(req):
    return render(
        req,
        "library/landing.html"
    )
