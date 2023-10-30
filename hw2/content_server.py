import sys
import ast
import socket, sys
import threading
import json 
import time
BUFSIZE = 1024  # size of receiving buffer

node_info = dict() #stores info like uuid, name, port, peer_count
node_neighbors = dict()
seq_dict = dict()
seq_dict_lock = threading.Lock()
stored_lsa = dict()
lsa_lock = threading.Lock()
inactive_nodes = set()

seq = 1
s = None
threads_running = False

def send_ack(msg):
    global seq_dict
    _, info, _, _ = msg.split("|")
    neigh_info = ast.literal_eval(info)
    name, uuid, hostname, backend_port, distance_metric = neigh_info["name"], neigh_info["uuid"], "localhost", neigh_info["backend_port"], neigh_info["distance_metric"]
    if uuid not in node_neighbors:
        neigh_info = {"uuid": uuid, 
                        "hostname" : hostname,
                        "backend_port" : backend_port, 
                        "distance_metric": distance_metric,
                        "name": name,
                        "active": True,
                        "time": int(time.time())}
        node_neighbors[uuid] = neigh_info
        with seq_dict_lock:
            seq_dict[name] = 0

    else: 
        node_neighbors[uuid]["time"] = int(time.time())
        node_neighbors[uuid]["name"] = name
        node_neighbors[uuid]["active"] = True
        with seq_dict_lock:
            if name not in seq_dict:
                seq_dict[name] = 0


def receive_lsa(msg):
    global seq_dict
    global stored_lsa
    _,sender_name, sender_seq, sender_neighbors = msg.split("|")

    with seq_dict_lock:
        if sender_name not in seq_dict:
            seq_dict[sender_name] = int(sender_seq)

        if seq_dict[sender_name] > int(sender_seq):
            return
        seq_dict[sender_name] = int(sender_seq)

    #store LSA in table
    neighbors = json.loads(sender_neighbors)
    with lsa_lock:
        stored_lsa[sender_name] = neighbors

    copy_neighbors = json.dumps(node_neighbors)
    neigh_data = json.loads(copy_neighbors)

    for n in neigh_data:
        data = neigh_data[n]
        
        if data["active"] and sender_name != data["name"] :
            server_address = data["hostname"]
            server_port = int(data["backend_port"])
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.sendto(msg.encode(), (server_address, server_port))
            s.close() #close port 

    
def client():
    # create socket
    s.setblocking(0)

    # main loop
    while threads_running:
        # accept a packet
        
        try: 
            msg, addr = s.recvfrom(BUFSIZE)
            msg = msg.decode()

            if "sendKA" in msg:
                send_ack(msg)
            elif "LSA" in msg:
                receive_lsa(msg)
        except:
            pass
    s.close()
    return 
            
def check_active_nodes():
    global seq_dict
    while threads_running:
        copy_neighbors = json.dumps(node_neighbors)
        neigh_data = json.loads(copy_neighbors)
        for n in neigh_data:
            timestamp = neigh_data[n]["time"]
            if timestamp != None and (int(time.time()) - timestamp) > 5:
                uuid = neigh_data[n]["uuid"]
                node_neighbors[uuid]["active"] = False
                node_neighbors[uuid]["time"] = None

                #map logic 
                with seq_dict_lock:
                    seq_dict[node_neighbors[uuid]["name"]] = 0

    return 

def keep_alive():
    while threads_running:
        copy_neighbors = json.dumps(node_neighbors)
        neigh_data = json.loads(copy_neighbors)
        for n in neigh_data:
            data = neigh_data[n]
            server_address = data["hostname"]
            server_port = int(data["backend_port"])

            # create socket
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

            node_msg = {"name":node_info["name"], "uuid": node_info["uuid"], "backend_port": node_info["backend_port"], "distance_metric" : int(data["distance_metric"])}
            msg_string = "sendKA "+ "|" + str(node_msg) +  "|"  + " -> " + "|" + data["uuid"] 

            # send message to server
            s.sendto(msg_string.encode(), (server_address, server_port))
            s.close() #close port 
        time.sleep(2) #adding 2 second delay before sending out next round of keep alives
    return 


def return_uuid():
    print({"uuid":node_info["uuid"]})
 
def add_neighbor(msg):
    _,iid, host, port, metric = msg.split()
    uuid = iid.split("=")[1]
    hostname = host.split("=")[1]
    backend_port = port.split("=")[1]
    distance_metric = metric.split("=")[1]
    info = {"uuid": uuid.strip(), 
            "hostname" : hostname.strip(),
            "backend_port" : backend_port.strip(), 
            "distance_metric": distance_metric.strip(),
            "name": None,
            "active": False,
            "time": None}
        
    node_neighbors[uuid.strip()] = info

def return_neighbors():
    output = {"neighbors": dict()}
    copy_neighbors = json.dumps(node_neighbors)
    neigh_data = json.loads(copy_neighbors)
    for n in neigh_data:
        data = neigh_data[n]
        if data["active"]:
            output["neighbors"][data["name"]] = {"uuid": data["uuid"], 
                                                "host": data["hostname"],
                                                "backend_port": int(data["backend_port"]),
                                                "metric": int(data["distance_metric"])}
    print(output)

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
                uuid, hostname, backend_port, distance_metric = value.split(",")
                info = {"uuid": uuid.strip(), 
                        "hostname" : hostname.strip(),
                        "backend_port" : backend_port.strip(), 
                        "distance_metric": distance_metric.strip(),
                        "name": None,
                        "active": False,
                        "time": None}

                node_neighbors[uuid.strip()] = info

def link_state_ad():
    while threads_running:
        copy_neighbors = json.dumps(node_neighbors)
        neigh_data = json.loads(copy_neighbors)
        
        for n in neigh_data:
            data = neigh_data[n]
            if data["active"]:
                server_address = data["hostname"]
                server_port = int(data["backend_port"])  
                global seq
                # create socket
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                msg = "LSA" + "|" + node_info["name"] + "|" + str(seq) + "|" + copy_neighbors

                seq += 1

                s.sendto(msg.encode(), (server_address, server_port))
                s.close() #close port 
        time.sleep(2)
    return 

def construct_map():
    global inactive_nodes
    new_graph = dict()
    #go through nodes to current node
    copy_neighbors = json.dumps(node_neighbors)
    neigh_data = json.loads(copy_neighbors)
    
    initial_neighbors = dict()
    for n in neigh_data:
        data = neigh_data[n]
        if data["active"]:
            if data["name"] in inactive_nodes: inactive_nodes.remove(data["name"])
            initial_neighbors[data["name"]] = int(data["distance_metric"])
        else:
             inactive_nodes.add(data["name"])

    new_graph[node_info["name"]] = initial_neighbors
    global stored_lsa
    with lsa_lock:
        for n in stored_lsa:
            if n not in inactive_nodes:
                #active_neighbors = dict()
                neighbors = stored_lsa[n]
                for uuid in neighbors:
                    if not neighbors[uuid]["active"]:
                        inactive_nodes.add(neighbors[uuid]["name"])

        #print(inactive_nodes, "1")
        for n in stored_lsa:
            if n not in inactive_nodes:
                active_neighbors = dict()
                neighbors = stored_lsa[n]
                for uuid in neighbors:
                    if neighbors[uuid]["active"]:
                        if neighbors[uuid]["name"] in inactive_nodes: inactive_nodes.remove(neighbors[uuid]["name"])
                        name = neighbors[uuid]["name"]
                        metric = neighbors[uuid]["distance_metric"]
                        active_neighbors[name] = int(metric)
                    else:
                        inactive_nodes.add(neighbors[uuid]["name"])

                new_graph[n] = active_neighbors
        #print(inactive_nodes, "2")
    
    print({"map":new_graph})


if __name__ == '__main__':
    command = sys.argv[1]
    config_file = sys.argv[2]
    set_configuration(config_file)


    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    SERVER_PORT = int(node_info["backend_port"])
    s.bind(("localhost", SERVER_PORT))

    keep_alive_messages = threading.Thread(target=keep_alive)
    check_nodes = threading.Thread(target=check_active_nodes)
    client_thread = threading.Thread(target=client)
    link_state_thread = threading.Thread(target=link_state_ad)
    threads = [client_thread, keep_alive_messages,check_nodes, link_state_thread]
    
    threads_running = True
    
    for t in threads:
        t.start()

    while True:
        msg_string = input()

        if msg_string == "uuid":
            return_uuid()
        elif msg_string == "neighbors":
            return_neighbors()
        elif "addneighbor" in msg_string:
            add_neighbor(msg_string)
        elif msg_string == "kill":
            threads_running = False
            for t in threads:
                t.join()
            s.close()
            exit(0)
        elif msg_string == "print_neighbour":
            print(node_neighbors)
        elif "map" in msg_string:
            construct_map()
            # print({"map": dict()})
        elif "rank" in msg_string:
            print({"rank":dict()})
        elif "sequence_info" in msg_string:
            print(seq_dict)
        elif "lsa" in msg_string:
            print(stored_lsa)
        elif "removed" in msg_string:
            print(inactive_nodes)