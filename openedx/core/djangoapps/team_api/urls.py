"""
Defines the URL routes for this app.
"""

#from .accounts.views import AccountView
#from .preferences.views import PreferencesView, PreferencesDetailView

from django.conf.urls import patterns, url

from .views import TeamsListView, TeamsDetailView, TeamMembershipListView, TeamMembershipDetailView

TEAM_ID_PATTERN = r'(?P<team_id>[\w.+-]+)'
USERNAME_PATTERN = r'(?P<username>[\w.+-]+)'

urlpatterns = patterns(
    '',
    url(
        r'^v0/teams$',
        TeamsListView.as_view(),
        name="teams_list"
    ),
    url(
        r'^v0/teams/' + TEAM_ID_PATTERN + '$',
        TeamsDetailView.as_view(),
        name="teams_detail"
    ),
    url(
        r'^v0/team_membership$',
        TeamMembershipListView.as_view(),
        name="team_membership_list"
    ),
    url(
        r'^v0/team_membership/' + TEAM_ID_PATTERN + ',' + USERNAME_PATTERN + '$',
        TeamMembershipDetailView.as_view(),
        name="team_membership_detail"
    )
)
