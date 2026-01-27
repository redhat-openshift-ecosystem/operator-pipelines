from unittest.mock import MagicMock, patch

import lark
from operatorcert.webhook_dispatcher.config import Filter, load_config
import pytest
from pydantic import ValidationError


@patch("operatorcert.webhook_dispatcher.config.yaml.safe_load")
@patch("operatorcert.webhook_dispatcher.config.open")
def test_load_config(mock_open: MagicMock, mock_yaml_load: MagicMock) -> None:
    mock_open.return_value = MagicMock()
    mock_yaml_load.return_value = {
        "dispatcher": {
            "items": [
                {
                    "name": "test",
                    "events": ["push"],
                    "full_repository_name": "test/test",
                    "callback_url": "https://test.com",
                    "capacity": {
                        "max_capacity": 1,
                        "type": "ocp_tekton",
                        "pipeline_name": "test",
                        "namespace": "test",
                    },
                    "filter": {
                        "cel_expression": "body.action == 'push'",
                    },
                }
            ]
        },
        "security": {"token": "test"},
    }
    config = load_config("config/dispatcher_config.yaml")
    assert config is not None
    assert config.dispatcher is not None
    assert config.security is not None
    assert config.dispatcher.items is not None
    assert config.dispatcher.items[0].name == "test"
    assert config.dispatcher.items[0].events == ["push"]
    assert config.dispatcher.items[0].full_repository_name == "test/test"


def test_cel_expression_compilation() -> None:
    # Valid expression
    filter_config = Filter(cel_expression='body.action == "push"')  # type: ignore[arg-type]
    assert isinstance(filter_config.cel_expression, lark.Tree)

    # Empty expression
    filter_config_no_expr = Filter(cel_expression="")  # type: ignore[arg-type]
    assert filter_config_no_expr.cel_expression is None

    # Invalid expression
    with pytest.raises(ValidationError):
        Filter(cel_expression="body.action = push")  # type: ignore[arg-type]
