## 概览 Overview

度朔(Dushuo) 是一个用于通过监控数字活动来进行生死判断的系统，使用 Python 语言进行开发，并使用 FastAPI 框架运行 Web 服务。

当前项目 度朔·服务端(Dushuo Server) 是用以管理各个客户端上报的数字活动情况、分发客户端密钥、客户端短报文通信、以及最终任务执行等功能。

## 功能流程 Workflow

在设计上，服务端有以下功能：

0.  开始死亡判定倒计时
1.  接收客户端传来的数字活动信息，重置倒计时
2.  响应客户端状态请求，返回当前服务端状态信息
3.  相应客户端配置修改请求，修改服务端配置
4.  倒计时结束时，执行最终任务
5.  分发配对密钥和服务端信息

服务端应有以下配置：

0.  服务开放端口【不可由客户端修改】
1.  数字活动信息存储持续时间
2.  死亡判定倒计时时间
3.  最终任务执行脚本
4.  二维码链接开放窗口时间
5.  短报文缓存存续时间

服务端的完整执行流程如下：

1.  服务端启动
2.  开放一个链接（该链接在窗口时间过后关闭），提供：
    - 移动端扫码配对二维码，该二维码包含服务端地址与配对密钥
    - 桌面端配置码，为编码后的服务端地址与配对密钥
3.  侦听服务端口，若：
    - 接收到数字活动信息，则计入数据库并重置倒计时
    - 接收到状态请求，则返回当前服务端状态信息
    - 接收到配置修改请求，则按需修改服务端配置
    - 密钥不匹配，则拒绝请求
    - 接收到短报文请求时，若传入设备尚未获取当前消息，则：
        - 若内容为空，则为获取当前消息。若缓存中存在消息，则返回消息
        - 若内容为空，且缓存中无消息，则返回空
        - 若内容不为空，且缓存中无消息，则设置消息内容。
        - 若内容不为空，且缓存中存在消息，则删除缓存消息（不设置消息内容）。
4.  不断倒计时
5.  倒计时结束，执行最终任务


## 功能命令 Common Commands

- 安装依赖：`uv sync`
- 启动服务：`python src/main.py`
- 直接使用 Uvicorn 启动：`uvicorn dushuoserver.app:app --app-dir src --host 0.0.0.0 --port 8000`
- 代码格式化：`black src`

## 代码架构 Architecture

项目入口为 `src/main.py`

## 开发备注 Development Notes

### 新功能 Adding New Features

- 新增接口时，优先在 `src/dushuoserver/service/routers_*.py` 中添加路由。
- 业务逻辑应放在 `src/dushuoserver/services.py` 或独立服务模块中。
- 数据库访问应集中在 `src/dushuoserver/database.py`。
- 配置默认值与可修改项应在 `src/dushuoserver/config.py` 中维护。
- 请求与响应模型应放在 `src/dushuoserver/schemas.py`。
- 新增或修改接口后，同步更新 `docs/API-Reference.md`。

### 测试 Testing

- 当前项目暂无自动化测试，提交前至少运行 `python -m compileall src`。
- 建议使用 `pytest` 与 FastAPI `TestClient` 编写接口测试。
- 手动测试时，可通过 `GET /health`、`GET /`、`GET /api/status` 等接口验证服务。

### 代码风格 Code Style

1. 使用 [Black](https://github.com/psf/black) 风格格式化代码
2. 使用四空格而非制表符缩进
3. 使用 `PascalCase` 命名类
4. 使用 `snake_case` 命名变量、函数
5. 使用 `UPPER_CASE` 命名常量
6. 使用如下的风格书写代码行间文档、文档和代码注释须为汉语：

```python
class ClassName:
    """
    类描述
    """

    attribute_name = "value"
    """类属性描述"""

    def function_name(self, arg1, arg2):
        """
        函数功能描述
        
        参数
        ====
        arg1 : type
            参数功能描述
        arg2 : type
            可以为多行
        
        返回
        ====
        返回值类型
            返回值功能描述
        
        抛出（如有）
        ====
        异常类型
            异常功能描述
        """
        pass
```
