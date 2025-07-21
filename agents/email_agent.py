import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import streamlit as st
from typing import Dict

class EmailCommunicationAgent:
    def __init__(self):
        self.current_time = datetime(2025, 7, 21, 14, 42, 57)
        self.current_user = "A4xMimic"
    
    async def process_email_request(self, user_input: str, session_state) -> Dict:
        """Process email communication requests"""
        
        # Extract recipient and message type
        analysis = self._analyze_email_request(user_input)
        
        if analysis["type"] == "birthday_wishes":
            return await self._send_birthday_wishes(analysis, session_state)
        elif analysis["type"] == "urgent_meeting":
            return await self._send_urgent_meeting_email(analysis, session_state)
        elif analysis["type"] == "team_notification":
            return await self._send_team_notification(analysis, session_state)
        elif analysis["type"] == "general_email":
            return await self._send_general_email(analysis, session_state)
        else:
            return {
                "type": "error",
                "content": "Could not understand the email request. Please specify the recipient and message type."
            }
    
    def _analyze_email_request(self, user_input: str) -> Dict:
        """Analyze the email request to extract details"""
        user_lower = user_input.lower()
        
        # Extract recipient information
        recipients = []
        recipient_emails = []
        
        # Check for specific team members
        if "mayank" in user_lower:
            recipients.append("Mayank")
            recipient_emails.append("mayank2712005@gmail.com")
        
        # Check for team-wide emails
        if any(phrase in user_lower for phrase in ["all team", "team members", "entire team", "whole team"]):
            recipients = ["All Team Members"]
            # Get team emails from session state or use default
            recipient_emails = [
                "mayank2712005@gmail.com",
                "team1@company.com",
                "team2@company.com", 
                "team3@company.com",
                "team4@company.com",
                "team5@company.com"
            ]
        
        # Determine email type based on content
        email_type = "general_email"  # default
        
        if any(word in user_lower for word in ["birthday", "wishes", "bday", "celebration"]):
            email_type = "birthday_wishes"
        elif any(phrase in user_lower for phrase in ["urgent meeting", "urgent", "meeting", "immediate"]):
            email_type = "urgent_meeting"
        elif any(phrase in user_lower for phrase in ["notification", "inform", "announce", "update"]):
            email_type = "team_notification"
        
        return {
            "type": email_type,
            "recipients": recipients,
            "recipient_emails": recipient_emails,
            "original_request": user_input
        }
    
    async def _send_urgent_meeting_email(self, analysis: Dict, session_state) -> Dict:
        """Send urgent meeting notification email"""
        try:
            recipients = analysis["recipients"]
            recipient_emails = analysis["recipient_emails"]
            
            if not recipient_emails:
                return {
                    "type": "error", 
                    "content": "❌ No team email addresses found. Please configure team emails in sidebar."
                }
            
            # Check email configuration
            if not session_state.get('email_configured'):
                return {
                    "type": "text",
                    "content": f"""📧 **Urgent Meeting Email Ready to Send!**

**🚨 Urgent Meeting Notification:**
- **To:** {', '.join(recipients)}
- **Recipients:** {len(recipient_emails)} team members
- **From:** {self.current_user}
- **Time:** {self.current_time.strftime('%Y-%m-%d %H:%M:%S')} UTC

**📝 Email Content Preview:**
---
Subject: 🚨 URGENT: Team Meeting Required - Immediate Response Needed

Dear Team,

I hope this email finds you well. Due to urgent matters that require immediate attention, we need to schedule an emergency team meeting.

**Meeting Details:**
- 📅 Date: As soon as possible (today if available)
- 🕐 Time: To be confirmed based on team availability
- 📍 Location: To be announced
- 🎯 Priority: HIGH - Immediate response required

**What's Needed:**
1. Please reply with your immediate availability for today
2. Check your calendar for the next 2-3 hours
3. Come prepared for an important discussion

**Next Steps:**
- I will send calendar invites once we confirm the time
- Please acknowledge receipt of this email
- Contact me directly if you have any urgent conflicts

Thank you for your immediate attention to this matter.

Best regards,
{self.current_user}

Sent via ProActive Work-Life Assistant
---

⚠️ **Email not configured yet.** Configure SMTP settings in sidebar to send real emails.

**Alternative:** You can also schedule the meeting through calendar:
Try: "Schedule urgent team meeting for today"
                    """
                }
            
            # If email is configured, send actual email
            subject = "🚨 URGENT: Team Meeting Required - Immediate Response Needed"
            
            html_content = f"""
            <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
                <div style="background: linear-gradient(135deg, #ff6b6b 0%, #ee5a24 100%); color: white; padding: 2rem; border-radius: 15px; text-align: center; margin-bottom: 2rem;">
                    <h1 style="margin: 0;">🚨 URGENT MEETING</h1>
                    <h2 style="margin: 0.5rem 0 0 0;">Immediate Response Required</h2>
                </div>
                
                <div style="background: #fff3cd; border-left: 5px solid #ffc107; padding: 1.5rem; margin: 1.5rem 0;">
                    <h3 style="margin-top: 0; color: #856404;">⚡ High Priority Notification</h3>
                    <p style="margin-bottom: 0; font-weight: bold;">This meeting requires your immediate attention and response.</p>
                </div>
                
                <div style="background: #f8f9fa; padding: 2rem; border-radius: 12px; margin: 2rem 0;">
                    <h3>Dear Team,</h3>
                    <p>I hope this email finds you well. Due to urgent matters that require immediate attention, we need to schedule an emergency team meeting.</p>
                    
                    <h3>📋 Meeting Details:</h3>
                    <ul style="background: white; padding: 1rem; border-radius: 8px; border: 1px solid #dee2e6;">
                        <li><strong>📅 Date:</strong> As soon as possible (today if available)</li>
                        <li><strong>🕐 Time:</strong> To be confirmed based on team availability</li>
                        <li><strong>📍 Location:</strong> To be announced</li>
                        <li><strong>🎯 Priority:</strong> HIGH - Immediate response required</li>
                    </ul>
                    
                    <h3>✅ What's Needed From You:</h3>
                    <ol style="background: white; padding: 1rem; border-radius: 8px; border: 1px solid #dee2e6;">
                        <li>Please reply with your immediate availability for today</li>
                        <li>Check your calendar for the next 2-3 hours</li>
                        <li>Come prepared for an important discussion</li>
                    </ol>
                    
                    <h3>🚀 Next Steps:</h3>
                    <ul style="background: white; padding: 1rem; border-radius: 8px; border: 1px solid #dee2e6;">
                        <li>I will send calendar invites once we confirm the time</li>
                        <li>Please acknowledge receipt of this email</li>
                        <li>Contact me directly if you have any urgent conflicts</li>
                    </ul>
                </div>
                
                <div style="background: #d1ecf1; border: 1px solid #bee5eb; border-radius: 10px; padding: 1rem; margin: 2rem 0; text-align: center;">
                    <p style="margin: 0; font-weight: bold; color: #0c5460;">
                        Thank you for your immediate attention to this matter.
                    </p>
                </div>
                
                <div style="text-align: center; margin-top: 2rem;">
                    <p>Best regards,<br>
                    <strong>{self.current_user}</strong><br>
                    <em>Sent via ProActive Work-Life Assistant</em></p>
                    
                    <p style="font-size: 0.9rem; color: #666; margin-top: 1rem;">
                        Sent on: {self.current_time.strftime('%Y-%m-%d %H:%M:%S')} UTC
                    </p>
                </div>
            </body>
            </html>
            """
            
            # Send email to all recipients
            smtp_server = session_state.get('smtp_server')
            smtp_port = session_state.get('smtp_port')
            sender_email = session_state.get('email_address')
            sender_password = session_state.get('email_password')
            
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()
            server.login(sender_email, sender_password)
            
            sent_count = 0
            for recipient_email in recipient_emails:
                try:
                    msg = MIMEMultipart('alternative')
                    msg['From'] = sender_email
                    msg['To'] = recipient_email
                    msg['Subject'] = subject
                    
                    html_part = MIMEText(html_content, 'html')
                    msg.attach(html_part)
                    
                    server.send_message(msg)
                    sent_count += 1
                except Exception as email_error:
                    print(f"Failed to send to {recipient_email}: {email_error}")
            
            server.quit()
            
            return {
                "type": "text",
                "content": f"""
### ✅ Urgent Meeting Email Sent Successfully! 🚨

**📧 Email Delivery Summary:**
- **👥 Recipients:** {', '.join(recipients)}
- **📬 Subject:** {subject}
- **📤 Sent to:** {sent_count}/{len(recipient_emails)} team members
- **🕐 Sent at:** {self.current_time.strftime('%Y-%m-%d %H:%M:%S')} UTC
- **👤 From:** {self.current_user}

**🎯 Mission Status:** URGENT notification delivered!

**📋 Next Steps:**
1. Monitor email responses for availability
2. Schedule meeting once team confirms
3. Send calendar invites with meeting details
4. Follow up with any non-responders

**💡 Pro Tip:** Use "Schedule urgent team meeting for today" to create calendar event once time is confirmed.

🚨 **Urgent meeting notification sent to entire team!**
                """
            }
            
        except Exception as e:
            return {
                "type": "error",
                "content": f"❌ Failed to send urgent meeting email: {str(e)}"
            }
    
    async def _send_team_notification(self, analysis: Dict, session_state) -> Dict:
        """Send general team notification"""
        return {
            "type": "text",
            "content": f"""📧 **Team Notification Email Ready!**

**Request:** "{analysis['original_request']}"
**Recipients:** {', '.join(analysis['recipients'])}

📝 **Team notification features:**
- ✉️ General announcements
- 📢 Project updates  
- 🎉 Celebration notices
- 📋 Policy updates

**Current Time:** {self.current_time.strftime('%Y-%m-%d %H:%M:%S')} UTC

💡 **Configure SMTP settings in sidebar to send real emails!**
            """
        }
    
    async def _send_general_email(self, analysis: Dict, session_state) -> Dict:
        """FIXED: Handle general email requests"""
        return {
            "type": "text",
            "content": f"""📧 **Email Request Detected!**

**Your request:** "{analysis['original_request']}"
**Recipients:** {', '.join(analysis.get('recipients', ['Unknown']))}

✉️ **Email features available:**
- 🎂 Birthday wishes ✅
- 🚨 Urgent meeting notifications ✅
- 📢 Team announcements ✅
- 📧 General communications ✅

**Current Time:** {self.current_time.strftime('%Y-%m-%d %H:%M:%S')} UTC

💡 **To send emails:** Configure SMTP settings in sidebar first!

**Try these specific requests:**
- "Mail birthday wishes to Mayank"
- "Send urgent meeting email to all team"
- "Notify team about project update"
            """
        }
    
    async def _send_birthday_wishes(self, analysis: Dict, session_state) -> Dict:
        """Send birthday wishes email"""
        try:
            recipient = analysis["recipients"][0] if analysis["recipients"] else "Team Member"
            recipient_email = analysis["recipient_emails"][0] if analysis["recipient_emails"] else None
            
            if not recipient_email:
                return {
                    "type": "error", 
                    "content": f"❌ Could not find email address for {recipient}. Please add team member emails in sidebar."
                }
            
            # Check email configuration
            if not session_state.get('email_configured'):
                return {
                    "type": "error",
                    "content": "❌ Email not configured. Please configure SMTP settings in sidebar."
                }
            
            # Prepare birthday email
            subject = f"🎂 Happy Birthday {recipient.title()}!"
            
            html_content = f"""
            <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
                <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 2rem; border-radius: 15px; text-align: center; margin-bottom: 2rem;">
                    <h1 style="margin: 0;">🎉 Happy Birthday!</h1>
                    <h2 style="margin: 0.5rem 0 0 0;">Dear {recipient.title()}</h2>
                </div>
                
                <div style="background: #f8f9fa; padding: 2rem; border-radius: 12px; margin: 2rem 0;">
                    <p style="font-size: 1.1rem; margin-bottom: 1.5rem;">
                        🎂 Wishing you a very happy birthday filled with joy, laughter, and wonderful memories!
                    </p>
                    
                    <p style="margin-bottom: 1.5rem;">
                        🎁 May this new year of life bring you success, happiness, and all the things you've been hoping for.
                    </p>
                    
                    <p style="margin-bottom: 1.5rem;">
                        🌟 Thank you for being such an amazing team member. Your contributions make our workplace better every day!
                    </p>
                    
                    <div style="text-align: center; margin: 2rem 0;">
                        <div style="background: #fff3cd; border: 2px solid #ffeaa7; border-radius: 10px; padding: 1rem; display: inline-block;">
                            <p style="margin: 0; font-size: 1.2rem; color: #856404;">
                                🎈 Enjoy your special day! 🎈
                            </p>
                        </div>
                    </div>
                </div>
                
                <div style="text-align: center; margin-top: 2rem;">
                    <p>Best wishes,<br>
                    <strong>{self.current_user}</strong><br>
                    <em>Sent via ProActive Work-Life Assistant</em></p>
                    
                    <p style="font-size: 0.9rem; color: #666; margin-top: 1rem;">
                        Sent on: {self.current_time.strftime('%Y-%m-%d %H:%M:%S')} UTC
                    </p>
                </div>
            </body>
            </html>
            """
            
            # Send email
            smtp_server = session_state.get('smtp_server')
            smtp_port = session_state.get('smtp_port')
            sender_email = session_state.get('email_address')
            sender_password = session_state.get('email_password')
            
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()
            server.login(sender_email, sender_password)
            
            msg = MIMEMultipart('alternative')
            msg['From'] = sender_email
            msg['To'] = recipient_email
            msg['Subject'] = subject
            
            html_part = MIMEText(html_content, 'html')
            msg.attach(html_part)
            
            server.send_message(msg)
            server.quit()
            
            return {
                "type": "text",
                "content": f"""
### ✅ Birthday Wishes Sent Successfully!

**🎂 Birthday Email Details:**
- **👤 Recipient:** {recipient.title()}
- **📧 Email:** {recipient_email}
- **📬 Subject:** {subject}
- **🕐 Sent at:** {self.current_time.strftime('%Y-%m-%d %H:%M:%S')} UTC
- **👤 From:** {self.current_user}

**🎉 Message Delivered!** 
{recipient.title()} will receive your heartfelt birthday wishes shortly.

💡 **Pro Tip:** Consider following up with a team celebration or cake! 🍰
                """
            }
            
        except Exception as e:
            return {
                "type": "error",
                "content": f"❌ Failed to send birthday email: {str(e)}"
            }