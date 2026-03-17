import socket
import sys

def test_conn(host, port):
    try:
        print(f"Testing connectivity to {host}:{port}...")
        socket.setdefaulttimeout(10)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
        print(f"✅ Connection to {host}:{port} successful!")
    except Exception as e:
        print(f"❌ Connection to {host}:{port} failed: {e}")

if __name__ == "__main__":
    test_conn("8.8.8.8", 53)
    test_conn("api.openai.com", 443)
    print("Done.")
