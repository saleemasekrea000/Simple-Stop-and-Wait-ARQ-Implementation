import socket
import argparse
import math

MAX_SEGMENT_SIZE = 20476


class Client:
    def __init__(self, address, filename, filesize):
        self.address = address
        self.filename = filename
        self.filesize = int(filesize)
        self.received_size = 0
        self.received_data = b""
        self.current_chunk = 0
        self.total_chunks = math.ceil(self.filesize / MAX_SEGMENT_SIZE)
        self.last_acknowledged_chunk = -1


def serve(server_socket, max_connections):
    clients = []
    try:
        print(f"{server_socket.getsockname()}: Listening...")
        while True:
            data, address = server_socket.recvfrom(20480)
            print(f"{address}: {data.decode()}")

            message = data.decode().split("|")
            if message[0] == "s":
                start_message(
                    server_socket,
                    clients,
                    address,
                    message[1],
                    message[2],
                    message[3],
                    max_connections,
                )
            elif message[0] == "d":
                print(f"{address}: {message[0]}|{message[1]}|chunk{message[1]}")
                data_message(server_socket, clients, address, message[1], message[2])
            else:
                print("Opssssss Invalid message type received. Closing connection...")
                break
    except KeyboardInterrupt:
        print(f"{server_socket.getsockname()}: Shutting down...")
    finally:
        server_socket.close()


def start_message(
    server_socket,
    clients,
    address,
    sequence_number,
    filename,
    filesize,
    max_connections,
):

    client = Client(address, filename, filesize)
    for existing_client in clients:
        if existing_client.address == address:
            print(
                f"User already exists. Ignoring request from {filename} at {address}."
            )
            sequence_number = (int(sequence_number) + 1) % 2
            acknowledgment_message = f"a|{sequence_number}".encode()
            server_socket.sendto(acknowledgment_message, address)
            return

    client.last_acknowledged_chunk = int(sequence_number)
    sequence_number = (int(sequence_number) + 1) % 2
    clients.append(client)
    if len(clients) >= max_connections:
        acknowledgment_message = f"n|{sequence_number}".encode()
        server_socket.sendto(acknowledgment_message, address)
        return
    acknowledgment_message = f"a|{sequence_number}".encode()
    server_socket.sendto(acknowledgment_message, address)


def data_message(server_socket, clients, address, sequence_number, data):
    current_client = None
    current_chunk = int(sequence_number)
    for existing_client in clients:
        if existing_client.address == address:
            current_client = existing_client
            break

    if current_client is None:
        print(f"Client with address {address} not found in the client list.")
        sn = (int(sequence_number) + 1) % 2
        server_socket.sendto(f"n|{sn}".encode(), address)
        return

    # here it was working fine until i saw the statement can tested the server  under constant delay and packet loss might effect
    if current_chunk == current_client.last_acknowledged_chunk:
        sequence_number = (int(sequence_number) + 1) % 2
        acknowledgment_message = f"a|{sequence_number}".encode()
        server_socket.sendto(acknowledgment_message, address)
        print(
            f"Duplicate message received for chunk {current_chunk}. Ignoring duplicate data."
        )
        return

    current_client.last_acknowledged_chunk = int(sequence_number)
    current_client.received_data += data.encode()
    current_client.received_size += len(data)
    current_client.current_chunk += 1
    sequence_number = (int(sequence_number) + 1) % 2
    acknowledgment_message = f"a|{sequence_number}".encode()
    server_socket.sendto(acknowledgment_message, address)
    if current_client.current_chunk == current_client.total_chunks:
        with open(current_client.filename, "wb") as f:
            f.write(current_client.received_data)
        print(f"{address}\tReceived {current_client.filename}")
        clients.remove(current_client)


def main():
    parser = argparse.ArgumentParser(description="UDP File Transfer Server")
    parser.add_argument("port", type=int, help="Port number to listen on")
    parser.add_argument(
        "max_connections", type=int, help="Maximum number of concurrent connections"
    )
    args = parser.parse_args()
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_socket.bind(("0.0.0.0", args.port))
    print(f"Server is listening on port {args.port}....")
    serve(server_socket, args.max_connections)


if __name__ == "__main__":
    main()
