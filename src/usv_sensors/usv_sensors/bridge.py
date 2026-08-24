# SPDX-FileCopyrightText: Copyright (C) ARDUINO SRL (http://www.arduino.cc)
#
# SPDX-License-Identifier: MPL-2.0
#
# Ported unchanged from gps_and_water_quality_and_ros (python/src/ros_led/ros_led/app_utils/bridge.py)
# so usv_sensors can talk to the B1 board's Arduino MCU over the same RouterBridge protocol.

from functools import wraps
import inspect
import queue
import socket
import threading
import msgpack
import time
import os
from urllib.parse import urlparse


_reconnect_delay = 3.0  # seconds

# Error codes for RPC messages received from the RPC router. These are defined in the RPC router itself.
ROUTE_ALREADY_EXISTS_ERR = 0x05

# Error codes for RPC messages sent to Arduino_RPClite. These are defined in the lib itself.
MALFORMED_CALL_ERR = 0xFD
FUNCTION_NOT_FOUND_ERR = 0xFE
GENERIC_ERR = 0xFF


class Bridge:
    @staticmethod
    def notify(method_name: str, *params):
        """Sends a notification to the microcontroller without waiting for a response."""
        ClientServer().notify(method_name, *params)

    @staticmethod
    def call(method_name: str, *params, timeout: int = 10):
        """Calls a method on the microcontroller and waits for a response."""
        return ClientServer().call(method_name, *params, timeout=timeout)

    @staticmethod
    def provide(method_name: str, handler: callable):
        """Makes a method available to the microcontroller, so it can call it remotely."""
        ClientServer().provide(method_name, handler)

    @staticmethod
    def unprovide(method_name: str):
        """Makes a method no more available to the microcontroller."""
        ClientServer().unprovide(method_name)


def _is_unbound_or_class_method(func):
    try:
        sig = inspect.signature(func)
        params = list(sig.parameters.values())
        if not params:
            return False
        first_param = params[0]
        return first_param.kind in (
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
            inspect.Parameter.POSITIONAL_ONLY,
        ) and first_param.name in ("self", "cls")
    except ValueError:
        return False


class SingletonMeta(type):
    _instance = None
    _instance_lock = threading.Lock()

    def __call__(cls, *args, **kwargs):
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = super().__call__(*args, **kwargs)
        return cls._instance


class ClientServer(metaclass=SingletonMeta):
    def __init__(self, address: str = "unix:///var/run/arduino-router.sock"):
        self.next_msgid = 0
        self.next_msgid_lock = threading.Lock()
        self.callbacks = {}  # msgid -> (on_result, on_error)
        self.callbacks_lock = threading.Lock()
        self.handlers = {}  # method name -> function
        self.handlers_lock = threading.Lock()

        address_config = os.environ.get("APP_SOCKET", address)
        urlparsed = urlparse(address_config)
        if urlparsed.scheme == "unix":
            self.socket_type = "unix"
            self._peer_addr = urlparsed.path
        elif urlparsed.scheme == "tcp":
            self.socket_type = "tcp"
            self._peer_addr = (urlparsed.hostname, urlparsed.port)

        self._conn = None
        self._conn_lock = threading.Lock()
        self._is_connected_flag = threading.Event()

        self._connect()

        self._read_thread = threading.Thread(target=self._conn_manager, name="Bridge.read_loop", daemon=True)
        self._read_thread.start()

    def notify(self, method_name: str, *params):
        request = [2, method_name, params]
        try:
            self._send_bytes(msgpack.packb(request))
        except ConnectionError:
            pass
        except Exception:
            pass

    def call(self, method_name: str, *params, timeout: int = 10):
        msgid = self._increment_next_msgid()
        request = [0, msgid, method_name, params]

        resp_queue = queue.Queue(maxsize=1)

        def on_result(result):
            resp_queue.put((True, result))

        def on_error(error):
            resp_queue.put((False, error))

        with self.callbacks_lock:
            self.callbacks[msgid] = (on_result, on_error)

        try:
            self._send_bytes(msgpack.packb(request))
        except Exception as e:
            with self.callbacks_lock:
                self.callbacks.pop(msgid, None)
            raise RuntimeError(f"Failed to call method '{method_name}': {e}") from e

        try:
            (success, response) = resp_queue.get(timeout=timeout)
            if success:
                return response
            else:
                err_code, err_msg = response
                raise ValueError(f"Request '{method_name}' failed: {err_msg} ({err_code})")
        except queue.Empty:
            with self.callbacks_lock:
                if self.callbacks.pop(msgid, None):
                    try:
                        self.notify("$/cancelRequest", msgid)
                    except Exception:
                        pass
            raise TimeoutError(f"Request '{method_name}' timed out after {timeout}s")
        except Exception:
            with self.callbacks_lock:
                self.callbacks.pop(msgid, None)
            raise

    def provide(self, method_name: str, handler):
        if not callable(handler):
            raise ValueError("Handler must be a callable.")

        try:
            self.call("$/register", method_name)
        except Exception as e:
            raise RuntimeError(f"Failed to register method '{method_name}': {e}")

        with self.handlers_lock:
            self.handlers[method_name] = handler

    def unprovide(self, method_name: str):
        with self.handlers_lock:
            if method_name not in self.handlers:
                return

        try:
            self.call("$/unregister", method_name)
        except Exception as e:
            raise RuntimeError(f"Failed to unregister method '{method_name}': {e}")

        with self.handlers_lock:
            self.handlers.pop(method_name, None)

    def _increment_next_msgid(self):
        with self.next_msgid_lock:
            self.next_msgid = (self.next_msgid + 1) % (2**32)
            while self.next_msgid in self.callbacks:
                self.next_msgid = (self.next_msgid + 1) % (2**32)
            return self.next_msgid

    def _conn_manager(self):
        while True:
            self._connect()
            self._read_loop()
            time.sleep(_reconnect_delay)

    def _connect(self):
        if self._is_connected():
            return

        if self._conn:
            with self._conn_lock:
                try:
                    self._conn.close()
                except Exception:
                    pass
                self._conn = None

        self._is_connected_flag.clear()

        while not self._is_connected():
            try:
                with self._conn_lock:
                    if self.socket_type == "unix":
                        self._conn = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                        self._conn.connect(self._peer_addr)
                    elif self.socket_type == "tcp":
                        self._conn = socket.create_connection(self._peer_addr, timeout=5)
                self._conn.settimeout(None)
                self._is_connected_flag.set()

                def register_methods_on_reconnect():
                    with self.handlers_lock:
                        for method in self.handlers.keys():
                            try:
                                self.call("$/register", method)
                            except Exception:
                                pass

                if self.handlers:
                    t = threading.Thread(target=register_methods_on_reconnect, name="Bridge.register_methods_on_reconnect", daemon=True)
                    t.start()

                return
            except Exception:
                time.sleep(_reconnect_delay)

    def _is_connected(self) -> bool:
        if self._conn is None:
            return False

        try:
            data = self._conn.recv(8, socket.MSG_DONTWAIT | socket.MSG_PEEK)
            if len(data) == 0:
                return False
            return True
        except BlockingIOError:
            return True
        except ConnectionResetError:
            return False
        except Exception:
            return False

    def _read_loop(self):
        unpacker = msgpack.Unpacker()
        try:
            while True:
                try:
                    data = self._conn.recv(4096)
                    if not data:
                        break
                    unpacker.feed(data)
                    for msg in unpacker:
                        self._handle_msg(msg)
                except ConnectionResetError:
                    break
                except Exception:
                    continue
        finally:
            self._fail_pending_callbacks(ConnectionError("Connection to router lost."))

    def _decode_method(self, method_name) -> str:
        if isinstance(method_name, bytes):
            return method_name.decode()
        if isinstance(method_name, str):
            return method_name
        raise ValueError(f"Invalid method name type: {type(method_name)}. Expected str or bytes.")

    def _handle_msg(self, msg: list):
        if not msg or not isinstance(msg, list):
            return

        msg_type = msg[0]
        try:
            if msg_type == 0:  # Request: [0, msgid, method, params]
                if len(msg) != 4:
                    raise ValueError(f"Invalid RPC request: expected length 4, got {len(msg)}")
                _, msgid, method, params = msg
                if not isinstance(params, (list, tuple)):
                    raise ValueError("Invalid RPC request params: expected array or tuple")

                method_name = self._decode_method(method)

                with self.handlers_lock:
                    handler = self.handlers.get(method_name)

                if handler:
                    try:
                        result = handler(*params)
                        self._send_response(msgid, None, result)
                    except Exception as e:
                        self._send_response(msgid, e, None)
                else:
                    self._send_response(msgid, NameError(f"Method not found: '{method_name}'", method_name), None)

            elif msg_type == 1:  # Response: [1, msgid, error, result]
                if len(msg) != 4:
                    raise ValueError(f"Invalid RPC response: expected length 4, got {len(msg)}")
                _, msgid, error, result = msg
                if error and (not isinstance(error, list) or len(error) < 2):
                    raise ValueError("Invalid error format in RPC response")

                with self.callbacks_lock:
                    cbs = self.callbacks.pop(msgid, None)
                if cbs:
                    on_result, on_error = cbs
                    if result is None and error is None:
                        on_result(None)
                    elif result is not None or (error is not None and error[0] == ROUTE_ALREADY_EXISTS_ERR):
                        on_result(result)
                    elif error is not None:
                        on_error(error)
                    else:
                        on_result([GENERIC_ERR, "Unknown error occurred."])

            elif msg_type == 2:  # Notification: [2, method, params]
                if len(msg) != 3:
                    raise ValueError(f"Invalid RPC notification: expected length 3, got {len(msg)}")
                _, method, params = msg
                if not isinstance(params, (list, tuple)):
                    raise ValueError("Invalid RPC notification params: expected array or tuple")

                method_name = self._decode_method(method)

                with self.handlers_lock:
                    handler = self.handlers.get(method_name)

                if handler:
                    try:
                        handler(*params)
                    except Exception:
                        pass
        except ValueError:
            pass
        except Exception:
            pass

    def _fail_pending_callbacks(self, reason: Exception):
        with self.callbacks_lock:
            for _, (_, on_error) in list(self.callbacks.items()):
                if on_error:
                    try:
                        on_error(reason)
                    except Exception:
                        pass
            self.callbacks.clear()

    def _send_response(self, msgid: int, error, response):
        err = None
        if error is not None:
            err_code = GENERIC_ERR
            err_msg = str(error)
            if isinstance(error, NameError):
                err_code = FUNCTION_NOT_FOUND_ERR
            elif isinstance(error, (TypeError, ValueError)):
                err_code = MALFORMED_CALL_ERR
            err = [err_code, err_msg]

        msg = [1, msgid, err, response]
        try:
            self._send_bytes(msgpack.packb(msg))
        except ConnectionError:
            pass
        except Exception:
            pass

    def _send_bytes(self, packed_data: bytes):
        if not self._is_connected_flag.is_set():
            if not self._is_connected_flag.wait(timeout=_reconnect_delay):
                raise ConnectionError("Not connected to router, send failed.")

        with self._conn_lock:
            if self._conn is None:
                raise ConnectionError("No connection object for router, send failed.")
            try:
                self._conn.sendall(packed_data)
            except socket.error as e:
                raise ConnectionError(f"Send failed due to socket error: {e}")
