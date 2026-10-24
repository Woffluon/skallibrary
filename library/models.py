import uuid
from typing import Any
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.db import models


def validate_cover_image(value: Any) -> None:
    """Kapak görselinin maksimum 2MB boyutunda olmasını doğrular."""
    limit = 2 * 1024 * 1024
    if value.size > limit:
        raise ValidationError("Kapak görseli maksimum 2MB boyutunda olabilir.")


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
    cover = models.ImageField(
        upload_to='covers/',
        blank=True,
        null=True,
        validators=[
            FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png', 'webp']),
            validate_cover_image,
        ],
        verbose_name="Kapak Resmi",
    )
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
        db_index=True,
        verbose_name="Durum",
    )

    class Meta:
        verbose_name = "Kitap"
        verbose_name_plural = "Kitaplar"
        indexes = [
            models.Index(fields=['name', 'author'], name='book_name_author_idx'),
        ]
        constraints = [
            models.CheckConstraint(
                condition=(
                    (models.Q(status__in=['pending', 'approved', 'return_pending']) & models.Q(borrowed_by__isnull=False)) |
                    (models.Q(status__in=['returned', 'denied']) & models.Q(borrowed_by__isnull=True))
                ),
                name="book_status_borrower_consistency"
            )
        ]

    def request_borrow(self, user: Any) -> None:
        """Öğrencinin ödünç alma talebini doğrular ve onay bekliyor durumuna alır."""
        if not getattr(user, 'is_active', True):
            raise ValidationError("Aktif olmayan kullanıcı ödünç talebinde bulunamaz.")
        if self.status in ['pending', 'approved', 'return_pending'] or self.borrowed_by is not None:
            raise ValidationError("Bu kitap şu anda ödünç alınamaz.")
        self.status = 'pending'
        self.borrowed_by = user

    def approve_borrow(self) -> None:
        """Yöneticinin ödünç alma talebini onaylamasını sağlar."""
        if self.status != 'pending':
            raise ValidationError("Yalnızca onay bekleyen ödünç talepleri onaylanabilir.")
        self.status = 'approved'

    def deny_borrow(self) -> None:
        """Yöneticinin ödünç alma talebini reddetmesini ve kitabı boşa çıkarmasını sağlar."""
        if self.status != 'pending':
            raise ValidationError("Yalnızca onay bekleyen ödünç talepleri reddedilebilir.")
        self.status = 'denied'
        self.borrowed_by = None

    def request_return(self, user: Any) -> None:
        """Öğrencinin ödünç aldığı kitap için iade talebi başlatmasını sağlar."""
        if self.borrowed_by != user or self.status != 'approved':
            raise ValidationError("Bu kitap için iade işlemi başlatamazsınız.")
        self.status = 'return_pending'

    def confirm_return(self) -> None:
        """Yöneticinin iade talebini onaylayarak kitabı tekrar müsait duruma getirmesini sağlar."""
        if self.status != 'return_pending':
            raise ValidationError("Yalnızca iade onayı bekleyen kitapların iadesi onaylanabilir.")
        self.status = 'returned'
        self.borrowed_by = None

    def deny_return(self) -> None:
        """Yöneticinin iade talebini reddederek kitabı tekrar ödünç verildi durumuna almasını sağlar."""
        if self.status != 'return_pending':
            raise ValidationError("Yalnızca iade onayı bekleyen kitapların iade talebi reddedilebilir.")
        self.status = 'approved'

    @property
    def borrowed(self) -> bool:
        """Kitabın şu anda öğrenci kullanımında veya iade sürecinde olup olmadığını belirtir."""
        return self.status in ['approved', 'return_pending']

    @property
    def is_available(self) -> bool:
        """Kitabın yeni bir ödünç talebi için müsait olup olmadığını belirtir."""
        return self.status in ['returned', 'denied'] and self.borrowed_by is None

    def __str__(self) -> str:
        """Kitabın adını ve yazarını gösteren metin temsilini döndürür."""
        return f"{self.name} - {self.author}"
