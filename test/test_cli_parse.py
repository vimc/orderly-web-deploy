import pytest

import orderly_web
import orderly_web.cli
from orderly_web.cli import string_to_dict


def test_cli_parse_start():
    target, args = orderly_web.cli.parse_args(["start", "path"])
    assert target == orderly_web.start
    assert args == ("path", None, [], False)


def test_cli_parse_start_with_extra():
    target, args = orderly_web.cli.parse_args(
        ["start", "path", "--extra=extra.yml"])
    assert target == orderly_web.start
    assert args == ("path", "extra.yml", [], False)


def test_cli_parse_start_with_options():
    target, args = orderly_web.cli.parse_args(
        ["start", "path", "--option=a=x", "--option=b.c=y"])
    assert target == orderly_web.start
    options = [{'a': 'x'}, {'b': {'c': 'y'}}]
    assert args == ("path", None, options, False)


def test_cli_parse_validate_options():
    msg = "Invalid option 'foo', expected option in form key=value"
    with pytest.raises(Exception, match=msg):
        orderly_web.cli.parse_args(["start", "path", "--option=foo"])
    msg = "Invalid option 'a=b=c', expected option in form key=value"
    with pytest.raises(Exception, match=msg):
        orderly_web.cli.parse_args(["start", "path", "--option=a=b=c"])


def test_string_to_dict():
    assert string_to_dict("a", "x") == {"a": "x"}
    assert string_to_dict("a.b", "x") == {"a": {"b": "x"}}
    assert string_to_dict("a.b.c", "x") == {"a": {"b": {"c": "x"}}}
