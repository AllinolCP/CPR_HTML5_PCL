import awebus
import asyncio
from loguru import logger
from enum import IntEnum
from inspect import iscoroutinefunction
from functools import partial
from typing import Any, Callable, get_type_hints

def _is_coro( o ):
    """
    Return True if the given object is a coroutine(-compatible) object
    """
    return asyncio.iscoroutine( o ) or asyncio.iscoroutinefunction( o )


class SmartPriority(IntEnum):
    HIGH = -1
    MODERATE = 0
    LOW = 1

class _Packet:
    __slots__ = ['id']

    def __init__(self, packet_id):
        self.id = packet_id

    def __eq__(self, other):
        return self.id == other.id

    def __hash__(self):
        return hash(self.id)
        
    def __str__(self):
        return self.id


class JSONPacket(_Packet):
    pass


class SmartEvent(awebus.EventMixin):
    
    def __init__( self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.debug = kwargs.get("debug", True)

    @logger.catch
    def on(self, event:Any, *, callback:Callable = None):
        listener_event = str(event)

        def listener_handler_wrapper(listener_callback_function:Callable):
            listener_callback_function.function_attributes = {
                'priority': SmartPriority.MODERATE
            }

            super(SmartEvent, self).on(listener_event, listener_callback_function)

            if self.debug:
                logger.debug(f"added listener - '{listener_callback_function.__module__}::{listener_callback_function.__name__}' to event '{listener_event}'")

            return listener_callback_function

        if callback is not None:
            return listener_handler_wrapper(callback)

        return listener_handler_wrapper


    async def __check_and_enforce_arg_type_hints(self, function:Callable, *args, **kwargs):
        hints = get_type_hints(function)

        all_args = kwargs.copy()
        all_args.update(dict(zip(function.__code__.co_varnames, args)))

        for argument, argument_value in list(all_args.items()):
            argument_type = type(argument_value)

            if argument in hints:
                if not issubclass(argument_type, hints[argument]):
                    logger.warning("Event-Callback:{function.__name__}, argument:{argument} - expected object of type '{hint_type}', got '{argument_type}' instead. Attempting cast.",
                        function=function, argument=argument, hint_type=hints[argument], argument_type=argument_type)
                    
                    try:
                        new_argument_value = hints[argument].parse(argument_value) if hasattr(hints[argument], 'parse') else hints[argument](argument_value)
                        all_args[argument] = new_argument_value
                    except:
                        logger.error(f"Event-Callback:{function.__name__}, argument:{argument} - Failed to cast '{argument_type}' to '{hints[argument]}'. Skipping listener and all low-priority callbacks.")

                        return False, None, None
        
        return True, tuple(all_args[i] for i in function.__code__.co_varnames), dict(i for i in all_args.items() if i[0] not in function.__code__.co_varnames)


    @logger.catch
    async def emit(self, event:Any, *args, **kwargs):
        awaitables = list()
        listener_event = str(event)
        handlers = sorted(self._get_and_clean_event_handlers(listener_event), 
            key=lambda f: f.function_attributes.get('priority', SmartPriority.MODERATE) if hasattr(f, 'function_attributes') else SmartPriority.MODERATE)

        loop = asyncio.get_running_loop()

        for handler in handlers:
            type_check_success, _args, _kwargs = await self.__check_and_enforce_arg_type_hints(handler, *args, **kwargs)
            if not type_check_success:
                if True:
                    logger.info(f"Event-Callback:{handler.__name__} type-hint incompatibility ignored. The function callback and all low-priority callback is not skipped.")
                    _args, _kwargs = args, kwargs

                else:
                    break

            if _is_coro(handler):
                awaitables.append(handler(*_args, **_kwargs))
            else:
                functionWrapper = partial(handler, *_args, **_kwargs)
                awaitables.append(loop.run_in_executor(None, functionWrapper))

        if self.debug:
            logger.debug(f"emitting {len(awaitables)} listeners for the event '{listener_event}'")

        result = await asyncio.gather(*awaitables, loop=loop)
        return result

event = SmartEvent(debug=True)