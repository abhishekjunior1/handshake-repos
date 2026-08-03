"""Launches pytest with site initialisation disabled.

Invoked as ``python3 -S /tests/run_pytest.py <pytest args...>`` from test.sh,
which owns the argument list. Skipping site.py means a ``sitecustomize`` or
``usercustomize`` module planted in site-packages never executes, so agent code
cannot monkey-patch the test runner into reporting passes. site-packages is put
back on sys.path explicitly — the path comes from sysconfig, which is stdlib and
therefore unaffected by the same trick.
"""

import sys
import sysconfig

for entry in (sysconfig.get_paths()["purelib"], sysconfig.get_paths()["platlib"]):
    if entry not in sys.path:
        sys.path.append(entry)

from pytest import console_main  # noqa: E402  (import must follow the path fix)

sys.argv = ["pytest", *sys.argv[1:]]

sys.exit(console_main())
