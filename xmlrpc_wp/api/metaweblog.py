import datetime
import os
import time

from xmlrpclib import Binary, Fault, DateTime

from django.contrib.sites.models import Site
from django.utils.encoding import smart_unicode
from django.utils.text import unescape_entities

from xmlrpc_wp.api import API, MediaHelpers


class Story(object):
    pass


class Image(object):
    pass


class Video(object):
    pass


def from_gmt(gmt_datetime):
    """Converts a naive GMT datetime into a naive local datetime."""
    return gmt_datetime - datetime.timedelta(seconds=time.timezone)


def to_gmt(local_datetime):
    """Converts a naive local datetime into a naive GMT datetime."""
    return local_datetime + datetime.timedelta(seconds=time.timezone)


def get_preview_url(obj):
    return None


class MetaWeblog(API, MediaHelpers):
    """
    Supports some of the API defined at
    http://mindsharestrategy.com/2010/wp-xmlrpc-metaweblog/

    """

    namespace = 'metaWeblog'

    @classmethod
    def _get_story_data(cls, story, site=None):

        url = story.get_absolute_url(site=site)
        preview_url = get_preview_url(story) or url

        # See http://codex.wordpress.org/Post_Status_Transitions
        if story.is_published:
            if story.pub_date > datetime.datetime.now():
                post_status = 'future'
            else:
                post_status = 'publish'
        else:
            post_status = 'draft'

        # unescaping as inlines are escaped.
        story_body = unescape_entities(story.raw_body)

        # Add media image items as HTML in the story body.
        # They'll get converted back when saving the story.
        images = list(story.images.all())
        videos = list(story.videos.all())
        story_body = cls._create_media_html(images, videos) + story_body

        return {
            'dateCreated': DateTime(story.pub_date),
            'userid': str(story.author.id),
            'postid': str(story.id),
            'description': story_body,
            'title': story.headline,
            'link': url,
            'permaLink': preview_url,
            'categories': [smart_unicode(cat) for cat in story.categories.all()],
            'mt_excerpt': story.get_short_summary(),
            'mt_text_more': '',
            'wp_more_text': '',
            'mt_allow_comments': int(story.comments.enabled),
            'mt_allow_pings': 0,
            'mt_keywords': ', '.join((smart_unicode(tag) for tag in story.tags)),
            'wp_slug': story.slug,
            'wp_password': '',
            'wp_author_id': str(story.author.id),
            'wp_author_display_name': story.author.username,
            'date_created_gmt': DateTime(to_gmt(story.pub_date)),
            'post_status': post_status,
            'custom_fields': [],
            'wp_post_format': 'standard',
            'date_modified': DateTime(story.updated_date or story.pub_date),
            'date_modified_gmt': DateTime(to_gmt(story.updated_date or story.pub_date)),
        }

    @classmethod
    def _save_story_data(cls, story, content, user, publish='publish'):

        if not isinstance(content, dict):
            raise Fault(400, 'The content value must be a struct')

        if content.get('post_type', 'post') != 'post':
            raise Fault(501, 'Not implemented. This only supports post_type=post')

        for field in ('title', 'description'):
            if not content.get(field):
                raise Fault(400, 'You did not supply a value for %s' % field)

        story.headline = content['title']
        story.slug = content.get('wp_slug', '')

        story.raw_teaser_short = content.get('mt_excerpt', '')
        story.raw_teaser_long = content.get('mt_text_more', '')

        if publish != 'publish':
            story.is_published = False
        elif content.get('post_status') != 'publish':
            story.is_published = False
        elif content.get('wp_password'):
            story.is_published = False
        else:
            story.is_published = True

        if content.get('dateCreated'):
            story.pub_date = content.get('dateCreated')
        elif content.get('date_created_gmt'):
            story.pub_date = from_gmt(content.get('date_created_gmt'))
        else:
            # On new stories, or existing stories set to "Publish Immediately,"
            # it won't send a date at all. Existing stories which don't change
            # the date will actually supply the old date as date_created_gmt.
            story.pub_date = datetime.datetime.now()

        # Strip the body of any media images, so we can attach them as
        # media items (after saving, because they are many-to-many).
        story_body, media_images, media_videos = cls._parse_media_html(content['description'])

        # TODO: add story_body to story

        # TODO: add user to story as author

        story.save()

        # Now add many-to-many data.

        # TODO: add media_images to story
        # TODO: add media_videos to story

        # TODO: add categories to story
        categories = content.get('categories')

        # TODO: add tags to story
        tags = content.get('mt_keywords', '')

        # TODO: enable comments on story
        allow_comments = bool(content.get('mt_allow_comments'))

        return story.id

    @classmethod
    def editPost(cls, post_id, username, password, content, publish='publish'):
        """
        Updates the specified existing post/story.

        :type post_id: int
        :type username: string
        :type password: string
        :type content: struct
        :type publish: string

        :returns: true
        :rtype: boolean

        """

        # Ensures the user is a staff member.
        user = cls._get_authenticated_user(username, password)

        # Ensures the user has permission to edit.
        story = cls._get_story(post_id, user=user)

        # Update the story.
        cls._save_story_data(story, content, user, publish=publish)

        return True

    @classmethod
    def getPost(cls, post_id, username, password, data=None):
        """
        Gets data for the specified post/story.

        :type post_id: int
        :type username: string
        :type password: string

        :returns: {story data}
        :rtype: struct

        """

        # Note: the WordPress app sends an extra struct argument.
        # I have added data=None to accept the useless parameter.

        # Ensures the user is a staff member.
        user = cls._get_authenticated_user(username, password)

        # Ensures the user has permission to edit.
        story = cls._get_story(post_id, user=user)

        data = cls._get_story_data(story)

        # Return the story data.
        return data

    @classmethod
    def getRecentPosts(cls, blog_id, username, password, limit=10):
        """
        Gets a list of recent posts for the specified blog/site.

        :type blog_id: int
        :type username: string
        :type password: string
        :type limit: int

        :returns: [{story data}, ...]
        :rtype: array

        """

        try:
            limit = int(limit)
        except (TypeError, ValueError):
            raise Fault(400, 'Invalid limit')

        # Ensures the user is a staff member.
        user = cls._get_authenticated_user(username, password)

        # Ensures the user is a staff member for this site.
        site = cls._get_allowed_site(blog_id, user)

        # Build a query to find editable stories for this user.
        editable_stories = Story.objects.filter(
            author=user,
            sites=site,
        )

        # Now get and return all of the data.
        posts = []
        for story in editable_stories[:limit].iterator():
            story_data = cls._get_story_data(story, site=site)
            posts.append(story_data)
        return posts

    @classmethod
    def newMediaObject(cls, blog_id, username, password, data):
        """
        Uploads a media file to the specified blog/site.

        The data value should be a struct containing:
            name: filename string
            type: mimetype string
            bits: base64 encoded contents

        :type blog_id: int
        :type username: string
        :type password: string
        :type data: struct

        :returns: {file, url, type}
        :rtype: struct

        """

        fields = (
            ('name', str),
            ('type', str),
            ('bits', Binary),
        )

        for field, data_type in fields:
            value = data.get(field)
            if not value:
                raise Fault(400, 'You did not supply a value for data.%s' % field)
            elif not isinstance(value, data_type):
                raise Fault(400, 'Invalid value type for for data.%s: %s' % (field, type(value)))

        mimetype = data['type']
        if mimetype not in cls.allowed_mime_types:
            raise Fault(415, 'Unsupported media type: %s' % mimetype)

        # Ensures the user is a staff member.
        user = cls._get_authenticated_user(username, password)

        # Ensures the user is a staff member for this site.
        site = cls._get_allowed_site(blog_id, user)

        try:
            media_data = data['bits'].data
        except TypeError, error:
            raise Fault(400, 'Could not process media data: %s' % error)

        media_instance = None

        if mimetype in cls.image_mime_types:

            media_instance = Image.create_from_data(media_data, data['name'], author=user)
            url = media_instance.url

        elif mimetype in cls.video_mime_types:
            media_instance = Video.create_from_data(media_data, data['name'], author=user)
            domain = Site.objects.get_current()
            url = "http://%s%s" % (domain, media_instance.get_absolute_url())

        if media_instance:
            if 'site' in media_instance._meta.get_all_field_names():
                media_instance.site = site
                media_instance.save()
            if 'sites' in media_instance._meta.get_all_field_names():
                media_instance.sites.add(site)

        return {
            'file': os.path.basename(url),
            'url': url,
            'type': mimetype,
        }

    @classmethod
    def newPost(cls, blog_id, username, password, content, publish='publish'):
        """
        Creates a new story/post on the specified blog/site.

        :type blog_id: int
        :type username: string
        :type password: string
        :type content: struct
        :type publish: string

        :returns: 'new story id'
        :rtype: string

        """

        # Ensures the user is a staff member.
        user = cls._get_authenticated_user(username, password)

        # Ensures the user is a staff member for this site.
        site = cls._get_allowed_site(blog_id, user)

        # Create a new story and update its details.
        story = Story()
        story.author = user

        # Set the source for the story.
        site_source = site.detail.primary_source
        user_sources = user.account.sources.all()
        if site_source in user_sources or not user_sources:
            story.source = site_source
        elif user_sources:
            story.source = user_sources[0]

        cls._save_story_data(story, content, user, publish=publish)
        story.sites = [site]

        return str(story.id)
