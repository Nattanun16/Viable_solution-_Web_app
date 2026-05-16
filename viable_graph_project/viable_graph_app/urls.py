from django.urls import path
from . import views

urlpatterns = [
    path('', views.home_view, name='home'),
    path('api/chart-data/', views.problem_chart_data, name='chart_data'), # ลิงก์สำหรับดึงสถิติไปทำกราฟ
]