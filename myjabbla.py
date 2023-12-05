import requests
import json
from typing import List

class ApiError(Exception):
    def __init__(self, msg):
        self.message = msg
        
class User:
    def __init__(self, mj, info):
        self.myjabbla = mj
        self.id = info["id"]
        self.login = info["login"]
        self.isadmin = info["admin"]
        
    def __str__(self):
        return f"<User id:{self.id}, login:{self.login}, admin:{self.isadmin}>"
    
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
        
class MyJabbla:
    def __init__(self) -> None:
        self.baseUrl = "https://api.jabbla.com/v1/"
        self.session = requests.Session()
        self.loggedIn = False
        self.top_group = -1
        
    def __del__(self):
        if self.loggedIn:
            self.logout()
    
    def do_post_request(self, url, payload ):
        theUrl = self.baseUrl + url
        headers = {
        'Content-Type': 'application/json'
        }

        response = self.session.request("POST", theUrl, headers=headers, data=json.dumps(payload))
        info = json.loads(response.content)
        return info
    
    def do_put_request(self, url, payload ):
        theUrl = self.baseUrl + url
        headers = {
        'Content-Type': 'application/json'
        }

        response = self.session.request("PUT", theUrl, headers=headers, data=json.dumps(payload))
        info = json.loads(response.content)
        return info

    def do_get_request(self, url):
        theUrl = self.baseUrl + url
        headers = {
        'Content-Type': 'application/json'
        }

        response = self.session.request("GET", theUrl, headers=headers)
        info = json.loads(response.content)
        return info
    
    def do_del_request(self, url):
        theUrl = self.baseUrl + url
        headers = {
        'Content-Type': 'application/json'
        }

        response = self.session.request("DELETE", theUrl, headers=headers)
        info = json.loads(response.content)
        return info
        
    def login(self, username: str, password: str) -> bool:
        url = "login"

        payload = { "login": username, "password": password}
        info = self.do_post_request(url, payload)
        if not info["error"]:
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
    
    