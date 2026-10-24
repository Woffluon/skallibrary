from django.urls import path, include
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('', views.book_list, name="book_list"),
    path('books/', views.book_list),
    path("borrow/<uuid:book_id>/", views.borrow_book, name="borrow_book"),
    path("return/<uuid:book_id>/", views.return_book, name="return_book"),
    path('accounts/login/',
        auth_views.LoginView.as_view(template_name="library/login.html"),
        name="login"
    ),
    path("accounts/", include("django.contrib.auth.urls")),
]
