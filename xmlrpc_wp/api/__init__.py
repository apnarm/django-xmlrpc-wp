"""
TODO: make this generic and not specific to APN's models and inlines.
        have some way to use subclasss, or register behaviour.

"""

import os
import re

from SimpleXMLRPCServer import list_public_methods
from urlparse import urlparse
from xmlrpclib import Fault

from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.utils.html import escape


class Story(object):
    pass


class Image(object):
    pass


class Video(object):
    pass


class MediaHelpers(object):

    image_mime_types = ('image/jpeg', 'image/png', 'image/gif')
    video_mime_types = ('video/mp4', 'video/3gpp', 'video/quicktime')

    allowed_mime_types = image_mime_types + video_mime_types

    embedded_image_format = '<a href="%(url)s"><img src="%(url)s" alt="%(alt)s" class="alignnone size-full" /></a><br /><br />'
    embedded_image_re = re.compile(r'(?:\s*<br\s*/>\s*<br\s*/>\s*)*<a href="([^"]+)">\s*<img[^>]+src="\1"[^>]+>\s*</a>')

    embedded_video_format = '<video src="%(url)s" controls="controls" width="640" height="360">Your browser does not support the video tag</video><br /><br />'
    embedded_video_re = re.compile(r'(?:\s*<br\s*/>\s*)*<video\s*src="([^"]+)"\s*[^<]*</video>')

    inline_video_format = '<inline type="video" id="%(pk)s" align=\"normal/\"><br />'

    @classmethod
    def _create_media_html(cls, images, videos):
        """
        Creates the image/media HTML for the given image and video instances.

        """

        media_html = ''

        for image in images:
            image_url = image.url
            media_html += cls.embedded_image_format % {
                'url': image_url,
                'alt': os.path.basename(image_url),
            }

        for video in videos:
            domain = Site.objects.get_current().domain
            video_url = "http://%s%s" % (domain, video.get_absolute_url())
            media_html += cls.embedded_video_format % {
                'url': video_url
            }

        return media_html

    @classmethod
    def extract_image(cls, image_match):

        image_url = image_match.group(1)
        image_path = re.sub('^%s' % re.escape(settings.MEDIA_URL), '', image_url)

        try:
            # Try to find a matching image object that we can use.
            # If found, it will be added as a media image item later on.
            return Image.objects.get(path=image_path)
        except Image.DoesNotExist:
            return None

    @classmethod
    def extract_video(cls, video_match):
        video_url = video_match.group(1)
        video_url = urlparse(video_url)
        video_pk = os.path.split(video_url.path.rstrip('/'))[1]

        try:
            # Try to find a matching video object that we can use.
            # If found, it will be added as a media image item later on.
            return Video.objects.get(pk=video_pk)
        except Video.DoesNotExist:
            return None

    @classmethod
    def _parse_media_html(cls, content):
        """
        If there is any image HTML at the top of the content, then try to find
        matching Image instances, and remove the associated HTML.

        Returns the stripped content, and list of media image instances.

        """

        media_images = []
        media_videos = []

        unknown_media = []

        while True:
            # this True is because we only do a match at the start of the document until we find nothing more.

            image_match = cls.embedded_image_re.match(content)
            video_match = cls.embedded_video_re.match(content)

            if not (image_match or video_match):
                break

            match = None

            if image_match:

                match = image_match
                image = cls.extract_image(match)

                if image:
                    media_images.append(image)
                else:
                    # Some other image. Remember the HTML so it
                    # can be added back to the body afterwards.
                    unknown_media.append(match.group(0))

            elif video_match:

                match = video_match
                video = cls.extract_video(video_match)

                if video:
                    media_videos.append(video)
                else:
                    # Some other video. Remember the HTML so it
                    # can be added back to the body afterwards.
                    unknown_media.append(match.group(0))

            # Remove this piece of HTML from the content.
            content = content.replace(match.group(0), '', 1)

        # Extract inline videos after the head.
        def replace_with_video_inline(video_match):
            video = cls.extract_video(video_match)
            if video:
                text = cls.inline_video_format % {'pk': video.pk}
                return escape(text)
            return ''

        content = re.sub(cls.embedded_video_re, replace_with_video_inline, content)

        # Restore the HTML of unknown media.
        content = ''.join(unknown_media) + content

        return content, media_images, media_videos


class SiteHelpers(object):

    @classmethod
    def _get_enabled_sites(cls):
        """
        Gets sites with XML RPC enabled. Defaults to all sites.
        Returns a Site queryset.

        """

        return Site.objects.all()

    @classmethod
    def _get_enabled_site_ids(cls):
        """
        Gets sites with XML RPC enabled. Defaults to all sites.
        Returns a list of Site IDs.

        """

        return cls._get_enabled_sites(ids=False).values_list('id', flat=True)

    @classmethod
    def _get_allowed_site(cls, site_id, user):
        """
        Gets the site object, with permission checks for the given user.

        """

        try:
            site_id = int(site_id)
        except (TypeError, ValueError):
            raise Fault(400, 'Invalid blog_id/site_id')

        if site_id not in cls._get_enabled_sites_ids():
            raise Fault(404, 'Unknown blog_id/site_id')

        try:
            return cls._get_allowed_sites(user).get(id=site_id)
        except Site.DoesNotExist:
            raise Fault(403, 'Not permitted to access this blog_id/site_id')

    @classmethod
    def _get_allowed_sites(cls, user):
        """
        Gets the available sites for the given user. Defaults to all
        enabled sites for staff users, or no sites for ordinary users.

        """

        if user.is_staff:
            return cls._get_enabled_sites()
        else:
            return Site.objects.none()


class StoryHelpers(object):

    @staticmethod
    def _get_story(story_id, user=None):
        """
        Gets a Story with the given ID.
        Performs permission checks for the user if provided.

        """

        try:
            story_id = int(story_id)
        except (TypeError, ValueError):
            raise Fault(400, 'Invalid post_id/story_id')

        try:
            story = Story.objects.get(id=story_id)
        except Story.DoesNotExist:
            raise Fault(404, 'Unknown post_id/story_id')

        if user and story.source:
            if not user.has_edit_permissions_to_source(story.source.pk):
                raise Fault(403, 'Not permitted to access this story')

        return story


class UserHelpers(object):

    @staticmethod
    def _get_authenticated_user(username, password):
        """
        Gets the user for the given username and password.

        The user lookup is filtered by the keyword arguments. By default, it
        filters on is_active=True and is_staff=True

        Raises a Fault if the user was not found or the password was incorrect.

        """

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            user = False

        if not user or not user.check_password(password):
            raise Fault(403, 'Incorrect login details.')

        if not user.is_active:
            raise Fault(403, 'Your account has been deactivated.')

        if not user.is_staff or not user.has_perm('xmlrpc.use_xmlrpc'):
            raise Fault(403, 'Your account is not allowed to access this service.')

        return user


class API(SiteHelpers, StoryHelpers, UserHelpers):

    namespace = None

    @classmethod
    def register_with(cls, dispatcher):
        """Adds this API's methods to the given dispatcher."""
        for method_name in list_public_methods(cls):
            if method_name != 'register_with':
                method = getattr(cls, method_name)
                full_name = '.'.join((part for part in (cls.namespace, method_name) if part))
                dispatcher.register_function(method, full_name)
