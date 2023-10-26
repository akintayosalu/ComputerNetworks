import sys
import ast
# for line in sys.stdin:
#     if "Exit" == line.strip():
#         break
#     print("Nada")
# print("Done")

node_info = dict() #stores info like uuid, name, port, peer_count
node_neighbors = dict()

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
                #handling info on neighbor to node 
                uuid, hostname, backend_port, distance_metric = value.split(",")
                node_neighbors[key] = {"uuid": uuid.strip(), 
                                       "hostname" : hostname.strip(),
                                        "backend_port" : backend_port.strip(), 
                                         "distance_metric": distance_metric.strip()}

if __name__ == '__main__':
    command = sys.argv[1]
    config_file = sys.argv[2]
    set_configuration(config_file)
    
    for line in sys.stdin:
        
        if "uuid" == line.strip():
            output = str({"uuid":node_info["uuid"]})
            print(ast.literal_eval(output))
        if "Exit" == line.strip():
            break
