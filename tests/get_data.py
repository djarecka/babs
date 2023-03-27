"""This is to get data for pytests"""
import sys
import os
import os.path as op
import pytest
# import tempfile
import shutil
import subprocess
import datalad.api as dlapi
sys.path.append("..")
from babs.utils import (read_yaml)   # noqa

# =============== Define several constant variables: ==================
__location__ = os.path.realpath(
    os.path.join(os.getcwd(), os.path.dirname(__file__)))

# containers:
LIST_WHICH_BIDSAPP = ["toybidsapp", "fmriprep", "qsiprep"]
TOYBIDSAPP_VERSION = "0.0.6"   # +++++++++++++++++++++++
TOYBIDSAPP_VERSION_DASH = TOYBIDSAPP_VERSION.replace(".", "-")
FN_TOYBIDSAPP_SIF_CIRCLECI = op.join("/singularity_images",
                                     "toybidsapp_" + TOYBIDSAPP_VERSION + ".sif")

# path of input datasets:
ORIGIN_INPUT_DATA = read_yaml(op.join(__location__, "origin_input_dataset.yaml"))
INFO_2ND_INPUT_DATA = {
    "which_input": "zipped_derivatives_qsiprep",
    # "type_session": this should be consistent with the first dataset
    "if_input_local": False
}
# ====================================================================

def get_input_data(which_input, type_session, if_input_local, tmp_path_factory):
    """
    This is to get the path of input data.

    Parameters:
    ---------------
    which_input: str
        'BIDS' or 'zipped_derivatives_qsiprep'
    type_session: str
        'single-ses' or 'multi-ses'
    if_input_local: bool
        if the input dataset is local [True] or remote (e.g., on OSF) [False]
    tmp_path_factory: fixture
        see: https://docs.pytest.org/en/7.1.x/how-to/tmp_path.html#the-tmp-path-factory-fixture
        API see: https://docs.pytest.org/en/7.1.x/reference/reference.html#tmp-path-factory

    Returns:
    -----------
    path_in: str
        where is the input dataset
    """
    if not if_input_local:
        # directly grab from pre-defined YAML file:
        path_in = ORIGIN_INPUT_DATA[which_input][type_session]
    else:
        origin_in = ORIGIN_INPUT_DATA[which_input][type_session]
        # create a temporary folder:
        path_in_pathlib = tmp_path_factory.mktemp(which_input)
        # turn into a string of absolute path (but seems not necessary):
        path_in = path_in_pathlib.absolute().as_posix()
        # ^^ e.g.: `/private/var/folders/fn/????/T/pytest-of-<username>/pytest-00/<which_input>0`
        #   `????` is random number but consistent across pytests;
        #   `pytest-00` is index of pytest, 01, 02, etc. Only most recent 3 temp dir will be kept.
        #   `<which_input>0`: e.g., `bids0`, `bids1`, etc.
        #       --> Even if same `which_input`, the temp dir won't be duplicated. Tested.

        # clone to this local temporary place:
        dlapi.clone(source=origin_in,
                    path=path_in)

    return path_in

@pytest.fixture(scope="session")
def if_singularity_installed():
    if_singularity_installed = if_command_installed("singularity")
    # also check if Docker is installed:
    if_docker_installed = if_command_installed("docker")
    # check if one of `singularity` and `docker` is installed:
    if (not if_singularity_installed) and (not if_docker_installed):
        raise Exception("Neither singularity or docker is installed!")

    return if_singularity_installed

@pytest.fixture(scope="session")
def if_circleci():
    """ If it's currently running on CircleCI """
    env_circleci = os.getenv('CIRCLECI')    # a string 'true' or None
    if env_circleci:
        if_circleci = True
    else:
        if_circleci = False

    return if_circleci

@pytest.fixture(scope="session")
def container_ds_path(if_circleci, tmp_path_factory):
    """
    This is to get toy BIDS App container image + create a datalad dataset of it.
        Depending on if pytest is running on CircleCI,
    it will use pre-built sif file (for CircleCI), or pull the Docker image (for other cases).
        Warning: no matter which BIDS App, we'll use toy BIDS App as the image,
    and name the container as those in `LIST_WHICH_BIDSAPP`. Tested that the same image
    can have different names in one datalad dataset.

    Parameters:
    --------------
    if_circleci: from a fixture; bool
        If it's on circle ci. If so, will use pre-built sif file of toybidsapp stored in
        the docker image used for BABS tests.
    tmp_path_factory: fixture in pytest

    Returns:
    -----------
    origin_container_ds: `pathlib.Path`
        path to the created container datalad dataset
        Note: seems `pathlib.Path` type is accepted by datalad and `op`
    """
    docker_addr = "pennlinc/toy_bids_app:" + TOYBIDSAPP_VERSION

    # Pull the container image:
    if if_circleci:
        # assert the sif file exists:
        assert op.exists(FN_TOYBIDSAPP_SIF_CIRCLECI)
    else:
        # directly pull from docker:
        cmd = "docker pull " + docker_addr
        proc_docker_pull = subprocess.run(
            cmd.split())
        proc_docker_pull.check_returncode()

    # Set up container datalad dataset that holds several names of containers
    #   though all of them are toy BIDS App...
    # create a temporary dir:
    origin_container_ds = tmp_path_factory.mktemp("my-container")
    # create a new datalad dataset for holding the container:
    container_ds_handle = dlapi.create(path=origin_container_ds)
    # add container image into this datalad dataset:
    for which_bidsapp in LIST_WHICH_BIDSAPP:
        if if_circleci:   # add the sif file:
            # datalad containers-add --url ${fn_sif} toybidsapp-${version_tag_dash}
            # API help: in python env: `help(dlapi.containers_add)`
            container_ds_handle.containers_add(
                name=which_bidsapp+"-"+TOYBIDSAPP_VERSION_DASH,  # e.g., "toybidsapp-0-0-6"
                url=FN_TOYBIDSAPP_SIF_CIRCLECI)
            # # can remove the original sif file now:
            # os.remove(FN_TOYBIDSAPP_SIF_CIRCLECI)
        else:   # add docker image:
            # datalad containers-add --url dhub://pennlinc/toy_bids_app:${version_tag} \
            #   toybidsapp-${version_tag_dash}
            container_ds_handle.containers_add(
                name=which_bidsapp+"-"+TOYBIDSAPP_VERSION_DASH,  # e.g., "toybidsapp-0-0-6"
                url="dhub://"+docker_addr   # e.g., "dhub://pennlinc/toy_bids_app:0.0.6"
            )

    return origin_container_ds

def if_command_installed(cmd):
    """
    This is to check if a command has been installed on the system

    Parameters:
    ------------
    cmd: str
        the command you want to test. e.g., 'singularity'

    Returns:
    ---------
    if_installed: bool
        True or False
    """
    a = shutil.which(cmd)
    if a is None:   # not exist:
        if_installed = False
    else:
        if_installed = True

    return if_installed