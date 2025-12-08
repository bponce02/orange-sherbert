from django.db import models

class Book(models.Model):
    title = models.CharField(max_length=100)
    author = models.ForeignKey('Author', on_delete=models.CASCADE)
    isbn = models.CharField(max_length=13)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    pub_date = models.DateField()
    checked_out = models.BooleanField(default=False)
    def __str__(self):
        return self.title

class Author(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

