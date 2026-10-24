import uuid
from django.conf import settings
from django.db import models


class Book(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('denied', 'Denied'),
        ('return_pending', 'Return Pending'),
        ('returned', 'Returned'),
    )

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    name = models.CharField(max_length=255)
    author = models.CharField(max_length=255)
    cover = models.ImageField(upload_to='covers/', blank=True, null=True)
    borrowed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="borrowed_books",
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='returned',
    )

    @property
    def borrowed(self):
        return self.status in ['approved', 'return_pending']

    @property
    def is_available(self):
        return self.status in ['returned', 'denied'] and self.borrowed_by is None

    def __str__(self):
        return f"{self.name} - {self.author}"
