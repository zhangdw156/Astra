# Generate tools.jsonl for Skill

## Objective

Analyze the SKILL.md file in the specified skill directory and generate a corresponding tools.jsonl file. The generated tools.jsonl should be placed in the skill directory.

## Environment Notes

The local environment has uv package manager installed, but does NOT have a native Python environment. Therefore:

- When running Python scripts for validation, you MUST use `uv run python` command
- DO NOT use `python` or `python3` commands directly
- Example: `uv run python {baseDir}/scripts/xxx.py`

## Directory Placeholders

Please replace the following placeholders when executing the task:

- **Target Skill Directory**: `{SKILL_DIR}` — The skill directory that needs tools.jsonl generated
- **Example Skill Directory**: `{EXAMPLE_DIR}` — The example skill directory used as reference

## Steps to Follow

### Step 1: Analyze the Example Skill

Following the progressive disclosure principle, you should explore the example skill directory as needed to understand the output format and tool structure. Start by reading the key files and explore additional files when necessary:

1. Read {EXAMPLE_DIR}/tools.jsonl to understand the output file format and structure
2. Read {EXAMPLE_DIR}/SKILL.md to understand how to extract tool information from skill definitions
3. Explore other files in {EXAMPLE_DIR}/ (such as scripts, configuration files, or documentation) as needed to fully understand the skill implementation

### Step 2: Analyze the Target Skill

Similarly, explore the target skill directory to extract all commands and functional points. Use progressive disclosure to read files as needed:

1. Read {SKILL_DIR}/SKILL.md and extract all commands and functional points
2. Explore other files in {SKILL_DIR}/ (such as scripts, configuration files, or documentation) as needed to understand the complete functionality
3. Analyze the purpose, parameters, and usage scenarios for each command based on the information gathered

### Step 3: Generate tools.jsonl

Generate tools.jsonl file based on the following format, one JSON object per line:

```json
{"name": "tool_name", "description": "Tool description", "inputSchema": {"type": "object", "properties": {...}, "required": [...]}}
```

#### Naming Conventions

- Tool names: Use snake_case format (e.g., `compare_markets`, `analyze_topic`)
- Description: Clearly explain the tool's purpose, use cases, and differences from related tools

#### inputSchema Specification

```json
{
  "type": "object",
  "properties": {
    "parameter_name": {
      "type": "parameter_type",
      "description": "Parameter description",
      "enum": ["option1", "option2"],  // Only add when there are limited values
      "default": default_value          // Only add when there is a default value
    }
  },
  "required": ["required_param1", "required_param2"]
}
```

#### Parameter Types

- Use `"type": "string"` for strings
- Use `"type": "integer"` or `"type": "number"` for numbers
- Use `"type": "boolean"` for booleans
- Use `"type": "array"` for arrays

### Step 4: Validate and Save

1. Save the generated tools.jsonl to `{SKILL_DIR}/tools.jsonl`
2. Validate the JSONL format using: `uv run python -c "import json; [json.loads(line) for line in open('{SKILL_DIR}/tools.jsonl')]"`

## Important Notes

- The number of generated tools should match the number of commands in SKILL.md
- Each tool's description should clearly explain its purpose and appropriately mention related tools to avoid confusion
- Ensure required parameters are declared in the required array
- Do not miss any commands that appear in SKILL.md