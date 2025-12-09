from orange_sherbert.view import CRUDView
from .models import Book, Author

class BookCRUDView(CRUDView):
    model = Book
    fields = '__all__'
    filter_fields = ['author', 'checked_out']
    search_fields = ['title', 'isbn']
    restricted_fields = {'ordered_from': 'can_view_ordered_from'}

class AuthorCRUDView(CRUDView):
    model = Author
    fields = '__all__'
    search_fields = ['name']
    