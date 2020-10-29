import asyncio
import handlers
import json
import pathlib
import ssl
import websockets
from crypto import Crypto
from events import event, JSONPacket
from events.reloader import hot_reload_module
from loguru import logger

ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
cert = pathlib.Path(__file__).with_name("cpr.pem")
ssl_context.load_verify_locations(cert)
class PenguinRewritten: 
    def __init__(self, username, password, port=7070):
        self.username = username
        self.password = Crypto.get_login_hash(password, 'a94c5ed2140fc249ee3ce0729e19af5a')
        self.port = port
        self.token = None
        self.player = None
        self.servers = None
        self.crumbs = {}
        self.loop = asyncio.get_running_loop()
        
    async def start(self):
        await hot_reload_module(handlers)
        await self.connect()
        await self.login()
        
    async def login(self):
        await self.send_json(action='login:u', params=[self.username,self.password])     
        
    async def world_login(self, world_name):
        try:
            self.server = self.servers[world_name.lower()]
            self.port = self.server['port']
            await self.connect()
            await self.send_json(action='world:auth', params=[self.token])
        except KeyError:
            logger.error('Please enter a valid server!')


    async def add_free_items(self):
        logger.info('Adding items...')
        for item in self.crumbs['item']:
            if self.crumbs['item'][item]['cost'] == 0:
                await self.send_json(
                    action='inventory:buy_inventory',
                    params=[item]
                )   
                
    async def add_coins(self, amount):
        logger.info('Adding coins...')          
           
    async def join_room(self):
        await self.send_json(
            action='navigation:join_room',
            params=[-1,-1,-1]
        )

    async def listen(self):
        while not self.socket.closed:
            try:
                message = await self.socket.recv()
                await self.handle_json_data(message)
            except websockets.exceptions.ConnectionClosedError:
                logger.info('Client has disconnected from the server')
        
    async def connect(self):
        self.socket = await websockets.connect(
        f"wss://server.cprewritten.net:{self.port}/html5",
        ssl=ssl_context)
        self.loop.create_task(self.listen())
            
    async def send_line(self, data):
        logger.info(f'Sent JSON data: {data}')
        await self.socket.send(data)

    async def send_json(self, **data):
        await self.send_line(json.dumps(data))
        
    async def handle_json_data(self, data):
        data = json.loads(data)
        logger.info(f'Received JSON data: {data}')
        packet_id = data['action']
        packet_data = data['params']
        packet = JSONPacket(packet_id)
        await event.emit(packet, self, *packet_data)

    def __repr__(self):
        return f'<Spheniscidae {self.username}>'
