from django.urls import path

from tests.demo.catalog import views

app_name = "catalog"

urlpatterns = [
    path("", views.ProductListView.as_view(), name="list"),
    path("search/", views.search, name="search"),
    path("search/<str:query>/", views.search, name="search"),
    path("new/", views.ProductCreateView.as_view(), name="create"),
    path("stock/", views.StockView.as_view(), name="stock"),
    path("wishlist/", views.WishlistView.as_view(), name="wishlist"),
    path("suppliers/", views.SupplierView.as_view(), name="suppliers"),
    path("<slug:slug>/", views.ProductDetailView.as_view(), name="detail"),
    path("<slug:slug>/delete/", views.ProductDeleteView.as_view(), name="delete"),
    path("<slug:slug>/reviews/", views.ReviewView.as_view(), name="reviews"),
]
