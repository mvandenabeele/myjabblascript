import os
import myjabbla
from dotenv import load_dotenv

def select_subgroup(parent_group: myjabbla.Group) -> myjabbla.Group:
    target_subgroups = parent_group.subgroups()
    if len(target_subgroups) > 0:
        print("The target group has subgroups, please select one:")
        print("0: <Select this group>")
        for idx, sg in enumerate(target_subgroups):
            print(f"{idx+1}: {sg.name} (id:{sg.id})")
        sel = int(input("Select subgroup by number: "))
        if sel == 0:
            return None
        if sel < 1 or sel > len(target_subgroups):
            print("Invalid selection")
            return

        subgroup = select_subgroup(target_subgroups[sel-1])
        if subgroup is not None:
            return subgroup
        else:
            return target_subgroups[sel-1]

    return None
            
def main():
    load_dotenv()
    

    # https://patorjk.com/software/taag/#p=display&f=Ogre&t=MyJabbla+Bulk+Impoerter&x=none&v=4&h=4&w=80&we=false
    print(
'''                                       
               __        _     _     _           ___       _ _       _____                            _            
  /\/\  _   _  \ \  __ _| |__ | |__ | | __ _    / __\_   _| | | __   \_   \_ __ ___  _ __   ___  _ __| |_ ___ _ __ 
 /    \| | | |  \ \/ _` | '_ \| '_ \| |/ _` |  /__\// | | | | |/ /    / /\/ '_ ` _ \| '_ \ / _ \| '__| __/ _ \ '__|
/ /\/\ \ |_| /\_/ / (_| | |_) | |_) | | (_| | / \/  \ |_| | |   <  /\/ /_ | | | | | | |_) | (_) | |  | ||  __/ |   
\/    \/\__, \___/ \__,_|_.__/|_.__/|_|\__,_| \_____/\__,_|_|_|\_\ \____/ |_| |_| |_| .__/ \___/|_|   \__\___|_|   
        |___/                                                                       |_|                            
'''
    )
    print(f"Using base url {os.getenv('MYJABBLA_BASE_URL')}")
    
    mj = myjabbla.Server(os.getenv("MYJABBLA_BASE_URL"))
    mj.set_api_key(os.getenv("MYJABBLA_API_KEY"))
     
    packet = input("What serial number should accounts be added to? ")
    try:
        target_group = mj.get_group_sn(packet)
        target_group = select_subgroup(target_group) or target_group
        
        print(target_group)
            
    except myjabbla.ApiError as e:  
        print(f"Error: {e.message}")    
        

if __name__ == "__main__":
    main()