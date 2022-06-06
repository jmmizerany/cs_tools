import itertools
import pathlib
import zipfile
import shutil
import os

import nox_poetry as nox


ON_GITHUB = "GITHUB_ACTIONS" in os.environ
PY_VERSIONS = [
    "3.6.8",
    "3.7", "3.8", "3.9", "3.10"
]
DIST = pathlib.Path(__file__).parent / "dist"
DIST_PKGS = DIST / "pkgs"
REQS_TXT = DIST_PKGS / 'requirements.txt'
SUPPORTED_PLATFORM_MATRIX = {
    # fmt: off
    # PEP425: Compatibility Tags for Built Distributions
    "windows": ("win_amd64", ),

    # "macosx_12_x86_64",  # Moneterey [released: 2021.10.25]
    # "macosx_11_x86_64",  # Big Sur   [released: 2020.11.12]
    # Catalina (10.15) ----------------------> [EOL tbd]
    # Mojave   (10.14) ----------------------> [EOL 2021.10.25]
    "mac": ("macosx_10_15_x86_64", "macosx_10_14_x86_64"),

    # PEP600: manylinux_x_y_<arch> based on glibc>=x.y  (future-proofed)
    # PEP599: manylinux2014_<arch> --> CentOS7 [EOL 2024.06.30]
    # PEP571: manylinux2010_<arch> --> CentOS6 [EOL 2020.11.30]
    # PEP513: manylinux1_<arch> -----> CentOS5 [EOL 2017.03.31]
    "linux": (
        "manylinux_2_17_x86_64", "manylinux2014_x86_64",  # alias, strict
        "manylinux_2_12_x86_64", "manylinux2010_x86_64",  # alias, strict
        "manylinux_2_5_x86_64", "manylinux1_x86_64",      # alias, strict
    ),
    # fmt: on
}


def zip_it(dir_: pathlib.Path, *, name: str, path: str = None, new: bool = True) -> None:
    """
    """
    if path is not None and path.endswith('/'):
        path = pathlib.Path(path).name

    if new:
        pathlib.Path(name).unlink(missing_ok=True)

    with zipfile.ZipFile(name, "a", zipfile.ZIP_DEFLATED) as zip_:
        for file in dir_.iterdir():
            arcname = path if path is None else f'{path}/{file.name}'

            if file.name == '__pycache__':
                continue
            if arcname in zip_.namelist():
                continue

            zip_.write(file, arcname=arcname)


@nox.session(python=PY_VERSIONS, reuse_venv=not ON_GITHUB)
def vendor_packages(session):
    """
    Build offline distributable installer.

    For this to be truly effective, the builder must have access to all
    python versions in the PY_VERSIONS constraint. Consider using pyenv
    or docker to build.
    """
    # TODO: use argparse for the following args
    # --silent         :: defaults to ON_GITHUB
    # --ensure-install :: run the poetry-install step
    # --no-cleanup     :: don't remove files

    # session.run("poetry", "install", external=True, silent=not ON_GITHUB)
    session.run(
        # fmt: off
        "poetry", "export",
        "-f", "requirements.txt",
        "--output", REQS_TXT.as_posix(),
        "--without-hashes",
        external=True,
        silent=not ON_GITHUB
        # fmt: on
    )

    session.run("poetry", "build", "--format", "wheel", external=True, silent=not ON_GITHUB)
    WHL_FILE = pathlib.Path(next(DIST_PKGS.parent.glob("cs_tools*.whl")))

    for platform, platforms in SUPPORTED_PLATFORM_MATRIX.items():
        dest = DIST_PKGS / platform

        # session.log(f'cleaning {dest}..')
        # shutil.rmtree(dest, ignore_errors=True)

        # download our dependencies
        # - since poetry found and resolved our dependencies, --no-deps is fine to use
        session.run(
            # fmt: off
            "pip", "download",
            "-r", REQS_TXT.as_posix(),
            "--dest", dest.as_posix(),
            "--no-cache-dir",
            "--no-deps",
            *itertools.chain.from_iterable(["--platform", p] for p in platforms),
            silent=not ON_GITHUB
            # fmt: on
        )

        session.log(f'adding {WHL_FILE.name} to {platform}/')
        shutil.copyfile(WHL_FILE, dest / WHL_FILE.name)

        if not ON_GITHUB:
            session.log(f'zipping {platform}/ for distribution..')
            _, version, *_ = WHL_FILE.stem.split('-')
            archive = DIST / f"{platform}-cs_tools-{version}.zip"
            zip_it(dest, name=archive, path='pkgs/')
            zip_it(DIST / 'bootstrap', name=archive, path='bootstrap/', new=False)
            # shutil.rmtree(dest, ignore_errors=True)

    # if not ON_GITHUB:
    #     session.log('cleaning temporary files..')
    #     WHL_FILE.unlink()
    #     REQS_TXT.unlink()


# @nox.session(python=PY_VERSIONS, reuse_venv=not ON_GITHUB)
# def version_bump(session):
#     # TODO: use argparse for the following args
#     # --major          :: False
#     # --minor          :: False
#     # --patch          :: False
#     # --beta           :: False
#     session.run("poetry", "version")


@nox.session(python=PY_VERSIONS, reuse_venv=not ON_GITHUB)
def tests(session):
    """
    Ensure we test our code.
    """
    session.run("poetry", "install", external=True)
    session.run("ward")


# @nox.session(python=PY_VERSIONS, reuse_venv=not ON_GITHUB)
# def code_quality(session):
#     session.run("poetry", "install", external=True)
