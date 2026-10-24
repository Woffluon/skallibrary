import io
from PIL import Image
import importlib
import os
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.db import IntegrityError, transaction
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from library.admin import approve_borrow, confirm_return, deny_borrow, deny_return
from library.models import Book

User = get_user_model()


class MockModelAdmin:
    def message_user(self, request, message):
        pass


class BorrowReturnFlowTests(TestCase):
    def setUp(self):
        self.student = User.objects.create_user(username='student1', password='password123')
        self.other_student = User.objects.create_user(username='student2', password='password123')
        self.admin = User.objects.create_superuser(username='admin', password='adminpassword')
        self.book = Book.objects.create(name='Nutuk', author='Mustafa Kemal Atatürk')

    def test_public_signup_removed(self):
        response = self.client.get('/accounts/signup/')
        self.assertEqual(response.status_code, 404)

    def test_student_borrow_request_sets_pending(self):
        self.client.login(username='student1', password='password123')
        response = self.client.post(reverse('borrow_book', kwargs={'book_id': self.book.id}))
        self.assertRedirects(response, reverse('book_list'))

        self.book.refresh_from_db()
        self.assertEqual(self.book.status, 'pending')
        self.assertEqual(self.book.borrowed_by, self.student)

    def test_cannot_borrow_if_already_pending_or_approved(self):
        self.book.status = 'pending'
        self.book.borrowed_by = self.student
        self.book.save()

        self.client.login(username='student2', password='password123')
        self.client.post(reverse('borrow_book', kwargs={'book_id': self.book.id}))
        self.book.refresh_from_db()
        self.assertEqual(self.book.borrowed_by, self.student)

        self.book.status = 'approved'
        self.book.save()
        self.client.post(reverse('borrow_book', kwargs={'book_id': self.book.id}))
        self.book.refresh_from_db()
        self.assertEqual(self.book.borrowed_by, self.student)

    def test_admin_approve_and_deny_actions(self):
        self.book.status = 'pending'
        self.book.borrowed_by = self.student
        self.book.save()

        approve_borrow(MockModelAdmin(), None, Book.objects.filter(id=self.book.id))
        self.book.refresh_from_db()
        self.assertEqual(self.book.status, 'approved')
        self.assertTrue(self.book.borrowed)

        self.book.status = 'pending'
        self.book.save()
        deny_borrow(MockModelAdmin(), None, Book.objects.filter(id=self.book.id))
        self.book.refresh_from_db()
        self.assertEqual(self.book.status, 'denied')
        self.assertIsNone(self.book.borrowed_by)
        self.assertTrue(self.book.is_available)

    def test_admin_deny_return_action_and_action_isolation(self):
        # Setup book in return_pending state
        self.book.status = 'return_pending'
        self.book.borrowed_by = self.student
        self.book.save()

        # "Ödünç talebini reddet" on return_pending book changes nothing
        deny_borrow(MockModelAdmin(), None, Book.objects.filter(id=self.book.id))
        self.book.refresh_from_db()
        self.assertEqual(self.book.status, 'return_pending')
        self.assertEqual(self.book.borrowed_by, self.student)

        # "Ödünç talebini onayla" on return_pending book changes nothing
        approve_borrow(MockModelAdmin(), None, Book.objects.filter(id=self.book.id))
        self.book.refresh_from_db()
        self.assertEqual(self.book.status, 'return_pending')
        self.assertEqual(self.book.borrowed_by, self.student)

        # "İade talebini reddet" resets return_pending -> approved and keeps borrowed_by
        deny_return(MockModelAdmin(), None, Book.objects.filter(id=self.book.id))
        self.book.refresh_from_db()
        self.assertEqual(self.book.status, 'approved')
        self.assertEqual(self.book.borrowed_by, self.student)

        # "İade talebini reddet" or "İadeyi onayla" on pending book changes nothing
        self.book.status = 'pending'
        self.book.save()
        deny_return(MockModelAdmin(), None, Book.objects.filter(id=self.book.id))
        self.book.refresh_from_db()
        self.assertEqual(self.book.status, 'pending')

        confirm_return(MockModelAdmin(), None, Book.objects.filter(id=self.book.id))
        self.book.refresh_from_db()
        self.assertEqual(self.book.status, 'pending')

    def test_return_flow(self):
        self.book.status = 'approved'
        self.book.borrowed_by = self.student
        self.book.save()

        # Another student cannot return this book
        self.client.login(username='student2', password='password123')
        self.client.post(reverse('return_book', kwargs={'book_id': self.book.id}))
        self.book.refresh_from_db()
        self.assertEqual(self.book.status, 'approved')

        # Borrower returns it -> return_pending
        self.client.login(username='student1', password='password123')
        response = self.client.post(reverse('return_book', kwargs={'book_id': self.book.id}))
        self.assertRedirects(response, reverse('book_list'))
        self.book.refresh_from_db()
        self.assertEqual(self.book.status, 'return_pending')

        # Admin confirms return -> returned
        confirm_return(MockModelAdmin(), None, Book.objects.filter(id=self.book.id))
        self.book.refresh_from_db()
        self.assertEqual(self.book.status, 'returned')
        self.assertIsNone(self.book.borrowed_by)
        self.assertTrue(self.book.is_available)

    def test_logged_out_visibility_does_not_leak_borrower(self):
        self.book.status = 'approved'
        self.book.borrowed_by = self.student
        self.book.save()

        response = self.client.get(reverse('book_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Ödünçte')
        self.assertNotContains(response, 'student1')

    def test_cover_placeholder_when_no_cover(self):
        response = self.client.get(reverse('book_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'book-cover-placeholder')

    def test_cover_image_display_when_present(self):
        image = Image.new('RGB', (100, 100), color='blue')
        byte_io = io.BytesIO()
        image.save(byte_io, format='JPEG')
        uploaded_image = SimpleUploadedFile('test_cover.jpg', byte_io.getvalue(), content_type='image/jpeg')

        book_with_cover = Book.objects.create(name='Kapaklı Kitap', author='Yazar', cover=uploaded_image)
        try:
            response = self.client.get(reverse('book_list'))
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, book_with_cover.cover.url)
        finally:
            if book_with_cover.cover:
                book_with_cover.cover.delete(save=False)


class BookModelIntegrityAndSecurityTests(TestCase):
    """
    - Model durum makinesi metotları (request_borrow, approve_borrow, deny_borrow, request_return, confirm_return, deny_return)
    - Geçersiz durum geçişlerinde ValidationError fırlatılması
    - Veritabanı CheckConstraint ile durum ve borrowed_by tutarsızlığında IntegrityError fırlatılması
    - DEBUG=False ve DJANGO_SECRET_KEY='' yapılandırmasında ImproperlyConfigured fırlatılması
    """

    def setUp(self):
        self.student = User.objects.create_user(username='ogrenci1', password='parola123')
        self.other_student = User.objects.create_user(username='ogrenci2', password='parola123')
        self.book = Book.objects.create(name='Kuyucaklı Yusuf', author='Sabahattin Ali')

    def test_model_valid_state_transitions(self):
        """
        Model durum geçiş metotlarının standart mutlu yol (happy path) akış testi:
        request_borrow -> approve_borrow -> request_return -> confirm_return
        """
        # 1. Ödünç talebi oluşturma (returned -> pending)
        self.book.request_borrow(self.student)
        self.assertEqual(self.book.status, 'pending')
        self.assertEqual(self.book.borrowed_by, self.student)

        # 2. Yönetici ödünç onaylama (pending -> approved)
        self.book.approve_borrow()
        self.assertEqual(self.book.status, 'approved')
        self.assertEqual(self.book.borrowed_by, self.student)

        # 3. Öğrenci iade talebi oluşturma (approved -> return_pending)
        self.book.request_return(self.student)
        self.assertEqual(self.book.status, 'return_pending')
        self.assertEqual(self.book.borrowed_by, self.student)

        # 4. Yönetici iade onaylama (return_pending -> returned)
        self.book.confirm_return()
        self.assertEqual(self.book.status, 'returned')
        self.assertIsNone(self.book.borrowed_by)

    def test_model_deny_transitions(self):
        """
        Model ret durum geçişlerinin testi:
        - deny_borrow (pending -> denied, borrowed_by sıfırlanır)
        - deny_return (return_pending -> approved, borrowed_by korunur)
        """
        # 1. Ödünç talebini reddetme
        self.book.request_borrow(self.student)
        self.book.deny_borrow()
        self.assertEqual(self.book.status, 'denied')
        self.assertIsNone(self.book.borrowed_by)

        # Reddedilmiş kitap tekrar ödünç talep edilebilir ve onaylanabilir
        self.book.request_borrow(self.student)
        self.book.approve_borrow()

        # 2. İade talebini reddetme
        self.book.request_return(self.student)
        self.book.deny_return()
        self.assertEqual(self.book.status, 'approved')
        self.assertEqual(self.book.borrowed_by, self.student)

    def test_invalid_state_transitions_raise_validation_error(self):
        """
        Geçersiz durum geçişlerinde django.core.exceptions.ValidationError fırlatıldığının testi.
        """
        # 1. Kitap zaten pending durumundayken tekrar ödünç talebinde bulunulamaz
        self.book.status = 'pending'
        self.book.borrowed_by = self.student
        self.book.save()
        with self.assertRaises(ValidationError):
            self.book.request_borrow(self.other_student)

        # 2. Kitap approved durumundayken yeni ödünç talebinde bulunulamaz
        self.book.status = 'approved'
        self.book.save()
        with self.assertRaises(ValidationError):
            self.book.request_borrow(self.student)

        # 3. Kitabı ödünç almamış farklı bir öğrenci iade talebi iletemez
        with self.assertRaises(ValidationError):
            self.book.request_return(self.other_student)

        # 4. pending durumunda olmayan kitap için approve_borrow çağrılamaz
        self.book.status = 'returned'
        self.book.borrowed_by = None
        self.book.save()
        with self.assertRaises(ValidationError):
            self.book.approve_borrow()

        # 5. pending durumunda olmayan kitap için deny_borrow çağrılamaz
        with self.assertRaises(ValidationError):
            self.book.deny_borrow()

        # 6. return_pending durumunda olmayan kitap için confirm_return çağrılamaz
        with self.assertRaises(ValidationError):
            self.book.confirm_return()

        # 7. return_pending durumunda olmayan kitap için deny_return çağrılamaz
        with self.assertRaises(ValidationError):
            self.book.deny_return()

    def test_state_and_borrower_consistency_integrity_error(self):
        """
        Durum ve borrowed_by tutarsızlığında veritabanı CheckConstraint kaynaklı
        django.db.IntegrityError fırlatıldığının testi.
        """
        # 1. 'returned' durumunda borrowed_by dolu olamaz
        with transaction.atomic():
            with self.assertRaises(IntegrityError):
                Book.objects.create(name='Hatalı Kitap 1', author='Yazar 1', status='returned', borrowed_by=self.student)

        # 2. 'denied' durumunda borrowed_by dolu olamaz
        with transaction.atomic():
            with self.assertRaises(IntegrityError):
                Book.objects.create(name='Hatalı Kitap 2', author='Yazar 2', status='denied', borrowed_by=self.student)

        # 3. 'approved' durumunda borrowed_by None olamaz
        with transaction.atomic():
            with self.assertRaises(IntegrityError):
                Book.objects.create(name='Hatalı Kitap 3', author='Yazar 3', status='approved', borrowed_by=None)

        # 4. 'pending' durumunda borrowed_by None olamaz
        with transaction.atomic():
            with self.assertRaises(IntegrityError):
                Book.objects.create(name='Hatalı Kitap 4', author='Yazar 4', status='pending', borrowed_by=None)

        # 5. 'return_pending' durumunda borrowed_by None olamaz
        with transaction.atomic():
            with self.assertRaises(IntegrityError):
                Book.objects.create(name='Hatalı Kitap 5', author='Yazar 5', status='return_pending', borrowed_by=None)

    def test_production_secret_key_required_when_debug_false(self):
        """
        DEBUG=False ve DJANGO_SECRET_KEY="" olduğunda
        django.core.exceptions.ImproperlyConfigured fırlatıldığının testi.
        """
        import config.settings

        try:
            with patch.dict(os.environ, {"DJANGO_DEBUG": "False", "DJANGO_SECRET_KEY": ""}):
                with self.assertRaises(ImproperlyConfigured):
                    importlib.reload(config.settings)
        finally:
            # Test ortamının ayarlarını orijinal haline geri yükle
            importlib.reload(config.settings)


class BookListPerformanceAndCoverValidationTests(TestCase):
    """
    - Kitap listesinde N+1 sorgu problemi tespiti (sorgu sayısının sabit olması)
    - Kapak görseli dosya boyutu sınırlaması (maksimum 2MB) doğrulaması
    - Kapak görseli dosya uzantısı doğrulaması (güvenli görsel formatları)
    - Veritabanı indekslerinin tanımlanmış olmasının doğrulanması (name + author bileşik indeksi ve status indeksi)
    """

    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password123')
        self.other_user = User.objects.create_user(username='otheruser', password='password123')

    def test_book_list_query_count_constant(self):
        """
        10 adet ödünç verilmiş ve 5 adet müsait kitap olduğunda,
        kitap listeleme sayfasının N+1 problemi olmadan sabit 3 sorgu ile çalışması beklenir.
        kitap listeleme sayfasında N+1 sorgusu oluşmadığını doğrular.
        """
        # 10 adet ödünç verilmiş kitap oluştur
        for i in range(10):
            Book.objects.create(
                name=f"Ödünç Kitap {i}",
                author=f"Yazar {i}",
                status='approved',
                borrowed_by=self.other_user
            )
        # 5 adet ödünç verilmemiş (müsait) kitap oluştur
        for i in range(5):
            Book.objects.create(
                name=f"Müsait Kitap {i}",
                author=f"Yazar {i}",
                status='returned',
                borrowed_by=None
            )

        self.client.login(username='testuser', password='password123')

        # Giriş yapmış kullanıcı ile kitap listeleme sayfası istendiğinde
        # 1 session sorgusu + 1 giriş yapan auth_user sorgusu + 1 optimize edilmiş kitap sorgusu = toplam 3 sorgu olmalıdır.
        with self.assertNumQueries(3):
            response = self.client.get(reverse('book_list'))
            self.assertEqual(response.status_code, 200)

    def test_cover_image_size_limit_validation(self):
        """
        2MB'den büyük (2.5MB) kapak resmi yüklendiğinde full_clean() çağrısının
        ValidationError fırlatması gerekir.
        Mevcut kodda boyut sınırlama doğrulayıcısı olmadığı için FAIL etmelidir.
        """
        file_size_2_5_mb = int(2.5 * 1024 * 1024)
        large_image_content = b'x' * file_size_2_5_mb
        large_cover = SimpleUploadedFile(
            name='large_cover.jpg',
            content=large_image_content,
            content_type='image/jpeg'
        )

        book = Book(
            name='Büyük Kapaklı Kitap',
            author='Test Yazar',
            cover=large_cover
        )

        with self.assertRaises(ValidationError):
            book.full_clean()

    def test_cover_image_extension_validation(self):
        """
        Geçersiz uzantıya sahip dosya (örn. .exe veya .sh) yüklendiğinde full_clean()
        çağrısının ValidationError fırlatması gerekir.
        Mevcut kodda uzantı doğrulayıcısı olmadığı için FAIL etmelidir.
        """
        malicious_file = SimpleUploadedFile(
            name='dangerous_script.sh',
            content=b'#!/bin/bash\necho "test"',
            content_type='text/x-shellscript'
        )

        book = Book(
            name='Zararlı Dosyalı Kitap',
            author='Test Yazar',
            cover=malicious_file
        )

        with self.assertRaises(ValidationError):
            book.full_clean()

    def test_book_indexes_defined(self):
        """
        Book modeli üzerinde performans için gerekli indekslerin tanımlı olduğunu doğrular:
        - Book._meta.indexes içinde 'book_name_author_idx' isimli indeks bulunmalı.
        - Book._meta.get_field('status').db_index değeri True olmalı.
        Mevcut kodda indeksler tanımlı olmadığı için FAIL etmelidir.
        """
        index_names = [index.name for index in Book._meta.indexes]
        self.assertIn(
            'book_name_author_idx',
            index_names,
            "Book modeli 'book_name_author_idx' bileşik indeksine sahip olmalıdır."
        )
        self.assertTrue(
            Book._meta.get_field('status').db_index,
            "'status' alanı üzerinde db_index=True tanımlanmış olmalıdır."
        )

