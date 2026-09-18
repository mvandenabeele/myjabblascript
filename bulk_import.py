import os
import re
import csv
import secrets
import myjabbla
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from threading import Lock

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

def check_user_exists(server, login, row_index):
    """Helper function to check if a user exists (for multithreading)"""
    try:
        exists_user = server.get_user(login)
        return row_index, exists_user, None
    except myjabbla.ItemNotFoundError:
        return row_index, None, None
    except myjabbla.ApiError as e:
        return row_index, None, e

def create_user_account(target_group, login, password, name,email, row_index):
    """Helper function to create a user account (for multithreading)"""
    try:
        added_user = target_group.add_user(login, password, name, email)
        return row_index, added_user, None
    except myjabbla.ApiError as e:
        return row_index, None, e

# no confusable characters: 0/O/o, 1/l/I/i
PASSWORD_ALPHABETS = (
    "abcdefghjkmnpqrstuvwxyz",
    "ABCDEFGHJKLMNPQRSTUVWXYZ",
    "23456789",
)

def generate_password(length=8):
    """Random password with at least one lowercase letter, uppercase letter and digit"""
    alphabet = "".join(PASSWORD_ALPHABETS)
    while True:
        password = "".join(secrets.choice(alphabet) for _ in range(length))
        if all(any(c in chars for c in password) for chars in PASSWORD_ALPHABETS):
            return password

def load_lines_from_xlsx(file_path):
    from openpyxl import load_workbook
    wb = load_workbook(filename=file_path)
    sheet = wb.active
    
    max_line_width = 0
    lines = []
    sheet_rows = []  # sheet row number (1-based) of each returned line
    for i, row in enumerate(sheet.iter_rows(values_only=True)):
        line_width = 0
        for w, cell in enumerate(row):
            if cell is not None:
                line_width = w
                
        if line_width > max_line_width:
            max_line_width = line_width
                    
        has_data = line_width > 0

        if has_data:
            lines.append(row)
            sheet_rows.append(i+1)
    
    clean_lines = []
    for row in lines:
        clean_lines.append( row[:max_line_width+1] )
    return clean_lines, sheet_rows

def load_lines_from_csv(file_path):
    import csv
    lines = []
    with open(file_path) as csvfile:
        reader = csv.reader(csvfile)
        for row in reader:
            row = tuple(row)
            lines.append(row)
    return lines

def save_passwords_to_xlsx(file_path, passwords, header_row=None):
    """Write passwords ({sheet row: password}) to the first empty column of the active sheet"""
    from openpyxl import load_workbook
    wb = load_workbook(filename=file_path)
    sheet = wb.active

    col = 1
    while any(sheet.cell(row=r, column=col).value is not None for r in range(1, sheet.max_row+1)):
        col += 1

    if header_row is not None:
        sheet.cell(row=header_row, column=col, value="password")
    for row, password in passwords.items():
        sheet.cell(row=row, column=col, value=password)

    while True:
        try:
            wb.save(file_path)
            break
        except PermissionError:
            input(f"Cannot write {file_path}, is it open in Excel? Close it and press Enter to retry...")
    print(f"Generated passwords written to column {sheet.cell(row=1, column=col).column_letter} of {file_path}")

def save_passwords_to_csv(file_path, passwords, header_row=None):
    """Write passwords ({line index: password}) to the first empty column of the csv file"""
    lines = [list(row) for row in load_lines_from_csv(file_path)]

    col = 0
    while any(len(row) > col and row[col] != "" for row in lines):
        col += 1

    def set_cell(row, value):
        lines[row].extend([""] * (col + 1 - len(lines[row])))
        lines[row][col] = value

    if header_row is not None:
        set_cell(header_row, "password")
    for row, password in passwords.items():
        set_cell(row, password)

    while True:
        try:
            with open(file_path, "w", newline="") as csvfile:
                csv.writer(csvfile).writerows(lines)
            break
        except PermissionError:
            input(f"Cannot write {file_path}, is it open in Excel? Close it and press Enter to retry...")
    print(f"Generated passwords written to column {col} of {file_path}")

def process_xlsx(file_path, target_group: myjabbla.Group, server: myjabbla.Server, max_workers=10):
    
    sheet_rows = None
    if file_path.endswith(".xlsx"):
        data_lines, sheet_rows = load_lines_from_xlsx(file_path)
    else:
        data_lines = load_lines_from_csv(file_path)

    # print first 10 rows
    for i, row in enumerate(data_lines):
        if i < 10:
            print(i, row)
        else:
            break
        
    #ask for line number to start from
    start_line = int(input("Enter line number to start from (0-indexed): "))
    data_lines = data_lines[start_line:]
    
    login_col = None
    pwd_col = None
    email_col = None
    
    for i, row in enumerate(data_lines):
        print(f"----- record {i} -----")
        for j,c in enumerate(row):
            print(j, c)

    login_col = int(input("Enter column number for login: "))
    pwd_col = int(input("Enter column number for password (or -1 to generate passwords): "))
    name_col = int(input("Enter column number for name (or -1 if none): "))   
    email_col = int(input("Enter column number for email (or -1 if none): "))   
    
    # Collect all user data first
    user_data = []
    for i, row in enumerate(data_lines):
        if row[login_col] and (pwd_col < 0 or row[pwd_col]) and (email_col < 0 or row[email_col]):  # Skip empty rows
            password = row[pwd_col] if pwd_col >= 0 else generate_password()
            user_data.append((i+start_line, row[login_col], password, row[name_col] if name_col >= 0 else "", row[email_col] if email_col >= 0 else ""))
    
    print(f"Found {len(user_data)} users to process")
    
    # Multithreaded user existence checking
    conflicts = []
    errors = []
    lock = Lock()
    
    print("Checking existing users...")
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all check tasks
        future_to_data = {
            executor.submit(check_user_exists, server, login, row_index): (row_index, login)
            for row_index, login, _, _, _ in user_data
        }
        
        completed = 0
        for future in as_completed(future_to_data):
            row_index, existing_user, error = future.result()
            completed += 1
            
            if completed % 10 == 0 or completed == len(user_data):
                print(f"Checked {completed}/{len(user_data)} users...")
            
            if existing_user:
                with lock:
                    conflicts.append(existing_user)
            elif error:
                with lock:
                    errors.append((row_index, future_to_data[future][1], error.message))
    
    if errors:
        print("Errors occurred while checking users:")
        for row_index, login, error_msg in errors:
            print(f" - Row {row_index}, login {login}: {error_msg}")
    
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
    
    # Multithreaded user creation
    creation_errors = []
    created_users = []
    
    print("Creating users...")
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all creation tasks
        future_to_data = {
            executor.submit(create_user_account, target_group, login, password, name, email, row_index): 
            (row_index, login, name, password, email)
            for row_index, login, password, name,email in user_data
        }
        
        completed = 0
        for future in as_completed(future_to_data):
            row_index, created_user, error = future.result()
            completed += 1
            
            if completed % 10 == 0 or completed == len(user_data):
                print(f"Created {completed}/{len(user_data)} users...")
            
            if created_user:
                with lock:
                    created_users.append((row_index, created_user))
            else:
                with lock:
                    creation_errors.append((row_index, future_to_data[future][1], error.message))
    
    # Report results
    print(f"\nImport completed!")
    print(f"Successfully created: {len(created_users)} users")
    
    if creation_errors:
        print(f"Errors creating {len(creation_errors)} users:")
        for row_index, login, error_msg in creation_errors:
            print(f" - Row {row_index}, login {login}: {error_msg}")

    if pwd_col < 0 and created_users:
        created_rows = {row_index for row_index, _ in created_users}
        passwords = {row_index: password
                     for row_index, _, password, _, _ in user_data if row_index in created_rows}
        header_row = start_line-1 if start_line > 0 else None
        if sheet_rows is not None:
            passwords = {sheet_rows[row_index]: password for row_index, password in passwords.items()}
            header_row = sheet_rows[header_row] if header_row is not None else None
            save_passwords_to_xlsx(file_path, passwords, header_row)
        else:
            save_passwords_to_csv(file_path, passwords, header_row)
              
def main():
    load_dotenv()
    
    # Configuration for multithreading
    MAX_WORKERS = 10  # Adjust this based on your API rate limits
    

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
    
    file_candidates = [] 
    # find first xlsx file in current directory
    for file in os.listdir("."):
        if file.endswith(".csv"):
            print(f"Found csv file: {file}")
            file_candidates.append(file)
        elif file.endswith(".xlsx"):
            print(f"Found xlsx file: {file}")
            file_candidates.append(file)

    # newest files first
    file_candidates.sort(key=os.path.getmtime, reverse=True)

    for idx, fname in enumerate(file_candidates):
        print(f"{idx}: {fname}")
    file = None
    if len(file_candidates) == 0:
        print("No xlsx or csv files found in current directory. Please place the file to import here.")
        return
    elif len(file_candidates) == 1:
        file = file_candidates[0]
    else:
        sel = int(input("Multiple files found, select file by number: "))
        if sel < 0 or sel >= len(file_candidates):
            print("Invalid selection")
            return
        file = file_candidates[sel]
        
    if file:
        print(f"Processing file: {file}")
        
    # suggest a serial number (ME/SPR followed by digits) found in the filename
    match = re.search(r"(?<![A-Za-z])(ME|SPR)\d+", file, re.IGNORECASE)
    suggested = match.group(0).upper() if match else None
    if suggested:
        packet = input(f"What serial number should accounts be added to? [{suggested}] ").strip() or suggested
    else:
        packet = input("What serial number should accounts be added to? ").strip()
    try:
        target_group = mj.get_group_sn(packet)
        target_group = select_subgroup(target_group) or target_group
        
        print(target_group)
        process_xlsx(file, target_group, mj, MAX_WORKERS)
            
    except myjabbla.ApiError as e:  
        print(f"Error: {e.message}")    
        

if __name__ == "__main__":
    main()