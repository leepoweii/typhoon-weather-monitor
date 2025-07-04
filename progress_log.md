# Progress Log - Typhoon Weather Monitor

## 2025-07-04 - Fixed LINE Bot FlexMessage Errors

### Issues Fixed:
1. **FlexContainer Object Handling**: Fixed incorrect usage where FlexMessage objects were being treated as dictionaries in `line_bot.py`
2. **FlexMessage Construction**: Corrected the flow where FlexMessageBuilder returns FlexMessage objects directly, not dictionaries
3. **JSON Validation**: Added proper error handling and validation for FlexContainer creation from JSON
4. **Reply Token Expiration**: Improved error handling for expired reply tokens to prevent spam errors

### Files Modified:
- `/notifications/line_bot.py` - Fixed FlexContainer usage in push and reply methods
- `/notifications/flex_message_builder.py` - Added JSON validation and error handling
- `/CLAUDE.md` - Updated documentation with corrected LINE Bot integration notes

### Technical Details:
- **Before**: `flex_container_dict = self.flex_builder.create_typhoon_status_flex(result)` treated return value as dict
- **After**: `flex_message = self.flex_builder.create_typhoon_status_flex(result)` correctly handles FlexMessage object
- **Added**: JSON validation with try-catch blocks in all FlexContainer.from_json() calls
- **Added**: Specific handling for "Invalid reply token" errors to prevent error loops

### Error Resolution:
- Fixed "invalid property /type" errors by properly constructing FlexContainer objects
- Fixed "Invalid reply token" errors by adding graceful handling for expired tokens
- Added fallback to text messages when FlexMessage creation fails

### Status:
✅ All syntax checks passed
✅ FlexMessage construction errors resolved
✅ Error handling improved
✅ Documentation updated

## 2025-07-04 - Fixed LINE Bot URI Validation Errors

### Issues Fixed:
1. **Invalid URI Scheme**: Fixed "invalid uri scheme" errors in FlexMessage footer buttons
2. **Localhost URI Rejection**: LINE Bot rejects localhost URLs, added validation to use placeholder URLs
3. **Missing URI Scheme**: Added automatic https:// scheme for URIs missing protocols

### Files Modified:
- `/notifications/flex_message_builder.py` - Added URI validation function and fixed button URIs

### Technical Details:
- **Added**: `validate_uri()` function to handle URI validation for LINE Bot compatibility
- **Fixed**: Footer button URIs in `create_typhoon_status_flex()` and `create_test_notification_flex()`
- **Replaced**: `self.base_url` with `validate_uri(self.base_url)` in all button actions
- **Fallback**: Uses `https://example.com` for localhost or invalid URIs

### Error Resolution:
- Fixed "(400) Bad Request" errors caused by invalid URI schemes
- Resolved "invalid uri" and "invalid uri scheme" validation errors
- Ensured LINE Bot compatibility with proper URI formatting

### Status:
✅ URI validation function implemented and tested
✅ All FlexMessage URI errors resolved
✅ LINE Bot compatibility improved