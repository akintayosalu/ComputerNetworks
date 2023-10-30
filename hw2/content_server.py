import sys
import ast
import socket, sys
import threading
import json 
import time
import heapq
BUFSIZE = 1024  # size of receiving buffer

node_info = dict() #stores info like uuid, name, port, peer_count
node_neighbors = dict() #stores info on node's neighbors
seq_dict = dict() #stores sequence number for received LSAs
seq_dict_lock = threading.Lock() 
stored_lsa = dict()
lsa_lock = threading.Lock() #lock for stored LSA acces
inactive_nodes = set() #stores inactive nodes in entire graph based on LSAs 
graph = dict()
graph_lock = threading.Lock() #lock for accesing graph
seq = 1 #sequence number for LSAs 
s = None #client socket 
threads_running = False #flag to inform threads to keep running 

#helper to accept keep alive messages and update node's neighbors as required 
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
        #update time a keep alive from a certain neighbor was received 
        node_neighbors[uuid]["time"] = int(time.time())
        node_neighbors[uuid]["name"] = name
        node_neighbors[uuid]["active"] = True
        with seq_dict_lock:
            if name not in seq_dict:
                seq_dict[name] = 0

#helper that receives recent LSAs and stores it
def receive_lsa(msg):
    global seq_dict
    global stored_lsa
    _,sender_name, sender_seq, sender_neighbors = msg.split("|")

    with seq_dict_lock:
        if sender_name not in seq_dict:
            seq_dict[sender_name] = int(sender_seq)
        #discard LSA if sequence number is < last stored LSA from specific neighbor
        if seq_dict[sender_name] > int(sender_seq):
            return
        seq_dict[sender_name] = int(sender_seq)

    #store LSA in table
    neighbors = json.loads(sender_neighbors)
    with lsa_lock:
        stored_lsa[sender_name] = neighbors

    copy_neighbors = json.dumps(node_neighbors)
    neigh_data = json.loads(copy_neighbors)

    #forward received LSA to neighbors
    for n in neigh_data:
        data = neigh_data[n]
        
        if data["active"] and sender_name != data["name"] :
            server_address = data["hostname"]
            server_port = int(data["backend_port"])
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.sendto(msg.encode(), (server_address, server_port))
            s.close() #close port 

#receives incoming packets
def client():
    # create socket
    s.setblocking(0) #needed as s.recvfrom(BUFSIZE) blocks if there are no incoming packets

    while threads_running:
        # accept a packet
        try: 
            msg, addr = s.recvfrom(BUFSIZE)
            msg = msg.decode()
        
            if "sendKA" in msg: #receiving a keep alive
                send_ack(msg)
            elif "LSA" in msg: #receiving link state advetisement
                receive_lsa(msg)
        except:
            pass
    s.close()
    return 

#checks last time a neighbor sent out keep alive to determine inactive nodes     
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

                with seq_dict_lock:
                    seq_dict[node_neighbors[uuid]["name"]] = 0

    return 

#sends keep alive messages to immediate neighbors to find inactive nodes
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

#returns uuid of current node
def return_uuid():
    print({"uuid":node_info["uuid"]})

#adds neighbor to node's neighbors
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

#returns the active neighbors from the node's neighbors
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

#grabs information from config file
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

#sends out LSAs to neighbors
def link_state_ad():
    while threads_running:
        copy_neighbors = json.dumps(node_neighbors)
        neigh_data = json.loads(copy_neighbors)
        
        #go through neighbors and send out LSAs (current state of node's neighbors)
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

#returns the map of the graph based on LSAs
def construct_map():
    while threads_running:
        global inactive_nodes
        new_graph = dict()
        copy_neighbors = json.dumps(node_neighbors)
        neigh_data = json.loads(copy_neighbors)
        
        #add immediate neighbors to graph
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
            #get inactive nodes
            for n in stored_lsa:
                if n not in inactive_nodes:
                    neighbors = stored_lsa[n]
                    for uuid in neighbors:
                        if not neighbors[uuid]["active"]:
                            inactive_nodes.add(neighbors[uuid]["name"])

            #build the graph
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

        global graph
        with graph_lock:
            graph = new_graph
        time.sleep(2)

#returns the rank at current node
def construct_rank():
    #Dijkstra's Algorithm
    root = node_info["name"]
    dist_d = dict()
    global stored_lsa
    with lsa_lock:
        for n in stored_lsa:
            dist_d[n] = float('inf')
    dist_d[root] = 0
    minHeap = [(dist_d[root],root)]
    heapq.heapify(minHeap)

    seen = set()
    global graph
    with graph_lock:
        while minHeap:
            dist, curr = heapq.heappop(minHeap)
            if curr not in seen:
                for n in graph[curr]:
                    if  dist_d[n] > dist + graph[curr][n]:
                        dist_d[n] = dist + graph[curr][n]
                        heapq.heappush(minHeap,(dist + graph[curr][n],n))
                seen.add(curr)

    ranking = dict()
    for n in dist_d:
        if n != root and dist_d[n] != float('inf'):
            ranking[n] = dist_d[n]

    print({"rank":ranking})



if __name__ == '__main__':
    command = sys.argv[1]
    config_file = sys.argv[2] #get config file
    set_configuration(config_file)

    #create socket for client
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    SERVER_PORT = int(node_info["backend_port"])
    s.bind(("localhost", SERVER_PORT))

    #initialize threads for different functions that run continuously
    keep_alive_messages = threading.Thread(target=keep_alive) #send keep alives
    check_nodes = threading.Thread(target=check_active_nodes) #check for inactive nodes
    client_thread = threading.Thread(target=client) #receives incoming messages
    link_state_thread = threading.Thread(target=link_state_ad) #send link state advertisements
    build_graph_thread  = threading.Thread(target=construct_map) #builds graph from LSA
    threads = [client_thread, keep_alive_messages,check_nodes, link_state_thread,build_graph_thread]
    
    threads_running = True
    
    #starts threads 
    for t in threads:
        t.start()

    #gets input from the cmdline and calls
    #relevant function
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
            #closes threads 
            for t in threads:
                t.join()
            s.close()
            exit(0)
        elif "map" in msg_string:
            with graph_lock:
                print({"map":graph})
        elif "rank" in msg_string:
            construct_rank()