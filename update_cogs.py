import os
import re

def update_cog_file(filepath):
    with open(filepath, 'r') as f:
        content = f.read()

    # Extract class name and model name
    class_match = re.search(r'class\s+(\w+)', content)
    name_match = re.search(r'name="([^"]+)"', content)
    
    if not class_match or not name_match:
        print(f"Skipping {filepath} - Could not find class or name")
        return

    model_name = name_match.group(1)
    
    # Create trigger words list
    trigger_words = [
        f'[{model_name}]',
        f'[{model_name.lower()}]'
    ]
    
    # Add variations for models with dashes
    if '-' in model_name:
        no_dash = model_name.replace('-', '')
        trigger_words.extend([
            f'[{no_dash}]',
            f'[{no_dash.lower()}]'
        ])

    # Create trigger_words parameter string
    trigger_words_str = f'trigger_words={trigger_words}, '

    # Update the super().__init__ call
    init_pattern = r'super\(\)\.__init__\(bot,\s*'
    if 'trigger_words=' not in content:
        content = re.sub(init_pattern, f'super().__init__(bot, {trigger_words_str}', content)

    # Fix setup function to be async and use correct await
    setup_pattern = r'def setup\(bot\):'
    if 'async def setup' not in content:
        content = content.replace('def setup(bot):', 'async def setup(bot):')
        content = content.replace('bot.add_cog(', 'await bot.add_cog(')
    
    # Fix any double awaits
    content = content.replace('await await', 'await')

    # Write updated content back to file
    with open(filepath, 'w') as f:
        f.write(content)
    
    print(f"Updated {filepath}")

def main():
    cogs_dir = 'cogs'
    for filename in os.listdir(cogs_dir):
        if filename.endswith('_cog.py') and filename not in ['base_cog.py', '__init__.py']:
            filepath = os.path.join(cogs_dir, filename)
            update_cog_file(filepath)

if __name__ == '__main__':
    main()
