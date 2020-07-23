import logging
import sys
import os
import subprocess
import configparser

logger = logging.getLogger('retrieve-globus')
logging.basicConfig(level=logging.WARN)


class Retrieve:

    """
    Class to enable git-annex to retrieve and register dataset information in Globus Transfer. Depending on the dataset
    status, the initremote or the enableremote commands are launched
    """

    def __init__(self):
        self.url_prefix = 'globus://'
        self.annex_uuid = None

    def __call__(self, dataset_path, dataset_name, remote_prefix, encryption, with_remove=False):
        self.dataset_path = dataset_path
        self.remote_prefix = remote_prefix
        self.dataset_name = dataset_name
        self.encryption = str(encryption).lower()
        # if dataset info must be removed in git annex
        self.remove = with_remove

    @property
    def remote_path(self):
        """
        Builds globus path
        """
        return self.url_prefix + self.dataset_name + self.remote_prefix

    def get_remote_path(self):
        """
        Returns globus path
        """
        return self.remote_path

    @staticmethod
    def _execute_cmd(func, message):
        try:
            func
        except Exception as ex:
            logger.error('An exception occurred: ' + message + '-->' + str(ex))
            sys.exit()

# ******************************************************************************************************************** #

    def _get_annex_uuid(self):
        """
        Get the annex-uuid from the config
        """
        config = configparser.ConfigParser()
        config.read(self.dataset_path + "/.git/config")
        try:
            return config['remote "globus"']['annex-uuid']
        except Exception as ex:
            logger.error('The following exceptions was raised during annex-uuid retrieving: ' + str(ex))
            sys.exit()

    @staticmethod
    def _set_up():
        """
        Runs the setup which involves authentication to Globus
        """
        setup_command = ['git-annex-remote-globus', 'setup']
        process = subprocess.Popen(setup_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        _, error = process.communicate()
        return error

    def _init_remote(self):
        """
        Runs initremote for a new dataset or enableremote to update an existing dataset
        """
        encryption = 'encryption=%s' % self.encryption
        endpoint = 'endpoint=%s' % self.dataset_name
        fileprefix = 'fileprefix=%s' % self.remote_prefix
        if not self.remove:
            logger.info('initializing remote')
            initremote_command = \
                ['git', 'annex', 'initremote', 'globus',  'type=external', 'externaltype=globus', endpoint, fileprefix,
                 encryption]
            process = subprocess.Popen(initremote_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            _, error = process.communicate()
        else:
            logger.info('enabling remote')
            enableremote_command = ['git', 'annex', 'enableremote', 'globus', endpoint, fileprefix]
            process = subprocess.Popen(enableremote_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            _, error = process.communicate()

        if error:
            logger.error(error)
        return

    def initialize(self):
        # runs authentication if necessary
        self._execute_cmd(self._set_up(), 'An error occurred during setup')
        # initializes a globus remote
        self._execute_cmd(self._init_remote(), 'An error occurred during initialization')
        if not self.annex_uuid:
            self.annex_uuid = self._get_annex_uuid()

# ******************************************************************************************************************** #

    def retrieve_files(self, ds_path, remote_path):
        """
        Recursively retrieves files in the dataset that will be saved by git-annex as a key-value pair, where the
        value is a globus url
        :param ds_path: dataset path
        :param remote_path: globus path to build urls
        """
        try:
            # list content
            for elem in os.listdir(ds_path):
                update_path = os.path.join(ds_path, elem)
                update_remote_path = os.path.join(remote_path, elem)
                if os.path.isdir(update_path):
                    # recurse
                    self.retrieve_files(update_path, update_remote_path)
                else:
                    if os.path.islink(update_path):
                        key = str(os.readlink(update_path)).split('/')[-1]
                        # print(key, update_remote_path)
                        self.process(key, update_remote_path)
                        logger.info("Retrieved:: " + str(update_path))
                    else:
                        pass
        except Exception as ex:
            logger.error('The following exception was raised while retrieving files: ' + str(ex))
            sys.exit()

    def _set_present_key(self, key, val):
        """
        Sets a file key present with 1, meaning that git annex registers the file as present and
        available for download from globus
        """
        # set present key
        setpresentkey_command = ['git', 'annex', 'setpresentkey', key, self.annex_uuid, str(val)]
        process = subprocess.Popen(setpresentkey_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        _, error = process.communicate()
        return error

    @staticmethod
    def _rm_url(file_path, url):
        """
        Removes a globus url from git annex branch
        :param file_path: dynamic file path (no prefix)
        :param url: globus url
        """
        # register url
        registerurl_command = ['git', 'annex', 'rmurl', file_path, url]
        process = subprocess.Popen(registerurl_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        _, error = process.communicate()
        return error

    @staticmethod
    def _register_url(key, url):
        """
        Registers a globus url (value) with git annex, which belong to the key-value pair
        """
        # register url
        registerurl_command = ['git', 'annex', 'registerurl', key, url]
        process = subprocess.Popen(registerurl_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        _, error = process.communicate()
        return error

    def process(self, key, url):
        """
        Processes a key-value pair
        """
        # TODO: add count of errors
        if self.remove:
            self._execute_cmd(self._set_present_key(key, 0),
                              str('An error occurred during setpresent 0 key with path: ' + url))
            file_path = url.split(self.remote_prefix)[1]
            # make sure the file path is valid
            if file_path.startswith('/'):
                file_path = file_path[1:]
            # remove globus url
            self._execute_cmd(self._rm_url(file_path, url),
                              str('An error occurred during url removal with path: ' + url))
        else:
            self._execute_cmd(self._set_present_key(key, 1),
                              str('An error occurred during setpresent 1 key with path: ' + url))
            # register globus url
            self._execute_cmd(self._register_url(key, url),
                              str('An error occurred during url registration with path: ' + url))



