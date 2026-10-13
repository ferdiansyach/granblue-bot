import json

with open(r'C:\Users\iyan\.gemini\antigravity-ide\brain\cd1167f7-1bfd-43c3-9665-a65f674fa845\.system_generated\logs\transcript.jsonl', 'r', encoding='utf-8') as f:
    for line in f:
        obj = json.loads(line)
        step = obj.get('step_index')
        if step is not None and 904 <= step <= 915:
            print(f"Step {step}: {obj.get('type')}")
            content = obj.get('content')
            if content:
                print(f"  Content: {str(content)[:250]}")
            calls = obj.get('tool_calls')
            if calls:
                for c in calls:
                    print(f"  Call: {c.get('name')} {list(c.get('args', {}).keys())}")
