from django.urls import path, include
from . import views

urlpatterns = [
    path('books/', views.book_list, name="book_list"),
    path("borrow/<uuid:book_id>/", views.borrow_book, name="borrow_book"),
    path("accounts/", include("django.contrib.auth.urls")),
    path("accounts/signup/", views.signup, name="signup"),
    path('', views.landing, name="landing")
]
