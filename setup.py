from cx_Freeze import setup, Executable

# 需要打包的 Python 文件
executables = [Executable("server.py", base=None, icon="1icon.ico")]

# 包含所需的依赖项
packages = ["flask", "flask_socketio", "eventlet", "flask_limiter", "uuid", "threading", "logging", "dns"]

# 配置
setup(
    name="ForwardServer",
    version="1.0",
    description="WebSocket服务器",
    options={"build_exe": {"packages": packages, "include_files": ["server_config"]}},
    executables=executables,
)
