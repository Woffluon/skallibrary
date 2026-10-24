import io
from PIL import Image
from django.contrib.auth import get_user_model
from django.core import mail
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

    def test_student_borrow_request_pending_and_email_sent(self):
        self.client.login(username='student1', password='password123')
        response = self.client.post(reverse('borrow_book', kwargs={'book_id': self.book.id}))
        self.assertRedirects(response, reverse('book_list'))

        self.book.refresh_from_db()
        self.assertEqual(self.book.status, 'pending')
        self.assertEqual(self.book.borrowed_by, self.student)

        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('Nutuk', mail.outbox[0].subject)
        self.assertIn('admin@example.com', mail.outbox[0].to)

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
