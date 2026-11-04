"""Independent native grant signing for shared scientific and I/O tests."""

import hashlib
import hmac
import os
from pathlib import Path
import time

from services.utility_helpers import FILE_GRANT_VERSION


def sign_grant(secret, path, access, *, expires=None):
    resolved = Path(path).resolve()
    expires = int(time.time()) + 60 if expires is None else expires
    identity_path = resolved if access == "read" else resolved.parent
    if os.name == "nt":
        from services.windows_secure_fs import (
            WINDOWS_FILE_GRANT_VERSION,
            canonicalize_windows_path,
            pin_windows_path,
        )

        resolved = canonicalize_windows_path(str(resolved))
        with pin_windows_path(identity_path, directory=access == "write") as pinned:
            identity = pinned.identity
        version = WINDOWS_FILE_GRANT_VERSION
        device, inode = identity.volume_hex, identity.file_id_hex
    else:
        version = FILE_GRANT_VERSION
        selected = identity_path.stat()
        device, inode = str(selected.st_dev), str(selected.st_ino)
    payload = f"{version}\0{access}\0{expires}\0{resolved}\0{device}\0{inode}"
    digest = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return f"{version}.{expires}.{device}.{inode}.{digest}"


def rename_pinned(source, destination):
    """POSIX permits pinned renames; Windows must block them with sharing denial."""
    if os.name == "nt":
        try:
            source.rename(destination)
        except PermissionError as error:
            assert error.winerror in {5, 32}, error
        else:
            raise AssertionError("Pinned Windows input was renameable")
        return False
    source.rename(destination)
    return True
