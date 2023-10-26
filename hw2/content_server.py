import sys
import ast
import socket, sys
import threading

BUFSIZE = 1024  # size of receiving buffer

node_info = dict() #stores info like uuid, name, port, peer_count
node_neighbors = dict()
present_neighbors = dict()

def keep_alive():
    for n in node_neighbors:
        server_address = node_neighbors[n]["hostname"]
        server_port = int(node_neighbors[n]["backend_port"])
        # create socket
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.setblocking(0) #make non-blocking 
        # generate message
        msg_string = node_info["uuid"] + " -> " + node_neighbors[n]["uuid"]

        # send message to server
        s.sendto(msg_string.encode(), (server_address, server_port))

        try:
            # get echo message
            echo_string, addr = s.recvfrom(BUFSIZE)
            # print echo message
            print('Echo from the server: '+echo_string.decode(),flush=True)
        except socket.error as e:
            # If no data is available, an error will be raised
            pass

        s.close() #close port 

def client():
    while True:
        keep_alive()
    #sys.exit(0) dont really want to exit program

def receive():
    # create socket
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    SERVER_PORT = int(node_info["backend_port"])
    s.bind(("localhost", SERVER_PORT))

    # main loop
    while True:
        # accept a packet
        dgram, addr = s.recvfrom(BUFSIZE)
        dgram = dgram.decode()

        # print the message
        print('New connection from '+str(addr[0])+':'+str(addr[1])+'; Message: '+dgram,flush=True)

        # echo the message back
        s.sendto(dgram.encode(), addr)

    # exit
    s.close()
    sys.exit(0)

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
                uuid, hostname, backend_port, distance_metric = value.split(",")
                node_neighbors[key] = {"uuid": uuid.strip(), 
                                       "hostname" : hostname.strip(),
                                        "backend_port" : backend_port.strip(), 
                                         "distance_metric": distance_metric.strip(),
                                          "name": None,
                                           "active": False}

def return_neighbors():
    output = {"neighbors": dict()}
    for n in node_neighbors:
        if node_neighbors[n]["active"]:
            output["neighbors"][node_neighbors[n]["name"]] = {"uuid": node_neighbors[n]["uuid"], 
                                                              "host": node_neighbors[n]["hostname"],
                                                              "backend_port": int(node_neighbors[n]["backend_port"]),
                                                              "metric": int(node_neighbors[n]["distance_metric"])}
    output = str(output)
    print(ast.literal_eval(output),flush=True)

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
        continue

    # for line in sys.stdin:
    #     print(sys.stdin)
            
    #     if "uuid" == line.strip():
    #         output = str({"uuid":node_info["uuid"]})
    #         print(ast.literal_eval(output))
    #     elif "neighbors" == line.strip():
    #         return_neighbors()

    #     if "Exit" == line.strip():
    #         break