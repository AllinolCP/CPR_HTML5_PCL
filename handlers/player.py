from events import event, JSONPacket
from loguru import logger
from penguin import Penguin
import json

@event.on(JSONPacket('login:u'))
async def get_login_data(p, penguin_id, nickname, token, player_data, server_list, PST, servers, word_regex):
    p.token = token
    p.servers = server_list
    logger.info(f'Select a server to join {list(p.servers.keys())}')
    
async def get_crumbs(p):
    crumbs = ['item', 'room', 'game']
    for _ in crumbs:
        await p.send_json(
            action='engine:get_crumbs',
            params=[_]
        )
    await p.join_room()
    
@event.on(JSONPacket('world:auth'))
async def get_world_login_data(p, penguin_id, nickname, player_data):
    p.player = Penguin(**player_data)
    logger.info(f'\
        Successfully logged in to {p.server["english"]}\
    ')
    await get_crumbs(p)
        
@event.on(JSONPacket('engine:get_crumbs'))
async def parse_crumbs(p, crumb_type, crumb):
    p.crumbs[crumb_type] = json.loads(crumb)     
    
@event.on(JSONPacket('inventory:buy_inventory'))
async def item_bought(p, item_id:str):
    logger.info(f"\
    Successfully purchased item\
    '{p.crumbs['item'][item_id]['english']}'\
    with cost of {p.crumbs['item'][item_id]['cost']}\
    ")
    
@event.on(JSONPacket('navigation:join_room'))
async def join_room(p, room_id:str, x, y):
    logger.info(p.crumbs)
    logger.info(f'Joined Room\
    {p.crumbs["room"][room_id]["english"]}')
    await p.send_json(
        action='inventory:get_inventory',
        params=[]
    )
    
@event.on(JSONPacket('engine:prompt'))
async def prompt(p, prompt_type, prompt_message, logout):
    logger.info(prompt_message)
    