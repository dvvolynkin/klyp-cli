#!/usr/bin/env python3
import argparse
import json
from pathlib import Path
import sys
import os
import subprocess
import shutil
import time
import urllib.request
import urllib.error
import re # For parsing version from remote script

try:
    import pyperclip
except ImportError:
    print("Error: The 'pyperclip' library was not found. Please install it: 'pip install pyperclip'")
    print("For Linux, you might also need 'xclip' or 'xsel': 'sudo apt-get install xclip' or 'sudo apt-get install xsel'")
    sys.exit(1)

try:
    from colorama import Fore, Style, init as colorama_init
    colorama_init(autoreset=True)
except ImportError:
    class DummyColor:
        def __getattr__(self, name): return ""
    Fore = DummyColor()
    Style = DummyColor()
    print("Warning: 'colorama' library not found. Output will not be colored. Install with 'pip install colorama'.")

# --- Configuration Keys ---
CONFIG_FILE_NAME = ".klyp.json"
KLYP_IGNORE_FILE_NAME = ".klypignore"
CURRENT_SCOPE_KEY = "_klyp_current_scope"
KLYP_CONFIG_VERSION_KEY = "_klyp_version"

# Scope object keys
SCOPE_FILES_KEY = "files"
SCOPE_CONTEXT_FILE_KEY = "context_file"
SCOPE_PROMPT_FILE_KEY = "prompt_file" # New key for prompt file

# --- Constants for Update Mechanism ---
KLYP_GITHUB_USER_CONFIG = "__KLYP_GITHUB_USER__"
KLYP_GITHUB_REPO_CONFIG = "__KLYP_GITHUB_REPO__"
KLYP_DEFAULT_BRANCH_CONFIG = "__KLYP_DEFAULT_BRANCH__"
_DEFAULT_UPDATE_GITHUB_USER = "dvvolynkin"
_DEFAULT_UPDATE_GITHUB_REPO = "klyp-cli"
_DEFAULT_UPDATE_DEFAULT_BRANCH = "main"
INSTALL_SCRIPT_URL_TEMPLATE = "https://raw.githubusercontent.com/{user}/{repo}/{branch}/install.sh"

# --- Constants for Periodic Version Check ---
KLYP_CURRENT_VERSION = "0.13.0" # Incremented version
# VERSION_FILE_ON_REPO has been removed; we now parse klyp.py directly
USER_STATE_DIR_NAME = ".klyp"
USER_STATE_FILE_NAME = "state.json"
VERSION_CHECK_INTERVAL_SECONDS = 24 * 60 * 60

RESERVED_COMMAND_NAMES = set()
SCOPE_ACTION_COMMAND_NAMES = [
    'add', 'a', 'new', 'mk',
    'set', 's',
    'delete', 'del', 'rm',
    'rename', 'ren', 'mv',
    'list', 'ls'
]
SCOPE_ACTION_COMMAND_NAMES = [name.lower() for name in SCOPE_ACTION_COMMAND_NAMES]
RESERVED_KLYP_KEYS = {CURRENT_SCOPE_KEY, KLYP_CONFIG_VERSION_KEY}

# --- Utility Functions for User State (Version Check) ---
def get_user_state_dir() -> Path:
    return Path(os.path.expanduser("~")) / USER_STATE_DIR_NAME

def get_user_state_file_path() -> Path:
    return get_user_state_dir() / USER_STATE_FILE_NAME

def load_user_state() -> dict:
    state_file = get_user_state_file_path()
    if not state_file.exists(): return {}
    try:
        with open(state_file, 'r', encoding='utf-8') as f: return json.load(f)
    except (json.JSONDecodeError, IOError): return {}

def save_user_state(data: dict):
    state_dir = get_user_state_dir()
    state_file = get_user_state_file_path()
    try:
        state_dir.mkdir(parents=True, exist_ok=True)
        with open(state_file, 'w', encoding='utf-8') as f: json.dump(data, f, indent=4)
    except IOError: pass

# --- Core Configuration Handling ---
def get_config_path() -> Path:
    return Path.cwd() / CONFIG_FILE_NAME

def _initialize_scope_dict() -> dict:
    """Returns a new, empty scope dictionary with all standard keys."""
    return {
        SCOPE_FILES_KEY: [],
        SCOPE_CONTEXT_FILE_KEY: None,
        SCOPE_PROMPT_FILE_KEY: None
    }

def load_config() -> dict:
    config_path = get_config_path()
    if not config_path.exists(): return {}
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        # Ensure essential keys are present in loaded scopes for robustness
        for scope_name, scope_content in data.items():
            if not scope_name.startswith("_klyp_") and isinstance(scope_content, dict):
                if SCOPE_FILES_KEY not in scope_content:
                    scope_content[SCOPE_FILES_KEY] = []
                if SCOPE_CONTEXT_FILE_KEY not in scope_content:
                    scope_content[SCOPE_CONTEXT_FILE_KEY] = None
                if SCOPE_PROMPT_FILE_KEY not in scope_content: # Ensure prompt file key
                    scope_content[SCOPE_PROMPT_FILE_KEY] = None
        return data
    except json.JSONDecodeError:
        print(f"{Fore.RED}Error: Config file {config_path} is corrupted. Fix or delete and run 'klyp init'.{Style.RESET_ALL}")
        sys.exit(1)
    except Exception as e:
        print(f"{Fore.RED}Error loading configuration: {e}{Style.RESET_ALL}")
        sys.exit(1)

def save_config(data: dict):
    config_path = get_config_path()
    for key, value in data.items():
        if not key.startswith("_klyp_") and isinstance(value, dict): # Scope object
            if SCOPE_FILES_KEY in value and isinstance(value.get(SCOPE_FILES_KEY), list):
                data[key][SCOPE_FILES_KEY] = sorted(list(set(value[SCOPE_FILES_KEY])))
    try:
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, sort_keys=True)
    except Exception as e:
        print(f"{Fore.RED}Error saving configuration: {e}{Style.RESET_ALL}")
        sys.exit(1)

def get_current_scope_name(config: dict) -> str | None:
    return config.get(CURRENT_SCOPE_KEY)

def get_scope_data(config: dict, scope_name: str) -> dict | None:
    if not scope_name or not is_valid_scope_name(scope_name)[0]:
        return None
    scope_item = config.get(scope_name)
    if isinstance(scope_item, dict) and SCOPE_FILES_KEY in scope_item:
        # Ensure structure consistency upon retrieval, if somehow missed by load_config
        if SCOPE_CONTEXT_FILE_KEY not in scope_item:
            scope_item[SCOPE_CONTEXT_FILE_KEY] = None
        if SCOPE_PROMPT_FILE_KEY not in scope_item:
            scope_item[SCOPE_PROMPT_FILE_KEY] = None
        return scope_item
    return None

def get_display_path(absolute_path: Path, base_dir: Path) -> str:
    try:
        if not absolute_path.is_absolute():
             absolute_path = (base_dir / absolute_path).resolve()
        relative_path_str = os.path.relpath(absolute_path, base_dir)
    except ValueError: return str(absolute_path)
    display_path = Path(relative_path_str).as_posix()
    if not (display_path.startswith(('../', './')) or display_path == '.' or Path(display_path).is_absolute()):
        display_path = './' + display_path
    elif display_path == '.': display_path = './'
    return display_path

def check_config_initialized(config: dict):
    if not get_config_path().exists() and not config:
        print(f"{Fore.RED}Error: Klyp not initialized. Run 'klyp init'.{Style.RESET_ALL}")
        sys.exit(1)

def is_valid_scope_name(scope_name: str) -> tuple[bool, str]:
    if not scope_name: return False, "Scope name cannot be empty."
    if scope_name in RESERVED_KLYP_KEYS:
        return False, f"Scope name '{scope_name}' is a Klyp reserved key."
    if scope_name.lower() in RESERVED_COMMAND_NAMES:
        return False, f"Scope name '{scope_name}' is a reserved command."
    if scope_name.lower() in SCOPE_ACTION_COMMAND_NAMES:
         return False, f"Scope name '{scope_name}' is a reserved scope action."
    return True, ""

# --- .klypignore ---
def load_klypignore_patterns(project_root_dir: Path) -> list[str]:
    ignore_file_path = project_root_dir / KLYP_IGNORE_FILE_NAME
    patterns = []
    if ignore_file_path.is_file():
        try:
            with open(ignore_file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    stripped = line.strip()
                    if stripped and not stripped.startswith('#'): patterns.append(stripped)
        except IOError as e: print(f"{Fore.YELLOW}Warn: Could not read {KLYP_IGNORE_FILE_NAME}: {e}{Style.RESET_ALL}", file=sys.stderr)
    return patterns

# --- Command Handlers ---
def handle_init_cmd(args):
    config_path = get_config_path()
    config = {}
    if config_path.exists():
        try:
            with open(config_path, 'r') as f: temp_conf = json.load(f)
            if KLYP_CONFIG_VERSION_KEY in temp_conf or CURRENT_SCOPE_KEY in temp_conf:
                overwrite = input(f"{Fore.YELLOW}Config file {config_path} exists. Overwrite? (y/N): {Style.RESET_ALL}").strip().lower()
                if overwrite != 'y': print(f"{Fore.YELLOW}Init cancelled.{Style.RESET_ALL}"); return
        except (json.JSONDecodeError, IOError): pass
        print(f"{Fore.YELLOW}Overwriting config...{Style.RESET_ALL}")

    default_scope_name = "default"
    config[KLYP_CONFIG_VERSION_KEY] = KLYP_CURRENT_VERSION
    config[CURRENT_SCOPE_KEY] = default_scope_name
    config[default_scope_name] = _initialize_scope_dict()
    save_config(config)
    print(f"{Fore.GREEN}Klyp initialized. Active scope: '{default_scope_name}'.{Style.RESET_ALL}")

def handle_scope_list_cmd(args):
    config = load_config()
    check_config_initialized(config)
    active_scope = get_current_scope_name(config)
    if active_scope and get_scope_data(config, active_scope):
        print(f"Active scope: {Style.BRIGHT}{Fore.CYAN}*{active_scope}*{Style.RESET_ALL}")
    elif active_scope:
        print(f"{Fore.YELLOW}Active scope '{active_scope}' is set but invalid.{Style.RESET_ALL}")
    else:
        print(f"{Fore.YELLOW}No active scope. Use 'klyp use <name>'.{Style.RESET_ALL}")
    
    scopes = sorted([s_name for s_name in config if get_scope_data(config, s_name)])
    if scopes: print(f"Available scopes: {Fore.BLUE}{', '.join(scopes)}{Style.RESET_ALL}")
    else: print(f"{Fore.YELLOW}No scopes defined.{Style.RESET_ALL}")

def handle_scope_set_cmd(args):
    config = load_config()
    check_config_initialized(config)
    name = args.scope_name
    is_valid, err = is_valid_scope_name(name)
    if not is_valid: print(f"{Fore.RED}Error: {err}{Style.RESET_ALL}"); sys.exit(1)
    
    config[CURRENT_SCOPE_KEY] = name
    created = False
    if not get_scope_data(config, name):
        config[name] = _initialize_scope_dict()
        created = True
    save_config(config)
    if created: print(f"{Fore.GREEN}Scope '{name}' created.{Style.RESET_ALL}")
    print(f"{Fore.GREEN}Active scope set to '{name}'.{Style.RESET_ALL}")

def handle_use_cmd(args): handle_scope_set_cmd(args)

def handle_scope_add_cmd(args): # This is for adding a new scope object
    config = load_config()
    check_config_initialized(config)
    name = args.scope_name
    is_valid, err = is_valid_scope_name(name)
    if not is_valid: print(f"{Fore.RED}Error: {err}{Style.RESET_ALL}"); sys.exit(1)
    if get_scope_data(config, name):
        print(f"{Fore.YELLOW}Scope '{name}' already exists.{Style.RESET_ALL}"); return
    config[name] = _initialize_scope_dict()
    save_config(config)
    print(f"{Fore.GREEN}Scope '{name}' added.{Style.RESET_ALL}")

def handle_scope_delete_cmd(args):
    config = load_config()
    check_config_initialized(config)
    name = args.scope_name
    if not get_scope_data(config, name):
        print(f"{Fore.RED}Error: Scope '{name}' not found.{Style.RESET_ALL}"); sys.exit(1)
    confirm = input(f"{Fore.YELLOW}Delete scope '{name}'? (y/N): {Style.RESET_ALL}").strip().lower()
    if confirm == 'y':
        del config[name]
        if get_current_scope_name(config) == name:
            del config[CURRENT_SCOPE_KEY] # Or set to None, or find another scope
            print(f"{Fore.YELLOW}Active scope '{name}' unset.{Style.RESET_ALL}")
        save_config(config)
        print(f"{Fore.GREEN}Scope '{name}' deleted.{Style.RESET_ALL}")
    else: print(f"{Fore.YELLOW}Deletion cancelled.{Style.RESET_ALL}")

def handle_scope_rename_cmd(args):
    config = load_config()
    check_config_initialized(config)
    old, new = args.old_scope_name, args.new_scope_name
    if not get_scope_data(config, old):
        print(f"{Fore.RED}Error: Old scope '{old}' not found.{Style.RESET_ALL}"); sys.exit(1)
    is_valid, err = is_valid_scope_name(new)
    if not is_valid: print(f"{Fore.RED}Error: Invalid new name '{new}'. {err}{Style.RESET_ALL}"); sys.exit(1)
    if get_scope_data(config, new):
        print(f"{Fore.RED}Error: New name '{new}' already exists.{Style.RESET_ALL}"); sys.exit(1)
    if old == new: print(f"{Fore.YELLOW}Names are same.{Style.RESET_ALL}"); return
    
    config[new] = config.pop(old)
    if get_current_scope_name(config) == old: config[CURRENT_SCOPE_KEY] = new
    save_config(config)
    print(f"{Fore.GREEN}Scope '{old}' renamed to '{new}'.{Style.RESET_ALL}")

def handle_add_cmd(args):
    config = load_config()
    check_config_initialized(config)
    project_root_dir = Path.cwd()
    
    target_scope_name = args.scope_name if args.scope_name else get_current_scope_name(config)
    if not target_scope_name:
        file_type_msg = ""
        if args.add_context: file_type_msg = "--context "
        elif args.add_prompt: file_type_msg = "--prompt "
        print(f"{Fore.RED}No active scope. Specify scope: klyp add {file_type_msg}<file> <scope_name>{Style.RESET_ALL}"); sys.exit(1)

    scope_data = get_scope_data(config, target_scope_name)
    if not scope_data: # If scope doesn't exist, create it
        is_valid_fmt, err_fmt = is_valid_scope_name(target_scope_name)
        if not is_valid_fmt:
            print(f"{Fore.RED}Invalid target scope '{target_scope_name}': {err_fmt}{Style.RESET_ALL}"); sys.exit(1)
        config[target_scope_name] = _initialize_scope_dict()
        scope_data = config[target_scope_name]
        print(f"{Fore.GREEN}Scope '{target_scope_name}' created.{Style.RESET_ALL}")

    if args.add_context:
        file_to_set = Path(args.file_paths[0])
        if not file_to_set.is_file():
            print(f"{Fore.RED}Error: Context file '{file_to_set}' not found or not a file.{Style.RESET_ALL}"); sys.exit(1)
        abs_path_str = str(file_to_set.resolve())
        scope_data[SCOPE_CONTEXT_FILE_KEY] = abs_path_str
        save_config(config)
        dp = get_display_path(file_to_set, project_root_dir)
        print(f"{Fore.GREEN}Context file for scope '{target_scope_name}' set to: {dp}{Style.RESET_ALL}")
    elif args.add_prompt:
        file_to_set = Path(args.file_paths[0])
        if not file_to_set.is_file():
            print(f"{Fore.RED}Error: Prompt file '{file_to_set}' not found or not a file.{Style.RESET_ALL}"); sys.exit(1)
        abs_path_str = str(file_to_set.resolve())
        scope_data[SCOPE_PROMPT_FILE_KEY] = abs_path_str
        save_config(config)
        dp = get_display_path(file_to_set, project_root_dir)
        print(f"{Fore.GREEN}Prompt file for scope '{target_scope_name}' set to: {dp}{Style.RESET_ALL}")
    else: # Adding code files
        files_added_count = 0
        for file_path_str in args.file_paths:
            file_to_add = Path(file_path_str)
            if not file_to_add.is_file():
                print(f"{Fore.RED}Error: '{file_to_add}' is not a file. Skipping.{Style.RESET_ALL}"); continue
            
            abs_file_path_str = str(file_to_add.resolve())
            if abs_file_path_str not in scope_data[SCOPE_FILES_KEY]:
                scope_data[SCOPE_FILES_KEY].append(abs_file_path_str)
                files_added_count += 1
                dp = get_display_path(file_to_add, project_root_dir)
                print(f"{Fore.GREEN}File '{dp}' added to scope '{target_scope_name}'.{Style.RESET_ALL}")
            else:
                dp = get_display_path(file_to_add, project_root_dir)
                print(f"{Fore.YELLOW}File '{dp}' already in scope '{target_scope_name}'.{Style.RESET_ALL}")
        if files_added_count > 0:
            save_config(config)

def handle_remove_cmd(args):
    config = load_config()
    check_config_initialized(config)
    project_root_dir = Path.cwd()

    target_scope_name = args.scope_name if args.scope_name else get_current_scope_name(config)
    if not target_scope_name:
        action_msg = ""
        if args.remove_context: action_msg = "--context "
        elif args.remove_prompt: action_msg = "--prompt "
        else: action_msg = "[file] " # Placeholder as file path would be missing too
        print(f"{Fore.RED}No active scope. Specify scope: klyp remove {action_msg}<scope_name>{Style.RESET_ALL}"); sys.exit(1)
    
    scope_data = get_scope_data(config, target_scope_name)
    if not scope_data:
        print(f"{Fore.RED}Error: Scope '{target_scope_name}' not found.{Style.RESET_ALL}"); sys.exit(1)

    if args.remove_context:
        if scope_data.get(SCOPE_CONTEXT_FILE_KEY):
            scope_data[SCOPE_CONTEXT_FILE_KEY] = None
            save_config(config)
            print(f"{Fore.GREEN}Context file removed from scope '{target_scope_name}'.{Style.RESET_ALL}")
        else:
            print(f"{Fore.YELLOW}No context file set for scope '{target_scope_name}'. Nothing to remove.{Style.RESET_ALL}")
    elif args.remove_prompt:
        if scope_data.get(SCOPE_PROMPT_FILE_KEY):
            scope_data[SCOPE_PROMPT_FILE_KEY] = None
            save_config(config)
            print(f"{Fore.GREEN}Prompt file removed from scope '{target_scope_name}'.{Style.RESET_ALL}")
        else:
            print(f"{Fore.YELLOW}No prompt file set for scope '{target_scope_name}'. Nothing to remove.{Style.RESET_ALL}")
    elif args.file_path: # Removing a code file
        file_to_remove_input = Path(args.file_path)
        abs_path_to_remove_str = str(file_to_remove_input.resolve())

        if abs_path_to_remove_str in scope_data[SCOPE_FILES_KEY]:
            scope_data[SCOPE_FILES_KEY].remove(abs_path_to_remove_str)
            save_config(config)
            dp = get_display_path(file_to_remove_input, project_root_dir)
            print(f"{Fore.GREEN}File '{dp}' removed from scope '{target_scope_name}'.{Style.RESET_ALL}")
        else:
            # Try to give a helpful message if the user provided a relative path that doesn't match stored absolute
            dp_res = get_display_path(file_to_remove_input.resolve(), project_root_dir)
            print(f"{Fore.RED}Error: File '{args.file_path}' (resolved to '{dp_res}') not in scope '{target_scope_name}'.{Style.RESET_ALL}")
    # The argument parser validation in main_cli should prevent reaching here without a valid action

# --- Content Generation (`copy`/`run`) ---
def _get_formatted_scope_content(
    requested_scope_name: str | None, config: dict, project_root_dir: Path, command_verb: str
) -> tuple[str, int, int, str]:

    actual_scope_name = requested_scope_name or get_current_scope_name(config)
    if not actual_scope_name:
        print(f"{Fore.RED}Error: No active scope. Use 'klyp use <name>' or specify scope.{Style.RESET_ALL}")
        sys.exit(1)

    scope_data = get_scope_data(config, actual_scope_name)
    if not scope_data:
        print(f"{Fore.RED}Error: Scope '{actual_scope_name}' not found or invalid.{Style.RESET_ALL}")
        sys.exit(1)

    output_parts = []
    
    # 1. Context File
    context_content_str = ""
    context_file_path_str = scope_data.get(SCOPE_CONTEXT_FILE_KEY)
    if context_file_path_str:
        context_file_path = Path(context_file_path_str)
        if context_file_path.is_file():
            try:
                context_content_str = context_file_path.read_text(encoding='utf-8').strip()
                if context_content_str:
                    output_parts.append(context_content_str)
            except IOError as e:
                print(f"{Fore.YELLOW}Warning: Could not read context file '{get_display_path(context_file_path, project_root_dir)}': {e}{Style.RESET_ALL}")
        else:
            print(f"{Fore.YELLOW}Warning: Context file '{get_display_path(context_file_path, project_root_dir)}' for scope '{actual_scope_name}' is missing.{Style.RESET_ALL}")

    # 2. Code Files (Structure and Content)
    file_paths_str_list = scope_data.get(SCOPE_FILES_KEY, [])
    path_tuples_for_sorting = []
    for abs_path_str in file_paths_str_list:
        file_obj = Path(abs_path_str)
        display_p = get_display_path(file_obj, project_root_dir)
        path_tuples_for_sorting.append((display_p, abs_path_str, file_obj))
    path_tuples_for_sorting.sort(key=lambda item: item[0])

    missing_files_display = []
    files_to_process_tuples = []
    for dp, abs_p_str, f_obj in path_tuples_for_sorting:
        if not f_obj.is_file(): missing_files_display.append(dp)
        else: files_to_process_tuples.append((dp, abs_p_str))
    
    if missing_files_display:
        print(f"{Fore.RED}Error: Cannot {command_verb} from '{actual_scope_name}' due to missing files:{Style.RESET_ALL}")
        for p_disp in sorted(missing_files_display): print(f"{Fore.RED}  - {p_disp}{Style.RESET_ALL}")
        sys.exit(1)

    files_read_count = 0
    if files_to_process_tuples:
        if output_parts and output_parts[-1] and not output_parts[-1].isspace(): output_parts.append("\n\n") # Separator if context was added
        output_parts.append("Project Structure:\n```\n")
        for dp, _ in files_to_process_tuples: output_parts.append(f"{dp}\n")
        output_parts.append("```\n\n")
        for dp, abs_p_str in files_to_process_tuples:
            try:
                content = Path(abs_p_str).read_text(encoding='utf-8').strip()
                output_parts.append(f"{dp}:\n```\n{content}\n```\n\n") # Ensure newline after each file block
                files_read_count += 1
            except IOError as e: print(f"{Fore.YELLOW}Warning: Could not read file '{dp}': {e}. Skipping.{Style.RESET_ALL}")
        if not files_read_count and file_paths_str_list: # All files existed in list but none could be read
             print(f"{Fore.YELLOW}No files in scope '{actual_scope_name}' could be read.{Style.RESET_ALL}")
    
    # 3. Prompt File
    prompt_content_str = ""
    prompt_file_path_str = scope_data.get(SCOPE_PROMPT_FILE_KEY)
    if prompt_file_path_str:
        prompt_file_path = Path(prompt_file_path_str)
        if prompt_file_path.is_file():
            try:
                prompt_content_str = prompt_file_path.read_text(encoding='utf-8').strip()
                if prompt_content_str:
                    if output_parts and output_parts[-1] and not output_parts[-1].isspace() and not output_parts[-1].endswith("\n\n"):
                         # Ensure separation if last part was a file content block which already adds \n\n
                         # This condition might be tricky; simpler to just ensure a blank line if content exists
                         if not output_parts[-1].endswith("\n\n"): output_parts.append("\n") # Minimal separation
                    output_parts.append(prompt_content_str)
            except IOError as e:
                print(f"{Fore.YELLOW}Warning: Could not read prompt file '{get_display_path(prompt_file_path, project_root_dir)}': {e}{Style.RESET_ALL}")
        else:
            print(f"{Fore.YELLOW}Warning: Prompt file '{get_display_path(prompt_file_path, project_root_dir)}' for scope '{actual_scope_name}' is missing.{Style.RESET_ALL}")

    if not output_parts or all(part.isspace() for part in output_parts) :
         # This check needs to consider if only context/prompt was there but files were empty
         if not context_content_str and not file_paths_str_list and not prompt_content_str:
            print(f"{Fore.YELLOW}Scope '{actual_scope_name}' is completely empty. Nothing to {command_verb}.{Style.RESET_ALL}")
            return "", 0, 0, actual_scope_name
         elif not any(p.strip() for p in output_parts): # If parts exist but are all whitespace
            print(f"{Fore.YELLOW}Scope '{actual_scope_name}' resulted in effectively empty output. Nothing to {command_verb}.{Style.RESET_ALL}")
            return "", 0, 0, actual_scope_name


    final_str = "".join(output_parts).strip() # Strip trailing newlines from last element
    if final_str: final_str += "\n" # Ensure a single trailing newline
    return final_str, files_read_count, len(final_str), actual_scope_name

def handle_copy_cmd(args):
    config, p_root = load_config(), Path.cwd()
    check_config_initialized(config)
    content, files, chars, scope_name = _get_formatted_scope_content(args.scope_name, config, p_root, "copy")
    
    # Check if content is effectively empty (e.g. only whitespace or just a final newline)
    # files > 0 check is useful if files were listed but content couldn't be read, but _get_formatted_scope_content handles some of this
    if not content.strip() and files == 0: 
        # Check if context or prompt was set, as they might be the only content
        active_scope_name = args.scope_name or get_current_scope_name(config)
        scope_data = get_scope_data(config, active_scope_name) if active_scope_name else {}
        if not (scope_data.get(SCOPE_CONTEXT_FILE_KEY) or scope_data.get(SCOPE_PROMPT_FILE_KEY)):
             pyperclip.copy("") # Explicitly copy empty string if truly nothing to copy
             # Message already printed by _get_formatted_scope_content if scope was empty
             return 
    try:
        pyperclip.copy(content)
        if content.strip(): # Only print success if there was something meaningful to copy
            print(f"{Fore.GREEN}Scope '{scope_name}' ({files} file(s), {chars} chars) copied.{Style.RESET_ALL}")
        # If content was empty/whitespace, _get_formatted_scope_content already printed a warning
    except pyperclip.PyperclipException as e:
        print(f"{Fore.RED}Error copying: {e}{Style.RESET_ALL}"); sys.exit(1)

def handle_run_cmd(args):
    config, p_root = load_config(), Path.cwd()
    check_config_initialized(config)
    content, files, chars, scope_name = _get_formatted_scope_content(args.scope_name, config, p_root, "run")
    
    if not content.strip() and files == 0:
        # Similar logic to copy_cmd for empty content
        active_scope_name = args.scope_name or get_current_scope_name(config)
        scope_data = get_scope_data(config, active_scope_name) if active_scope_name else {}
        if not (scope_data.get(SCOPE_CONTEXT_FILE_KEY) or scope_data.get(SCOPE_PROMPT_FILE_KEY)):
            # Message already printed by _get_formatted_scope_content if scope was empty
            return

    sys.stdout.write(content)
    # _get_formatted_scope_content ensures a final newline if content is not empty
    sys.stdout.flush()
    if content.strip(): # Only print success if there was something meaningful
        print(f"{Fore.GREEN}Scope '{scope_name}' ({files} file(s), {chars} chars) printed.{Style.RESET_ALL}", file=sys.stderr)

def handle_status_cmd(args):
    config, p_root = load_config(), Path.cwd()
    check_config_initialized(config)
    print(f"{Style.BRIGHT}Klyp v{KLYP_CURRENT_VERSION} Status{Style.RESET_ALL} (Project: {p_root})")

    active_scope_name = get_current_scope_name(config)
    scopes_to_display = []
    if args.scope_name:
        if not get_scope_data(config, args.scope_name):
            print(f"{Fore.RED}Error: Scope '{args.scope_name}' not found.{Style.RESET_ALL}"); sys.exit(1)
        scopes_to_display.append(args.scope_name)
    elif active_scope_name and get_scope_data(config, active_scope_name): # Default to active if no specific scope given
        scopes_to_display.append(active_scope_name)
    else: # If no specific scope and no active scope, or active scope is invalid, show all
        all_proj_scopes = sorted([s_name for s_name in config if get_scope_data(config, s_name)])
        if not all_proj_scopes: print(f"{Fore.YELLOW}No scopes defined.{Style.RESET_ALL}"); return
        if not args.scope_name : # Only print this if user didn't specify a scope
            print(f"{Fore.YELLOW}No active scope or specific scope requested. Showing all valid scopes:{Style.RESET_ALL}")
        scopes_to_display.extend(all_proj_scopes)
        if not scopes_to_display: print(f"{Fore.YELLOW}No scopes to display status for.{Style.RESET_ALL}"); return


    for scope_name_to_show in scopes_to_display:
        scope_data = get_scope_data(config, scope_name_to_show)
        if not scope_data: # Should be caught by earlier checks, but as safeguard
            print(f"{Fore.YELLOW}Warning: Could not retrieve data for scope '{scope_name_to_show}'. Skipping.{Style.RESET_ALL}")
            continue
            
        marker = f"{Style.BRIGHT}{Fore.CYAN} (* Active){Style.RESET_ALL}" if scope_name_to_show == active_scope_name else ""
        print(f"\n{Style.BRIGHT}Scope: {Fore.MAGENTA}{scope_name_to_show}{Style.RESET_ALL}{marker}")

        # Context File
        context_file_path_str = scope_data.get(SCOPE_CONTEXT_FILE_KEY)
        if context_file_path_str:
            context_file_p = Path(context_file_path_str)
            status_ctx = f"{Fore.GREEN}[OK]{Style.RESET_ALL}" if context_file_p.is_file() else f"{Fore.RED}[MISSING]{Style.RESET_ALL}"
            print(f"  Context File: {Fore.BLUE}{get_display_path(context_file_p, p_root)}{Style.RESET_ALL} {status_ctx}")
        else:
            print(f"  Context File: {Fore.YELLOW}(Not set){Style.RESET_ALL}")

        # Prompt File
        prompt_file_path_str = scope_data.get(SCOPE_PROMPT_FILE_KEY)
        if prompt_file_path_str:
            prompt_file_p = Path(prompt_file_path_str)
            status_prompt = f"{Fore.GREEN}[OK]{Style.RESET_ALL}" if prompt_file_p.is_file() else f"{Fore.RED}[MISSING]{Style.RESET_ALL}"
            print(f"  Prompt File:  {Fore.BLUE}{get_display_path(prompt_file_p, p_root)}{Style.RESET_ALL} {status_prompt}")
        else:
            print(f"  Prompt File:  {Fore.YELLOW}(Not set){Style.RESET_ALL}")

        # Tracked Files
        files_list = scope_data.get(SCOPE_FILES_KEY, [])
        if not files_list: print(f"  Tracked Files: {Fore.YELLOW}(None){Style.RESET_ALL}"); continue
        
        print(f"  Tracked Files ({len(files_list)}):")
        sorted_file_paths = sorted(files_list, key=lambda p_str: get_display_path(Path(p_str), p_root))
        for abs_file_path_str in sorted_file_paths:
            file_p = Path(abs_file_path_str)
            status_file = f"{Fore.GREEN}[OK]{Style.RESET_ALL}" if file_p.is_file() else f"{Fore.RED}[MISSING]{Style.RESET_ALL}"
            print(f"    - {Fore.BLUE}{get_display_path(file_p, p_root)}{Style.RESET_ALL} {status_file}")
            if not file_p.is_file() and file_p.exists(): # e.g. it's a directory
                 print(f"      {Fore.YELLOW}↳ Note: Path exists but is not a regular file.{Style.RESET_ALL}")

# --- Update and Version Check ---
def get_update_repo_details():
    user = os.getenv("KLYP_UPDATE_USER", KLYP_GITHUB_USER_CONFIG)
    repo = os.getenv("KLYP_UPDATE_REPO", KLYP_GITHUB_REPO_CONFIG)
    branch = os.getenv("KLYP_UPDATE_BRANCH", KLYP_DEFAULT_BRANCH_CONFIG)
    is_default = user == KLYP_GITHUB_USER_CONFIG or repo == KLYP_GITHUB_REPO_CONFIG or branch == KLYP_DEFAULT_BRANCH_CONFIG
    user = _DEFAULT_UPDATE_GITHUB_USER if user == KLYP_GITHUB_USER_CONFIG or not user else user
    repo = _DEFAULT_UPDATE_GITHUB_REPO if repo == KLYP_GITHUB_REPO_CONFIG or not repo else repo
    branch = _DEFAULT_UPDATE_DEFAULT_BRANCH if branch == KLYP_DEFAULT_BRANCH_CONFIG or not branch else branch
    return user, repo, branch, is_default

def handle_update_cmd(args):
    print(f"{Fore.CYAN}Attempting to update Klyp...{Style.RESET_ALL}")
    user, repo, branch, used_defaults = get_update_repo_details()
    url = INSTALL_SCRIPT_URL_TEMPLATE.format(user=user, repo=repo, branch=branch)
    if used_defaults: print(f"{Fore.YELLOW}Using default update repo: {user}/{repo}@{branch}{Style.RESET_ALL}")
    else: print(f"{Fore.GREEN}Updating from: {user}/{repo}@{branch}{Style.RESET_ALL}")
    
    cmd_parts = []
    if shutil.which("curl"): cmd_parts = ["curl", "-fsSL", url]
    elif shutil.which("wget"): cmd_parts = ["wget", "-qO-", url]
    else: print(f"{Fore.RED}curl/wget not found.{Style.RESET_ALL}"); sys.exit(1)
    try:
        if not shutil.which("bash"): print(f"{Fore.RED}bash not found.{Style.RESET_ALL}"); sys.exit(1)
        dl = subprocess.Popen(cmd_parts, stdout=subprocess.PIPE, text=True)
        bash = subprocess.Popen(["bash"], stdin=dl.stdout, text=True)
        if dl.stdout: dl.stdout.close()
        rc = bash.wait(); dl.wait()
        if rc == 0 and (dl.returncode is None or dl.returncode == 0): print(f"{Fore.GREEN}Update invoked.{Style.RESET_ALL}")
        else: print(f"{Fore.RED}Update failed (dl:{dl.returncode}, bash:{rc}).{Style.RESET_ALL}")
        sys.exit(rc if rc != 0 else (dl.returncode or 0) )
    except Exception as e: print(f"{Fore.RED}Update error: {e}{Style.RESET_ALL}"); sys.exit(1)

def check_for_klyp_updates():
    user_state = load_user_state()
    last_check_timestamp = user_state.get("last_version_check_timestamp", 0.0)
    current_time = time.time()

    if (current_time - last_check_timestamp) > VERSION_CHECK_INTERVAL_SECONDS:
        user_state["last_version_check_timestamp"] = current_time
        save_user_state(user_state)

        effective_user, effective_repo, effective_branch, _ = get_update_repo_details()
        script_url = f"https://raw.githubusercontent.com/{effective_user}/{effective_repo}/{effective_branch}/klyp.py"

        try:
            req = urllib.request.Request(script_url, headers={'User-Agent': f'KlypVersionCheck/{KLYP_CURRENT_VERSION}'})
            with urllib.request.urlopen(req, timeout=10) as response:
                if response.status == 200:
                    remote_script_content = response.read().decode('utf-8')
                    match = re.search(r"""KLYP_CURRENT_VERSION\s*=\s*["']([\d\.]+)["']""", remote_script_content) # More flexible version regex
                    
                    if match:
                        latest_version_str = match.group(1)
                        try:
                            # Simple lexicographical comparison for version strings like "0.13.0", "0.2.0"
                            # For more robust, use packaging.version.parse
                            if latest_version_str > KLYP_CURRENT_VERSION:
                                print(f"{Fore.YELLOW}{Style.BRIGHT}[Klyp Update] New version ({latest_version_str}) available! "
                                      f"You have {KLYP_CURRENT_VERSION}. Run 'klyp update'.{Style.RESET_ALL}", file=sys.stderr)
                        except Exception: pass # Ignore parsing errors
        except Exception: pass # Ignore network or other errors silently


# --- Main CLI Parser Setup ---
def main_cli():
    global RESERVED_COMMAND_NAMES, SCOPE_ACTION_COMMAND_NAMES
    parser = argparse.ArgumentParser(prog="klyp",
                                     description="Manage and consolidate text from files for LLM prompts.",
                                     formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("--version", action="version", version=f"klyp v{KLYP_CURRENT_VERSION}")
    subparsers = parser.add_subparsers(dest="command_name", title="Commands", metavar="<command>", help="Available Klyp commands")

    def add_cmd_to_reserved(name, aliases=None):
        RESERVED_COMMAND_NAMES.add(name.lower())
        if aliases:
            for alias in aliases: RESERVED_COMMAND_NAMES.add(alias.lower())

    p_init = subparsers.add_parser("init", help="Initialize Klyp in the current project directory.")
    p_init.set_defaults(func=handle_init_cmd); add_cmd_to_reserved("init")

    p_scope = subparsers.add_parser("scope", help="Manage scopes. Default action is 'list'.")
    scope_subs = p_scope.add_subparsers(dest="scope_action", title="Scope actions", metavar="<action>")
    p_scope.set_defaults(func=handle_scope_list_cmd); add_cmd_to_reserved("scope")

    scope_actions_config = [
        ("list", ["ls"], "List all available scopes and show the active one.", handle_scope_list_cmd, []),
        ("add", ["new", "mk"], "Create a new, empty scope.", handle_scope_add_cmd, ["scope_name"]), # 'a' alias removed to avoid clash with main 'add'
        ("set", ["s"], "Set a scope as active. Creates it if it doesn't exist.", handle_scope_set_cmd, ["scope_name"]),
        ("delete", ["del", "rm"], "Delete an existing scope.", handle_scope_delete_cmd, ["scope_name"]),
        ("rename", ["ren", "mv"], "Rename an existing scope.", handle_scope_rename_cmd, ["old_scope_name", "new_scope_name"]),
    ]
    for cmd, aliases, hlp, func, pos_args in scope_actions_config:
        p = scope_subs.add_parser(cmd, aliases=aliases, help=hlp)
        for arg_name in pos_args: p.add_argument(arg_name)
        p.set_defaults(func=func)

    p_use = subparsers.add_parser("use", aliases=["u"], help="Set active scope (alias for 'scope set').")
    p_use.add_argument("scope_name", help="Name of the scope to set as active or create."); p_use.set_defaults(func=handle_use_cmd)
    add_cmd_to_reserved("use", ["u"])

    p_add = subparsers.add_parser("add", help="Add code files, context file, or prompt file to a scope.")
    add_group = p_add.add_mutually_exclusive_group()
    add_group.add_argument("--context", dest="add_context", action="store_true", help="The provided file is a context file.")
    add_group.add_argument("--prompt", dest="add_prompt", action="store_true", help="The provided file is a prompt file.")
    p_add.add_argument("file_paths", nargs='+', help="Path(s) to code file(s), or a single path if --context or --prompt.")
    p_add.add_argument("scope_name", nargs='?', default=None, help="Target scope name (default: current active scope).")
    p_add.set_defaults(func=handle_add_cmd); add_cmd_to_reserved("add")

    p_remove = subparsers.add_parser("remove", aliases=["rmv"], help="Remove code file, context file, or prompt file from a scope.")
    remove_group = p_remove.add_mutually_exclusive_group()
    remove_group.add_argument("--context", dest="remove_context", action="store_true", help="Remove the context file from the scope.")
    remove_group.add_argument("--prompt", dest="remove_prompt", action="store_true", help="Remove the prompt file from the scope.")
    p_remove.add_argument("file_path", nargs='?', default=None, help="Path to code file to remove (not used with --context or --prompt).")
    p_remove.add_argument("scope_name", nargs='?', default=None, help="Target scope name (default: current active scope).")
    p_remove.set_defaults(func=handle_remove_cmd); add_cmd_to_reserved("remove", ["rmv"])
    
    p_copy = subparsers.add_parser("copy", aliases=["cp"], help="Assemble scope content and copy it to the clipboard.")
    p_copy.add_argument("scope_name", nargs='?', default=None, help="Scope to copy (default: active scope)."); p_copy.set_defaults(func=handle_copy_cmd)
    add_cmd_to_reserved("copy", ["cp"])

    p_run = subparsers.add_parser("run", help="Assemble scope content and print it to standard output.")
    p_run.add_argument("scope_name", nargs='?', default=None, help="Scope to run (default: active scope)."); p_run.set_defaults(func=handle_run_cmd)
    add_cmd_to_reserved("run")

    p_status = subparsers.add_parser("status", aliases=["st"], help="Show status of scopes (files, context, prompt, missing items).")
    p_status.add_argument("scope_name", nargs='?', default=None, help="Scope to check status (default: active, or all if none active)."); p_status.set_defaults(func=handle_status_cmd)
    add_cmd_to_reserved("status", ["st"])
    
    p_update = subparsers.add_parser("update", help="Update Klyp to the latest version from its source.")
    p_update.set_defaults(func=handle_update_cmd); add_cmd_to_reserved("update")
    
    p_help = subparsers.add_parser("help", aliases=["h"], help="Show this help message and exit.")
    # For p_help, we just want it to trigger parser's own help.
    # A simple way is to let it fall through, or explicitly call print_help if it gets its own 'func'.
    # However, if 'help' is a subcommand, argparse handles it. If 'klyp help <command>' is desired, more setup needed.
    # For now, 'klyp help' or 'klyp --help' is sufficient.
    # The default behavior of a subparser with no func might be to print its own help.
    # Let's explicitly make it print the main parser's help.
    p_help.set_defaults(func=lambda args_unused, main_parser=parser: (main_parser.print_help(sys.stdout), sys.exit(0)))
    add_cmd_to_reserved("help", ["h"])


    for key in RESERVED_KLYP_KEYS: RESERVED_COMMAND_NAMES.add(key.lower())

    # Handle cases where no subcommand is given, or 'klyp <scope_name>' is used as a shortcut for 'klyp copy <scope_name>'
    # This needs to be done carefully due to argparse's parsing sequence.
    # A common pattern is to parse_known_args first if we want to intercept some arguments.

    if len(sys.argv) == 1: # No arguments, print help
        parser.print_help(sys.stdout)
        sys.exit(0)

    # Check for 'klyp <scope_name>' shortcut for 'klyp copy <scope_name>'
    # This is a bit tricky because <scope_name> could be a valid command name.
    # We'll parse normally and then, if command_name is None but other args exist, try to interpret.
    # A more robust way is to make 'copy' the default action or handle it specially.
    # For now, let's rely on explicit commands or the default 'klyp' (no args) for help.
    # If `klyp <scope_name>` is used, it should ideally map to `klyp copy <scope_name>` or `klyp run <scope_name>`.
    # The README previously suggested `klyp <scope_name>` as alias for run. Let's stick to copy for clipboard focus.

    args = parser.parse_args()
    exit_code = 0
    cmd_executed = False

    # Argument validation
    if args.command_name == "add":
        if (args.add_context or args.add_prompt) and len(args.file_paths) > 1:
            flag_used = "--context" if args.add_context else "--prompt"
            parser.error(f"argument file_paths: expected 1 file path when using {flag_used}.")
    elif args.command_name == "remove":
        if (args.remove_context or args.remove_prompt) and args.file_path:
            flag_used = "--context" if args.remove_context else "--prompt"
            parser.error(f"argument file_path: not allowed when using {flag_used} for removal.")
        if not (args.remove_context or args.remove_prompt or args.file_path):
            parser.error("For 'remove', you must specify a code file_path, or --context, or --prompt.")


    try:
        if hasattr(args, 'func') and args.func is not None:
            args.func(args)
            cmd_executed = True
        elif args.command_name == "scope" and not args.scope_action: # 'klyp scope' defaults to 'klyp scope list'
            handle_scope_list_cmd(args)
            cmd_executed = True
        elif args.command_name: # A command was given but no func matched (should not happen with proper setup)
            # This might catch if a sub-subcommand was expected but not given for 'scope'
            # Find the subparser for the command and print its help
            active_parser = parser
            if args.command_name in subparsers.choices:
                active_parser = subparsers.choices[args.command_name]
                if hasattr(args, 'scope_action') and args.scope_action and hasattr(active_parser, '_subparsers') and active_parser._subparsers:
                    # This is getting complex; rely on argparse's default help for invalid subcommands
                    pass # Let argparse handle it or fall through
            active_parser.print_help(sys.stdout)
            exit_code=1
            cmd_executed=True
        else: # No command name parsed (e.g. 'klyp --some-unknown-option')
            parser.print_help(sys.stdout)
            exit_code=1
            # args.command_name="help" # Not strictly true, but we showed help
            cmd_executed=True

    except SystemExit as e:
        exit_code = e.code if e.code is not None else 0
        cmd_executed=True # Or false if we want to say it didn't "execute" a klyp function
    except Exception as e:
        print(f"{Fore.RED}{Style.BRIGHT}An unexpected error occurred: {e}{Style.RESET_ALL}", file=sys.stderr)
        # For debugging:
        # import traceback
        # traceback.print_exc()
        exit_code=1
        cmd_executed=True
    
    # Perform update check after successful command execution (excluding update and help itself)
    if cmd_executed and exit_code == 0:
        is_informational_cmd = args.command_name in ["update", "help"] or \
                               (len(sys.argv) > 1 and sys.argv[1] in ['--version', '--help', '-h'])
        if not is_informational_cmd:
            try:
                check_for_klyp_updates()
            except Exception: # Silently ignore update check failures
                pass
            
    if exit_code != 0:
        sys.exit(exit_code)

if __name__ == "__main__":
    main_cli()