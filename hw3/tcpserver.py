import json 
import sys
import socket
import threading
import os
import random
import struct 
import filecmp

node_info = dict()
peer_info = dict()
BUFSIZE = 2048  # size of receiving buffer
s = None #socket for receiving/sending bytes
transmitted_packets = dict()
port_to_hostname = dict()
received_bytes = [0,[]] #will have to handle ordering at some point
count = 0
threads_running = False
received_file = ""


def receive_handshake(src_port, dst_port, sequence_number, acknowledgement_number,data_length, syn, ack, data):
    syn, ack = 1,1
    acknowledgement_number = sequence_number + 1
    sequence_number = random.randint(0, 2**32 - 1)
    transmission = open(data, "rb")
    transmitted_packets[src_port] = [sequence_number,transmission] #need to also handle mutliple requests

    file_length_str = str(os.stat(data).st_size)
    new_data = bytes(file_length_str + (1024-len(file_length_str))*" ", 'utf-8')
    packed_data = struct.pack("HHLLHHH1024s", dst_port, src_port, sequence_number, acknowledgement_number,data_length, syn, ack, new_data)

    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.sendto(packed_data, (port_to_hostname[src_port], src_port))
    s.close() #close port
    return 

def send_ack(src_port, dst_port, sequence_number, acknowledgement_number,data_length, syn, ack, data):
    syn, ack = 0,1
    acknowledgement_number = sequence_number
    sequence_number = 0
    data = bytes(1024*" ", 'utf-8')

    packed_data = struct.pack("HHLLHHH1024s", dst_port, src_port, sequence_number, acknowledgement_number,data_length, syn, ack, data)
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.sendto(packed_data, (port_to_hostname[src_port], src_port))
    s.close() #close port
    return

def send_data(src_port, dst_port, sequence_number, acknowledgement_number,data_length, syn, ack, data):
    if acknowledgement_number == transmitted_packets[src_port][0]:
        f = transmitted_packets[src_port][1]
        packet_bytes = f.read(1024)
        # if len(packet_bytes) < 1024:
        #     f.close()

        sequence_number += len(packet_bytes)
        transmitted_packets[src_port][0] = sequence_number
        acknowledgement_number = 0
        data_length = len(packet_bytes)
        syn, ack = 1,0

        #build packet and send it 
        packed_data = struct.pack("HHLLHHH1024s", dst_port, src_port, sequence_number, acknowledgement_number,data_length, syn, ack, packet_bytes)
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.sendto(packed_data, (port_to_hostname[src_port], src_port))
        s.close() #close port
    else:
        pass #going to be used for retransmission
    return

def build_file():
    file_bytes = bytes().join(received_bytes[1])
    global received_file
    #fake_filename = "1" + received_file
    newFile = open(received_file, "wb")
    newFile.write(file_bytes)
    newFile.close()

    #just checking if copied file is the same as original
    #return_bool = filecmp.cmp(fake_filename, received_file, shallow=False)
    #print(return_bool)
    return


def print_received_packet(src_port, dst_port, sequence_number, acknowledgement_number, data_length, syn, ack, data):
    print(type(data))
    print("SRC PRT " + str(src_port))
    print("DST PORT " + str(dst_port))
    print("SEQ NUM " + str(sequence_number))
    print("ACK NUMBER" + str(acknowledgement_number))
    print("DATA LENGTH" + str(data_length))
    print("SYN/ACK " + str(syn) + "/" + str(ack))
    print("DATA " + str(data))
    return 

def send_fin(src_port, dst_port, sequence_number, acknowledgement_number,data_length, syn, ack, data):
    syn, ack = 0,0 # 0 ACK & 0 SYN working as a FIN here
    acknowledgement_number = sequence_number
    sequence_number = 0
    data = bytes(1024*" ", 'utf-8')

    packed_data = struct.pack("HHLLHHH1024s", dst_port, src_port, sequence_number, acknowledgement_number,data_length, syn, ack, data)
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.sendto(packed_data, (port_to_hostname[src_port], src_port))
    s.close() #close port
    return

def receive():
    global received_bytes, threads_running
    while threads_running:
        packet, addr = s.recvfrom(2048)
        src_port, dst_port, sequence_number, acknowledgement_number, data_length, syn, ack, data = struct.unpack("HHLLHHH1024s",packet)
        # print_received_packet(src_port, dst_port, sequence_number, acknowledgement_number, data_length, syn, ack, data)
        
        if syn == 1 and ack == 0:
            if data_length > 0:
                #complete packet sent (might not be the case for when we start doing windows and packet loss)
                if data_length != 1024:
                    received_bytes[1].append(data[0:data_length])
                    build_file()
                    received_bytes = [0,[]]  #empty out data from newly received file that has been created
                    #send fin to server 
                    send_fin(src_port, dst_port, sequence_number, acknowledgement_number,data_length, syn, ack, data)
                else:
                    received_bytes[1].append(data)
                    #send ACK back to server to receive more packets
                    send_ack(src_port, dst_port, sequence_number, acknowledgement_number,data_length, syn, ack, data)
            else:
                #server receiving first part of handshake
                data = (data.decode()).strip()
                receive_handshake(src_port, dst_port, sequence_number, acknowledgement_number,data_length, syn, ack, data)
        #client receiving second part of handshake
        elif syn == 1 and ack == 1:
            data = (data.decode()).strip()
            received_bytes[0] = eval(data) #the data is size of incoming file
            send_ack(src_port, dst_port, sequence_number, acknowledgement_number,data_length, syn, ack, data)
        elif syn == 0 and ack == 1:
            send_data(src_port, dst_port, sequence_number, acknowledgement_number,data_length, syn, ack, data)
        elif syn == 0 and ack == 0 and transmitted_packets[src_port][0] == acknowledgement_number:
            transmitted_packets[src_port][1].close()
            del transmitted_packets[src_port]
    return

def initialize_handshake(filename):
    src_port = node_info["port"]
    dst_port = peer_info[filename]["port"]
    syn, ack = 1,0
    sequence_number = random.randint(0, 2**32 - 1)
    acknowledgement_number = 0
    data_length = 0
    data = bytes(filename + (1024-len(filename))*" ", 'utf-8')
    packed_data = struct.pack("HHLLHHH1024s", src_port, dst_port, sequence_number, acknowledgement_number, data_length, syn, ack, data)

    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.sendto(packed_data, (peer_info[filename]["hostname"], peer_info[filename]["port"]))
    s.close() #close port
    #print("SENT HANDSHAKE1")
    return  


def read_configuaration(config_file):
    f = open(config_file)
    data = json.load(f)

    #store hostname, port, peers, content_info
    node_info["hostname"] = data["hostname"]
    node_info["port"] = data["port"]
    node_info["peers"] = data["peers"]
    node_info["content_info"] = data["content_info"]

    for info in data["peer_info"]:
        keys = info["content_info"]
        port_to_hostname[info["port"]] = info["hostname"]
        for k in keys:
            peer_info[k] = dict()
            peer_info[k]["hostname"] = info["hostname"]
            peer_info[k]["port"] = info["port"]
            #port_to_hostname[peer_info[k]["port"]] = info["hostname"]

    return

if __name__ == '__main__':
    config_file = sys.argv[1]
    read_configuaration(config_file)

    #intialize socket 
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    SERVER_PORT = node_info["port"]
    HOST = node_info["hostname"]
    #s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((HOST, SERVER_PORT)) #need to close s

    receiver_thread = threading.Thread(target=receive)
    threads = [receiver_thread]

    threads_running = True
    
    #starts threads (REMEMBER TO CLOSE) or make daemon threads
    for t in threads:
        t.start()

    while True:
        filename = input()
        if filename in peer_info:
            initialize_handshake(filename)
            received_file = filename
        elif filename.strip() == "kill":
            threads_running = False
            for t in threads:
                t.join()
    
