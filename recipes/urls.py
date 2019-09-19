from django.urls import path, re_path

from . import views

urlpatterns = [
    re_path(r'^ingredients/(?:$|index/$)', views.list_ingredients,
            name='ingredients-index'),
    path('mixture/new/', views.add_new_mixture, name='mixture-new'),
    path('mixture/preview', views.mixture_preview, name='mixture-preview'),
    path('new/', views.RecipeFormView.as_view(), name='recipe-new'),
]
