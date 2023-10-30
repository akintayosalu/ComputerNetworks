import sys
import ast
import socket, sys
import threading
import json 
import time
BUFSIZE = 1024  # size of receiving buffer

node_info = dict() #stores info like uuid, name, port, peer_count
node_neighbors = dict()
#node_names = set()
deleted = set()
graph = dict()
seq_dict = dict()
seq = 1
s = None
threads_running = False

def send_ack(msg):
    global graph
    global seq 
    global deleted 
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

        #logic for building graph
        graph[node_info["name"]][name] = int(distance_metric)
        #print(graph)
        seq_dict[name] = [0,set()]
        #node_names.add(name)
    else:
        #updating last time keep alive from neighbour was received 
        #idx = present_neighbors[uuid] 
        node_neighbors[uuid]["time"] = int(time.time())
        node_neighbors[uuid]["name"] = name
        node_neighbors[uuid]["active"] = True

        #logic for map 
        #print(graph)
        graph[node_info["name"]][name] = int(distance_metric)
        #node_names.add(name)
        if name not in seq_dict:
            seq_dict[name] = [0,set()]

        if name in deleted:
            deleted.remove(name)

def receive_lsa(msg):
    global seq_dict
    _,sender_name, sender_seq, str_grap = msg.split("|")
    #print(int(sender_seq), seq_dict[sender_name][0],sender_name)
    # print(seq_dict[sender_name][0], int(sender_seq))
    if seq_dict[sender_name][0] > int(sender_seq):
        return
    # print(seq_dict[sender_name][0], int(sender_seq))
    seq_dict[sender_name][0] = int(sender_seq)

    new_graph = dict()
    sender_graph = ast.literal_eval(str_grap)
    
    # print("SENDER ", sender_graph)
    global graph
    global deleted 
    
    # print("NODE ", graph)
    # print()
    sender_nodes = sender_graph.keys()
    # print("S/N ", sender_nodes)
    node_names = graph.keys()
    # print("node_names ", node_names)
    

    # print("1 ", new_graph)
    #same nodes to add to graph
    for n in sender_nodes:
        if n in node_names:
            # same_nodes.add(n)
            if n != node_info["name"]:
                new_graph[n] = sender_graph[n]
            else:
                new_graph[n] = graph[n]

    # print("2 ", new_graph)
    #new nodes to add 
    for n in sender_nodes:
        if n not in node_names and n not in deleted:
            new_graph[n] = sender_graph[n]
            seq_dict[sender_name][1].add(n)

    # print("3 ", new_graph)
    #nodes to remove 
    for n in node_names:
        if n not in sender_nodes and n not in seq_dict[sender_name][1]:
            new_graph[n] = graph[n]
        elif n not in sender_nodes and n in seq_dict[sender_name][1]:
            seq_dict[sender_name][1].remove(n)

    # print("4 ", new_graph)
    #global graph
    graph = new_graph
    
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
                #print("here")
                #print(msg)
                receive_lsa(msg)
        except:
            pass
    s.close()
    return 
            
def check_active_nodes():
    while threads_running:
        copy_neighbors = json.dumps(node_neighbors)
        neigh_data = json.loads(copy_neighbors)
        for n in neigh_data:
            timestamp = neigh_data[n]["time"]
            if timestamp != None and (int(time.time()) - timestamp) > 5:
                #print("HERE")
                #then it is inactive
                uuid = neigh_data[n]["uuid"]
                #idx = present_neighbors[uuid] 
                node_neighbors[uuid]["active"] = False
                node_neighbors[uuid]["time"] = None

                #print(node_neighbors[uuid]["name"])
                #extra logic 
                #node_names.remove(node_neighbors[uuid]["name"])
                global graph 
                global seq_dict
                global deleted
                seq_dict[node_neighbors[uuid]["name"]] = [0,set()]
                
                del graph[node_neighbors[uuid]["name"]] #REMOVE node: {neighbors} from graph
                del graph[node_info["name"]][node_neighbors[uuid]["name"]] # removed node from ROOT NODE neighbors dict
                deleted.add(node_neighbors[uuid]["name"])
                # print("DELETING ", node_neighbors[uuid]["name"])
                # print(graph)

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
        time.sleep(1) #adding 2 second delay before sending out next round of keep alives
    return 


def return_uuid():
    #output = str({"uuid":node_info["uuid"]})
    print({"uuid":node_info["uuid"]})
    #print(ast.literal_eval(output))
 
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
        copy_graph = json.dumps(graph)
        
        for n in neigh_data:
            data = neigh_data[n]
            if data["active"]:
                server_address = data["hostname"]
                server_port = int(data["backend_port"])  
                global seq
                # create socket
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                msg = "LSA" + "|" + node_info["name"] + "|" + str(seq) + "|" + copy_graph
                #print(msg)

                
                seq += 1

                s.sendto(msg.encode(), (server_address, server_port))
                s.close() #close port 
        time.sleep(1)
    return 



def initialize_graph():
    global graph 
    graph = {node_info["name"]: dict()}
    #print(graph)

if __name__ == '__main__':
    command = sys.argv[1]
    config_file = sys.argv[2]
    set_configuration(config_file)
    initialize_graph()

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
            print(graph)
        elif "rank" in msg_string:
            print({"rank":dict()})
        elif "sequence_info" in msg_string:
            print(seq_dict)