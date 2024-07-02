import socket
import threading
import json
import sys
import os
import secrets


""" การรันโปรแกรมบนสองเครื่อง:
บนเครื่องแรก: python p2p_node.py 5000
บนเครื่องที่สอง: python p2p_node.py 5001
ใช้ตัวเลือกที่ 1 บนเครื่องใดเครื่องหนึ่งเพื่อเชื่อมต่อกับอีกเครื่อง """

# wallet = 0x6222fb2521bac69b5b61b1e105aceb1c8eb80890
# wallet2 = 0x7651b52d6cdb52fe2c18c65e3e5596a45f674e75


class Node:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.peers = []  # รายการเก็บ socket ของ peer ที่เชื่อมต่อ
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # สร้าง socket แบบ TCP สำหรับการเชื่อมต่อ
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # ตั้งค่า socket เพื่อให้สามารถใช้ที่อยู่ซ้ำได้
        self.transactions = []  # รายการเก็บ transactions ที่ได้รับ
        self.transaction_file = f"transactions_{port}.json"  # ชื่อไฟล์สำหรับเก็บ transactions
        self.wallet_address = self.generate_wallet_address()  # สร้าง wallet address สำหรับโหนดนี้

    def generate_wallet_address(self):
        # สร้าง wallet address โดยใช้ secrets.token_hex() เพื่อสร้างข้อมูลสุ่มที่ปลอดภัย
        return '0x' + secrets.token_hex(20)

    def start(self):
        # เริ่มต้นการทำงานของโหนด
        self.socket.bind((self.host, self.port))  # ผูก socket กับ host และ port ที่กำหนด
        self.socket.listen(1)  # เริ่มต้นการรอรับการเชื่อมต่อฝั่ง server โดยยอมรับ client สูงสุด 1 คน
        print(f"Node listening on {self.host}:{self.port}")  # แสดงข้อความบอกว่าโหนดพร้อมที่จะรับการเชื่อมต่อจาก client
        print(f"Your wallet address is: {self.wallet_address}")  # แสดง wallet address ของโหนดนี้

        self.load_transactions()  # โหลด transactions ที่บันทึกไว้จากไฟล์ (ถ้ามี)

        # เริ่ม thread สำหรับรับการเชื่อมต่อใหม่
        accept_thread = threading.Thread(target=self.accept_connections)
        accept_thread.start()

    def accept_connections(self):
        while True:
            # รอรับการเชื่อมต่อใหม่
            client_socket, address = self.socket.accept()
            print(f"New connection from {address}")  # แสดงข้อความบอกถึงการเชื่อมต่อใหม่จาก client

            # เริ่ม thread ใหม่สำหรับการจัดการกับการเชื่อมต่อนี้
            client_thread = threading.Thread(target=self.handle_client, args=(client_socket,))
            client_thread.start()

    def handle_client(self, client_socket):
        while True:
            try:
                # รับข้อมูลจาก client
                data = client_socket.recv(1024)
                if not data:
                    break
                message = json.loads(data.decode('utf-8'))  # แปลงข้อมูลที่รับมาเป็น JSON
                
                self.process_message(message)  # ประมวลผลข้อมูลที่ได้รับ

            except Exception as e:
                print(f"Error handling client: {e}")  # แสดงข้อผิดพลาดที่เกิดขึ้นในการจัดการ client
                break

        client_socket.close()  # ปิดการเชื่อมต่อกับ client ที่เสร็จสิ้นการทำงาน

    def connect_to_peer(self, peer_host, peer_port):
        try:
            # สร้างการเชื่อมต่อไปยัง peer
            peer_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # สร้าง socket แบบ TCP สำหรับเชื่อมต่อ
            peer_socket.connect((peer_host, peer_port))  # เชื่อมต่อไปยัง peer ที่กำหนด
            self.peers.append(peer_socket)  # เพิ่ม peer_socket เข้าไปในรายการของ peer ที่เชื่อมต่ออยู่
            print(f"Connected to peer {peer_host}:{peer_port}")  # แสดงข้อความบอกว่าเชื่อมต่อกับ peer เรียบร้อย

            # เริ่ม thread สำหรับการรับข้อมูลจาก peer นี้
            peer_thread = threading.Thread(target=self.handle_client, args=(peer_socket,))
            peer_thread.start()

        except Exception as e:
            print(f"Error connecting to peer: {e}")  # แสดงข้อผิดพลาดที่เกิดขึ้นในการเชื่อมต่อกับ peer


    def broadcast(self, message):
        # ส่งข้อมูลไปยังทุก peer ที่เชื่อมต่ออยู่
        for peer_socket in self.peers:
            try:
                peer_socket.send(json.dumps(message).encode('utf-8'))  # ส่งข้อมูลในรูปแบบ JSON ไปยังทุก peer
            except Exception as e:
                print(f"Error broadcasting to peer: {e}")  # แสดงข้อผิดพลาดที่เกิดขึ้นในการส่งข้อมูลไปยัง peer
                self.peers.remove(peer_socket)  # ลบ peer_socket ที่เกิดข้อผิดพลาดออกจากรายการของ peer ที่เชื่อมต่ออยู่

    def process_message(self, message):
        # ประมวลผลข้อความที่ได้รับ
        if message['type'] == 'transaction':
            print(f"Received transaction: {message['data']}")  # แสดงข้อความบอกว่าได้รับ transaction มา
            self.add_transaction(message['data'])  # เพิ่ม transaction ที่ได้รับเข้าไปในรายการและบันทึกลงไฟล์
        else:
            print(f"Received message: {message}")  # แสดงข้อความถ้าประเภทข้อความที่ได้รับไม่ใช่ 'transaction'

    def add_transaction(self, transaction):
        # เพิ่ม transaction ใหม่และบันทึกลงไฟล์
        self.transactions.append(transaction)  # เพิ่ม transaction ใหม่เข้าไปในรายการ
        self.save_transactions()  # บันทึก transactions ลงไฟล์
        print(f"Transaction added and saved: {transaction}")  # แสดงข้อความบอกว่าเพิ่มและบันทึก transaction เรียบร้อย


    def create_transaction(self, recipient, amount):
        # สร้าง transaction ใหม่
        transaction = {
            'sender': self.wallet_address,
            'recipient': recipient,
            'amount': amount
        }
        self.add_transaction(transaction)  # เพิ่ม transaction ใหม่เข้าไปในรายการและส่ง broadcast ไปยัง peer ทั้งหมด
        self.broadcast({'type': 'transaction', 'data': transaction})  # ส่ง transaction ไปยังทุก peer ที่เชื่อมต่ออยู่

    def save_transactions(self):
        # บันทึก transactions ลงไฟล์
        with open(self.transaction_file, 'w') as f:
            json.dump(self.transactions, f)  # เขียนรายการ transactions ลงในไฟล์ในรูปแบบ JSON

    def load_transactions(self):
        # โหลด transactions จากไฟล์ (ถ้ามี)
        if os.path.exists(self.transaction_file):
            with open(self.transaction_file, 'r') as f:
                self.transactions = json.load(f)  # โหลด transactions จากไฟล์เข้าไปในรายการ transactions
            print(f"Loaded {len(self.transactions)} transactions from file.")  # แสดงข้อความบอกว่าโหลด transactions จากไฟล์เรียบร้อย


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python p2p.py <port>")
        sys.exit(1)
    
    port = int(sys.argv[1]) # กำหนด port
    node = Node("0.0.0.0", port)  # ใช้ "0.0.0.0" เพื่อรับการเชื่อมต่อจากภายนอก
    node.start() # เริ่มต้นการทำงานของโหนด
    
    while True: # ลุปการทำงาน
        print("\n1. Connect to a peer")
        print("2. Create a transaction")
        print("3. View all transactions")
        print("4. View my wallet address")
        print("5. Exit")
        choice = input("Enter your choice: ") # ให้ผู้ใช้ป้อนตัวเลือก
        
        if choice == '1':
            peer_host = input("Enter peer host to connect: ")  # รับ input
            peer_port = int(input("Enter peer port to connect: ")) # รับ input
            node.connect_to_peer(peer_host, peer_port) # เชื่อมต่อไปยัง peer ที่ระบุ
        elif choice == '2':
            recipient = input("Enter recipient wallet address: ") # รับ input
            amount = float(input("Enter amount: ")) # รับ input
            node.create_transaction(recipient, amount) # สร้าง transaction ใหม่
        elif choice == '3':
            print("All transactions:")
            for tx in node.transactions: # แสดงรายการ transactions ทั้งหมดที่จัดเก็บในโหนด
                print(tx) 
        elif choice == '4':
            print(f"Your wallet address is: {node.wallet_address}") # แสดง wallet address ของโหนด
        elif choice == '5': # ออกจากลูปและจบโปรแกรม
            break
        else:
            print("Invalid choice. Please try again.")  # แสดงข้อความหากป้อนตัวเลือกไม่ถูกต้อง

    print("Exiting...")  # แสดงข้อความบอกว่าโปรแกรมกำลังจะออก