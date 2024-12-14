#!/Users/donyin/miniconda3/envs/common/bin/python
import os
import sqlite3
from typing import List, Any, Dict
from src.api.antropic import AntropicResponse


class Field:
    def __init__(self):
        self.cache_dir = "cache"
        self.db_path = os.path.join(self.cache_dir, "database.db")
        self._init_db()

    def _init_db(self):
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS email_cache (
                email_id TEXT PRIMARY KEY,
                compulsory INTEGER,
                opportunity_score REAL,
                harm_score REAL,
                actions TEXT,
                intention TEXT,
                compulsory_cost REAL,
                opportunity_cost REAL,
                harm_cost REAL,
                actions_cost REAL,
                intention_cost REAL,
                model_name TEXT
            )
        """
        )
        conn.commit()
        conn.close()

    def get(self, email_id: str, field_name: str) -> Any:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(f"SELECT {field_name} FROM email_cache WHERE email_id = ?", (email_id,))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else None

    def save(self, email_id: str, **fields):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Check if email_id exists
        cursor.execute("SELECT 1 FROM email_cache WHERE email_id = ?", (email_id,))
        exists = cursor.fetchone() is not None

        if exists:
            # Update existing record
            set_clause = ", ".join([f"{k} = ?" for k in fields.keys()])
            values = list(fields.values()) + [email_id]
            cursor.execute(f"UPDATE email_cache SET {set_clause} WHERE email_id = ?", values)
        else:
            # Insert new record
            columns = ["email_id"] + list(fields.keys())
            placeholders = ",".join(["?" for _ in range(len(columns))])
            values = [email_id] + list(fields.values())
            cursor.execute(f"INSERT INTO email_cache ({','.join(columns)}) VALUES ({placeholders})", values)

        conn.commit()
        conn.close()


field = Field()


def analyze_compulsory(user_background: str, content_email: str, email_id: str) -> bool:
    """Determine if the email requires mandatory attention."""
    # Check cache first
    cached_result = field.get(email_id, "compulsory")
    if cached_result is not None:
        return bool(cached_result)

    prompt = f"""Given this user background: {user_background}
And this email content: {content_email}

Determine if this email requires mandatory/compulsory attention.
Return a **Python dictionary** with key 'compulsory' and a boolean value.
Consider factors like urgency, sender authority, legal obligations, etc.

**Your response should be in the form:**
{{'compulsory': True}}
"""

    response = AntropicResponse(prompt, requested_keys=["compulsory"])
    result, total_cost, name_model = response.get_completion()

    # Get the boolean value directly from the dictionary
    is_compulsory = result.get("compulsory", False)

    field.save(email_id, compulsory=int(is_compulsory), compulsory_cost=total_cost, model_name=name_model)
    return is_compulsory


def analyze_opportunity(user_background: str, content_email: str, email_id: str) -> float:
    """Score the career development opportunity (0-10)."""
    # Check cache first
    cached_result = field.get(email_id, "opportunity_score")
    if cached_result is not None:
        return float(cached_result)

    prompt = f"""Given this user background: {user_background}
    And this email content: {content_email}
    
    Score the career development opportunity from 0-10.
    Return a dictionary with key 'opportunity_score'.
    Consider factors like networking potential, skill development, visibility, etc.

    Your response should be in the form:
    {{'opportunity_score': 7.5}}
    """

    response = AntropicResponse(prompt, requested_keys=["opportunity_score"])
    result, total_cost, name_model = response.get_completion()
    score = float(result.get("opportunity_score", 5.0))

    field.save(email_id, opportunity_score=score, opportunity_cost=total_cost, model_name=name_model)
    return score


def analyze_harm(user_background: str, content_email: str, email_id: str) -> float:
    """Score potential harm of ignoring (0-10)."""
    # Check cache first
    cached_result = field.get(email_id, "harm_score")
    if cached_result is not None:
        return float(cached_result)

    prompt = f"""Given this user background: {user_background}
    And this email content: {content_email}
    
    Score the potential harm/risk of ignoring this email from 0-10.
    E.g., if the email is about a weekly news letter, the harm score should be 0.
    If this is from the supervisor about a deadline, the harm score should be 10. etc

    Return a dictionary with key 'harm_score'.
    Consider factors like relationship damage, missed deadlines, legal risks, etc."""

    response = AntropicResponse(prompt, ["harm_score"])
    result, total_cost, name_model = response.get_completion()
    score = float(result.get("harm_score", 5.0))

    # Save to cache
    field.save(email_id, harm_score=score, harm_cost=total_cost, model_name=name_model)
    return score


def analyze_actions(user_background: str, content_email: str, email_id: str) -> str:
    """Recommend action steps."""
    # Check cache first
    cached_result = field.get(email_id, "actions")
    if cached_result is not None:
        return cached_result

    prompt = f"""Given this user background: {user_background}
    And this email content: {content_email}
    
    First of all determine whether the email explicitly asks for a confirmation or response.
    And recommend specific action steps to handle the situation.
    Return a dictionary with key 'actions' containing a newline-separated string of actions.
    Be specific and practical.

    Your response should be in the form:
    {{'actions': 'Action 1\\nAction 2\\nAction 3'}}
    5 steps max, be extremely concise and content-focused, no fluff.
    """

    response = AntropicResponse(prompt, ["actions"])
    result, total_cost, name_model = response.get_completion()
    actions_str = result.get("actions", "Review email\nDraft response")

    # Store the string directly
    field.save(email_id, actions=actions_str, actions_cost=total_cost, model_name=name_model)
    return actions_str


def analyze_intention(user_background: str, content_email: str, email_id: str) -> str:
    """Analyze sender's intention."""
    # Check cache first
    cached_result = field.get(email_id, "intention")
    if cached_result is not None:
        return cached_result

    prompt = f"""Given this user background: {user_background}
    And this email content: {content_email}
    
    Analyze the sender's primary intention/purpose.
    Return a dictionary with key 'intention' containing a brief description.
    Be concise but insightful.
    
    Your response should be in the form:
    {{'intention': 'Brief description'}}
    """

    response = AntropicResponse(prompt, ["intention"])
    result, total_cost, name_model = response.get_completion()
    intention = result.get("intention", "Request for information")

    field.save(email_id, intention=intention, intention_cost=total_cost, model_name=name_model)
    return intention


def analyze_priority(user_background: str, content_email: str, email_id: str) -> Dict[str, Any]:
    """Analyze priority metrics (compulsory, opportunity, harm) in a single call."""
    # Check cache first for all three values
    cached_compulsory = field.get(email_id, "compulsory")
    cached_opportunity = field.get(email_id, "opportunity_score")
    cached_harm = field.get(email_id, "harm_score")

    if all(x is not None for x in [cached_compulsory, cached_opportunity, cached_harm]):
        return {
            "compulsory": bool(cached_compulsory),
            "opportunity_score": float(cached_opportunity),
            "harm_score": float(cached_harm)
        }

    prompt = f"""Given this user background: {user_background}
    And this email content: {content_email}
    
    Analyze the priority of this email by providing three metrics:
    1. Whether this email requires mandatory/compulsory attention (boolean)
    2. Career development opportunity score (0-10)
    3. Potential harm/risk score if ignored (0-10)

    Return a Python dictionary with three keys:
    - 'compulsory': boolean indicating if mandatory attention is required
    - 'opportunity_score': float (0-10) indicating career development potential
    - 'harm_score': float (0-10) indicating potential harm if ignored

    Consider:
    - For compulsory: urgency, sender authority, legal obligations
    - For opportunity: networking potential, skill development, visibility
    - For harm: relationship damage, missed deadlines, legal risks

    Your response should be in the form:
    {{'compulsory': True, 'opportunity_score': 7.5, 'harm_score': 8.0}}
    """

    response = AntropicResponse(prompt, requested_keys=["compulsory", "opportunity_score", "harm_score"])
    result, total_cost, name_model = response.get_completion()

    # Extract values with defaults
    priority_analysis = {
        "compulsory": result.get("compulsory", False),
        "opportunity_score": float(result.get("opportunity_score", 5.0)),
        "harm_score": float(result.get("harm_score", 5.0))
    }

    # Save all values to cache, including the cost
    field.save(
        email_id,
        compulsory=int(priority_analysis["compulsory"]),
        opportunity_score=priority_analysis["opportunity_score"],
        harm_score=priority_analysis["harm_score"],
        compulsory_cost=total_cost,  # Save the cost
        model_name=name_model
    )

    return priority_analysis


if __name__ == "__main__":
    user_background = "Software engineer working on ML projects"
    test_email = """
    Hi,
    
    The quarterly planning meeting is scheduled for next Tuesday at 2pm. 
    We'll be discussing the ML model deployment timeline and resource allocation.
    Please prepare a brief update on your current projects.
    
    Best regards,
    Manager
    """
    email_id = "test123"

    # Test analyze_actions
    print("\nTesting analyze_actions:")
    actions = analyze_actions(user_background, test_email, email_id)
    print("Recommended actions:")
    print(actions)  # Print the string directly

    # Test analyze_intention
    print("\nTesting analyze_intention:")
    intention = analyze_intention(user_background, test_email, email_id)
    print(f"Sender intention: {intention}")
