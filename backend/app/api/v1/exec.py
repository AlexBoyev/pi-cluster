import asyncio
import queue
import socket
import threading

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from jose import JWTError
from starlette.concurrency import run_in_threadpool

from app.auth.service import decode_token
from app.services.k8s_service import K8sService, _load_api

router = APIRouter(tags=["exec"])


@router.websocket("/ws/exec/{name}")
async def ws_exec(
    websocket: WebSocket,
    name: str,
    namespace: str = Query("pi-apps"),
    token: str = Query(...),
) -> None:
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            await websocket.close(code=4001)
            return
    except JWTError:
        await websocket.close(code=4001)
        return

    pod_name = await run_in_threadpool(K8sService().get_first_pod_name, name, namespace)
    if not pod_name:
        await websocket.accept()
        await websocket.send_text(f"[error] No running pod found for {name}\r\n")
        await websocket.close()
        return

    await websocket.accept()

    loop = asyncio.get_running_loop()
    out_q: asyncio.Queue[str | None] = asyncio.Queue()
    in_q: queue.Queue[str] = queue.Queue()

    def run_exec() -> None:
        from kubernetes import client as k8s_client
        from kubernetes.stream import stream as k8s_stream

        _load_api()
        core = k8s_client.CoreV1Api()
        try:
            resp = k8s_stream(
                core.connect_get_namespaced_pod_exec,
                pod_name,
                namespace,
                command=["/bin/sh"],
                stderr=True,
                stdin=True,
                stdout=True,
                tty=True,
                _preload_content=False,
            )
            while resp.is_open():
                resp.update(timeout=1)
                if resp.peek_stdout():
                    data = resp.read_stdout()
                    if data:
                        loop.call_soon_threadsafe(out_q.put_nowait, data)
                if resp.peek_stderr():
                    data = resp.read_stderr()
                    if data:
                        loop.call_soon_threadsafe(out_q.put_nowait, data)
                try:
                    inp = in_q.get_nowait()
                    resp.write_stdin(inp)
                except queue.Empty:
                    pass
        except Exception as exc:
            loop.call_soon_threadsafe(out_q.put_nowait, f"\r\n[error] {exc}\r\n")
        finally:
            loop.call_soon_threadsafe(out_q.put_nowait, None)

    thread = threading.Thread(target=run_exec, daemon=True)
    thread.start()

    async def send_output() -> None:
        while True:
            data = await out_q.get()
            if data is None:
                break
            try:
                await websocket.send_text(data)
            except Exception:
                break

    send_task = asyncio.create_task(send_output())
    try:
        while True:
            msg = await websocket.receive_text()
            in_q.put(msg)
    except WebSocketDisconnect:
        pass
    finally:
        send_task.cancel()


@router.websocket("/ws/logs/{name}")
async def ws_logs(
    websocket: WebSocket,
    name: str,
    namespace: str = Query("pi-apps"),
    container: str | None = Query(None),
    tail: int = Query(200),
    token: str = Query(...),
    pod: str | None = Query(None),
) -> None:
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            await websocket.close(code=4001)
            return
    except JWTError:
        await websocket.close(code=4001)
        return

    if pod:
        pod_name = pod
    else:
        pod_name = await run_in_threadpool(K8sService().get_first_pod_name, name, namespace)
    if not pod_name:
        await websocket.accept()
        await websocket.send_text(f"[error] No running pod found for {name}\n")
        await websocket.close()
        return

    await websocket.accept()
    loop = asyncio.get_running_loop()
    out_q: asyncio.Queue[str | None] = asyncio.Queue()

    def run_logs() -> None:
        from kubernetes import client as k8s_client
        _load_api()
        core = k8s_client.CoreV1Api()
        kwargs: dict = dict(
            name=pod_name,
            namespace=namespace,
            follow=True,
            _preload_content=False,
            tail_lines=tail,
        )
        if container:
            kwargs["container"] = container
        loop.call_soon_threadsafe(
            out_q.put_nowait,
            f"[streaming pod/{pod_name}  container/{container or 'default'}]\n\n",
        )
        try:
            resp = core.read_namespaced_pod_log(**kwargs)
            for chunk in resp:
                if isinstance(chunk, bytes):
                    chunk = chunk.decode("utf-8", errors="replace")
                if chunk:
                    loop.call_soon_threadsafe(out_q.put_nowait, chunk)
        except Exception as exc:
            loop.call_soon_threadsafe(out_q.put_nowait, f"\n[error] {exc}\n")
        finally:
            loop.call_soon_threadsafe(out_q.put_nowait, None)

    thread = threading.Thread(target=run_logs, daemon=True)
    thread.start()

    async def send_log_output() -> None:
        while True:
            data = await out_q.get()
            if data is None:
                break
            try:
                await websocket.send_text(data)
            except Exception:
                break

    send_task = asyncio.create_task(send_log_output())
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        send_task.cancel()


@router.websocket("/ws/ssh/{node_ip}")
async def ws_ssh(
    websocket: WebSocket,
    node_ip: str,
    token: str = Query(...),
) -> None:
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            await websocket.close(code=4001)
            return
    except JWTError:
        await websocket.close(code=4001)
        return

    await websocket.accept()
    loop = asyncio.get_running_loop()
    out_q: asyncio.Queue[str | None] = asyncio.Queue()
    in_q: queue.Queue[str] = queue.Queue()

    def run_ssh() -> None:
        import paramiko as _paramiko
        from app.config import settings as _s
        client = _paramiko.SSHClient()
        client.set_missing_host_key_policy(_paramiko.AutoAddPolicy())
        try:
            client.connect(
                node_ip,
                username=_s.ssh_username,
                password=_s.ssh_password,
                timeout=_s.ssh_connect_timeout,
            )
            chan = client.invoke_shell(term="xterm-256color", width=200, height=50)
            chan.settimeout(0.1)
            loop.call_soon_threadsafe(
                out_q.put_nowait,
                f"[SSH] Connected to {node_ip} as {_s.ssh_username}\r\n",
            )
            while True:
                try:
                    data = chan.recv(4096)
                    if not data:
                        break
                    loop.call_soon_threadsafe(out_q.put_nowait, data.decode("utf-8", errors="replace"))
                except socket.timeout:
                    pass  # no output yet — fall through to check for pending input
                except Exception:
                    break
                try:
                    inp = in_q.get_nowait()
                    chan.send(inp)
                except queue.Empty:
                    pass
                if chan.closed or chan.exit_status_ready():
                    break
        except Exception as exc:
            loop.call_soon_threadsafe(out_q.put_nowait, f"\r\n[SSH error] {exc}\r\n")
        finally:
            client.close()
            loop.call_soon_threadsafe(out_q.put_nowait, None)

    thread = threading.Thread(target=run_ssh, daemon=True)
    thread.start()

    async def send_output() -> None:
        while True:
            data = await out_q.get()
            if data is None:
                break
            try:
                await websocket.send_text(data)
            except Exception:
                break

    send_task = asyncio.create_task(send_output())
    try:
        while True:
            msg = await websocket.receive_text()
            in_q.put(msg)
    except WebSocketDisconnect:
        pass
    finally:
        send_task.cancel()
