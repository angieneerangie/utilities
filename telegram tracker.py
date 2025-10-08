import asyncio
from telethon import TelegramClient
from telethon.tl.types import User
from datetime import datetime, timedelta, timezone
import json

# Your API credentials from https://my.telegram.org
API_ID = 'API_ID_HERE'  
API_HASH = 'API_HASH_HERE'
PHONE_NUMBER = 'YOUR_PHONE_NUMBER_HERE'  # Your phone number with country code

# Target user info (with their consent)
TARGET_PHONE = 'TARGET_PHONE'  # Person's phone number with country code
# OR
TARGET_USER_ID = TARGET_USER_ID  # Person's Telegram user ID

SESSION_NAME = 'tracking_session'

class TelegramStatusTracker:
    def __init__(self, api_id, api_hash, phone_number):
        self.client = TelegramClient(SESSION_NAME, api_id, api_hash)
        self.phone_number = phone_number
        self.status_data = []
        
    async def setup_client(self):
        """Initialize and authenticate the client"""
        await self.client.start(phone=self.phone_number)
        print("Client created and authenticated successfully!")
        
    async def get_user_status_by_phone(self, phone_number):
        """Get user status using phone number"""
        try:
            user = await self.client.get_entity(phone_number)
            return await self._extract_status_info(user)
        except Exception as e:
            print(f"Error getting user by phone: {e}")
            return None
            
    async def get_user_status_by_id(self, user_id):
        """Get user status using Telegram ID"""
        try:
            user = await self.client.get_entity(user_id)
            return await self._extract_status_info(user)
        except Exception as e:
            print(f"Error getting user by ID: {e}")
            return None
    
    async def _extract_status_info(self, user):
        """Extract status information from user object"""
        if isinstance(user, User):
            status = user.status
            current_time = datetime.now(timezone.utc)
            
            status_info = {
                'timestamp': current_time.isoformat(),
                'user_id': user.id,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'username': user.username
            }
            
            if status is None:
                status_info.update({
                    'online': False,
                    'status': 'Long time ago',
                    'last_seen': 'Unknown'
                })
            elif hasattr(status, 'was_online'):
                # User was online at specific time
                last_seen = status.was_online
                status_info.update({
                    'online': False,
                    'status': 'Last seen',
                    'last_seen': last_seen.isoformat(),
                    'last_seen_ago': str(current_time - last_seen)
                })
            elif hasattr(status, 'expires'):
                # User is currently online
                online_since = datetime.fromtimestamp(
                    datetime.now(timezone.utc).timestamp() - status.expires.timestamp(),
                    tz=timezone.utc
                )
                status_info.update({
                    'online': True,
                    'status': 'Online',
                    'online_since': online_since.isoformat(),
                    'online_for': str(datetime.now(timezone.utc) - online_since)
                })
            elif type(status).__name__ == 'UserStatusRecently':
                status_info.update({
                    'online': False,
                    'status': 'Last seen recently',
                    'last_seen': 'Within a day'
                })
            elif type(status).__name__ == 'UserStatusLastWeek':
                status_info.update({
                    'online': False,
                    'status': 'Last seen within a week',
                    'last_seen': 'Within a week'
                })
            elif type(status).__name__ == 'UserStatusLastMonth':
                status_info.update({
                    'online': False,
                    'status': 'Last seen within a month',
                    'last_seen': 'Within a month'
                })
            else:
                status_info.update({
                    'online': False,
                    'status': f'Unknown: {type(status).__name__}',
                    'last_seen': 'Unknown'
                })
            
            return status_info
        return None
    
    async def track_48_hours(self, identifier, use_phone=True):
        """Track user status for 48 hours"""
        print(f"Starting 48-hour tracking for: {identifier}")
        print("Press Ctrl+C to stop tracking early")
        
        start_time = datetime.now()
        end_time = start_time + timedelta(hours=48)
        
        try:
            while datetime.now() < end_time:
                # Get current status
                if use_phone:
                    status_info = await self.get_user_status_by_phone(identifier)
                else:
                    status_info = await self.get_user_status_by_id(identifier)
                
                if status_info:
                    self.status_data.append(status_info)
                    
                    # Print current status
                    print(f"\n[{status_info['timestamp']}]")
                    print(f"User: {status_info.get('first_name', 'Unknown')} "
                          f"{status_info.get('last_name', '')}")
                    if status_info['online']:
                        print(f"Status: {status_info['status']}")
                        print(f"Online for: {status_info.get('online_for', 'Unknown')}")
                    else:
                        print(f"Status: {status_info['status']}")
                        print(f"Last seen: {status_info.get('last_seen', 'Unknown')}")
                        if 'last_seen_ago' in status_info:
                            print(f"Last seen ago: {status_info['last_seen_ago']}")
                    
                    # Save to file
                    self.save_data()
                
                # Wait 5 minutes before next check
                await asyncio.sleep(300)  # 300 seconds = 5 minutes
                
        except KeyboardInterrupt:
            print("\nTracking stopped by user")
        except Exception as e:
            print(f"Tracking error: {e}")
        
        print(f"\nTracking completed. Collected {len(self.status_data)} data points")
        self.generate_report()
    
    def save_data(self):
        """Save data to JSON file"""
        with open('telegram_status_data.json', 'w') as f:
            json.dump(self.status_data, f, indent=2)
    
    def generate_report(self):
        """Generate a summary report"""
        if not self.status_data:
            print("No data collected")
            return
            
        online_sessions = []
        current_online_start = None
        
        for entry in self.status_data:
            if entry['online'] and current_online_start is None:
                current_online_start = datetime.fromisoformat(entry['timestamp'])
            elif not entry['online'] and current_online_start is not None:
                online_end = datetime.fromisoformat(entry['timestamp'])
                session_duration = online_end - current_online_start
                online_sessions.append({
                    'start': current_online_start,
                    'end': online_end,
                    'duration': session_duration
                })
                current_online_start = None
        
        # Handle case where user was still online at end of tracking
        if current_online_start is not None:
            online_end = datetime.fromisoformat(self.status_data[-1]['timestamp'])
            session_duration = online_end - current_online_start
            online_sessions.append({
                'start': current_online_start,
                'end': online_end,
                'duration': session_duration
            })
        
        print("\n" + "="*50)
        print("48-HOUR TRACKING REPORT")
        print("="*50)
        print(f"Total data points: {len(self.status_data)}")
        print(f"Online sessions detected: {len(online_sessions)}")
        
        total_online_time = timedelta()
        for i, session in enumerate(online_sessions, 1):
            print(f"\nSession {i}:")
            print(f"  Start: {session['start']}")
            print(f"  End: {session['end']}")
            print(f"  Duration: {session['duration']}")
            total_online_time += session['duration']
        
        print(f"\nTotal online time: {total_online_time}")
        print(f"Percentage of time online: {(total_online_time.total_seconds() / (48 * 3600)) * 100:.2f}%")
        
        # Save report
        report = {
            'tracking_period': '48_hours',
            'total_data_points': len(self.status_data),
            'online_sessions_count': len(online_sessions),
            'total_online_time_seconds': total_online_time.total_seconds(),
            'online_sessions': [
                {
                    'start': s['start'].isoformat(),
                    'end': s['end'].isoformat(),
                    'duration_seconds': s['duration'].total_seconds()
                } for s in online_sessions
            ]
        }
        
        with open('telegram_status_report.json', 'w') as f:
            json.dump(report, f, indent=2)
        
        print("\nDetailed data saved to: telegram_status_data.json")
        print("Report saved to: telegram_status_report.json")

async def main():
    # Initialize tracker
    tracker = TelegramStatusTracker(API_ID, API_HASH, PHONE_NUMBER)
    
    # Setup client
    await tracker.setup_client()
    
    # Choose tracking method
    print("Choose tracking method:")
    print("1. Phone number")
    print("2. Telegram User ID")
    
    choice = input("Enter choice (1 or 2): ").strip()
    
    if choice == "1":
        phone = input("Enter phone number (with country code): ").strip()
        await tracker.track_48_hours(phone, use_phone=True)
    elif choice == "2":
        try:
            user_id = int(input("Enter Telegram User ID: ").strip())
            await tracker.track_48_hours(user_id, use_phone=False)
        except ValueError:
            print("Invalid User ID. Must be a number.")
    else:
        print("Invalid choice")

if __name__ == "__main__":
    # Create and run the event loop
    asyncio.run(main())
