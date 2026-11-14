"""
计入所有使用的库之协议展示
"""


def main():

    from .logger import logger

    from TrimLog import __version__ as TrimlogVersion
    from uvicorn import __version__ as UvicornVersion
    from pydantic import __version__ as PydanticVersion
    from tomli_w import __version__ as TomliWVersion
    from fastapi import __version__ as FastAPIVersion

    logger.license_shower(
        lib_name="Uvicorn",
        license_name="BSD-3-Clause license",
        license_line="Copyright © 2017-present, Encode OSS Ltd. All rights reserved.",
        lib_version=UvicornVersion,
        include_startline=True,
        include_endline=False,
    )

    logger.license_shower(
        lib_name="pydantic",
        license_name="MIT License",
        license_line="Copyright (c) 2017 to present Pydantic Services Inc. and individual contributors.",
        lib_version=PydanticVersion,
        include_startline=True,
        include_endline=False,
    )

    logger.license_shower(
        lib_name="tomli_w",
        license_name="MIT License",
        license_line="Copyright (c) 2021 Taneli Hukkinen",
        lib_version=TomliWVersion,
        include_startline=True,
        include_endline=False,
    )

    logger.license_shower(
        lib_name="FastAPI",
        license_name="MIT License",
        license_line="Copyright (c) 2018 Sebastián Ramírez",
        lib_version=FastAPIVersion,
        include_startline=True,
        include_endline=False,
    )

    logger.license_shower(
        lib_name="TrimLog",
        license_name="Apache License, Version 2.0",
        license_line="版权所有 © 2022-2026 FedDragon1, bgArray, Eilles",
        lib_version=TrimlogVersion,
        include_startline=True,
        include_endline=True,
    )


if __name__ == "__main__":
    main()
