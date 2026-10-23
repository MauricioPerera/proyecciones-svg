"""Four different-radius concurrent cylindrical bores, projected directly to SVG."""
from __future__ import annotations

import sys

import taladros_cruzados as base
from tres_taladros import ThreeBores, decorate


class FourBores(ThreeBores):
    """Cuatro taladros de diámetros distintos, ejes concurrentes y ocho bocas separadas."""
    type_name='quadruple_crossed_bores'
    count=4


if __name__=='__main__':
    sys.exit(base.main(constructor=FourBores,decorator=decorate))
