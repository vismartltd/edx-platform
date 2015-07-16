"""Url configuration for the auth module."""

from django.conf.urls import include, patterns, url
from pipeline import redirect_to_studio

urlpatterns = patterns(
    '',
    url(r'^auth/', include('social.apps.django_app.urls', namespace='social')),
    url(r'^auth_redirect_to/studio', redirect_to_studio),
)
