import socket
import threading
import json
import sys 
import os 
import secrets 
"""
การรันโปรแกรมบนสองเครื่อง:
บนเครื่องแรก: python p2p_node.py 5000
บนเครื่องที่สอง: python p2p_node.py 5001
ใช้ตัวเลือกที่ 1 บนเครื่องใดเครื่องหนึ่งเพื่อเชื่อมต่อกับอีกเครื่อง
"""

# wallet = 0x6222fb2521bac69b5b61b1e105aceb1c8eb80890
# wallet2 = 0x7651b52d6cdb52fe2c18c65e3e5596a45f674e75

class Node:
    def __init__(self, host, port):
        self.host = host  # กำหนด host ที่โหนดจะใช้งาน
        self.port = port  # กำหนด port ที่โหนดจะใช้งาน
        self.peers = []  # เก็บรายการ socket ของ peer ที่เชื่อมต่อ
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # สร้าง socket สำหรับการเชื่อมต่อ
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # กำหนดคุณสมบัติ reuse address ให้ socket
        self.transactions = []  # เก็บรายการ transactions
        self.transaction_file = f"transactions_{port}.json"  # ไฟล์สำหรับบันทึก transactions
        self.wallet_address = self.generate_wallet_address()  # สร้าง wallet address สำหรับโหนดนี้

    def generate_wallet_address(self):
        # สร้าง wallet address แบบง่ายๆ (ในระบบจริงจะซับซ้อนกว่านี้มาก)
        return '0x' + secrets.token_hex(20)

    def start(self):
        # เริ่มต้นการทำงานของโหนด
        self.socket.bind((self.host, self.port))  # ผูก socket กับ host และ port ที่กำหนด
        self.socket.listen(1)  # ตั้งค่า socket ให้รอฟังการเชื่อมต่อใหม่
        print(f"Node listening on {self.host}:{self.port}")
        print(f"Your wallet address is: {self.wallet_address}")

        self.load_transactions()  # โหลด transactions จากไฟล์ (ถ้ามี)

        # เริ่ม thread สำหรับรับการเชื่อมต่อใหม่
        accept_thread = threading.Thread(target=self.accept_connections)
        accept_thread.start()

    def accept_connections(self):
        while True:
            # รอรับการเชื่อมต่อใหม่
            client_socket, address = self.socket.accept()
            print(f"New connection from {address}")

            # เริ่ม thread ใหม่สำหรับจัดการการเชื่อมต่อนี้
            client_thread = threading.Thread(target=self.handle_client, args=(client_socket,))
            client_thread.start()

    def handle_client(self, client_socket):
        while True:
            try:
                message = client_socket.recv(1024).decode()  # รับข้อความจาก client
                if message:
                    print(f"Received message: {message}")
                    self.handle_message(message)  # จัดการกับข้อความที่ได้รับ
                else:
                    client_socket.close()
                    break
            except:
                client_socket.close()
                break

    def handle_message(self, message):
        try:
            message = json.loads(message)  # แปลงข้อความ JSON เป็น object
            if message['type'] == 'transaction':
                self.add_transaction(message['data'])  # เพิ่ม transaction ใหม่
        except Exception as e:
            print(f"Failed to handle message: {e}")

    def add_transaction(self, transaction):
        self.transactions.append(transaction)  # เพิ่ม transaction เข้าไปในรายการ
        self.save_transactions()  # บันทึก transactions ลงไฟล์

    def connect_to_peer(self, peer_host, peer_port):
        peer_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # สร้าง socket สำหรับเชื่อมต่อกับ peer
        peer_socket.connect((peer_host, peer_port))  # เชื่อมต่อกับ peer
        self.peers.append(peer_socket)  # เพิ่ม socket ของ peer เข้าไปในรายการ
        print(f"Connected to peer {peer_host}:{peer_port}")

    def broadcast(self, message):
        for peer in self.peers:
            try:
                peer.sendall(json.dumps(message).encode())  # ส่งข้อความไปยัง peer ทุกตัว
            except:
                self.peers.remove(peer)

    def create_transaction(self, recipient, amount):
        transaction = {
            'sender': self.wallet_address,
            'recipient': recipient,
            'amount': amount
        }
        self.add_transaction(transaction)  # เพิ่ม transaction ใหม่
        self.broadcast({'type': 'transaction', 'data': transaction})  # ส่งข้อความ broadcast

    def save_transactions(self):
        # บันทึก transactions ลงไฟล์
        with open(self.transaction_file, 'w') as f:
            json.dump(self.transactions, f)

    def load_transactions(self):
        # โหลด transactions จากไฟล์ (ถ้ามี)
        if os.path.exists(self.transaction_file):
            with open(self.transaction_file, 'r') as f:
                self.transactions = json.load(f)
            print(f"Loaded {len(self.transactions)} transactions from file.")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python p2p.py <port>")
        sys.exit(1)
    
    port = int(sys.argv[1])
    node = Node("0.0.0.0", port)  # ใช้ "0.0.0.0" เพื่อรับการเชื่อมต่อจากภายนอก
    node.start()
    
    while True:
        print("\n1. Connect to a peer")
        print("2. Create a transaction")
        print("3. View all transactions")
        print("4. View my wallet address")
        print("5. Exit")
        choice = input("Enter your choice: ")
        
        if choice == '1':
            peer_host = input("Enter peer host to connect: ")
            peer_port = int(input("Enter peer port to connect: "))
            node.connect_to_peer(peer_host, peer_port)
        elif choice == '2':
            recipient = input("Enter recipient wallet address: ")
            amount = float(input("Enter amount: "))
            node.create_transaction(recipient, amount)
        elif choice == '3':
            print("All transactions:")
            for tx in node.transactions:
                print(tx)
        elif choice == '4':
            print(f"Your wallet address is: {node.wallet_address}")
        elif choice == '5':
            break
        else:
            print("Invalid choice. Please try again.")

    print("Exiting...")
