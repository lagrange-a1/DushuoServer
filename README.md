[CodeStyle: black]: https://img.shields.io/badge/code%20style-black-121110.svg?style=for-the-badge&label=代码风格
[python]: https://img.shields.io/badge/python-3.10-AB70FF?style=for-the-badge
[release]: https://img.shields.io/github/v/release/lagrange-a1/DushuoServer?style=for-the-badge&label=发行版&include_prereleases
[license]: https://img.shields.io/github/license/Lagrange-a1/DushuoServer?style=for-the-badge&label=协议&color=228B22
[github-repo-stars]: https://img.shields.io/github/stars/lagrange-a1/DushuoServer?color=20D9B9&logo=GitHub&style=for-the-badge
[github-repo-forks]: https://img.shields.io/github/forks/lagrange-a1/DushuoServer?color=20D9B9&logo=GitHub&style=for-the-badge
[github-commit-activity]: https://img.shields.io/github/commit-activity/m/lagrange-a1/DushuoServer%2Fmain?style=for-the-badge&logo=GitHub&label=提交活动&color=20D9B9

<h1 align="center">度朔<small style="font-size: 45%">服务端</small></h1>
<h3 align="center">一个通过监控数字活动来进行生死判断并执行亡语命令的系统</h3>
<!--
<p align="center">
    <img src="https://img.shields.io/badge/DEVELOPED%20WITH%20THE%20AWE%20FOR%20YOUR%20OWN%20LIFE-FF3432?style=for-the-badge">
<p>
-->
<p align="center">
<t align="center" style="text-align: center; color: #F2F4F6; background-color: #F03432; font-size: 110%; font-family: 'OPPOSans', MiSans, Noto Sans SC, Noto Sans CJK SC, Sans-Serif; ">
尊重如泰山般沉重的阁下的生命 以此期盼您能够珍爱自己的存在</t>
</p>

<!-- [![][Bilibili: 金羿ELS]](https://space.bilibili.com/397369002/)
[![][Bilibili: 玉衡Alioth]](https://space.bilibili.com/604072474) -->
[![CodeStyle: black]](https://github.com/psf/black)
[![][python]](https://www.python.org/)
[![][license]](LICENSE)
[![][release]](../../releases)
[![github-repo-stars]](https://github.com/lagrange-a1/DushuoServer/stargazers)
[![github-repo-forks]](https://github.com/lagrange-a1/DushuoServer/forks)
[![github-commit-activity]](https://github.com/lagrange-a1/DushuoServer/commits)

## 介绍

度朔山、度灵欢，引入鬼门关。

> _上古之人，有神荼、鬱壘者，昆弟二人，性能執鬼，居東海度朔山上，立桃樹下，簡閱百鬼。_
>
> —— 汉·王充《論衡·亂龍》

**度朔**是一个通过监控数字活动来进行生死判断并执行亡语命令的系统。

通过运行于用户的各个计算机或行动设备上的度朔客户端，记录用户的数字活动数据。当用户在一定时间内的数字活动完全为空，则执行最终命令。

**重要提示**：本项目及项目产品，不担保用户发出内容的有效性。若使用本项目发送*遗嘱*或类似内容，本项目不确保该行为在任何国家的法律法规中合法有效。

> 若我在某一刻停止了一切数字生活，这样的情况达到一定的时间，则我便已死亡。若我死亡，我的亡语将被执行。

本仓库为度朔系统的**服务端**，提供纯后端 HTTP 接口、并负责执行最终命令。度朔系统的[**客户端**](../dushuoclient)则提供数字活动上报的功能。

## 功能

客户端监测用户的数字活动数据，将数据上传至服务端，服务端收到任意客户端的数字活动之后，会刷新一个死亡判定倒计时。

当倒计时结束，服务端将执行客户端上传的命令作为最终任务。

## 启动

### 安装

本服务端依赖于 Python 3.10+，请确保阁下设备中存在该版本的解释器。

<details open>
<summary><b>使用 uv 管理的虚拟环境安装</b></summary>

在你想要安装本服务端的文件夹下依次执行：
```bash
uv venv ".venv" --prompt DushuoServer # 创建虚拟环境
.venv\Scripts\activate # 激活虚拟环境（在 Windows 下）
source .venv/bin/activate # 激活虚拟环境（在 *nix 下）
uv pip install DushuoServer # 安装服务端
```
</details>

<details open>
<summary><b>使用 pip + venv 安装</b></summary>

在你想要安装本服务端的文件夹下依次执行：
```bash
python -m venv ".venv" --prompt DushuoServer # 创建虚拟环境
.venv\Scripts\activate # 激活虚拟环境（在 Windows 下）
source .venv/bin/activate # 激活虚拟环境（在 *nix 下）
pip install DushuoServer # 安装服务端
```
</details>

### 启动

```bash
dushuoserver
```

在启动指令后增加 `--help` 参数查看参数说明，例如：

```bash
dushuoserver --help
```

启动服务时，可以在命令行通过 `--config` 参数指定配置文件路径，例如：

```bash
dushuoserver --config /path/to/config.toml
```

所有参数，除 --config 指定配置文件外，其余参数均可通过配置文件提供。故不另行解释，详见下方配置文件说明。

## 配置

服务端启动时，读取配置参数的优先级为：**默认配置 < 配置文件 < 命令行参数 < 服务端现有数据库**

其中，数据库仅会存储运行时参数。以下是[默认配置文件](./src/example_config.toml)：

| 层级 | 参数名称 | 默认值 | 类型 | 许可值 | 说明 |
| --- | --- | --- | --- | --- | --- |
|  | host_address | `"0.0.0.0"` | 字符串 | 合法的网络地址 | 服务地址 |
|  | host_port | `18470` | 整数 | `0`~`65535` | 服务端口 |
|  | log_level | `INFO` | 字符串 | 只能为`TRACE`、`DEBUG`、`INFO`、`WARNING`、`ERROR`、`CRITICAL`其中之一。大小写不敏感。 | 全局日志等级，用以控制输出的日志在控制台的打印等级，设定之后，只有与设定值同级或更高级的日志才会打印在控制台上。若运行目录下包含文件 `debugging.status.on`，则无论如何都会覆写为 `TRACE` |
|  | db_path | `"dushuodb.sqlite3"` | 字符串 | 合法的文件路径 | 数据库路径。若数据库中包含 **`[runtime]`** 层级对应的配置信息，则会覆盖该项配置配置。 |
|  | demo_mode | `false` | 逻辑 | `true` 或 `false` | 是否开启演示模式。当开启演示模式时，服务端将不会执行最终命令（但倒计时不会锁死为死亡状态，而是重新展开），所有接口依旧生效；服务端会每五分钟清理一次已配对超过1小时的客户端公钥；服务端的配对窗口改为常开 |
| **`[uvicron]`** | workers | `1` | 整数 | `1`~理论`+∞` | uvicorn 工作进程数 |
| **`[uvicron]`** | hot_reload | `false` | 逻辑 | `true` 或 `false` | 是否开启热重载 |
| **`[uvicron]`** | access_log | `true` | 逻辑 | `true` 或 `false` | 是否开启访问日志 |
| **`[runtime]`** | activity_cache_duration | `86400` | 整数 | `0`~`+∞` | 客户端活动消息的缓存时长（秒）；该参数决定了客户端上传的数字活动信息在服务端保存的时间；若设置为 `0`，则当传入活动时，服务端不存储任何活动，只刷新倒计时 |
| **`[runtime]`** | death_countdown | `86400` | 整数 | `0`~`+∞` | 死亡判定倒计时（秒）；该参数决定了多久没有收到数字活动信息会就会执行该命令 |
| **`[runtime]`** | execution_task | `""` | 字符串 | 符合当前系统要求的控制台命令 | 最终任务执行命令；此参数为倒计时结束时，服务端执行的命令 |
| **`[runtime]`** | message_cache_duration | `3600` | 整数 | `0`~`+∞` | 短报文缓存时长（秒）；该参数决定了短报文保存在服务端的时间 |
| **`[runtime]`** | pairing_window_time | `300` | 整数 | `0`~`+∞` | 配对窗口时长（秒）；该参数决定新的配对窗口开启的时长 |
| **`[runtime]`** | signature_time_tolerance | `300` | 整数 | `0`~`+∞` | 签名时间容差（秒）；该参数决定客户端发送请求所携带的时间戳与服务端时间的容差，理论上不可能超过一分钟 |


### 演示模式

将 `demo_mode` 设为 `true`（配置文件或启动参数 `--demo`）即可把服务端作为公共测试环境运行。演示模式下：

- **最终任务不予执行**：倒计时到期时仅在日志中记录，不会运行 `execution_task`；其余接口一律照常生效
- **不锁定死亡状态**：到期后倒计时立即重新展开，`GET /api/status` 保持 `alive`，`POST /api/activity` 的重置行为持续可用；若要观察真实的死亡流程，请关闭演示模式
- **配对窗口常开**：`GET /`、`GET /api/pairing`、`POST /api/pair` 不会因超时而返回 `410`，剩余时间字段返回 `null`
- **定期清理配对客户端**：每 60 秒删除一次配对时刻早于 3600 秒之前的客户端记录；被清理的客户端须重新配对

该项为启动级参数，只能由配置文件或命令行设定，客户端无法通过 `PUT /api/config` 修改，以免远程调用方解除演示模式的保护。

```bash
dushuoserver --demo
```


## 接口

详见 [接口文档](./docs/API-Reference.md) 。除 `/health` 与配对相关接口外，所有业务接口均需要先在配对窗口内完成配对，之后以客户端私钥对请求签名（签名置于 `X-Client-Id` 、 `X-Timestamp` 、 `X-Signature` 三个请求头中），由服务端以配对时登记的公钥校验。

## 协议

本项目使用 [Apache License, Version 2.0](./LICENSE) 授权。软件在原样提供的情况下，不在任何情况下提供任何担保。

```text
Copyright © 2026-present Eilles
All rights reserved.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
```

## 说明

此项目不保证用户使用本项目发出的内容的合法性，即，若本项目被用户配置为死亡时发送遗嘱、遗赠协议，本项目不确保该遗嘱或遗赠协议真实、合法、有效。阁下应当遵循所在国家的法律法规，自行决断执行指令的内容，并自行承担所有风险。

<t style="font-size: 120%; color: #0089F2">请明白：**你不必独自面对一切**。你任何时候，包括现在的感受，都非常重要。如果需要寻求帮助，请拨打急救电话`120`、或心理危机援助热线`12356`。**你不是一个人、也无需单独一人**。你现在愿意表达出来，是非常重要的一步。世界健康组织强调，社会支持、心理治疗、药物治疗与限制危险手段都能显著降低遭遇心理问题而产生危险想法的风险。**你的生命有价值，你值得被倾听、被理解，也值得获得专业帮助**。如果你现在处于紧急危险中，请不必怕麻烦，立即拨打急救电话`120`或心理援助热线`12356`。</t>

<details open>
<summary><b style="font-size: 120%; color: #0089F2">心理援助热线清单</b></summary>

| 援助服务名称 | 热线号码 |
| --- | --- |
| 全国统一心理援助热线电话 | 12356 |
| 全国青少年心理咨询热线 | 12355 |
| 全国妇女儿童心理咨询热线 | 12338 |
| 全国卫生健康热线 | 12320 |
| 中国心理危机与自杀干预中心救助热线| 010-62715275 |
| 北京心理援助热线 | 010-82951332 |

</details>

<t style="font-size: 120%; color: #0089F2">如果你需要缓解，无法拿起电话与人交谈，可以试着与[通义](https://www.qianwen.com/)、[豆包](https://www.doubao.com/chat/)等人工智能模型免费语音沟通，或者打字咨询。</t>

