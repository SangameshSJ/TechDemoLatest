# scripts/detect_drift.py
# Detect drift in Pulumi infrastructure

#!/usr/bin/env python3

import json
import subprocess
import sys
import os
import datetime

def run_command(command):
    """Run a shell command and return the output"""
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error executing command: {command}")
        print(result.stderr)
        return None
    return result.stdout.strip()

def get_stack_resources(stack_name):
    """Get current resources in the stack"""
    # Ensure the correct stack is selected
    run_command(f"pulumi stack select {stack_name}")
    
    # Export the stack's state
    output = run_command("pulumi stack export")
    if not output:
        return None
    
    try:
        data = json.loads(output)
        return data.get("deployment", {}).get("resources", [])
    except json.JSONDecodeError:
        print("Failed to parse stack resources output")
        return None

def detect_drift(stack_name):
    """Detect infrastructure drift using Pulumi's refresh command"""
    print(f"Detecting drift for stack: {stack_name}")
    
    # First, check if the stack exists
    stacks = run_command("pulumi stack ls --json")
    if not stacks:
        print("Failed to list stacks")
        return False
    
    try:
        stacks_data = json.loads(stacks)
        stack_exists = any(s.get("name") == stack_name for s in stacks_data)
        if not stack_exists:
            print(f"Stack '{stack_name}' does not exist")
            return False
    except json.JSONDecodeError:
        print("Failed to parse stacks list")
        return False
    
    # Read the saved state file
    state_file = f"pulumi-state-{stack_name}.json"
    try:
        with open(state_file, "r") as f:
            saved_state = json.load(f)
    except FileNotFoundError:
        print(f"No saved state file found at {state_file}")
        return False
    
    # Run pulumi refresh in preview mode
    preview_output = run_command(f"pulumi preview --stack {stack_name} --json")
    if not preview_output:
        return False
    
    try:
        preview_data = json.loads(preview_output)
        changes = preview_data.get("steps", [])
        
        if not changes:
            print("No drift detected. Infrastructure is consistent with the Pulumi state.")
            return True
        
        print(f"Detected {len(changes)} changes in infrastructure:")
        for change in changes:
            resource_urn = change.get("urn", "unknown")
            op = change.get("op", "unknown")
            print(f"  - {op} operation on {resource_urn}")
        
        # If there are changes, show what specific values changed
        detailed_preview = run_command(f"pulumi preview --stack {stack_name} --diff")
        print("\nDetailed change information:")
        print(detailed_preview)
        
        return False
        
    except json.JSONDecodeError:
        print("Failed to parse Pulumi preview output as JSON")
        return False

def update_state_file(stack_name):
    """Update the state file with current resource information"""
    resources = get_stack_resources(stack_name)
    if not resources:
        return False
    
    outputs_output = run_command(f"pulumi stack output --stack {stack_name} --json")
    if not outputs_output:
        return False
    
    try:
        outputs = json.loads(outputs_output)
        state_data = {
            "last_update": str(datetime.datetime.now()),
            "stack": stack_name,
            "resource_count": len(resources),
            "outputs": outputs
        }
        
        with open(f"pulumi-state-{stack_name}.json", "w") as f:
            json.dump(state_data, f, indent=2)
        
        print(f"Updated state file for stack {stack_name}")
        return True
    except json.JSONDecodeError:
        print("Failed to parse outputs")
        return False

if __name__ == "__main__":
    # Parse command-line arguments
    if "--update-state" in sys.argv:
        # If --update-state is present, the stack name is the next argument (if provided)
        stack_name = None
        if len(sys.argv) > 2:  # Check if a stack name is provided after --update-state
            stack_name = sys.argv[2]
        else:
            # Default to the current stack
            stack_name = run_command("pulumi stack --show-name")
        
        # Update the state file
        success = update_state_file(stack_name)
        sys.exit(0 if success else 1)
    else:
        # If --update-state is not present, detect drift
        stack_name = sys.argv[1] if len(sys.argv) > 1 else run_command("pulumi stack --show-name")
        is_consistent = detect_drift(stack_name)
        sys.exit(0 if is_consistent else 1)