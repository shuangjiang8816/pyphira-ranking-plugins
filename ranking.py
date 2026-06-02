# plugins/my_plugin.py
import utils.room as room
from rymc.phira.protocol.data.message import ChatMessage
from rymc.phira.protocol.packet.clientbound import ClientBoundMessagePacket

import requests

PLUGIN_INFO = {
    "name": "panking",
    "version": "0.1.1",
    "description":"为phira多人游戏添加了排行榜功能，当前版本修复了不同房间排行榜串线的问题",
}

player_url = "https://phira.5wyxi.com/user/"
store_url = "https://phira.5wyxi.com/record/"

# 全局变量，存储不同房间的状态
room_dict:dict = {}
# 缓存玩家id，减轻官方服务器压力
player_id_map:dict = {}

def setup(ctx):
    def on_auth_success(connection=None, **_):
        connection.send(ClientBoundMessagePacket(ChatMessage(-1, "欢迎游玩phira!(服务端已修改,排行榜插件by:霜降awa)")))

    def broadcast_to_all(message,rooms_id):
        """向房间内玩家广播消息"""
        packet = ClientBoundMessagePacket(ChatMessage(-1, message))
        
        # 遍历所有房间的所有玩家
        for user in room_dict[rooms_id].users.values():
            try:
                user.connection.send(packet)
            except Exception as e:
                ctx.logger.error(f"广播失败: {e}")

    def ranking(player_list:list) -> str:
        """排名逻辑"""
        def format(ranking_list:list) -> str:
            """格式化"""
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

    def to_ranking(packet=None,handler=None, **_):
        """排名主函数"""

        # 请求本次游玩数据
        play_id = packet.id
        return_message= requests.get(f"{store_url}{play_id}")
        player_information = return_message.json()
        player_id = player_information['player']
        score = player_information['score']
        accuracy = player_information['accuracy']

        # 先检查id是否存在缓存，不存在则从官方服务器获取
        if not player_id in player_id_map:
            player = requests.get(f"{player_url}{player_id}")
            name = player.json()['name']
            # 缓存到内存中
            player_id_map[player_id] = name
        else:
            name = player_id_map[player_id]

        # 获取房间id 
        room_id = room.get_roomId(player_id)['roomId']
        # 整理成字典并保存
        player_dict = {"name":name,"score":score,"accuracy":accuracy}
        room_dict[room_id].player_list.append(player_dict)
        room_dict[room_id].finish.add(player_id)

        # 检查是否所有玩家完成游戏
        if len(room_dict[room_id].users) == len(room_dict[room_id].finish):
            # 排序并广播
            result = ranking(room_dict[room_id].player_list)
            broadcast_to_all(result,room_id)
            # 清空房间信息
            room_dict[room_id].finish.clear()
            room_dict[room_id].player_list.clear()

    def save_room(handler=None, **_):
        """复制并追加房间信息"""
        user_id = handler.user_info.id
        ctx.logger.debug(room.get_roomId(user_id))
        
        # 防止获取失败，重试3次
        for _ in range(0,3):
            result = room.get_roomId(user_id)
            if result['status'] == "0":
                room_id = result['roomId']
                room_dict[room_id] = room.rooms[room_id] # 复制房间信息
                room_dict[room_id].player_list = []      # 追加一个列表，用于储存游玩结束的玩家的游玩信息
                room_dict[room_id].finish = set()        # 更改finished字典为空集合
                ctx.logger.debug("成功复制房间信息")
                break
            else:
                ctx.logger.debug("玩家不在房间内！")
                pass

    def printing1(packet=None,**kwargs):
        """调试用"""
        if not "ServerBoundPingPacket" in str(type(packet)):# 过滤心跳包
            ctx.logger.debug(packet)

    # ctx.on("packet.received", printing1)
    ctx.on("auth.success", on_auth_success)
    ctx.on('handler.handleRequestStart.after',save_room)
    ctx.on("handler.handlePlayed.after", to_ranking)

    # 可选：返回 teardown，用于卸载/重载前清理资源
    def teardown():
        ctx.logger.info("排行榜插件已卸载，感谢你的使用！")

        return teardown
