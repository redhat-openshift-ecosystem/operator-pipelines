from unittest.mock import MagicMock, patch

from operatorcert.entrypoints import hydra_checklist


@patch("operatorcert.entrypoints.hydra_checklist.setup_argparser")
@patch("operatorcert.entrypoints.hydra_checklist.check_hydra_checklist_status")
def test_main(mock_check: MagicMock, mock_arg_parser: MagicMock) -> None:
    hydra_checklist.main()
    mock_check.assert_called_once()


@patch("operatorcert.entrypoints.hydra_checklist.hydra.get")
def test_check_hydra_checklist_status_overall_completed(mock_get: MagicMock) -> None:
    mock_get.return_value = {"completed": True}
    hydra_checklist.check_hydra_checklist_status("foo", "fake-hydra.url", False)


@patch("operatorcert.entrypoints.hydra_checklist.hydra.get")
def test_check_hydra_checklist_status_items_completed(mock_get: MagicMock) -> None:
    mock_get.return_value = {
        "checklistItems": [
            {"title": "Test1", "completed": True},
            {"title": "Test2", "completed": True},
            {"title": "Test3", "completed": True},
        ],
        "completed": False,
    }
    hydra_checklist.check_hydra_checklist_status("foo", "fake-hydra.url", False)


@patch("sys.exit")
@patch("operatorcert.entrypoints.hydra_checklist.hydra.get")
def test_check_hydra_checklist_status_incomplete(
    mock_get: MagicMock, mock_exit: MagicMock
) -> None:
    mock_get.return_value = {
        "checklistItems": [
            {"title": "Test1", "completed": False},
            {"title": "Test2", "completed": True},
            {"title": "Test3", "completed": False},
        ],
        "completed": False,
    }
    hydra_checklist.check_hydra_checklist_status("foo", "fake-hydra.url", False)
    mock_exit.assert_called_once_with(1)

    # If the developer flag is on
    mock_get.return_value = {
        "checklistItems": [
            {"title": "Test1", "completed": False},
            {"title": "Test2", "completed": True},
            {"title": "Test3", "completed": False},
        ],
        "completed": False,
    }
    hydra_checklist.check_hydra_checklist_status("foo", "fake-hydra.url", True)
