from django.contrib.auth.models import User
from rest_framework import serializers
from .models import CourseTeam, CourseTeamMembership

class CollapsedUserSerializer(serializers.HyperlinkedModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name='accounts_api', lookup_field='username')

    class Meta:
        model = User
        fields = ("username", "url")


class CollapsedCourseTeamSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.CharField(source='team_id')
    url = serializers.HyperlinkedIdentityField(view_name='teams_detail', lookup_field='team_id')

    class Meta:
        model = CourseTeam
        fields = ("id", "url")


class UserMembershipSerializer(serializers.ModelSerializer):
    user = CollapsedUserSerializer()

    class Meta:
        model = CourseTeamMembership
        fields = ("user", "date_joined")


class MembershipSerializer(serializers.ModelSerializer):
    user = CollapsedUserSerializer()
    team = CollapsedCourseTeamSerializer()

    class Meta:
        model = CourseTeamMembership
        fields = ("user", "team", "date_joined")


class CourseTeamSerializer(serializers.ModelSerializer):
    id = serializers.CharField(source='team_id')
    membership = UserMembershipSerializer(many=True)

    class Meta:
        model = CourseTeam
        fields = ("id", "name", "is_active", "course_id", "topic_id", "date_created", "description", "country", "language", "membership")
        # read_only_fields = ("id", "email", "username")
