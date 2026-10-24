import uuid
from django.conf import settings
from django.db import models


class Book(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Onay bekliyor'),
        ('approved', 'Ödünç verildi'),
        ('denied', 'Reddedildi'),
        ('return_pending', 'İade onayı bekliyor'),
        ('returned', 'İade edildi'),
    )

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name="Kimlik",
    )
    name = models.CharField(max_length=255, verbose_name="Kitap Adı")
    author = models.CharField(max_length=255, verbose_name="Yazar")
    cover = models.ImageField(upload_to='covers/', blank=True, null=True, verbose_name="Kapak Resmi")
    borrowed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="borrowed_books",
        verbose_name="Ödünç Alan Öğrenci",
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='returned',
        verbose_name="Durum",
    )

    class Meta:
        verbose_name = "Kitap"
        verbose_name_plural = "Kitaplar"

    @property
    def borrowed(self):
        return self.status in ['approved', 'return_pending']

    @property
    def is_available(self):
        return self.status in ['returned', 'denied'] and self.borrowed_by is None

    def __str__(self):
        return f"{self.name} - {self.author}"
