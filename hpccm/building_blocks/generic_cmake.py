# Copyright (c) 2019, NVIDIA CORPORATION.  All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# pylint: disable=invalid-name, too-few-public-methods
# pylint: disable=too-many-instance-attributes

"""Generic cmake building block"""

from __future__ import absolute_import
from __future__ import unicode_literals
from __future__ import print_function

import posixpath
import re

import hpccm.templates.CMakeBuild
import hpccm.templates.downloader
import hpccm.templates.envvars
import hpccm.templates.ldconfig
import hpccm.templates.rm

from hpccm.building_blocks.base import bb_base
from hpccm.primitives.comment import comment
from hpccm.primitives.copy import copy
from hpccm.primitives.environment import environment
from hpccm.primitives.shell import shell
from hpccm.toolchain import toolchain

class generic_cmake(bb_base, hpccm.templates.CMakeBuild,
                    hpccm.templates.downloader, hpccm.templates.envvars,
                    hpccm.templates.ldconfig, hpccm.templates.rm):
    """The `generic_cmake` building block downloads, configures,
    builds, and installs a specified CMake enabled package.

    # Parameters

    branch: The git branch to clone.  Only recognized if the
    `repository` parameter is specified.  The default is empty, i.e.,
    use the default branch for the repository.

    build_directory: The location to build the package.  The default
    value is a `build` subdirectory in the source code location.

    build_environment: Dictionary of environment variables and values
    to set when building the package.  The default is an empty
    dictionary.

    check: Boolean flag to specify whether the `make check` step
    should be performed.  The default is False.

    cmake_opts: List of options to pass to `cmake`.  The default value
    is an empty list.

    commit: The git commit to clone.  Only recognized if the
    `repository` parameter is specified.  The default is empty, i.e.,
    use the latest commit on the default branch for the repository.

    devel_environment: Dictionary of environment variables and values,
    e.g., `LD_LIBRARY_PATH` and `PATH`, to set in the development
    stage after the package is built and installed.  The default is an
    empty dictionary.

    directory: The source code location.  The default value is the
    basename of the downloaded package.  If the value is not an
    absolute path, then the temporary working directory is prepended.

    environment: Boolean flag to specify whether the environment
    should be modified (see `devel_environment` and
    `runtime_environment`).  The default is True.

    install: Boolean flag to specify whether the `make install` step
    should be performed.  The default is True.

    ldconfig: Boolean flag to specify whether the library directory
    should be added dynamic linker cache.  The default value is False.

    libdir: The path relative to the install prefix to use when
    configuring the dynamic linker cache.  The default value is `lib`.

    make: Boolean flag to specify whether the `make` step should be
    performed.  The default is True.

    postinstall: List of shell commands to run after running 'make
    install'.  The working directory is the install prefix.  The
    default is an empty list.

    preconfigure: List of shell commands to run prior to running
    `cmake`.  The working directory is the source code location.  The
    default is an empty list.

    prefix: The top level install location.  The default value is
    `/usr/local`. It is highly recommended not to use this default and
    instead set the prefix to a package specific directory.

    recursive: Initialize and checkout git submodules. `repository` parameter
    must be specified. The default is False.

    repository: The git repository of the package to build.  One of
    this paramter or the `url` parameter must be specified.

    _run_arguments: Specify additional [Dockerfile RUN arguments](https://github.com/moby/buildkit/blob/master/frontend/dockerfile/docs/experimental.md) (Docker specific).

    runtime_environment: Dictionary of environment variables and
    values, e.g., `LD_LIBRARY_PATH` and `PATH`, to set in the runtime
    stage.  The default is an empty dictionary.

    toolchain: The toolchain object.  This should be used if
    non-default compilers or other toolchain options are needed.  The
    default is empty.

    url: The URL of the tarball package to build.  One of this
    parameter or the `repository` parameter must be specified.

    # Examples

    ```python
    generic_cmake(cmake_opts=['-D CMAKE_BUILD_TYPE=Release',
                              '-D CUDA_TOOLKIT_ROOT_DIR=/usr/local/cuda',
                              '-D GMX_BUILD_OWN_FFTW=ON',
                              '-D GMX_GPU=ON',
                              '-D GMX_MPI=OFF',
                              '-D GMX_OPENMP=ON',
                              '-D GMX_PREFER_STATIC_LIBS=ON',
                              '-D MPIEXEC_PREFLAGS=--allow-run-as-root'],
                  directory='gromacs-2018.2',
                  prefix='/usr/local/gromacs',
                  url='https://github.com/gromacs/gromacs/archive/v2018.2.tar.gz')
    ```

    ```python
    generic_cmake(branch='v0.8.0',
                  cmake_opts=['-D CMAKE_BUILD_TYPE=RELEASE',
                              '-D QUDA_DIRAC_CLOVER=ON',
                              '-D QUDA_DIRAC_DOMAIN_WALL=ON',
                              '-D QUDA_DIRAC_STAGGERED=ON',
                              '-D QUDA_DIRAC_TWISTED_CLOVER=ON',
                              '-D QUDA_DIRAC_TWISTED_MASS=ON',
                              '-D QUDA_DIRAC_WILSON=ON',
                              '-D QUDA_FORCE_GAUGE=ON',
                              '-D QUDA_FORCE_HISQ=ON',
                              '-D QUDA_GPU_ARCH=sm_70',
                              '-D QUDA_INTERFACE_MILC=ON',
                              '-D QUDA_INTERFACE_QDP=ON',
                              '-D QUDA_LINK_HISQ=ON',
                              '-D QUDA_MPI=ON'],
                  prefix='/usr/local/quda',
                  repository='https://github.com/lattice/quda.git')
    ```

    """

    def __init__(self, **kwargs):
        """Initialize building block"""

        super(generic_cmake, self).__init__(**kwargs)

        self.__build_directory = kwargs.get('build_directory', 'build')
        self.__build_environment = kwargs.get('build_environment', {})
        self.__check = kwargs.get('check', False)
        self.cmake_opts = kwargs.get('cmake_opts', [])
        self.__directory = kwargs.get('directory', None)
        self.environment_variables = kwargs.get('devel_environment', {})
        self.__install = kwargs.get('install', True)
        self.__libdir = kwargs.get('libdir', 'lib')
        self.__make = kwargs.get('make', True)
        self.__postinstall = kwargs.get('postinstall', [])
        self.__preconfigure = kwargs.get('preconfigure', [])
        self.__recursive = kwargs.get('recursive', False)
        self.__run_arguments = kwargs.get('_run_arguments', None)
        self.runtime_environment_variables = kwargs.get('runtime_environment', {})
        self.__toolchain = kwargs.get('toolchain', toolchain())

        self.__commands = [] # Filled in by __setup()
        self.__wd = '/var/tmp' # working directory

        # Construct the series of steps to execute
        self.__setup()

        # Fill in container instructions
        self.__instructions()

    def __instructions(self):
        """Fill in container instructions"""

        if self.url:
            self += comment(self.url, reformat=False)
        elif self.repository:
            self += comment(self.repository, reformat=False)
        self += shell(_arguments=self.__run_arguments,
                      commands=self.__commands)
        self += environment(variables=self.environment_step())

    def __setup(self):
        """Construct the series of shell commands, i.e., fill in
           self.__commands"""

        # Get source
        self.__commands.append(self.download_step(recursive=self.__recursive,
                                                  wd=self.__wd))

        # directory containing the unarchived package
        if self.__directory:
            if posixpath.isabs(self.__directory):
                self.src_directory = self.__directory
            else:
                self.src_directory = posixpath.join(self.__wd,
                                                    self.__directory)

        # Preconfigure setup
        if self.__preconfigure:
            # Assume the preconfigure commands should be run from the
            # source directory
            self.__commands.append('cd {}'.format(self.src_directory))
            self.__commands.extend(self.__preconfigure)

        # Configure
        build_environment = []
        if self.__build_environment:
            for key, val in sorted(self.__build_environment.items()):
                build_environment.append('{0}={1}'.format(key, val))
        self.__commands.append(self.configure_step(
            build_directory=self.__build_directory,
            directory=self.src_directory, environment=build_environment,
            toolchain=self.__toolchain))

        # Build
        if self.__make:
            self.__commands.append(self.build_step())

        # Check the build
        if self.__check:
            self.__commands.append(self.build_step(target='check'))

        # Install
        if self.__install:
            self.__commands.append(self.build_step(target='install'))

        if self.__postinstall:
            # Assume the postinstall commands should be run from the
            # install directory
            self.__commands.append('cd {}'.format(self.prefix))
            self.__commands.extend(self.__postinstall)

        # Set library path
        if self.ldconfig:
            self.__commands.append(self.ldcache_step(
                directory=posixpath.join(self.prefix, self.__libdir)))

        # Cleanup
        remove = [self.src_directory]
        if self.url:
            remove.append(posixpath.join(self.__wd,
                                         posixpath.basename(self.url)))
        if self.__build_directory:
            if posixpath.isabs(self.__build_directory):
                remove.append(self.__build_directory)
        self.__commands.append(self.cleanup_step(items=remove))


    def runtime(self, _from='0'):
        """Generate the set of instructions to install the runtime specific
        components from a build in a previous stage.

        # Examples

        ```python
        g = generic_cmake(...)
        Stage0 += g
        Stage1 += g.runtime()
        ```
        """
        if self.prefix:
            instructions = []
            if self.url:
                instructions.append(comment(self.url, reformat=False))
            elif self.repository:
                instructions.append(comment(self.repository, reformat=False))
            instructions.append(copy(_from=_from, src=self.prefix,
                                     dest=self.prefix))
            if self.ldconfig:
                instructions.append(shell(commands=[self.ldcache_step(
                    directory=posixpath.join(self.prefix, self.__libdir))]))
            if self.runtime_environment_variables:
                instructions.append(environment(
                    variables=self.environment_step(runtime=True)))
            return '\n'.join(str(x) for x in instructions)
        else: # pragma: no cover
            return
