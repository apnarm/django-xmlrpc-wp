import logging
import sys
import xmlrpclib

from SimpleXMLRPCServer import SimpleXMLRPCDispatcher, Fault

from xmlrpc_wp.api.metaweblog import MetaWeblog
from xmlrpc_wp.api.wp import WordPress
from xmlrpc_wp.api.wpcom import WordPressCom
from xmlrpc_wp.utils import get_arguments, get_method_info


class Dispatcher(SimpleXMLRPCDispatcher):

    def _exception_response(self):
        exc_type, exc_value, exc_tb = sys.exc_info()
        return xmlrpclib.dumps(
            xmlrpclib.Fault(1, '%s: %s' % (exc_type.__name__, exc_value)),
            encoding=self.encoding,
            allow_none=self.allow_none,
        )

    def run(self, xml_data):
        """
        Processes the XML data, executes the commands, and returns the result.

        This is just a version of _marshaled_dispatch that uses datetime objects
        rather than these weird DateTime instances.

        """

        try:
            params, method_name = xmlrpclib.loads(xml_data, use_datetime=1)
        except Exception:
            return self._exception_response()

        if logging.debug:
            method = self.funcs.get(method_name)
            if method:
                # Log the method signature that is being called.
                # Hide the password though!
                args = list(get_arguments(method)[0])
                for (position, (name, value)) in enumerate(zip(args, params)):
                    if name == 'password':
                        value = '*' * len(value)
                    args[position] = value
                logging.debug('Running %s%s' % (method_name, tuple(args)))

        try:
            response = self._dispatch(method_name, params)
            response = (response,)
            return xmlrpclib.dumps(response, methodresponse=1,
                                   allow_none=self.allow_none,
                                   encoding=self.encoding)

        except Fault, fault:
            logging.warning('Fault: %s' % fault)
            return xmlrpclib.dumps(
                fault,
                allow_none=self.allow_none,
                encoding=self.encoding,
            )

        except Exception, error:
            logging.error('Exception: %s' % error)
            return self._exception_response()

    def system_listMethods(self):
        """
        Gets a list of the methods supported by the server.

        :returns: ['method name', ...]
        :rtype: list

        """

        return SimpleXMLRPCDispatcher.system_listMethods(self)

    def system_methodHelp(self, method_name):
        """
        Gets documentation for the specified method.

        :type method_name: string

        :returns: 'help text'
        :rtype: string

        """

        return SimpleXMLRPCDispatcher.system_methodHelp(self, method_name)

    def system_methodSignature(self, method_name):
        """
        Gets a list describing the signature of specified method. The first
        value is the return type, and the following values are the argument
        types in the order that they must be passed in.

        :type method_name: string

        :returns: ['return type', 'arg1 type', 'arg2 type', ...]
        :rtype: array

        """

        try:
            method = self.funcs[method_name]
        except KeyError:
            raise Fault(404, 'Method not found.')

        method_info = get_method_info(method)

        return_type = method_info.get('returns', {}).get('type')
        if not return_type:
            # If the signature is not defined in the method's docstring,
            # then just abort and say we don't know the signature.
            return 'undef'

        arg_types = []
        for arg_info in method_info.get('args', {}).values():
            arg_type = arg_info.get('type')
            if arg_type:
                arg_types.append(arg_type)
            else:
                # If we have arg info but it's missing the type,
                # then just abort and say we don't know the signature.
                return 'undef'

        return [return_type] + arg_types

    def register_multicall_functions(self):
        self.funcs.update({'system.multicall': self.multicall})

    def multicall(self, *args, **kwargs):
        # wordpress provides the list as separate arguments, so we need to
        # use *args to get them as a list and pass them through to the stdlib.
        return self.system_multicall(args)


dispatcher = Dispatcher(allow_none=False, encoding=None)
dispatcher.register_introspection_functions()
dispatcher.register_multicall_functions()


MetaWeblog.register_with(dispatcher)
WordPress.register_with(dispatcher)
WordPressCom.register_with(dispatcher)
