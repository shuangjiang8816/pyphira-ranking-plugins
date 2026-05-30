# plugins/my_plugin.py
from utils.room import rooms
from rymc.phira.protocol.data.message import ChatMessage
from rymc.phira.protocol.packet.clientbound import ClientBoundMessagePacket

import requests

PLUGIN_INFO = {
    "name": "panking",
    "version": "0.0.1",
    "description":"新增排行榜功能",
}

player_url = "https://phira.5wyxi.com/user/"
store_url = "https://phira.5wyxi.com/record/"
player_list = []
rooms_values = rooms.values()

def setup(ctx):
    def broadcast_to_all(message,rooms_values):
        """向所有在线玩家广播消息"""
        packet = ClientBoundMessagePacket(ChatMessage(-1, message))
        
        # 遍历所有房间的所有玩家
        for room in rooms_values:
            for room_user in room.users.values():
                try:
                    room_user.connection.send(packet)
                except Exception as e:
                    ctx.logger.error(f"广播失败: {e}")

    def ranking(player_list:list) -> str:
        def format(ranking_list:list) -> str:
            ranking_message:str = ""
            for i in range(0,len(ranking_list)):
                name = ranking_list[i]['name']
                score = ranking_list[i]['score']
                accuracy = ranking_list[i]['accuracy']
                ranking_message += f"第{i+1}名:{name},{score}({accuracy*100:.2f}%)\n"
            return ranking_message

        def get_score(player:dict) -> int:
            return player['score']
        
        ranking_list:list = sorted(player_list,key=get_score,reverse=True)
        return format(ranking_list)

    def on_chat(packet=None, **_):
        # packet 是 ServerBoundChatPacket
        # 解析出游玩id
        play_id = packet.id
        # 请求本次游玩数据
        return_message= requests.get(f"{store_url}{play_id}")
        player_information = return_message.json()
        score = player_information['score']
        accuracy = player_information['accuracy']
        # 获取玩家名称
        player = requests.get(f"{player_url}{player_information['player']}")
        name = player.json()['name']
        # 整理成字典并保存
        player_dict = {"name":name,"score":score,"accuracy":accuracy}
        player_list.append(player_dict)
        # 排序并格式化
        # 广播
        result = ranking(player_list)
        broadcast_to_all(ranking(player_list),rooms_values)
        ctx.logger.debug(result)

    def clear(packet=None, **_):
        # 先保存房间
        global player_list,rooms_values
        rooms_values = rooms.values()
        player_list = []

    def printing1(packet=None,**kwargs):
        ctx.logger.debug(packet)

    def on_auth_success(connection=None, **_):
        connection.send(ClientBoundMessagePacket(ChatMessage(-1, "欢迎游玩phira!(服务端已修改,排行榜插件by:霜降awa)")))

    # ctx.on("packet.received", printing1)
    ctx.on("auth.success", on_auth_success)
    ctx.on("packet.ServerBoundPlayedPacket.received", on_chat)
    ctx.on("packet.ServerBoundSelectChartPacket.received",clear)

    # 可选：返回 teardown，用于卸载/重载前清理资源
    def teardown():
        ctx.logger.info("排行榜插件已卸载，感谢你的使用！")

        return teardown