from scripts.Crawlers.BaseCrawler import BaseCrawler
from scripts.run_remote import Retrieve
import os
import json
import requests
import xmltodict
import keyring
import sys
import logging
import time
from fair_research_login.local_server import LocalServerCodeHandler
from globus_sdk import (NativeAppAuthClient, TransferClient, TransferData,
                        RefreshTokenAuthorizer, TransferAPIError)

versions = None

logger = logging.getLogger('FRDR-crawler')
logging.basicConfig(level=logging.INFO)


# info at https://www.frdr-dfdr.ca/docs/en/searching/
# dev info https://www.frdr-dfdr.ca/docs/en/advanced/

class FrdrCrawler(BaseCrawler):
    def __init__(self, github_token, config_path, verbose, force):
        super().__init__(github_token, config_path, verbose, force)
        self.settings = {
            'client_id': '01589ab6-70d1-4e1c-b33d-14b6af4a16be',
            'redirect_uri': 'https://auth.globus.org/v2/web/auth-code',
            'scopes': ('openid email profile '
                       'urn:globus:auth:scope:transfer.api.globus.org:all')
        }
        self.verbose = None
        self.transfer_client = None
        # set up authentication procedure to retrieve tokens
        self.setup()

    @staticmethod
    def load_tokens():
        """
        Load a set of saved tokens from keyring
        """
        tokens = keyring.get_password("globus-remote", "auth-tokens")
        return eval(tokens)

    @staticmethod
    def save_tokens(tokens):
        """
        Save a set of tokens in keyring for later use.
        """
        keyring.set_password("globus-remote", "auth-tokens", str(tokens))

    def update_tokens_on_refresh(self, token_response):
        """
        Callback function passed into the RefreshTokenAuthorizer
        Will be invoked any time a new access token is fetched.
        """
        keyring.delete_password("globus-remote", "auth-tokens")
        self.save_tokens(token_response.by_resource_server)

    @staticmethod
    def do_native_app_authentication(client_id, no_browser=False, requested_scopes=None,
                                     local_server_code_handler=LocalServerCodeHandler()):
        """
        Does a Native App authentication flow and returns a dict of tokens keyed by service name.
        """
        client = NativeAppAuthClient(client_id=client_id)
        code_handler = local_server_code_handler  # or secondary_code_handler

        if os.environ.get('SSH_TTY', os.environ.get('SSH_CONNECTION')):
            no_browser = True

        with code_handler.start():
            client.oauth2_start_flow(
                requested_scopes=requested_scopes,
                refresh_tokens=True,
                redirect_uri=code_handler.get_redirect_uri()
            )
            auth_url = client.oauth2_get_authorize_url()
            auth_code = code_handler.authenticate(url=auth_url, no_browser=no_browser)

        token_response = client.oauth2_exchange_code_for_tokens(auth_code)

        return token_response.by_resource_server

    def setup(self):
        """
        Launches authentication procedure
        """
        tokens = None
        try:
            # if we already have tokens, load and use them
            tokens = self.load_tokens()
        except Exception as e:
            logger.info('Tokens not available, try to authenticate: ', e)

        if not tokens:
            # if we need to get tokens, start the Native App authentication process
            tokens = self.do_native_app_authentication(self.settings['client_id'],
                                                       requested_scopes=self.settings['scopes'])
            try:
                self.save_tokens(tokens)
            except Exception as e:
                logger.error('Exception while saving tokens with keyring: ', e)
                sys.exit()
        self.authenticate(tokens)

    def authenticate(self, tokens=None):
        """
        Manages authentication and returns transfer client to enable operations on dataset
        """
        # get tokens from keyring
        if not tokens:
            tokens = self.load_tokens()

        transfer_tokens = tokens['transfer.api.globus.org']

        auth_client = NativeAppAuthClient(client_id=self.settings['client_id'])

        authorizer = RefreshTokenAuthorizer(
            transfer_tokens['refresh_token'],
            auth_client,
            access_token=transfer_tokens['access_token'],
            expires_at=transfer_tokens['expires_at_seconds'],
            on_refresh=self.update_tokens_on_refresh)

        self.transfer_client = TransferClient(authorizer=authorizer)

    def is_completed(self, task_id):
        """
        Waits that an event completes by checking the status of the transfer task
        :param task_id: id of the transfer task
        """
        time.sleep(5)
        task = self.transfer_client.get_task(task_id)
        if task['status'] == 'ACTIVE':
            # keep waiting
            if task['nice_status_short_description'] != 'Queued':
                logger.info("Current status description: ", task['nice_status_short_description'])
            self.is_completed(task_id)
        elif task['status'] == 'SUCCEEDED':
            logger.info("successfully downloaded")
            return
        elif task['status'] == 'INACTIVE':
            logger.error("Inactivity occurred: The task has been suspended and will not continue without intervention."
                         "Currently, only credential expiration will cause this state.")
        else:
            logger.error("Failed: The task or one of its subtasks failed, expired, or was canceled.")

    def transfer_data(self, source_ep, source_path, file_name=None, dest_path=None):
        """
        Enables directory or files transfer between endpoints
        :param source_ep: source endpoint ID
        :param source_path: source dataset prefix path
        :param file_name: file name to transfer (None if a directory is transferred)
        :param dest_path: transfer destination path
        """
        # default value to transfer directories
        is_recursive = True
        destination_ep = None

        # get the destination endpoint
        # NOTE that the current search will be successful if the login to globus is under conp.crawlers@gmail.com
        for ep in self.transfer_client.endpoint_search('FRDR-crawler', filter_scope='my-endpoints'):
            destination_ep = ep['id']

        if not destination_ep:
            logger.error('Invalid endpoint search')

        # find destination path to transfer to is the current directory if not specified otherwise
        destination_path = dest_path or os.path.abspath(os.path.dirname(__file__))

        if not source_path.startswith('/'):
            logger.error('Source path must be absolute')
        if not destination_path.startswith('/'):
            logger.error('Destination path must be absolute')

        # check if a source directory is valid
        try:
            self.transfer_client.operation_ls(source_ep, path=source_path)
        except TransferAPIError as e:
            logger.error(e)

        if file_name:
            is_recursive = False
            destination_path = os.path.join(destination_path, str(file_name))
            source_path = source_path + str(file_name)

        # transfer data - source directory recursively
        tdata = TransferData(self.transfer_client,
                             source_ep,
                             destination_ep,
                             label='Transfer Data')

        tdata.add_item(source_path, destination_path, recursive=is_recursive)

        try:
            logger.info('Submitting a transfer task')
            task = self.transfer_client.submit_transfer(tdata)
        except TransferAPIError as e:
            logger.error(e)
            sys.exit(1)
        else:
            print('\ttask_id: {}'.format(task['task_id']))
            print('You can monitor the transfer task programmatically using Globus SDK'
                  ', or go to the Web UI, https://app.globus.org/activity/{}.'
                  .format(task['task_id']))

        # submit task
        try:
            self.is_completed(task['task_id'])
        finally:
            return destination_path

    def _query_frdr(self):
        """
        Queries FRDR with a given request and obtains metadata
        """
        query = 'https://www.frdr-dfdr.ca/oai/request?verb=ListRecords&metadataPrefix=frdr'
        results = requests.get(query)
        # parse xml
        results_dict = xmltodict.parse(results.text)
        # load into json(dict) object
        results_json = json.loads(json.dumps(results_dict))
        if self.verbose:
            logger.info("FRDR query: {}".format(query))
        return results_json["OAI-PMH"]["ListRecords"]["record"]

    def get_all_files_description(self, ep_id, ep_path):
        """
        Extracts information on file extensions and dataset size
        :param ep_id: dataset globus endpoint
        :param ep_path: dataset globus prefix path
        """
        files_types = []

        def _get_contents(contents):
            for content in contents:
                if isinstance(content, dict):
                    if "type" in content.keys() and content["type"] == "file":
                        file_ext = str(content["name"].split(".")[1])
                        if file_ext not in files_types:
                            files_types.append(file_ext)

                    elif "type" in content.keys() and content["type"] == "dir":
                        _get_contents(content["contents"])
                    else:
                        continue
                else:
                    continue

        # instantiate the file_size.json transfer
        file_sizes_path = self.transfer_data(ep_id, ep_path, file_name='file_sizes.json')
        # open file and read
        with open(file_sizes_path) as json_file:
            json_contents = json.load(json_file)
        # access contents to get list of file types
        _get_contents(json_contents["contents"])
        dataset_size = json_contents["size"]
        globus_path = json_contents["path"]
        # remove file_sizes
        os.remove(file_sizes_path)
        return files_types, dataset_size, globus_path

    def get_all_dataset_description(self):
        """
        Builds DATS for all dataset in the field of neuroscience
        """
        frdr_dois = []
        datasets = self._query_frdr()
        for dataset in datasets:
            metadata = dataset["metadata"]["frdr:frdr"]

            # TODO: to be updated: we are now testing 1 dataset
            if "An End-to-end System for Automatic Characterization of Iba1 Immunopositive Microglia in Whole Slide Imaging: Data" in metadata["dc:title"]:

                files_types, ds_size, globus_path = \
                    self.get_all_files_description(metadata["frdr:globusEndpointName"],
                                                   metadata["frdr:globusEndpointPath"])

                frdr_dois.append(
                {
                    "identifier": {
                        "identifier": metadata["dc:identifier"][0],
                        "identifierSource": "DOI",
                    },
                    "concept_doi": metadata["dc:identifier"][1],
                    "latest_version": metadata["dc:date"][0],
                    "title": metadata["dc:title"],
                    "creators": list(
                        map(lambda x: {"name": x}, metadata["dc:creator"])
                    ),
                    "description": metadata["dc:description"],
                    "version": metadata["dc:version"]
                    if "dc:version" in metadata.keys()
                    else "None",
                    "licenses": list(map(lambda x: {"name": x}, metadata["dc:rights"])),
                    "keywords": list(map(lambda x: {"value": x}, metadata["dc:subject"])),
                    "distributions": [
                        {
                            "formats": [
                                file_format.upper()
                                for file_format in files_types
                                # Do not modify specific file formats.
                                if files_types not in ["NIfTI", "BigWig"]
                            ],
                            "size": int(ds_size),
                            # "unit": {"value": dataset_unit},
                            "access": {
                                "landingPage": metadata["dc:identifier"],
                                "authorizations": [
                                    {
                                        "value": "public"

                                    }
                                ],
                            },
                        }
                    ],
                    "globusProperties": [
                        {
                            "category": "globusEndpoint",
                            "values": [
                                {
                                    "EndpointName": metadata["frdr:globusEndpointName"]
                                },
                                {
                                    "EndpointPath": globus_path
                                }
                            ],
                        }
                    ],
                }
            )
        if self.verbose:
            logger.info("Retrieved FRDR DOIs: ")
            for frdr_doi in frdr_dois:
                logger.info(
                    "- Title: {}, Concept DOI: {}, Latest version DOI: {}".format(
                        frdr_doi["title"],
                        frdr_doi["concept_doi"],
                        frdr_doi["latest_version"],
                    )
                )

        return frdr_dois

    @staticmethod
    def _create_frdr_tracker(path, dataset):
        with open(path, "w") as f:
            data = {
                "version": dataset["latest_version"],
                "title": dataset["title"],
                "endpointName": dataset["globusProperties"][0]["values"][0]["EndpointName"]
            }
            json.dump(data, f, indent=4)

    @staticmethod
    def _retrieve(ds_path, ep_name, ep_path, git_repo, remove=False, tracker_path=None, branch_name=None):
        """
        Updates git-annex with a new dataset location
        """
        dataset_dir = ds_path.split("conp-dataset/")[1]
        os.chdir(dataset_dir)
        logger.info("Switch directory to: ", os.getcwd())
        # instantiates dataset retrieval
        retriever = Retrieve()

        # if the dataset was moved to a different endpoint, old info must be removed in the git annex branch
        if remove:
            f = open(tracker_path, "r")
            tracker = json.load(f)
            # call on old endpoint info to remove dataset info in git annex
            retriever(ds_path, tracker["endpointName"], tracker["endpointPath"], encryption=None, with_remove=remove)
            retriever.initialize()
            retriever.retrieve_files(ds_path, retriever.get_remote_path())
            f.close()

        # adds fresh endpoint info
        retriever(ds_path, ep_name, ep_path, encryption=None)
        retriever.initialize()
        # retrieves dataset info to be saved by git annex
        retriever.retrieve_files(ds_path, retriever.get_remote_path())

        git_repo.git.checkout("git-annex")

        # push to git-annex branch
        git_repo.git.push("origin", "git-annex")
        logger.info("pushed to git annex")

        git_repo.git.checkout("master")
        os.chdir("../..")
        logger.info("Switch directory to: ", os.getcwd())

    def _download(self, ds_description, dataset_dir, dataset, git_repo, branch_name=None):
        """
        Downloads the dataset and updates git-annex
        """
        # find root path
        root_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        ds_path = os.path.join(root_path, dataset_dir)
        # get globus values
        ep_name = ds_description["globusProperties"][0]["values"][0]["EndpointName"]
        ep_path = ds_description["globusProperties"][0]["values"][1]["EndpointPath"]
        # perform transfer of the given dataset
        logger.info("downloading...", ep_name, ep_path, ds_path)
        self.transfer_data(ep_name,
                           ep_path,
                           dest_path=ds_path)
        dataset.save()
        dataset.publish(to="origin")
        # register dataset
        logger.info("retrieving...", ds_path, ep_name, ep_path)
        self._retrieve(ds_path, ep_name, ep_path, git_repo, branch_name=branch_name)

    def add_new_dataset(self, dataset_description, dataset_dir):
        """
        Adds any one time configuration such as annex ignoring files or adding dataset version tracker
        and downloads datasets
        :param dataset_description: a dataset description
        :param dataset_dir: dataset path relative to conp-dataset, such as project/dataset_name
        """
        ds = self.datalad.Dataset(dataset_dir)
        ds.no_annex(".conp-frdr-crawler.json")
        config_path = os.path.join(dataset_dir, "config")
        # fill in the config file
        with open(config_path, 'w') as f:
            f.write("pip install update git-annex-remote-globus \ngit-annex-remote-globus setup \ngit annex enableremote globus")
            f.close()
        ds.no_annex("config")
        ds.save()

        repo = self.git.Repo(dataset_dir)
        clean_title = dataset_dir.split('/')[1]
        branch_name = "conp-bot/" + clean_title
        if branch_name in repo.remotes.origin.refs:
            repo.git.checkout(branch_name)

        # Download dataset
        self._download(dataset_description, dataset_dir, ds, repo, branch_name)

        # Add .conp-osf-crawler.json tracker file
        self._create_frdr_tracker(
           os.path.join(dataset_dir, ".conp-frdr-crawler.json"), dataset_description)

    def update_if_necessary(self, dataset_description, dataset_dir):
        """
        Update dataset if a change is detected in the dataset last modified date
        """
        tracker_path = os.path.join(dataset_dir, ".conp-frdr-crawler.json")
        repo = self.git.Repo(dataset_dir)
        clean_title = dataset_dir.split('/')[1]
        branch_name = "conp-bot/" + clean_title
        if branch_name not in repo.remotes.origin.refs:  # New dataset
            repo.git.checkout("-b", branch_name)

        if not os.path.isfile(tracker_path):
            logger.info("{} does not exist in dataset, skipping".format(tracker_path))
            return False
        with open(tracker_path, "r") as f:
            tracker = json.load(f)
        if tracker["version"] == dataset_description["latest_version"]:
            # Same version, no need to update
            if self.verbose:
                logger.info("{}, version {} same as current FRDR vesion, no need to update"
                      .format(dataset_description["title"], dataset_description["latest_version"]))
            # evaluate change on endpoint name
            endpoint_name = dataset_description["globusProperties"][0]["values"][0]["EndpointName"]
            if tracker["endpointName"] != endpoint_name:
                # Update dataset if endpoint has changed
                if self.verbose:
                    logger.info("{}, last endpoint name {} different from current FRDR version {}, updating"
                          .format(dataset_description["title"], tracker["endpointName"],
                                  endpoint_name))
                # find root path
                root_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                ds_path = os.path.join(root_path, dataset_dir)
                # retrieve without downloading. The remove flag is to remove the previous dataset info in git annex
                self._retrieve(ds_path, endpoint_name,
                               dataset_description["globusProperties"][0]["values"][1]["EndpointPath"],
                               repo, remove=True, tracker_path=tracker_path)
                # update tracker with latest globus location
                with open(tracker_path, "w") as f:
                    tracker = json.load(f)
                    tracker["endpointName"] = endpoint_name
                    tracker.close()
                return True

            else:
                # Same version, no need update
                return False
        else:
            # Update dataset
            if self.verbose:
                logger.info("{}, latest version {} different from current FRDR version {}, updating"
                      .format(dataset_description["title"], tracker["version"],
                              dataset_description["latest_version"]))

            # Remove all data and DATS.json files
            for file_name in os.listdir(dataset_dir):
                if file_name[0] == "." or file_name == "README.md":
                    continue
                self.datalad.remove(os.path.join(dataset_dir, file_name), check=False)

            ds = self.datalad.Dataset(dataset_dir)

            # Download dataset
            self._download(dataset_description, dataset_dir, ds, repo)

            # Add .conp-osf-crawler.json tracker file
            self._create_frdr_tracker(
                os.path.join(dataset_dir, ".conp-frdr-crawler.json"), dataset_description)

            return True

    def get_readme_content(self, dataset):
        return """# {}

Crawled from FRDR

## Description

{}""".format(dataset["title"], dataset["description"])





