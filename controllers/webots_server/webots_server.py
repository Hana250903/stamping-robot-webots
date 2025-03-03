import asyncio
import websockets
import json
import time
from datetime import datetime
from controller import Robot, Motor

# Danh sách các khớp điều khiển
JOINT_NAMES = ["base", "upperarm", "forearm", "wrist", "rotational_wrist", "gripper::right"]
TIME_STEP = 32  

class IprHd6m90Controller:
    def __init__(self):
        self.robot = Robot()
        self.joints = {}
        
        for joint in JOINT_NAMES:
            motor = self.robot.getDevice(joint)
            if motor:
                motor.setPosition(0.0)
                motor.setVelocity(10.0)
                self.joints[joint] = motor
            else:
                self.log_status(f"⚠️ Warning: {joint} not found!", "WARNING")

    def log_status(self, message, status="INFO"):
        """Ghi log vào file"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"[{timestamp}] {status}: {message}"
        print(log_message)

        with open("robot_process.log", "a") as log_file:
            log_file.write(log_message + "\n")

    def move_joint(self, joint_name, position):
        """Di chuyển khớp"""
        if joint_name in self.joints:
            self.joints[joint_name].setPosition(position)
        else:
            raise ValueError(f"❌ Error: Joint '{joint_name}' not found!")

controller = IprHd6m90Controller()
timestep = int(controller.robot.getBasicTimeStep())

async def websocket_handler(websocket, path):
    while controller.robot.step(timestep) != -1:
        try:
            data = await websocket.recv()
            command = json.loads(data)
            response = {}

            if command.get("reset"):
                success = controller.reset_position()
                response = {"status": "OK" if success else "ERROR", "message": "Reset done" if success else "Reset Failed"}

            elif command.get("pick_up_stamp"):
                success = controller.pick_up_stamp()
                response = {"status": "OK" if success else "ERROR", "message": "Pick-up done" if success else "Pick-up Failed"}

            elif command.get("press_stamp"):
                success = controller.press_stamp()
                response = {"status": "OK" if success else "ERROR", "message": "Pressing done" if success else "Pressing Failed"}

            elif command.get("release_stamp"):
                success = controller.releasing_stamp()
                response = {"status": "OK" if success else "ERROR", "message": "Release done" if success else "Release Failed"}

            elif command.get("run"):
                response = controller.run()

            await websocket.send(json.dumps(response))
        except Exception as e:
            controller.log_status(f"🔥 Unexpected Error: {e}", "ERROR")

async def main():
    controller.log_status("✅ Starting WebSocket server...", "INFO")
    server = await websockets.serve(websocket_handler, "localhost", 8766)
    await server.wait_closed()

if __name__ == "__main__":
    asyncio.run(main())
