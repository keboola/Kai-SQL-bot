import unittest
from database_connection import DatabaseConnection

class TestDatabaseConnection(unittest.TestCase):
    def test_init_with_secrets(self):
        # Test initialization with secrets
        connection = DatabaseConnection()
        self.assertEqual(connection.account_identifier, st.secrets["account_identifier"])
        self.assertEqual(connection.user, st.secrets["user"])
        self.assertEqual(connection.password, st.secrets["password"])
        self.assertEqual(connection.database_name, st.secrets["database_name"])
        self.assertEqual(connection.schema_name, st.secrets["schema_name"])
        self.assertEqual(connection.warehouse_name, st.secrets["warehouse_name"])
        self.assertEqual(connection.role_name, st.secrets["role_name"])

    def test_init_with_arguments(self):
        # Test initialization with arguments
        connection = DatabaseConnection(account_identifier="test_account", user="test_user",
                                       password="test_password", database_name="test_db",
                                       schema_name="test_schema", warehouse_name="test_warehouse",
                                       role_name="test_role")
        self.assertEqual(connection.account_identifier, "test_account")
        self.assertEqual(connection.user, "test_user")
        self.assertEqual(connection.password, "test_password")
        self.assertEqual(connection.database_name, "test_db")
        self.assertEqual(connection.schema_name, "test_schema")
        self.assertEqual(connection.warehouse_name, "test_warehouse")
        self.assertEqual(connection.role_name, "test_role")

if __name__ == '__main__':
    unittest.main()