<div align="center">
<br/>
<h1>Data Manager</h1>
<h3>A Complete Data Organization Solution</h3>
<br/>
<img src="https://img.shields.io/badge/Python-14354C?style=for-the-badge&logo=python&logoColor=white" alt="built with Python3" />
<img src="https://img.shields.io/badge/sqlite-%2307405e.svg?style=for-the-badge&logo=sqlite&logoColor=white" alt="built with SQLite" />
<img src="https://img.shields.io/badge/html5-%23E34F26.svg?style=for-the-badge&logo=html5&logoColor=white" alt="built with HTML" />
<img src="https://img.shields.io/badge/css3-%231572B6.svg?style=for-the-badge&logo=css3&logoColor=white" alt="built with CSS" />
<img src="https://img.shields.io/badge/shell_script-%23121011.svg?style=for-the-badge&logo=gnu-bash&logoColor=white" alt="built with Shell Script" />

</div>

## 🚀 Unleash Your Data's Potential

Data Manager is a powerful, intuitive platform designed to simplify how you organize, search, and interact with your data. Say goodbye to chaotic file systems and hello to streamlined data management!

### ✨ Key Features

- **Smart Search** - Find exactly what you need with an intelligent natural language search assistant
- **Secure Access** - Robust authentication system keeps your data protected
- **Intuitive Interface** - Navigate your data with ease through a clean, user-friendly design
- **Cross-Platform** - Works seamlessly across different operating systems
- **Customizable** - Tailor the experience to fit your specific workflow needs

## 🔧 Installation

### Source code
Clone the repository, then run `pip3 install -r requirements.txt` inside the repository folder.

### PyPI
\<to be added\>

### Linux dependencies
This app is designed for Linux distributions. Install the dependencies using:
```console
Amin@Maximus:./Data-Manager$ python3 src/main.py -hu localhost:8080
```

## 🚀 Usage
Check out the [documentation](https://github.com/AminAlam/Data-Manager/wiki) for detailed guides.

Launch the program with:
```console
Amin@Maximus:./Data-Manager$ python3 src/main.py --server_ip localhost --port 8080
```
Access the app at http://localhost:8080. You can also run it on a different port (ensure the port is open in your firewall settings).
The default username and password are *admin* and *admin* (You can change this password in the <em>profile</em> tab).

## 📚 Documentation

For comprehensive documentation, visit the [wiki](https://github.com/AminAlam/Data-Manager/wiki).

## 🌐 Browser Add-on for Google Drive Integration

Data Manager now includes a browser add-on that allows you to easily add Google Drive documents (Docs, Sheets, Slides) directly to your Data Manager without visiting the website.

### Features
- One-click addition of Google Drive documents to Data Manager
- Automatic extraction of document title and URL
- Seamless integration with your existing Data Manager account
- Secure API key-based authentication

### Installation
1. Log in to your Data Manager
2. Go to your profile page
3. Click "Configure Browser Add-on"
4. Generate an API key
5. Download and install the browser extension
6. Configure the extension with your server URL, username, and API key

### Usage
1. Navigate to any Google Doc, Sheet, or Slide
2. Click the Data Manager extension icon in your browser toolbar
3. Add tags and notes as needed
4. Click "Add to Data Manager"

### API Key Management
Data Manager uses a secure API key system that doesn't interfere with your regular password. API keys are stored separately in the database and can be regenerated at any time without affecting your normal login credentials.

For more details, see the [Browser Add-on Documentation](browser-extension/README.md).

## Environment Variables

The application uses environment variables for configuration. To set up your environment:

1. Copy the `.env.example` file to `.env`:
   ```bash
   cp .env.example .env
   ```

2. Edit the `.env` file and fill in your configuration values:
   ```
   # Data Manager Environment Variables
   
   # Flask Secret Key
   SECRET_KEY=your_secret_key_here
   
   # reCAPTCHA Keys
   RECAPTCHA_PUBLIC_KEY=your_recaptcha_public_key
   RECAPTCHA_PRIVATE_KEY=your_recaptcha_private_key
   
   # Email Configuration
   SENDER_EMAIL_ADDRESS=your_email@example.com
   SENDER_EMAIL_PASSWORD=your_email_password
   
   # Claude API Key
   CLAUDE_API_KEY=your_claude_api_key
   ```

3. Make sure to install the required packages:
   ```bash
   pip install -r requirements.txt
   ```

4. The application will automatically load these environment variables at startup.

**Note:** Never commit your `.env` file to version control. It's already added to `.gitignore`.
