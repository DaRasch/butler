# Butler

A lightweight meta build system for complex projects.

Butler is a build system that is not focused on a specific language. It instead helps you in orchestrating the various build systems, packaging systems and distribution methods often present in very large projects.

## A basic example

```python
# build.py
import butler
from butler import jarvis # Your butler is named jarvis

# The actual implementation of these stubs is up to the user. For now let us
# assume that my_buildsystem.py contains two functions with signatures:
#   check(source_dir: Path, target_dir: Path) -> bool: ...
#   compile(source_dir: pathlib.Path, target_dir: pathlib.Path) -> None: ...
my_buildsystem = butler.include('buildsupport/my_buildsystem.py')

# Butler exposes some useful information about the build context.
ctx = butler.context

build_dir = ctx.cmdlineargs.get('builddir', ctx.cwd() / 'build')
source_dir = butler.cwd() / 'src'

@jarvis.task()
def check_build():
    '''Check, if files changed since the last build.

    Tasks without dependencies are always executed as butler has no way to know,
    if they need to be executed or not.'''
    return my_buildsystem.check(source_dir, target_dir)

@jarvis.task(depends=[check_build])
def build():
    '''Compile the sources into a target artefact.'''

    my_buildsystem.compile(source_dir, target_dir)
```

```bash
butler build
```

## Features

### Lightweight

Concentrating on the cross-sectional functionalities of a build system allows it to stay small and easily understandable.

### Library, not language

Being a library instead of its own language - be that an actual programming language (e.g. make) or an adhoc language embedded in a decalartive config file format (e.g. ant) - makes for a low barrier of entry for anyone who knows some python and allows users to leverage the full power of the python ecosystem.

Another benefit of the library approach is that it does not require a custom language server or other dev tools. All the tools already exist for python.

### Discoverable

Butler is designed to be easily introspectable via its commandline interface. Annoyed by having to read through dozens of task definition files to figure out the execution order for a given set of tasks? No more!

```bash
butler --graph mytask myothertask
```

Which tasks depend on a given task?

```bash
butler --extends mytask
```

What does a task do and where is it defined?

```bash
butler --describe mytask
```

What tasks are actually available?

```bash
butler
```

### Powerfull task dependency resolution

Any build system worth its salt helps you manage the dependencies between the various tasks in the build process.

```python
# build.py
from butler import jarvis

@jarvis.task()
def validate(): ...

@jarvis.task(depends=[validate])
def build(): ...

@jarvis.task(depends=[build])
def test(): ...

@jarvis.task(depends=[build])
def package(): ...

@jarvis.task(depends=[test, package])
def dist(): ...
```

#### Distribution and inversion

Butler also allows distributing tasks across multiple files and it also offers inverse dependency declarations.

```python
# build.py
import butler
from butler import jarvis

butler.include('subproject_a/build.py')
butler.include('subproject_bc/build.py')

# Using the interface
interface = butler.include('shared/interface.py')

@jarvis.task(depends=[interface.build])
def package(): ...
```

```python
# shared/interface.py
from butler import jarvis

# Interface
@jarvis.task()
def build(): ...

@jarvis.task()
def clean(): ...
```

```python
# subproject_a/build.py
import butler
from butler import jarvis

interface = butler.include('../shared/interface.py')

class ProjectA:
    @jarvis.task(extends=[interface.build])
    def build(): ...

    @jarvis.task(extends=[interface.clean])
    def clean(): ...
```

```python
# subproject_bc/build.py
import butler
from butler import jarvis

interface = butler.include('../shared/interface.py')

class ProjectB:
    @jarvis.task(extends=[interface.build])
    def build(): ...

class ProjectC:
    @jarvis.task(extends=[interface.build])
    def build(): ...
```

#### [WIP] Data dependencies

...
