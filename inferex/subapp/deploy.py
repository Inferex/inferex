""" Deploy sub-app.

Responsible for packaging local code bundle and then submitting to Inferex
infrastructure for deployment
"""
import os
import tarfile
import tempfile
from pathlib import Path

import requests
import typer
from yaspin import yaspin
from progress.bar import FillingSquaresBar

from inferex.api.client import OperatorClient
from inferex.io.termformat import SPINNER_COLOR, error, info, success
from inferex.io.utils import bundle_size, handle_api_response


PROGRESS_BAR_STEP = 20


def run_deploy(target_dir: Path, git_sha: str):
    """Run a deployment

    Bundles application coe into a compressed archive (xz), and then sends to
    Inferex infrastructure

    Args:
        target_dir (Path): The path to the users Inferex project folder,
                           must contain a inferex.yaml file
        git_sha (str): The computed git SHA of the users current project folder,
                       including unstaged files.

    Raises:
        Exit: Typer internal exception to terminate the application on critical error
    """
    # Disable the no-member warning generated by requests
    # pylint: disable=no-member
    info(f"Preparing to deploy: {target_dir}\n")

    with tempfile.NamedTemporaryFile(delete=True, suffix=".tar.xz") as file_p:
        # Compress the bundle
        with yaspin(text="  Compressing", color=SPINNER_COLOR) as _:
            with tarfile.open(file_p.name, "w:xz") as tar:
                for dir_name, _, file_list in os.walk(target_dir):
                    for file_name in file_list:
                        # recurse target_dir and add the files to a tar archive
                        fs_path = os.path.join(dir_name, file_name)
                        archive_path = os.path.relpath(fs_path, target_dir)
                        tar.add(fs_path, arcname=archive_path)

        filesize_bytes = os.stat(file_p.name).st_size
        success(f"Bundle prepared: {bundle_size(filesize_bytes)}")

        # Upload the file
        prog_bar = FillingSquaresBar("     Uploading", max=PROGRESS_BAR_STEP)

        def prog_callback(monitor):
            complete = PROGRESS_BAR_STEP * monitor.bytes_read / filesize_bytes
            prog_bar.goto(complete)

        client = OperatorClient()
        if client.cached_token is None:
            error("No token present in token.json, exiting.")
            info("Did you get a token with 'inferex login'?")
            raise typer.Exit(1)

        try:
            response = client.deploy(
                git_sha, file_p.name, target_dir, callback=prog_callback
            )
            prog_bar.finish()
        except requests.exceptions.ConnectionError as conn_err:
            error(str(conn_err))
            raise typer.Exit(1)

        if response.status_code == requests.codes.ok:
            success("Deploy complete")

        elif response.status_code == requests.codes.forbidden:
            error(
                f"""Invalid Login,
                please double check your username, password, and/or token
                (status code {response.status_code})"""
            )

        else:
            handle_api_response(response)
