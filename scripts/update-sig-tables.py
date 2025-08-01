#!/usr/bin/env python3
import pip
import sys

# in the Makefile we use a unmodified python container to run this script, so we need to install pyyaml if it's not already installed
if (len(sys.argv) > 1) and (sys.argv[1] == "--install"):
    pip.main(['install', 'pyyaml'])
    sys.argv = sys.argv[1:]

import yaml

# Do not safe the file but verify that it is different from the original one.
run_in_check_mode = (len(sys.argv) > 1) and (sys.argv[1] == "--check")

# Define the YAML input file and the markdown file to be updated
yaml_input = "sigs.yml"
markdown_file = "README.md"

# Define the markers
start_marker = "<!-- sigs -->"
end_marker = "<!-- endsigs -->"

def format_chat(chat):
    if chat['type'] == 'slack':
        return f"[{chat['name']}](https://cloud-native.slack.com/archives/{chat['id']})"
    elif chat['type'] == 'other':
        return f"[{chat['name']}]({chat['link']})"
    else:
        return ""

# Read the YAML file
with open(yaml_input, 'r') as file:
    data = yaml.safe_load(file)

# Extract the top and bottom parts of the existing markdown file
with open(markdown_file, 'r') as file:
    content = file.read()
    top_part, bottom_part = content.split(start_marker, 1)[0], content.split(end_marker, 1)[1]

# Generate the markdown content for each SIG group
markdown_content = start_marker + '\n'
for group in data:
    # Group heading
    group_name = group['name']
    markdown_content += f"### {group_name}\n\n"

    # Table headers (removing unsupported CSS styling)
    markdown_content += "| Name | Meeting Information | Slack Channel | Repositories |\n"
    markdown_content += "|------|---------------------|---------------|-------------|\n"

    # Table rows for SIGs
    for sig in group['sigs']:
        name = sig['name']
        meeting = sig.get('meeting', '')
        notes_type = sig['notes'].get('type', '')
        notes_value = sig['notes'].get('value', '')

        chats = " and ".join(
            [format_chat(chat) 
            for chat in sig.get('chat', [])
            if chat.get('name') and chat.get('type')]
        )

        short_name = None
        for chat in sig.get('chat', []):
            if chat.get('type') == 'slack':
                short_name = 'sig-' + chat.get('name').replace('#otel-', '').replace('sig-', '')
                break

        invites = sig.get('invites', 'none')

        # Process repositories with smaller text
        repositories = sig.get('repositories', [])
        repo_links = []
        for repo_url in repositories:
            if repo_url.startswith('https://github.com/'):
                repo_name = repo_url.split('/')[-1]
                repo_links.append(f"<sub>[{repo_name}]({repo_url})</sub>")
        
        repos_formatted = "<br/>".join(repo_links) if repo_links else ""

        # Construct notes and calendar entries based on type
        if notes_type == "gDoc":
            notes = f"[Meeting Notes](https://docs.google.com/document/d/{notes_value})"
        else:
            notes = notes_value if notes_value else ""
        
        if invites == "none":
            calendar = ""
        else:
            calendar = f"[Calendar]({invites})" if invites else ""
        
        # Combine meeting time, notes, and calendar into a single cell with smaller text
        meeting_info_parts = []
        if meeting:
            meeting_info_parts.append(f"<sub>**Time:** {meeting}</sub>")
        if notes:
            meeting_info_parts.append(f"<sub>**Notes:** {notes}</sub>")
        if calendar:
            meeting_invite_link = f"https://groups.google.com/a/opentelemetry.io/g/{invites}" if invites != "none" else ""
            if meeting_invite_link:
                meeting_info_parts.append(f"<sub>**Calendar:** [Join Meeting Group]({meeting_invite_link})</sub>")
        
        meeting_info = "<br/>".join(meeting_info_parts) if meeting_info_parts else ""
        
        markdown_content += f"| <a id=\"{short_name}\"></a>{name} | {meeting_info} | {chats} | {repos_formatted} |\n"

    # Add spacing after the table
    markdown_content += "\n\n"

markdown_content += end_marker

result = top_part + markdown_content + bottom_part

if run_in_check_mode:
    with open(markdown_file, 'r') as file:
        original = file.read()
    if original == result:
        sys.exit(0)
    else:
        sys.exit(1)
else:
    # Write the updated markdown content to file
    with open(markdown_file, 'w') as file:
        file.write(top_part)
        file.write(markdown_content)
        file.write(bottom_part)

# Inform the user that the markdown file has been updated
print("The markdown file has been updated with the new SIG tables.")
