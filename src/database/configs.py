import operators

class database_configs():
    def __init__(self) -> None:
        self.dbName = './src/database/db_main.db'
        self.make_conn()
        self.table_lists = [
            """ CREATE TABLE IF NOT EXISTS experiments (
                                        id_hash text NOT NULL,
                                        tags text,
                                        extra_txt text,
                                        file_path text,
                                        date DATETIME NOT NULL,
                                        author text NOT NULL,
                                        id integer primary key autoincrement
                                    ); """, 
        """ CREATE TABLE IF NOT EXISTS tags (
                                        tag text NOT NULL,
                                        id integer primary key autoincrement
                                    ); """,

        """ CREATE TABLE IF NOT EXISTS authors (
                                        author text NOT NULL,
                                        id integer primary key autoincrement
                                    ); """
        ]
    def make_conn(self):
        self.conn = operators.create_connection(self.dbName)