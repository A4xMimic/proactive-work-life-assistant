import asyncio
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import Dict, List, Any
import json
from datetime import datetime

from utils.logger import setup_logger

logger = setup_logger(__name__)

class CommunicationAgent:
    """Agent responsible for sending invitations and communications"""
    
    def __init__(self, config):
        self.config = config
        
    async def send_invitations(self, event_details: Dict, restaurant_details: Dict,
                             reservation_details: Dict, session_state: Dict) -> Dict:
        """Send calendar invitations and notification emails"""
        try:
            # Prepare invitation content
            invitation_content = self.create_invitation_content(
                event_details, restaurant_details, reservation_details
            )
            
            # Send emails to attendees
            email_results = await self.send_email_notifications(
                invitation_content, event_details.get("attendees", []), session_state
            )
            
            # Create summary message
            summary = self.create_communication_summary(email_results, event_details)
            
            return {
                "success": True,
                "message": "Invitations sent successfully",
                "email_results": email_results,
                "summary": summary
            }
            
        except Exception as e:
            logger.error(f"Error sending invitations: {str(e)}")
            return {
                "success": False,
                "message": f"Failed to send invitations: {str(e)}"
            }
    
    def create_invitation_content(self, event_details: Dict, restaurant_details: Dict,
                                reservation_details: Dict) -> Dict:
        """Create structured invitation content"""
        
        # Email subject
        subject = f"🍽️ Team Dinner Invitation - {restaurant_details['name']}"
        
        # Email body
        body = f"""
Dear Team,

You're invited to our team dinner!

📅 **Event Details:**
• Date: {event_details.get('start_time', '').split('T')[0]}
• Time: {event_details.get('start_time', '').split('T')[1][:5] if 'T' in event_details.get('start_time', '') else 'TBD'}
• Duration: 2 hours

🍽️ **Restaurant Information:**
• Name: {restaurant_details['name']}
• Address: {restaurant_details.get('address', 'Address will be shared')}
• Cuisine: {', '.join(restaurant_details.get('cuisine', ['Various']))}
• Rating: {restaurant_details.get('rating', 'N/A')} ⭐

📋 **Reservation Details:**
• Confirmation: {reservation_details.get('confirmation', 'Pending')}
• Method: {reservation_details.get('method', 'Manual')}
• Party Size: {event_details.get('party_size', 'TBD')} people

{self._get_reservation_instructions(reservation_details)}

Please confirm your attendance by responding to this email or updating the calendar event.

Looking forward to a great evening together!

Best regards,
Your Proactive Work-Life Assistant 🤖
        """
        
        return {
            "subject": subject,
            "body": body,
            "html_body": self.create_html_invitation(event_details, restaurant_details, reservation_details)
        }
    
    def _get_reservation_instructions(self, reservation_details: Dict) -> str:
        """Get reservation-specific instructions"""
        if reservation_details.get("method") == "manual":
            instructions = reservation_details.get("instructions", {})
            contact_info = instructions.get("contact_info", [])
            
            if contact_info:
                return f"""
📞 **Important:** This reservation requires manual confirmation.
Please contact the restaurant directly:

{chr(10).join(contact_info)}

Suggested script: "{instructions.get('script', 'Please make a reservation for our group.')}"
"""
        
        return ""
    
    def create_html_invitation(self, event_details: Dict, restaurant_details: Dict,
                             reservation_details: Dict) -> str:
        """Create HTML version of the invitation"""
        
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                   color: white; padding: 20px; text-align: center; }}
        .content {{ padding: 20px; }}
        .section {{ margin: 20px 0; padding: 15px; border-left: 4px solid #667eea; 
                   background: #f8f9fa; }}
        .restaurant-info {{ background: #e8f5e8; }}
        .reservation-info {{ background: #fff3cd; }}
        .footer {{ text-align: center; color: #666; margin-top: 30px; }}
        .emoji {{ font-size: 1.2em; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🍽️ Team Dinner Invitation</h1>
        <h2>{restaurant_details['name']}</h2>
    </div>
    
    <div class="content">
        <div class="section">
            <h3>📅 Event Details</h3>
            <p><strong>Date:</strong> {event_details.get('start_time', '').split('T')[0]}</p>
            <p><strong>Time:</strong> {event_details.get('start_time', '').split('T')[1][:5] if 'T' in event_details.get('start_time', '') else 'TBD'}</p>
            <p><strong>Duration:</strong> 2 hours</p>
        </div>
        
        <div class="section restaurant-info">
            <h3>🍽️ Restaurant Information</h3>
            <p><strong>Name:</strong> {restaurant_details['name']}</p>
            <p><strong>Address:</strong> {restaurant_details.get('address', 'Address will be shared')}</p>
            <p><strong>Cuisine:</strong> {', '.join(restaurant_details.get('cuisine', ['Various']))}</p>
            <p><strong>Rating:</strong> {restaurant_details.get('rating', 'N/A')} ⭐</p>
        </div>
        
        <div class="section reservation-info">
            <h3>📋 Reservation Details</h3>
            <p><strong>Confirmation:</strong> {reservation_details.get('confirmation', 'Pending')}</p>
            <p><strong>Method:</strong> {reservation_details.get('method', 'Manual')}</p>
            <p><strong>Party Size:</strong> {event_details.get('party_size', 'TBD')} people</p>
        </div>
        
        <div class="footer">
            <p>Please confirm your attendance by responding to this email.</p>
            <p><em>Sent by your Proactive Work-Life Assistant 🤖</em></p>
        </div>
    </div>
</body>
</html>
        """
        
        return html
    
    async def send_email_notifications(self, content: Dict, attendees: List[str],
                                     session_state: Dict) -> List[Dict]:
        """Send email notifications to attendees"""
        email_results = []
        
        # For demo purposes, we'll simulate email sending
        # In production, you'd integrate with actual email services
        
        for attendee in attendees:
            try:
                # Simulate email sending
                result = await self.simulate_email_send(attendee, content)
                email_results.append(result)
                
            except Exception as e:
                logger.error(f"Failed to send email to {attendee}: {str(e)}")
                email_results.append({
                    "recipient": attendee,
                    "success": False,
                    "error": str(e)
                })
        
        return email_results
    
    async def simulate_email_send(self, recipient: str, content: Dict) -> Dict:
        """Simulate email sending for demo purposes"""
        # Simulate network delay
        await asyncio.sleep(0.5)
        
        return {
            "recipient": recipient,
            "success": True,
            "subject": content["subject"],
            "sent_at": datetime.now().isoformat(),
            "message": "Email sent successfully (simulated)"
        }
    
    def create_communication_summary(self, email_results: List[Dict], 
                                   event_details: Dict) -> Dict:
        """Create a summary of communication results"""
        total_emails = len(email_results)
        successful_emails = sum(1 for result in email_results if result.get("success"))
        failed_emails = total_emails - successful_emails
        
        return {
            "total_invitations": total_emails,
            "successful_sends": successful_emails,
            "failed_sends": failed_emails,
            "success_rate": f"{(successful_emails/total_emails*100):.1f}%" if total_emails > 0 else "0%",
            "calendar_event_created": event_details.get("id") is not None
        }