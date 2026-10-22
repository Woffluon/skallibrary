from django.contrib.auth import authenticate,login
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render, redirect
from django.views.decorators.http import require_POST
from django.contrib.auth.forms import UserCreationForm

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

    book.borrowed_by = req.user
    book.save()

    return redirect('book_list')

@login_required
@require_POST
def return_book(req, book_id):
    book = get_object_or_404(Book, id=book_id)
    book.borrowed_by = None
    book.save()

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
        "library/signup.html",
        {"form":form}
    )

def landing(req):
    return render(
        req,
        "library/landing.html"
    )
