CLAUDE_CONFIG = {
    "betas": {
        "code_execution":  "code-execution-2025-08-25",
        "skills": "skills-2025-10-02"
    },
    "tools": {
        "code_execution": {"type": "code_execution_20250825", "name": "code_execution"}
    },
    "skills": {
        "lead_reply_classifier": "skill_0112C4qjeAAoFJsXK7qiuJ1h",
        "response_generator": "skill_018LhMnJy1U2Jw9wGu4FGb1T"
    }
}

NO_REPLY_TYPES = ['Have onsite team', 'OptOut', 'Aggressive', 'Not relevant']
TRANSITIONS = {
    "Interested": "1576533000089318034",
    "Not Interested": "1576533000089298136",
    "Auto-reply": "1576533000520924902"
}
