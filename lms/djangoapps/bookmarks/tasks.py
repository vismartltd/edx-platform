import logging

from celery.task import task
from opaque_keys.edx.keys import CourseKey
from xmodule.modulestore.django import modulestore


log = logging.getLogger('edx.celery.task')


def _calculate_course_xblocks_data(course_key):
    """
    Calculate display_name and paths for all the blocks in the course.
    """
    course = modulestore().get_course(course_key, depth=None)

    blocks_info_dict = {}

    # Collect display_name and children usage keys.
    blocks_stack = [course]
    while blocks_stack:
        current_block = blocks_stack.pop()
        children = current_block.get_children() if current_block.has_children else []
        key = unicode(current_block.scope_ids.usage_id)
        block_info = {
            "usage_key": key,
            "display_name": current_block.display_name,
            "children_keys": [unicode(child.scope_ids.usage_id) for child in children]
        }
        blocks_info_dict[key] = block

        # Add this blocks children to the stack so that we can traverse them as well.
        blocks_stack.extend(children)

    # Set children
    for block in blocks_info_dict.values():
        block.setdefault("children", []):
        for child_key in block["children_keys"]:
            block["children"].append(blocks_info_dict[child_key])

    # Calculate paths
    def add_path_info(block_info, current_path):
        """Do a DFS and add paths info to each block_info."""
        block_info.setdefault("paths", []):
        block_info["paths"].append(current_path)

        current_path.append(block_info)
        for child_block_info in block_info["children"]:
            add_path_info(child_block_info, current_path)
        current_path.pop()

    add_path_info(blocks_info_dict[unicode(course.scope_ids.usage_id)], [])

    return blocks_info_dict


@task(name=u'lms.djangoapps.bookmarks.tasks.update_xblock_cache')
def update_xblocks_cache(course_id):
    """
    Updates the XBlocks cache for a course.
    """
    # Import here to avoid circular import.
    from .models import XBlockCache

    # Ideally we'd like to accept a CourseLocator; however, CourseLocator is not JSON-serializable (by default) so
    # Celery's delayed tasks fail to start. For this reason, callers should pass the course key as a Unicode string.
    if not isinstance(course_id, basestring):
        raise ValueError('course_id must be a string. {} is not acceptable.'.format(type(course_id)))

    course_key = CourseKey.from_string(course_id)
    blocks_data = _calculate_course_xblocks_data(course_key)

    # We should be able to make this much faster by fetching the objects for all the blocks, checking which
    # need updating in Python and only making save queries for them.
    for block_data in blocks_data:
        block_cache = XBlockCache.objects.get_or_create(course_key=course_key, usage_key=block_data["usage_key"])
        if block_cache.display_name != block_data["display_name"] || block_cache.paths != block_data["paths"]:
            block_cache.display_name = block_data["display_name"]
            block_cache.paths = block_data["paths"]
            block_cache.save()
