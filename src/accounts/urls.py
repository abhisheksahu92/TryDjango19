from django.contrib import admin
from django.urls import path
from accounts import views

app_name = 'comments'

urlpatterns = [
    path('login',views.login_view,name='login'),
    path('register',views.register_view,name='logout'),
    path('logout',views.logout_view,name='register'),

]