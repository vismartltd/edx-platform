"""
Defines the URL routes for this app.
"""

#from .accounts.views import AccountView
#from .preferences.views import PreferencesView, PreferencesDetailView

from django.conf.urls import patterns, url

from .views import TeamsView

urlpatterns = patterns(
    '',
    url(
        r'^v0/teams$',
        TeamsView.as_view(),
        name="test_of_team_api"
    ),
)
