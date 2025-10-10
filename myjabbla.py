import requests
import json
from typing import List

class ApiError(Exception):
    def __init__(self, msg):
        self.message = msg
        
class ItemNotFoundError(ApiError):
    def __init__(self, msg):
        super().__init__(msg)
        
class User:
    def __init__(self, mj, info):
        self.myjabbla = mj
        self.id = info["id"]
        self.login = info["login"]
        self.isadmin = info["admin"]
        self.packet_sn = info["packet_sn"]
        if "group_id" in info:
            self.group_id = info["group_id"]
        elif "group" in info and "id" in info["group"]:
            self.group_id = info["group"]["id"]
        else:
            self.group_id = None    
        
    def __str__(self):
        return f"<User id:{self.id}, login:{self.login}, admin:{self.isadmin}, group_id:{self.group_id}>"
    
    def update_password(self, password: str) -> bool:
        if self.id is None or self.id < 1:
            return False
        
        url = f"weblockaccount/{self.id}"
        
        payload = {}
        payload["user"] = {}
        payload["user"]["password"] = password
        
        info = self.myjabbla.do_post_request(url, payload)
        return not info["error"]
    
    def delete(self) -> bool:
        url = f"weblockaccount/{self.id}"
        
        payload = {}
        info = self.myjabbla.do_del_request(url)
        return not info["error"]
    
    def get_group(self) -> 'Group':
        return self.myjabbla.get_group(self.group_id)

        
class Group:
    def __init__(self, mj, info):
        self.myjabbla = mj
        self.id = info["id"]
        self.name = info["name"]
        self.packet = info["packet"]
        
    def __str__(self):
        return f"<Group id:{self.id}, name:{self.name}>"
    
    def users(self) -> List[User]:
        result = list()
        info = self.myjabbla.do_get_request(f"weblockgroup/{self.id}/users")
        if not info["error"]:
            data = info["data"]
            for d in data:
                result.append( User(self.myjabbla, d))
        return result
    
    def subgroups(self) -> List['Group']:
        result = list()
        info = self.myjabbla.do_get_request(f"weblockgroup/{self.id}/subgroups")
        if not info["error"]:
            data = info["data"]
            for d in data:
                result.append(Group(self.myjabbla, d))
        return result
    
    def delete(self) -> bool:
        url = f"weblockgroup/{self.id}"

        info = self.myjabbla.do_del_request(url)
        return not info["error"]
    
    def add_user(self, login: str, password: str, name: str) -> User:
        url = f"weblockgroup/{self.id}/adduser"
        
        payload = {}
        payload["user"] = {}
        payload["user"]["login"] = login
        payload["user"]["password"] = password
        payload["user"]["name"] = name
        
        info = self.myjabbla.do_put_request(url, payload)
        if info["error"]:
            raise( ApiError(info["errormsg"]))
        
        return User(self.myjabbla, info["weblockuser"])
    
    def add_subgroup(self, name: str) -> 'Group':
        url = f"weblockgroup/{self.id}/addgroup"
        
        payload = {}
        payload["group"] = {}
        payload["group"]["name"] = name
        
        info = self.myjabbla.do_put_request(url, payload)
        if info["error"]:
            raise( ApiError(info["errormsg"]))
        
        return Group(self.myjabbla, info["weblockgroup"])
        
class Server:
    def __init__(self, base_url: str = None) -> None:
        self.baseUrl = base_url or "https://api.jabbla.com/v1/"
        self.session = requests.Session()
        self.loggedIn = False
        self.top_group = -1
        self.api_key = None
        
    def __del__(self):
        if self.loggedIn:
            self.logout()
    
    def _construct_headers(self):
        headers = {
            'Content-Type': 'application/json'
        }
        if self.api_key is not None:
            headers['Authorization'] = f"apikey {self.api_key}"
        return headers
    
    def do_post_request(self, url, payload ):
        theUrl = self.baseUrl + url
        headers = self._construct_headers()

        response = self.session.request("POST", theUrl, headers=headers, data=json.dumps(payload))
        info = json.loads(response.content)
        return info
    
    def do_put_request(self, url, payload ):
        theUrl = self.baseUrl + url
        headers = self._construct_headers()

        response = self.session.request("PUT", theUrl, headers=headers, data=json.dumps(payload))
        info = json.loads(response.content)
        return info

    def do_get_request(self, url):
        theUrl = self.baseUrl + url
        headers = self._construct_headers()

        response = self.session.request("GET", theUrl, headers=headers)
        info = json.loads(response.content)
        
        if response.status_code == 404:
            msg = "Item not found"
            if "errormsg" in info:
                msg = info["errormsg"]
            raise( ItemNotFoundError(msg))

        
        return info
    
    def do_del_request(self, url):
        theUrl = self.baseUrl + url
        headers = self._construct_headers()

        response = self.session.request("DELETE", theUrl, headers=headers)
        info = json.loads(response.content)
        return info
        
    def set_api_key(self, api_key: str):
        self.api_key = api_key
        
    def login(self, username: str, password: str) -> bool:
        url = "login"

        payload = { "login": username, "password": password}
        info = self.do_post_request(url, payload)
        if not info["error"]:
            if "obj" in info and "group_id" in info["obj"]:
                self.top_group = info["obj"]["group_id"]
            
            print(f"Toplevel group for {username} is {self.top_group}")
            return True

        return False
    
    def logout(self) -> bool:
        if self.loggedIn:
            url = "login"
            self.do_post_request(url, {})
            return True
        
        return False
    
    def toplevelgroup(self) -> Group:
        url = f"weblockgroup/{self.top_group}"
        info = self.do_get_request(url)
        
        return Group(self, info["data"])
    
    def get_user(self, login: str) -> User:
        url = f"weblockaccount/login/{login}"
        info = self.do_get_request(url)
        if info["error"]:
            raise( ApiError(info["errormsg"]))
        
        return User(self, info["data"])
    
    def get_group(self, group_id: int) -> Group:
        url = f"weblockgroup/{group_id}"
        info = self.do_get_request(url)
        if info["error"]:
            raise( ApiError(info["errormsg"]))
        
        return Group(self, info["data"])
    
    def get_group_sn(self, sn: str) -> Group:
        url = f"weblockgroup/{sn}/license"
        info = self.do_get_request(url)
        if info["error"]:
            raise( ApiError(info["errormsg"]))
        
        if "data" not in info or info["data"] is None:
            raise( ApiError(f"No group for serial number {sn}"))
        
        return Group(self, info["data"])
    
    