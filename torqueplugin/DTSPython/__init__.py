"""Compatibility package for the legacy Torque exporter modules.

This keeps the old absolute imports working under Python 3 while also making
the core DTSPython symbols available from ``from DTSPython import *``.
"""

from __future__ import annotations

import sys as _sys

from . import Dts_Mesh as _Dts_Mesh
from . import Torque_Math as _Torque_Math

_sys.modules.setdefault("Dts_Mesh", _Dts_Mesh)
_sys.modules.setdefault("Torque_Math", _Torque_Math)

from .Dts_Mesh import *  # noqa: F401,F403
from .Torque_Math import *  # noqa: F401,F403

from . import Torque_Util as _Torque_Util

_sys.modules.setdefault("Torque_Util", _Torque_Util)

from .Torque_Util import *  # noqa: F401,F403

from . import Dts_Shape as _Dts_Shape

_sys.modules.setdefault("Dts_Shape", _Dts_Shape)

from .Dts_Shape import *  # noqa: F401,F403

from . import Dts_Stream as _Dts_Stream

_sys.modules.setdefault("Dts_Stream", _Dts_Stream)
