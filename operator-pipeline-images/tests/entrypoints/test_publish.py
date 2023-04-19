from unittest.mock import MagicMock, patch

from operatorcert.entrypoints import publish


def test_setup_argparser() -> None:
    assert publish.setup_argparser() is not None


@patch("operatorcert.entrypoints.publish.pyxis.patch")
@patch("operatorcert.entrypoints.publish.pyxis.get_vendor_by_org_id")
def test_publish_vendor_no_change(
    mock_get_vendor: MagicMock, mock_patch: MagicMock
) -> None:
    mock_get_vendor.return_value = {"_id": "foo", "published": True}
    args = MagicMock()
    resp = publish.publish_vendor(args)

    assert resp == {"_id": "foo", "published": True}
    mock_patch.assert_not_called()


@patch("operatorcert.entrypoints.publish.pyxis.patch")
@patch("operatorcert.entrypoints.publish.pyxis.get_vendor_by_org_id")
def test_publish_vendor(mock_get_vendor: MagicMock, mock_patch: MagicMock) -> None:
    mock_get_vendor.return_value = {"_id": "foo", "published": False}
    mock_patch.return_value = {"_id": "foo", "published": True}
    args = MagicMock()
    args.pyxis_url = "https://pyxis.com/"
    resp = publish.publish_vendor(args)

    mock_patch.assert_called_once_with(
        "https://pyxis.com/v1/vendors/id/foo", {"published": True}
    )
    assert resp == {"_id": "foo", "published": True}


@patch("operatorcert.entrypoints.publish.pyxis.patch")
@patch("operatorcert.entrypoints.publish.pyxis.get_repository_by_isv_pid")
@patch("operatorcert.entrypoints.publish.pyxis.get_project")
def test_publish_repository_exists(
    mock_get_project: MagicMock, mock_get_repo: MagicMock, mock_patch: MagicMock
) -> None:
    args = MagicMock()
    args.pyxis_url = "https://pyxis.com/"
    mock_get_project.return_value = {"container": {"isv_pid": "foo"}}
    mock_get_repo.return_value = {"published": True}
    resp = publish.publish_repository(args)

    assert resp == {"published": True}
    mock_patch.assert_not_called()

    mock_get_repo.return_value = {"published": False, "_id": "foobar"}
    mock_patch.return_value = {"published": True}
    resp = publish.publish_repository(args)

    assert resp == {"published": True}
    mock_patch.assert_called_once_with(
        "https://pyxis.com/v1/repositories/id/foobar", {"published": True}
    )


@patch("operatorcert.entrypoints.publish.create_repository")
@patch("operatorcert.entrypoints.publish.pyxis.get_repository_by_isv_pid")
@patch("operatorcert.entrypoints.publish.pyxis.get_project")
def test_publish_repository_create(
    mock_get_project: MagicMock, mock_get_repo: MagicMock, mock_create_repo: MagicMock
) -> None:
    args = MagicMock()
    mock_get_project.return_value = {"container": {"isv_pid": "foo"}}
    mock_get_repo.return_value = None

    mock_create_repo.return_value = {"published": True}
    resp = publish.publish_repository(args)

    mock_create_repo.assert_called_once()
    assert resp == {"published": True}


def test_create_repository_unsupported() -> None:
    project = {"container": {"distribution_method": "external"}}
    assert publish.create_repository(MagicMock(), project) is None


@patch("operatorcert.entrypoints.publish.pyxis.post")
@patch("operatorcert.entrypoints.publish.pyxis.get_vendor_by_org_id")
def test_create_repository(mock_get_vendor: MagicMock, mock_post: MagicMock) -> None:
    project = {
        "container": {
            "distribution_method": "rhcc",
            "repository_name": "repo_name",
            "repository_description": "very long description " * 10,
            "release_category": "rel_cat",
            "privileged": True,
            "application_categories": "app_cat",
            "isv_pid": "pid",
        },
        "name": "project_name",
    }
    mock_get_vendor.return_value = {"label": "my_label"}

    args = MagicMock()
    args.connect_registry = "registry.connect.dev.redhat.com"
    args.pyxis_url = "https://pyxis.com/"

    publish.create_repository(args, project)

    expected_repo = {
        "release_categories": ["rel_cat"],
        "display_data": {
            "name": "project_name",
            "long_description": "very long description " * 10,
            "short_description": "very long description very long description "
            "very long description very long description very...",
        },
        "non_production_only": False,
        "privileged_images_allowed": True,
        "protected_for_pull": False,
        "protected_for_search": False,
        "registry": "registry.connect.dev.redhat.com",
        "repository": "my_label/repo_name",
        "build_categories": ["Operator bundle"],
        "isv_pid": "pid",
        "application_categories": "app_cat",
        "includes_multiple_content_streams": False,
        "published": True,
        "vendor_label": "my_label",
    }
    mock_post.assert_called_once_with(
        "https://pyxis.com/v1/repositories", expected_repo
    )
