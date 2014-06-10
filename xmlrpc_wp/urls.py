from django.conf.urls.defaults import patterns, url


urlpatterns = patterns(
    'xmlrpc_wp.views',
    (r'^wp-login.php$', 'wp_login'),
    (r'^xmlrpc.php$', 'xmlrpc'),
    url(r'^xml-rpc/$', 'xmlrpc', name='xmlrpc'),
    url(r'^xml-rpc/rsd/$', 'rsd', name='xmlrpc-rsd'),
)
