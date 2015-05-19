from django.contrib.auth.models import User
from rest_framework import serializers
from .models import CourseTeam



class CourseTeamSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.SerializerMethodField("get_id")
    course_id = serializers.SerializerMethodField("get_course_id")
    membership = serializers.SerializerMethodField("get_membership")

    def get_id(self, obj):
        return obj.course_user_group.name

    def get_course_id(self, obj):
        return obj.course_user_group.course_id

    def get_membership(self, obj):
        return obj.course_user_group.users

    class Meta:
        model = CourseTeam
        # This list is the minimal set required by the notification service
        fields = ("id", "name", "is_active", "course_id", "topic_id", "date_created", "description", "country", "language", "membership")
        # read_only_fields = ("id", "email", "username")
