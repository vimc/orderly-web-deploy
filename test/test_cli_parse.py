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


def test_cli_parse_status():
    target, args = orderly_web.cli.parse_args(["status", "path"])
    assert target == orderly_web.status
    assert args == ("path",)


def test_cli_parse_stop():
    target, args = orderly_web.cli.parse_args(["stop", "path"])
    assert target == orderly_web.stop
    assert args == ("path", False, False, False, False, None, [])

    target, args = orderly_web.cli.parse_args(["stop", "path", "--kill"])
    assert target == orderly_web.stop
    assert args == ("path", True, False, False, False, None, [])

    target, args = orderly_web.cli.parse_args(["stop", "path", "--network"])
    assert args == ("path", False, True, False, False, None, [])

    target, args = orderly_web.cli.parse_args(["stop", "path", "--volumes"])
    assert args == ("path", False, False, True, False, None, [])

    target, args = orderly_web.cli.parse_args(["stop", "path", "--force",
                                               "--extra=./extra_path",
                                               "--option=k=v"])
    assert args == ("path", False, False, False, True, "./extra_path",
                    [{"k": "v"}])


def test_cli_parse_add_users():
    args = ["admin",
            "path",
            "add-users",
            "test.user@example.com",
            "another.user@email.com"]
    target, args = orderly_web.cli.parse_args(args)
    assert target == orderly_web.add_users
    assert args == ("path", ["test.user@example.com",
                             "another.user@email.com"])


def test_cli_parse_add_groups():
    args = ["admin",
            "path",
            "add-groups",
            "admin",
            "funders"]
    target, args = orderly_web.cli.parse_args(args)
    assert target == orderly_web.add_groups
    assert args == ("path", ["admin", "funders"])


def test_cli_parse_add_members():
    args = ["admin",
            "path",
            "add-members",
            "admin",
            "test.user@email.com",
            "another.user@email.com"]
    target, args = orderly_web.cli.parse_args(args)
    assert target == orderly_web.add_members
    assert args == ("path", "admin", ["test.user@email.com",
                                      "another.user@email.com"])


def test_cli_parse_grant():
    args = ["admin",
            "path",
            "grant",
            "admin",
            "*/reports.read",
            "*/reports.run"]
    target, args = orderly_web.cli.parse_args(args)
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
