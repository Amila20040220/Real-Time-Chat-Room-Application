# Real-Time Chat Application

This is a complete, real-time chat application featuring a Python WebSocket server, a modern web-based client, and a command-line client. The server is built using the `websockets` library, and the frontend uses HTML, Tailwind CSS, and vanilla JavaScript for a responsive and animated user experience.

## Features

-   **Real-time Messaging:** Instant message delivery using WebSockets.
-   **Multiple Chat Rooms:** Users can subscribe to and publish in multiple rooms.
-   **Persistent History:** Chat history is logged to the filesystem (`logs/` directory) and the last 50 messages are sent to new subscribers.
-   **User Presence:** See who is in a room, with real-time join/leave notifications.
-   **Modern Web UI:** A responsive, single-page application built with Tailwind CSS, featuring animations and a mobile-friendly layout.
-   **Command-Line Client:** A fully functional terminal-based client (`client.py`) for alternative access or testing.
-   **No External Database:** The application is self-contained and uses file-based logging for persistence.
-   **Simple Protocol:** A straightforward JSON-based protocol for client-server communication.

## Project Components

-   `server.py`: The core WebSocket server built with Python and the `websockets` library. It manages users, rooms, message broadcasting, and history logging.
-   `index.html`: The single-page web client. It handles user login, room subscriptions, and message display in a responsive interface.
-   `client.py`: A command-line client for interacting with the chat server from the terminal.
-   `common.py`: Shared constants and JSON helper functions used by both the server and the terminal client.
-   [cite_start]`requirements.txt`: A list of the required Python dependencies[cite: 1].

## Setup and Installation

### Prerequisites

-   [cite_start]Python 3.10 or newer[cite: 1].

### Installation Steps

1.  **Clone the repository or download the files:**
    ```bash
    git clone [https://github.com/your-username/real-time-chat.git](https://github.com/your-username/real-time-chat.git)
    cd real-time-chat
    ```

2.  **Create and activate a virtual environment (recommended):**
    ```bash
    # For macOS/Linux
    python3 -m venv venv
    source venv/bin/activate

    # For Windows
    python -m venv venv
    .\venv\Scripts\activate
    ```

3.  **Install the required Python packages:**
    ```bash
    pip install -r requirements.txt
    ```

## How to Run

1.  **Start the Server:**
    Open a terminal and run the server script.
    ```bash
    python server.py
    ```
    By default, the server will start on `ws://0.0.0.0:2024`.

2.  **Use the Web Client:**
    Open the `index.html` file directly in a modern web browser (like Chrome, Firefox, or Edge). No web server is needed.

3.  **Use the Terminal Client (Optional):**
    Open a *new* terminal window (while the server is running) and run the client script.
    ```bash
    python client.py
    ```
    Follow the on-screen commands (e.g., `/login alice`) to interact with the chat.

### Configuration

You can change the default port by setting the `CHAT_PORT` environment variable before running the server or client.

```bash
# Example: Run server on port 8000
CHAT_PORT=8000 python server.py

# Example: Connect client to port 8000
CHAT_PORT=8000 python client.py
