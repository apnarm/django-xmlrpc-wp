import inspect
import pydoc
import re

from django.utils.datastructures import SortedDict


def get_arguments(method):

    args, varargs, keywords, defaults = inspect.getargspec(method)
    if args[0] in ('self', 'cls'):
        args = args[1:]
    else:
        args = list(args)

    kwargs = {}
    defaults = list(defaults or [])
    while defaults:
        kwargs[args.pop()] = defaults.pop(0)

    return tuple(args), kwargs


def get_method_info(method):

    info = {}

    help_text = pydoc.getdoc(method)

    args = SortedDict()
    desc_re = re.compile(':(?P<desc>param|parameter|arg|argument|key|keyword)\s+(?P<name>.+):\s+(?P<value>.+)')
    type_re = re.compile(':(?P<type>type)\s+(?P<name>.+):\s+(?P<value>.+)')
    for expression in (desc_re, type_re):
        for match in expression.finditer(help_text):
            data = match.groupdict()
            if 'desc' in data:
                key = 'desc'
            else:
                key = 'type'
            name = data['name']
            value = data['value']
            args.setdefault(name, {})
            args[name][key] = value
        help_text = expression.sub('', help_text)
    if args:
        info['args'] = args

    desc_re = re.compile(':(?P<desc>returns?):\s+(?P<value>.+)')
    type_re = re.compile(':(?P<type>rtype):\s+(?P<value>.+)')
    for expression in (desc_re, type_re):
        match = expression.search(help_text)
        if match:
            data = match.groupdict()
            if 'desc' in data:
                key = 'desc'
            else:
                key = 'type'
            value = data['value']
            info.setdefault('returns', {})
            info['returns'][key] = value
        help_text = expression.sub('', help_text)

    info['help_text'] = help_text.strip()
    info['signature'] = get_signature(method)

    return info


def get_signature(method):
    args, varargs, varkw, defaults = inspect.getargspec(method)
    if args[0] in ('self', 'cls'):
        args = args[1:]
    return inspect.formatargspec(args, varargs, varkw, defaults).strip('()')
