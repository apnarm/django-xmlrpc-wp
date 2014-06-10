from xmlrpclib import Fault

from django.core.urlresolvers import reverse
from django.utils.encoding import smart_unicode

from xmlrpc_wp.api import API


class Category(object):
    pass


class WordPress(API):
    """
    Supports some of the API defined at http://codex.wordpress.org/XML-RPC_wp
    Note: This API is current as of the 3.1 release.

    """

    namespace = 'wp'

    @classmethod
    def getCategories(cls, blog_id, username, password):
        """
        Gets a list of available categories for this user on this blog/site.

        :type blog_id: int
        :type username: string
        :type password: string

        :returns: [{category data}, ...]
        :rtype: array

        """

        # Ensures the user is a staff member.
        user = cls._get_authenticated_user(username, password)

        # Ensures the user is a staff member for this site.
        site = cls._get_allowed_site(blog_id, user)

        # Get categories for this user and for this site.
        result = []
        for category in Category.objects.filter(sites=site):
            result.append({
                'categoryId': category.id,
                'parentId': category.parent and category.parent.id or 0,
                'description': smart_unicode(category),
                'categoryDescription': category.description,
                'categoryName': smart_unicode(category),
                'htmlUrl': '',  # TODO: what is this?
                'rssUrl': '',  # TODO: what is this?
            })
        return result

    @classmethod
    def getComments(cls, *args):
        """Returns a user-friendly error message."""
        raise Fault(501, 'Sorry, comments are not supported at this time.')

    #@classmethod
    #def getComments(cls, blog_id, username, password, struct):
    #    """
    #    Gets a list of comments for the specified post using a filter.
    #    The blog/site value is ignored due to the APN comment model.
    #
    #    """
    #
    #    """
    #    :type blog_id: int
    #    :type username: string
    #    :type password: string
    #    :type struct: struct
    #
    #    :returns: [{comment data}, ...]
    #    :rtype: array
    #
    #    """
    #

    @classmethod
    def getPages(cls, *args):
        """Returns a user-friendly error message."""
        raise Fault(501, 'Sorry, pages are not supported at this time.')

    #@classmethod
    #def getPages(cls, blog_id, username, password, max_pages=10):
    #    """
    #    Gets a list of editable flatpages on the specified blog/site
    #    for the current user.
    #
    #    :type blog_id: int
    #    :type username: string
    #    :type password: string
    #    :type max_pages: int
    #
    #    :returns: [{page data}, ...]
    #    :rtype: array
    #
    #    """
    #

    @classmethod
    def getUsersBlogs(cls, username, password):
        """
        Gets a list of sites/blogs for the current user.

        :type username: string
        :type password: string

        :returns: [{site data}, ...]
        :rtype: array

        """

        user = cls._get_authenticated_user(username, password)
        blogs = []
        for site in cls._get_allowed_sites(user):
            domain = site.domain
            url = 'http://%s/' % domain
            xmlrpc_url = 'http://%s%s' % (domain, reverse('xmlrpc'))
            blogs.append({
                'isAdmin': user.is_staff,
                'url': url,
                'blogid': str(site.id),
                'blogName': site.name,
                'xmlrpc': xmlrpc_url,
            })
        return blogs
