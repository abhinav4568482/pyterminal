#!/usr/bin/env python3
"""
Simple Python Terminal Emulator

A basic terminal emulator that allows users to execute system commands
in a loop until they type 'exit' or 'quit'.

Author: AI Assistant
"""

import subprocess
import sys
import os
import platform
import stat
from pathlib import Path
import psutil
from colorama import Fore, Style, init
import openai
import json

# --- Command History and Auto-Completion Imports ---
import readline
import atexit
import glob

# Initialize colorama for cross-platform color support
init(autoreset=True)


# --- Command History Setup ---
HISTFILE = os.path.expanduser("~/.pyterminal_history")
try:
    readline.read_history_file(HISTFILE)
except FileNotFoundError:
    pass
atexit.register(readline.write_history_file, HISTFILE)

# --- Auto-Completion Setup ---
INTERNAL_COMMANDS = [
    "ls", "cd", "pwd", "mkdir", "rm", "cat", "cpu", "mem", "memory",
    "processes", "ps", "help", "tellmeabout_developer", "clear", "exit", "quit", "q"
]

def completer(text, state):
    """
    Auto-complete for internal commands and file/directory names.
    """
    # Get the current input line
    line = readline.get_line_buffer()
    split_line = line.strip().split()
    # If first word, complete command
    if len(split_line) == 0 or (len(split_line) == 1 and not line.endswith(' ')):
        options = [cmd for cmd in INTERNAL_COMMANDS if cmd.startswith(text)]
    else:
        # Complete file/dir names for argument
        arg = text or ''
        # Use glob to match files/dirs
        options = glob.glob(arg + '*')
        # Add trailing slash for directories
        options = [o + ('/' if os.path.isdir(o) else '') for o in options]
    # If multiple options, print them all on first Tab press
    if state == 0 and len(options) > 1:
        print('\n' + '  '.join(options))
        readline.redisplay()
    try:
        return options[state]
    except IndexError:
        return None

readline.set_completer(completer)
readline.parse_and_bind('tab: complete')

# OpenAI API configuration
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
if not OPENAI_API_KEY:
    print(f"{Fore.YELLOW}Warning: OPENAI_API_KEY environment variable not set. AI features will be disabled.{Style.RESET_ALL}")
    AI_ENABLED = False
else:
    openai.api_key = OPENAI_API_KEY
    AI_ENABLED = True


def run_command(command):
    """
    Execute a command using native Python modules for core functionality,
    falling back to subprocess for external commands or AI processing.
    
    Args:
        command (str): The command to execute
        
    Returns:
        tuple: (success: bool, output: str, error: str)
    """
    # Split command into parts
    parts = command.strip().split()
    if not parts:
        return False, "", "Empty command"
    
    cmd = parts[0].lower()
    args = parts[1:] if len(parts) > 1 else []
    
    # Check if this should be processed by AI
    # If command is longer than 2 words and doesn't match any native command, use AI
    if (len(parts) > 2 and 
        cmd not in ["pwd", "ls", "cd", "mkdir", "rm", "cat", "cpu", "mem", "memory", 
                   "processes", "ps", "help", "tellmeabout_developer", "clear"] and
        AI_ENABLED):
        return _handle_ai_command(command)
    
    # Also check for common natural language patterns even with fewer words
    natural_language_patterns = ["show me", "list all", "create a", "what is", "how to", "can you"]
    if (any(pattern in command.lower() for pattern in natural_language_patterns) and AI_ENABLED):
        return _handle_ai_command(command)
    
    # Handle native Python commands with robust error handling
    if cmd == "pwd":
        return _handle_pwd()
    elif cmd == "ls":
        return _handle_ls(args)
    elif cmd == "cd":
        return _handle_cd_robust(args)
    elif cmd == "mkdir":
        return _handle_mkdir_robust(args)
    elif cmd == "rm":
        return _handle_rm_robust(args)
    elif cmd == "cat":
        return _handle_cat_robust(args)
    elif cmd == "cpu":
        return _handle_cpu()
    elif cmd in ["mem", "memory"]:
        return _handle_memory()
    elif cmd in ["processes", "ps"]:
        return _handle_processes()
    elif cmd == "help":
        return _handle_help()
    elif cmd == "tellmeabout_developer":
        return _handle_developer_info()
    else:
        # For non-native commands, use subprocess
        return _handle_external_command(command)


def _handle_pwd():
    """Handle pwd command - print working directory."""
    try:
        current_dir = os.getcwd()
        return True, current_dir + "\n", ""
    except Exception as e:
        return False, "", f"Error getting current directory: {str(e)}"


def _handle_ls(args):
    """Handle ls command - list directory contents."""
    try:
        # Get directory to list (current directory if no args)
        target_dir = args[0] if args else "."
        
        # Check if directory exists
        if not os.path.exists(target_dir):
            return False, "", f"Directory not found: '{target_dir}'"
        
        if not os.path.isdir(target_dir):
            return False, "", f"Not a directory: '{target_dir}'"
        
        # List directory contents
        items = os.listdir(target_dir)
        if not items:
            return True, "Directory is empty\n", ""
        
        # Format output with file/folder indicators
        output_lines = []
        for item in sorted(items):
            item_path = os.path.join(target_dir, item)
            if os.path.isdir(item_path):
                output_lines.append(f"📁 {item}/")
            else:
                # Get file size for display
                try:
                    size = os.path.getsize(item_path)
                    if size < 1024:
                        size_str = f"{size}B"
                    elif size < 1024 * 1024:
                        size_str = f"{size // 1024}KB"
                    else:
                        size_str = f"{size // (1024 * 1024)}MB"
                    output_lines.append(f"📄 {item} ({size_str})")
                except OSError:
                    output_lines.append(f"📄 {item}")
        
        return True, "\n".join(output_lines) + "\n", ""
        
    except Exception as e:
        return False, "", f"Error listing directory: {str(e)}"


def _handle_cd(args):
    """Handle cd command - change directory."""
    try:
        if not args:
            # No argument - go to home directory
            home_dir = os.path.expanduser("~")
            os.chdir(home_dir)
            return True, "", ""  # Silent success - prompt will show new directory
        
        target_dir = args[0]
        
        # Handle special cases
        if target_dir == "..":
            os.chdir("..")
        elif target_dir == ".":
            pass  # Stay in current directory
        elif target_dir.startswith("~"):
            # Handle tilde expansion
            target_dir = os.path.expanduser(target_dir)
            os.chdir(target_dir)
        else:
            # Regular directory change
            os.chdir(target_dir)
        
        return True, "", ""  # Silent success - prompt will show new directory
        
    except FileNotFoundError:
        return False, "", f"Directory not found: '{args[0]}'"
    except NotADirectoryError:
        return False, "", f"Not a directory: '{args[0]}'"
    except PermissionError:
        return False, "", f"Permission denied: '{args[0]}'"
    except Exception as e:
        return False, "", f"Error changing directory: {str(e)}"


def _handle_mkdir(args):
    """Handle mkdir command - create directory."""
    try:
        if not args:
            return False, "", "mkdir: missing operand"
        
        dir_name = args[0]
        
        # Check if directory already exists
        if os.path.exists(dir_name):
            if os.path.isdir(dir_name):
                return False, "", f"Directory already exists: '{dir_name}'"
            else:
                return False, "", f"File exists with same name: '{dir_name}'"
        
        # Create directory
        os.makedirs(dir_name, exist_ok=False)
        return True, f"Created directory: {dir_name}\n", ""
        
    except FileExistsError:
        return False, "", f"Directory already exists: '{args[0]}'"
    except PermissionError:
        return False, "", f"Permission denied: '{args[0]}'"
    except Exception as e:
        return False, "", f"Error creating directory: {str(e)}"


def _handle_rm(args):
    """Handle rm command - remove file."""
    try:
        if not args:
            return False, "", "rm: missing operand"
        
        file_name = args[0]
        
        # Check if file exists
        if not os.path.exists(file_name):
            return False, "", f"File not found: '{file_name}'"
        
        # Check if it's a directory (for safety, don't delete directories yet)
        if os.path.isdir(file_name):
            return False, "", f"'{file_name}' is a directory. Use 'rmdir' for directories."
        
        # Remove file
        os.remove(file_name)
        return True, f"Removed file: {file_name}\n", ""
        
    except FileNotFoundError:
        return False, "", f"File not found: '{args[0]}'"
    except PermissionError:
        return False, "", f"Permission denied: '{args[0]}'"
    except IsADirectoryError:
        return False, "", f"'{args[0]}' is a directory. Use 'rmdir' for directories."
    except Exception as e:
        return False, "", f"Error removing file: {str(e)}"


def _handle_cat(args):
    """Handle cat command - display file contents."""
    try:
        if not args:
            return False, "", "cat: missing operand"
        
        file_name = args[0]
        
        # Check if file exists
        if not os.path.exists(file_name):
            return False, "", f"File not found: '{file_name}'"
        
        if not os.path.isfile(file_name):
            return False, "", f"'{file_name}' is not a file"
        
        # Read and display file contents
        with open(file_name, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
        
        return True, content + "\n", ""
        
    except FileNotFoundError:
        return False, "", f"File not found: '{args[0]}'"
    except PermissionError:
        return False, "", f"Permission denied: '{args[0]}'"
    except UnicodeDecodeError:
        return False, "", f"Cannot read file (binary or encoding issue): '{args[0]}'"
    except Exception as e:
        return False, "", f"Error reading file: {str(e)}"


def _handle_cpu():
    """Handle cpu command - show CPU usage percentage."""
    try:
        cpu_percent = psutil.cpu_percent(interval=1)
        return True, f"{Fore.YELLOW}CPU Usage: {cpu_percent}%{Style.RESET_ALL}\n", ""
    except Exception as e:
        return False, "", f"Error getting CPU usage: {str(e)}"


def _handle_memory():
    """Handle mem/memory command - show memory usage details."""
    try:
        memory = psutil.virtual_memory()
        
        # Convert bytes to human readable format
        def format_bytes(bytes_value):
            for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
                if bytes_value < 1024.0:
                    return f"{bytes_value:.1f} {unit}"
                bytes_value /= 1024.0
            return f"{bytes_value:.1f} PB"
        
        total = format_bytes(memory.total)
        available = format_bytes(memory.available)
        used = format_bytes(memory.used)
        
        output = f"{Fore.YELLOW}Memory Usage: {memory.percent}%{Style.RESET_ALL}\n"
        output += f"{Fore.YELLOW}Total: {total} | Available: {available} | Used: {used}{Style.RESET_ALL}\n"
        
        return True, output, ""
    except Exception as e:
        return False, "", f"Error getting memory usage: {str(e)}"


def _handle_processes():
    """Handle processes/ps command - show running processes."""
    try:
        processes = []
        total_count = 0
        
        # Collect process information
        for proc in psutil.process_iter(['pid', 'name']):
            total_count += 1
            try:
                processes.append((proc.info['pid'], proc.info['name']))
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                # Skip processes that can't be accessed
                continue
        
        # Sort by PID for consistent output
        processes.sort(key=lambda x: x[0])
        
        # Format output
        output = f"Total Processes: {total_count}\n"
        output += "Showing top 20:\n"
        output += "PID     Name\n"
        output += "-" * 30 + "\n"
        
        # Show first 20 processes
        for pid, name in processes[:20]:
            output += f"{pid:<8} {name}\n"
        
        if total_count > 20:
            output += f"... and {total_count - 20} more processes\n"
        
        return True, output, ""
    except Exception as e:
        return False, "", f"Error getting process list: {str(e)}"


def _handle_help():
    """Handle help command - show available commands and descriptions."""
    try:
        ai_status = f"{Fore.GREEN}Enabled{Style.RESET_ALL}" if AI_ENABLED else f"{Fore.RED}Disabled{Style.RESET_ALL}"
        
        help_text = f"""{Fore.BLUE}Available Commands:{Style.RESET_ALL}
{Fore.CYAN}ls <dir>{Style.RESET_ALL}     - List files and directories in the current folder
{Fore.CYAN}cd <dir>{Style.RESET_ALL}     - Change the current working directory
{Fore.CYAN}pwd{Style.RESET_ALL}          - Print the current working directory
{Fore.CYAN}mkdir <dir>{Style.RESET_ALL}  - Create a new directory
{Fore.CYAN}rm <file>{Style.RESET_ALL}    - Remove a file
{Fore.CYAN}cat <file>{Style.RESET_ALL}   - Display the contents of a file
{Fore.CYAN}cpu{Style.RESET_ALL}          - Show CPU usage percentage
{Fore.CYAN}mem/memory{Style.RESET_ALL}   - Show Memory usage statistics
{Fore.CYAN}processes/ps{Style.RESET_ALL} - List running processes
{Fore.CYAN}clear{Style.RESET_ALL}        - Clear the terminal screen
{Fore.CYAN}help{Style.RESET_ALL}         - Show this help message
{Fore.CYAN}tellmeabout_developer{Style.RESET_ALL} - Show developer information
{Fore.CYAN}exit/quit{Style.RESET_ALL}    - Exit the terminal

{Fore.MAGENTA}AI Features:{Style.RESET_ALL}
{Fore.CYAN}Natural Language{Style.RESET_ALL} - Type natural language commands (3+ words)
{Fore.CYAN}AI Status:{Style.RESET_ALL} {ai_status}

{Fore.YELLOW}Note: External system commands are also supported through subprocess.{Style.RESET_ALL}

{Fore.LIGHTBLUE_EX}designed by Abhinav{Style.RESET_ALL}"""
        
        return True, help_text + "\n", ""
    except Exception as e:
        return False, "", f"Error displaying help: {str(e)}"


def _handle_developer_info():
    """Handle tellmeabout_developer command - show developer information."""
    try:
        developer_info = f"""
{Fore.CYAN}+==============================================================+{Style.RESET_ALL}
{Fore.CYAN}|                    {Style.BRIGHT}DEVELOPER INFORMATION{Style.RESET_ALL}{Fore.CYAN}                    |{Style.RESET_ALL}
{Fore.CYAN}+==============================================================+{Style.RESET_ALL}
{Fore.CYAN}|{Style.RESET_ALL}                                                              {Fore.CYAN}|{Style.RESET_ALL}
{Fore.CYAN}|{Style.RESET_ALL}  {Fore.GREEN}Name:{Style.RESET_ALL}    Abhinav Singh (RA2211033010203)                    {Fore.CYAN}|{Style.RESET_ALL}
{Fore.CYAN}|{Style.RESET_ALL}                                                              {Fore.CYAN}|{Style.RESET_ALL}
{Fore.CYAN}|{Style.RESET_ALL}  {Fore.GREEN}College:{Style.RESET_ALL} SRM Institute of Science and Technology          {Fore.CYAN}|{Style.RESET_ALL}
{Fore.CYAN}|{Style.RESET_ALL}                                                              {Fore.CYAN}|{Style.RESET_ALL}
{Fore.CYAN}|{Style.RESET_ALL}  {Fore.GREEN}Course:{Style.RESET_ALL}  B.Tech Computer Science Engineering with        {Fore.CYAN}|{Style.RESET_ALL}
{Fore.CYAN}|{Style.RESET_ALL}            specialization in Software Engineering              {Fore.CYAN}|{Style.RESET_ALL}
{Fore.CYAN}|{Style.RESET_ALL}                                                              {Fore.CYAN}|{Style.RESET_ALL}
{Fore.CYAN}+==============================================================+{Style.RESET_ALL}

{Fore.LIGHTBLUE_EX}Thank you for using PyTerminal!{Style.RESET_ALL}
"""
        
        return True, developer_info, ""
    except Exception as e:
        return False, "", f"Error displaying developer information: {str(e)}"


def interpret_natural_language(user_input):
    """
    Interpret natural language input and convert it to terminal commands using OpenAI GPT.
    
    Args:
        user_input (str): Natural language command from user
        
    Returns:
        tuple: (success: bool, command: str, explanation: str, error: str)
    """
    if not AI_ENABLED:
        return False, "", "", f"{Fore.RED}AI features are disabled. Please set OPENAI_API_KEY environment variable.{Style.RESET_ALL}"
    
    try:
        # Use the exact system prompt as specified
        system_prompt = """You are a helpful assistant that converts natural language requests into terminal commands. 
Return ONLY the terminal commands needed to accomplish the task, nothing else. 
Use standard bash commands. If multiple commands are needed, separate them with &&.
Example: 
Input: "create a folder called documents and make a file notes.txt inside it"
Output: "mkdir documents && cd documents && touch notes.txt"
"""

        # Call OpenAI API with specified settings
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input}
            ],
            max_tokens=150,
            temperature=0.1
        )
        
        # Parse the AI response (now returns plain text commands)
        ai_response = response.choices[0].message.content.strip()
        
        if ai_response:
            # AI now returns plain text commands directly
            command = ai_response
            explanation = f"AI converted: '{user_input}' to terminal command"
            return True, command, explanation, ""
        else:
            return False, "", "", f"{Fore.RED}AI could not generate a valid command.{Style.RESET_ALL}"
            
    except openai.error.AuthenticationError:
        return False, "", "", f"{Fore.RED}AI Error: Invalid API key. Please check your OPENAI_API_KEY.{Style.RESET_ALL}"
    
    except openai.error.RateLimitError:
        return False, "", "", f"{Fore.RED}AI Error: Rate limit exceeded. Please try again in a moment.{Style.RESET_ALL}"
    
    except openai.error.APIConnectionError:
        return False, "", "", f"{Fore.RED}AI Error: Unable to connect to OpenAI service. Check your internet connection.{Style.RESET_ALL}"
    
    except openai.error.APIError as e:
        return False, "", "", f"{Fore.RED}AI Error: OpenAI API error - {str(e)}{Style.RESET_ALL}"
    
    except openai.error.InvalidRequestError as e:
        return False, "", "", f"{Fore.RED}AI Error: Invalid request - {str(e)}{Style.RESET_ALL}"
    
    except openai.error.Timeout:
        return False, "", "", f"{Fore.RED}AI Error: Request timed out. Please try again.{Style.RESET_ALL}"
    
    except ConnectionError:
        return False, "", "", f"{Fore.RED}AI Error: Network connection failed. Please check your internet connection.{Style.RESET_ALL}"
    
    except Exception as e:
        return False, "", "", f"{Fore.RED}AI Error: Unexpected error occurred - {str(e)}{Style.RESET_ALL}"


def _handle_ai_command(natural_language_input):
    """Handle AI-driven natural language command processing."""
    # Use the new interpret_natural_language function
    success, command, explanation, error = interpret_natural_language(natural_language_input)
    
    if not success:
        return False, "", error
    
    if command:
        # Display AI suggestion and explanation
        print(f"{Fore.CYAN}AI Suggestion: {command}{Style.RESET_ALL}")
        if explanation:
            print(f"{Fore.YELLOW}Explanation: {explanation}{Style.RESET_ALL}")
        print()
        
        # Execute the command
        return run_command(command)
    else:
        return False, "", f"{Fore.RED}AI could not generate a valid command.{Style.RESET_ALL}"


def _handle_cd_robust(args):
    """Handle cd command with robust error handling."""
    # Check if argument was provided
    if not args:
        return False, "", "cd: missing directory argument. Usage: cd <directory>"
    
    target_dir = args[0]
    
    try:
        # Handle special cases
        if target_dir == "..":
            os.chdir("..")
        elif target_dir == ".":
            pass  # Stay in current directory
        elif target_dir.startswith("~"):
            # Handle tilde expansion
            target_dir = os.path.expanduser(target_dir)
            os.chdir(target_dir)
        else:
            # Regular directory change
            os.chdir(target_dir)
        
        return True, "", ""  # Silent success - prompt will show new directory
        
    except FileNotFoundError:
        return False, "", f"cd: no such directory: '{args[0]}'"
    except NotADirectoryError:
        return False, "", f"cd: not a directory: '{args[0]}'"
    except PermissionError:
        return False, "", f"cd: permission denied: '{args[0]}'"
    except Exception as e:
        return False, "", f"cd: error: {str(e)}"


def _handle_mkdir_robust(args):
    """Handle mkdir command with robust error handling."""
    # Check if argument was provided
    if not args:
        return False, "", "mkdir: missing directory name. Usage: mkdir <directory_name>"
    
    dir_name = args[0]
    
    try:
        # Create directory
        os.makedirs(dir_name, exist_ok=False)
        return True, f"{Fore.GREEN}Created directory: {dir_name}{Style.RESET_ALL}\n", ""
        
    except FileExistsError:
        return False, "", f"mkdir: cannot create directory '{dir_name}': File exists"
    except PermissionError:
        return False, "", f"mkdir: permission denied: '{dir_name}'"
    except OSError as e:
        return False, "", f"mkdir: cannot create directory '{dir_name}': {str(e)}"
    except Exception as e:
        return False, "", f"mkdir: error: {str(e)}"


def _handle_rm_robust(args):
    """Handle rm command with robust error handling."""
    # Check if argument was provided
    if not args:
        return False, "", "rm: missing file name. Usage: rm <file_name>"
    
    file_name = args[0]
    
    try:
        # Check if it's a directory (for safety, don't delete directories yet)
        if os.path.isdir(file_name):
            return False, "", f"rm: cannot remove '{file_name}': Is a directory"
        
        # Remove file
        os.remove(file_name)
        return True, f"{Fore.GREEN}Removed file: {file_name}{Style.RESET_ALL}\n", ""
        
    except FileNotFoundError:
        return False, "", f"rm: cannot remove '{file_name}': No such file"
    except IsADirectoryError:
        return False, "", f"rm: cannot remove '{file_name}': Is a directory"
    except PermissionError:
        return False, "", f"rm: permission denied: '{file_name}'"
    except Exception as e:
        return False, "", f"rm: error: {str(e)}"


def _handle_cat_robust(args):
    """Handle cat command with robust error handling."""
    # Check if argument was provided
    if not args:
        return False, "", "cat: missing file name. Usage: cat <file_name>"
    
    file_name = args[0]
    
    try:
        # Check if file exists
        if not os.path.exists(file_name):
            return False, "", f"cat: no such file: '{file_name}'"
        
        if not os.path.isfile(file_name):
            return False, "", f"cat: '{file_name}' is not a file"
        
        # Read and display file contents
        with open(file_name, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
        
        return True, content + "\n", ""
        
    except FileNotFoundError:
        return False, "", f"cat: no such file: '{file_name}'"
    except PermissionError:
        return False, "", f"cat: permission denied: '{file_name}'"
    except UnicodeDecodeError:
        return False, "", f"cat: cannot read file (binary or encoding issue): '{file_name}'"
    except Exception as e:
        return False, "", f"cat: error: {str(e)}"


def _handle_external_command(command):
    """Handle external commands using subprocess."""
    try:
        # Handle different shell commands based on the operating system
        if platform.system() == "Windows":
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30
            )
        else:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30
            )
        
        if result.returncode == 0:
            return True, result.stdout, result.stderr
        else:
            return False, result.stdout, result.stderr
            
    except subprocess.TimeoutExpired:
        return False, "", "Command timed out after 30 seconds"
    except FileNotFoundError:
        # Extract command name for better error message
        cmd_name = command.split()[0] if command.split() else "command"
        return False, "", f"command not found: {cmd_name}"
    except Exception as e:
        return False, "", f"Error executing external command: {str(e)}"




def get_prompt():
    """
    Generate the terminal prompt string with current working directory.
    
    Returns:
        str: Colorized formatted prompt string
    """
    try:
        current_dir = os.getcwd()
        # Truncate long paths for better readability
        if len(current_dir) > 50:
            current_dir = "..." + current_dir[-47:]
        return f"{Fore.GREEN}[{current_dir}]{Style.RESET_ALL} {Fore.LIGHTGREEN_EX}$ {Style.RESET_ALL}"
    except Exception:
        return f"{Fore.LIGHTGREEN_EX}$ {Style.RESET_ALL}"


def main():
    """
    Main function that runs the terminal emulator loop.
    """
    # Clear the screen for a clean start
    os.system('cls' if os.name == 'nt' else 'clear')
    
    # Display persistent header with colors
    print(Fore.CYAN + "=" * 60)
    print(Fore.CYAN + Style.BRIGHT + "            PyTerminal (Python Powered)")
    print(Fore.LIGHTBLUE_EX + "                designed by Abhinav")
    print(Fore.YELLOW + "Type 'help' for available commands.")
    print(Fore.CYAN + "=" * 60)
    
    # Main terminal loop
    while True:
        try:
            # Display custom prompt and get user input
            user_input = input(get_prompt())
            
            # Handle empty input
            if not user_input:
                continue
                
            # Handle exit commands
            if user_input.lower() in ['exit', 'quit', 'q']:
                print("Goodbye!")
                break
                
            # Handle clear command
            if user_input.lower() == 'clear':
                os.system('cls' if os.name == 'nt' else 'clear')
                # Re-display header after clear
                print(Fore.CYAN + "=" * 60)
                print(Fore.CYAN + Style.BRIGHT + "            PyTerminal (Python Powered)")
                print(Fore.LIGHTBLUE_EX + "                designed by Abhinav")
                print(Fore.YELLOW + "Type 'help' for available commands.")
                print(Fore.CYAN + "=" * 60)
                continue
            
            # Execute the command
            success, output, error = run_command(user_input)
            
            # Display results
            if success:
                if output:
                    print(output, end="")
                if error:
                    print(f"{Fore.YELLOW}Warning: {error}{Style.RESET_ALL}", end="")
            else:
                if error:
                    print(f"{Fore.RED}Error: {error}{Style.RESET_ALL}", end="")
                if output:
                    print(f"Output: {output}", end="")
                    
        except KeyboardInterrupt:
            print("\n\nUse 'exit' or 'quit' to close the terminal")
            continue
        except EOFError:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"\nUnexpected error: {str(e)}")
            continue


if __name__ == "__main__":
    main()
