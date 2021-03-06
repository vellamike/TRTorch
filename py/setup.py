import os
import sys
import glob
import setuptools
from setuptools import setup, Extension, find_packages
from setuptools.command.build_ext import build_ext
from setuptools.command.develop import develop
from setuptools.command.install import install
from distutils.cmd import Command
from wheel.bdist_wheel import bdist_wheel

from torch.utils import cpp_extension
from shutil import copyfile, rmtree

import subprocess

dir_path = os.path.dirname(os.path.realpath(__file__))

__version__ = '0.0.2'

def build_libtrtorch_pre_cxx11_abi(develop=True, use_dist_dir=True):
    cmd = ["/usr/bin/bazel", "build"]
    cmd.append("//cpp/api/lib:libtrtorch.so")
    if develop:
        cmd.append("--compilation_mode=dbg")
    else:
        cmd.append("--compilation_mode=opt")
    if use_dist_dir:
        cmd.append("--distdir=third_party/dist_dir/x86_64-linux-gnu")
    cmd.append("--config=python")

    print("building libtrtorch")
    status_code = subprocess.run(cmd).returncode

    if status_code != 0:
        sys.exit(status_code)


def gen_version_file():
    if not os.path.exists(dir_path + '/trtorch/_version.py'):
        os.mknod(dir_path + '/trtorch/_version.py')

    with open(dir_path + '/trtorch/_version.py', 'w') as f:
        print("creating version file")
        f.write("__version__ = \"" + __version__ + '\"')

def copy_libtrtorch(multilinux=False):
    if not os.path.exists(dir_path + '/trtorch/lib'):
        os.makedirs(dir_path + '/trtorch/lib')

    print("copying library into module")
    if multilinux:
        copyfile(dir_path + "/build/libtrtorch_build/libtrtorch.so", dir_path + '/trtorch/lib/libtrtorch.so')
    else:
        copyfile(dir_path + "/../bazel-bin/cpp/api/lib/libtrtorch.so", dir_path + '/trtorch/lib/libtrtorch.so')

class DevelopCommand(develop):
    description = "Builds the package and symlinks it into the PYTHONPATH"

    def initialize_options(self):
        develop.initialize_options(self)

    def finalize_options(self):
        develop.finalize_options(self)

    def run(self):
        build_libtrtorch_pre_cxx11_abi(develop=True)
        gen_version_file()
        copy_libtrtorch()
        develop.run(self)


class InstallCommand(install):
    description = "Builds the package"

    def initialize_options(self):
        install.initialize_options(self)

    def finalize_options(self):
        install.finalize_options(self)

    def run(self):
        build_libtrtorch_pre_cxx11_abi(develop=False)
        gen_version_file()
        copy_libtrtorch()
        install.run(self)

class BdistCommand(bdist_wheel):
    description = "Builds the package"

    def initialize_options(self):
        bdist_wheel.initialize_options(self)

    def finalize_options(self):
        bdist_wheel.finalize_options(self)

    def run(self):
        build_libtrtorch_pre_cxx11_abi(develop=False)
        gen_version_file()
        copy_libtrtorch()
        bdist_wheel.run(self)

class CleanCommand(Command):
    """Custom clean command to tidy up the project root."""
    PY_CLEAN_FILES = ['./build', './dist', './trtorch/__pycache__', './trtorch/lib', './*.pyc', './*.tgz', './*.egg-info']
    description = "Command to tidy up the project root"
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        for path_spec in self.PY_CLEAN_FILES:
            # Make paths absolute and relative to this path
            abs_paths = glob.glob(os.path.normpath(os.path.join(dir_path, path_spec)))
            for path in [str(p) for p in abs_paths]:
                if not path.startswith(dir_path):
                    # Die if path in CLEAN_FILES is absolute + outside this directory
                    raise ValueError("%s is not a path inside %s" % (path, dir_path))
                print('Removing %s' % os.path.relpath(path))
                rmtree(path)

ext_modules = [
    cpp_extension.CUDAExtension('trtorch._C',
                                ['trtorch/csrc/trtorch_py.cpp'],
                                library_dirs=[
                                    dir_path + '/trtorch/lib/libtrtorch.so',
                                    dir_path + '/trtorch/lib/'
                                ],
                                libraries=[
                                    "trtorch"
                                ],
                                include_dirs=[
                                    dir_path + "/../",
                                    dir_path + "/../bazel-TRTorch/external/tensorrt/include",
                                ],
                                extra_compile_args=[
                                    "-D_GLIBCXX_USE_CXX11_ABI=0",
                                    "-Wno-deprecated-declaration",
                                ],
                                extra_link_args=[
                                    "-D_GLIBCXX_USE_CXX11_ABI=0"
                                    "-Wl,--no-as-needed",
                                    "-ltrtorch",
                                    "-Wl,-rpath,$ORIGIN/lib"
                                ],
                                undef_macros=[ "NDEBUG" ]
                            )
]

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
    name='trtorch',
    version=__version__,
    author='NVIDIA',
    author_email='narens@nvidia.com',
    url='https://nvidia.github.io/TRTorch',
    description='A compiler backend for PyTorch JIT targeting NVIDIA GPUs',
    long_description_content_type='text/markdown',
    long_description=long_description,
    ext_modules=ext_modules,
    install_requires=[
        'torch==1.5.0',
    ],
    setup_requires=[],
    cmdclass={
        'install': InstallCommand,
        'clean': CleanCommand,
        'develop': DevelopCommand,
        'build_ext': cpp_extension.BuildExtension,
        'bdist_wheel': BdistCommand,
    },
    zip_safe=False,
    license="BSD",
    packages=find_packages(),
    platform="Linux",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Environment :: GPU :: NVIDIA CUDA",
        "License :: OSI Approved :: BSD License",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: C++",
        "Programming Language :: Python",
        "Programming Language :: Python :: Implementation :: CPython",
        "Topic :: Scientific/Engineering",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Topic :: Software Development",
        "Topic :: Software Development :: Libraries"
    ],
    python_requires='>=3.6',
    include_package_data=True,
    package_data={
        'trtorch': ['lib/*.so'],
    },
    exclude_package_data={
        '': ['*.cpp', '*.h'],
        'trtorch': ['csrc/*.cpp'],
    }
)
