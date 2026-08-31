import json
import requests

url="http://localhost:11434/api/chat"

playload={
    "model":"qwen2.5vl:3b",
    "messages":[
        {
            "role":"user",
            "content":"ou se situe rabat?"
        }
    ],
    "stream":False
}

response=requests.post(url=url,json=playload)

print(response.json()["message"]["content"])