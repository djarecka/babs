# This is to test `babs-check-setup`.

import os
import os.path as op
import sys
import argparse
import pytest
from unittest import mock
sys.path.append("..")
from babs.cli import (    # noqa
    babs_init_main,
    babs_check_setup_main)
from get_data import (   # noqa
    get_input_data,
    container_ds_path,
    if_circleci,
    templateflow_home,
    __location__,
    INFO_2ND_INPUT_DATA,
    LIST_WHICH_BIDSAPP,
    TOYBIDSAPP_VERSION_DASH
)

@pytest.mark.order(index=2)
@pytest.mark.parametrize(
    "which_case",
    [("no_babs_project"),
     ("keep_failed")]
)
def test_babs_check_setup(
        which_case,
        tmp_path, tmp_path_factory,
        container_ds_path, if_circleci):
    """
    This is to test `babs-check-setup` in different failed `babs-init` cases.
    Successful `babs-init` has been tested in `test_babs_init.py`.
    We won't test `--job-test` either as that requires installation of cluster simulation system.

    Parameters:
    ---------------
    which_case: str
        'no_babs_project', 'keep_failed'
        For both cases, `container_ds` will be a wrong path, leading to `babs-init` failure;
        in addition, for case 'keep_failed', flag `--keep-if-failed` in `babs-init` will turn on
    tmp_path: fixture from pytest
    tmp_path_factory: fixture from pytest
    container_ds_path: fixture; str
        Path to the container datalad dataset
    """
    # fixed variables:
    which_bidsapp = "toybidsapp"
    assert which_bidsapp in LIST_WHICH_BIDSAPP
    which_input = "BIDS"
    type_session = "multi-ses"
    if_input_local = False

    # Get the path to input dataset:
    path_in = get_input_data(which_input, type_session, if_input_local, tmp_path_factory)
    input_ds_cli = [[which_input, path_in]]

    # Container dataset - has been set up by fixture `prep_container_ds_toybidsapp()`
    assert op.exists(container_ds_path)
    assert op.exists(op.join(container_ds_path, ".datalad/config"))
    container_ds_path_wrong = "/random/path/to/container_ds"

    # Get the cli of `babs-init`:
    where_project = tmp_path.absolute().as_posix()   # turn into a string
    project_name = "my_babs_project"
    project_root = op.join(where_project, project_name)
    container_name = which_bidsapp + "-" + TOYBIDSAPP_VERSION_DASH
    container_config_yaml_filename = "example_container_" + which_bidsapp + ".yaml"
    container_config_yaml_file = op.join(op.dirname(__location__), "notebooks",
                                         container_config_yaml_filename)

    babs_init_opts = argparse.Namespace(
        where_project=where_project,
        project_name=project_name,
        input=input_ds_cli,
        list_sub_file=None,
        # container_ds=container_ds_path,
        container_name=container_name,
        container_config_yaml_file=container_config_yaml_file,
        type_session=type_session,
        type_system="sge",
        keep_if_failed=False
    )

    # inject something wrong --> `babs-init` will fail:
    babs_init_opts.container_ds = container_ds_path_wrong
    if which_case == "keep_failed":
        babs_init_opts.keep_if_failed = True

    # run `babs-init`:
    with mock.patch.object(
            argparse.ArgumentParser, 'parse_args', return_value=babs_init_opts):
        babs_init_main()

    # Get cli of `babs-check-setup`:
    babs_check_setup_opts = argparse.Namespace(
        project_root=project_root,
        job_test=False
    )
    # Set up expected error message from `babs-check-setup`:
    if which_case == "no_babs_project":
        error_type = Exception   # what's after `raise` in the source code
        error_msg = "`--project-root` does not exist!"
        # ^^ see `get_existing_babs_proj()` in CLI
    elif which_case == "keep_failed":
        error_type = AssertionError   # error from `assert`
        error_msg = "Analysis DataLad dataset's status is not clean"

    # Run `babs-check-setup`:
    with mock.patch.object(
            argparse.ArgumentParser, 'parse_args', return_value=babs_check_setup_opts):
        with pytest.raises(error_type,
                           match=error_msg):   # contains what pattern in error message
            babs_check_setup_main()
