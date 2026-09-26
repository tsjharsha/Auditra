import httpx
import json

def run_test():
    base_url = "http://127.0.0.1:8002"
    
    # 1. Reset
    r_reset = httpx.post(f"{base_url}/verification/reset")
    print(f"Reset: {r_reset.json()}")

    # 2. Stream
    with httpx.stream("GET", f"{base_url}/verification/stream", timeout=120.0) as r_stream:
        for line in r_stream.iter_lines():
            if line:
                print(line)

if __name__ == "__main__":
    run_test()
