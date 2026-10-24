# SKAL Kütüphanesi

Sezai Karakoç Anadolu Lisesi kütüphane yönetim sistemi. Öğrenci ödünç/iade onay döngüsü, kitap kataloğu ve Django admin yönetimini sağlar.

## Akış Şeması

```mermaid
stateDiagram-v2
    [*] --> Müsait: Kitap oluşturuldu (returned)

    Müsait --> Onay_Bekliyor: Öğrenci ödünç talebi (pending)
    note right of Onay_Bekliyor
        Yöneticiye e-posta bildirimi gider
    end note

    Onay_Bekliyor --> Ödünç_Verildi: Admin onaylar (approved)
    Onay_Bekliyor --> Müsait: Admin reddeder (denied)

    Ödünç_Verildi --> İade_Bekliyor: Öğrenci iade talebi (return_pending)
    İade_Bekliyor --> Müsait: Admin iadeyi onaylar (returned)
    İade_Bekliyor --> Ödünç_Verildi: Admin iadeyi reddeder (approved)
```

## Kurulum ve Çalıştırma

```bash
python -m venv venv
source venv/bin/activate  # Windows: .\venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

- Katalog: `http://127.0.0.1:8000/`
- Yönetim paneli: `http://127.0.0.1:8000/admin/`

## Testler

```bash
python manage.py test
```

## Canlı Ortam

Canlıya çıkarken `.env.example` dosyasını `.env` olarak kopyalayıp değişkenleri tanımlayın:

```bash
cp .env.example .env
python manage.py collectstatic --noinput
```

`DJANGO_DEBUG=False` olduğunda HTTPS, HSTS, secure cookies ve WhiteNoise statik sunumu otomatik devreye girer.

## Lisans

AGPL-3.0. Detaylar için [LICENSE](LICENSE).
