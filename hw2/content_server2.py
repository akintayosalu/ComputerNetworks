import sys
import ast
import socket, sys
import threading
import json 
BUFSIZE = 1024  # size of receiving buffer

node_info = dict() #stores info like uuid, name, port, peer_count
node_neighbors = dict()
present_neighbors = dict()

count = 0
lock = threading.Lock()
print_lock = threading.Lock()


def keep_alive():
    while True:
        copy_neighbors = json.dumps(node_neighbors)
        neigh_data = json.loads(copy_neighbors)
        for n in neigh_data:
            data = neigh_data[str(n)]
            server_address = data["hostname"]
            server_port = int(data["backend_port"])

            # create socket
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

            node_msg = {"name":node_info["name"], "uuid": node_info["uuid"], "backend_port": node_info["backend_port"], "distance_metric" : int(data["distance_metric"])}
            msg_string = "sendKA "+ "|" + str(node_msg) +  "|"  + " -> " + "|" + data["uuid"] 

            # send message to server
            s.sendto(msg_string.encode(), (server_address, server_port))
            s.close() #close port 

def client():
    # create socket
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    SERVER_PORT = int(node_info["backend_port"])
    s.bind(("localhost", SERVER_PORT))

    # main loop
    while True:
        # accept a packet
        msg, addr = s.recvfrom(BUFSIZE)
        msg = msg.decode()

        if "sendKA" in msg:
            send_ack(msg)
        elif "confirmKA" in msg:
            neigh_uuid = msg.split()[1]
            idx = present_neighbors[neigh_uuid] 
            node_neighbors[idx]["name"] = msg.split()[2]
            node_neighbors[idx]["active"] = True

def send_ack(msg):
    _, info, _, _ = msg.split("|")
    neigh_info = ast.literal_eval(info)
    name, uuid, hostname, backend_port, distance_metric = neigh_info["name"], neigh_info["uuid"], "localhost", neigh_info["backend_port"], neigh_info["distance_metric"]
    global count
    with lock:
        neigh_info = {"uuid": uuid, 
                                "hostname" : hostname,
                                "backend_port" : backend_port, 
                                "distance_metric": distance_metric,
                                    "name": name,
                                    "active": True}
        node_neighbors[count] = neigh_info
        present_neighbors[uuid] = count
        count += 1

    server_address = "localhost"
    server_port = backend_port
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # send acknowledgement msg
    msg_string = "confirmKA " + node_info["uuid"] + " " + node_info["name"]

    # send message to server
    s.sendto(msg_string.encode(), (server_address, int(server_port)))
    s.close()

def return_uuid():
    output = str({"uuid":node_info["uuid"]})
    print(ast.literal_eval(output))

def add_neighbor(msg):
    global count
    with lock:
        print(msg.split(" "))
        _,iid, host, port, metric = msg.split()
        print(iid, host, port, metric)
        uuid = iid.split("=")[1]
        hostname = host.split("=")[1]
        backend_port = port.split("=")[1]
        distance_metric = metric.split("=")[1]
        info = {"uuid": uuid.strip(), 
                    "hostname" : "localhost",
                        "backend_port" : backend_port.strip(), 
                            "distance_metric": distance_metric.strip(),
                                "name": None,
                                     "active": False}
        node_neighbors[count] = info
        present_neighbors[uuid.strip()] = count
        count += 1
        #print(node_neighbors)
            

def receive():
    keep_alive_messages = threading.Thread(target=keep_alive, daemon=True)
    keep_alive_messages.start()

def server():
    receive()

def set_configuration(config_file):
    file1 = open(config_file, "r")
    config_lines = file1.readlines()
    for line in config_lines: 
        key, value = line.strip().split("=")
        key, value = key.strip(), value.strip()
        if "peer_" not in key:
            node_info[key] = value
        else:
            if key == "peer_count":
                node_info[key] = value
            else:
                #add mapping of temp 
                #handling info on neighbor to node 
                global count
                with lock:
                    uuid, hostname, backend_port, distance_metric = value.split(",")
                    info = {"uuid": uuid.strip(), 
                                        "hostname" : "localhost",
                                            "backend_port" : backend_port.strip(), 
                                            "distance_metric": distance_metric.strip(),
                                            "name": None,
                                            "active": False}

                    node_neighbors[count] = info
                    present_neighbors[uuid.strip()] = count
                    count += 1

def return_neighbors():
    output = {"neighbors": dict()}
    copy_neighbors = json.dumps(node_neighbors)
    neigh_data = json.loads(copy_neighbors)
    for n in neigh_data:
        data = neigh_data[str(n)]
        if data["active"]:
            output["neighbors"][data["name"]] = {"uuid": data["uuid"], 
                                                    "host": data["hostname"],
                                                        "backend_port": int(data["backend_port"]),
                                                            "metric": int(data["distance_metric"])}
    output = str(output)
    print(ast.literal_eval(output))

if __name__ == '__main__':
    command = sys.argv[1]
    config_file = sys.argv[2]
    set_configuration(config_file)

    server_thread = threading.Thread(target=server, daemon=True)
    client_thread = threading.Thread(target=client, daemon=True)
    threads = [client_thread, server_thread]
    
    for t in threads:
        t.start()

    while True:
        msg_string = input("Input command for system ")

        if msg_string == "uuid":
            return_uuid()
        elif msg_string == "neighbors":
            return_neighbors()
        elif "addneighbor" in msg_string:
            add_neighbor(msg_string)
        elif msg_string == "kill":
            exit()

        