from rest_framework.pagination import PageNumberPagination

class BancoExercicioPagination(PageNumberPagination):
    page_size = 20  # padrão inicial
    page_size_query_param = "page_size"
    max_page_size = 100
