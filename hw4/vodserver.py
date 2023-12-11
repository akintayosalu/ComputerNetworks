import sys
import socket
import os
import threading 
from datetime import datetime, timezone

threads_running = False
SERVER_HOST = '' # Symbolic name, meaning all available interfaces
s = None
BUFSIZE = 2048
CHUNKSIZE = 5242880
file_types = {
    ".txt": "text/plain",
    ".css": "text/css",
    ".htm": "text/html",
    ".html": "text/html",
    ".gif": "image/gif",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".mp4": "video/mp4",
    ".webm": "video/webm",
    ".ogg": "video/webm",
    ".js": "application/javascript",
}

not_found_html = b"""
<html>
<head>
<title>Simple 404 Error Page</title>
<link href="https://fonts.googleapis.com/css?family=Roboto:700" rel="stylesheet">
<style>
h1{
font-size:80px;
font-weight:800;
text-align:center;
font-family: 'Roboto', sans-serif;
}
h2
{
font-size:25px;
text-align:center;
font-family: 'Roboto', sans-serif;
margin-top:-40px;
}
p{
text-align:center;
font-family: 'Roboto', sans-serif;
font-size:12px;
}

.container
{
width:300px;
margin: 0 auto;
margin-top:15%;
}
</style>
</head>
<body>
<div class="container">
<h1>404</h1>
<h2>Page Not Found</h2>
</div>
</body>
</html>
"""

forbidden_html = b"""
<html>
<head>
<title>Simple 403 Error Page</title>
<link href="https://fonts.googleapis.com/css?family=Roboto:700" rel="stylesheet">
<style>
h1{
font-size:80px;
font-weight:800;
text-align:center;
font-family: 'Roboto', sans-serif;
}
h2
{
font-size:25px;
text-align:center;
font-family: 'Roboto', sans-serif;
margin-top:-40px;
}
p{
text-align:center;
font-family: 'Roboto', sans-serif;
font-size:12px;
}

.container
{
width:300px;
margin: 0 auto;
margin-top:15%;
}
</style>
</head>
<body>
<div class="container">
<h1>403</h1>
<h2>Page is Forbidden</h2>
</div>
</body>
</html>
"""

def get_date():
    current_utc_time = datetime.now(timezone.utc)
    timestamp = current_utc_time.strftime('%a, %d %b %Y %H:%M:%S GMT')
    return timestamp

def get_modified_date(path):
    create_time = os.path.getctime(path)
    create_date_gmt = datetime.utcfromtimestamp(create_time)
    timestamp = create_date_gmt.strftime('%a, %d %b %Y %H:%M:%S GMT')
    return timestamp

def get_content_type(path):
    file_type = os.path.splitext(path)[1].lower()
    type_name = file_types.get(file_type,"application/octet-stream")
    return type_name

def send_200(file_bytes, path,connection_socket):
    response_code = "HTTP/1.1 200 OK\n"
    accept_ranges = "Accept-Ranges: bytes\n"
    date_info = "Date: " + get_date() + "\n"
    connection_info = "Connection: close\n"
    content_length = "Content-Length: " + str(os.stat(path).st_size) + "\n"
    last_modified = "Last-Modified: " + get_modified_date(path) + "\n"
    content_type = "Content-Type: " + get_content_type(path) + "\n" 
    message_bytes = (bytes(response_code + accept_ranges + date_info + last_modified + connection_info + content_length + content_type + "\n", "utf-8") + file_bytes)
    # print(response_code + accept_ranges + date_info + last_modified + connection_info + content_length + content_type)
    # print(path)
    connection_socket.send(message_bytes)
    return 

def send_206(start,end,file_bytes,path,connection_socket):
    response_code = "HTTP/1.1 206 Partial Content\n"
    accept_ranges = "Accept-Ranges: bytes\n"
    date_info = "Date: " + get_date() + "\n"
    connection_info = "Connection: keep-alive\n"
    partial_bytes = file_bytes[start:end+1]
    content_length = "Content-Length: " + str(len(partial_bytes)) + "\n"
    content_range = "Content-Range: bytes " + str(start) + "-" + str(end) + "/" + str(len(file_bytes)) + "\n"
    last_modified = "Last-Modified: " + get_modified_date(path) + "\n"
    content_type = "Content-Type: " + get_content_type(path) + "\n" 
    message_bytes = (bytes(response_code + accept_ranges + date_info + last_modified + connection_info + content_length + content_range + content_type + "\n", "utf-8") + partial_bytes)
    # print(response_code + accept_ranges + date_info + last_modified + connection_info + content_length + content_range + content_type)
    # print(path)
    connection_socket.send(message_bytes)
    return 

def send_403(connection_socket):
    response_code = "HTTP/1.1 403 Forbidden\n"
    date_info = "Date: " + get_date() + "\n"
    connection_info = "Connection: close\n"
    content_type = "Content-Type: text/html\n" 
    content_length = "Content-Length: "+ str(len(forbidden_html)) + "\n"
    message_bytes = (bytes(response_code + date_info + connection_info + content_type + content_length + "\n", "utf-8") + forbidden_html)
    connection_socket.send(message_bytes)
    return 

def send_404(connection_socket):
    response_code = "HTTP/1.1 404 Not Found\n"
    date_info = "Date: " + get_date() + "\n"
    connection_info = "Connection: close\n"
    content_type = "Content-Type: text/html\n" 
    content_length = "Content-Length: "+ str(len(not_found_html)) + "\n"
    message_bytes = (bytes(response_code + date_info + connection_info + content_type + content_length + "\n", "utf-8") + not_found_html)
    connection_socket.send(message_bytes)
    return 

def not_existing(request_file):
    path = "content" + request_file
    return not os.path.isfile(path)

def is_confidential(request_file):
    directories = request_file.split("/")
    return "confidential" in directories

def parse_request(request, connection_socket):
    request_file = ""
    start, end = None, None
    for lines in request.splitlines():
        if lines[0:3] == "GET":
            filename = lines.split(" ")[1]
            request_file = filename
        elif lines[0:5] == "Range":
            range_info = lines.split(":")[1]
            ranges = range_info.split("=")[1].split("-")
            start = int(ranges[0])
            if ranges[1] != "":
                end = int(ranges[1])
    
    if (is_confidential(request_file)):
        send_403(connection_socket) 
    elif (not_existing(request_file)):
        send_404(connection_socket) 
    else:
        path = "content" + request_file
        f = open(path, "rb")
        file_bytes = f.read()
        f.close()
        size = os.stat(path).st_size
        if size <= CHUNKSIZE:
            #regular 200 response
            send_200(file_bytes,path,connection_socket)
        else:
            if start == None: start = 0
            if end == None: end = size-1
            send_206(start,end,file_bytes,path,connection_socket)
    return 

def server():
    while True:
        # accept a connection
        connection_socket, client_address = s.accept()

        # receive the message
        http_request = connection_socket.recv(BUFSIZE).decode()
        #print(http_request)
        response_thread = threading.Thread(target=parse_request, args=(http_request, connection_socket), daemon=True)
        response_thread.start()
        
    s.close()
    return 
        
if __name__ == '__main__':
    SERVER_PORT = int(sys.argv[1])
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) #without this line, if the previous execution has left the socket in a TIME_WAIT state, the socket can’t be immediately reused ([Errno 98] Address already in use)
    s.bind((SERVER_HOST, SERVER_PORT))

    # listen on socket
    s.listen(30)

    # server_thread = threading.Thread(target=server, daemon=True)
    # threads = [server_thread]
    # threads_running = True
    # for t in threads:
    #     t.start()

    server()

    # while True:
    #     continue


