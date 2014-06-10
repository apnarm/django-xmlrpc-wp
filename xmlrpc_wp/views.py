from django.contrib.auth import authenticate, login
from django.contrib.sites.models import Site
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseServerError
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.utils.datastructures import SortedDict
from django.utils.html import strip_spaces_between_tags

from xmlrpc_wp.dispatcher import dispatcher
from xmlrpc_wp.utils import get_method_info


NAMESPACE_TITLES = {
    'metaWeblog': 'MetaWeblog',
    'system': 'System',
    'wp': 'WordPress',
    'wpcom': 'WordPressCom',
}


def xmlrpc(request):

    if request.POST:

        redirect = request.POST.get('redirect_to')
        if redirect:
            return HttpResponseRedirect(redirect)

        output = dispatcher.run(request.raw_post_data)

        host = request.get_host()
        domain = Site.objects.get_current().domain
        if host != domain:
            for protocol in ('http', 'https'):
                output = output.replace(
                    '%s://%s/' % (protocol, domain),
                    '%s://%s/' % (protocol, host),
                )

        response = HttpResponse(mimetype='application/xml')
        response.write(strip_spaces_between_tags(output))
        return response

    methods = {}
    for method_name in dispatcher.system_listMethods():
        namespace = method_name.split('.')[0]
        methods.setdefault(namespace, SortedDict())
        methods[namespace][method_name] = get_method_info(dispatcher.funcs[method_name])

    method_lists = []
    for namespace in sorted(methods.keys()):
        method_lists.append((
            namespace,
            NAMESPACE_TITLES.get(namespace, namespace),
            methods[namespace].items(),
        ))

    return render_to_response(
        template_name='xmlrpc/xmlrpc.html',
        dictionary={
            'method_lists': method_lists,
        },
        context_instance=RequestContext(request),
    )


def rsd(request):
    return render_to_response(
        template_name='xmlrpc/rsd.html',
        context_instance=RequestContext(request),
        mimetype='text/xml',
    )


def wp_login(request):
    """Partial implementation of wp-login.php from WordPress."""

    if request.POST:

        username = request.POST.get('log')
        password = request.POST.get('pwd')

        if username and password:
            user = authenticate(username=username, password=password)
            if user:
                login(request, user)

        redirect = request.POST.get('redirect_to')
        if redirect:
            return HttpResponseRedirect(redirect)

    return HttpResponseServerError('Unsupported URL.', status=501)
