from unittest.mock import MagicMock, patch

from operatorcert.entrypoints import hydra_checklist


@patch("operatorcert.entrypoints.hydra_checklist.setup_argparser")
@patch("operatorcert.entrypoints.hydra_checklist.check_hydra_checklist_status")
def test_main(mock_check: MagicMock, mock_arg_parser: MagicMock) -> None:
    hydra_checklist.main()
    mock_check.assert_called_once()


def test_check_single_hydra_checklist_pass() -> None:
    checklist = {
        "checklistItems": [
            {"title": "Test1", "status": "COMPLETED", "optional": False},
            {"title": "Test2", "status": "COMPLETED", "optional": True},
            {
                "title": "Test3",
                "status": "NOT_COMPLETED",
                "optional": True,
                "reasons": ["It failed"],
            },
        ],
    }
    resp = hydra_checklist.check_single_hydra_checklist(checklist)
    assert resp == True


def test_check_single_hydra_checklist_fail() -> None:
    checklist = {
        "checklistItems": [
            {"title": "Test1", "status": "COMPLETED", "optional": False},
            {
                "title": "Test2",
                "status": "NOT_COMPLETED",
                "optional": False,
                "reasons": ["It failed"],
            },
        ],
    }
    resp = hydra_checklist.check_single_hydra_checklist(checklist)
    assert resp == False


@patch("operatorcert.entrypoints.hydra_checklist.hydra.get")
def test_check_hydra_checklist_status_overall_completed(mock_get: MagicMock) -> None:
    mock_get.return_value = {"status": "COMPLETED"}
    hydra_checklist.check_hydra_checklist_status("foo", "fake-hydra.url", False)


@patch("operatorcert.entrypoints.hydra_checklist.check_single_hydra_checklist")
@patch("operatorcert.entrypoints.hydra_checklist.hydra.get")
def test_check_hydra_checklist_status_items_completed(
    mock_get: MagicMock, mock_completed: MagicMock
) -> None:
    mock_get.return_value = {
        "status": "NOT_COMPLETED",
    }
    mock_completed.return_value = True
    hydra_checklist.check_hydra_checklist_status("foo", "fake-hydra.url", False)


@patch("sys.exit")
@patch("operatorcert.entrypoints.hydra_checklist.check_single_hydra_checklist")
@patch("operatorcert.entrypoints.hydra_checklist.hydra.get")
def test_check_hydra_checklist_status_incomplete(
    mock_get: MagicMock, mock_completed: MagicMock, mock_exit: MagicMock
) -> None:
    mock_get.return_value = {"status": "NOT_COMPLETED", "items": [{"name": "val"}]}
    mock_completed.return_value = False
    hydra_checklist.check_hydra_checklist_status("foo", "fake-hydra.url", False)
    mock_exit.assert_called_once_with(1)

    # If the developer flag is on
    mock_exit.reset_mock()
    hydra_checklist.check_hydra_checklist_status("foo", "fake-hydra.url", True)
    mock_exit.assert_not_called()
