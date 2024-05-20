import argparse
import itertools
import pathlib
import sys

import butler
from butler.runner import run


def errprint(*args, **kwargs) -> None:
    print(*args, **kwargs, file=sys.stderr)


class Logger:
    SILENT = 0
    ERROR = 1
    WARNING = 2
    INFO = 3
    PRETTY = 4
    DEBUG = 5
    TRACE = 6

    def __init__(self, level: int) -> None:
        self._level = level

    def error(self, *args, **kwargs) -> None:
        if self._level >= self.ERROR:
            errprint('ERROR:', *args, **kwargs)
        exit(1)

    def warning(self, *args, **kwargs) -> None:
        if self._level >= self.WARNING:
            errprint('WARNING:', *args, **kwargs)

    def info(self, *args, **kwargs) -> None:
        if self._level >= self.INFO:
            print(*args, **kwargs)

    def pretty(self, *args, **kwargs) -> None:
        if self._level >= self.PRETTY:
            print(*args, **kwargs)

    def debug(self, *args, **kwargs) -> None:
        if self._level >= self.DEBUG:
            print(*args, **kwargs)

    def trace(self, *args, **kwargs) -> None:
        if self._level >= self.TRACE:
            print(*args, **kwargs)


def main():
    parser = argparse.ArgumentParser(prog='butler', description='A lightweight meta build system.')
    parser.add_argument('targets', metavar='TARGET', nargs='*', help='task to be executed')
    parser.add_argument('-V', '--version', action='version', version=butler.__version__)
    group = parser.add_argument_group(title='general')
    group.add_argument(
        '-D',
        '--define',
        nargs=2,
        metavar=('KEY', 'VALUE'),
        dest='arguments',
        action='append',
        help='make KEY=VALUE available to tasks during execution. Can be given multiple times',
    )
    group.add_argument(
        '-f',
        '--file',
        action='store',
        type=pathlib.Path,
        default=pathlib.Path(
            'build.py',
            help='use FILE as the starting point for task collection. Default: ./build.py',
        ),
    )
    group.add_argument(
        '-s',
        '--silent',
        action='count',
        default=0,
        help='reduce output verbosity. Can be given multiple times',
    )
    group.add_argument(
        '-v',
        '--verbose',
        action='count',
        default=Logger.PRETTY,
        help='increase output verbosity. Can be given multiple times',
    )
    group = parser.add_argument_group(title='discovery')
    inspectors = group.add_mutually_exclusive_group()
    inspectors.add_argument(
        '--depends',
        action='store_const',
        dest='inspector',
        const='depends',
        help='list all direct dependencies for each TARGET and exit',
    )
    inspectors.add_argument(
        '--extends',
        action='store_const',
        dest='inspector',
        const='extends',
        help='list all direct dependencies for each TARGET and exit',
    )
    inspectors.add_argument(
        '--describe',
        action='store_const',
        dest='inspector',
        const='describe',
        help='print definition location and docstring of TARGET and exit',
    )
    inspectors.add_argument(
        '--graph',
        action='store_const',
        dest='inspector',
        const='graph',
        help='print each layer of mutually non-dependent TARGETs and exit',
    )
    args = parser.parse_args(sys.argv[1:])
    print(args._get_kwargs())

    logger = Logger(args.verbose - args.silent)

    main_file: pathlib.Path = args.file.resolve()
    if not main_file.is_file():
        logger.error('No such file:', main_file)
    butler.include(main_file)

    def inspect(inspector: str | None, targets: list[str]) -> None:
        if not targets:
            targets = [task.name for task in butler.jarvis]
        targets = sorted(targets)
        match inspector:
            case 'depends':
                logger.pretty('Direct dependencies in the form "<target>: <dep> ...":')
                for t in targets:
                    deps = butler.jarvis._graph.successors(butler.jarvis._by_name[t])
                    deps = sorted([d.name for d in deps])
                    print(' ', f'{t}:', *deps)
            case 'extends':
                logger.pretty('Direct extensions in the form "<target>: <dep> ...":')
                for t in targets:
                    exts = butler.jarvis._graph.predecessors(butler.jarvis._by_name[t])
                    exts = sorted([d.name for d in exts])
                    print(' ', f'{t}:', *exts)
            case 'describe':
                if len(targets) > 1:
                    logger.error('Can only describe exactly one target')
                for t in targets:
                    action = butler.jarvis[t].action
                    code = action.__code__
                    print(f'{t}: {code.co_filename}:{code.co_firstlineno}')
                    print(action.__doc__)
            case 'graph':
                logger.pretty('Target hierarchy (starting at roots).')
                for layer in butler.jarvis._layers(targets):
                    print(' ', *(task.name for task in layer))
        exit()

    if args.inspector is not None:
        inspect(args.inspector, args.targets)

    if not args.targets:
        targets = sorted([task.name for task in butler.jarvis])
        start_column = max(len(target) for target in targets)
        logger.pretty('Available targets:')
        for target in targets:
            action = butler.jarvis[target].action
            space = ' ' * (start_column - len(target))
            doctitle = ' '.join(itertools.takewhile(bool, action.__doc__.splitlines()))
            logger.info(' ', target, space, doctitle)
        exit()

    try:
        for name in itertools.compress(
            run(butler.jarvis, args.targets, {}), itertools.cycle([True, False])
        ):
            print(name)
    except Exception as e:
        logger.error(e)
