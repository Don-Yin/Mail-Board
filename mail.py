#!/Users/donyin/miniconda3/envs/common/bin/python

"""
Outlook email handler for macOS - provides email counting, content retrieval, and intelligent analysis
"""

from datetime import datetime
from dataclasses import dataclass
from typing import Dict, List, Optional
from appscript import app as appscript_app
from flask import Flask, render_template, redirect, url_for, jsonify
import hashlib, yaml, threading

from src.analytics.fields import analyze_priority, analyze_actions, analyze_intention, field


@dataclass
class EmailAnalysis:
    is_compulsory: bool
    opportunity_score: float  # 0-10
    harm_score: float  # 0-10
    recommended_actions: str
    sender_intention: str
    compulsory_cost: float
    opportunity_cost: float
    harm_cost: float
    actions_cost: float
    intention_cost: float
    model_name: str


@dataclass
class EmailMessage:
    message_id: str
    subject: str
    sender: str
    date: datetime
    cc: List[str]
    content: str
    unread: bool
    analysis: Optional[EmailAnalysis] = None


# Load user background from configurations file
with open("configurations.yaml", "r") as f:
    configurations = yaml.safe_load(f)
    USER_BACKGROUND = configurations["USER_BACKGROUND"]


class OutlookMailbox:
    def __init__(self):
        self.outlook = appscript_app("Microsoft Outlook")
        self.inbox = self.outlook.inbox.get()

    def get_inbox_count(self) -> Optional[Dict[str, int]]:
        try:
            return {"total": len(self.inbox.messages.get()), "unread": self.inbox.unread_count.get()}
        except Exception as e:
            print(f"Error getting inbox count: {str(e)}")
            return None

    def _get_email_address(self, recipient) -> str:
        return str(recipient)

    def _generate_message_id(self, msg) -> str:
        components = [
            str(msg.subject.get() if hasattr(msg.subject, "get") else msg.subject),
            str(self._get_email_address(msg.sender.get())),
            str(msg.time_received.get() if hasattr(msg.time_received, "get") else datetime.now()),
        ]
        return hashlib.md5("".join(components).encode()).hexdigest()

    def _process_message(self, msg) -> EmailMessage:
        sender = "Unknown"
        content = "<p>No content available</p>"
        subject = "Error loading message"

        date = datetime.now()
        is_read = False
        cc_recipients = []

        sender = self._get_email_address(msg.sender.get())

        content = msg.content.get() if hasattr(msg.content, "get") else str(msg.content)
        if hasattr(msg, "html_content") and msg.html_content.get():
            content = msg.html_content.get()

        subject = msg.subject.get() if hasattr(msg.subject, "get") else str(msg.subject)
        date = msg.time_received.get() if hasattr(msg.time_received, "get") else datetime.now()

        is_read = msg.is_read.get() if hasattr(msg.is_read, "get") else msg.was_read.get() if hasattr(msg.was_read, "get") else False

        cc_recipients = []
        if hasattr(msg, "cc_recipients"):
            cc_list = msg.cc_recipients.get()
            if cc_list:
                for recipient in cc_list:
                    cc_address = self._get_email_address(recipient)
                    cc_recipients.append(cc_address)

        if not content or content.strip() == "":
            content = "<p>No content available</p>"

        message_id = self._generate_message_id(msg)

        return EmailMessage(
            message_id=message_id,
            subject=subject,
            sender=sender,
            date=date,
            cc=cc_recipients,
            content=content,
            unread=not is_read,
            analysis=None,
        )

    def get_email_details(self, limit: int = 10) -> List[EmailMessage]:
        messages = self.inbox.messages.get()[:limit]
        email_list = [self._process_message(msg) for msg in messages]
        print(f"Retrieved {len(email_list)} emails.")
        return email_list


app = Flask(__name__)
email_cache = {"emails": [], "current_index": 0}
api_lock = threading.Lock()


@app.route("/")
def index():
    outlook = OutlookMailbox()
    counts = outlook.get_inbox_count()
    email_cache["emails"] = outlook.get_email_details(limit=counts["total"])
    email_cache["current_index"] = 0
    return render_template("index.html", total=counts["total"], unread=counts["unread"])


@app.route("/stats/")
def stats():
    return render_template("stats.html")


@app.route("/email")
def show_email():
    if not email_cache["emails"]:
        print("Email cache is empty.")
        return redirect(url_for("index"))

    print(f"Current index: {email_cache['current_index']}")
    current_email = email_cache["emails"][email_cache["current_index"]]
    email_date_iso = current_email.date.isoformat()

    total_emails = len(email_cache["emails"])
    return render_template(
        "email.html",
        email=current_email,
        index=email_cache["current_index"] + 1,
        total=total_emails,
        email_date_iso=email_date_iso,
        user_background=USER_BACKGROUND,
    )


@app.route("/next")
def next_email():
    if email_cache["current_index"] < len(email_cache["emails"]) - 1:
        email_cache["current_index"] += 1
    return redirect(url_for("show_email"))


@app.route("/prev")
def prev_email():
    if email_cache["current_index"] > 0:
        email_cache["current_index"] -= 1
    return redirect(url_for("show_email"))


@app.route("/open_in_outlook")
def open_in_outlook():
    if not email_cache["emails"]:
        return {"success": False, "error": "No email selected"}

    try:
        current_email = email_cache["emails"][email_cache["current_index"]]
        outlook = appscript_app("Microsoft Outlook")

        messages = outlook.inbox.messages.get()
        for msg in messages:
            if msg.subject.get() == current_email.subject and msg.time_received.get() == current_email.date:
                msg.open()
                outlook.activate()
                return {"success": True}

        return {"success": False, "error": "Email not found in Outlook"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.route("/email_analysis/<message_id>")
def email_analysis(message_id):
    email = next((email for email in email_cache["emails"] if email.message_id == message_id), None)
    if email is None:
        return jsonify({"success": False, "error": "Email not found"}), 404

    if email.analysis is not None:
        analysis = email.analysis
    else:
        priority_analysis = analyze_priority(USER_BACKGROUND, email.content, email.message_id)
        recommended_actions = analyze_actions(USER_BACKGROUND, email.content, email.message_id)
        sender_intention = analyze_intention(USER_BACKGROUND, email.content, email.message_id)

        analysis = EmailAnalysis(
            is_compulsory=priority_analysis["compulsory"],
            opportunity_score=priority_analysis["opportunity_score"],
            harm_score=priority_analysis["harm_score"],
            recommended_actions=recommended_actions,
            sender_intention=sender_intention,
            compulsory_cost=field.get(email.message_id, "compulsory_cost") or 0.0,
            opportunity_cost=field.get(email.message_id, "opportunity_cost") or 0.0,
            harm_cost=field.get(email.message_id, "harm_cost") or 0.0,
            actions_cost=field.get(email.message_id, "actions_cost") or 0.0,
            intention_cost=field.get(email.message_id, "intention_cost") or 0.0,
            model_name=field.get(email.message_id, "model_name") or "Unknown",
        )
        email.analysis = analysis

    analysis_data = {
        "is_compulsory": analysis.is_compulsory,
        "opportunity_score": analysis.opportunity_score,
        "harm_score": analysis.harm_score,
        "recommended_actions": analysis.recommended_actions,
        "sender_intention": analysis.sender_intention,
        "costs": {
            "model_name": analysis.model_name,
            "compulsory": analysis.compulsory_cost,
            "opportunity": analysis.opportunity_cost,
            "harm": analysis.harm_cost,
            "actions": analysis.actions_cost,
            "intention": analysis.intention_cost,
            "total": (
                analysis.compulsory_cost +
                analysis.opportunity_cost +
                analysis.harm_cost +
                analysis.actions_cost +
                analysis.intention_cost
            ),
        },
    }

    return jsonify({"success": True, "analysis": analysis_data})


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5001)
