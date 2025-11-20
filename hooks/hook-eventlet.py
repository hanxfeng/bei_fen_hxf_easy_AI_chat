from PyInstaller.utils.hooks import collect_submodules

# 收集 eventlet 模块的所有子模块
hiddenimports = collect_submodules('eventlet')
