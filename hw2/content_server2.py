import sys
import ast
import socket, sys
import threading
import json 
import time
BUFSIZE = 1024  # size of receiving buffer

node_info = dict() #stores info like uuid, name, port, peer_count
node_neighbors = dict()
present_neighbors = dict()

count = 0
lock = threading.Lock()
print_lock = threading.Lock()

def send_ack(msg):
    _, info, _, _ = msg.split("|")
    neigh_info = ast.literal_eval(info)
    name, uuid, hostname, backend_port, distance_metric = neigh_info["name"], neigh_info["uuid"], "localhost", neigh_info["backend_port"], neigh_info["distance_metric"]
    if uuid not in present_neighbors:
        global count
        with lock:
            neigh_info = {"uuid": uuid, 
                          "hostname" : hostname,
                          "backend_port" : backend_port, 
                          "distance_metric": distance_metric,
                          "name": name,
                          "active": True,
                          "time": int(time.time())}
            node_neighbors[count] = neigh_info
            present_neighbors[uuid] = count
            count += 1
    else:
        #need to test this 
        idx = present_neighbors[uuid] 
        node_neighbors[idx]["time"] = int(time.time())
        node_neighbors[idx]["name"] = name
        node_neighbors[idx]["active"] = True
        #(node_neighbors[idx]["time"],node_neighbors[idx]["name"])
        #add some logic here 

    # server_address = "localhost"
    # server_port = backend_port
    # s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # # send acknowledgement msg
    # node_msg = {"name":node_info["name"], "uuid": node_info["uuid"], "backend_port": node_info["backend_port"], "distance_metric" : distance_metric}
    # msg_string = "confirmKA " + node_info["uuid"] + " " + node_info["name"] + " " + str(node_msg)

    # # send message to server
    # s.sendto(msg_string.encode(), (server_address, int(server_port)))
    # s.close()

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
        # elif "confirmKA" in msg:
        #     neigh_uuid = msg.split()[1]
        #     if neigh_uuid in present_neighbors:
        #         idx = present_neighbors[neigh_uuid] 
        #         node_neighbors[idx]["name"] = msg.split()[2]
        #         node_neighbors[idx]["active"] = True
        #     else:
        #         print(msg.split()[3])
        #         neigh_info = ast.literal_eval(msg.split()[3])
        #         name, uuid, hostname, backend_port, distance_metric = neigh_info["name"], neigh_info["uuid"], "localhost", neigh_info["backend_port"], neigh_info["distance_metric"]
        #         global count
        #         with lock:
        #             neigh_info = {"uuid": uuid, 
        #                         "hostname" : hostname,
        #                         "backend_port" : backend_port, 
        #                         "distance_metric": distance_metric,
        #                         "name": name,
        #                         "active": True,
        #                         "time": int(time.time())}
        #             node_neighbors[count] = neigh_info
        #             present_neighbors[uuid] = count
        #             count += 1



            
def check_active_nodes():
    while True:
        copy_neighbors = json.dumps(node_neighbors)
        neigh_data = json.loads(copy_neighbors)
        for n in neigh_data:
            timestamp = neigh_data[str(n)]["time"]
            if timestamp != None and (int(time.time()) - timestamp) > 5:
                #then it is inactive
                uuid = neigh_data[str(n)]["uuid"]
                idx = present_neighbors[uuid] 
                node_neighbors[idx]["active"] = False
                node_neighbors[idx]["time"] = None
                #del node_neighbors[idx]
                #del present_neighbors[uuid]
                #print("Removing " + uuid)

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

def receive():
    keep_alive_messages = threading.Thread(target=keep_alive, daemon=True)
    check_nodes = threading.Thread(target=check_active_nodes, daemon=True)

    threads = [keep_alive_messages, check_nodes]
    for t in threads:
        t.start()
    # keep_alive_messages.start()
    # check_active_nodes.start()

def server():
    receive()

def return_uuid():
    output = str({"uuid":node_info["uuid"]})
    print(ast.literal_eval(output))

def add_neighbor(msg):
    global count
    with lock:
        _,iid, host, port, metric = msg.split()
        uuid = iid.split("=")[1]
        hostname = host.split("=")[1]
        backend_port = port.split("=")[1]
        distance_metric = metric.split("=")[1]
        info = {"uuid": uuid.strip(), 
                "hostname" : "localhost",
                "backend_port" : backend_port.strip(), 
                "distance_metric": distance_metric.strip(),
                "name": None,
                "active": False,
                "time": None}
        
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
                uuid, hostname, backend_port, distance_metric = value.split(",")
                info = {"uuid": uuid.strip(), 
                        "hostname" : "localhost",
                        "backend_port" : backend_port.strip(), 
                        "distance_metric": distance_metric.strip(),
                        "name": None,
                        "active": False,
                        "time": None}

                node_neighbors[count] = info
                present_neighbors[uuid.strip()] = count
                count += 1

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
            sys.exit(0)
        elif msg_string == "print_neighbour":
            print(str(node_neighbors))
        elif msg_string == "print_present":
            print(str(present_neighbors))

        