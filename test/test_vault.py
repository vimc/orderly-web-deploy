import pytest
import vault_dev

from orderly_web.vault import resolve_secret, vault_config, vault_not_enabled


def test_secret_reading():
    with vault_dev.server() as s:
        client = s.client()
        client.write("secret/foo", value="s3cret")
        assert resolve_secret("foo", client) == (False, "foo")
        assert resolve_secret("VAULT:secret/foo:value", client) == \
            (True, "s3cret")


def test_accessor_validation():
    with vault_dev.server() as s:
        client = s.client()
        with pytest.raises(Exception, match="Invalid vault accessor"):
            resolve_secret("VAULT:invalid", client)
        with pytest.raises(Exception, match="Invalid vault accessor"):
            resolve_secret("VAULT:invalid:a:b", client)


def test_error_for_missing_secret():
    with vault_dev.server() as s:
        client = s.client()
        msg = "Did not find secret at 'secret/foo'"
        with pytest.raises(Exception, match=msg):
            resolve_secret("VAULT:secret/foo:bar", client)


def test_error_for_missing_secret_key():
    with vault_dev.server() as s:
        client = s.client()
        client.write("secret/foo", value="s3cret")
        msg = "Did not find key 'bar' at secret path 'secret/foo'"
        with pytest.raises(Exception, match=msg):
            resolve_secret("VAULT:secret/foo:bar", client)


def test_vault_config():
    with vault_dev.server() as s:
        client = s.client()
        url = "http://localhost:{}".format(s.port)
        cfg = vault_config(url, "token", {"token": s.token})
        cl = cfg.client()
        assert cl.is_authenticated()


def test_vault_config_when_missing():
    cfg = vault_config(None, "token", {"token": "root"})
    cl = cfg.client()
    assert type(cl) == vault_not_enabled
    with pytest.raises(Exception, match="Vault access is not enabled"):
        cl.read("secret/foo")
