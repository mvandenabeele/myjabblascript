import myjabbla

def main():
    mj = myjabbla.MyJabbla()

    print(
'''                                       
               _     _   _   _                     
 _____ _ _    |_|___| |_| |_| |___   ___ ___ _____ 
|     | | |_  | | .'| . | . | | .'|_|  _| . |     |
|_|_|_|_  |_|_| |__,|___|___|_|__,|_|___|___|_|_|_|
      |___| |___|                                  
'''
    )                                                                                                                         

    print("Sample usage for myjabbla python API.")
    print()
    print("Please note, every action will be done WITHOUT WARNINGS.")
    print("Pay attention to what you delete!")
    print()
    login = input("Admin account login? ")
    password = input("Password? ")
    if( mj.login(login, password)):
        print("Login okay")
        myGroup = mj.toplevelgroup()
        print(f"Toplevel group: {myGroup}")
        
        subGroups = myGroup.subgroups()
        for sub in subGroups:
            print( f"Subgroup {sub}")
            
        try:
            newSubGroup = myGroup.add_subgroup("new group")
            print( f"Created {newSubGroup}")
            newSubGroup.delete()
        except myjabbla.ApiError as e:
            print( f"Api error: {e.messsage}")
        
        myGroupUsers = myGroup.users()
        for u in myGroupUsers:
            print (f"User {u}")
            
        if myGroupUsers[0].update_password("newpwd"):
            print("Password set")
        else:
            print("Could not set password")
        
        try:
            newUser = myGroup.add_user("accountdiezekernietbestaat2", "polleke", "Bestaat Al")
            print( f"Created {newUser}")
            if newUser.delete():
                print("User deleted")
            else:
                print("Could not delete user")
        except myjabbla.ApiError as e:
            print( f"Api error: {e.message}")
    else:
        print("Login failed")
    
    
if __name__ == "__main__":
    main()