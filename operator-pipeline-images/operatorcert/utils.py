import json
import logging
import os
import pathlib
from typing import Dict, List, Optional, Tuple

from requests import Session
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

LOGGER = logging.getLogger("operator-cert")


def find_file(
    base_path: pathlib.Path, relative_paths: List[Tuple[str, ...]]
) -> Optional[pathlib.Path]:
    """
    Finds the first file that exists in a list of relative paths.

    Args:
        base_path (Path): A root path to start from
        relative_paths (List[Tuple[str]]): An ordered list of relative paths
            (in tuples) to look for.

    Returns:
        A Path object for the first file found; None otherwise.
    """
    for path in relative_paths:
        new_path = base_path.joinpath(*path)
        if new_path.exists() and new_path.is_file():
            return new_path
    return None


def store_results(results: Dict[str, str]):
    """
    Store the given results into files in given directory.

    Args:
        results (Dict): Dictionary, where key is a result name (name of file to store value),
        and value is result value (to be stored in file).
    """
    for result_name, result_value in results.items():
        if result_value is None:
            result_value = ""
            LOGGER.error(f"Result {result_name} is empty")
        LOGGER.debug(f"Storing {result_name}")
        with open(result_name, "w") as result_file:
            if type(result_value) is dict:
                json.dump(result_value, result_file)
            else:
                result_file.write(str(result_value))


def set_client_keytab(keytab_file: str):
    """
    Set env variable with default client keytab.
    Args:
        keytab_file (path): path to keytab file (default /etc/krb5.krb)
    """
    if not keytab_file:
        return
    if not os.path.isfile(keytab_file):
        raise IOError("Keytab file %s does not exist", keytab_file)
    os.environ["KRB5_CLIENT_KTNAME"] = "FILE:{}".format(keytab_file)
    LOGGER.debug(
        "Set KRB5_CLIENT_KTNAME env variable: %s", os.environ["KRB5_CLIENT_KTNAME"]
    )


def add_session_retries(
    session: Session,
    total: int = 10,
    backoff_factor: int = 1,
    status_forcelist: Optional[Tuple[int]] = (408, 500, 502, 503, 504),
) -> None:
    """
    Adds retries to a requests HTTP/HTTPS session.
    The default values provide exponential backoff for a max wait of ~8.5 mins

    Reference the urllib3 documentation for more details about the kwargs.

    Args:
        session (Session): A requests session
        total (int): See urllib3 docs
        backoff_factor (int): See urllib3 docs
        status_forcelist (tuple[int]|None): See urllib3 docs
    """
    retries = Retry(
        total=total,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
        # Don't raise a MaxRetryError for codes in status_forcelist.
        # This allows for more graceful exception handling using
        # Response.raise_for_status.
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
