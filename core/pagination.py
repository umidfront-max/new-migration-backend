"""Sahifalash sozlamalari."""
from rest_framework.pagination import PageNumberPagination


class DefaultPagination(PageNumberPagination):
    """Standart sahifalash — `?page=2&page_size=100`."""

    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 500


class LargePagination(DefaultPagination):
    """Xarita va grafik uchun — bir so'rovda hamma yozuv kerak bo'lganda."""

    page_size = 500
