from unittest.mock import MagicMock, patch


from operatorcert.entrypoints import check_operator_name


@patch("operatorcert.entrypoints.check_operator_name.setup_argparser")
@patch("operatorcert.entrypoints.check_operator_name.check_operator_name")
def test_main(mock_check: MagicMock, mock_arg_parser: MagicMock) -> None:
    check_operator_name.main()
    mock_check.assert_called_once()


@patch("sys.exit")
@patch("operatorcert.entrypoints.check_operator_name.pyxis.get")
def test_check_operator_name_is_the_same(
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

    check_operator_name.check_operator_name(args)
    mock_exit.assert_not_called()


@patch("sys.exit")
@patch("operatorcert.entrypoints.check_operator_name.pyxis.get")
def test_check_operator_name_taken_and_different(
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

    check_operator_name.check_operator_name(args)
    mock_exit.assert_called_once_with(1)


@patch("sys.exit")
@patch("operatorcert.entrypoints.check_operator_name.pyxis.get")
def test_check_operator_name_not_registered(
    mock_get: MagicMock, mock_exit: MagicMock
) -> None:
    args = MagicMock()
    args.pyxis_url = "http://foo.com/"
    args.key_path = "key.path"
    args.association = "ospid-123"
    args.operator_name = "operator-available"

    mock_get.return_value.status_code = 404
    mock_get.return_value.json.return_value = {}

    check_operator_name.check_operator_name(args)
    mock_exit.assert_not_called()
