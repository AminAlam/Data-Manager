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
                                        conditions text,
                                        experiment_name text,
                                        experiment_parent text,
                                        id integer primary key autoincrement
                                    ); """, 
        """ CREATE TABLE IF NOT EXISTS tags (
                                        tag text NOT NULL,
                                        id integer primary key autoincrement
                                    ); """,
        """ CREATE TABLE IF NOT EXISTS conditions (
                                        condition text NOT NULL,
                                        id integer primary key autoincrement
                                    ); """,
        """ CREATE TABLE IF NOT EXISTS authors (
                                        author text NOT NULL,
                                        id integer primary key autoincrement
                                    ); """,
        """ CREATE TABLE IF NOT EXISTS users (
                                        username text NOT NULL,
                                        password text NOT NULL,
                                        admin bool NOT NULL,
                                        name text,
                                        email text,
                                        id integer primary key autoincrement
                                    ); """,
        """ CREATE TABLE IF NOT EXISTS conditions_templates (
                                        author text NOT NULL,
                                        template_name text NOT NULL,
                                        conditions text NOT NULL,
                                        id integer primary key autoincrement
                                    ); """,
        """ CREATE TABLE IF NOT EXISTS messages (
                                        author text NOT NULL,
                                        message text NOT NULL,
                                        date text NOT NULL,
                                        destination text NOT NULL,
                                        id integer primary key autoincrement
                                    ); """,

        # alter table messages add column destination text NOT NULL before message column;

        """ Alter table messages add column destination text NOT NULL; """,

        """ CREATE TABLE IF NOT EXISTS logs (
                                        username text NOT NULL,
                                        action text NOT NULL,
                                        date text NOT NULL,
                                        status text NOT NULL,   
                                        error text,
                                        id integer primary key autoincrement
                                    ); """
        ]
    def make_conn(self):
        self.conn = operators.create_connection(self.dbName)