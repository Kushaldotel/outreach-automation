from django.urls import path

from . import views

urlpatterns = [
    path('leads/upload/', views.upload_leads),
    path('leads/', views.list_leads),
    path('leads/bulk-delete/', views.bulk_delete_leads),
    path('leads/<int:pk>/', views.lead_detail),
    path('template/', views.template_view),
    path('campaign/send/', views.send_campaign),
    path('inbox/poll/', views.poll_inbox),
    path('inbox/<int:pk>/reanalyze/', views.reanalyze_inbox),
    path('inbox/', views.list_inbox),
    path('sent/', views.list_sent),
    path('settings/', views.app_settings),
    path('replies/', views.list_replies),
    path('drafts/', views.list_drafts),
    path('drafts/<int:pk>/', views.update_draft),
    path('drafts/<int:pk>/send/', views.send_draft),
    path('drafts/<int:pk>/reject/', views.reject_draft),
    path('stats/', views.stats),
]
