import time
import rclpy
from rclpy.node import Node
from std_msgs.msg import Int8
from Speech_Lib import Speech
mySpeech = Speech()


class VoicePlayer(Node):
    def __init__(self):
        super().__init__('Player_Node')
        self.sub_playID = self.create_subscription(Int8,'player_id',self.playercallback,1000)
        
    def playercallback(self,msg):
        ID_value = msg.data
        print("ID_value: ",ID_value)
        if ID_value!=0:
        	play_id = ID_value
        	print("play_id = ",play_id)
        	mySpeech.void_write(int(play_id))

def main(args=None):
    rclpy.init(args=args)
    voice_player = VoicePlayer()
    try:    
        rclpy.spin(voice_player)
    except KeyboardInterrupt:
        pass
    finally:
        voice_player.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()     

    
