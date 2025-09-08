# uLauncher Port Killer Extension

A uLauncher extension that allows you to quickly terminate ports and processes directly from the uLauncher interface.


## Features

- 🔍 **Port Discovery**: Scan and list all active network ports on your system
- 🎯 **Process Information**: Display port number, protocol (TCP/UDP), process name, and PID
- ⚡ **Quick Termination**: Kill processes directly from uLauncher
- 🔧 **Configurable**: Customize keyword, kill method, and system port visibility
- 🚀 **Performance Optimized**: Smart caching and debouncing for smooth experience

## Installation

# Manually from source
The extensions' directory is located at: $HOME/.local/share/ulauncher/extensions
Go to that location, and while being inside, just git clone this repository.

# Ulauncher's GUI
1. Open uLauncher and go to Extensions (or press `Ctrl+,`)

2. Click "Add extension" and paste this repository URL:
   ```
   https://github.com/cosmincraciun97/port-killer-ulauncher
   ```

3. The extension will be automatically downloaded and installed

4. Make sure `psutil` is installed (the extension requires it):
   ```bash
   pip install psutil
   ```
5. Configure the extension preferences if needed and start using it!

## Usage

1. Open uLauncher (default: `Ctrl+Space`)
2. Type the keyword `port` (configurable)
3. Browse through active ports and their associated processes
4. Press Enter on a port to immediately terminate the process
5. See success/failure feedback

### Search Examples

- `port` - Show all active ports
- `port 80` - Show only port 80
- `port nginx` - Show ports used by nginx processes
- `port tcp` - Show only TCP ports

## Configuration

Access extension preferences through uLauncher settings:

### Keyword
- **Default**: `port`
- **Description**: The keyword to trigger the port killer
- **Example**: Change to `kill` or `pk` for shorter commands

### Show System Ports
- **Default**: No
- **Options**: Yes / No
- **Description**: Include system/privileged ports (< 1024) in results

### Kill Method
- **Default**: Graceful (SIGTERM)
- **Options**: 
  - Graceful (SIGTERM) - Allows processes to clean up before terminating
  - Force (SIGKILL) - Immediately terminates processes
- **Description**: Method used to terminate processes

## Technical Details

### Dependencies
- **psutil**: Cross-platform library for system and process monitoring
- **Python 3.6+**: Required for uLauncher extensions

### Port Detection
The extension uses multiple methods for port detection:
1. **Primary**: `psutil.net_connections()` for cross-platform compatibility
2. **Fallback**: System commands (`netstat -tulpn`) if psutil fails

### Performance Features
- **Caching**: Port information is cached for 2 seconds to improve responsiveness
- **Debouncing**: 0.5-second query debounce prevents excessive system calls
- **Result Limiting**: Maximum 15 results to maintain UI performance

### Security & Safety
- **Permission Handling**: Gracefully handles cases where processes cannot be terminated
- **Process Validation**: Checks if processes exist before attempting termination
- **Error Feedback**: Clear error messages for failed operations

## Troubleshooting

### Extension Not Loading
1. Check that `psutil` is installed: `python -c "import psutil"`
2. Verify file permissions in the extension directory
3. Check uLauncher logs for error messages

### Permission Errors
- Some system processes require elevated privileges to terminate
- The extension will show clear error messages for permission issues
- Consider running processes you want to kill with user permissions

### No Ports Showing
1. Verify that processes are actually listening on ports: `netstat -tulpn`
2. Check if "Show System Ports" setting matches your needs
3. Try different search terms to ensure filtering isn't hiding results

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes and test thoroughly
4. Submit a pull request with a clear description

## License

MIT LICENSE

## Support

If you encounter issues or have feature requests, please:
1. Check the troubleshooting section above
2. Review uLauncher logs for error details
3. Open an issue with detailed information about your problem

---

**⚠️ Warning**: This extension can terminate system processes. Use with caution and ensure you understand what processes you're killing to avoid system instability.
