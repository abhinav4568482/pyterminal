#!/usr/bin/env python3
"""
PyTerminal Web - AI-Powered Terminal Emulator Web Application

A Flask-based web terminal emulator that allows users to execute system commands
through a web interface with AI-driven natural language processing capabilities.

Author: Abhinav Singh (RA2211033010203)
"""

from flask import Flask, render_template, request, jsonify, session
import subprocess
import sys
import os
import platform
import stat
from pathlib import Path
import psutil
import openai
import json
import uuid
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'pyterminal_web_secret_key_2024'

# OpenAI API configuration
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
if not OPENAI_API_KEY:
    print("Warning: OPENAI_API_KEY environment variable not set. AI features will be disabled.")
    AI_ENABLED = False
else:
    openai.api_key = OPENAI_API_KEY
    AI_ENABLED = True

# Store command history per session
command_history = {}

def get_session_id():
    """Get or create session ID for command history."""
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
    return session['session_id']

def add_to_history(session_id, command, output, success):
    """Add command to session history."""
    if session_id not in command_history:
        command_history[session_id] = []
    
    command_history[session_id].append({
        'timestamp': datetime.now().isoformat(),
        'command': command,
        'output': output,
        'success': success
    })

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
    if (len(parts) > 2 and 
        cmd not in ["pwd", "ls", "cd", "mkdir", "rm", "cat", "cpu", "mem", "memory", 
                   "processes", "ps", "help", "tellmeabout_developer", "clear"] and
        AI_ENABLED):
        return _handle_ai_command(command)
    
    # Also check for common natural language patterns even with fewer words
    natural_language_patterns = ["show me", "list all", "create a", "what is", "how to", "can you"]
    if (any(pattern in command.lower() for pattern in natural_language_patterns) and AI_ENABLED):
        return _handle_ai_command(command)
    
    # Handle native Python commands
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
    elif cmd == "clear":
        return _handle_clear()
    elif cmd == "history":
        return _handle_history()
    else:
        # For non-native commands, use subprocess
        return _handle_external_command(command)

def _handle_pwd():
    """Handle pwd command - print working directory."""
    try:
        current_dir = os.getcwd()
        return True, current_dir, ""
    except Exception as e:
        return False, "", f"Error getting current directory: {str(e)}"

def _handle_ls(args):
    """Handle ls command - list directory contents."""
    try:
        target_dir = args[0] if args else "."
        
        if not os.path.exists(target_dir):
            return False, "", f"Directory not found: '{target_dir}'"
        
        if not os.path.isdir(target_dir):
            return False, "", f"Not a directory: '{target_dir}'"
        
        items = os.listdir(target_dir)
        if not items:
            return True, "Directory is empty", ""
        
        output_lines = []
        for item in sorted(items):
            item_path = os.path.join(target_dir, item)
            if os.path.isdir(item_path):
                output_lines.append(f"📁 {item}/")
            else:
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
        
        return True, "\n".join(output_lines), ""
        
    except Exception as e:
        return False, "", f"Error listing directory: {str(e)}"

def _handle_cd_robust(args):
    """Handle cd command with robust error handling."""
    if not args:
        return False, "", "cd: missing directory argument. Usage: cd <directory>"
    
    target_dir = args[0]
    
    try:
        if target_dir == "..":
            os.chdir("..")
        elif target_dir == ".":
            pass
        elif target_dir.startswith("~"):
            target_dir = os.path.expanduser(target_dir)
            os.chdir(target_dir)
        else:
            os.chdir(target_dir)
        
        return True, f"Changed to: {os.getcwd()}", ""
        
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
    if not args:
        return False, "", "mkdir: missing directory name. Usage: mkdir <directory_name>"
    
    dir_name = args[0]
    
    try:
        os.makedirs(dir_name, exist_ok=False)
        return True, f"Created directory: {dir_name}", ""
        
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
    if not args:
        return False, "", "rm: missing file name. Usage: rm <file_name>"
    
    file_name = args[0]
    
    try:
        if os.path.isdir(file_name):
            return False, "", f"rm: cannot remove '{file_name}': Is a directory"
        
        os.remove(file_name)
        return True, f"Removed file: {file_name}", ""
        
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
    if not args:
        return False, "", "cat: missing file name. Usage: cat <file_name>"
    
    file_name = args[0]
    
    try:
        if not os.path.exists(file_name):
            return False, "", f"cat: no such file: '{file_name}'"
        
        if not os.path.isfile(file_name):
            return False, "", f"cat: '{file_name}' is not a file"
        
        with open(file_name, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
        
        return True, content, ""
        
    except FileNotFoundError:
        return False, "", f"cat: no such file: '{file_name}'"
    except PermissionError:
        return False, "", f"cat: permission denied: '{file_name}'"
    except UnicodeDecodeError:
        return False, "", f"cat: cannot read file (binary or encoding issue): '{file_name}'"
    except Exception as e:
        return False, "", f"cat: error: {str(e)}"

def _handle_cpu():
    """Handle cpu command - show CPU usage percentage."""
    try:
        cpu_percent = psutil.cpu_percent(interval=1)
        return True, f"CPU Usage: {cpu_percent}%", ""
    except Exception as e:
        return False, "", f"Error getting CPU usage: {str(e)}"

def _handle_memory():
    """Handle mem/memory command - show memory usage details."""
    try:
        memory = psutil.virtual_memory()
        
        def format_bytes(bytes_value):
            for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
                if bytes_value < 1024.0:
                    return f"{bytes_value:.1f} {unit}"
                bytes_value /= 1024.0
            return f"{bytes_value:.1f} PB"
        
        total = format_bytes(memory.total)
        available = format_bytes(memory.available)
        used = format_bytes(memory.used)
        
        output = f"Memory Usage: {memory.percent}%\n"
        output += f"Total: {total} | Available: {available} | Used: {used}"
        
        return True, output, ""
    except Exception as e:
        return False, "", f"Error getting memory usage: {str(e)}"

def _handle_processes():
    """Handle processes/ps command - show running processes."""
    try:
        processes = []
        total_count = 0
        
        for proc in psutil.process_iter(['pid', 'name']):
            total_count += 1
            try:
                processes.append((proc.info['pid'], proc.info['name']))
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
        
        processes.sort(key=lambda x: x[0])
        
        output = f"Total Processes: {total_count}\n"
        output += "Showing top 20:\n"
        output += "PID     Name\n"
        output += "-" * 30 + "\n"
        
        for pid, name in processes[:20]:
            output += f"{pid:<8} {name}\n"
        
        if total_count > 20:
            output += f"... and {total_count - 20} more processes"
        
        return True, output, ""
    except Exception as e:
        return False, "", f"Error getting process list: {str(e)}"

def _handle_help():
    """Handle help command - show available commands and descriptions."""
    try:
        ai_status = "Enabled" if AI_ENABLED else "Disabled"
        
        help_text = f"""Available Commands:
ls <dir>     - List files and directories in the current folder
cd <dir>     - Change the current working directory
pwd          - Print the current working directory
mkdir <dir>  - Create a new directory
rm <file>    - Remove a file
cat <file>   - Display the contents of a file
cpu          - Show CPU usage percentage
mem/memory   - Show Memory usage statistics
processes/ps - List running processes
clear        - Clear the terminal screen
history      - Show command history
help         - Show this help message
tellmeabout_developer - Show developer information

AI Features:
Natural Language - Type natural language commands (3+ words)
AI Status: {ai_status}

Note: External system commands are also supported through subprocess.

designed by Abhinav"""
        
        return True, help_text, ""
    except Exception as e:
        return False, "", f"Error displaying help: {str(e)}"

def _handle_developer_info():
    """Handle tellmeabout_developer command - show developer information."""
    try:
        developer_info = """
+==============================================================+
|                    DEVELOPER INFORMATION                    |
+==============================================================+
|                                                              |
|  Name:    Abhinav Singh (RA2211033010203)                   |
|                                                              |
|  College: SRM Institute of Science and Technology          |
|                                                              |
|  Course:  B.Tech Computer Science Engineering with        |
|            specialization in Software Engineering              |
|                                                              |
+==============================================================+

Thank you for using PyTerminal Web!
"""
        
        return True, developer_info, ""
    except Exception as e:
        return False, "", f"Error displaying developer information: {str(e)}"

def _handle_clear():
    """Handle clear command - clear terminal screen."""
    return True, "CLEAR_SCREEN", ""

def _handle_history():
    """Handle history command - show command history."""
    try:
        session_id = get_session_id()
        if session_id not in command_history or not command_history[session_id]:
            return True, "No commands in history", ""
        
        history_output = "Command History:\n"
        history_output += "-" * 50 + "\n"
        
        for i, entry in enumerate(command_history[session_id][-20:], 1):  # Show last 20 commands
            status = "✓" if entry['success'] else "✗"
            history_output += f"{i:2d}. {status} {entry['command']}\n"
        
        return True, history_output, ""
    except Exception as e:
        return False, "", f"Error displaying history: {str(e)}"

def interpret_natural_language(user_input):
    """
    Interpret natural language input and convert it to terminal commands using OpenAI GPT.
    """
    if not AI_ENABLED:
        return False, "", "", "AI features are disabled. Please set OPENAI_API_KEY environment variable."
    
    try:
        system_prompt = """You are a helpful assistant that converts natural language requests into terminal commands. 
Return ONLY the terminal commands needed to accomplish the task, nothing else. 
Use standard bash commands. If multiple commands are needed, separate them with &&.
Example: 
Input: "create a folder called documents and make a file notes.txt inside it"
Output: "mkdir documents && cd documents && touch notes.txt"
"""

        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input}
            ],
            max_tokens=150,
            temperature=0.1
        )
        
        ai_response = response.choices[0].message.content.strip()
        
        if ai_response:
            command = ai_response
            explanation = f"AI converted: '{user_input}' to terminal command"
            return True, command, explanation, ""
        else:
            return False, "", "", "AI could not generate a valid command."
            
    except Exception as e:
        return False, "", "", f"AI Error: {str(e)}"

def _handle_ai_command(natural_language_input):
    """Handle AI-driven natural language command processing."""
    success, command, explanation, error = interpret_natural_language(natural_language_input)
    
    if not success:
        return False, "", error
    
    if command:
        # Execute the command
        return run_command(command)
    else:
        return False, "", "AI could not generate a valid command."

def _handle_external_command(command):
    """Handle external commands using subprocess."""
    try:
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
        cmd_name = command.split()[0] if command.split() else "command"
        return False, "", f"command not found: {cmd_name}"
    except Exception as e:
        return False, "", f"Error executing external command: {str(e)}"

@app.route('/')
def index():
    """Main page with terminal interface."""
    return render_template('index.html', ai_enabled=AI_ENABLED)

@app.route('/execute', methods=['POST'])
def execute_command():
    """Execute a command and return the result."""
    try:
        data = request.get_json()
        command = data.get('command', '').strip()
        
        if not command:
            return jsonify({'success': False, 'output': '', 'error': 'Empty command'})
        
        # Handle special commands
        if command.lower() in ['exit', 'quit', 'q']:
            return jsonify({'success': True, 'output': 'Goodbye!', 'error': '', 'exit': True})
        
        # Execute the command
        success, output, error = run_command(command)
        
        # Add to history
        session_id = get_session_id()
        add_to_history(session_id, command, output, success)
        
        # Handle clear command
        if output == "CLEAR_SCREEN":
            return jsonify({'success': True, 'output': '', 'error': '', 'clear': True})
        
        return jsonify({
            'success': success,
            'output': output,
            'error': error,
            'current_dir': os.getcwd()
        })
        
    except Exception as e:
        return jsonify({'success': False, 'output': '', 'error': f'Server error: {str(e)}'})

@app.route('/history')
def get_history():
    """Get command history for current session."""
    try:
        session_id = get_session_id()
        history = command_history.get(session_id, [])
        return jsonify({'history': history})
    except Exception as e:
        return jsonify({'error': f'Error getting history: {str(e)}'})

if __name__ == '__main__':
    print("Starting PyTerminal Web...")
    print("Open your browser and go to: http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)
