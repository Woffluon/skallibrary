// Sezai Karakoç Anadolu Lisesi Kütüphanesi - İstemci İşlevleri

document.addEventListener('DOMContentLoaded', () => {
    // 1. Mobil Menü Açma/Kapatma
    const navToggle = document.getElementById('navToggle');
    const navMenu = document.getElementById('navMenu');

    if (navToggle && navMenu) {
        navToggle.addEventListener('click', () => {
            const isExpanded = navToggle.getAttribute('aria-expanded') === 'true';
            navToggle.setAttribute('aria-expanded', !isExpanded);
            navMenu.classList.toggle('nav-open');
        });

        // Dışarı tıklandığında menüyü kapat
        document.addEventListener('click', (event) => {
            if (!navToggle.contains(event.target) && !navMenu.contains(event.target)) {
                navMenu.classList.remove('nav-open');
                navToggle.setAttribute('aria-expanded', 'false');
            }
        });
    }

    // 2. Canlı Kitap Arama ve Filtreleme
    const bookSearch = document.getElementById('bookSearch');
    const booksGrid = document.getElementById('booksGrid');
    const bookCards = document.querySelectorAll('.book-card');
    const bookCountElem = document.getElementById('booksCount');
    const noResultsMsg = document.getElementById('noSearchResults');

    if (bookSearch && bookCards.length > 0) {
        const totalBooks = bookCards.length;

        bookSearch.addEventListener('input', (e) => {
            const query = e.target.value.trim().toLocaleLowerCase('tr-TR');
            let visibleCount = 0;

            bookCards.forEach((card) => {
                const name = (card.getAttribute('data-name') || '').toLocaleLowerCase('tr-TR');
                const author = (card.getAttribute('data-author') || '').toLocaleLowerCase('tr-TR');

                if (name.includes(query) || author.includes(query)) {
                    card.style.display = '';
                    visibleCount++;
                } else {
                    card.style.display = 'none';
                }
            });

            if (bookCountElem) {
                if (query === '') {
                    bookCountElem.textContent = `Toplam ${totalBooks} kitap`;
                } else {
                    bookCountElem.textContent = `${visibleCount} / ${totalBooks} kitap bulundu`;
                }
            }

            if (noResultsMsg) {
                if (visibleCount === 0) {
                    noResultsMsg.style.display = 'block';
                } else {
                    noResultsMsg.style.display = 'none';
                }
            }
        });
    }
});
