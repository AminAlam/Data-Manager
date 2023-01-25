
class ChatRoom():
    def __init__(self, db_configs) -> None:
        self.db_configs = db_configs
        self.conn = db_configs.conn

    def add_message(self, message):
        cur = self.conn.cursor()
        cur.execute("INSERT INTO messages (author, destination, message, date) VALUES (?, ?, ?, ?)", (message['author'], message['destination'], message['message'], message['date_time']))
        self.conn.commit()

    def get_messages(self):
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM messages")
        messages = cur.fetchall()
        cols = [column[0] for column in cur.description]
        messages = [dict(zip(cols, row)) for row in messages]
        return messages

    def delete_message(self, message_id):
        conn = self.db_configs.conn
        cur = conn.cursor()
        cur.execute("DELETE FROM messages WHERE id = ?", (message_id,))
        self.conn.commit()