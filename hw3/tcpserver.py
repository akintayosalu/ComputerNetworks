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

#packer = struct.Struct('HHLLHH1024c')

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
    print("SENT HANDSHAKE2")

def send_ack(src_port, dst_port, sequence_number, acknowledgement_number,data_length, syn, ack, data):
    syn, ack = 0,1
    acknowledgement_number = sequence_number
    sequence_number = 0
    data = bytes(1024*" ", 'utf-8')
    packed_data = struct.pack("HHLLHHH1024s", dst_port, src_port, sequence_number, acknowledgement_number,data_length, syn, ack, data)

    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.sendto(packed_data, (port_to_hostname[src_port], src_port))
    s.close() #close port
    print("SENT HANDSHAKE 3")

def send_data(src_port, dst_port, sequence_number, acknowledgement_number,data_length, syn, ack, data):
    if acknowledgement_number == transmitted_packets[src_port][0]:
        f = transmitted_packets[src_port][1]
        packet_bytes = f.read(1024)
        if len(packet_bytes) < 1024:
            print(len(packet_bytes))
            print(packet_bytes)
            print("REACHED THE END")
            f.close()
            #exit(0)
        #print(packet_bytes)
        sequence_number += len(packet_bytes)
        transmitted_packets[src_port][0] = sequence_number
        acknowledgement_number = 0
        data_length = len(packet_bytes)
        syn, ack = 1,0

        packed_data = struct.pack("HHLLHHH1024s", dst_port, src_port, sequence_number, acknowledgement_number,data_length, syn, ack, packet_bytes)
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.sendto(packed_data, (port_to_hostname[src_port], src_port))
        s.close() #close port
        print("SENT DATA")

        if data_length != 1024:
            exit()


    return

def build_file():
    file_bytes = bytes().join(received_bytes[1])
    newFile = open("fake.jpg", "wb")
    newFile.write(file_bytes)
    newFile.close()

    return_bool = filecmp.cmp("fake.jpg", "Carnegie_Mellon_University.jpg", shallow=False)
    print(return_bool)

    #AT THIS POINT WE WANT TO EMPTY EVERYTHING



def receive():
    while threads_running:
        packet, addr = s.recvfrom(2048)
        src_port, dst_port, sequence_number, acknowledgement_number, data_length, syn, ack, data = struct.unpack("HHLLHHH1024s",packet)
        # print(type(data))
        # #data = (data.decode()).strip()
        # print("SRC PRT " + str(src_port))
        # print("DST PORT " + str(dst_port))
        # print("SEQ NUM " + str(sequence_number))
        # print("ACK NUMBER" + str(acknowledgement_number))
        # print("DATA LENGTH" + str(data_length))
        # print("SYN/ACK " + str(syn) + "/" + str(ack))
        # print("DATA " + str(data))

        if syn == 1 and ack == 0:
            if data_length > 0:
                if data_length != 1024:
                    received_bytes[1].append(data[0:data_length])
                    build_file()
                    # print(received_bytes[1])
                    # print(len(received_bytes[1]), received_bytes[0])
                    exit()
                else:
                    received_bytes[1].append(data)
                    #send ACK back to server to receive more packets
                    send_ack(src_port, dst_port, sequence_number, acknowledgement_number,data_length, syn, ack, data)
                #print(received_bytes[1])
                # global count 
                # if count >= 10:
                #     print(received_bytes[1][1])
                #     exit(0)
                # count += 1
                print("RECEIVING DATA")
                #exit()
            else:
                data = (data.decode()).strip()
                receive_handshake(src_port, dst_port, sequence_number, acknowledgement_number,data_length, syn, ack, data)
            #differentiate
        elif syn == 1 and ack == 1:
            #print("SEND NORMAL ACK")
            data = (data.decode()).strip()
            received_bytes[0] = eval(data)
            send_ack(src_port, dst_port, sequence_number, acknowledgement_number,data_length, syn, ack, data)
        elif syn == 0 and ack == 1:
            send_data(src_port, dst_port, sequence_number, acknowledgement_number,data_length, syn, ack, data)
            print("SEND DATA")
        
        print()
        
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
    print("SENT HANDSHAKE1")
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
        for k in keys:
            peer_info[k] = dict()
            peer_info[k]["hostname"] = info["hostname"]
            peer_info[k]["port"] = info["port"]
            port_to_hostname[peer_info[k]["port"]] = info["hostname"]

    return

if __name__ == '__main__':
    config_file = sys.argv[1]
    read_configuaration(config_file)

    #intialize socket 
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    SERVER_PORT = node_info["port"]
    HOST = node_info["hostname"]
    s.bind((HOST, SERVER_PORT)) #need to close s

    receiver_thread = threading.Thread(target=receive)
    threads = [receiver_thread]

    threads_running = True
    
    #starts threads (REMEMBER TO CLOSE)
    for t in threads:
        t.start()

    while True:
        filename = input()
        if filename in peer_info:
            
            #begin 3-way handshake 
            initialize_handshake(filename)
            #print(msg_string)
            #break
    
