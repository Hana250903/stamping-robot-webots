from controller import Robot, Motor, Supervisor
import asyncio
import websockets
import json
import threading

# Danh sách khớp của robot
JOINT_NAMES = ["base", "upperarm", "forearm", "wrist", "rotational_wrist", "gripper::right"]

class IprHd6m90Controller:
    def __init__(self):
        self.robot = Supervisor()  # ✅ Đúng
        self.joints = {}
        self.running = False  # 🚀 Biến này kiểm soát trạng thái robot
        self.waiting_logged = False  # Tránh spam "Waiting for command"

        # Tốc độ tối đa
        self.MAX_SPEED = 5.0  # rad/s

        self.stamp = self.robot.getFromDef("STAMP")
        self.paper = self.robot.getFromDef("A4PAPER")
        
        if self.stamp is None:
            print("❌ STAMP not found!")
        if self.paper is None:
            print("❌ A4PAPER not found!")


        # Khởi tạo khớp
        for joint in JOINT_NAMES:
            self.joints[joint] = self.robot.getDevice(joint)
            if self.joints[joint] is None:
                print(f"⚠️ Warning: {joint} not found!")
            else:
                self.joints[joint].setPosition(float("inf"))  # Chế độ kiểm soát tốc độ
                self.joints[joint].setVelocity(self.MAX_SPEED)
                self.joints[joint].setPosition(0)  # 🚀 Đặt vị trí khớp về 0

        print("✅ Robot initialized, all joints set to 0 position.")
    
    def check_collision(self):
        """Kiểm tra xem con dấu có chạm vào giấy không."""
        if self.stamp and self.paper:
            stamp_pos = self.stamp.getPosition()
            paper_pos = self.paper.getPosition()
            
            # Kiểm tra khoảng cách X, Y, Z
            if abs(stamp_pos[0] - paper_pos[0]) < 0.02 and abs(stamp_pos[1] - paper_pos[1]) < 0.02 and abs(stamp_pos[2] - paper_pos[2]) < 0.002:
                print("🖋️ Stamp has touched the paper! Marking the paper...")

                # ✅ Làm hiện dấu in
                self.stamp_appearance.getField("transparency").setSFFloat(0)
                return True
        return False
    
    def update_paper_texture(self):
    if self.paper:
        paper_texture = self.paper.getField("appearance").getSFNode().getField("textureTransform")
        if paper_texture:
            print("🖋️ Updating paper texture to show stamp mark...")
            paper_texture.setSFVec2f("scale", [1.2, 1.2])  # Giả lập dấu đã đóng

    
    def log_status(self, message, status):
        print(f"[{status}] {message}")

    def move_joint(self, joint_name, position):
        """Di chuyển khớp đến vị trí mong muốn."""
        print(f"🚀 Moving joint {joint_name} to {position}")  # 🛠 Debug

        if joint_name in self.joints and self.joints[joint_name] is not None:
            min_pos = self.joints[joint_name].getMinPosition()
            max_pos = self.joints[joint_name].getMaxPosition()

            position = max(min(position, max_pos), min_pos)
            self.joints[joint_name].setPosition(position)
            print(f"✅ {joint_name} moved to {position} rad")
        else:
            print(f"❌ Error: {joint_name} not found!")  # 🛠 Báo lỗi nếu không tìm thấy khớp

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
        self.move_joint("upperarm", -1.4)
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
        self.move_joint("upperarm", -1.45)
        self.update_paper_texture()
        self.move_joint("wrist", -1.1)
        self.robot.step(2000)

        self.log_status("Lifting stamp...", "PROCESSING")
        self.move_joint("upperarm", 0.0)
        self.robot.step(1000)
        self.log_status("Press stamp completed", "SUCCESS")
        
         # Kiểm tra va chạm
        if self.check_collision():
            print("✅ Paper has been stamped!")
        
        self.move_joint("upperarm", 0.0)
        self.robot.step(1000)

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

        self.move_joint("upperarm", -1.4)
        self.move_joint("gripper::right", 0.7)

        self.log_status("Lifting arm...", "PROCESSING")
        self.move_joint("wrist", -0.8)
        self.move_joint("upperarm", 0.0)
        self.robot.step(1000)
        self.log_status("Release stamp completed", "SUCCESS")
        
    def stop(self):
        """Dừng hoạt động của robot."""
        print("🛑 Stop requested!")
        self.stop_requested = True
        self.running = False    
  
    def run(self):
        """Chạy tuần tự các bước pick_up_stamp -> press_stamp -> release_stamp."""
        self.running = True
        self.pick_up_stamp()
        self.press_stamp()
        self.release_stamp()
        self.running = False

    def reset(self):
        """Di chuyển robot về vị trí ban đầu."""
        print("🔄 Resetting arm to initial position...")
        self.move_joint("base", 0.0)
        self.move_joint("upperarm", 0.0)
        self.move_joint("forearm", 0.0)
        self.move_joint("wrist", 0.0)
        self.move_joint("rotational_wrist", 0.0)
        self.move_joint("gripper::right", 0.1)  # Để gripper mở sẵn
        
# Khởi tạo bộ điều khiển
controller = IprHd6m90Controller()
timestep = int(controller.robot.getBasicTimeStep())

# Tạo hàng đợi để xử lý lệnh
command_queue = asyncio.Queue()

def run_webots():
    """Vòng lặp Webots chạy liên tục nhưng chỉ cập nhật khi có lệnh."""
    print("🛠 Webots loop started!")
    while controller.robot.step(timestep) != -1:
        if controller.running:
            print("⏳ Webots is executing a command...")
            controller.waiting_logged = False  # Reset trạng thái waiting
        elif command_queue.empty() and not controller.waiting_logged:
            print("⏳ Waiting for command...")
            controller.waiting_logged = True  # Chỉ in một lần khi hàng đợi trống
            
async def process_commands():
    """Xử lý lệnh từ WebSocket."""
    while True:
        command = await command_queue.get()
        print(f"🔄 Processing command: {command}")  # 🛠 Debug

        if "joint" in command and "position" in command:
            controller.running = True  
            controller.move_joint(command["joint"], command["position"])
            await asyncio.sleep(0.5)  # 🕒 Chờ để robot thực hiện lệnh
            controller.running = False  # 🛑 Chỉ dừng khi xong
        elif command.get("command") in ["pick_up_stamp", "press_stamp", "release_stamp", "run", "stop", "reset"]:
            controller.running = True
            getattr(controller, command.get("command"))()
            controller.running = False
        else:
            print(f"⚠️ Unknown command: {command}")

async def websocket_handler(websocket, path):
    """Xử lý kết nối WebSocket từ client."""
    try:
        async for message in websocket:
            print(f"📩 Received: {message}")  # 🛠 In ra lệnh từ client

            command = json.loads(message)
            if command.get("command") in ["pick_up_stamp", "press_stamp", "release_stamp", "run", "stop", "reset"] or ("joint" in command and "position" in command):
                await command_queue.put(command)
                await websocket.send(json.dumps({"status": "OK"}))
            else:
                print(f"⚠️ Invalid command received: {command}")
                await websocket.send(json.dumps({"status": "ERROR", "message": "Invalid command"}))
    except websockets.exceptions.ConnectionClosed:
        print("❌ Client disconnected")

async def main():
    """Chạy server WebSocket song song với Webots."""
    server = await websockets.serve(websocket_handler, "localhost", 8766)
    print("✅ WebSocket server is running on ws://localhost:8766")

    # Chạy xử lý lệnh từ hàng đợi
    asyncio.create_task(process_commands())

    await server.wait_closed()  # Giữ server chạy

if __name__ == "__main__":
    # Chạy Webots trong một thread riêng
    webots_thread = threading.Thread(target=run_webots, daemon=True)
    webots_thread.start()

    # Chạy asyncio event loop
    asyncio.run(main())
