"""
Handles account discovery from creds directory and authentication.
"""

import os
from .config import DEFAULT_CREDS_DIR
from .upload import get_authenticated_service

def get_account_names(creds_dir, accounts_arg=None, all_accounts=False):
    """
    Build list of valid account subfolder names.
    
    Args:
        creds_dir (str): Path to creds directory.
        accounts_arg (str, optional): Comma-separated account names.
        all_accounts (bool): Use all valid subfolders.
    
    Returns:
        list: List of valid account names.
    
    Raises:
        ValueError: If no valid accounts found.
    """
    if not os.path.exists(creds_dir):
        raise ValueError(f"Creds directory '{creds_dir}' does not exist.")
    
    subdirs = [d for d in os.listdir(creds_dir) if os.path.isdir(os.path.join(creds_dir, d))]
    if not subdirs:
        raise ValueError(f"No account subfolders found in '{creds_dir}'.")
    
    if accounts_arg:
        specified_accounts = [acc.strip() for acc in accounts_arg.split(',')]
        valid_accounts = []
        for acc in specified_accounts:
            acc_path = os.path.join(creds_dir, acc)
            if os.path.exists(acc_path) and os.path.isdir(acc_path):
                client_secrets = os.path.join(acc_path, "client_secrets.json")
                if os.path.exists(client_secrets):
                    valid_accounts.append(acc)
                else:
                    print(f"Warning: Skipping account '{acc}': missing client_secrets.json")
            else:
                print(f"Warning: Skipping account '{acc}': subfolder not found")
        if not valid_accounts:
            raise ValueError("No valid accounts specified.")
        return valid_accounts
    elif all_accounts:
        valid_accounts = []
        for subdir in subdirs:
            client_secrets = os.path.join(creds_dir, subdir, "client_secrets.json")
            if os.path.exists(client_secrets):
                valid_accounts.append(subdir)
            else:
                print(f"Warning: Skipping subfolder '{subdir}': missing client_secrets.json")
        if not valid_accounts:
            raise ValueError("No valid accounts found in creds dir.")
        return valid_accounts
    else:
        # Fallback: Use first valid subfolder
        for subdir in subdirs:
            client_secrets = os.path.join(creds_dir, subdir, "client_secrets.json")
            if os.path.exists(client_secrets):
                return [subdir]
        raise ValueError("No valid account found (first subfolder with client_secrets.json).")

def authenticate_accounts(creds_dir, account_names):
    """
    Authenticate accounts and return dict of {account_name: youtube_service}.
    
    Args:
        creds_dir (str): Path to creds directory.
        account_names (list): List of account names to authenticate.
    
    Returns:
        tuple: (dict: {account_name: service}, int: num_accounts)
    
    Raises:
        ValueError: If no accounts could be authenticated.
    """
    account_services = {}
    num_accounts = 0
    for acc_name in account_names:
        acc_dir = os.path.join(creds_dir, acc_name)
        client_secrets = os.path.join(acc_dir, "client_secrets.json")
        token_file = os.path.join(acc_dir, "token.json")
        try:
            service = get_authenticated_service(client_secrets, token_file)
            account_services[acc_name] = service
            num_accounts += 1
            print(f"Authenticated account '{acc_name}' successfully.")
        except Exception as e:
            print(f"Warning: Failed to authenticate '{acc_name}': {e}. Skipping this account.")
            continue
    if not account_services:
        raise ValueError("No accounts could be authenticated.")
    return account_services, num_accounts