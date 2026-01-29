############################################################
# Author:           Tomas Vanagas, Adris Čypas
# Updated:          2026-01-29
# Version:          1.1
# Description:      Bridge agent for Active Directory
############################################################

import requests
import json
import fnmatch

import pyad.adquery
from pyad import aduser



# --------------------------------------
# Configuration
# --------------------------------------
config = {}
with open('config.json', 'r') as f:
    config = json.load(f)







# --------------------------------------
# Helper Functions for AD Path Resolution
# --------------------------------------
def domain_to_base_dn(domain):
    """
    Convert domain name to base DN.
    Example: 'corp.example.com' -> 'DC=corp,DC=example,DC=com'
    """
    return ','.join(f'DC={part}' for part in domain.split('.'))


def get_group_ou_path(group_name):
    """
    Get the OU path for a group based on config mappings.
    Supports exact matches and wildcard patterns (e.g., 'HR-*').
    Falls back to 'default' if no match found.
    """
    group_paths = config['activedir'].get('groupPaths', {})
    
    # First, check for exact match
    if group_name in group_paths:
        return group_paths[group_name]
    
    # Then, check for wildcard patterns
    for pattern, ou_path in group_paths.items():
        if pattern != 'default' and fnmatch.fnmatch(group_name, pattern):
            return ou_path
    
    # Fall back to default
    return group_paths.get('default', '')


def get_base_dn():
    """
    Get the base DN from config, or generate it from domain.
    """
    if 'baseDn' in config['activedir'] and config['activedir']['baseDn']:
        return config['activedir']['baseDn']
    return domain_to_base_dn(config['activedir']['domain'])


def build_group_dn(group_name):
    """
    Build the full Distinguished Name for a group.
    Example: CN=IT-Department,OU=IT,OU=Departments,DC=corp,DC=example,DC=com
    """
    ou_path = get_group_ou_path(group_name)
    base_dn = get_base_dn()
    
    if ou_path:
        return f"CN={group_name},{ou_path},{base_dn}"
    else:
        return f"CN={group_name},{base_dn}"










# ----------------------------------------------------------------------------------------------------------------
# STEP 1: Get actions to do in activedirectory (Tracer System asks to do something in activedir)
# ----------------------------------------------------------------------------------------------------------------
responseFromTracer = requests.get(
    config['tracer']['tracerActivedirBridgeUrl'],
    headers={'X-API-Key': config['tracer']['tracerActivedirBridgeApi']}
).text
responseFromTracer = json.loads(responseFromTracer)
sendToTracer = {}





# ----------------------------------------------------------------------------------------------------------------
# STEP 2: Collect data about users from activedir (Tracer System asks to collect data about users)
# ----------------------------------------------------------------------------------------------------------------
print("[*] Collecting data about users from activedir...")
if('aduserinfo' in responseFromTracer):
    sendToTracer['aduserinfo'] = {}
    for activedirID in responseFromTracer['aduserinfo']:
        activedirID = str(activedirID)

        # # Debug: print the activedirID
        # print(" activedirID: " + activedirID)

        try:
            sendToTracer['aduserinfo'][activedirID] = {}
            user = aduser.ADUser.from_cn(activedirID)

            # # Debug: print the user
            # print(str(activedirID) + ":" + user.get_attribute("mail")[0])

            
            try:
                sendToTracer['aduserinfo'][activedirID]['Email'] = user.get_attribute("mail")[0]
            except:
                pass
            try:
                sendToTracer['aduserinfo'][activedirID]['NameSurname'] = user.get_attribute("displayName")[0]
            except:
                pass
            try:
                sendToTracer['aduserinfo'][activedirID]['Description'] = user.get_attribute("description")[0]
            except:
                pass
            try:
                sendToTracer['aduserinfo'][activedirID]['JobTitle'] = user.get_attribute("title")[0]
            except:
                pass

        except Exception as e:
            print(e)
            pass
        #time.sleep(1)

    # # Debug
    # print(json.dumps(sendToTracer['aduserinfo'], indent=4))





# ----------------------------------------------------------------------------------------------------------------
# STEP 3: Collect data about groups from activedir (Tracer System asks to collect data about activedirgroups)
# ----------------------------------------------------------------------------------------------------------------
print("[*] Collecting data about groups from activedir...")
if('adgroupmembers' in responseFromTracer):
    q = pyad.adquery.ADQuery()

    sendToTracer['adgroupmembers'] = {}
    for adGroupName in responseFromTracer['adgroupmembers']:
        sendToTracer['adgroupmembers'][adGroupName] = []

        # Build group DN from config (supports multiple OU paths via pattern matching)
        group_dn = build_group_dn(adGroupName)
        base_dn = get_base_dn()

        q.execute_query(
            attributes = ["name"],
            where_clause = f"objectClass = 'user' AND objectCategory = 'person' AND memberof = '{group_dn}'",
            base_dn = base_dn
        )

        results = q.get_results()
        for i in results:
            sendToTracer['adgroupmembers'][adGroupName].append(i.get('name'))

    # # Debug
    # print(json.dumps(sendToTracer['adgroupmembers'], indent=4))




# ----------------------------------------------------------------------------------------------------------------
# STEP 4: Send activedir data to Tracer system (Fulfill Tracer System's request)
# ----------------------------------------------------------------------------------------------------------------
print("[*] Sending data to Tracer system...")
responseFromTracer = requests.post(
    config['tracer']['tracerActivedirBridgeUrl'], 
    json=sendToTracer, 
    headers={'X-API-Key': config['tracer']['tracerActivedirBridgeApi']}
).text
print("[*] Tracer System response: " + responseFromTracer)
print(responseFromTracer)






