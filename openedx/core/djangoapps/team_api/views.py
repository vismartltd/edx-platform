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

from courseware import courses
from opaque_keys.edx.keys import CourseKey

from .models import CourseTeam
from .serializers import CourseTeamSerializer

class TeamsView(APIView):

    authentication_classes = (OAuth2AuthenticationAllowInactiveUser, SessionAuthenticationAllowInactiveUser)
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        """
        GET /api/team/v0/teams/
        """

        """
        request.user

        try:
            user_preferences = get_user_preferences(request.user, username=username)
        except UserNotAuthorized:
            return Response(status=status.HTTP_403_FORBIDDEN)
        except UserNotFound:
            return Response(status=status.HTTP_404_NOT_FOUND)
        """

        serializer = CourseTeamSerializer(CourseTeam.objects.all(), many=True)
        return Response(serializer.data)

    def post(self, request):
        """
        POST /api/team/v0/teams/

        if not request.DATA or not getattr(request.DATA, "keys", None):
            error_message = _("No data provided for user preference update")
            return Response(
                {
                    "developer_message": error_message,
                    "user_message": error_message
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        try:
            with transaction.commit_on_success():
                update_user_preferences(request.user, request.DATA, username=username)
        except UserNotAuthorized:
            return Response(status=status.HTTP_403_FORBIDDEN)
        except UserNotFound:
            return Response(status=status.HTTP_404_NOT_FOUND)
        except PreferenceValidationError as error:
            return Response(
                {"field_errors": error.preference_errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        except PreferenceUpdateError as error:
            return Response(
                {
                    "developer_message": error.developer_message,
                    "user_message": error.user_message
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        return Response(status=status.HTTP_204_NO_CONTENT)


        {
          "id": "solar_team37",
          "name": "Solar Team",
          "topic_id": "solar_power",
          "course_id": "energy101",
          "is_active": true,
          "description": "The Solar Team are interested in all aspects of solar power and how it can gain widespread adoption.",
          "language": "en",
          "membership": [
            {
              "user": {
                "username: "andya",
                "url": "https://openedx.example.com/api/user/v1/accounts/andya"
              },
              "date_joined": "2015-04-09T17:31:56Z",
              "last_activity": "2015-04-09T17:31:56Z"
            },
            // ...
          ],
          // ...
        }
        cls, team_name, course_id, description, topic_id=None, course_user_group=None, country=None, language=None
        """

        course_id = CourseKey.from_string(request.DATA['course_id'])

        team = CourseTeam.create(
            team_name=request.DATA['name'],
            course_id=course_id,
            description=request.DATA['description'],
            topic_id=request.DATA['topic_id'],
            country=request.DATA.get('country'),
            language=request.DATA.get('language'),
        ).course_user_group

        return Response(team)
