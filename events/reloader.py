import asyncio
import os
import importlib
import pkgutil
import pathlib
from collections import deque
from types import ModuleType
from loguru import logger
from hachiko.hachiko import AIOWatchdog, AIOEventHandler
from typing import List, Dict

__MODULE_WATCHERS__:Dict[str, AIOWatchdog] = dict()


class MyEventHandler(AIOEventHandler):

    def __init__(self, module, *, debug = True):
        AIOEventHandler.__init__(self)
        self.parent_path = module.__path__
        self.parend_path_lib = pathlib.Path(module.__path__[-1])
        self.parent_name = module.__name__
        self.modules = deque()
        self.debug = debug

        if self.debug:
            logger.debug(f"watching changes on module: {self.parent_name}")

    async def on_any_event(self, event):
        path = event.src_path
        isdir = event.is_directory

        if not isdir and not path.endswith(".py"):
            return

        if self.debug:
            logger.debug(f"file {event.event_type} : src={path}, isdir={isdir}")

        await (self.reload_module(path) if not isdir else self.reload_package(path))

    @logger.catch
    async def reload_package(self, package_path:str):
        package_path = pathlib.Path(package_path)
        relative_path = package_path.absolute().relative_to(self.parend_path_lib)
        package_name = ".".join(relative_path.with_suffix("").parts)

        for module in list(self.modules):
            if module.__name__.startswith(package_name):
                self.modules.remove(module)
                #await self.reload_module(module)

    @logger.catch
    async def reload_module(self, module_path:str):
        for module in self.modules: # search for module
            if module.__file__.startswith(module_path):
                break

        else:
            # not found, probably not imported. try importing
            await self.import_module(module_path)
            return

        self.modules.remove(module)
        await self._reload_module(module)

    async def _reload_module(self, module:ModuleType):
        try:
            if not os.path.isfile(module.__file__):
                return

            list(delattr(module, attr) for attr in dir(module) if attr not in ('__name__', '__file__'))
            importlib.reload(module)
            self.modules.append(module)

            if self.debug:
                logger.debug(f"reloaded module: {module.__name__}")
        except:
            if self.debug:
               logger.exception(f"failed to reload module: {module.__name__}") 


    async def import_module(self, module_path:str):
        try:
            if not os.path.isfile(module_path):
                return

            module_path = pathlib.Path(module_path)
            relative_path = module_path.relative_to(self.parend_path_lib)
            if relative_path.name == "__init__.py":
                relative_path = relative_path.parent

            module_name = ".".join(relative_path.with_suffix("").parts)
            module_name = f"{self.parent_name}.{module_name}"
            mod = importlib.import_module(module_name, module_path)
            
            self.modules.append(mod)

            if self.debug:
                logger.debug(f"imported module: {module_name}")
        except Exception:
            if self.debug:
                logger.exception(f"failed to import module: {module_name}")

    @logger.catch
    async def load_modules(self, scope = None, _path = None):
        if self.debug:
            logger.info(f"loading modules in {self.parent_name}")

        ms_path = self.parent_path if _path == None else _path
        ms_name = self.parent_name if scope == None else scope.strip('.')
        for im, name, ispkg in pkgutil.iter_modules(ms_path, prefix=f"{ms_name}."):
            hm = importlib.import_module(name, package=ms_path)
            if ispkg:
                await self.loadModules(hm.__name__, hm.__path__)
            else:
                self.modules.append(hm)


async def hot_reload_module(module:ModuleType):
    path = os.path.dirname(module.__file__)
    evh = MyEventHandler(module, debug=True)
    await evh.load_modules()

    if True:
        watch = AIOWatchdog(path, event_handler=evh, recursive=True)
        __MODULE_WATCHERS__[module.__name__] = watch
        watch.start()