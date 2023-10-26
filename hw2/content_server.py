import sys
import ast
import socket, sys



SERVER_HOST = ''  # Symbolic name, meaning all available interfaces
BUFSIZE = 1024  # size of receiving buffer

node_info = dict() #stores info like uuid, name, port, peer_count
node_neighbors = dict()
present_neighbors = dict()

def client():
    server_address = node_neighbors["peer_0"]["hostname"]
    server_port = int(node_neighbors["peer_0"]["backend_port"])
    #MAKE IT A FOR LOOP INSTEAD but for testing leave it like this!!

    # create socket
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # get message from keyboard
    msg_string = input('Send this to the server: ')

    # send message to server
    s.sendto(msg_string.encode(), (server_address, server_port))

    # get echo message
    echo_string, addr = s.recvfrom(BUFSIZE)

    # print echo message
    print('Echo from the server: '+echo_string.decode())

    # exit
    s.close()
    sys.exit(0)

def server():
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
        print('New connection from '+str(addr[0])+':'+str(addr[1])+'; Message: '+dgram)

        # echo the message back
        s.sendto(dgram.encode(), addr)

    # exit
    s.close()
    sys.exit(0)

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
    print(ast.literal_eval(output))

if __name__ == '__main__':
    command = sys.argv[1]
    config_file = sys.argv[2]
    set_configuration(config_file)

    if node_info["uuid"] == "825ced20-72f6-11ee-b962-0242ac120002":
        client()
    elif node_info["uuid"] == "9148a284-72f6-11ee-b962-0242ac120002":
        server()
    
    # for line in sys.stdin:
        
    #     if "uuid" == line.strip():
    #         output = str({"uuid":node_info["uuid"]})
    #         print(ast.literal_eval(output))
    #     elif "neighbors" == line.strip():
    #         return_neighbors()

    #     if "Exit" == line.strip():
    #         break
