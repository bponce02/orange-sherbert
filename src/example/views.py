from orange_sherbert.view import CRUDView
from .models import Book, Author

class BookCRUDView(CRUDView):
    model = Book

class AuthorCRUDView(CRUDView):
    model = Author
    