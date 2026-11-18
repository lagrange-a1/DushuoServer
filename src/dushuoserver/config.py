"""度朔服务端配置定义。"""

from sys import version_info as python_version, argv as cli_args
from pathlib import Path
from typing import Any, Annotated, Literal

from pydantic import BaseModel, Field, field_serializer, field_validator

import tomli_w

if python_version >= (3, 11):
    import tomllib
else:
    import tomli as tomllib  # pyright: ignore[reportMissingImports]


class DeshuoConfigBaseModel(BaseModel):

    def update(self, key: str, value: Any):
        """更新运行时参数。"""
        if key in self.model_fields_set:  # 检测字段是否存在
            if isinstance(value, value_type := getattr(self, key).__class__):
                setattr(self, key, value)
                return
            raise TypeError("参数`{}`不符合`{}`的类型要求。".format(key, value_type))
        raise ValueError("`{}`不是一个运行时参数")


class UvicronConfig(DeshuoConfigBaseModel):
    """Uvicorn 配置"""

    workers: int = 1
    """Uvicorn 工作进程数"""
    hot_reload: bool = False
    """是否启用 Uvicorn 热重载"""
    access_log: bool = True
    """是否启用 Uvicorn 访问日志"""


class RuntimeConfig(DeshuoConfigBaseModel):
    """运行时参数配置"""

    activity_cache_duration: int = 86400
    """客户端活动消息的缓存时长（秒）"""
    death_countdown: int = 86400  # 死亡倒计时
    """死亡判定倒计时（秒）"""
    execution_task: str = ""
    """最终任务执行命令"""
    message_cache_duration: int = 3600
    """短报文消息缓存时间（秒）"""
    pairing_window_time: int = 300
    """配对窗口时长（秒）"""
    signature_time_tolerance: int = 300
    """签名时间容差（秒）"""


class ServerConfig(DeshuoConfigBaseModel):
    """服务端配置。"""

    # 服务参数
    host_address: str = "0.0.0.0"
    """监听地址"""
    host_port: int = 18470
    """监听端口"""
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO", description="全局日志等级"
    )
    """全局日志等级"""
    db_path: Path = Field(
        default=Path("dushuodb.sqlite3"), description="数据库文件路径"
    )
    """数据库文件路径"""
    demo_mode: bool = Field(default=False, description="是否作为演示服务器启用")

    uvicron: UvicronConfig = Field(default_factory=UvicronConfig)
    """Uvicorn 配置"""
    runtime: RuntimeConfig = Field(default_factory=RuntimeConfig)
    """运行时参数配置"""

    # 校验 log_level 字段时（读入时），进行转换
    @field_validator("log_level", mode="before")
    @staticmethod
    def _normalize_log_level(v: object) -> object:
        if isinstance(v, str):
            v = v.upper()
        if v in ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"):
            return v
        else:
            print(
                "【***】传入的日志等级参数`{}`无效，现已切换为`DEBUG`等级。".format(v)
            )
            return "DEBUG"

    # 序列化 db_path 字段时（输出时），进行转换
    @field_serializer("db_path")
    def serialize_db_path(self, value: Path) -> str:
        return str(value)

    @classmethod
    def load_config(cls, config_file: Path | str) -> ServerConfig:
        with open(config_file, "rb") as f:
            return cls.model_validate(tomllib.load(f))

    def save_config(self, config_file: Path | str) -> None:
        with open(config_file, "wb") as f:
            tomli_w.dump(self.model_dump(), f)

    def dump_as_toml(self) -> str:
        return tomli_w.dumps(self.model_dump())


config = ServerConfig()


if __name__ == "__main__":

    if cli_args:
        print("【***】加载配置文件：", cli_args[1])
        config = ServerConfig.load_config(cli_args[1])
    # config.runtime.update("death_countdown", 5454)

    print(config.dump_as_toml())
    print(config.model_dump())

    # print(config.runtime.model_dump())
