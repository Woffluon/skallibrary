"""
SKAL Kütüphanesi - Yönetim Paneli Gösterge Paneli ve Rozet Geri Çağrıları.

Bu modül, Django Unfold yönetim arayüzü için dinamik KPI istatistiklerini,
son hareketleri ve kenar çubuğundaki (sidebar) bildirim rozetlerini üretir.
"""

from typing import Any
from django.http import HttpRequest
from library.models import Book


def pending_books_badge(request: HttpRequest) -> str | None:
    """Kenar çubuğunda kitap kataloğu için bekleyen talep rozetini üretir.

    Onay bekleyen ('pending') ve iade onayı bekleyen ('return_pending') kitapların
    toplam sayısını hesaplar. Sayı 0'dan büyükse string olarak döndürür;
    herhangi bir bekleyen talep bulunmuyorsa rozetin görünmemesi için None döner.

    Args:
        request: Mevcut HTTP isteği.

    Returns:
        str | None: Bekleyen işlem sayısı (string) veya rozet gösterilmeyecekse None.
    """
    count = Book.objects.filter(status__in=['pending', 'return_pending']).count()
    return str(count) if count > 0 else None


def dashboard_callback(request: HttpRequest, context: dict[str, Any]) -> dict[str, Any]:
    """Django Unfold ana gösterge paneli için gerçek veriye dayalı KPI ve hareket verilerini hazırlar.

    Hesaplanan KPI metrikleri:
      - Toplam Kitap: Sistemde kayıtlı tüm kitap sayısı.
      - Müsait Kitaplar: Durumu iade edilmiş/reddedilmiş ve ödünç alanı olmayan kitaplar.
      - Onay Bekleyen Ödünç Talepleri: Durumu 'pending' olan kitaplar.
      - İade Onayı Bekleyenler: Durumu 'return_pending' olan kitaplar.
      - Aktif Ödünçteki Kitaplar: Durumu 'approved' olan kitaplar.

    Ayrıca N+1 sorgu optimizasyonu sağlanarak (select_related('borrowed_by'))
    son 5 kitap kaydı ve ilişkili kullanıcı bilgisi 'recent_loans' listesine eklenir.

    Args:
        request: Mevcut HTTP isteği.
        context: Django Unfold şablon bağlamı (context).

    Returns:
        dict[str, Any]: Zenginleştirilmiş şablon bağlamı.
    """
    total_books: int = Book.objects.count()
    available_books: int = Book.objects.filter(
        status__in=['returned', 'denied'],
        borrowed_by__isnull=True,
    ).count()
    pending_borrows: int = Book.objects.filter(status='pending').count()
    pending_returns: int = Book.objects.filter(status='return_pending').count()
    approved_loans: int = Book.objects.filter(status='approved').count()

    recent_loans: list[Book] = list(
        Book.objects.select_related('borrowed_by').all()[:5]
    )

    kpi_stats: dict[str, int] = {
        "total_books": total_books,
        "available_books": available_books,
        "pending_borrows": pending_borrows,
        "pending_returns": pending_returns,
        "approved_loans": approved_loans,
    }

    kpi_cards: list[dict[str, Any]] = [
        {
            "title": "Toplam Kitap",
            "metric": total_books,
            "icon": "auto_stories",
            "description": "Kütüphanede kayıtlı toplam kitap sayısı",
        },
        {
            "title": "Müsait Kitaplar",
            "metric": available_books,
            "icon": "check_circle",
            "description": "Ödünç alınabilir durumdaki kitaplar",
        },
        {
            "title": "Onay Bekleyen Ödünç Talepleri",
            "metric": pending_borrows,
            "icon": "hourglass_top",
            "description": "Öğrencilerin onay bekleyen ödünç talepleri",
        },
        {
            "title": "İade Onayı Bekleyenler",
            "metric": pending_returns,
            "icon": "assignment_return",
            "description": "İade işlemi onay bekleyen kitaplar",
        },
        {
            "title": "Aktif Ödünçteki Kitaplar",
            "metric": approved_loans,
            "icon": "person_pin",
            "description": "Öğrencilerin kullanımında olan kitaplar",
        },
    ]

    context.update({
        "kpi_stats": kpi_stats,
        "kpi_cards": kpi_cards,
        "recent_loans": recent_loans,
        "recent_books": recent_loans,
    })

    return context
