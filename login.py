import asyncio
from asynccmd import Cmd
from client import PenguinRewritten
import sys
class PCL_CPR(Cmd):
    def __init__(self, mode, intro, prompt):
        # We need to pass in Cmd class mode of async cmd running
        super().__init__(mode=mode)
        self.intro = intro
        self.prompt = prompt
        
    def start(self, loop):
        self.loop = loop
        super().cmdloop(loop)
    
    def do_login(self, args):
        args = args.split(' ')
        self.client = PenguinRewritten(args[0], args[1], 7070)
        self.loop.create_task(self.client.start())
        
    def do_join(self, args):
        self.loop.create_task(self.client.world_login(args))    
        
    def do_addall(self, args):
        self.loop.create_task(self.client.add_free_items())
        
if sys.platform == 'win32':
    loop = asyncio.ProactorEventLoop()
    mode = "Run"
else:
    loop = asyncio.get_event_loop()
    mode = "Reader"
# create instance
cmd = PCL_CPR(mode=mode, intro="CPR PCL", prompt="> ")
cmd.start(loop)  # prepaire instance
try:
    loop.run_forever()  # our cmd will run automatilly from this moment
except KeyboardInterrupt:
    loop.stop()
