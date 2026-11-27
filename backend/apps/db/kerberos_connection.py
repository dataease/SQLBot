"""Datasource-local Kerberos credentials; no changes to the API process environment."""

import base64
import multiprocessing
import os
import re
import signal
import subprocess
import tempfile
import threading
from pathlib import Path

_LIMIT = threading.BoundedSemaphore(8)
_ERROR = (
    "Kerberos connection failed; check credentials, KDC, DNS and runtime dependencies"
)


def validate_profile(text: str) -> str:
    """Accept a deliberately small krb5 profile subset, excluding file/plugin directives."""
    if not isinstance(text, str) or len(text.encode()) > 65536:
        raise ValueError("Invalid Kerberos profile")
    section = ""
    realm_open = False
    output = []
    allowed = {
        "default_realm",
        "dns_lookup_kdc",
        "dns_lookup_realm",
        "rdns",
        "dns_canonicalize_hostname",
        "ticket_lifetime",
        "renew_lifetime",
        "forwardable",
        "udp_preference_limit",
        "clockskew",
    }
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith(("#", ";")):
            continue
        if line in ("[libdefaults]", "[realms]", "[domain_realm]") and not realm_open:
            section = line[1:-1]
        elif (
            section == "realms"
            and not realm_open
            and re.fullmatch(r"[A-Za-z0-9_.-]+\s*=\s*\{", line)
        ):
            realm_open = True
        elif section == "realms" and realm_open and line == "}":
            realm_open = False
        else:
            if "=" not in line:
                raise ValueError("Unsupported Kerberos profile directive")
            key, value = (part.strip() for part in line.split("=", 1))
            valid_key = (
                section == "libdefaults"
                and key in allowed
                or section == "realms"
                and realm_open
                and key in {"kdc", "admin_server", "kpasswd_server"}
                or section == "domain_realm"
                and re.fullmatch(r"\.?[A-Za-z0-9_.-]+", key)
            )
            valid_value = re.fullmatch(r"[A-Za-z0-9_.:@-]+", value) or (
                section == "realms"
                and key == "kdc"
                and re.fullmatch(r"(?:tcp|udp)/[A-Za-z0-9_.-]+(?::[0-9]+)?", value)
            )
            if not valid_key or not valid_value:
                raise ValueError("Unsupported Kerberos profile setting")
        output.append(line)
    if realm_open or not output:
        raise ValueError("Invalid Kerberos profile")
    return "\n".join(output) + "\n"


def validate_credentials(config: dict) -> bytes:
    validate_profile(config.get("kerberosConf", ""))
    principal = config.get("kerberosPrincipal", "")
    if not isinstance(principal, str) or not re.fullmatch(
        r"[A-Za-z0-9_][A-Za-z0-9_./-]*@[A-Za-z0-9_.-]+", principal
    ):
        raise ValueError("Invalid Kerberos principal")
    service = config.get("kerberosService", "")
    if not isinstance(service, str) or not re.fullmatch(
        r"[A-Za-z][A-Za-z0-9_-]{0,63}", service
    ):
        raise ValueError("Invalid Kerberos service")
    host = config.get("kerberosHost", "")
    if not isinstance(host, str) or (
        host
        and (
            len(host) > 253
            or not all(
                re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?", label)
                for label in host.rstrip(".").split(".")
            )
        )
    ):
        raise ValueError("Invalid Kerberos service hostname")
    encoded = config.get("kerberosKeytab", "")
    if not isinstance(encoded, str) or len(encoded) > 350000:
        raise ValueError("Invalid keytab size")
    try:
        keytab = base64.b64decode(encoded, validate=True)
    except (ValueError, TypeError):
        raise ValueError("Invalid keytab encoding") from None
    if not 4 <= len(keytab) <= 262144 or keytab[:2] not in (b"\x05\x01", b"\x05\x02"):
        raise ValueError("Invalid keytab")
    return keytab


def connect_hs2(hive, config):
    """Called only in a datasource-owned worker; keep TCP and SASL targets separate."""
    original = hive.get_installed_sasl

    def sasl_client(host, sasl_auth, service=None, username=None, password=None):
        return original(
            host=config.get("kerberosHost") or host,
            sasl_auth=sasl_auth,
            service=service,
            username=username,
            password=password,
        )

    hive.get_installed_sasl = sasl_client
    try:
        return hive.connect(
            host=config["host"],
            port=config["port"],
            username=config["username"],
            database=config["database"],
            auth="KERBEROS",
            kerberos_service_name=config["kerberosService"],
        )
    finally:
        hive.get_installed_sasl = original


def _worker(pipe, config, directory):
    conn = cursor = None
    connected = False
    # Include kinit in the worker's process group so cancellation cannot orphan it.
    if hasattr(os, "setsid"):
        os.setsid()
    try:
        root = Path(directory)
        profile = root / "krb5.conf"
        keytab = root / "client.keytab"
        profile.write_text(validate_profile(config["kerberosConf"]))
        keytab.write_bytes(validate_credentials(config))
        profile.chmod(0o600)
        keytab.chmod(0o600)
        # This process belongs to exactly one connection/identity.
        os.environ["KRB5_CONFIG"] = str(profile)
        os.environ["KRB5CCNAME"] = "FILE:" + str(root / "ccache")
        os.environ["KRB5_CLIENT_KTNAME"] = str(keytab)
        subprocess.run(
            ["kinit", "-k", "-t", str(keytab), config["kerberosPrincipal"]],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=30,
            check=True,
        )
        from pyhive import hive

        conn = connect_hs2(hive, config)
        cursor = conn.cursor()
        connected = True
        pipe.send((True, None))
        while True:
            command, value = pipe.recv()
            if command == "close":
                break
            if command == "execute":
                cursor.execute(value)
                pipe.send((True, cursor.description))
            elif command == "fetchall":
                pipe.send((True, cursor.fetchall()))
            else:
                raise ValueError("Unsupported operation")
    except (EOFError, BrokenPipeError):
        pass
    except Exception as error:
        message = _ERROR
        if connected:
            message = "SQL execution failed"
            from pyhive.exc import Error as HiveError

            if isinstance(error, HiveError):
                detail = str(error)
                for secret in (
                    config.get("password"),
                    config.get("kerberosKeytab"),
                    config.get("kerberosConf"),
                    directory,
                ):
                    if secret:
                        detail = detail.replace(secret, "[redacted]")
                message += ": " + detail[:4000]
        try:
            pipe.send((False, message))
        except (EOFError, BrokenPipeError):
            pass
    finally:
        if cursor is not None:
            try:
                cursor.close()
            except Exception:
                pass
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass
        pipe.close()


class KerberosConnection:
    """Small DB-API facade. Each connection obtains fresh tickets and cleans them on close."""

    def __init__(self, config):
        validate_credentials(config)
        self.timeout = max(1, min(config.get("timeout") or 30, 300))
        self.closed = False
        self.description = None
        if not _LIMIT.acquire(timeout=self.timeout):
            raise RuntimeError(_ERROR)
        self.directory = None
        self.process = None
        self.pipe = None
        try:
            self.directory = tempfile.TemporaryDirectory(prefix="sqlbot-kerberos-")
            context = multiprocessing.get_context("spawn")
            self.pipe, child = context.Pipe()
            self.process = context.Process(
                target=_worker, args=(child, config, self.directory.name), daemon=True
            )
            self.process.start()
            child.close()
            self._receive()
        except BaseException:
            self.close()
            raise

    def _receive(self):
        if not self.pipe.poll(self.timeout):
            self.close()
            raise RuntimeError(_ERROR)
        try:
            ok, result = self.pipe.recv()
        except (EOFError, OSError):
            self.close()
            raise RuntimeError(_ERROR) from None
        if not ok:
            self.close()
            raise RuntimeError(result)
        return result

    def cursor(self):
        return _Cursor(self)

    def close(self):
        if self.closed:
            return
        self.closed = True
        try:
            try:
                if self.pipe is not None:
                    self.pipe.close()
            finally:
                if self.process is not None and self.process.pid is not None:
                    self.process.join(timeout=0.2)
                    if self.process.is_alive():
                        self._terminate_group(signal.SIGTERM)
                        self.process.join(timeout=2)
                    if self.process.is_alive():
                        self._terminate_group(signal.SIGKILL)
                        self.process.join()
        finally:
            try:
                if self.directory is not None:
                    self.directory.cleanup()
            finally:
                _LIMIT.release()

    def _terminate_group(self, sig):
        if hasattr(os, "killpg"):
            try:
                os.killpg(self.process.pid, sig)
                return
            except ProcessLookupError:
                pass
        if sig == signal.SIGTERM:
            self.process.terminate()
        else:
            self.process.kill()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


class _Cursor:
    def __init__(self, connection):
        self.connection = connection
        self.description = None

    def execute(self, sql):
        self.connection.pipe.send(("execute", sql))
        self.description = self.connection._receive()

    def fetchall(self):
        self.connection.pipe.send(("fetchall", None))
        return self.connection._receive()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


class KerberosPool:
    def __init__(self, config):
        self.config = config

    def connection(self):
        return KerberosConnection(self.config)
