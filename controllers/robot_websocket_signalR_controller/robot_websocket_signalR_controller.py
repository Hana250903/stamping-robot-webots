from controller import Robot, Motor
import asyncio
import threading
import requests
import json
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

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
        return status  # Trả về giá trị status

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

    def pick_up_stamp(self, job_id):
        print("🛠 Picking up stamp...")
        self.log_status("Picking up stamp", "InProgress")
        self.move_joint("base", 3)
        self.move_joint("upperarm", -1.1)
        self.move_joint("forearm", 0)
        self.move_joint("wrist", -1)
        self.move_joint("gripper::right", 0.7)
        self.move_joint("rotational_wrist", 0)
        self.robot.step(1000)
        
        self.log_status("Grabbing the stamp...", "InProgress")
        self.move_joint("upperarm", -1.5)
        self.move_joint("gripper::right", -0.04)
        self.robot.step(1500)
        
        self.log_status("Lifting stamp...", "InProgress")
        self.move_joint("upperarm", 0.0)
        self.robot.step(1000)
        self.log_status("Pick up stamp completed", "Completed")
        send_update(job_id, "Completed")

    def press_stamp(self, job_id):
        print("🔨 Pressing stamp...")
        self.log_status("Pressing stamp", "InProgress")
        self.move_joint("base", 6.0)
        self.move_joint("upperarm", -1)
        self.move_joint("forearm", 0.3)
        self.move_joint("wrist", -0.8)
        self.robot.step(1500)

        self.log_status("Pressing stamp...", "InProgress")
        self.move_joint("upperarm", -1.5)
        self.move_joint("wrist", -1.4)
        self.robot.step(1500)

        self.log_status("Lifting stamp...", "InProgress")
        self.move_joint("upperarm", 0.0)
        self.robot.step(1000)
        self.log_status("Press stamp completed", "Completed")
        send_update(job_id, "Completed")

    def release_stamp(self, job_id):
        print("🛠 Releasing stamp...")
        self.log_status("Releasing stamp", "InProgress")
        self.move_joint("base", 3)
        self.move_joint("upperarm", -1.1)
        self.move_joint("forearm", 0)
        self.move_joint("wrist", -1)
        self.move_joint("gripper::right", -0.04)
        self.move_joint("rotational_wrist", 0)
        self.robot.step(1500)

        self.move_joint("upperarm", -1.5)
        self.move_joint("gripper::right", 0.7)

        self.log_status("Lifting arm...", "InProgress")
        self.move_joint("wrist", -0.8)
        self.move_joint("upperarm", 0.0)
        self.robot.step(1000)
        self.log_status("Release stamp completed", "Completed")
        send_update(job_id, "Completed")
        
    def align_stamp(self, job_id):
        """Căn chỉnh con dấu trước khi đóng dấu"""
        print("📏 Aligning stamp...")
        self.log_status("Aligning stamp", "InProgress")
        
        self.move_joint("base", 3.5)
        self.move_joint("upperarm", -1.0)
        self.move_joint("forearm", 0.2)
        self.move_joint("wrist", -1.2)
        self.robot.step(1200)
    
        self.log_status("Fine-tuning alignment...", "InProgress")
        self.move_joint("forearm", 0.0)
        self.move_joint("wrist", -1.0)
        self.robot.step(800)
    
        self.log_status("Alignment completed", "Completed")
        send_update(job_id, "Completed")        

    def rotate_stamp(self, job_id):
        """Xoay con dấu để điều chỉnh hướng"""
        print("🔄 Rotating stamp...")
        self.log_status("Rotating stamp", "InProgress")
        
        self.move_joint("rotational_wrist", 0.5)
        self.robot.step(800)
    
        self.move_joint("rotational_wrist", -0.5)
        self.robot.step(800)
    
        self.move_joint("rotational_wrist", 0.0)
        self.robot.step(500)
    
        self.log_status("Rotation completed", "Completed")
        send_update(job_id, "Completed")    
        
    def shake_stamp(self, job_id):
        """Lắc nhẹ con dấu để đảm bảo mực bám đều"""
        print("🔄 Shaking stamp...")
        self.log_status("Shaking stamp", "InProgress")
    
        for _ in range(3):  # Lắc 3 lần
            self.move_joint("wrist", -1.2)
            self.robot.step(500)
            self.move_joint("wrist", -0.8)
            self.robot.step(500)
    
        self.log_status("Shake completed", "Completed")
        send_update(job_id, "Completed")
    
    def clean_stamp(self, job_id):
        """ Làm sạch con dấu sau khi đóng dấu để tránh lem mực"""
        print("🧼 Cleaning stamp...")
        self.log_status("Cleaning stamp", "InProgress")
    
        self.move_joint("base", 5.0)
        self.move_joint("upperarm", -1.3)
        self.move_joint("forearm", 0.2)
        self.move_joint("wrist", -1.1)
        self.robot.step(1200)
    
        self.move_joint("gripper::right", 0.2)  # Mô phỏng chạm vào khăn lau
        self.robot.step(800)
    
        self.log_status("Cleaning completed", "Completed")
        send_update(job_id, "Completed")
    
    def inspect_stamp(self, job_id):
        """Kiểm tra vị trí và chất lượng con dấu trước khi tiếp tục"""
        print("🔍 Inspecting stamp...")
        self.log_status("Inspecting stamp", "InProgress")
    
        self.move_joint("base", 4.0)
        self.move_joint("upperarm", -0.8)
        self.move_joint("forearm", 0.1)
        self.move_joint("wrist", -0.9)
        self.robot.step(1000)
    
        self.log_status("Inspection completed", "Completed")
        send_update(job_id, "Completed") 
        
    def stop(self, job_id):
        """Dừng hoạt động của robot."""
        print("🛑 Stop requested!")
        self.running = False  
        send_update(job_id, "Completed") 

    def reset(self, job_id):
        """Di chuyển robot về vị trí ban đầu."""
        print("🔄 Resetting arm to initial position...")
        if job_id is None:
            print("No job_id provided. Resetting all jobs.")
            self.log_status("Inspecting stamp", "InProgress")
            self.move_joint("base", 0.0)
            self.move_joint("upperarm", 0.0)
            self.move_joint("forearm", 0.0)
            self.move_joint("wrist", 0.0)
            self.move_joint("rotational_wrist", 0.0)
            self.move_joint("gripper::right", 0.1)
            self.log_status("Inspection completed", "Completed")
        else:
            print(f"Resetting job with ID: {job_id}")
            self.log_status("Inspecting stamp", "InProgress")
            self.move_joint("base", 0.0)
            self.move_joint("upperarm", 0.0)
            self.move_joint("forearm", 0.0)
            self.move_joint("wrist", 0.0)
            self.move_joint("rotational_wrist", 0.0)
            self.move_joint("gripper::right", 0.1)
            self.log_status("Inspection completed", "Completed")
            send_update(job_id, "Completed")  

# API_URL = "https://stampingrobotapi.azurewebsites.net/robotHub"
API_URL = "https://localhost:7196/robotHub"
def create_task(coroutine):
    """Tạo một task bất đồng bộ an toàn trong event loop hiện tại."""
    try:
        loop = asyncio.get_running_loop()
        return loop.create_task(coroutine)
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(coroutine)

API_UPDATE_JOB = "https://localhost:7196/api/stamping-jobs/{}"

def send_update(job_id, status):
    """Gửi cập nhật trạng thái của một stampingJob lên API bằng phương thức PATCH"""
    
    job = API_UPDATE_JOB.format(job_id)
    payload = f"{status}"
    headers = {"Content-Type": "application/json"}

    try:
        response = requests.patch(job, json=payload, headers=headers, verify=False, timeout=10)  # Tăng timeout
        response.raise_for_status()  # Tự động xử lý lỗi HTTP
        
        print(f"✅ Updated job {job_id} to {status}")

    except requests.exceptions.HTTPError as http_err:
        print(f"❌ HTTP error occurred for job {job_id}: {http_err} - {response.text}")
    except requests.exceptions.RequestException as req_err:
        print(f"❌ Request error for job {job_id}: {req_err}")

API_UPDATE_SESSION = "https://localhost:7196/api/stamping-sessions/{}"

def send_update_session(session_id, status):
    """Gửi cập nhật trạng thái của một stampingJob lên API bằng phương thức PATCH"""
    session = API_UPDATE_SESSION.format(session_id)
    payload = f"{status}"
    headers = {"Content-Type": "application/json"}

    try:
        response = requests.patch(session, json=payload, headers=headers, verify=False, timeout=10)
        response.raise_for_status()  # Tự động xử lý lỗi HTTP
        print(f"✅ Updated job {session_id} to {status}")

    except requests.exceptions.HTTPError as http_err:
        print(f"❌ HTTP error occurred for job {session_id}: {http_err} - {response.text}")
    except requests.exceptions.RequestException as req_err:
        print(f"❌ Request error for job {session_id}: {req_err}")

API_UPDATE_TASK = "https://localhost:7196/api/task-assignments"

def send_update_task(job_id, status, image_captured="", details=""):
    """Gửi cập nhật trạng thái của một task lên API bằng phương thức POST"""
    
    payload = {
        "jobId": job_id,
        "status": status,
        "imageCaptured": image_captured,
        "details": details
    }
    
    headers = {"Content-Type": "application/json"}

    try:
        response = requests.post(API_UPDATE_TASK, json=payload, headers=headers, verify=False, timeout=10)
        response.raise_for_status()  # Xử lý lỗi HTTP nếu có
        
        print(f"✅ Updated job {job_id} to {status}")

    except requests.exceptions.HTTPError as http_err:
        print(f"❌ HTTP error occurred for job {job_id}: {http_err} - {response.text}")
    except requests.exceptions.RequestException as req_err:
        print(f"❌ Request error for job {job_id}: {req_err}")
        
API_UPDATE_ROBOT = "https://localhost:7196/api/robots/{}"

def send_update_robot(robot_id, status):
    """Gửi cập nhật trạng thái của một stampingJob lên API bằng phương thức PATCH"""
    
    job = API_UPDATE_ROBOT.format(robot_id)
    payload = f"{status}"
    headers = {"Content-Type": "application/json"}

    try:
        response = requests.patch(job, json=payload, headers=headers, verify=False, timeout=10)  # Tăng timeout
        response.raise_for_status()  # Tự động xử lý lỗi HTTP
        
        print(f"✅ Updated Robot {robot_id} to {status}")

    except requests.exceptions.HTTPError as http_err:
        print(f"❌ HTTP error occurred for job {robot_id}: {http_err} - {response.text}")
    except requests.exceptions.RequestException as req_err:
        print(f"❌ Request error for job {robot_id}: {req_err}")

def on_message(message):
    """Nhận lệnh từ API, giải JSON và thực hiện các bước dập dấu theo thứ tự tăng dần."""
    print(f"📩 Received task data: {json.dumps(message, indent=2)}")

    global command_queue  

    try:
        if isinstance(message, list):
            message = message[0]  

        robot_id = message.get("robotId")
        if not robot_id:
             print("❌ No robot found!")
             return 
        
        session_id = message.get("id")
        if not session_id:
            print("❌ Missing session ID! Cannot proceed.")
            return  # Không có session ID -> Dừng luôn

        stamping_jobs = message.get("stampingJobs", [])
        if not stamping_jobs:
            print("❌ No stamping jobs found!")
            return
        
        # Sắp xếp danh sách stampingJobs theo stepNumber tăng dần
        stamping_jobs_sorted = sorted(stamping_jobs, key=lambda job: job["stepNumber"])

        for job in stamping_jobs_sorted:
            job_id = job["id"]
            action = job["action"]
            step = job["stepNumber"]
            task_id = job["id"]
            print(f"🔄 Executing Step {step}: {action} (Job ID: {job_id})")
            
            if action == "reset":
                controller.reset(job_id)
            elif action == "pick-up-stamp":
                controller.pick_up_stamp(job_id)
            elif action == "press-stamp":
                controller.press_stamp(job_id)
            elif action == "release-stamp":
                controller.release_stamp(job_id)
            elif action == "align_stamp":
                controller.align_stamp(job_id)
            elif action == "rotate_stamp":
                controller.rotate_stamp(job_id)
            elif action == "shake_stamp":
                controller.shake_stamp(job_id)
            elif action == "clean_stamp":
                controller.clean_stamp(job_id)
            elif action == "inspect_stamp":
                controller.inspect_stamp(job_id)                
            else:
                print(f"⚠️ Unknown action: {action}, skipping...")

            send_update(job_id, "Completed")  
            send_update_task(task_id, "Completed")

        send_update_session(session_id, "Finished")
        send_update_robot(robot_id, "Idle")
        print(f"✅ Updated status to Finished for Session ID {session_id}")
        
    except Exception as e:
        print(f"❌ Error processing message: {e}")

async def process_commands():
    """Xử lý lệnh từ WebSocket."""
    while True:
        queue_size = command_queue.qsize()
        print(f"📦 Command queue size: {queue_size}")

        if queue_size > 0:
            command = await command_queue.get()
            print(f"🔄 Processing command: {command}")

            try:
                if isinstance(command, str):
                    command = json.loads(command)
            except json.JSONDecodeError:
                command = {"command": command.strip()}

            action = command.get("command")
            if action in ["pick_up_stamp", "press_stamp", "release_stamp", "run", "stop", "reset"]:
                controller.running = True
                getattr(controller, action)()
                controller.running = False
            else:
                for joint_name, position in command.items():
                    mapped_joint = JOINT_MAPPING.get(joint_name)
                    if mapped_joint:
                        print(f"🔹 Moving {mapped_joint} to {position}")
                        controller.move_joint(mapped_joint, position)
                    else:
                        print(f"⚠️ Unknown joint: {joint_name}, skipping...")
        
        await asyncio.sleep(0.5)  # Giảm tải CPU

        
def run_webots():
    """Vòng lặp Webots chạy liên tục nhưng chỉ cập nhật khi có lệnh."""
    print("🛠 Webots loop started!")
    previous_state = None  # Trạng thái trước đó

    while controller.robot.step(timestep) != -1:
        if controller.running:
            if previous_state != "running":
                print("⏳ Webots is executing a command...")
            previous_state = "running"
        elif command_queue.empty():
            if previous_state != "waiting":
                print("⏳ Waiting for command...")
            previous_state = "waiting"

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
        .with_url(API_URL, options={"verify_ssl": False})\
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

def on_message(message):
    """Nhận lệnh từ API, giải JSON và thực hiện các bước dập dấu."""
    print(f"📩 Received task data: {json.dumps(message, indent=2)}")

    global command_queue  

    try:
        if isinstance(message, list):
            message = message[0]  

        stamping_jobs = message.get("stampingJobs", [])
        if not stamping_jobs:
            print("❌ No stamping jobs found!")
            return
        
        for job in stamping_jobs:
            job_id = job["id"]
            action = job["action"]
            step = job["stepNumber"]

            print(f"🔄 Executing Step {step}: {action} (Job ID: {job_id})")
            
            if action == "reset":
                controller.reset()
            elif action == "pick-up-stamp":
                controller.pick_up_stamp()
            elif action == "press-stamp":
                controller.press_stamp()
            elif action == "release-stamp":
                controller.release_stamp()
            else:
                print(f"⚠️ Unknown action: {action}, skipping...")

            send_update(job_id, "Completed")  

    except Exception as e:
        print(f"❌ Error processing message: {e}")