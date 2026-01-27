from unittest.mock import MagicMock, patch


from operatorcert.entrypoints import reserve_operator_name


@patch("operatorcert.entrypoints.reserve_operator_name.setup_argparser")
@patch("operatorcert.entrypoints.reserve_operator_name.reserve_operator_name")
@patch(
    "operatorcert.entrypoints.reserve_operator_name.check_operator_name_registered_for_association"
)
@patch("operatorcert.entrypoints.reserve_operator_name.check_operator_name")
def test_main(
    mock_check: MagicMock,
    mock_check_association: MagicMock,
    mock_reserve: MagicMock,
    mock_arg_parser: MagicMock,
) -> None:
    reserve_operator_name.main()
    mock_check_association.assert_called_once()
    mock_check.assert_called_once()
    mock_reserve.assert_called_once()


@patch("sys.exit")
@patch("operatorcert.entrypoints.reserve_operator_name.pyxis.get")
def test_check_operator_name_registered_for_association_same_name(
    mock_get: MagicMock, mock_exit: MagicMock
) -> None:
    args = MagicMock()
    args.pyxis_url = "http://foo.com/"
    args.key_path = "key.path"
    args.association = "ospid-123"
    args.operator_name = "operator-equal"

    mock_get.status_code = 200
    mock_get.return_value.json.return_value = {
        "data": [
            {
                "association": "ospid-123",
                "package_name": "operator-equal",
            }
        ]
    }

    reserve_operator_name.check_operator_name_registered_for_association(args)
    mock_exit.assert_not_called()


@patch("sys.exit")
@patch("operatorcert.entrypoints.reserve_operator_name.pyxis.get")
def test_check_operator_name_registered_for_association_name_different(
    mock_get: MagicMock, mock_exit: MagicMock
) -> None:
    args = MagicMock()
    args.pyxis_url = "http://foo.com/"
    args.key_path = "key.path"
    args.association = "ospid-123"
    args.operator_name = "operator-x"

    mock_get.status_code = 200
    mock_get.return_value.json.return_value = {
        "data": [
            {
                "association": "ospid-123",
                "package_name": "operator-y",
            }
        ]
    }

    reserve_operator_name.check_operator_name_registered_for_association(args)
    mock_exit.assert_called_once_with(1)


@patch("sys.exit")
@patch("operatorcert.entrypoints.reserve_operator_name.pyxis.get")
def test_check_operator_name_registered_for_association_not_registered(
    mock_get: MagicMock, mock_exit: MagicMock
) -> None:
    args = MagicMock()
    args.pyxis_url = "http://foo.com/"
    args.key_path = "key.path"
    args.association = "ospid-123"
    args.operator_name = "operator-available"

    mock_get.return_value.status_code = 404
    mock_get.return_value.json.return_value = {}

    reserve_operator_name.check_operator_name_registered_for_association(args)
    mock_exit.assert_not_called()


@patch("sys.exit")
@patch("operatorcert.entrypoints.reserve_operator_name.pyxis.get")
def test_check_operator_name_taken(mock_get: MagicMock, mock_exit: MagicMock) -> None:
    args = MagicMock()
    args.pyxis_url = "http://foo.com/"
    args.key_path = "key.path"
    args.association = "ospid-123"
    args.package_name = "operator-taken"

    mock_get.status_code = 200
    mock_get.return_value.json.return_value = {
        "data": [
            {
                "association": "ospid-other",
                "package_name": "operator-taken",
            }
        ]
    }

    reserve_operator_name.check_operator_name(args)
    mock_exit.assert_called_once_with(1)


@patch("sys.exit")
@patch("operatorcert.entrypoints.reserve_operator_name.pyxis.get")
def test_check_operator_name_taken_by_same_assocation(
    mock_get: MagicMock, mock_exit: MagicMock
) -> None:
    args = MagicMock()
    args.pyxis_url = "http://foo.com/"
    args.key_path = "key.path"
    args.association = "ospid-123"
    args.package_name = "operator-taken"

    mock_get.status_code = 200
    mock_get.return_value.json.return_value = {
        "data": [
            {
                "association": "ospid-123",
                "package_name": "operator-taken",
            }
        ]
    }

    reserve_operator_name.check_operator_name(args)
    mock_exit.assert_called_once_with(0)


@patch("sys.exit")
@patch("operatorcert.entrypoints.reserve_operator_name.pyxis.get")
def test_check_operator_name_available(
    mock_get: MagicMock, mock_exit: MagicMock
) -> None:
    args = MagicMock()
    args.pyxis_url = "http://foo.com/"
    args.key_path = "key.path"
    args.association = "ospid-123"
    args.package_name = "operator-available"

    mock_get.return_value.status_code = 404
    mock_get.return_value.json.return_value = {}

    reserve_operator_name.check_operator_name(args)
    mock_exit.assert_not_called()


@patch("operatorcert.entrypoints.reserve_operator_name.pyxis.post")
def test_reserve_operator_name(mock_post: MagicMock) -> None:
    args = MagicMock()
    args.pyxis_url = "http://foo.com/"
    args.key_path = "key.path"
    args.association = "ospid-123"
    args.operator_name = "operator-new"
    args.source = "sample_source"

    mock_post.return_value.json.return_value = {
        "data": [
            {
                "association": "ospid-123",
                "package_name": "operator-new",
            }
        ]
    }

    reserve_operator_name.reserve_operator_name(args)
    mock_post.assert_called_once_with(
        "http://foo.com/v1/operators/packages",
        {
            "association": "ospid-123",
            "package_name": "operator-new",
            "source": "sample_source",
        },
    )
