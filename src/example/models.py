from django.db import models

class Book(models.Model):
    title = models.CharField(max_length=100,verbose_name='Title')
    author = models.ForeignKey('Author', on_delete=models.CASCADE,verbose_name='Author')
    isbn = models.CharField(max_length=13,verbose_name='ISBN')
    price = models.DecimalField(max_digits=10, decimal_places=2,verbose_name='Price')
    pub_date = models.DateField(verbose_name='Publication Date')
    checked_out = models.BooleanField(default=False,verbose_name='Checked Out')
    def __str__(self):
        return self.title

class Author(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

