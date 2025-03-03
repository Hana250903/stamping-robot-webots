import asyncio
import websockets
import json

async def websocket_client():
    uri = "ws://localhost:8766"

    try:
        print("🔄 Connecting to WebSocket server...")
        async with websockets.connect(uri) as websocket:
            print("✅ Connected to WebSocket server!")

            while True:  # 🔄 Duy trì vòng lặp nhập lệnh từ user
                user_input = input("👉 Enter command: ").strip()

                if user_input.lower() == "exit":
                    print("👋 Exiting...")
                    break  # Thoát khỏi vòng lặp

                elif user_input.lower() == "reset":
                    await websocket.send(json.dumps({"command": "reset"}))
                
                elif user_input.lower() == "pick_up_stamp":
                    await websocket.send(json.dumps({"command": "pick_up_stamp"}))

                elif user_input.lower() == "press_stamp":
                    await websocket.send(json.dumps({"command": "press_stamp"}))

                elif user_input.lower() == "release_stamp":
                    await websocket.send(json.dumps({"command": "release_stamp"}))

                elif user_input.lower() == "run":
                    await websocket.send(json.dumps({"command": "run"}))
                
                elif user_input.lower() == "stop":
                    await websocket.send(json.dumps({"command": "stop"}))
                
                elif user_input.lower() == "reset":
                    await websocket.send(json.dumps({"command": "reset"}))                
                
                else:
                    # 📌 Xử lý lệnh di chuyển khớp (VD: "base 1.5, wrist 0.8")
                    try:
                        commands = []
                        for cmd in user_input.split(","):
                            joint, position = cmd.strip().split()
                            commands.append({"joint": joint, "position": float(position)})

                        await websocket.send(json.dumps({"commands": commands}))

                    except ValueError:
                        print("⚠️ Invalid format! Use `<joint> <position>` or `reset`")
                        continue  # Quay lại nhập lệnh

                # 📩 Nhận phản hồi từ server
                response = await websocket.recv()
                print("📩 Server response:", json.loads(response))

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(websocket_client())
