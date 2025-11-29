from rest_framework.pagination import PageNumberPagination


class HabitPagination(PageNumberPagination):
    page_size = 2
    page_query_param = "page"