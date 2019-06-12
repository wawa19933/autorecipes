"""A generic Conan recipe for CMake projects."""

import importlib.util
import os
from pathlib import Path
import subprocess as sp
import typing as t

from conans import CMake, ConanFile  # type: ignore

from autorecipes.descriptors import cached_property, classproperty


class CMakeAttributes:
    """A descriptor that lazily loads attributes from the CMake configuration."""

    def __init__(self):
        self.attrs = None

    def __get__(self, obj: object, typ: type = None) -> t.Mapping[str, t.Any]:
        if self.attrs is None:
            source_dir = Path(os.getcwd())
            build_dir = source_dir / '.conan_cmake'
            build_dir.mkdir(parents=True, exist_ok=True)
            sp.run(['conan', 'install', source_dir], cwd=build_dir)
            # It would save us some time if the CMake CLI could configure
            # without generating.
            # TODO: Use scm attribute to copy code?
            # TODO: Append call to configure_file to end of CMakeLists.txt,
            # temporarily.
            sp.run(
                [
                    'cmake',
                    '-DCMAKE_TOOLCHAIN_FILE=conan_paths.cmake',
                    source_dir,
                ],
                cwd=build_dir,
            )

            spec = importlib.util.spec_from_file_location( # type: ignore
                'conan_attrs', build_dir / 'conan_attrs.py'
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)  # type: ignore
            self.attrs = module
        return self.attrs

    def __matmul__(self, key):
        """Create a descriptor that lazily returns one attribute."""

        @classproperty
        def f(cls):
            # We are assuming that the :class:`CMakeAttributes` descriptor
            # will be named ``attrs``.
            return getattr(cls.attrs, key)  # type: ignore

        f.__name__ = key
        return f


class CMakeConanFile(ConanFile):
    """A base class for Conan recipes for CMake projects."""

    attrs = CMakeAttributes()

    name = attrs @ 'name'
    version = attrs @ 'version'
    description = attrs @ 'description'
    homepage = attrs @ 'homepage'
    url = attrs @ 'url'

    # TODO: ConanAttributes like requires, build_requires, generators
    # Is there a facility in ``conans`` for parsing ``conanfile.txt``?
    # For now, just hard code.
    generators = 'cmake_find_package', 'cmake_paths'
    build_requires = ['doctest/2.3.1@bincrafters/stable']

    scm = {
        'type': 'git',
        'url': 'auto',
        'revision': 'auto',
    }

    settings = 'arch', 'os', 'compiler', 'build_type'
    options = {'shared': [True, False]}
    default_options = {'shared': False}

    @cached_property
    def cmake(self) -> CMake:  # pylint: disable=missing-docstring
        cmake = CMake(self)
        cmake.configure()
        return cmake

    def build(self):
        self.cmake.build()  # pylint: disable=no-member

    def package(self):
        self.cmake.install()  # pylint: disable=no-member

    def package_info(self):
        # TODO: dependency options from ``conanfile.txt``.
        # TODO
        pass