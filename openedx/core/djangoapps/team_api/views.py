"""
NOTE: this API is WIP and has not yet been approved. Do not use this API without talking to Christina or Andy.

For more information, see:
https://openedx.atlassian.net/wiki/display/TNL/Team+API
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework import permissions
from rest_framework.parsers import JSONParser

from django.db import transaction
from django.utils.translation import ugettext as _

from openedx.core.lib.api.authentication import (
    SessionAuthenticationAllowInactiveUser,
    OAuth2AuthenticationAllowInactiveUser,
)
from openedx.core.lib.api.parsers import MergePatchParser
from openedx.core.lib.api.permissions import IsUserInUrlOrStaff
#from ..errors import UserNotFound, UserNotAuthorized

from opaque_keys.edx.keys import CourseKey

from .models import CourseTeam, CourseTeamMembership
from .serializers import CourseTeamSerializer, MembershipSerializer


class TeamsListView(APIView):

    authentication_classes = (OAuth2AuthenticationAllowInactiveUser, SessionAuthenticationAllowInactiveUser)
    #permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        """
        GET /api/team/v0/teams/
        """

        serializer = CourseTeamSerializer(CourseTeam.objects.all(), many=True)
        return Response(serializer.data)

    def post(self, request):
        """
        POST /api/team/v0/teams/
        """

        course_id = CourseKey.from_string(request.DATA['course_id'])

        team = CourseTeam.create(
            name=request.DATA['name'],
            course_id=course_id,
            description=request.DATA['description'],
            topic_id=request.DATA['topic_id'],
            country=request.DATA.get('country'),
            language=request.DATA.get('language'),
        )

        return Response(CourseTeamSerializer(team).data)


class TeamsDetailView(APIView):

    def get(self, request, team_id):
        """
        GET /api/team/v0/teams/{team_id}
        """

        return Response(CourseTeamSerializer(CourseTeam.objects.get(team_id=team_id)).data)


class TeamMembershipListView(APIView):

    authentication_classes = (OAuth2AuthenticationAllowInactiveUser, SessionAuthenticationAllowInactiveUser)
    #permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        """
        GET /api/team/v0/team_membership
        """
        serializer = MembershipSerializer(CourseTeamMembership.objects.all(), many=True)
        return Response(serializer.data)

class TeamMembershipDetailView(APIView):

    def get(self, request, team_id, username):
        """
        GET /api/team/v0/team_membership/{team_id},{username}
        """

        try:
            membership = CourseTeamMembership.objects.get(team__team_id=team_id, user__username=username)
            return Response(MembershipSerializer(membership).data)
        except CourseTeamMembership.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
