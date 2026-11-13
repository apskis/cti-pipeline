"""
The CTI house style, forwarded from genelabs-cti-documentation.

This used to be a second full copy of that module. It now loads the one copy, so
the two skills cannot drift apart, and the colours and logo come from the
company's brand file like every other builder.
"""
import importlib.util
import os

_SOURCE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..",
                       "genelabs-cti-documentation", "scripts", "genelabs_style.py")
# Loaded under its own name: this file is also called genelabs_style, so a plain
# import would find itself.
_spec = importlib.util.spec_from_file_location("_cti_house_style", _SOURCE)
_style = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_style)

globals().update({k: v for k, v in vars(_style).items() if not k.startswith("__")})
