from xmlrpc_wp.api import API


class WordPressCom(API):

    namespace = 'wpcom'

    @classmethod
    def getFeatures(cls, *args):
        """
        Gets the available features.
        This only contains information about video uploading.

        :returns: {features}
        :rtype: struct

        """

        return {
            'videopress_enabled': True,
        }
