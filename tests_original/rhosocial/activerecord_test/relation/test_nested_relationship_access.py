# tests/rhosocial/activerecord_test/relation/test_nested_relationship_access.py
import time


def test_nested_relationship_access(author, book, chapter):
    """Test accessing deeply nested relationships."""
    # First level relation access
    author_books = author.books()
    assert author_books is not None

    # Second level relation access
    book_chapters = author_books[0].chapters()
    assert book_chapters is not None


def test_bidirectional_relationship_consistency(author, book):
    """Test consistency of bidirectional relationships."""
    # Forward relationship
    author_books = author.books()
    assert len(author_books) > 0
    first_book = author_books[0]

    # Backward relationship
    book_author = first_book.author()
    assert book_author.id == author.id


def test_custom_loader_caching(author):
    """Test custom loader with caching."""
    # First access - should use loader
    books = author.books()
    assert books is not None

    # Second access - should use cache
    cached_books = author.books()
    assert cached_books == books

    # Wait for TTL expiration
    time.sleep(1.1)

    # Third access - should use loader again
    new_books = author.books()
    assert new_books is not None


def test_one_to_one_relationship(author, profile):
    """Test HasOne/BelongsTo relationship pair."""
    # Access from author side
    author_profile = author.profile()
    assert author_profile is not None
    assert author_profile.author_id == author.id

    # Access from profile side
    profile_author = profile.author()
    assert profile_author is not None
    assert profile_author.id == profile.author_id
