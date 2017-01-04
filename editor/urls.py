from django.conf.urls import url
from editor import views

urlpatterns = [
	url(r'^users/$', views.users),
	url(r'^users/(?P<user_id>[^/]+)/$', views.user),
	url(r'^documents/(?P<document_id>[^/]+)/$', views.document),
	url(r'^documents/(?P<document_id>[^/]+)/changes/$', views.document_changes),
]
