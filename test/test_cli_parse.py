import pytest

import orderly_web
import orderly_web.cli
from orderly_web.cli import string_to_dict
from orderly_web.status import print_status


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


def test_cli_parse_status():
    target, args = orderly_web.cli.parse_args(["status", "path"])
    assert target == print_status
    assert args == ("path", )


def test_cli_parse_stop():
    target, args = orderly_web.cli.parse_args(["stop", "path"])
    assert target == orderly_web.stop
    assert args == ("path", False)
    target, args = orderly_web.cli.parse_args(["stop", "path", "--kill"])
    assert target == orderly_web.stop
    assert args == ("path", True)


def test_cli_parse_add_users():
    target, args = orderly_web.cli.parse_args(
        ["admin", "path", "add-users", "test.user@example.com", "another.user@email.com"])
    assert target == orderly_web.add_users
    assert args == ("path", ["test.user@example.com", "another.user@email.com"])


def test_cli_parse_add_groups():
    target, args = orderly_web.cli.parse_args(
        ["admin", "path", "add-groups", "admin", "funders"])
    assert target == orderly_web.add_groups
    assert args == ("path", ["admin", "funders"])


def test_cli_parse_add_members():
    target, args = orderly_web.cli.parse_args(
        ["admin", "path", "add-members", "admin", "test.user@email.com", "another.user@email.com"])
    assert target == orderly_web.add_members
    assert args == ("path", "admin", ["test.user@email.com", "another.user@email.com"])


def test_cli_parse_grant():
    target, args = orderly_web.cli.parse_args(
        ["admin", "path", "grant", "admin", "*/reports.read", "*/reports.run"])
    assert target == orderly_web.grant
    assert args == ("path", "admin", ["*/reports.read", "*/reports.run"])


def test_cli_parse_validate_options():
    msg = "Invalid option 'foo', expected option in form key=value"
    with pytest.raises(Exception, match=msg):
        orderly_web.cli.parse_args(["start", "path", "--option=foo"])
    msg = "Invalid option 'a=b=c', expected option in form key=value"
    with pytest.raises(Exception, match=msg):
        orderly_web.cli.parse_args(["start", "path", "--option=a=b=c"])


def test_string_to_dict():
    assert string_to_dict("a=x") == {"a": "x"}
    assert string_to_dict("a.b=x") == {"a": {"b": "x"}}
    assert string_to_dict("a.b.c=x") == {"a": {"b": {"c": "x"}}}
    assert string_to_dict("a.b.c=True") == {"a": {"b": {"c": True}}}
    assert string_to_dict("a.b.c=1") == {"a": {"b": {"c": 1}}}
    assert string_to_dict("a.b.c=1.23") == {"a": {"b": {"c": 1.23}}}
    msg = "Invalid option 'foo', expected option in form key=value"
    with pytest.raises(Exception, match=msg):
        string_to_dict("foo")
    msg = "Invalid option 'a=b=c', expected option in form key=value"
    with pytest.raises(Exception, match=msg):
        string_to_dict("a=b=c")
    msg = "Invalid value '{}' - expected simple type"
    with pytest.raises(Exception, match=msg):
        string_to_dict("a={}")
