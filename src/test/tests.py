import pytest
from example.models import Author, Book


@pytest.fixture
def author():
    return Author.objects.create(name='Test Author')


@pytest.fixture
def book(author):
    return Book.objects.create(title='Test Book', author=author)


@pytest.mark.django_db
@pytest.mark.parametrize('url_template,needs_object', [
    ('/author/', False),
    ('/author/create/', False),
    ('/author/{}/', True),
    ('/author/{}/update/', True),
    ('/author/{}/delete/', True),
    ('/book/', False),
    ('/book/create/', False),
    ('/book/{}/', True),
    ('/book/{}/update/', True),
    ('/book/{}/delete/', True),
])
def test_all_views_return_200(client, author, book, url_template, needs_object):
    """Test that all CRUD views return 200."""
    if needs_object:
        # Use author for author URLs, book for book URLs
        obj = book if url_template.startswith('/book') else author
        url = url_template.format(obj.pk)
    else:
        url = url_template
    
    response = client.get(url)
    assert response.status_code == 200