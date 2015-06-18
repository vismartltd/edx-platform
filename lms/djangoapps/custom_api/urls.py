"""
URLs for mobile API
"""
from django.conf.urls import patterns, url

from views import user_grades, all_grades

USERNAME_PATTERN = r'(?P<username>[\w.+-]+)'

urlpatterns = patterns(
    '',
    url(r'^all_grades$', all_grades),
    url(r'^user_grades/' + USERNAME_PATTERN + '$', user_grades),
)
