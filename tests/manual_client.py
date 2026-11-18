"""度朔服务端人工测试客户端。

以交互式菜单逐个调用服务端接口，用于人工检验各接口的可用性。

用法（在项目根目录执行）：

    uv run --extra dev python tests/manual_client.py

身份信息（客户端标识与 Ed25519 私钥）保存在 tests/.manual_client_profile.json，
删除该文件即可重置身份并重新配对。

短报文协议提示：
    content 为空        获取当前缓存消息；
    content 不为空      若缓存为空则设置新消息；
                        若当前消息未被本客户端获取过则删除当前消息；
                        若当前消息已被本客户端获取过则返回 already_fetched。
"""

import json
import sys
from pathlib import Path
from typing import Any, Optional

try:
    import httpx
except ImportError:
    raise SystemExit(
        "缺少 httpx 依赖，请改用：uv run --extra dev python tests/manual_client.py"
    )

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).parent))

from client_tools import build_signed_body, generate_keypair

PROFILE_PATH = Path(__file__).parent / ".manual_client_profile.json"
DEFAULT_SERVER = "http://127.0.0.1:18470"

MENU = """\
----------- 度朔服务端人工测试客户端 -----------
  1   健康检查              GET  /health
  2   查看配对信息          GET  /api/pairing
  3   打开配对页面          GET  /
  4   配对（上传公钥）      POST /api/pair
  5   重新开放配对窗口      POST /api/pairing/reopen
  6   上报数字活动          POST /api/activity
  7   查询服务状态          POST /api/status
  8   读取配置              POST /api/config
  9   修改配置              PUT  /api/config
  10  短报文操作            POST /api/message
  0   退出
----------------------------------------------"""

# 可修改的运行时配置项：名称、类型、提示。
RUNTIME_FIELDS = (
    ("activity_cache_duration", int, "数字活动缓存时长（秒）"),
    ("death_countdown", int, "死亡判定倒计时（秒）"),
    ("execution_task", str, "最终任务执行命令"),
    ("message_cache_duration", int, "短报文缓存时长（秒）"),
    ("pairing_window_time", int, "配对窗口时长（秒）"),
)


def load_profile() -> Optional[dict[str, Any]]:
    """读取本地身份文件。"""
    if not PROFILE_PATH.exists():
        return None
    try:
        return json.loads(PROFILE_PATH.read_text("utf-8"))
    except Exception:
        print("身份文件已损坏，将重新创建。")
        return None


def create_profile() -> dict[str, Any]:
    """生成新的客户端身份并保存。"""
    client_id = input("客户端标识 [manual-client]: ").strip() or "manual-client"
    private_pem, public_pem = generate_keypair()

    profile = {
        "client_id": client_id,
        "private_key": private_pem.decode(),
        "public_key": public_pem.decode(),
    }
    PROFILE_PATH.write_text(
        json.dumps(profile, ensure_ascii=False, indent=2), "utf-8"
    )
    print("已生成密钥对并保存至：{}".format(PROFILE_PATH))
    return profile


def show_response(response: httpx.Response) -> None:
    """打印响应内容。"""
    print("状态码：{}".format(response.status_code))
    try:
        print(json.dumps(response.json(), ensure_ascii=False, indent=2))
    except Exception:
        text = response.text
        if len(text) > 400:
            text = text[:400] + "……（已截断）"
        print(text)
    print()


def signed_request(
    http: httpx.Client,
    profile: dict[str, Any],
    method: str,
    path: str,
    payload: dict[str, Any],
) -> httpx.Response:
    """构造并发送一个带签名的业务请求。"""
    body = build_signed_body(
        profile["client_id"], profile["private_key"].encode(), payload
    )
    return http.request(method, path, json=body)


def do_pair(http: httpx.Client, profile: dict[str, Any]) -> None:
    """执行配对。"""
    print("尝试从服务端获取当前配对码……")
    try:
        response = http.get("/api/pairing")
    except httpx.HTTPError as exc:
        print("无法连接服务端：{}".format(exc))
        response = None

    code = None
    if response is not None and response.status_code == 200:
        code = response.json().get("pairing_code")
        print("服务端当前配对码：{}".format(code))
        if input("使用该配对码？[Y/n]: ").strip().lower() == "n":
            code = None
    elif response is not None:
        print("获取配对信息失败（{}）：{}".format(response.status_code, response.text))

    if code is None:
        code = input("请手动输入配对码: ").strip()

    if not code:
        print("未提供配对码，已取消。")
        return

    show_response(
        http.post(
            "/api/pair",
            json={
                "pairing_code": code,
                "client_id": profile["client_id"],
                "public_key": profile["public_key"],
            },
        )
    )


def do_activity(http: httpx.Client, profile: dict[str, Any]) -> None:
    """上报数字活动。"""
    activity = input("数字活动描述 [手动测试活动]: ").strip() or "手动测试活动"
    show_response(
        signed_request(http, profile, "POST", "/api/activity", {"activity": activity})
    )


def do_config_update(http: httpx.Client, profile: dict[str, Any]) -> None:
    """修改运行时配置。"""
    updates = {}
    for key, value_type, description in RUNTIME_FIELDS:
        raw = input("{}（直接回车跳过）: ".format(description)).strip()
        if not raw:
            continue
        try:
            updates[key] = value_type(raw)
        except ValueError:
            print("输入的不是有效的{}值，已跳过该字段。".format(value_type.__name__))

    show_response(signed_request(http, profile, "PUT", "/api/config", updates))


def do_message(http: httpx.Client, profile: dict[str, Any]) -> None:
    """短报文操作。"""
    content = input("消息内容（直接回车表示获取消息）: ")
    show_response(
        signed_request(
            http, profile, "POST", "/api/message", {"content": content or None}
        )
    )


def main() -> None:
    """交互式主循环。"""
    print("度朔服务端人工测试客户端")
    server = input("服务端地址 [{}]: ".format(DEFAULT_SERVER)).strip() or DEFAULT_SERVER

    profile = load_profile() or create_profile()
    print("当前客户端标识：{}\n".format(profile["client_id"]))

    with httpx.Client(base_url=server, timeout=10.0) as http:
        while True:
            print(MENU)
            choice = input("请选择: ").strip()

            try:
                if choice == "1":
                    show_response(http.get("/health"))
                elif choice == "2":
                    show_response(http.get("/api/pairing"))
                elif choice == "3":
                    show_response(http.get("/"))
                elif choice == "4":
                    do_pair(http, profile)
                elif choice == "5":
                    show_response(
                        signed_request(
                            http, profile, "POST", "/api/pairing/reopen", {}
                        )
                    )
                elif choice == "6":
                    do_activity(http, profile)
                elif choice == "7":
                    show_response(
                        signed_request(http, profile, "POST", "/api/status", {})
                    )
                elif choice == "8":
                    show_response(
                        signed_request(http, profile, "POST", "/api/config", {})
                    )
                elif choice == "9":
                    do_config_update(http, profile)
                elif choice == "10":
                    do_message(http, profile)
                elif choice == "0":
                    print("再见。")
                    return
                else:
                    print("无效的选择。\n")
            except httpx.HTTPError as exc:
                print("请求失败：{}\n".format(exc))


if __name__ == "__main__":
    main()
