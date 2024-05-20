import itertools
import pathlib
import sys

import butler
from butler.runner import run


def main():
    target = pathlib.Path(sys.argv[1]).resolve()
    butler.include(target)

    for name in itertools.compress(
        run(butler.jarvis, sys.argv[2:], {}), itertools.cycle([True, False])
    ):
        print(name)
