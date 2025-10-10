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

def process_xlsx(file_path, target_group: myjabbla.Group, server: myjabbla.Server):
    from openpyxl import load_workbook
    wb = load_workbook(filename=file_path)
    sheet = wb.active
    
    # print first 10 rows
    for i, row in enumerate(sheet.iter_rows(values_only=True)):
        if i < 10:
            print(i, row)
        else:
            break
        
    #ask for line number to start from
    start_line = int(input("Enter line number to start from (0-indexed): "))
    login_col = None
    pwd_col = None
    email_col = None
    
    for i, row in enumerate(sheet.iter_rows(values_only=True, min_row=start_line+1, max_row=start_line+1)):
        for j,c in enumerate(row):
            print(j, c)

    login_col = int(input("Enter column number for login: "))
    pwd_col = int(input("Enter column number for password: "))
    email_col = int(input("Enter column number for email: "))   
    
    conflicts = []
    for i, row in enumerate(sheet.iter_rows(values_only=True, min_row=start_line+1)):
        print(f"Checking {i+start_line}: login={row[login_col]}, pwd={row[pwd_col]}, email={row[email_col]}")
        try:
            exists_user = server.get_user(row[login_col])
            conflicts.append(exists_user)
        except myjabbla.ItemNotFoundError:
            pass
        except myjabbla.ApiError as e:
            print(f"Error checking user {row[login_col]}: {e.message}")
              
    if len(conflicts) > 0:
        print("The following logins already exist:")
        for c in conflicts:
            print(f" - {c.login} (id:{c.id}, packet:{c.packet_sn})")
            
        print("\nPlease resolve these conflicts and try again.")
        return
    
    print("No conflicts found, proceeding with import.")
    ok = input("Type 'yes' to proceed: ")
    if ok.lower() != 'yes':
        print("Aborting.")
        return
    
    for i, row in enumerate(sheet.iter_rows(values_only=True, min_row=start_line+1)):
        print(f"Creating {i+start_line}: login={row[login_col]}, pwd={row[pwd_col]}, email={row[email_col]}")
        try:
            added_user = target_group.add_user(row[login_col], row[pwd_col], row[email_col])     

        except myjabbla.ApiError as e:
            print(f"Error creating user {row[login_col]}: {e.message}")
              
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
     
     # find first xlsx file in current directory
    for file in os.listdir("."):
        if file.endswith(".xlsx"):
            print(f"Found xlsx file: {file}")
            break
    if file:
        print(f"Processing file: {file}")
        
    packet = input("What serial number should accounts be added to? ")
    try:
        target_group = mj.get_group_sn(packet)
        target_group = select_subgroup(target_group) or target_group
        
        print(target_group)
        process_xlsx(file, target_group, mj)
            
    except myjabbla.ApiError as e:  
        print(f"Error: {e.message}")    
        

if __name__ == "__main__":
    main()