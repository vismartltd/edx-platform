"""
Setup script for the Open edX package.
"""

from setuptools import setup

setup(
    name="Open edX",
    version="0.3",
    install_requires=["distribute"],
    requires=[],
    # NOTE: These are not the names we should be installing.  This tree should
    # be reorganized to be a more conventional Python tree.
    packages=[
        "openedx.core.djangoapps.course_groups",
        "openedx.core.djangoapps.user_api",
        "lms",
        "cms",
    ],
    entry_points={
        "openedx.course_view_type": [
            "ccx = lms.djangoapps.ccx.plugins:CcxCourseViewType",
            "edxnotes = lms.djangoapps.edxnotes.plugins:EdxNotesCourseViewType",
            "instructor = lms.djangoapps.instructor.views.instructor_dashboard:InstructorDashboardViewType",
            "courseware = openedx.core.djangoapps.course_views.tabs:CoursewareTab",
            "course_info = openedx.core.djangoapps.course_views.tabs:CourseInfoTab",
            'wiki = openedx.core.djangoapps.course_views.tabs:WikiTab',
            'discussion = openedx.core.djangoapps.course_views.tabs:DiscussionTab',
            'external_discussion = openedx.core.djangoapps.course_views.tabs:ExternalDiscussionTab',
            'external_link = openedx.core.djangoapps.course_views.tabs:ExternalLinkTab',
            'textbooks = openedx.core.djangoapps.course_views.tabs:TextbookTabs',
            'pdf_textbooks = openedx.core.djangoapps.course_views.tabs:PDFTextbookTabs',
            'html_textbooks = openedx.core.djangoapps.course_views.tabs:HtmlTextbookTabs',
            'progress = openedx.core.djangoapps.course_views.tabs:ProgressTab',
            'static_tab = openedx.core.djangoapps.course_views.tabs:StaticTab',
            'peer_grading = openedx.core.djangoapps.course_views.tabs:PeerGradingTab',
            'staff_grading = openedx.core.djangoapps.course_views.tabs:StaffGradingTab',
            'open_ended = openedx.core.djangoapps.course_views.tabs:OpenEndedGradingTab',
            'notes = openedx.core.djangoapps.course_views.tabs:NotesTab',
            'syllabus = openedx.core.djangoapps.course_views.tabs:SyllabusTab',
        ],
        "openedx.user_partition_scheme": [
            "random = openedx.core.djangoapps.user_api.partition_schemes:RandomUserPartitionScheme",
            "cohort = openedx.core.djangoapps.course_groups.partition_scheme:CohortPartitionScheme",
        ],
    }
)
