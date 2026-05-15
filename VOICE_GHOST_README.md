# 👻 Voice Ghost Feature - "User was here"

## 📋 Overview
The Voice Ghost feature displays a "User was here" message when someone leaves a voice channel, similar to Discord's native activity indicators. This helps server members know who was recently active in voice channels.

## ✨ Features

### 🎯 Core Functionality
- **Automatic Detection**: Monitors voice channel join/leave events
- **Smart Messaging**: Shows ghost messages in linked text channels
- **Auto Cleanup**: Messages disappear when user returns or after 30 minutes
- **Customizable Format**: Admins can customize the ghost message format
- **Channel Linking**: Automatically finds appropriate text channels for each voice channel

### 🔧 Admin Controls
- **Enable/Disable**: Toggle the feature on/off per server
- **Duration Control**: Set how long ghost messages stay visible (5-120 minutes)
- **Message Customization**: Customize the ghost message format
- **Testing Tools**: Test the system without actually leaving voice

## 🚀 How It Works

### 1. Voice Channel Activity
```
User joins Voice Channel → No action (ghost removed if exists)
User leaves Voice Channel → Ghost message appears in linked text channel
User rejoins same channel → Ghost message disappears immediately
```

### 2. Channel Linking Priority
The bot finds text channels in this order:
1. **Same Name**: Text channel with same name as voice channel
2. **Same Category**: Any text channel in the same category
3. **General Channels**: Channels named "general", "chat", "main", etc.
4. **First Available**: Any text channel the bot can send messages to

### 3. Message Format
Default: `{username} was here`

Available variables:
- `{username}` - User's display name
- `{user}` - User mention (@user)
- `{channel}` - Voice channel name

## 📝 Commands

### Admin Commands (Requires Administrator permission)

#### Basic Management
```
!voiceghost status          # Show current settings and active ghosts
!voiceghost toggle          # Enable/disable the feature
!voiceghost test            # Test the system (creates temporary ghost)
```

#### Customization
```
!voiceghost format <message>    # Customize ghost message format
!voiceghost duration <minutes>  # Set ghost duration (5-120 minutes)
```

#### Examples
```bash
# Customize the message
!voiceghost format "{username} was chilling here"
!voiceghost format "👻 {user} just left {channel}"

# Set duration to 15 minutes
!voiceghost duration 15

# Check current status
!voiceghost status
```

## 🎨 Visual Design

### Ghost Message Appearance
```
👻 Username was here
   [User Avatar] Username
   [Timestamp: Just now]
```

- **Color**: Light gray (#747F8D) to indicate inactive status
- **Icon**: Ghost emoji (👻) for visual recognition
- **Avatar**: User's profile picture
- **Timestamp**: When they left the channel

## ⚙️ Configuration

### Default Settings
- **Enabled**: Yes
- **Duration**: 30 minutes
- **Format**: `{username} was here`
- **Show in Channel**: Yes

### Database Tables
The feature uses two main tables:
- `voice_presence`: Stores active ghost messages
- `voice_presence_settings`: Stores per-server configuration

## 🔍 Use Cases

### Community Servers
- **Social Awareness**: See who was recently active
- **Conversation Starters**: Know who to ping for voice chat
- **Activity Tracking**: Monitor voice channel usage

### Gaming Servers
- **Team Formation**: See who was in game channels
- **Session Tracking**: Know when teammates were online
- **Coordination**: Better team communication

### Study/Work Servers
- **Study Buddies**: See who was in study rooms
- **Collaboration**: Track work session participants
- **Availability**: Know who might be available soon

## 🛠️ Technical Details

### Performance
- **Memory Efficient**: Only stores active ghosts in memory
- **Auto Cleanup**: Removes old data every 5 minutes
- **Database Optimized**: Efficient queries and indexing

### Error Handling
- **Graceful Failures**: Continues working if message deletion fails
- **Permission Checks**: Verifies bot permissions before sending
- **Fallback Channels**: Multiple strategies for finding text channels

### Privacy Considerations
- **Opt-out**: Server admins can disable the feature
- **Temporary**: Messages are automatically cleaned up
- **Non-intrusive**: Uses subtle styling and placement

## 🚨 Troubleshooting

### Common Issues

#### Ghost messages not appearing
1. Check if feature is enabled: `!voiceghost status`
2. Verify bot has send message permissions in text channels
3. Ensure there's a linked text channel for the voice channel

#### Messages not disappearing
1. Check if user actually rejoined the same voice channel
2. Wait for automatic cleanup (runs every 5 minutes)
3. Restart the bot if issues persist

#### Permission errors
1. Ensure bot has "Send Messages" permission in target channels
2. Check if bot has "Read Message History" for message deletion
3. Verify bot role hierarchy for accessing channels

### Debug Commands
```bash
!voiceghost status    # Shows active ghosts and settings
!voiceghost test      # Creates a test ghost message
```

## 📊 Statistics

The `!voiceghost status` command shows:
- Current enable/disable status
- Ghost message duration setting
- Custom message format
- Number of currently active ghost messages

## 🔄 Updates and Maintenance

### Automatic Cleanup
- Runs every 5 minutes
- Removes ghosts older than configured duration
- Cleans up database entries
- Handles failed message deletions

### Memory Management
- Stores only essential data in memory
- Removes empty channel entries
- Efficient data structures for fast lookups

## 🎯 Future Enhancements

### Planned Features
- **Voice Activity Heatmaps**: Visual representation of voice channel usage
- **Ghost Message Reactions**: Allow users to react to ghost messages
- **Advanced Filtering**: Filter ghosts by user roles or permissions
- **Integration**: Connect with other bot features for enhanced functionality

### Customization Options
- **Per-Channel Settings**: Different settings for different voice channels
- **Role-Based Visibility**: Show ghosts only to certain roles
- **Time-Based Rules**: Different behavior based on time of day

---

## 📞 Support

For issues or questions about the Voice Ghost feature:
1. Use `!voiceghost status` to check current settings
2. Try `!voiceghost test` to verify functionality
3. Check bot permissions in your server
4. Contact the bot developer if issues persist

**Note**: This feature mimics Discord's native "User was here" functionality but is implemented as a bot feature for servers that want more control and customization options.