import datetime
import os.path

from xmlrpclib import Binary, Fault

from django.contrib.auth.models import User, Group, Permission
from django.contrib.sites.models import Site
from django.test import TestCase

from xmlrpc_wp.api.metaweblog import MetaWeblog
from xmlrpc_wp.api.wp import WordPress
from xmlrpc_wp.utils import get_arguments


class XmlRpcTest(TestCase):

    def setUp(self):

        self.group = Group.objects.create(name='WordPress Publishers')

        Permission.objects.filter(codename='use_xmlrpc_wp').delete()
        self.permission = Permission.objects.create(
            codename='use_xmlrpc_wp',
            content_type__app_label='xmlrpc_wp',
            content_type__name='xmlrpc_wp',
        )

        self.site = Site.objects.all()[0]

        self.username = 'test'
        self.user_password = 'test123'
        User.objects.filter(username=self.username).delete()
        self.user = User.objects.create_user('test', email='test@test.com', password=self.user_password)
        self.user.is_staff = True
        self.user.save()
        self.user.groups.add(self.group)
        self.user.user_permissions.add(self.permission)

        # These are some standard arguments that we will use by default.
        # This avoids defining/passing them in multiple times.
        self.arguments = {
            'username': self.username,
            'password': self.user_password,
            'blog_id': self.site.id,
            'publish': 'publish',
            'limit': 1,
        }

    def check_authentication(self, method, **overrides):
        overrides['password'] = self.user_password + 'ohohoho'
        try:
            self.get_result(method, **overrides)
        except Fault:
            pass
        else:
            self.fail('%s did not raise an error when the password was wrong.' % method)

    def check_result(self, method, expected_result, **overrides):
        result = self.get_result(method, **overrides)
        self.assertEqual(result, expected_result)

    def check_result_type(self, method, result_type, **overrides):
        result = self.get_result(method, **overrides)
        self.assertTrue(result)
        self.assertTrue(isinstance(result, result_type))

    def get_result(self, method, **overrides):
        args, kwargs = get_arguments(method)
        arg_values = []
        for name in args:
            if name in overrides:
                arg_values.append(overrides[name])
            elif name in self.arguments:
                arg_values.append(self.arguments[name])
            else:
                self.fail('Missing argument "%s" for %s' % (name, method.__name__))
        for key in kwargs:
            if key in overrides:
                kwargs[key] = overrides[key]
            elif key in self.arguments:
                kwargs[key] = self.arguments[key]
        return method(*arg_values, **kwargs)


class MetaWeblogTests(XmlRpcTest):

    def test_newPost_editPost_getPost_getRecentPosts(self):

        # Create a NewsEntry using newPost.
        post_title = 'test_newPost_editPost_getPost_getRecentPosts'
        overrides = {
            'content': {
                'post_type': 'post',
                'title': post_title,
                'description': 'body text',
                'post_status': 'publish',
                # Hopefully, there will be no other stories set so far in the future.
                'dateCreated': datetime.datetime.now() + datetime.timedelta(days=99999),
            }
        }
        result = self.get_result(MetaWeblog.newPost, **overrides)

        # It should have returned the newly created id.
        story_id = int(result)

        # Edit it using editPost.
        overrides.update({
            'post_id': story_id,
        })
        self.check_result(MetaWeblog.editPost, True, **overrides)

        # Now fetch that NewsEntry using getPost.
        overrides = {'post_id': story_id}
        self.check_result_type(MetaWeblog.getPost, dict, **overrides)

        # Now get recent posts and check that it came back.
        result = self.get_result(MetaWeblog.getRecentPosts)
        self.assertTrue(isinstance(result, list))
        self.assertEqual(len(result), 1)  # self.arguments limit is 1
        self.assertEqual(result[0]['title'], post_title)

    def test_newMediaObject(self):
        # Create a new Image using the RPC method.
        path = os.path.join(
            os.path.dirname(__file__),
            'static',
            'xmlrpc_wp',
            'TODO.gif'
        )
        bits = Binary(open(path).read())
        overrides = {
            'data': {
                'name': path,
                'type': 'image/gif',
                'bits': bits,
            }
        }
        result = self.get_result(MetaWeblog.newMediaObject, **overrides)
        self.assertTrue(result)


class WordPressTest(XmlRpcTest):

    def test_getCategories(self):
        self.check_authentication(WordPress.getCategories)
        self.check_result_type(WordPress.getCategories, list)

    def test_getUsersBlogs(self):
        self.check_authentication(WordPress.getUsersBlogs)
        self.check_result_type(WordPress.getUsersBlogs, list)
