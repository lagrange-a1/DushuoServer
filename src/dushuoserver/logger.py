"""度朔服务端的日志模块"""


from TrimLog import object_constants, logger, log__init__, __version__ as TrimlogVersion
from . import __appname__, __version__

# 调试模式，在正式发布之前须要关闭
DEBUGGING = True

osc = object_constants.ObjectStateConstant(
    is_debugging=DEBUGGING,
    logging_project_name=__appname__,
    logging_project_version=__version__,
    is_this_a_release=not DEBUGGING,
    logging_exit_exec=lambda x: print(
        "[EXTREME CRITICAL ERROR] 运行时严重错误（`{}`:`{}`），本程序无法继续运行，请查阅日志文件：`{}`，特别关注以下错误信息：\n{}".format(
            x.exception_type, x.exception_value, x.log_file_path, x.message_content
        )
    ),
)
# print(osc.exit_execution)
osc.set_console(logger.console)

log__init__(osc, False)

logger.is_logging = True
logger.suffix = ".dss"
logger.is_tips = True
logger.printing = not osc.is_release

logger.baseinfo_shower()

logger.license_shower(
    lib_name="TrimLog",
    license_name="Apache License, Version 2.0",
    license_line="版权所有 © 2022-2026 FedDragon1, bgArray, Eilles",
    lib_version=TrimlogVersion,
    include_startline=True,
)
