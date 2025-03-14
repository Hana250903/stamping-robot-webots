from controller import Robot, Motor
import asyncio
import threading
import json
from signalrcore.hub_connection_builder import HubConnectionBuilder

# Danh sách khớp của robot
JOINT_NAMES = ["base", "upperarm", "forearm", "wrist", "rotational_wrist", "gripper::right"]
# Ánh xạ giữa tên khớp từ WebSocket và tên thực tế trong hệ thống
JOINT_MAPPING = {
    "base": "base",
    "upperarm": "upperarm",
    "forearm": "forearm",
    "wrist": "wrist",
    "rotationWrist": "rotational_wrist",  # Chuyển đổi tên đúng
    "gripper": "gripper::right"  # Chuyển đổi tên đúng
}

class IprHd6m90Controller:
    def __init__(self):
        self.robot = Robot()
        self.joints = {}
        self.running = False  
        self.waiting_logged = False  

        self.MAX_SPEED = 5.0  

        for joint in JOINT_NAMES:
            self.joints[joint] = self.robot.getDevice(joint)
            if self.joints[joint] is None:
                print(f"⚠️ Warning: {joint} not found!")
            else:
                self.joints[joint].setPosition(float("inf"))  
                self.joints[joint].setVelocity(self.MAX_SPEED)
                self.joints[joint].setPosition(0)  

        print("✅ Robot initialized, all joints set to 0 position.")
    
    def log_status(self, message, status):
        print(f"[{status}] {message}")

    def move_joint(self, joint_name, position):
        """Di chuyển khớp đến vị trí mong muốn."""
        print(f"🚀 Moving joint {joint_name} to {position}")  

        if joint_name in self.joints and self.joints[joint_name] is not None:
            min_pos = self.joints[joint_name].getMinPosition()
            max_pos = self.joints[joint_name].getMaxPosition()

            position = max(min(position, max_pos), min_pos)
            self.joints[joint_name].setPosition(position)
            print(f"✅ {joint_name} moved to {position} rad")
        else:
            print(f"❌ Error: {joint_name} not found!")  

    def pick_up_stamp(self):
        print("🛠 Picking up stamp...")
        self.log_status("Picking up stamp", "PROCESSING")
        self.move_joint("base", 3)
        self.move_joint("upperarm", -1.1)
        self.move_joint("forearm", 0)
        self.move_joint("wrist", -1)
        self.move_joint("gripper::right", 0.7)
        self.move_joint("rotational_wrist", 0)
        self.robot.step(1000)

        self.log_status("Grabbing the stamp...", "PROCESSING")
        self.move_joint("upperarm", -1.5)
        self.move_joint("gripper::right", -0.04)
        self.robot.step(1500)

        self.log_status("Lifting stamp...", "PROCESSING")
        self.move_joint("upperarm", 0.0)
        self.robot.step(1000)
        self.log_status("Pick up stamp completed", "SUCCESS")

    def press_stamp(self):
        print("🔨 Pressing stamp...")
        self.log_status("Pressing stamp", "PROCESSING")
        self.move_joint("base", 6.0)
        self.move_joint("upperarm", -1)
        self.move_joint("forearm", 0.3)
        self.move_joint("wrist", -0.8)
        self.robot.step(1500)

        self.log_status("Pressing stamp...", "PROCESSING")
        self.move_joint("upperarm", -1.5)
        self.move_joint("wrist", -1.4)
        self.robot.step(1500)

        self.log_status("Lifting stamp...", "PROCESSING")
        self.move_joint("upperarm", 0.0)
        self.robot.step(1000)
        self.log_status("Press stamp completed", "SUCCESS")

    def release_stamp(self):
        print("🛠 Releasing stamp...")
        self.log_status("Releasing stamp", "PROCESSING")
        self.move_joint("base", 3)
        self.move_joint("upperarm", -1.1)
        self.move_joint("forearm", 0)
        self.move_joint("wrist", -1)
        self.move_joint("gripper::right", -0.04)
        self.move_joint("rotational_wrist", 0)
        self.robot.step(1500)

        self.move_joint("upperarm", -1.5)
        self.move_joint("gripper::right", 0.7)

        self.log_status("Lifting arm...", "PROCESSING")
        self.move_joint("wrist", -0.8)
        self.move_joint("upperarm", 0.0)
        self.robot.step(1000)
        self.log_status("Release stamp completed", "SUCCESS")
        
    def stop(self):
        """Dừng hoạt động của robot."""
        print("🛑 Stop requested!")
        self.running = False  

    def reset(self):
        """Di chuyển robot về vị trí ban đầu."""
        print("🔄 Resetting arm to initial position...")
        self.move_joint("base", 0.0)
        self.move_joint("upperarm", 0.0)
        self.move_joint("forearm", 0.0)
        self.move_joint("wrist", 0.0)
        self.move_joint("rotational_wrist", 0.0)
        self.move_joint("gripper::right", 0.1)  

API_URL = "https://stampingrobotapi.azurewebsites.net/robotHub"

def create_task(coroutine):
    """Tạo một task bất đồng bộ an toàn trong event loop hiện tại."""
    try:
        loop = asyncio.get_running_loop()
        return loop.create_task(coroutine)
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(coroutine)
        
def on_message(message):
    """Nhận lệnh từ WebSocket và đưa vào hàng đợi."""
    print(f"📩 Received raw message: {message}")

    global command_queue  # Đảm bảo sử dụng đúng queue

    try:
        if isinstance(message, list):
            message = message[0]

        print(f"✅ Parsed command: {json.dumps(message, indent=2)}")

        # Đảm bảo queue đã được khởi tạo
        if command_queue is None:
            print("❌ command_queue is not initialized!")
            return

        # Lấy loop chính
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        if loop.is_running():
            future = asyncio.run_coroutine_threadsafe(command_queue.put(message), loop)
            future.result()  # Đợi cho lệnh được thêm vào queue
            print(f"✅ Command added to queue! New queue size: {command_queue.qsize()}")
        else:
            print("❌ Event loop is not running, using alternative method...")
            loop.run_until_complete(command_queue.put(message))
            print(f"✅ Command added using alternative method! New queue size: {command_queue.qsize()}")

    except Exception as e:
        print(f"❌ Error processing message: {e}")


async def process_commands():
    """Xử lý lệnh từ WebSocket."""
    while True:
        queue_size = command_queue.qsize()  # Kiểm tra số lượng lệnh trong queue
        print(f"📦 Command queue size: {queue_size}")

        if queue_size > 0:
            command = await command_queue.get()
            print(f"🔄 Processing command: {command}")  # Log khi bắt đầu xử lý lệnh
            
            for joint_name, position in command.items():
                mapped_joint = JOINT_MAPPING.get(joint_name)  
                if mapped_joint:
                    print(f"🔹 Moving {mapped_joint} to {position}")  
                    controller.move_joint(mapped_joint, position)
                else:
                    print(f"⚠️ Unknown joint: {joint_name}, skipping...")

        await asyncio.sleep(1)  # Tránh CPU quá tải
def run_webots():
    """Vòng lặp Webots chạy liên tục nhưng chỉ cập nhật khi có lệnh."""
    print("🛠 Webots loop started!")
    while controller.robot.step(timestep) != -1:
        if controller.running:
            print("⏳ Webots is executing a command...")
            controller.waiting_logged = False  
        elif command_queue.empty() and not controller.waiting_logged:
            print("⏳ Waiting for command...")
            controller.waiting_logged = True  

async def main():
    """Hàm chính khởi động tất cả các tiến trình"""
    global controller, timestep, command_queue

    print("🚀 Starting main()...")  

    controller = IprHd6m90Controller()
    timestep = int(controller.robot.getBasicTimeStep())
    command_queue = asyncio.Queue()

    print("✅ Initialized controller & queue!")

    # Kết nối WebSocket
    hub_connection = HubConnectionBuilder()\
        .with_url(API_URL)\
        .with_automatic_reconnect({"type": "interval", "intervals": [1, 2, 5, 10]})\
        .build()

    hub_connection.on("Send", on_message)
    hub_connection.start()
    print("✅ Connected to SignalR API!")

    # Chạy Webots trên luồng riêng
    webots_thread = threading.Thread(target=run_webots)
    webots_thread.start()
    print("🔄 Started Webots thread!")

    print("🔄 Starting command processing loop...")
    await process_commands()  # Quan trọng! Đảm bảo lệnh này không bị bỏ qua

# 🔥 Chạy main() nếu script được chạy độc lập
if __name__ == "__main__":
    asyncio.run(main())