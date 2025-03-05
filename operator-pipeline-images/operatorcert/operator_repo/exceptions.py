"""
Exceptions
"""


class OperatorRepoException(Exception):
    """Base exception class"""


class InvalidRepoException(OperatorRepoException):
    """Error caused by an invalid repository structure"""


class InvalidOperatorException(OperatorRepoException):
    """Error caused by an invalid operator"""


class InvalidBundleException(OperatorRepoException):
    """Error caused by an invalid bundle"""


class InvalidCatalogException(OperatorRepoException):
    """Error caused by an invalid catalog"""


class InvalidOperatorCatalogException(OperatorRepoException):
    """Error caused by an invalid operator catalog"""
