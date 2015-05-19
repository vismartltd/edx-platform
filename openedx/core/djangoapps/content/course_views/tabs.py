"""
Tabs for courseware.
"""
from abc import abstractmethod

from xmodule.tabs import CourseTab, key_checker, need_name
from openedx.core.lib.plugins.api import CourseViewType
from courseware.access import has_access
from student.models import CourseEnrollment
from ccx.overrides import get_current_ccx

_ = lambda text: text


def is_user_staff(course, user):
    """
    Returns true if the user is staff in the specified course, or globally.
    """
    return has_access(user, 'staff', course, course.id)


def is_user_enrolled_or_staff(course, user):
    """
    Returns true if the user is enrolled in the specified course,
    or if the user is staff.
    """
    return is_user_staff(course, user) or CourseEnrollment.is_enrolled(user, course.id)


class AuthenticatedCourseTab(CourseTab):
    """
    Abstract class for tabs that can be accessed by only authenticated users.
    """
    def is_enabled(self, course, settings, user=None):
        return not user or user.is_authenticated()


class EnrolledOrStaffTab(AuthenticatedCourseTab):
    """
    Abstract class for tabs that can be accessed by only users with staff access
    or users enrolled in the course.
    """
    def is_enabled(self, course, settings, user=None):  # pylint: disable=unused-argument
        if not user:
            return True
        return is_user_enrolled_or_staff(course, user)


class StaffTab(AuthenticatedCourseTab):
    """
    Abstract class for tabs that can be accessed by only users with staff access.
    """
    def is_enabled(self, course, settings, user=None):  # pylint: disable=unused-argument
        return not user or is_user_staff(course, user)


class HideableTab(CourseTab):
    """
    Abstract class for tabs that are hideable
    """
    is_hideable = True

    def __init__(self, name, tab_id, link_func, tab_dict):
        super(HideableTab, self).__init__(
            name=name,
            tab_id=tab_id,
            link_func=link_func,
        )
        self.is_hidden = tab_dict.get('is_hidden', False) if tab_dict else False

    def __getitem__(self, key):
        if key == 'is_hidden':
            return self.is_hidden
        else:
            return super(HideableTab, self).__getitem__(key)

    def __setitem__(self, key, value):
        if key == 'is_hidden':
            self.is_hidden = value
        else:
            super(HideableTab, self).__setitem__(key, value)

    def to_json(self):
        to_json_val = super(HideableTab, self).to_json()
        if self.is_hidden:
            to_json_val.update({'is_hidden': True})
        return to_json_val

    def __eq__(self, other):
        if not super(HideableTab, self).__eq__(other):
            return False
        return self.is_hidden == other.get('is_hidden', False)


class CoursewareTab(EnrolledOrStaffTab):
    """
    A tab containing the course content.
    """

    type = 'courseware'
    name = 'courseware'
    is_movable = False

    def __init__(self, tab_dict=None):  # pylint: disable=unused-argument
        super(CoursewareTab, self).__init__(
            # Translators: 'Courseware' refers to the tab in the courseware that leads to the content of a course
            name=_('Courseware'),  # support fixed name for the courseware tab
            tab_id=self.type,
            link_func=link_reverse_func(self.type),
        )


class CourseInfoTab(CourseTab):
    """
    A tab containing information about the course.
    """

    type = 'course_info'
    name = 'course_info'
    is_movable = False

    def __init__(self, tab_dict=None):
        super(CourseInfoTab, self).__init__(
            # Translators: "Course Info" is the name of the course's information and updates page
            name=tab_dict['name'] if tab_dict else _('Course Info'),
            tab_id='info',
            link_func=link_reverse_func('info'),
        )

    @classmethod
    def validate(cls, tab_dict, raise_error=True):
        return super(CourseInfoTab, cls).validate(tab_dict, raise_error) and need_name(tab_dict, raise_error)


class ProgressTab(EnrolledOrStaffTab):
    """
    A tab containing information about the authenticated user's progress.
    """

    type = 'progress'
    name = 'progress'

    def __init__(self, tab_dict=None):
        super(ProgressTab, self).__init__(
            # Translators: "Progress" is the name of the student's course progress page
            name=tab_dict['name'] if tab_dict else _('Progress'),
            tab_id=self.type,
            link_func=link_reverse_func(self.type),
        )

    def is_enabled(self, course, settings, user=None):
        super_can_display = super(ProgressTab, self).is_enabled(course, settings, user=user)
        return super_can_display and not course.hide_progress_tab

    @classmethod
    def validate(cls, tab_dict, raise_error=True):
        return super(ProgressTab, cls).validate(tab_dict, raise_error) and need_name(tab_dict, raise_error)


class WikiTab(HideableTab):
    """
    A tab_dict containing the course wiki.
    """

    type = 'wiki'
    name = 'wiki'

    def __init__(self, tab_dict=None):
        super(WikiTab, self).__init__(
            # Translators: "Wiki" is the name of the course's wiki page
            name=tab_dict['name'] if tab_dict else _('Wiki'),
            tab_id=self.type,
            link_func=link_reverse_func('course_wiki'),
            tab_dict=tab_dict,
        )

    def is_enabled(self, course, settings, user=None):
        if not settings.WIKI_ENABLED:
            return False
        if not user or course.allow_public_wiki_access:
            return True
        return is_user_enrolled_or_staff(course, user)

    @classmethod
    def validate(cls, tab_dict, raise_error=True):
        return super(WikiTab, cls).validate(tab_dict, raise_error) and need_name(tab_dict, raise_error)


class DiscussionTab(EnrolledOrStaffTab):
    """
    A tab only for the new Berkeley discussion forums.
    """

    type = 'discussion'
    name = 'discussion'

    def __init__(self, tab_dict=None):
        super(DiscussionTab, self).__init__(
            # Translators: "Discussion" is the title of the course forum page
            name=tab_dict['name'] if tab_dict else _('Discussion'),
            tab_id=self.type,
            link_func=link_reverse_func('django_comment_client.forum.views.forum_form_discussion'),
        )

    def is_enabled(self, course, settings, user=None):
        if settings.FEATURES.get('CUSTOM_COURSES_EDX', False):
            if get_current_ccx():
                return False
        super_can_display = super(DiscussionTab, self).is_enabled(course, settings, user=user)
        return settings.FEATURES.get('ENABLE_DISCUSSION_SERVICE') and super_can_display

    @classmethod
    def validate(cls, tab_dict, raise_error=True):
        return super(DiscussionTab, cls).validate(tab_dict, raise_error) and need_name(tab_dict, raise_error)


class LinkTab(CourseTab):
    """
    Abstract class for tabs that contain external links.
    """
    link_value = ''

    def __init__(self, name, tab_id, link_value):
        self.link_value = link_value
        super(LinkTab, self).__init__(
            name=name,
            tab_id=tab_id,
            link_func=link_value_func(self.link_value),
        )

    def __getitem__(self, key):
        if key == 'link':
            return self.link_value
        else:
            return super(LinkTab, self).__getitem__(key)

    def __setitem__(self, key, value):
        if key == 'link':
            self.link_value = value
        else:
            super(LinkTab, self).__setitem__(key, value)

    def to_json(self):
        to_json_val = super(LinkTab, self).to_json()
        to_json_val.update({'link': self.link_value})
        return to_json_val

    def __eq__(self, other):
        if not super(LinkTab, self).__eq__(other):
            return False
        return self.link_value == other.get('link')

    @classmethod
    def validate(cls, tab_dict, raise_error=True):
        return super(LinkTab, cls).validate(tab_dict, raise_error) and key_checker(['link'])(tab_dict, raise_error)


class ExternalDiscussionTab(LinkTab):
    """
    A tab that links to an external discussion service.
    """

    type = 'external_discussion'
    name = 'external_discussion'

    def __init__(self, tab_dict=None, link_value=None):
        super(ExternalDiscussionTab, self).__init__(
            # Translators: 'Discussion' refers to the tab in the courseware that leads to the discussion forums
            name=_('Discussion'),
            tab_id='discussion',
            link_value=tab_dict['link'] if tab_dict else link_value,
        )


class ExternalLinkTab(LinkTab):
    """
    A tab containing an external link.
    """
    type = 'external_link'
    name = 'external_link'

    def __init__(self, tab_dict):
        super(ExternalLinkTab, self).__init__(
            name=tab_dict['name'],
            tab_id=None,  # External links are never active.
            link_value=tab_dict['link'],
        )


class StaticTab(CourseTab):
    """
    A custom tab.
    """
    type = 'static_tab'
    name = 'static_tab'

    @classmethod
    def validate(cls, tab_dict, raise_error=True):
        return super(StaticTab, cls).validate(tab_dict, raise_error) and key_checker(['name', 'url_slug'])(tab_dict, raise_error)

    def __init__(self, tab_dict=None, name=None, url_slug=None):
        self.url_slug = tab_dict['url_slug'] if tab_dict else url_slug
        super(StaticTab, self).__init__(
            name=tab_dict['name'] if tab_dict else name,
            tab_id='static_tab_{0}'.format(self.url_slug),
            link_func=lambda course, reverse_func: reverse_func(self.type, args=[course.id.to_deprecated_string(), self.url_slug]),
        )

    def __getitem__(self, key):
        if key == 'url_slug':
            return self.url_slug
        else:
            return super(StaticTab, self).__getitem__(key)

    def __setitem__(self, key, value):
        if key == 'url_slug':
            self.url_slug = value
        else:
            super(StaticTab, self).__setitem__(key, value)

    def to_json(self):
        to_json_val = super(StaticTab, self).to_json()
        to_json_val.update({'url_slug': self.url_slug})
        return to_json_val

    def __eq__(self, other):
        if not super(StaticTab, self).__eq__(other):
            return False
        return self.url_slug == other.get('url_slug')


class SingleTextbookTab(CourseTab):
    """
    A tab representing a single textbook.  It is created temporarily when enumerating all textbooks within a
    Textbook collection tab.  It should not be serialized or persisted.
    """
    type = 'single_textbook'
    name = 'single_textbook'
    is_movable = False
    is_collection_item = True

    def to_json(self):
        raise NotImplementedError('SingleTextbookTab should not be serialized.')


class TextbookTabsBase(AuthenticatedCourseTab):
    """
    Abstract class for textbook collection tabs classes.
    """
    is_collection = True

    def __init__(self, tab_id):
        # Translators: 'Textbooks' refers to the tab in the course that leads to the course' textbooks
        super(TextbookTabsBase, self).__init__(
            name=_("Textbooks"),
            tab_id=tab_id,
            link_func=None,
        )

    @abstractmethod
    def items(self, course):
        """
        A generator for iterating through all the SingleTextbookTab book objects associated with this
        collection of textbooks.
        """
        pass


class TextbookTabs(TextbookTabsBase):
    """
    A tab representing the collection of all textbook tabs.
    """
    type = 'textbooks'
    name = 'textbooks'

    def __init__(self, tab_dict=None):  # pylint: disable=unused-argument
        super(TextbookTabs, self).__init__(
            tab_id=self.type,
        )

    def is_enabled(self, course, settings, user=None):
        return settings.FEATURES.get('ENABLE_TEXTBOOK')

    def items(self, course):
        for index, textbook in enumerate(course.textbooks):
            yield SingleTextbookTab(
                name=textbook.title,
                tab_id='textbook/{0}'.format(index),
                link_func=lambda course, reverse_func, index=index: reverse_func(
                    'book', args=[course.id.to_deprecated_string(), index]
                ),
            )


class PDFTextbookTabs(TextbookTabsBase):
    """
    A tab representing the collection of all PDF textbook tabs.
    """
    type = 'pdf_textbooks'
    name = 'pdf_textbooks'

    def __init__(self, tab_dict=None):  # pylint: disable=unused-argument
        super(PDFTextbookTabs, self).__init__(
            tab_id=self.type,
        )

    def items(self, course):
        for index, textbook in enumerate(course.pdf_textbooks):
            yield SingleTextbookTab(
                name=textbook['tab_title'],
                tab_id='pdftextbook/{0}'.format(index),
                link_func=lambda course, reverse_func, index=index: reverse_func(
                    'pdf_book', args=[course.id.to_deprecated_string(), index]
                ),
            )


class HtmlTextbookTabs(TextbookTabsBase):
    """
    A tab representing the collection of all Html textbook tabs.
    """
    type = 'html_textbooks'
    name = 'html_textbooks'

    def __init__(self, tab_dict=None):  # pylint: disable=unused-argument
        super(HtmlTextbookTabs, self).__init__(
            tab_id=self.type,
        )

    def items(self, course):
        for index, textbook in enumerate(course.html_textbooks):
            yield SingleTextbookTab(
                name=textbook['tab_title'],
                tab_id='htmltextbook/{0}'.format(index),
                link_func=lambda course, reverse_func, index=index: reverse_func(
                    'html_book', args=[course.id.to_deprecated_string(), index]
                ),
            )


class GradingTab(object):
    """
    Abstract class for tabs that involve Grading.
    """
    pass


class StaffGradingTab(StaffTab, GradingTab):
    """
    A tab for staff grading.
    """
    type = 'staff_grading'
    name = 'staff_grading'

    def __init__(self, tab_dict=None):  # pylint: disable=unused-argument
        super(StaffGradingTab, self).__init__(
            # Translators: "Staff grading" appears on a tab that allows
            # staff to view open-ended problems that require staff grading
            name=_("Staff grading"),
            tab_id=self.type,
            link_func=link_reverse_func(self.type),
        )


class PeerGradingTab(AuthenticatedCourseTab, GradingTab):
    """
    A tab for peer grading.
    """
    type = 'peer_grading'
    name = 'peer_grading'

    def __init__(self, tab_dict=None):  # pylint: disable=unused-argument
        super(PeerGradingTab, self).__init__(
            # Translators: "Peer grading" appears on a tab that allows
            # students to view open-ended problems that require grading
            name=_("Peer grading"),
            tab_id=self.type,
            link_func=link_reverse_func(self.type),
        )


class OpenEndedGradingTab(AuthenticatedCourseTab, GradingTab):
    """
    A tab for open ended grading.
    """
    type = 'open_ended'
    name = 'open_ended'

    def __init__(self, tab_dict=None):  # pylint: disable=unused-argument
        super(OpenEndedGradingTab, self).__init__(
            # Translators: "Open Ended Panel" appears on a tab that, when clicked, opens up a panel that
            # displays information about open-ended problems that a user has submitted or needs to grade
            name=_("Open Ended Panel"),
            tab_id=self.type,
            link_func=link_reverse_func('open_ended_notifications'),
        )


class SyllabusTab(CourseTab):
    """
    A tab for the course syllabus.
    """
    type = 'syllabus'
    name = 'syllabus'

    def is_enabled(self, course, settings, user=None):
        return hasattr(course, 'syllabus_present') and course.syllabus_present

    def __init__(self, tab_dict=None):  # pylint: disable=unused-argument
        super(SyllabusTab, self).__init__(
            # Translators: "Syllabus" appears on a tab that, when clicked, opens the syllabus of the course.
            name=_('Syllabus'),
            tab_id=self.type,
            link_func=link_reverse_func(self.type),
        )


class NotesTab(AuthenticatedCourseTab):
    """
    A tab for the course notes.
    """
    type = 'notes'
    name = 'notes'

    def is_enabled(self, course, settings, user=None):
        return settings.FEATURES.get('ENABLE_STUDENT_NOTES')

    def __init__(self, tab_dict=None):
        super(NotesTab, self).__init__(
            name=tab_dict['name'],
            tab_id=self.type,
            link_func=link_reverse_func(self.type),
        )

    @classmethod
    def validate(cls, tab_dict, raise_error=True):
        return super(NotesTab, cls).validate(tab_dict, raise_error) and need_name(tab_dict, raise_error)


class CourseViewTab(AuthenticatedCourseTab):
    """
    A tab that renders a course view.
    """

    def __init__(self, course_view_type, tab_dict=None):
        super(CourseViewTab, self).__init__(
            name=tab_dict['name'] if tab_dict else course_view_type.title,
            tab_id=course_view_type.name,
            link_func=link_reverse_func(course_view_type.view_name),
        )
        self.type = course_view_type.name
        self.course_view_type = course_view_type

    def is_enabled(self, course, settings, user=None):
        if not super(CourseViewTab, self).is_enabled(course, settings, user=user):
            return False
        return self.course_view_type.is_enabled(course, settings, user=user)


# Link Functions
def link_reverse_func(reverse_name):
    """
    Returns a function that takes in a course and reverse_url_func,
    and calls the reverse_url_func with the given reverse_name and course' ID.
    """
    return lambda course, reverse_url_func: reverse_url_func(reverse_name, args=[course.id.to_deprecated_string()])


def link_value_func(value):
    """
    Returns a function takes in a course and reverse_url_func, and returns the given value.
    """
    return lambda course, reverse_url_func: value
