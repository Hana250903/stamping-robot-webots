from controller import Robot, Motor

# Constants
TIME_STEP = 32  # Webots simulation time step in milliseconds
JOINT_NAMES = ["base", "upperarm", "forearm", "wrist", "rotational_wrist", "gripper::right"]

class IprHd6m90Controller:
    def __init__(self):
        self.robot = Robot()
        self.joints = {}

        # Khởi tạo các khớp của robot
        for joint in JOINT_NAMES:
            self.joints[joint] = self.robot.getDevice(joint)
            if self.joints[joint] is None:
                print(f"⚠️ Warning: {joint} not found!")
            else:
                self.joints[joint].setPosition(0.0)  # Đặt vị trí ban đầu

    def move_joint(self, joint_name, position):
        """Di chuyển khớp cụ thể đến vị trí trong giới hạn an toàn."""
        if joint_name in self.joints and self.joints[joint_name] is not None:
            min_pos = self.joints[joint_name].getMinPosition()
            max_pos = self.joints[joint_name].getMaxPosition()
            
            position = max(min(position, max_pos), min_pos)

            if min_pos != float("-inf") and max_pos != float("inf"):
                if not (min_pos <= position <= max_pos):
                    print(f"🚫 Invalid position for {joint_name}: {position} (Allowed: {min_pos} to {max_pos})")
                    return
            
            self.joints[joint_name].setPosition(position)
        else:
            print(f"❌ Error: {joint_name} not found!")

    def pick_up_stamp(self):
        """Di chuyển đến vị trí stamp và nhặt nó lên."""

        print("✅ Moving to stamp position...")
        self.move_joint("base", 3)  # Xoay về phía stamp
        self.move_joint("upperarm", -1.2)  # Hạ tay xuống gần stamp
        self.move_joint("forearm", 0)  # Điều chỉnh forearm
        self.move_joint("wrist", -1)  # Căn chỉnh cổ tay
        self.move_joint("gripper::right", 0.4)
        self.move_joint("rotational_wrist", 0)  # Xoay cổ tay nhặt stamp

        self.robot.step(1500)  # Chờ robot di chuyển

        # Đóng kẹp để cầm stamp
        print("✅ Grabbing the stamp...")
        self.move_joint("gripper::right", -0.04)  # Đóng gripper giữ stamp

        self.robot.step(1500)  # Chờ kẹp giữ chắc

        # Nâng stamp lên
        print("✅ Lifting stamp...")
        self.move_joint("upperarm", 0.0)  # Nâng tay lên
        self.robot.step(1000)
        
        return True  # Xác nhận đã cầm được stamp

    def press_stamp(self):
        """Di chuyển đến giấy và đóng dấu."""
        print("✅ Moving to paper position...")
        self.move_joint("base", 6.0)  # Xoay về giấy
        self.move_joint("upperarm", -1.5)  # Hạ tay xuống gần giấy
        self.move_joint("forearm", 0.3)  # Điều chỉnh forearm
        self.move_joint("wrist", -0.8)  # Căn chỉnh cổ tay

        self.robot.step(1000)  # Chờ robot di chuyển

        # Nhấn xuống giấy
        print("✅ Pressing stamp...")
        self.move_joint("wrist", -1.0)  # Ép xuống
        self.robot.step(1000)

        # Nhả stamp
        print("✅ Releasing stamp...")
        self.move_joint("gripper::right", 0.1)  # Mở kẹp để thả stamp

        self.robot.step(1000)  # Chờ mở kẹp

        # Nâng tay lên
        print("✅ Lifting arm...")
        self.move_joint("wrist", -0.8)
        self.move_joint("upperarm", 0.0)
        self.robot.step(1000)

    def reset_position(self):
        """Di chuyển robot về vị trí ban đầu."""
        print("🔄 Resetting arm to initial position...")
        self.move_joint("base", 0.0)
        self.move_joint("upperarm", 0.0)
        self.move_joint("forearm", 0.0)
        self.move_joint("wrist", 0.0)
        self.move_joint("rotational_wrist", 0.0)
        self.move_joint("gripper::right", 0.1)  # Để gripper mở sẵn
        self.robot.step(1000)

    def run(self):
        """Chạy quá trình nhặt stamp và đóng dấu."""
        while self.robot.step(TIME_STEP) != -1:
            if self.pick_up_stamp():  # Bước 1: Nhặt stamp
                self.press_stamp()  # Bước 2: Đóng dấu
                self.reset_position()  # Bước 3: Quay về vị trí ban đầu
            break  # Dừng sau khi hoàn thành 1 lần đóng dấu

if __name__ == "__main__":
    controller = IprHd6m90Controller()
    controller.run()
